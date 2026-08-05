"""Deterministic mission scenario + single analysis source for VOLCANO.

This module is the single source of truth for the VOLCANO mission. :func:`build_scenario`
defines every *input* (orbits, volcano scene, activity schedule, thermal/terrain
Z-maps, capture envelope, discovery cues, infiltration geometry, emitter posts)
from fixed quantities and fixed-seed generators, so the inputs are byte-for-byte
reproducible. :func:`solve_mission` then runs all seven capabilities over those
inputs and returns the full results dict — the one object both the BOND-API
adapter (``mission.execute``) and the manuscript token generator consume, so
outcome ``results`` and manuscript ``{{TOKEN}}``s can never disagree.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np

from you_only_live_twice.emitter_localization import (
    build_sensor_posts,
    localization_error,
    localize_tdoa,
    tdoa_measurements,
)
from you_only_live_twice.hidden_base_discovery import (
    build_discovery_scene,
    discovery_probability_curve,
    expected_discovery_effort,
    rank_search_order,
)
from you_only_live_twice.infiltration_planning import plan_infiltration
from you_only_live_twice.orbital_capture import (
    capture_windows,
    phasing_lead_angle,
    phasing_wait_time,
    velocity_matching_budget,
)
from you_only_live_twice.pattern_of_life import (
    BaseActivity,
    build_weekly_activity_schedule,
    pattern_summary,
)
from you_only_live_twice.rendezvous_windows import (
    CircularOrbit,
    find_rendezvous_windows,
    hohmann_transfer,
)
from you_only_live_twice.terrain_anomaly import (
    M_PER_CELL,
    build_volcano_scene,
    detect_concealed_lair,
    terrain_anomaly_mask,
    thermal_anomaly_mask,
)

__all__ = [
    "CODENAME",
    "M_PER_CELL",
    "PACKAGE_VERSION",
    "SEED",
    "build_scenario",
    "scenario_input_hash",
    "solve_mission",
]

#: Mission identity / version for the VOLCANO (1967) film package.
CODENAME = "VOLCANO"
PACKAGE_VERSION = "0.1.0"
#: Deterministic seed — the film's release year.
SEED = 1967

#: Capture envelope: the platform can grapple while the capsule is this close
#: and slow enough (km / m·s⁻¹).
CAPTURE_MAX_RANGE_KM = 1000.0
CAPTURE_MAX_SPEED_M_S = 2200.0
CAPTURE_DT_S = 120.0
CAPTURE_HORIZON_S = 86400.0

#: Discovery sensor model (standardized-cue Gaussian likelihood ratios).
DISCOVERY_MU_HOT = 2.5
DISCOVERY_BETA = 1.5
DISCOVERY_RF_POWER = 8.0
DISCOVERY_RF_DECAY_CELLS = 6.0
DISCOVERY_RF_NOISE = 0.35

#: Infiltration model weights and geometry.
INFIL_SLOPE_WEIGHT = 2.0
INFIL_THERMAL_WEIGHT = 3.0
INFIL_GUARD_WEIGHT = 4.0
INFIL_LAVA_FRACTION = 0.92  #: cells above this fraction of cone height are lava.

#: Emitter localisation ring geometry (metres).
EMITTER_RING_RADIUS_M = 25_000.0
EMITTER_SENSOR_COUNT = 5


def _orbits() -> dict[str, Any]:
    """The chase and target orbital elements (circular, near-polar recon)."""
    return {
        # Chaser: a rocket ~550 km up on a sun-synchronous-like inclination.
        "chaser": CircularOrbit.from_altitude(
            altitude_km=550.0,
            inclination=98.2 * 3.141592653589793 / 180.0,
            raan=45.0 * 3.141592653589793 / 180.0,
            initial_phase=0.0,
        ),
        # Target: the adversary space capsule a bit higher, offset in plane.
        "target": CircularOrbit.from_altitude(
            altitude_km=800.0,
            inclination=98.2 * 3.141592653589793 / 180.0,
            raan=45.5 * 3.141592653589793 / 180.0,
            initial_phase=1.9,
        ),
    }


def build_scenario() -> dict[str, Any]:
    """Assemble the full deterministic VOLCANO scenario (all mission inputs).

    Returns a dict carrying ``orbits``, ``volcano``, ``activity``, the anomaly
    Z-maps ``thermal_z``/``terrain_z``, the discovery scene, the infiltration
    geometry, the emitter posts, ``seed`` and the computed ``input_hash``.
    """
    orbits = _orbits()
    volcano = build_volcano_scene(seed=SEED)
    activity: tuple[BaseActivity, ...] = build_weekly_activity_schedule(seed=SEED)

    _ignore_th, thermal_z = thermal_anomaly_mask(volcano["thermal"])
    _ignore_te, terrain_z = terrain_anomaly_mask(volcano["elevation"])

    # The concealed base sits where its thermal + terrain signatures are
    # strongest (the region's bounding-box centroid can sit a few cells off the
    # temperature/terrain peak), so all downstream geometry shares one
    # self-consistent "true site": the argmax of the fused anomaly Z-scores.
    fused_peak = 0.5 * thermal_z + 0.5 * terrain_z
    size_grid = int(volcano["parameters"]["size"])
    _flat_idx = int(np.argmax(fused_peak))
    lair_site = (_flat_idx // size_grid, _flat_idx % size_grid)

    discovery = build_discovery_scene(
        volcano,
        thermal_z,
        terrain_z,
        seed=SEED,
        mu_hot=DISCOVERY_MU_HOT,
        beta=DISCOVERY_BETA,
        rf_power=DISCOVERY_RF_POWER,
        rf_decay_cells=DISCOVERY_RF_DECAY_CELLS,
        rf_noise=DISCOVERY_RF_NOISE,
        true_cell=lair_site,
    )

    size = int(volcano["parameters"]["size"])
    guard_posts = (
        (2, 2),
        (2, size - 3),
        (size - 3, 2),
        (size - 3, size - 3),
    )
    infiltration = {
        "guard_posts": guard_posts,
        "start": (size - 2, size - 2),
        "goal": lair_site,
        "impassable": volcano["elevation"]
        >= INFIL_LAVA_FRACTION * float(volcano["parameters"]["cone_height_m"]),
    }

    center_m = ((size - 1) / 2.0 * M_PER_CELL, (size - 1) / 2.0 * M_PER_CELL)
    emitter_m = (
        float(lair_site[0]) * M_PER_CELL,
        float(lair_site[1]) * M_PER_CELL,
    )
    emitter = {
        "sensor_posts": _emitter_posts(center_m),
        "emitter_m": emitter_m,
        "initial_guess": center_m,
    }

    return {
        "orbits": orbits,
        "volcano": volcano,
        "activity": activity,
        "thermal_z": thermal_z,
        "terrain_z": terrain_z,
        "lair_site": lair_site,
        "discovery": discovery,
        "infiltration": infiltration,
        "emitter": emitter,
        "seed": SEED,
        "input_hash": scenario_input_hash(),
    }


def _emitter_posts(center_m: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    return build_sensor_posts(
        center_m,
        ring_radius_m=EMITTER_RING_RADIUS_M,
        count=EMITTER_SENSOR_COUNT,
    )


def _solve_capture(orbits: dict[str, Any]) -> dict[str, Any]:
    chaser = orbits["chaser"]
    target = orbits["target"]
    windows = capture_windows(
        chaser,
        target,
        t_start=0.0,
        t_end=CAPTURE_HORIZON_S,
        dt=CAPTURE_DT_S,
        max_range_km=CAPTURE_MAX_RANGE_KM,
        max_speed_m_s=CAPTURE_MAX_SPEED_M_S,
    )
    first = windows[0] if windows else None
    grapple_dv = (
        velocity_matching_budget(chaser, target, first.start_s) if first else None
    )
    lead = phasing_lead_angle(chaser.radius, target.radius)
    wait = phasing_wait_time(chaser.radius, target.radius, target.initial_phase)
    return {
        "num_windows": len(windows),
        "first_window_start_s": round(first.start_s, 1) if first else None,
        "first_window_duration_s": round(first.duration_s, 1) if first else None,
        "first_window_min_speed_m_s": round(first.min_speed_m_s, 1) if first else None,
        "first_window_min_range_km": round(first.min_range_km, 2) if first else None,
        "grapple_delta_v_m_s": round(grapple_dv, 1) if grapple_dv is not None else None,
        "phasing_lead_deg": round(lead * 180.0 / 3.141592653589793, 2),
        "phasing_wait_s": float("inf") if math.isinf(wait) else round(wait, 1),
    }


def _solve_discovery(discovery: dict[str, Any]) -> dict[str, Any]:
    posterior = discovery["posterior"]
    true_cell = discovery["true_cell"]
    curve = discovery_probability_curve(posterior, max_cells=16)
    p_first_10 = float(curve[min(9, len(curve) - 1)]) if len(curve) else 0.0
    top_cell = rank_search_order(posterior)[0]
    return {
        "true_posterior": round(float(posterior[true_cell]), 6),
        "true_rank": int(expected_discovery_effort(posterior, true_cell)),
        "expected_effort_cells": round(
            expected_discovery_effort(posterior, true_cell), 1
        ),
        "prob_found_first_10": round(p_first_10, 4),
        "top_cell_posterior": round(float(posterior[top_cell]), 6),
        "num_candidate_cells": int(posterior.size),
    }


def _solve_infiltration(
    infiltration: dict[str, Any], volcano: dict[str, Any], thermal_z: Any
) -> dict[str, Any]:
    elevation = volcano["elevation"]
    plan = plan_infiltration(
        elevation,
        thermal_z,
        infiltration["guard_posts"],
        infiltration["start"],
        infiltration["goal"],
        impassable=infiltration["impassable"],
        slope_weight=INFIL_SLOPE_WEIGHT,
        thermal_weight=INFIL_THERMAL_WEIGHT,
        guard_weight=INFIL_GUARD_WEIGHT,
    )
    return {
        "route_cost": round(plan["optimal_cost"], 3),
        "path_length": int(plan["path_length"]),
        "expanded": int(plan["expanded"]),
        "thermal_exposure": round(plan["thermal_exposure"], 4),
        "baseline_cost": round(plan["baseline_cost"], 3),
        "cost_reduction": round(plan["cost_reduction"], 4),
    }


def _solve_emitter(emitter: dict[str, Any]) -> dict[str, Any]:
    sensors = emitter["sensor_posts"]
    true = emitter["emitter_m"]
    deltas = tdoa_measurements(sensors, true)

    estimate = localize_tdoa(
        sensors,
        deltas,
        x0=np.asarray(emitter["initial_guess"], dtype=float),
    )
    error = localization_error(estimate["estimate"], true)
    return {
        "error_m": round(error, 4),
        "iterations": int(estimate["iterations"]),
        "residual_norm": round(estimate["residual_norm"], 6),
        "num_sensors": len(sensors),
    }


def solve_mission(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run all seven capabilities over the scenario and return the results.

    This is the single source of truth shared by the mission adapter and the
    manuscript token generator.
    """
    orbits = scenario["orbits"]
    volcano = scenario["volcano"]
    rendezvous = _solve_rendezvous(orbits)
    capture = _solve_capture(orbits)
    lair = _lair_results(volcano)
    pattern = pattern_summary(scenario["activity"])
    discovery = _solve_discovery(scenario["discovery"])
    infiltration = _solve_infiltration(
        scenario["infiltration"], volcano, scenario["thermal_z"]
    )
    emitter = _solve_emitter(scenario["emitter"])
    return {
        "rendezvous": rendezvous,
        "capture": capture,
        "concealed_lair": lair,
        "pattern_of_life": pattern,
        "hidden_base_discovery": discovery,
        "infiltration": infiltration,
        "emitter_localization": emitter,
    }


def _solve_rendezvous(orbits: dict[str, Any]) -> dict[str, Any]:
    chaser = orbits["chaser"]
    target = orbits["target"]
    windows = find_rendezvous_windows(chaser, target, t_start=0.0, t_end=86400.0)
    transfer = hohmann_transfer(chaser.radius, target.radius)
    first = windows[0] if windows else None
    return {
        "num_windows": len(windows),
        "first_window_start_s": round(first.start_s, 1) if first else None,
        "first_window_duration_s": round(first.duration_s, 1) if first else None,
        "first_window_peak_elevation_deg": round(first.peak_elevation_deg, 2)
        if first
        else None,
        "delta_v_total_m_s": round(transfer["delta_v_total"], 1),
        "transfer_time_s": round(transfer["transfer_time_s"], 1),
    }


def _lair_results(volcano: dict[str, Any]) -> dict[str, Any]:
    regions, meta = detect_concealed_lair(volcano["thermal"], volcano["elevation"])
    top = regions[0] if regions else None
    return {
        "num_candidates": len(regions),
        "top_fused_score": round(top.fused_score, 3) if top else None,
        "top_thermal_score": round(top.thermal_score, 3) if top else None,
        "top_terrain_score": round(top.terrain_score, 3) if top else None,
        "top_area_cells": top.area_cells if top else 0,
        "num_components": meta["num_components"],
    }


def _scenario_descriptor() -> dict[str, Any]:
    """A JSON-serializable, deterministic description of the scenario."""
    return {
        "film": "you_only_live_twice",
        "codename": CODENAME,
        "seed": SEED,
        "orbits": {
            "chaser": {"altitude_km": 550.0, "inclination_deg": 98.2, "raan_deg": 45.0},
            "target": {
                "altitude_km": 800.0,
                "inclination_deg": 98.2,
                "raan_deg": 45.5,
                "phase_rad": 1.9,
            },
        },
        "volcano": {"size": 64, "cone_radius_cells": 20.0, "cone_height_m": 2000.0},
        "activity": {"base_rate_per_hour": 4.0, "hours": 168},
        "capture": {
            "max_range_km": CAPTURE_MAX_RANGE_KM,
            "max_speed_m_s": CAPTURE_MAX_SPEED_M_S,
        },
        "discovery": {
            "mu_hot": DISCOVERY_MU_HOT,
            "beta": DISCOVERY_BETA,
            "rf_power": DISCOVERY_RF_POWER,
        },
        "infiltration": {
            "slope_weight": INFIL_SLOPE_WEIGHT,
            "thermal_weight": INFIL_THERMAL_WEIGHT,
            "guard_weight": INFIL_GUARD_WEIGHT,
            "lava_fraction": INFIL_LAVA_FRACTION,
        },
        "emitter": {
            "ring_radius_m": EMITTER_RING_RADIUS_M,
            "sensor_count": EMITTER_SENSOR_COUNT,
        },
    }


def scenario_input_hash() -> str:
    """Stable sha256 fingerprint of the mission scenario (for provenance)."""
    descriptor = json.dumps(
        _scenario_descriptor(), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(descriptor.encode("utf-8")).hexdigest()
