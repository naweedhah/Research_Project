"""FACE-inspired directed reference graph, not an exact FACE reproduction."""
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Callable

from .contracts import PredictorCompatibilityError
from .feature_policy import ACTIONABLE, validate_changes
from .feasibility import check_feasibility
from .predictor import Predictor
from .prediction_policy import acceptance_reason, checked_prediction
from .schemas import Change, ChildFeatures, FeasibilityContext
from .synthetic_data import synthetic_reference_points

Point = tuple[int, int]


@dataclass(frozen=True)
class GraphCandidate:
    changes: tuple[Change, ...]
    path: tuple[Point, ...]
    path_cost: float


def build_reference_graph(reference: tuple[Point, ...]) -> dict[Point, tuple[tuple[Point, float], ...]]:
    """Directed +1 Manhattan neighbors; cost penalizes sparse grid neighborhoods."""
    nodes = set(reference)
    if len(nodes) != len(reference):
        raise ValueError("duplicate reference points")
    if any(not (1 <= m <= 5 and 0 <= d <= 5) for m, d in nodes):
        raise ValueError("reference point outside synthetic feature bounds")
    degrees = {p: sum((p[0] + dm, p[1] + dd) in nodes
                      for dm, dd in ((1, 0), (-1, 0), (0, 1), (0, -1))) for p in nodes}
    graph = {}
    for point in sorted(nodes):
        neighbors = []
        for neighbor in ((point[0] + 1, point[1]), (point[0], point[1] + 1)):
            if neighbor in nodes:
                # Unit L1 edge length times an inverse local-density proxy.
                weight = 1.0 + 1.0 / (1 + min(degrees[point], degrees[neighbor]))
                neighbors.append((neighbor, weight))
        graph[point] = tuple(neighbors)
    return graph


def _changes(start: Point, end: Point) -> tuple[Change, ...]:
    return tuple(Change(feature=feature, from_value=start[i], to_value=end[i])
                 for i, feature in enumerate(ACTIONABLE) if start[i] != end[i])


def bounded_reachable_paths(graph: dict[Point, tuple[tuple[Point, float], ...]], start: Point,
                            max_steps: int, edge_allowed: Callable[[tuple[Point, ...], Point], bool]
                            ) -> list[tuple[float, tuple[Point, ...]]]:
    """Dijkstra on (point, steps), retaining paths with different remaining budgets."""
    if start not in graph:
        return []
    queue: list[tuple[float, tuple[Point, ...]]] = [(0.0, (start,))]
    best = {(start, 0): 0.0}
    reached = []
    while queue:
        distance, path = heappop(queue)
        point = path[-1]
        steps = len(path) - 1
        if distance > best.get((point, steps), float("inf")):
            continue
        reached.append((distance, path))
        if steps >= max_steps:
            continue
        for neighbor, weight in graph[point]:
            if weight <= 0:
                raise ValueError("graph edge weights must be positive")
            if not edge_allowed(path, neighbor):
                continue
            new_distance = distance + weight
            state = (neighbor, steps + 1)
            if new_distance < best.get(state, float("inf")):
                best[state] = new_distance
                heappush(queue, (new_distance, path + (neighbor,)))
    return reached


def generate_face_paths(child: ChildFeatures, context: FeasibilityContext,
                        predictor: Predictor, max_changes: int,
                        reference: tuple[Point, ...] | None = None) -> list[GraphCandidate]:
    if reference is None:
        if predictor.contract.mode == "real":
            raise PredictorCompatibilityError("real graph reference data unavailable")
        reference = synthetic_reference_points()
    graph = build_reference_graph(reference)
    start = (child.meals_per_day, child.dietary_diversity)
    def edge_allowed(path: tuple[Point, ...], neighbor: Point) -> bool:
        point = path[-1]
        step = _changes(point, neighbor)
        current = child.model_validate({**child.model_dump(), **dict(zip(ACTIONABLE, point))})
        cumulative = _changes(start, neighbor)
        return (not validate_changes(current, step) and not validate_changes(child, cumulative)
                and check_feasibility(step, context)[0] == "feasible"
                and check_feasibility(cumulative, context)[0] == "feasible")

    found: dict[Point, GraphCandidate] = {}
    baseline = checked_prediction(predictor, child)
    for distance, path in bounded_reachable_paths(graph, start, max_changes, edge_allowed):
        point = path[-1]
        if point != start:
            candidate = child.model_validate({**child.model_dump(), **dict(zip(ACTIONABLE, point))})
            try:
                prediction = checked_prediction(predictor, candidate)
            except ValueError:
                continue
            if acceptance_reason(baseline, prediction, predictor.contract) is None:
                if point not in found or distance < found[point].path_cost:
                    found[point] = GraphCandidate(_changes(start, point), path, distance)
    return sorted(found.values(), key=lambda c: (c.path_cost, c.path))


def generate_face_candidates(child: ChildFeatures, context: FeasibilityContext,
                             predictor: Predictor, max_changes: int,
                             reference: tuple[Point, ...] | None = None) -> list[tuple[Change, ...]]:
    return [candidate.changes for candidate in
            generate_face_paths(child, context, predictor, max_changes, reference)]
