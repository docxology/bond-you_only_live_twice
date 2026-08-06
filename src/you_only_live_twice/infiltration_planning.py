"""Infiltration planning: a route into the concealed volcano lair.

To strike or extract from the hidden base an agent must travel from an entry
point on the rim to the lair core while staying off guard sight-lines and out
of thermal signature. This module plans that route with real algorithms:

* terrain fields — slope magnitude (``np.gradient``), thermal-exposure cost
  from the anomaly Z-map, and guard line-of-sight exposure (elevation-occluded
  visibility from every watch post);
* :func:`astar_path` — deterministic 4-connected A* over the combined cost
  field (heap-based, tie-broken by insertion order so the result is
  reproducible);
* :func:`greedy_baseline_path` — the same 4-connected search space negotiated
  by a greedy depth-first walk (always step to the cheapest-looking unvisited
  neighbour; retrace when it dead-ends), giving the *unplanned* route A* is
  measured against;
* :func:`plan_infiltration` — the full route report: optimal cost, path length,
  thermal exposure, and the exposure/cost reduction over the baseline.

A* optimality gives ``optimal_cost <= baseline_cost`` (and hence a non-negative
reduction) only because the baseline is a walk that *actually reaches the
goal* in the same 4-connected space: A* minimises over all such walks, and
every step cost is at least 1, so any goal-reaching walk costs at least as
much. A baseline that stopped short of the goal would carry no such guarantee —
its cost would simply be the cost of a shorter journey — which is why
:func:`greedy_baseline_path` backtracks out of dead ends and raises when the
goal is unreachable rather than returning a truncated route. The module is
infrastructure-free and deterministic.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "AStarResult",
    "astar_path",
    "combined_cost_field",
    "greedy_baseline_path",
    "guard_exposure_field",
    "plan_infiltration",
    "slope_magnitude",
]


@dataclass(frozen=True)
class AStarResult:
    """Deterministic A* outcome: the optimal path and its cost."""

    path: tuple[tuple[int, int], ...]  #: cells from start (inclusive) to goal.
    cost: float  #: total movement cost along the path.
    expanded: int  #: number of cells expanded during the search.

    @property
    def length(self) -> int:
        """Number of hops along the path."""
        return len(self.path) - 1


def slope_magnitude(elevation: np.ndarray) -> np.ndarray:
    """Per-cell slope magnitude :math:`\\sqrt{(\\partial z/\\partial r)^2 + (\\partial z/\\partial c)^2}`."""
    if elevation.ndim != 2:
        raise ValueError("elevation must be 2-D")
    grady, gradx = np.gradient(elevation)
    return np.hypot(gradx, grady)  # type: ignore[no-any-return]


def _normalize(values: np.ndarray) -> np.ndarray:
    """Scale a non-negative field to [0, 1] (0 stays 0)."""
    maximum = float(values.max())
    if maximum <= 0.0 or not math.isfinite(maximum):
        return np.zeros_like(values, dtype=float)
    return values / maximum


def thermal_exposure_field(thermal_z: np.ndarray) -> np.ndarray:
    """Thermal detection risk per cell from the anomaly Z-map, in [0, 1].

    Only a hot anomaly (``thermal_z > 0``) raises the risk of being spotted;
    cool/neutral cells carry no thermal penalty.
    """
    if thermal_z.ndim != 2:
        raise ValueError("thermal_z must be 2-D")
    return _normalize(np.maximum(0.0, thermal_z))


def _line_occluded(
    elevation: np.ndarray,
    post: tuple[int, int],
    cell: tuple[int, int],
) -> bool:
    """True when terrain blocks the sight line between a guard post and a cell.

    Samples the segment at integer grid points and compares the interpolated
    sight-line height against the terrain height, mirroring a standard
    digital-elevation line-of-sight test.
    """
    r0, c0 = post
    r1, c1 = cell
    steps = max(abs(r1 - r0), abs(c1 - c0))
    if steps == 0:
        return False
    post_h = float(elevation[r0, c0])
    cell_h = float(elevation[r1, c1])
    # ``k`` runs over [1, steps-1] exclusive, so the integer-rounded sample
    # ``(r, c)`` can never land exactly on the post (t=0) or the cell (t=1);
    # no endpoint guard is needed and any such check would be dead code.
    for k in range(1, steps):
        t = k / steps
        r = round(r0 + t * (r1 - r0))
        c = round(c0 + t * (c1 - c0))
        line_h = post_h + t * (cell_h - post_h)
        if float(elevation[r, c]) > line_h + 1e-6:
            return True
    return False


def guard_exposure_field(
    elevation: np.ndarray, guard_posts: tuple[tuple[int, int], ...]
) -> np.ndarray:
    """Per-cell count of guard posts with a clear line of sight.

    A higher count means the agent would be visible to more watchers at that
    cell, raising detection risk.
    """
    if elevation.ndim != 2:
        raise ValueError("elevation must be 2-D")
    exposure = np.zeros(elevation.shape, dtype=float)
    rows, cols = np.indices(elevation.shape)
    for post in guard_posts:
        visible = np.zeros(elevation.shape, dtype=bool)
        for r, c in zip(rows.ravel(), cols.ravel()):
            visible[r, c] = not _line_occluded(elevation, post, (int(r), int(c)))
        exposure += visible.astype(float)
    return exposure


def combined_cost_field(
    elevation: np.ndarray,
    thermal_z: np.ndarray,
    guard_posts: tuple[tuple[int, int], ...],
    impassable: np.ndarray | None = None,
    slope_weight: float = 2.0,
    thermal_weight: float = 3.0,
    guard_weight: float = 4.0,
) -> np.ndarray:
    """Per-cell movement cost combining slope, thermal and guard exposure.

    The base per-step cost is ``1.0``; the three risk terms are added as
    weighted normalized components. Cells flagged in ``impassable`` (or outside
    the grid) get infinite cost. ``guard_weight`` uses
    :func:`guard_exposure_field` rescaled by the number of posts, so it stays in
    [0, 1].
    """
    if elevation.shape != thermal_z.shape:
        raise ValueError("elevation and thermal_z must share the same shape")
    slope = _normalize(slope_magnitude(elevation))
    thermal = thermal_exposure_field(thermal_z)
    guard_n = guard_exposure_field(elevation, guard_posts)
    guard = _normalize(guard_n) if len(guard_posts) else np.zeros_like(elevation)

    cost = 1.0 + slope_weight * slope + thermal_weight * thermal + guard_weight * guard
    if impassable is not None:
        if impassable.shape != elevation.shape:
            raise ValueError("impassable must match the elevation shape")
        cost = np.where(impassable, np.inf, cost)
    return cost


def _neighbors(
    cell: tuple[int, int], shape: tuple[int, int]
) -> tuple[tuple[int, int], ...]:
    r, c = cell
    out: list[tuple[int, int]] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < shape[0] and 0 <= nc < shape[1]:
            out.append((nr, nc))
    return tuple(out)


def astar_path(
    cost_field: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> AStarResult:
    """Deterministic 4-connected A* from ``start`` to ``goal``.

    Uses an admissible Manhattan heuristic (every step costs at least 1.0,
    costs are non-negative), so the returned path is globally optimal. Ties in
    ``(f, g)`` are broken by a monotonically increasing insertion counter,
    making the result byte-reproducible.
    """
    if cost_field.ndim != 2:
        raise ValueError("cost_field must be 2-D")
    rows, cols = cost_field.shape
    start_cost = float(cost_field[start])
    if math.isinf(start_cost):
        raise ValueError("start cell is impassable")
    if math.isinf(float(cost_field[goal])):
        raise ValueError("goal cell is impassable")

    def h(cell: tuple[int, int]) -> float:
        return float(abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]))

    counter = 0
    # Heap entries are raw tuples (f, g, counter, cell); the counter makes
    # pops deterministic among equal (f, g).
    open_heap: list[tuple[float, float, int, tuple[int, int]]] = []
    start_g = 0.0
    heapq.heappush(open_heap, (start_g + h(start), start_g, counter, start))
    counter += 1
    g_score: dict[tuple[int, int], float] = {start: start_g}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    expanded = 0

    while open_heap:
        _current_f, current_g, _counter, cell = heapq.heappop(open_heap)
        if cell == goal:
            return AStarResult(
                path=_reconstruct(came_from, start, goal),
                cost=current_g,
                expanded=expanded,
            )
        expanded += 1
        for neighbor in _neighbors(cell, (rows, cols)):
            step = float(cost_field[neighbor])
            if math.isinf(step):
                continue
            tentative = current_g + step
            if tentative < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative
                came_from[neighbor] = cell
                heapq.heappush(
                    open_heap, (tentative + h(neighbor), tentative, counter, neighbor)
                )
                counter += 1
    raise ValueError("no path exists from start to goal")


def _reconstruct(
    came_from: dict[tuple[int, int], tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    cells: list[tuple[int, int]] = [goal]
    current = goal
    while current != start:
        current = came_from[current]
        cells.append(current)
    cells.reverse()
    return tuple(cells)


def greedy_baseline_path(
    cost_field: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> AStarResult:
    """A greedy depth-first walk over the same 4-connected space.

    Steps to the unvisited neighbour with the lowest total estimate
    ``move_cost + Manhattan(neighbour, goal)``. On a dead end it *retraces* one
    cell along the walk it came by — paying that cell's cost again, exactly as
    an agent physically doubling back would — and tries the next-best branch
    from there. It therefore always reaches the goal when the goal is reachable,
    and raises ``ValueError`` when it is not.

    That termination property is what makes the reported reduction meaningful:
    the returned ``cost`` is the cost of a real goal-reaching walk in the same
    space A* minimises over, so ``astar_path(...).cost <= greedy.cost`` holds.
    An earlier version broke out of dead ends and returned a truncated route;
    its cost was then the cost of a *shorter journey*, which can be lower than
    the optimal cost of the full journey, making the reduction negative.

    The returned ``path`` is the walk in traversal order and may repeat cells
    where the search backtracked; ``expanded`` counts the steps taken.
    """
    if cost_field.ndim != 2:
        raise ValueError("cost_field must be 2-D")
    rows, cols = cost_field.shape
    if math.isinf(float(cost_field[start])):
        raise ValueError("start cell is impassable")
    if math.isinf(float(cost_field[goal])):
        raise ValueError("goal cell is impassable")
    visited: set[tuple[int, int]] = {start}
    branch: list[tuple[int, int]] = [start]  # the un-retraced stem of the walk
    path: list[tuple[int, int]] = [start]  # every cell entered, in order
    cost = 0.0

    def h(cell: tuple[int, int]) -> float:
        return float(abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]))

    while branch[-1] != goal:
        current = branch[-1]
        candidates = [
            (n, float(cost_field[n]) + h(n))
            for n in _neighbors(current, (rows, cols))
            if n not in visited and not math.isinf(float(cost_field[n]))
        ]
        if candidates:
            best = min(candidates, key=lambda pair: (pair[1], pair[0]))[0]
            visited.add(best)
            branch.append(best)
        else:
            # Dead end: retrace one cell, paying to walk back over it.
            branch.pop()
            if not branch:
                raise ValueError("no path exists from start to goal")
            best = branch[-1]
        cost += float(cost_field[best])
        path.append(best)
    return AStarResult(path=tuple(path), cost=cost, expanded=len(path))


def plan_infiltration(
    elevation: np.ndarray,
    thermal_z: np.ndarray,
    guard_posts: tuple[tuple[int, int], ...],
    start: tuple[int, int],
    goal: tuple[int, int],
    impassable: np.ndarray | None = None,
    slope_weight: float = 2.0,
    thermal_weight: float = 3.0,
    guard_weight: float = 4.0,
) -> dict[str, Any]:
    """Plan the infiltration route and report cost, exposure and reduction.

    Returns a dict with ``optimal_path``, ``optimal_cost``, ``path_length``,
    ``expanded``, ``thermal_exposure`` (sum of thermal risk along the optimal
    path), ``baseline_cost``, ``cost_reduction`` (1 - optimal/baseline) and
    ``baseline_path``.

    Both routes end on ``goal`` — :func:`greedy_baseline_path` raises rather
    than returning a truncated walk — so ``cost_reduction`` is non-negative by
    A* optimality, not by a favourable comparator.
    """
    cost_field = combined_cost_field(
        elevation,
        thermal_z,
        guard_posts,
        impassable=impassable,
        slope_weight=slope_weight,
        thermal_weight=thermal_weight,
        guard_weight=guard_weight,
    )
    optimal = astar_path(cost_field, start, goal)
    baseline = greedy_baseline_path(cost_field, start, goal)
    exposure = float(
        sum(thermal_exposure_field(thermal_z)[r, c] for r, c in optimal.path)
    )
    reduction = 1.0 - optimal.cost / baseline.cost if baseline.cost > 0.0 else 0.0
    return {
        "optimal_path": optimal.path,
        "optimal_cost": optimal.cost,
        "path_length": optimal.length,
        "expanded": optimal.expanded,
        "thermal_exposure": exposure,
        "baseline_cost": baseline.cost,
        "cost_reduction": reduction,
        "baseline_path": baseline.path,
    }
