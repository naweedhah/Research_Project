"""Component 3 live service: the real maintenance workflow, kept apart from the demonstration sandbox (service.py).

1. Submit a batch: one screening round's model inputs, one row per child with a pseudonymous record_id. C3 validates
   it, checks drift against the active model's training data and gives a label-free warning. Outcomes are not known
   yet, so nothing is adapted at this point.
2. Submit the batch's outcomes when they arrive (the model predicts a year ahead). C3 first checks a recently
   deployed model on them (automatic rollback if it is worse than the previous one), then assesses reliability and,
   if it is harmed, builds a candidate from part of the labelled records and verifies it on the rest. Human approval
   is required by default.
3. Everything (registry with every model version, each version's training data, batches) is saved under
   C3_STATE_DIR (default components/c3_reliability_maintenance/state/, ignored by git), so it survives restarts.

Records stay on this machine and are never returned by the API: responses hold decisions and aggregate numbers only.
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from app.c3.service import C3_ROOT, context_report, cycle_summary, history_rows, jsonable
from component3.assess.subgroups import sex_age_groups
from component3.data import CATEGORICAL, NUMERIC, SCHEMA, load_prediction_data
from component3.experiments.run_real import evaluate, synthetic_setting, thresholds_from_baseline
from component3.interfaces import FeatureSchema
from component3.models import standin_factory
from component3.orchestrator import C3Orchestrator
from component3.registry import ModelRegistry, load_state, save_state
from component3.validate import default_validator

BATCH_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
MIN_RECORDS = 30     # fewer records make drift statistics and accuracy estimates meaningless
VERIFY_SHARE = 0.4   # labelled records held back to verify a candidate; never used to build it


class NotFound(LookupError):
    pass


class Conflict(RuntimeError):
    pass


def state_dir() -> Path:
    return Path(os.environ.get("C3_STATE_DIR", C3_ROOT / "state"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class LiveSetup:
    target: str
    schema: FeatureSchema
    factory: Callable[[], object]
    validator: object | None
    group_fn: Callable | None
    initial: Callable[[], dict]  # first start only: model, X_ref, y_ref, baseline, thresholds, criteria


def real_setup(target: str = "underweight", seed: int = 0) -> LiveSetup:
    """The stand-in C1 model trained on the real linked data: the same v1.0 the demonstration starts from."""
    factory = standin_factory(NUMERIC, CATEGORICAL)

    def initial() -> dict:
        data = load_prediction_data(target)
        setting = synthetic_setting(data, factory, seed)
        baseline = evaluate(setting.model, *setting.baseline_pool)
        thresholds, criteria = thresholds_from_baseline(baseline)
        return {"model": setting.model, "X_ref": setting.X_ref, "y_ref": setting.y_ref, "baseline": baseline,
                "thresholds": thresholds, "criteria": criteria}

    return LiveSetup(target, SCHEMA, factory, default_validator(), sex_age_groups(), initial)


class LiveService:
    def __init__(self, setup_fn: Callable[[], LiveSetup] = real_setup, directory: Path | None = None):
        self.setup_fn, self._directory = setup_fn, directory
        self._lock = threading.RLock()
        self.setup: LiveSetup | None = None
        self.state: dict | None = None

    # ------------------------------------------------------------ state
    @property
    def directory(self) -> Path:
        return self._directory or state_dir()

    def _state_path(self) -> Path:
        return self.directory / "state.joblib"

    def _batch_path(self, batch_id: str) -> Path:
        return self.directory / "batches" / f"{batch_id}.joblib"

    def _ready(self) -> None:
        if self.state is not None:
            return
        setup = self.setup_fn()
        if self._state_path().exists():
            state = load_state(self._state_path())
            if state["target"] != setup.target:
                raise Conflict(f"saved state is for {state['target']}, not {setup.target}; reset it or set C3_STATE_DIR")
        else:
            init = setup.initial()
            model = init["model"]
            state = {"target": setup.target, "created": _now(), "registry": ModelRegistry(model),
                     "training": {model.version: (init["X_ref"], np.asarray(init["y_ref"]))},
                     "baseline": init["baseline"], "thresholds": init["thresholds"], "criteria": init["criteria"],
                     "batches": {}, "awaiting_check": None, "last_cycle": None}
            save_state(state, self._state_path())
        self.setup, self.state = setup, state

    def _save(self) -> None:
        save_state(self.state, self._state_path())

    @property
    def registry(self) -> ModelRegistry:
        return self.state["registry"]

    def _training(self) -> tuple[pd.DataFrame, np.ndarray]:
        """Training data of the active model: the drift reference, and the history a retrained model builds on."""
        return self.state["training"][self.registry.active_model.version]

    def _orchestrator(self, require_approval: bool) -> C3Orchestrator:
        return C3Orchestrator(self.registry, self.setup.schema, self.state["thresholds"], self.state["criteria"],
                              validator=self.setup.validator, group_fn=self.setup.group_fn,
                              require_approval=require_approval)

    # ------------------------------------------------------------ input checks
    def _frame(self, records: list[dict]) -> tuple[pd.DataFrame, list[str], dict]:
        if len(records) < MIN_RECORDS:
            raise ValueError(f"a batch needs at least {MIN_RECORDS} records (got {len(records)})")
        df = pd.DataFrame.from_records(records)
        if "record_id" not in df or df["record_id"].isna().any():
            raise ValueError("every record needs a record_id")
        ids = df["record_id"].astype(str)
        if ids.duplicated().any():
            raise ValueError(f"duplicate record_id values: {sorted(set(ids[ids.duplicated()]))[:5]}")
        schema = self.setup.schema
        missing = [c for c in schema.columns if c not in df]
        if missing:
            raise ValueError(f"records are missing model input fields: {missing}")
        reference = self._training()[0]
        X, unknown = pd.DataFrame(index=df.index), {}
        for c in schema.numeric_columns:
            values = pd.to_numeric(df[c], errors="coerce")
            bad = values.isna() & df[c].notna()
            if bad.any():
                raise ValueError(f"{c} must be a number (record {ids[bad].iloc[0]})")
            X[c] = values.astype(float)
        for c in schema.categorical_columns:
            X[c] = pd.Series([np.nan if pd.isna(v) else str(v) for v in df[c]], index=df.index, dtype=object)
            known = set(reference[c].dropna().unique()) if c in reference else set()
            n_unknown = int((X[c].notna() & ~X[c].isin(known)).sum())
            if n_unknown:
                unknown[c] = n_unknown  # e.g. a typo or a new answer option; the model treats it as unseen
        notes = {"unknown_categories": unknown,
                 "ignored_fields": sorted(set(df.columns) - set(schema.columns) - {"record_id"})}
        return X[schema.columns].reset_index(drop=True), ids.tolist(), notes

    def _meta(self, batch_id: str) -> dict:
        if batch_id not in self.state["batches"]:
            raise NotFound(f"no batch {batch_id}")
        return self.state["batches"][batch_id]

    # ------------------------------------------------------------ queries
    def status(self) -> dict:
        with self._lock:
            try:
                self._ready()
            except FileNotFoundError as exc:
                return {"component": 3, "mode": "live", "ready": False, "reason": str(exc)}
            active, thr = self.registry.active_model, self.state["thresholds"]
            batches = self.state["batches"].values()
            return jsonable({
                "component": 3, "mode": "live", "ready": True, "target": f"{self.state['target']} (a year ahead)",
                "active_model": {"version": active.version, "action": active.metadata.action,
                                 "parent": active.metadata.parent_version,
                                 "trained_at": active.metadata.trained_at.isoformat(timespec="seconds"),
                                 "decision_threshold": active.metadata.decision_threshold,
                                 "training_records": len(self._training()[1])},
                "pending_approval": self.registry.pending.version if self.registry.pending else None,
                "awaiting_post_deployment_check": self.state["awaiting_check"],
                "baseline": self.state["baseline"],
                "thresholds": {"psi_flag": thr.psi_flag, "reliability_tau": thr.reliability_tau,
                               "calibration_tau": thr.calibration_tau, "min_sensitivity": thr.min_minority_recall},
                "batches": len(batches), "batches_awaiting_outcomes": sum(not b["labelled"] for b in batches),
                "last_cycle": self.state["last_cycle"]})

    def history(self) -> list[dict]:
        with self._lock:
            self._ready()
            return history_rows(self.registry)

    def batches(self) -> list[dict]:
        with self._lock:
            self._ready()
            return [{k: v for k, v in b.items() if k not in ("monitoring", "outcome_cycle")}
                    for b in self.state["batches"].values()]

    def batch(self, batch_id: str) -> dict:
        with self._lock:
            self._ready()
            return self._meta(batch_id)

    # ------------------------------------------------------------ workflow
    def submit_batch(self, records: list[dict], batch_id: str | None = None, area: str | None = None,
                     collected_from: date | None = None, collected_to: date | None = None,
                     context: str = "live") -> dict:
        with self._lock:
            self._ready()
            if batch_id is None:
                stamp, n = datetime.now(timezone.utc).strftime("B%Y%m%d-%H%M%S"), 1
                batch_id = stamp
                while batch_id in self.state["batches"]:
                    n += 1
                    batch_id = f"{stamp}-{n}"
            if not BATCH_ID.match(batch_id):
                raise ValueError("batch_id may only use letters, digits, '.', '_' and '-' (at most 64 characters)")
            if batch_id in self.state["batches"]:
                raise Conflict(f"batch {batch_id} already exists")
            if collected_from and collected_to and collected_from > collected_to:
                raise ValueError("collected_from is after collected_to")
            X, ids, notes = self._frame(records)
            ctx = (context_report(collected_from, collected_to, offline=context == "offline")
                   if collected_from and collected_to and context != "none" else None)

            before = self.registry.active_model.version
            cycle = self._orchestrator(False).run_cycle(reference_data=self._training()[0], current_data=X,
                                                        context=ctx)
            summary = cycle_summary(cycle, scenario=None, labels_available=False, model_before=before,
                                    registry=self.registry)
            meta = {"batch_id": batch_id, "area": area,
                    "collected_from": collected_from.isoformat() if collected_from else None,
                    "collected_to": collected_to.isoformat() if collected_to else None, "context": context,
                    "submitted": _now(), "records": len(X), "labelled": 0, "status": "awaiting_outcomes",
                    "model_version": before, "decision": summary["decision"], **notes}
            save_state({"X": X, "record_ids": ids}, self._batch_path(batch_id))
            self.state["batches"][batch_id] = {**meta, "monitoring": summary}
            self.state["last_cycle"] = summary
            self._save()
            return {**meta, "cycle": summary}

    def submit_outcomes(self, batch_id: str, labels: dict[str, int], require_approval: bool = True) -> dict:
        with self._lock:
            self._ready()
            meta = self._meta(batch_id)
            if meta["labelled"]:
                raise Conflict(f"outcomes for batch {batch_id} were already submitted")
            stored = load_state(self._batch_path(batch_id))
            ids = stored["record_ids"]
            unknown = sorted(set(labels) - set(ids))
            if unknown:
                raise ValueError(f"unknown record_id values: {unknown[:5]}")
            classes = list(self.registry.active_model.metadata.classes)
            bad = [k for k, v in labels.items() if v not in classes]
            if bad:
                raise ValueError(f"outcomes must be one of {classes} (record {bad[0]})")
            keep = np.array([i in labels for i in ids])
            X = stored["X"][keep].reset_index(drop=True)
            y = np.array([labels[i] for i in ids if i in labels])
            if len(y) < MIN_RECORDS:
                raise ValueError(f"at least {MIN_RECORDS} outcomes are needed (got {len(y)})")
            if min(np.sum(y == c) for c in classes) < 2:
                raise ValueError("outcomes need at least 2 children in every class to assess and verify the model")
            start, end = meta["collected_from"], meta["collected_to"]
            ctx = (context_report(date.fromisoformat(start), date.fromisoformat(end), meta["context"] == "offline")
                   if start and end and meta["context"] != "none" else None)

            result: dict = {"batch_id": batch_id, "outcomes": len(y)}
            orch = self._orchestrator(require_approval)
            # 1. A newly deployed model meets its first unseen outcomes: roll back if it is worse than the last one.
            if self.state["awaiting_check"] == self.registry.active_model.version:
                result["post_deployment_check"] = jsonable(orch.post_deployment_check(X, y))
                self.state["awaiting_check"] = None
            # 2. Assess the active model; adapt on part of the labelled records, verify on the rest.
            X_adapt, X_verify, y_adapt, y_verify = train_test_split(X, y, test_size=VERIFY_SHARE, stratify=y,
                                                                    random_state=0)
            X_adapt, X_verify = X_adapt.reset_index(drop=True), X_verify.reset_index(drop=True)
            before = self.registry.active_model.version
            X_train, y_train = self._training()
            cycle = orch.run_cycle(reference_data=X_train, current_data=X, current_labels=y,
                                   adapt_data=X_adapt, adapt_labels=y_adapt, verify_data=X_verify,
                                   verify_labels=y_verify, model_factory=self.setup.factory,
                                   retrain_history=(X_train, y_train), context=ctx)
            if cycle.candidate is not None:
                training = (X_train, y_train)
                if cycle.candidate.metadata.action == "retrain":
                    valid = (~self.setup.validator.validate(X_adapt).invalid if self.setup.validator
                             else np.ones(len(X_adapt), bool))
                    training = (pd.concat([X_train, X_adapt[valid]], ignore_index=True),
                                np.concatenate([y_train, y_adapt[valid]]))
                self.state["training"][cycle.candidate.version] = training
                if cycle.promoted:
                    self.state["awaiting_check"] = cycle.candidate.version
            summary = cycle_summary(cycle, scenario=None, labels_available=True, model_before=before,
                                    registry=self.registry)
            meta.update(labelled=len(y), status="assessed", outcomes_submitted=_now(),
                        outcome_decision=summary["decision"], outcome_cycle=summary,
                        post_deployment_check=result.get("post_deployment_check"))
            self.state["last_cycle"] = summary
            self._save()
            return {**result, "cycle": summary}

    # ------------------------------------------------------------ human controls
    def approve(self, approver: str) -> dict:
        with self._lock:
            self._ready()
            if self.registry.pending is None:
                raise Conflict("no model is waiting for approval")
            model = self.registry.approve(approver)
            self.state["awaiting_check"] = model.version
            self._save()
            return {"approved": model.version, "active_version": model.version,
                    "note": "the next batch of outcomes is checked against the previous model first"}

    def reject_pending(self, reason: str) -> dict:
        with self._lock:
            self._ready()
            if self.registry.pending is None:
                raise Conflict("no model is waiting for approval")
            version = self.registry.pending.version
            self.registry.reject_pending(reason)
            self._save()
            return {"rejected": version, "active_version": self.registry.active_model.version}

    def rollback(self) -> dict:
        with self._lock:
            self._ready()
            if self.registry.previous_model is None:
                raise Conflict("no earlier model to roll back to")
            model = self.registry.rollback()
            self.state["awaiting_check"] = None
            self._save()
            return {"rolled_back_to": model.version}

    def reset(self) -> dict:
        """Delete all live state (models, history, batches) and start again from the initial model."""
        with self._lock:
            for path in [self._state_path(), *(self.directory / "batches").glob("*.joblib")]:
                path.unlink(missing_ok=True)
            self.state = None
        return self.status()


live = LiveService()
