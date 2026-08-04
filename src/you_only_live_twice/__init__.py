"""VOLCANO — you_only_live_twice special-agent mission software.

Pure domain core for the 1967 film package *You Only Live Twice*. Three
special-agent analytical capabilities, each infrastructure-free and importable
without BOND-API:

* :mod:`~you_only_live_twice.rendezvous_windows` — space-capsule rendezvous /
  intercept window solving (orbital mechanics).
* :mod:`~you_only_live_twice.terrain_anomaly` — concealed-lair detection via
  thermal / terrain anomaly scoring (volcano-camouflage case).
* :mod:`~you_only_live_twice.pattern_of_life` — base pattern-of-life analysis.

:mod:`~you_only_live_twice.mission` is the thin adapter that exposes this core
to the BOND-API ``MissionProvider`` protocol (codename VOLCANO).
"""

from __future__ import annotations

__all__ = [
    "mission",
    "pattern_of_life",
    "rendezvous_windows",
    "scenario",
    "terrain_anomaly",
]

__version__ = "0.1.0"
