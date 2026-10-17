"""Rank category improvement, then minimal cost/change count, then stable feature order."""
from .feature_policy import ACTIONABLE, TEST_COST_UNITS
from .schemas import Change


def rank_key(changes: tuple[Change, ...], improved: bool) -> tuple:
    return (-int(improved), len(changes), sum(TEST_COST_UNITS[c.feature] for c in changes),
            tuple(ACTIONABLE.index(c.feature) for c in changes))


def select_diverse(items: list[tuple[tuple[Change, ...], bool, list[str]]], limit: int):
    ordered = sorted(items, key=lambda item: rank_key(item[0], item[1]))
    result = []
    used_first: set[str] = set()
    for item in ordered:
        if item[0][0].feature not in used_first:
            result.append(item)
            used_first.add(item[0][0].feature)
            if len(result) == limit:
                return result
    for item in ordered:
        if item not in result:
            result.append(item)
            if len(result) == limit:
                break
    return result
