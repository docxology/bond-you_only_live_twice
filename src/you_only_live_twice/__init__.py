"""VOLCANO — you_only_live_twice special-agent mission software.

Pure domain core for the 1967 film package *You Only Live Twice*. Seven
special-agent analytical capabilities, each infrastructure-free and importable
without BOND-API:

* :mod:`~you_only_live_twice.rendezvous_windows` — space-capsule rendezvous /
  intercept window solving (circular two-body orbital mechanics).
* :mod:`~you_only_live_twice.orbital_capture` — capture envelope, the
  velocity-matching grapple burn, and the phasing lead angle / wait time.
* :mod:`~you_only_live_twice.terrain_anomaly` — concealed-lair detection via
  thermal / terrain anomaly scoring (volcano-camouflage case).
* :mod:`~you_only_live_twice.hidden_base_discovery` — Bayesian fusion of
  thermal / terrain / RF cues into a posterior map and a search plan.
* :mod:`~you_only_live_twice.infiltration_planning` — slope / thermal / guard
  cost fields and a deterministic A* route against a greedy baseline.
* :mod:`~you_only_live_twice.emitter_localization` — TDOA hyperbolic
  multilateration of the base transmitter by Gauss–Newton.
* :mod:`~you_only_live_twice.pattern_of_life` — base pattern-of-life analysis.

:mod:`~you_only_live_twice.scenario` binds all seven into one deterministic
mission (``build_scenario`` / ``solve_mission``), and
:mod:`~you_only_live_twice.mission` is the thin adapter that exposes that
single analysis source to the BOND-API ``MissionProvider`` protocol (codename
VOLCANO).
"""

from __future__ import annotations

__all__ = [
    "emitter_localization",
    "hidden_base_discovery",
    "infiltration_planning",
    "mission",
    "orbital_capture",
    "pattern_of_life",
    "rendezvous_windows",
    "scenario",
    "terrain_anomaly",
]

__version__ = "0.1.0"
