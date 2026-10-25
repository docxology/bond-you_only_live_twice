"""VOLCANO — the BOND-API ``MissionProvider`` for You Only Live Twice.

This is the thin adapter between the film's pure domain core and the frozen
BOND-API mission protocol. It exposes a :class:`MissionProvider` at module top
level under the name the discovery contract expects, and it registers the
film's analytical *gadgets* with the :class:`bond_api.registry.GadgetRegistry`.

The domain modules stay infrastructure-free and importable without BOND-API;
only this module (and the protocol-identity lookup in
:mod:`you_only_live_twice.manuscript_variables`) imports the protocol. All
actual computation lives in
:func:`you_only_live_twice.scenario.solve_mission`, the single source shared by
this adapter and the manuscript token generator.
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

from you_only_live_twice.emitter_localization import localize_tdoa
from you_only_live_twice.hidden_base_discovery import (
    expected_discovery_effort,
    rank_search_order,
)
from you_only_live_twice.infiltration_planning import plan_infiltration
from you_only_live_twice.orbital_capture import capture_windows
from you_only_live_twice.pattern_of_life import pattern_summary
from you_only_live_twice.rendezvous_windows import (
    find_rendezvous_windows,
    hohmann_transfer,
)
from you_only_live_twice.scenario import (
    CODENAME,
    PACKAGE_VERSION,
    SEED,
    build_scenario,
    solve_mission,
)
from you_only_live_twice.terrain_anomaly import detect_concealed_lair

__all__ = ["MissionProvider", "__version__", "register_gadgets"]

__version__ = PACKAGE_VERSION


class MissionProvider:
    """Deterministic BOND-API mission provider for codename VOLCANO.

    Executes seven special-agent capabilities — orbital rendezvous windows,
    orbital capture & phasing, concealed-lair detection, hidden-base discovery,
    infiltration planning, emitter localisation, and pattern-of-life analysis —
    over a fixed, reproducible scenario.
    """

    film = "you_only_live_twice"

    def brief(self) -> MissionBrief:
        """Declare the VOLCANO mission: the special-agent objectives."""
        return MissionBrief(
            film=self.film,
            codename=CODENAME,
            objectives=(
                "solve space-capsule rendezvous and intercept windows",
                "engineer the orbital capture and phasing of the enemy capsule",
                "detect the concealed volcano-camouflaged lair",
                "localize the hidden base by Bayesian cue fusion and RF emission",
                "plan the infiltration route into the lair",
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
                Asset(
                    kind="signals",
                    name="tdoa_sensors",
                    payload={"sensor_count": 5},
                ),
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
        """Survey the request, the mission assets, and the constraints."""
        return ReconReport(
            findings=(
                Finding(label="goal", detail=request.goal),
                Finding(
                    label="orbital",
                    detail="chaser and target circular orbits are known; phasing solvable",
                ),
                Finding(
                    label="imagery",
                    detail="thermal + terrain volcano scene is available",
                ),
                Finding(
                    label="signals",
                    detail="passive TDOA sensors bracket the suspected base field",
                ),
                Finding(
                    label="schedule",
                    detail="one week of base activity events is available",
                ),
                Finding(label="constraint", detail="deterministic execution required"),
            )
        )

    def plan(self, brief: MissionBrief) -> MissionPlan:
        """Plan the analytical steps: rendezvous, capture, lair, discovery, infiltration, emitter, pattern."""
        return MissionPlan(
            steps=(
                Step(
                    name="rendezvous",
                    action="solve_windows",
                    params={"objective": brief.objectives[0]},
                ),
                Step(
                    name="capture",
                    action="solve_capture",
                    params={"objective": brief.objectives[1]},
                ),
                Step(
                    name="lair",
                    action="detect_concealed_lair",
                    params={"objective": brief.objectives[2]},
                ),
                Step(
                    name="discovery",
                    action="fuse_cues",
                    params={"objective": brief.objectives[3]},
                ),
                Step(
                    name="infiltration",
                    action="plan_route",
                    params={"objective": brief.objectives[4]},
                ),
                Step(
                    name="emitter",
                    action="localize_emitter",
                    params={"source": brief.assets[3].name},
                ),
                Step(
                    name="pattern",
                    action="pattern_summary",
                    params={"objective": brief.objectives[5]},
                ),
            )
        )

    def execute(self, plan: MissionPlan) -> MissionOutcome:
        """Run all capabilities over the fixed scenario and report metrics."""
        scenario = build_scenario()
        analysis = solve_mission(scenario)
        results: dict[str, Any] = {
            "steps_completed": len(plan.steps),
            **analysis,
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
                "orbital capture is a phasing problem: wait for the right lead angle, then match velocity",
                (
                    "whether cue fusion was *necessary* is an empirical question: "
                    "score each cue alone before claiming the base was found by "
                    "fusing weak sensors (this run's single-cue ranks are in the "
                    "evidence notes)"
                ),
                "a base's pattern of life is best read as a weekly, diurnal rhythm",
                "deterministic provenance makes every outcome independently auditable",
                *tuple(notes),
            ),
        )


def _evidence_notes(results: dict[str, Any]) -> tuple[str, ...]:
    """Human-readable evidence lines derived from the computed results."""
    notes: list[str] = []
    rendezvous = results.get("rendezvous", {})
    if rendezvous.get("num_windows"):
        notes.append(
            f"{rendezvous['num_windows']} rendezvous window(s), "
            f"closest within {rendezvous['first_window_start_s']} s"
        )
    capture = results.get("capture", {})
    if capture.get("num_windows"):
        notes.append(
            f"{capture['num_windows']} orbital capture window(s), "
            f"grapple delta-v {capture['grapple_delta_v_m_s']} m/s"
        )
    lair = results.get("concealed_lair", {})
    if lair.get("top_fused_score"):
        notes.append(
            f"top lair candidate fused score {lair['top_fused_score']}; the "
            f"detector's peak sits {lair.get('detector_offset_m')} m from the "
            f"injected facility centre"
        )
    discovery = results.get("hidden_base_discovery", {})
    if discovery.get("footprint_rank"):
        notes.append(
            f"greedy posterior search reaches the injected {discovery['footprint_cells']}"
            f"-cell lair footprint at rank {discovery['footprint_rank']} of "
            f"{discovery['num_candidate_cells']} candidate sites; the injected centre "
            f"cell itself ranks {discovery['centroid_rank']}"
        )
    single = discovery.get("single_cue_footprint_ranks") or {}
    if single:
        best = ", ".join(f"{name} {rank}" for name, rank in sorted(single.items()))
        sufficient = [name for name, rank in single.items() if rank == 1]
        notes.append(
            f"single-cue footprint ranks ({best}) — "
            + (
                f"{len(sufficient)} cue(s) already rank the footprint first alone, "
                "so fusion was not what found the base"
                if sufficient
                else "no single cue finds the footprint first; fusion was necessary"
            )
        )
    infiltration = results.get("infiltration", {})
    if infiltration.get("cost_reduction"):
        notes.append(
            f"infiltration route cuts cost by {infiltration['cost_reduction'] * 100:.1f}%"
        )
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
        "capture_solver": capture_windows,
        "lair_detector": detect_concealed_lair,
        "discovery_engine": expected_discovery_effort,
        "search_ranker": rank_search_order,
        "route_planner": plan_infiltration,
        "emitter_locator": localize_tdoa,
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
