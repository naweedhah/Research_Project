"""FACE-inspired directed reference graph, not an exact FACE reproduction."""
from dataclasses import dataclass
from heapq import heappop, heappush

from .feature_policy import ACTIONABLE, validate_changes
from .feasibility import check_feasibility
from .predictor import Predictor
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


def generate_face_paths(child: ChildFeatures, context: FeasibilityContext,
                        predictor: Predictor, max_changes: int,
                        reference: tuple[Point, ...] | None = None) -> list[GraphCandidate]:
    reference = synthetic_reference_points() if reference is None else reference
    graph = build_reference_graph(reference)
    start = (child.meals_per_day, child.dietary_diversity)
    if start not in graph:
        return []
    queue: list[tuple[float, tuple[Point, ...]]] = [(0.0, (start,))]
    best = {start: 0.0}
    found: list[GraphCandidate] = []
    while queue:
        distance, path = heappop(queue)
        point = path[-1]
        if distance > best.get(point, float("inf")):
            continue
        if point != start:
            candidate = child.model_validate({**child.model_dump(), **dict(zip(ACTIONABLE, point))})
            if predictor.predict_category(candidate) == "lower_concern":
                found.append(GraphCandidate(_changes(start, point), path, distance))
        if len(path) - 1 >= max_changes:
            continue
        for neighbor, weight in graph[point]:
            step = _changes(point, neighbor)
            current = child.model_validate({**child.model_dump(), **dict(zip(ACTIONABLE, point))})
            cumulative = _changes(start, neighbor)
            if validate_changes(current, step) or validate_changes(child, cumulative):
                continue
            if check_feasibility(step, context)[0] != "feasible":
                continue
            if check_feasibility(cumulative, context)[0] != "feasible":
                continue
            new_distance = distance + weight
            if new_distance < best.get(neighbor, float("inf")):
                best[neighbor] = new_distance
                heappush(queue, (new_distance, path + (neighbor,)))
    return sorted(found, key=lambda c: (c.path_cost, c.path))


def generate_face_candidates(child: ChildFeatures, context: FeasibilityContext,
                             predictor: Predictor, max_changes: int,
                             reference: tuple[Point, ...] | None = None) -> list[tuple[Change, ...]]:
    return [candidate.changes for candidate in
            generate_face_paths(child, context, predictor, max_changes, reference)]
