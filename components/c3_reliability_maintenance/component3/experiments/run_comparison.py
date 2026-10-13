"""Comparison harness (spec §16): runs all four strategies over a set of stress scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from component3.adapt.candidate import CandidateModel
from component3.adapt.retrain import fit_with_threshold
from component3.config import PromotionCriteria, Thresholds
from component3.experiments.metrics_experiment import (
    failed_adaptation_rate,
    intervention_rate,
    mean_action_cost,
    unnecessary_intervention_rate,
)
from component3.experiments.stress_scenarios import Scenario
from component3.experiments.strategies import STRATEGY_DECISION_FNS, build_orchestrator
from component3.interfaces import FeatureSchema, ModelMetadata
from component3.orchestrator import CycleReport
from component3.registry.registry import ModelRegistry


def fit_initial_model(
    model_factory: Callable[[], object],
    X: pd.DataFrame,
    y: np.ndarray,
    schema: FeatureSchema,
    version: str = "v1.0",
    operating_sensitivity: float = 0.80,
) -> CandidateModel:
    estimator, threshold = fit_with_threshold(model_factory, X, y, operating_sensitivity)
    classes = getattr(estimator, "classes_", np.unique(y))
    metadata = ModelMetadata(version=version, classes=tuple(np.asarray(classes).tolist()), parent_version=None,
                             action="initial", schema=schema, decision_threshold=threshold)
    return CandidateModel(estimator=estimator, version=version, metadata=metadata)


@dataclass(frozen=True)
class ComparisonRow:
    strategy: str
    scenario: str
    category: str
    cycle: CycleReport


def run_comparison(
    scenarios: list[Scenario],
    reference_data: pd.DataFrame,
    reference_labels: np.ndarray,
    current_data: pd.DataFrame,
    current_labels: np.ndarray,
    adapt_data: pd.DataFrame,
    adapt_labels: np.ndarray,
    verify_data: pd.DataFrame,
    verify_labels: np.ndarray,
    schema: FeatureSchema,
    model_factory: Callable[[], object],
    thresholds: Thresholds | None = None,
    criteria: PromotionCriteria | None = None,
    strategies: list[str] | None = None,
    seed: int = 0,
) -> list[ComparisonRow]:
    """Runs each strategy against each scenario from the same starting model and
    reference/adapt/verify splits, varying only what the scenario perturbs."""
    strategies = strategies or list(STRATEGY_DECISION_FNS)
    rng = np.random.default_rng(seed)
    rows: list[ComparisonRow] = []

    for scenario in scenarios:
        shifted_current, shifted_current_labels = scenario.apply(current_data, current_labels, rng)
        shifted_adapt, shifted_adapt_labels = scenario.apply(adapt_data, adapt_labels, rng)

        for strategy in strategies:
            initial_model = fit_initial_model(model_factory, reference_data, reference_labels, schema)
            registry = ModelRegistry(initial_model)
            orchestrator = build_orchestrator(strategy, registry, schema, thresholds, criteria)

            cycle = orchestrator.run_cycle(
                reference_data=reference_data,
                current_data=shifted_current,
                current_labels=shifted_current_labels,
                adapt_data=shifted_adapt,
                adapt_labels=shifted_adapt_labels,
                verify_data=verify_data,
                verify_labels=verify_labels,
                model_factory=model_factory,
            )
            rows.append(ComparisonRow(strategy=strategy, scenario=scenario.name, category=scenario.category, cycle=cycle))

    return rows


def summarize(rows: list[ComparisonRow]) -> pd.DataFrame:
    records = []
    for strategy in sorted({r.strategy for r in rows}):
        cycles = [r.cycle for r in rows if r.strategy == strategy]
        promoted = sum(1 for c in cycles if c.promoted)
        records.append(
            {
                "strategy": strategy,
                "n_cycles": len(cycles),
                "intervention_rate": intervention_rate(cycles),
                "unnecessary_intervention_rate": unnecessary_intervention_rate(cycles),
                "failed_adaptation_rate": failed_adaptation_rate(cycles),
                "promoted_rate": promoted / len(cycles) if cycles else float("nan"),
                "mean_action_cost": mean_action_cost(cycles),
            }
        )
    return pd.DataFrame.from_records(records)
