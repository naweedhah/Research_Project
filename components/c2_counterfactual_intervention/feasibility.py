"""Unknown evidence remains unresolved; test costs are abstract units."""
from .feature_policy import TEST_COST_UNITS
from .schemas import Change, FeasibilityContext


def check_feasibility(changes: tuple[Change, ...], context: FeasibilityContext) -> tuple[str, list[str]]:
    rejected: list[str] = []
    unresolved: list[str] = []
    cost = sum(TEST_COST_UNITS[c.feature] for c in changes)
    if context.budget_units is None:
        unresolved.append("budget unknown")
    elif cost > context.budget_units:
        rejected.append("exceeds supplied budget")
    for change in changes:
        feature = change.feature
        for name in ("available", "practical", "age_suitable", "eligible", "clinically_suitable", "transition_justified"):
            value = getattr(context, name).get(feature)
            if value is False:
                rejected.append(f"{feature}: {name} is false")
            elif value is None:
                unresolved.append(f"{feature}: {name} unknown")
    if rejected:
        return "rejected", rejected + unresolved
    if unresolved:
        return "unresolved", unresolved
    return "feasible", ["all supplied feasibility checks passed; professional review still required"]
