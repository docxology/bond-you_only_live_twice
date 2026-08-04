"""Deterministic mission scenario for VOLCANO.

This single source of truth defines the fixed scenario the mission executes:
the chaser and target orbits, the volcano-camouflage terrain/thermal scene, and
the base activity schedule. Keeping it here (rather than inline in
``mission.py``) makes the adapter thin and lets recon / figures / tests all
consume the same inputs.

All quantities are fixed or produced by fixed-seed generators, so the scenario
is byte-for-byte reproducible. The scenario also defines the stable
``input_hash`` a mission outcome carries as provenance.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from you_only_live_twice.pattern_of_life import (
    BaseActivity,
    build_weekly_activity_schedule,
)
from you_only_live_twice.rendezvous_windows import CircularOrbit
from you_only_live_twice.terrain_anomaly import build_volcano_scene

__all__ = [
    "CODENAME",
    "PACKAGE_VERSION",
    "SEED",
    "build_scenario",
    "scenario_input_hash",
]

#: Mission identity / version for the VOLCANO (1967) film package.
CODENAME = "VOLCANO"
PACKAGE_VERSION = "0.1.0"
#: Deterministic seed — the film's release year.
SEED = 1967


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
    """Assemble the full deterministic VOLCANO scenario.

    Returns a dict with ``orbits``, ``volcano`` (the terrain/thermal scene),
    ``activity`` (the base activity schedule), ``seed`` and the computed
    ``input_hash``.
    """
    volcano = build_volcano_scene(seed=SEED)
    activity: tuple[BaseActivity, ...] = build_weekly_activity_schedule(seed=SEED)
    return {
        "orbits": _orbits(),
        "volcano": volcano,
        "activity": activity,
        "seed": SEED,
        "input_hash": scenario_input_hash(),
    }


def _scenario_descriptor() -> dict[str, Any]:
    """A JSON-serializable, deterministic description of the scenario."""
    return {
        "film": "you_only_live_twice",
        "codename": CODENAME,
        "seed": SEED,
        "chaser": {"altitude_km": 550.0, "inclination_deg": 98.2, "raan_deg": 45.0},
        "target": {
            "altitude_km": 800.0,
            "inclination_deg": 98.2,
            "raan_deg": 45.5,
            "phase_rad": 1.9,
        },
        "volcano": {"size": 64, "cone_radius_cells": 20.0, "cone_height_m": 2000.0},
        "activity": {"base_rate_per_hour": 4.0, "hours": 168},
    }


def scenario_input_hash() -> str:
    """Stable sha256 fingerprint of the mission scenario (for provenance)."""
    descriptor = json.dumps(
        _scenario_descriptor(), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(descriptor.encode("utf-8")).hexdigest()
