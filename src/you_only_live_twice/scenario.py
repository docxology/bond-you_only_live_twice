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
    SPEED_OF_LIGHT,
    build_sensor_posts,
    localization_error,
    localize_tdoa,
    tdoa_error_sweep,
    tdoa_measurements,
    time_differences_to_ranges,
)
from you_only_live_twice.hidden_base_discovery import (
    build_discovery_scene,
    discovery_probability_curve,
    expected_discovery_effort,
    fuse_posteriors,
    posterior_expected_effort,
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
    fuse_anomaly_scores,
    terrain_anomaly_mask,
    thermal_anomaly_mask,
)

__all__ = [
    "CODENAME",
    "M_PER_CELL",
    "PACKAGE_VERSION",
    "SEED",
    "build_scenario",
    "scenario_descriptor",
    "scenario_input_hash",
    "solve_mission",
]

#: Mission identity / version for the VOLCANO (1967) film package.
CODENAME = "VOLCANO"
PACKAGE_VERSION = "0.1.0"
#: Deterministic seed — the film's release year.
SEED = 1967

#: Orbital geometry: chaser (capture platform) and target (adversary capsule).
CHASER_ALTITUDE_KM = 550.0
CHASER_INCLINATION_DEG = 98.2
CHASER_RAAN_DEG = 45.0
CHASER_PHASE_RAD = 0.0
TARGET_ALTITUDE_KM = 800.0
TARGET_INCLINATION_DEG = 98.2
TARGET_RAAN_DEG = 45.5
TARGET_PHASE_RAD = 1.9

#: Rendezvous (line-of-sight) window search envelope.
RENDEZVOUS_HORIZON_S = 86400.0
RENDEZVOUS_DT_S = 60.0
RENDEZVOUS_MAX_RANGE_KM = 500.0
RENDEZVOUS_MIN_ELEVATION_DEG = 10.0

#: Volcano-camouflage scene geometry.
VOLCANO_SIZE_CELLS = 64
VOLCANO_CONE_RADIUS_CELLS = 20.0
VOLCANO_CONE_HEIGHT_M = 2_000.0
VOLCANO_LAIR_HEAT_K = 25.0

#: Base activity schedule.
ACTIVITY_RATE_PER_HOUR = 4.0
ACTIVITY_DAYS = 7

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
#: Receiver timing jitter, seconds (10 ns, 1-sigma), applied to the arrival-time
#: differences *before* they are converted to ranges and solved. Without it the
#: reported localisation error is a round-trip identity of the forward model and
#: is 0.0 by construction; with it, the error is a measurement that can come out
#: worse.
EMITTER_TIME_NOISE_S = 1.0e-8

#: TDOA accuracy-envelope sweep: receiver timing-jitter levels (s, 1-sigma)
#: and the number of fixed-seed realizations averaged per level.
EMITTER_SWEEP_NOISE_LEVELS_S = (0.0, 1.0e-8, 2.0e-8, 5.0e-8, 1.0e-7, 2.0e-7)
EMITTER_SWEEP_REALIZATIONS = 24


def _orbits() -> dict[str, Any]:
    """The chase and target orbital elements (circular, near-polar recon)."""
    return {
        # Chaser: a rocket on a sun-synchronous-like inclination.
        "chaser": CircularOrbit.from_altitude(
            altitude_km=CHASER_ALTITUDE_KM,
            inclination=math.radians(CHASER_INCLINATION_DEG),
            raan=math.radians(CHASER_RAAN_DEG),
            initial_phase=CHASER_PHASE_RAD,
        ),
        # Target: the adversary space capsule a bit higher, offset in plane.
        "target": CircularOrbit.from_altitude(
            altitude_km=TARGET_ALTITUDE_KM,
            inclination=math.radians(TARGET_INCLINATION_DEG),
            raan=math.radians(TARGET_RAAN_DEG),
            initial_phase=TARGET_PHASE_RAD,
        ),
    }


def build_scenario() -> dict[str, Any]:
    """Assemble the full deterministic VOLCANO scenario (all mission inputs).

    Returns a dict carrying ``orbits``, ``volcano``, ``activity``, the anomaly
    Z-maps ``thermal_z``/``terrain_z``, the discovery scene, the infiltration
    geometry, the emitter posts, ``seed`` and the computed ``input_hash``.

    Ground truth vs. estimate. ``lair_site`` and ``lair_footprint`` are the
    facility's *injected* centre and carved extent, fixed by
    :func:`build_volcano_scene`'s geometry (cone centre plus
    ``lair_offset_cells``) before any sensor map is computed. Every downstream
    truth — the discovery scene's ``true_cell``, the RF emitter, the
    infiltration goal, the TDOA emitter — is that injected site.
    ``detected_site`` is separate: it is the anomaly detector's *estimate*, the
    argmax of the fused Z-maps. The two are not the same cell, and the gap
    between them is reported rather than defined away.
    """
    orbits = _orbits()
    volcano = build_volcano_scene(
        size=VOLCANO_SIZE_CELLS,
        cone_radius_cells=VOLCANO_CONE_RADIUS_CELLS,
        cone_height_m=VOLCANO_CONE_HEIGHT_M,
        lair_heat_kelvin=VOLCANO_LAIR_HEAT_K,
        seed=SEED,
    )
    activity: tuple[BaseActivity, ...] = build_weekly_activity_schedule(
        base_rate_per_hour=ACTIVITY_RATE_PER_HOUR,
        seed=SEED,
        num_days=ACTIVITY_DAYS,
    )

    _ignore_th, thermal_z = thermal_anomaly_mask(volcano["thermal"])
    _ignore_te, terrain_z = terrain_anomaly_mask(volcano["elevation"])

    # Ground truth: the injected lair centre, fixed by the scene geometry and
    # independent of every sensor map computed from that scene.
    lair_site = (int(volcano["lair_center"][0]), int(volcano["lair_center"][1]))
    lair_footprint: frozenset[tuple[int, int]] = volcano["lair_footprint"]

    # Estimate: the anomaly detector's own answer — the argmax of the fused
    # Z-maps. Deliberately *not* used as the ground truth; the offset between
    # the two is a reported result (``detector_offset_m``).
    fused_peak = fuse_anomaly_scores(thermal_z, terrain_z)
    size_grid = int(volcano["parameters"]["size"])
    _flat_idx = int(np.argmax(fused_peak))
    detected_site = (_flat_idx // size_grid, _flat_idx % size_grid)

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
        "imagery_site_m": (
            float(detected_site[0]) * M_PER_CELL,
            float(detected_site[1]) * M_PER_CELL,
        ),
        "time_noise_s": EMITTER_TIME_NOISE_S,
    }

    return {
        "orbits": orbits,
        "volcano": volcano,
        "activity": activity,
        "thermal_z": thermal_z,
        "terrain_z": terrain_z,
        "lair_site": lair_site,
        "lair_footprint": lair_footprint,
        "detected_site": detected_site,
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


def _footprint_rank(
    posterior: Any, footprint: frozenset[tuple[int, int]]
) -> tuple[int, tuple[int, int]]:
    """Rank at which a greedy posterior-order search first enters ``footprint``.

    The facility occupies many cells, so "did the search find the base" is a
    question about the footprint, not about one nominated centroid cell.
    """
    for rank, cell in enumerate(rank_search_order(posterior), start=1):
        if cell in footprint:
            return rank, cell
    # ``rank_search_order`` enumerates every grid cell and the scene generator
    # guarantees the injected footprint is a non-empty subset of that grid, so
    # a member of the footprint is always reached. This is a defensive
    # invariant against callers that hand an out-of-grid footprint, not a
    # hidden fallback — it is pinned by a negative-control test below.
    raise AssertionError("the injected footprint is disjoint from the search grid")


def _single_cue_footprint_ranks(
    discovery: dict[str, Any], footprint: frozenset[tuple[int, int]]
) -> dict[str, int]:
    """Footprint rank each cue reaches *on its own* (prior x that one cue).

    This is the number that decides whether fusion was actually necessary. If
    every single-cue rank is already 1, the cues are individually decisive and
    fusion sharpens the posterior rather than enabling the find.
    """
    priors = discovery["priors"]
    out: dict[str, int] = {}
    for name in ("thermal", "terrain", "rf"):
        single = fuse_posteriors(priors, discovery[f"lr_{name}"])
        out[name], _cell = _footprint_rank(single, footprint)
    out["prior_only"], _cell = _footprint_rank(priors / float(priors.sum()), footprint)
    return out


def _solve_discovery(
    discovery: dict[str, Any],
    footprint: frozenset[tuple[int, int]],
) -> dict[str, Any]:
    posterior = discovery["posterior"]
    true_cell = discovery["true_cell"]
    curve = discovery_probability_curve(posterior, max_cells=16)
    p_first_10 = float(curve[min(9, len(curve) - 1)]) if len(curve) else 0.0
    top_cell = rank_search_order(posterior)[0]
    footprint_rank, _first_hit = _footprint_rank(posterior, footprint)
    footprint_mass = float(sum(float(posterior[cell]) for cell in footprint))
    peak_offset_cells = math.dist(top_cell, true_cell)
    return {
        # Ground-truth-referenced measurements. ``footprint_*`` ask whether the
        # search found the *facility*; ``centroid_*`` ask the stricter question
        # of whether it landed on the injected centre cell. Both can fail.
        "footprint_rank": footprint_rank,
        "footprint_posterior": round(footprint_mass, 6),
        "footprint_cells": len(footprint),
        "top_cell_in_footprint": bool(top_cell in footprint),
        "centroid_rank": int(expected_discovery_effort(posterior, true_cell)),
        "centroid_posterior": float(f"{float(posterior[true_cell]):.3g}"),
        "peak_offset_cells": round(peak_offset_cells, 2),
        "peak_offset_m": round(peak_offset_cells * M_PER_CELL, 1),
        "single_cue_footprint_ranks": _single_cue_footprint_ranks(discovery, footprint),
        # Posterior-only statistics (no ground truth involved).
        "expected_effort_cells": round(posterior_expected_effort(posterior), 2),
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
    """Localize the emitter from *noisy* receiver timings.

    The receivers report arrival-time differences with a fixed-seed jitter of
    ``time_noise_s`` before anything is converted to metres, so the reported
    ``error_m`` is an achieved accuracy that could have come out worse — not the
    0.0 that a noise-free forward-model round trip returns by construction.
    """
    sensors = emitter["sensor_posts"]
    true = emitter["emitter_m"]
    range_deltas = tdoa_measurements(sensors, true)
    rng = np.random.default_rng(SEED)
    time_deltas = range_deltas / SPEED_OF_LIGHT + rng.normal(
        0.0, float(emitter["time_noise_s"]), range_deltas.shape
    )
    measured = time_differences_to_ranges(time_deltas)

    estimate = localize_tdoa(
        sensors,
        measured,
        x0=np.asarray(emitter["initial_guess"], dtype=float),
    )
    error = localization_error(estimate["estimate"], true)
    imagery = emitter["imagery_site_m"]
    sweep = tdoa_error_sweep(
        sensors,
        true,
        EMITTER_SWEEP_NOISE_LEVELS_S,
        np.asarray(emitter["initial_guess"], dtype=float),
        realizations=EMITTER_SWEEP_REALIZATIONS,
        base_seed=SEED,
    )
    return {
        "error_m": round(error, 4),
        "iterations": int(estimate["iterations"]),
        "residual_norm": round(estimate["residual_norm"], 6),
        "num_sensors": len(sensors),
        "time_noise_s": float(emitter["time_noise_s"]),
        # Cross-modal comparison against the *imagery* estimate. The radio and
        # imagery chains share no measurement, so this separation is a real
        # disagreement between two modalities, not a round-trip identity.
        "imagery_site_offset_m": round(
            localization_error(estimate["estimate"], imagery), 1
        ),
        "truth_to_imagery_offset_m": round(math.dist(true, imagery), 1),
        "sweep": sweep,
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
    lair = _lair_results(
        volcano,
        scenario["detected_site"],
        scenario["lair_site"],
        scenario["lair_footprint"],
    )
    pattern = pattern_summary(scenario["activity"])
    discovery = _solve_discovery(scenario["discovery"], scenario["lair_footprint"])
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
    windows = find_rendezvous_windows(
        chaser,
        target,
        t_start=0.0,
        t_end=RENDEZVOUS_HORIZON_S,
        dt=RENDEZVOUS_DT_S,
        max_range_km=RENDEZVOUS_MAX_RANGE_KM,
        min_elevation_deg=RENDEZVOUS_MIN_ELEVATION_DEG,
    )
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


def _lair_results(
    volcano: dict[str, Any],
    detected_site: tuple[int, int],
    true_site: tuple[int, int],
    footprint: frozenset[tuple[int, int]],
) -> dict[str, Any]:
    regions, meta = detect_concealed_lair(volcano["thermal"], volcano["elevation"])
    top = regions[0] if regions else None
    offset_cells = math.dist(detected_site, true_site)
    return {
        "num_candidates": len(regions),
        "top_fused_score": round(top.fused_score, 3) if top else None,
        "top_thermal_score": round(top.thermal_score, 3) if top else None,
        "top_terrain_score": round(top.terrain_score, 3) if top else None,
        "top_area_cells": top.area_cells if top else 0,
        "num_components": meta["num_components"],
        # Detector accuracy against the injected facility, measured rather than
        # asserted: the detector's peak is not the injected centre cell.
        "detected_cell": list(detected_site),
        "detected_in_footprint": bool(detected_site in footprint),
        "detector_offset_cells": round(offset_cells, 2),
        "detector_offset_m": round(offset_cells * M_PER_CELL, 1),
        "footprint_cells": len(footprint),
    }


def _scenario_descriptor() -> dict[str, Any]:
    """A JSON-serializable, deterministic description of the scenario."""
    return {
        "film": "you_only_live_twice",
        "codename": CODENAME,
        "seed": SEED,
        "orbits": {
            "chaser": {
                "altitude_km": CHASER_ALTITUDE_KM,
                "inclination_deg": CHASER_INCLINATION_DEG,
                "raan_deg": CHASER_RAAN_DEG,
                "phase_rad": CHASER_PHASE_RAD,
            },
            "target": {
                "altitude_km": TARGET_ALTITUDE_KM,
                "inclination_deg": TARGET_INCLINATION_DEG,
                "raan_deg": TARGET_RAAN_DEG,
                "phase_rad": TARGET_PHASE_RAD,
            },
        },
        "rendezvous": {
            "horizon_s": RENDEZVOUS_HORIZON_S,
            "dt_s": RENDEZVOUS_DT_S,
            "max_range_km": RENDEZVOUS_MAX_RANGE_KM,
            "min_elevation_deg": RENDEZVOUS_MIN_ELEVATION_DEG,
        },
        "volcano": {
            "size": VOLCANO_SIZE_CELLS,
            "cone_radius_cells": VOLCANO_CONE_RADIUS_CELLS,
            "cone_height_m": VOLCANO_CONE_HEIGHT_M,
            "lair_heat_kelvin": VOLCANO_LAIR_HEAT_K,
        },
        "activity": {
            "base_rate_per_hour": ACTIVITY_RATE_PER_HOUR,
            "hours": ACTIVITY_DAYS * 24,
        },
        "capture": {
            "max_range_km": CAPTURE_MAX_RANGE_KM,
            "max_speed_m_s": CAPTURE_MAX_SPEED_M_S,
            "dt_s": CAPTURE_DT_S,
            "horizon_s": CAPTURE_HORIZON_S,
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
            "time_noise_s": EMITTER_TIME_NOISE_S,
            "sweep_noise_levels_s": list(EMITTER_SWEEP_NOISE_LEVELS_S),
            "sweep_realizations": EMITTER_SWEEP_REALIZATIONS,
        },
    }


def scenario_descriptor() -> dict[str, Any]:
    """The public, JSON-serializable description of every scenario input.

    This is the object the provenance hash is taken over *and* the source the
    manuscript's experimental-setup tokens are hydrated from, so the reported
    parameters can never drift from the parameters actually simulated.
    """
    return _scenario_descriptor()


def scenario_input_hash() -> str:
    """Stable sha256 fingerprint of the mission scenario (for provenance)."""
    descriptor = json.dumps(
        _scenario_descriptor(), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(descriptor.encode("utf-8")).hexdigest()
