"""Real-data tests for the infiltration planning (A* route) module.

Verifies terrain fields, cost construction, deterministic A* routing, the
greedy baseline, and the non-negative cost reduction over a real terrain scene.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from you_only_live_twice.infiltration_planning import (
    AStarResult,
    astar_path,
    combined_cost_field,
    greedy_baseline_path,
    guard_exposure_field,
    plan_infiltration,
    slope_magnitude,
    thermal_exposure_field,
)
from you_only_live_twice.scenario import build_scenario
from you_only_live_twice.terrain_anomaly import build_volcano_scene


@pytest.fixture()
def _scene() -> dict:
    from you_only_live_twice.terrain_anomaly import (
        terrain_anomaly_mask,
        thermal_anomaly_mask,
    )

    volcano = build_volcano_scene(seed=1967)
    _t, thermal_z = thermal_anomaly_mask(volcano["thermal"])
    _d, terrain_z = terrain_anomaly_mask(volcano["elevation"])
    return {"volcano": volcano, "thermal_z": thermal_z, "terrain_z": terrain_z}


def test_slope_magnitude_shapes() -> None:
    elevation = build_volcano_scene(seed=1967)["elevation"]
    slope = slope_magnitude(elevation)
    assert slope.shape == elevation.shape
    assert np.all(slope >= 0.0)
    # A flat grid has zero slope.
    flat = np.ones((8, 8)) * 100.0
    np.testing.assert_allclose(slope_magnitude(flat), 0.0, atol=1e-9)
    with pytest.raises(ValueError):
        slope_magnitude(np.zeros(4))


def test_thermal_exposure_field() -> None:
    z = np.array([[0.0, 3.0], [-2.0, 5.0]])
    field = thermal_exposure_field(z)
    assert np.all(field >= 0.0)
    assert np.all(field <= 1.0)
    # Negative z (cool) contributes nothing; the max maps to 1.0.
    assert field[0, 0] == 0.0
    assert field[1, 1] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        thermal_exposure_field(np.zeros(4))


def test_guard_exposure_field() -> None:
    flat = np.zeros((8, 8))
    posts = ((0, 0),)
    exposure = guard_exposure_field(flat, posts)
    assert exposure.shape == (8, 8)
    # On a flat scene every cell is visible from the post -> exposure 1 there.
    assert np.all(exposure >= 1.0)
    with pytest.raises(ValueError):
        guard_exposure_field(np.zeros(4), posts)


def test_combined_cost_field_basics() -> None:
    volcano = build_volcano_scene(seed=1967)
    elevation = volcano["elevation"]
    z = np.zeros_like(elevation)
    cost = combined_cost_field(elevation, z, ())
    assert cost.shape == elevation.shape
    assert np.all(cost >= 1.0)
    # Impassable cells -> inf.
    imp = np.zeros_like(elevation, dtype=bool)
    imp[0, 0] = True
    cost_imp = combined_cost_field(elevation, z, (), impassable=imp)
    assert math.isinf(float(cost_imp[0, 0]))
    assert not math.isinf(float(cost_imp[5, 5]))
    with pytest.raises(ValueError):
        combined_cost_field(elevation, np.zeros((5, 5)), ())


def test_astar_path_is_optimal_and_deterministic() -> None:
    # A simple uniform field: cost == Manhattan distance.
    cost = np.ones((10, 10))
    a = astar_path(cost, (0, 0), (7, 4))
    b = astar_path(cost, (0, 0), (7, 4))
    assert a == b
    assert a.path[0] == (0, 0)
    assert a.path[-1] == (7, 4)
    assert a.cost == pytest.approx(11.0)  # 7 + 4 hops at unit cost
    assert a.length == 11
    assert a.expanded >= a.length


def test_astar_deterministic_obstacle_field() -> None:
    cost = np.ones((10, 10))
    cost[5, :9] = np.inf  # wall across the middle, with a gap at the right edge
    result = astar_path(cost, (0, 0), (9, 9))
    # The path must route around the wall (row 5 only crossed through the gap).
    assert all(r != 5 or c == 9 for r, c in result.path)
    assert result.path[0] == (0, 0)
    assert result.path[-1] == (9, 9)
    assert astar_path(cost, (0, 0), (9, 9)) == result


def test_astar_validates_impassable_endpoints() -> None:
    cost = np.ones((5, 5))
    cost[2, 2] = np.inf
    with pytest.raises(ValueError):
        astar_path(cost, (2, 2), (0, 0))
    with pytest.raises(ValueError):
        astar_path(cost, (0, 0), (2, 2))
    # No path when a wall fully separates start and goal.
    wall = np.ones((5, 5))
    wall[2, :] = np.inf
    with pytest.raises(ValueError):
        astar_path(wall, (0, 0), (4, 4))
    with pytest.raises(ValueError):
        astar_path(np.zeros(4), (0, 0), (1, 1))


def test_greedy_baseline_is_an_upper_bound() -> None:
    cost = np.ones((10, 10))
    cost[5, :9] = np.inf
    greedy = greedy_baseline_path(cost, (0, 0), (9, 9))
    optimal = astar_path(cost, (0, 0), (9, 9))
    assert greedy.path[-1] == (9, 9)
    assert greedy.cost >= optimal.cost  # greedy is never better than A*
    assert greedy.cost > 0.0


def test_canonical_scene_plans_a_route_with_reduction() -> None:
    scenario = build_scenario()
    volcano = scenario["volcano"]
    infil = scenario["infiltration"]
    plan = plan_infiltration(
        volcano["elevation"],
        scenario["thermal_z"],
        infil["guard_posts"],
        infil["start"],
        infil["goal"],
        impassable=infil["impassable"],
    )
    assert plan["optimal_path"][0] == infil["start"]
    assert plan["optimal_path"][-1] == infil["goal"]
    assert plan["path_length"] > 0
    assert plan["baseline_cost"] > 0.0
    # A* optimality guarantees a non-negative reduction (same search space).
    assert plan["cost_reduction"] >= -1e-9
    assert plan["thermal_exposure"] >= 0.0
    assert AStarResult(
        path=plan["optimal_path"], cost=plan["optimal_cost"], expanded=plan["expanded"]
    )
