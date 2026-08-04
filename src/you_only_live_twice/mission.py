"""VOLCANO — the BOND-API ``MissionProvider`` for You Only Live Twice.

This is the thin adapter between the film's pure domain core
(:mod:`you_only_live_twice.rendezvous_windows`, ``terrain_anomaly``,
``pattern_of_life``) and the frozen BOND-API mission protocol. It exposes a
:class:`MissionProvider` at module top level under the name the discovery
contract expects, and it registers the film's analytical *gadgets* with the
:class:`bond_api.registry.GadgetRegistry`.

The domain modules stay infrastructure-free and importable without BOND-API;
only this module (and the derivations in :mod:`you_only_live_twice.figures`)
depend on the protocol.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bond_api.protocol import (
    Asset,
    Constraint,
    Debrief,
    Finding,
    MissionBrief,
    MissionOutcome,
    MissionPlan,
    Provenance,
    ReconReport,
    ReconRequest,
    Step,
)
from bond_api.registry import GadgetRegistry

from you_only_live_twice.pattern_of_life import (
    BaseActivity,
    pattern_summary,
)
from you_only_live_twice.rendezvous_windows import (
    CircularOrbit,
    find_rendezvous_windows,
    hohmann_transfer,
)
from you_only_live_twice.scenario import (
    CODENAME,
    PACKAGE_VERSION,
    SEED,
    build_scenario,
)
from you_only_live_twice.terrain_anomaly import detect_concealed_lair

__all__ = ["MissionProvider", "__version__", "register_gadgets"]

__version__ = PACKAGE_VERSION


class MissionProvider:
    """Deterministic BOND-API mission provider for codename VOLCANO.

    Executes the three special-agent capabilities — orbital rendezvous
    windows, concealed-lair detection, and pattern-of-life analysis — over a
    fixed, reproducible scenario.
    """

    film = "you_only_live_twice"

    def brief(self) -> MissionBrief:
        """Declare the VOLCANO mission: three special-agent objectives."""
        return MissionBrief(
            film=self.film,
            codename=CODENAME,
            objectives=(
                "solve space-capsule rendezvous and intercept windows",
                "detect the concealed volcano-camouflaged lair",
                "characterize the adversary base pattern of life",
            ),
            assets=(
                Asset(
                    kind="orbital",
                    name="rendezvous_geometry",
                    payload={"altitudes_km": (550.0, 800.0)},
                ),
                Asset(kind="imagery", name="volcano_scene", payload={"size": 64}),
                Asset(kind="schedule", name="activity_events", payload={"hours": 168}),
            ),
            constraints=(
                Constraint(
                    kind="determinism",
                    detail="no random draws, no external calls, fixed seed",
                ),
                Constraint(
                    kind="lineage", detail="no exemplar lineage; VOLCANO-only package"
                ),
            ),
        )

    def recon(self, request: ReconRequest) -> ReconReport:
        """Survey the request, the three assets, and the determinism constraint."""
        return ReconReport(
            findings=(
                Finding(label="goal", detail=request.goal),
                Finding(
                    label="orbital",
                    detail="chaser and target circular orbits are known",
                ),
                Finding(
                    label="imagery",
                    detail="thermal + terrain volcano scene is available",
                ),
                Finding(
                    label="schedule",
                    detail="one week of base activity events is available",
                ),
                Finding(label="constraint", detail="deterministic execution required"),
            )
        )

    def plan(self, brief: MissionBrief) -> MissionPlan:
        """Plan the three analytical steps: rendezvous, lair, pattern-of-life."""
        return MissionPlan(
            steps=(
                Step(
                    name="rendezvous",
                    action="solve_windows",
                    params={"objectives": len(brief.objectives)},
                ),
                Step(
                    name="lair",
                    action="detect_concealed_lair",
                    params={"source": brief.assets[1].name},
                ),
                Step(
                    name="pattern",
                    action="pattern_summary",
                    params={"source": brief.assets[2].name},
                ),
            )
        )

    def execute(self, plan: MissionPlan) -> MissionOutcome:
        """Run all three capabilities over the fixed scenario and report metrics."""
        scenario = build_scenario()
        orbits: dict[str, CircularOrbit] = scenario["orbits"]
        volcano = scenario["volcano"]
        activity: tuple[BaseActivity, ...] = scenario["activity"]

        rendezvous_results = _solve_rendezvous(orbits["chaser"], orbits["target"])
        lair_results = _detect_lair(volcano["thermal"], volcano["elevation"])
        pattern_results = pattern_summary(activity)

        results: dict[str, Any] = {
            "steps_completed": len(plan.steps),
            "rendezvous": rendezvous_results,
            "concealed_lair": lair_results,
            "pattern_of_life": pattern_results,
            "seed": SEED,
        }
        return MissionOutcome(
            success=True,
            results=results,
            provenance=Provenance(
                package_version=PACKAGE_VERSION,
                seed=SEED,
                input_hash=scenario["input_hash"],
                wall_time_s=0.0,
            ),
        )

    def debrief(self, outcome: MissionOutcome) -> Debrief:
        """Summarize the mission and record VOLCANO's standing lessons."""
        notes = _evidence_notes(outcome.results)
        return Debrief(
            outcome=outcome,
            lessons=(
                "a concealed lair leaks heat and flattens terrain, even when camouflaged",
                "rendezvous windows are driven by relative orbital phase, not absolute motion",
                "a base's pattern of life is best read as a weekly, diurnal rhythm",
                "deterministic provenance makes every outcome independently auditable",
                *tuple(notes),
            ),
        )


def _solve_rendezvous(chaser: CircularOrbit, target: CircularOrbit) -> dict[str, Any]:
    """Compute rendezvous windows and an intercept delta-v budget."""
    windows = find_rendezvous_windows(chaser, target, t_start=0.0, t_end=86400.0)
    transfer = hohmann_transfer(chaser.radius, target.radius)
    first = windows[0] if windows else None

    def ev(e: CircularOrbit) -> float:
        return e.initial_phase

    return {
        "num_windows": len(windows),
        "first_window_start_s": round(first.start_s, 1) if first else None,
        "first_window_duration_s": round(first.duration_s, 1) if first else None,
        "first_window_peak_elevation_deg": round(first.peak_elevation_deg, 2)
        if first
        else None,
        "chaser_phase_rad": round(ev(chaser), 4),
        "target_phase_rad": round(ev(target), 4),
        "delta_v_total_m_s": round(transfer["delta_v_total"], 1),
        "transfer_time_s": round(transfer["transfer_time_s"], 1),
    }


def _detect_lair(thermal: Any, elevation: Any) -> dict[str, Any]:
    """Detect concealed-lair candidate regions and summarize the top hit."""
    regions, meta = detect_concealed_lair(thermal, elevation)
    top = regions[0] if regions else None
    return {
        "num_candidates": len(regions),
        "top_fused_score": round(top.fused_score, 3) if top else None,
        "top_thermal_score": round(top.thermal_score, 3) if top else None,
        "top_terrain_score": round(top.terrain_score, 3) if top else None,
        "top_area_cells": top.area_cells if top else 0,
        "num_components": meta["num_components"],
    }


def _evidence_notes(results: dict[str, Any]) -> tuple[str, ...]:
    """Human-readable evidence lines derived from the computed results."""
    notes: list[str] = []
    rendezvous = results.get("rendezvous", {})
    if rendezvous.get("num_windows"):
        notes.append(
            f"{rendezvous['num_windows']} rendezvous window(s), "
            f"closest within {rendezvous['first_window_start_s']} s"
        )
    lair = results.get("concealed_lair", {})
    if lair.get("top_fused_score"):
        notes.append(f"top lair candidate fused score {lair['top_fused_score']}")
    pattern = results.get("pattern_of_life", {})
    tempo = pattern.get("tempo")
    if tempo:
        notes.append(f"base operational tempo classified {tempo}")
    return tuple(notes)


def register_gadgets(registry: GadgetRegistry) -> GadgetRegistry:
    """Register this film's analytical gadgets with a ``GadgetRegistry``.

    Each gadget maps a capability name to the underlying pure-domain callable,
    allowing the orchestrator to invoke a single analytical service by name.
    """
    gadgets: dict[str, Callable[..., Any]] = {
        "rendezvous_solver": find_rendezvous_windows,
        "intercept_budget": hohmann_transfer,
        "lair_detector": detect_concealed_lair,
        "pattern_analyzer": pattern_summary,
    }
    registry.register(self_film(), gadgets)
    return registry


def self_film() -> str:
    """Return the film slug used when registering gadgets."""
    return MissionProvider.film


#: Convenience registry carrying this film's gadgets (used by scripts/tests).
FALLBACK_GADGETS = GadgetRegistry()
register_gadgets(FALLBACK_GADGETS)
