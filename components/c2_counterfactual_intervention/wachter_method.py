"""Wachter-style continuous optimization for an explicitly synthetic test target.

This objective is an engineering fixture, not a nutrition or C1 outcome model.
No optimized point can bypass the independent v2 evidence checks.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def optimize_test_pattern(baseline: tuple[float, float], *, target: float = 1.0,
                          max_iterations: int = 100) -> dict:
    """Relax two food-group indicators and minimize target, distance and box loss."""
    start = np.asarray(baseline, dtype=float)
    if start.shape != (2,) or np.any((start < 0) | (start > 1)):
        raise ValueError("two baseline indicators in [0,1] required")

    def objective(x):
        # Synthetic feasibility classifier: both groups present. Its smooth
        # relaxation is only for software verification of optimization.
        attainment = max(0.0, target - float(x[0] * x[1]))
        return 10.0 * attainment**2 + 0.1 * float(np.sum((x - start)**2))

    runs = []
    for initial in (start, np.array([0.5, 0.5]), np.ones(2)):
        result = minimize(objective, initial, method="L-BFGS-B", bounds=((0, 1), (0, 1)),
                          options={"maxiter": max_iterations, "ftol": 1e-10})
        runs.append(result)
    best = min(runs, key=lambda result: (float(result.fun), tuple(result.x)))
    discrete = tuple(int(value >= 0.5) for value in best.x)
    return {"status": "synthetic_software_test_only", "continuous": best.x.tolist(),
            "discrete": discrete, "objective_value": float(best.fun),
            "converged": bool(best.success), "iterations": int(best.nit),
            "initializations": len(runs), "independent_fixture_target_pass": discrete == (1, 1),
            "nutrition_validated": False, "c1_calls": 0}
