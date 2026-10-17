"""Exhaustive bounded one- and two-feature search with stable ordering."""
from itertools import combinations

from .feature_policy import ACTIONABLE, next_values
from .schemas import Change, ChildFeatures


def generate_candidates(child: ChildFeatures, max_changes: int = 2) -> list[tuple[Change, ...]]:
    options = [Change(feature=f, from_value=getattr(child, f), to_value=v)
               for f in ACTIONABLE for v in next_values(child, f)]
    result: list[tuple[Change, ...]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for size in range(1, max_changes + 1):
        for group in combinations(options, size):
            key = tuple(sorted((c.feature, str(c.to_value)) for c in group))
            if len({c.feature for c in group}) == size and key not in seen:
                seen.add(key)
                result.append(group)
    return result
