import numpy as np

from component3.config import PromotionCriteria
from component3.experiments.run_comparison import run_comparison, summarize
from component3.experiments.stress_scenarios import default_scenarios
from component3.experiments.strategies import STRATEGY_DECISION_FNS
from tests.helpers import make_toy_data, model_factory, toy_schema

LENIENT = PromotionCriteria(min_recall_macro=0.0, min_minority_recall=0.0, max_ece=1.0, max_brier=3.0, max_regression=1.0)


def test_default_scenarios_cover_expected_categories():
    scenarios = default_scenarios(["f0", "f1", "f2"], target_prevalence={0: 0.34, 1: 0.33, 2: 0.33})
    assert {s.category for s in scenarios} == {"A", "B", "C", "D"}


def test_run_comparison_produces_one_row_per_strategy_per_scenario():
    schema = toy_schema()
    X, y = make_toy_data(seed=3, n_samples=800)
    n = len(X)
    ref_idx, cur_idx, adapt_idx, verify_idx = np.array_split(np.arange(n), 4)
    scenarios = default_scenarios(list(X.columns)[:3])

    rows = run_comparison(
        scenarios=scenarios,
        reference_data=X.iloc[ref_idx].reset_index(drop=True),
        reference_labels=y[ref_idx],
        current_data=X.iloc[cur_idx].reset_index(drop=True),
        current_labels=y[cur_idx],
        adapt_data=X.iloc[adapt_idx].reset_index(drop=True),
        adapt_labels=y[adapt_idx],
        verify_data=X.iloc[verify_idx].reset_index(drop=True),
        verify_labels=y[verify_idx],
        schema=schema,
        model_factory=model_factory,
        criteria=LENIENT,
        seed=0,
    )

    assert len(rows) == len(scenarios) * len(STRATEGY_DECISION_FNS)

    summary = summarize(rows)
    assert set(summary["strategy"]) == set(STRATEGY_DECISION_FNS)
    assert (summary["n_cycles"] == len(scenarios)).all()
    # Static strategy never intervenes, by construction.
    static_row = summary[summary["strategy"] == "static"].iloc[0]
    assert static_row["intervention_rate"] == 0.0
