"""Component 3 service for the integrated backend: one deployed model, its registry, and maintenance cycles.

The C3 package lives in components/c3_reliability_maintenance and is added to the import path here. The model is the
C3 stand-in for C1 (swap in C1's model through the same interface). Child-level data is read from C3_DATA_DIR and
never returned by the API: responses contain only aggregate metrics, decisions and evidence.
"""

from __future__ import annotations

import json
import math
import sys
import threading
from datetime import date
from pathlib import Path

import numpy as np

C3_ROOT = Path(__file__).resolve().parents[3] / "components" / "c3_reliability_maintenance"
if str(C3_ROOT) not in sys.path:
    sys.path.insert(0, str(C3_ROOT))

from component3.assess.subgroups import sex_age_groups  # noqa: E402
from component3.context import build_context_report  # noqa: E402
from component3.context import sources as context_sources  # noqa: E402
from component3.data import CATEGORICAL, NUMERIC, load_prediction_data  # noqa: E402
from component3.experiments.run_real import evaluate, shift_grid, synthetic_setting, thresholds_from_baseline  # noqa: E402
from component3.models import standin_factory  # noqa: E402
from component3.orchestrator import C3Orchestrator  # noqa: E402
from component3.registry.registry import ModelRegistry  # noqa: E402
from component3.validate import default_validator  # noqa: E402

FIXTURES = C3_ROOT / "tests" / "fixtures"


def jsonable(value):
    """numpy / NaN / dataclass-free conversion so FastAPI can serialise evidence dictionaries."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(float(value)) else round(float(value), 4)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    return value


def scenarios() -> list[dict]:
    return [{"family": s.family, "strength": s.strength, "label": s.label, "category": s.category}
            for s in shift_grid()]


class C3Service:
    def __init__(self, target: str = "underweight", seed: int = 0):
        self.target, self.seed = target, seed
        self._lock = threading.Lock()
        self._ready = False
        self.last_cycle: dict | None = None

    # ------------------------------------------------------------ setup
    def _ensure_ready(self, require_approval: bool = False) -> None:
        if self._ready:
            self.orchestrator.require_approval = require_approval
            return
        self.data = load_prediction_data(self.target)
        self.factory = standin_factory(NUMERIC, CATEGORICAL)
        self.setting = synthetic_setting(self.data, self.factory, self.seed)
        self.baseline = evaluate(self.setting.model, *self.setting.baseline_pool)
        self.thresholds, self.criteria = thresholds_from_baseline(self.baseline)
        self.registry = ModelRegistry(self.setting.model)
        self.orchestrator = C3Orchestrator(self.registry, self.data.schema, self.thresholds, self.criteria,
                                           validator=default_validator(), group_fn=sex_age_groups(),
                                           require_approval=require_approval)
        self._ready = True

    def reset(self) -> dict:
        with self._lock:
            self._ready, self.last_cycle = False, None
            self._ensure_ready()
            return self.status()

    # ------------------------------------------------------------ queries
    def status(self) -> dict:
        if not self._ready:
            try:
                self._ensure_ready()
            except FileNotFoundError as exc:
                return {"component": 3, "ready": False, "reason": str(exc)}
        active = self.registry.active_model
        return {"component": 3, "ready": True, "target": f"{self.target} in 2026 (predicted from 2025)",
                "active_version": active.version, "decision_threshold": jsonable(active.metadata.decision_threshold),
                "pending_approval": self.registry.pending.version if self.registry.pending else None,
                "baseline": jsonable(self.baseline), "thresholds": {
                    "psi_flag": self.thresholds.psi_flag, "reliability_tau": round(self.thresholds.reliability_tau, 3),
                    "calibration_tau": round(self.thresholds.calibration_tau, 3),
                    "min_sensitivity": self.thresholds.min_minority_recall},
                "last_cycle": self.last_cycle}

    def history(self) -> list[dict]:
        self._ensure_ready()
        return [{"version": h.version, "action": h.action, "parent": h.parent_version,
                 "time": h.timestamp.isoformat(timespec="seconds"), "reason": h.reason,
                 "verification_passed": None if h.verification is None else h.verification.passed}
                for h in self.registry.history]

    @staticmethod
    def _context_report(start: date, end: date, offline: bool):
        """Offline mode uses the bundled real GDACS/WFP samples, so demos work without internet."""
        kwargs = {}
        if offline:
            kwargs = {"events": context_sources.parse_gdacs(json.loads((FIXTURES / "gdacs_sri_lanka_2025.json").read_text())),
                      "prices": context_sources.parse_wfp_prices(FIXTURES / "wfp_food_prices_lka_east_sample.csv"),
                      "fetch": False}
        return build_context_report(start, end, **kwargs)

    def context(self, start: date, end: date, offline: bool = False) -> dict:
        report = self._context_report(start, end, offline)
        return {**jsonable(report.as_evidence()), "explanation": report.explanation(), "area": report.area.name}

    # ------------------------------------------------------------ actions
    def run_cycle(self, family: str = "none", strength: float = 0.0, with_labels: bool = True,
                  context_start: date | None = None, context_end: date | None = None, offline_context: bool = True,
                  require_approval: bool = False) -> dict:
        with self._lock:
            self._ensure_ready(require_approval)
            shift = next((s for s in shift_grid() if s.family == family and s.strength == strength), None)
            if shift is None:
                raise ValueError(f"unknown scenario {family} / {strength}")
            rng = np.random.default_rng(len(self.registry.history))
            parts = {k: shift.apply(X, y, rng) for k, (X, y) in self.setting.parts.items()}
            context = (self._context_report(context_start, context_end, offline_context)
                       if context_start and context_end else None)
            before = self.registry.active_model.version
            cycle = self.orchestrator.run_cycle(
                reference_data=self.setting.X_ref, current_data=parts["current"][0],
                current_labels=parts["current"][1] if with_labels else None,
                adapt_data=parts["adapt"][0], adapt_labels=parts["adapt"][1],
                verify_data=parts["verify"][0], verify_labels=parts["verify"][1],
                model_factory=self.factory, retrain_history=(self.setting.X_ref, self.setting.y_ref), context=context)
            test_X, test_y = parts["test"]
            self.last_cycle = jsonable({
                "scenario": shift.label, "labels_available": with_labels, "model_before": before,
                "model_after": self.registry.active_model.version,
                "decision": cycle.decision.action.value, "reason": cycle.decision.reason,
                "drift": {"any_flagged": cycle.monitoring.any_flagged,
                          "prediction_psi": cycle.monitoring.prediction_psi,
                          "flagged_features": [{"feature": r.feature, "reasons": list(r.reasons)}
                                               for r in cycle.monitoring.feature_results if r.flagged]},
                "reliability": {"status": cycle.reliability.status, "reliable": cycle.reliability.reliable,
                                "metrics": {k: v for k, v in (cycle.reliability.metrics or {}).items()
                                            if k in ("recall_macro", "auroc", "ece", "recall_per_class", "subgroups")}},
                "candidate": None if cycle.candidate is None else cycle.candidate.version,
                "verification": None if cycle.verification is None else {
                    "passed": cycle.verification.passed, "failures": list(cycle.verification.failures)},
                "promoted": cycle.promoted, "pending_approval": cycle.pending_approval, "shadow": cycle.shadow,
                "label_free_warning": cycle.decision.evidence.get("label_free_warning"),
                "validation": cycle.decision.evidence.get("validation"),
                "context": cycle.decision.evidence.get("context"),
                "possible_causes": cycle.decision.evidence.get("possible_causes"),
                "test_after_cycle": evaluate(self.registry.active_model, test_X, test_y),
            })
            return self.last_cycle

    def approve(self, approver: str = "reviewer") -> dict:
        with self._lock:
            model = self.registry.approve(approver)
            return {"approved": model.version, "active_version": self.registry.active_model.version}

    def reject_pending(self, reason: str = "rejected by reviewer") -> dict:
        with self._lock:
            self.registry.reject_pending(reason)
            return {"rejected": True, "active_version": self.registry.active_model.version}

    def rollback(self) -> dict:
        with self._lock:
            model = self.registry.rollback()
            return {"rolled_back_to": model.version}


service = C3Service()
