"""Tests for the VOLCANO BOND-API MissionProvider and gadget registry.

Drives the real provider through the frozen protocol (no mocks) and checks that
it satisfies the runtime-checkable contract, produces deterministic outcomes
with full provenance, and registers its analytical gadgets.
"""

from __future__ import annotations

from bond_api.protocol import (
    MissionProvider as ProtocolProvider,
)
from bond_api.protocol import (
    ReconRequest,
    run_mission,
)
from bond_api.registry import GadgetRegistry, MissionRegistry

from you_only_live_twice.mission import (
    FALLBACK_GADGETS,
    MissionProvider,
    _evidence_notes,
    register_gadgets,
    self_film,
)


def test_provider_satisfies_protocol() -> None:
    assert isinstance(MissionProvider(), ProtocolProvider)


def test_provider_film_and_identity() -> None:
    provider = MissionProvider()
    assert provider.film == "you_only_live_twice"
    brief = provider.brief()
    assert brief.codename == "VOLCANO"
    assert len(brief.objectives) == 6
    assert brief.assets
    assert brief.constraints


def test_full_mission_flow_is_deterministic() -> None:
    request = ReconRequest(goal="locate the concealed lair and time the intercept")
    debrief_a = run_mission(MissionProvider(), request)
    debrief_b = run_mission(MissionProvider(), request)

    outcome = debrief_a.outcome
    assert outcome.success is True
    assert outcome.provenance.seed == 1967
    assert len(outcome.provenance.input_hash) == 64

    # Determinism: identical provenance and matching scalar sub-results.
    assert outcome.provenance == debrief_b.outcome.provenance
    for key in (
        "rendezvous",
        "capture",
        "concealed_lair",
        "hidden_base_discovery",
        "infiltration",
        "emitter_localization",
    ):
        assert outcome.results[key] == debrief_b.outcome.results[key]
    assert (
        outcome.results["pattern_of_life"]["num_events"]
        == debrief_b.outcome.results["pattern_of_life"]["num_events"]
    )
    assert debrief_a.lessons == debrief_b.lessons

    # All capabilities present with sane values.
    rv = outcome.results["rendezvous"]
    assert rv["num_windows"] >= 0
    assert rv["delta_v_total_m_s"] > 0.0
    cap = outcome.results["capture"]
    assert "num_windows" in cap and "grapple_delta_v_m_s" in cap
    lair = outcome.results["concealed_lair"]
    assert lair["num_candidates"] >= 0
    disc = outcome.results["hidden_base_discovery"]
    assert disc["num_candidate_cells"] > 0
    assert disc["footprint_rank"] >= 1
    # Truth and estimate are reported separately; the centroid is not recovered
    # and the outcome must keep saying so rather than collapsing them.
    assert disc["centroid_rank"] > disc["footprint_rank"]
    assert disc["peak_offset_m"] > 0.0
    lair_res = outcome.results["concealed_lair"]
    assert lair_res["detected_in_footprint"] is True
    assert lair_res["detector_offset_m"] > 0.0
    infil = outcome.results["infiltration"]
    assert infil["cost_reduction"] >= -1e-9
    emit = outcome.results["emitter_localization"]
    # A noise-free TDOA round trip returns 0.0 by construction; the mission
    # solves noisy timings, so the error must be a real positive quantity.
    assert emit["time_noise_s"] > 0.0
    assert emit["error_m"] > 0.0
    assert emit["imagery_site_offset_m"] > 0.0
    pat = outcome.results["pattern_of_life"]
    assert pat["num_events"] > 0
    assert pat["tempo"] in {"low", "medium", "high"}


def test_provider_plan_steps() -> None:
    provider = MissionProvider()
    plan = provider.plan(provider.brief())
    assert len(plan.steps) == 7
    names = [s.name for s in plan.steps]
    assert names == [
        "rendezvous",
        "capture",
        "lair",
        "discovery",
        "infiltration",
        "emitter",
        "pattern",
    ]
    actions = [s.action for s in plan.steps]
    assert actions == [
        "solve_windows",
        "solve_capture",
        "detect_concealed_lair",
        "fuse_cues",
        "plan_route",
        "localize_emitter",
        "pattern_summary",
    ]


def test_provider_recon_findings() -> None:
    provider = MissionProvider()
    report = provider.recon(ReconRequest(goal="recon the volcano basin"))
    labels = {f.label for f in report.findings}
    assert "goal" in labels
    assert "constraint" in labels


def test_provider_debrief_lessons() -> None:
    provider = MissionProvider()
    debrief = provider.debrief(provider.execute(provider.plan(provider.brief())))
    assert debrief.lessons
    assert all(isinstance(l, str) and l for l in debrief.lessons)


def test_evidence_notes_branches() -> None:
    # Empty results -> no evidence notes (falsy branches).
    assert (
        _evidence_notes(
            {
                "rendezvous": {"num_windows": 0},
                "capture": {"num_windows": 0},
                "concealed_lair": {},
                "hidden_base_discovery": {},
                "infiltration": {},
                "pattern_of_life": {},
            }
        )
        == ()
    )
    # Populated results -> notes include each capability's headline.
    notes = _evidence_notes(
        {
            "rendezvous": {"num_windows": 2, "first_window_start_s": 100.0},
            "capture": {"num_windows": 1, "grapple_delta_v_m_s": 900.0},
            "concealed_lair": {"top_fused_score": 5.0, "detector_offset_m": 5656.9},
            "hidden_base_discovery": {
                "footprint_rank": 1,
                "footprint_cells": 80,
                "centroid_rank": 80,
                "num_candidate_cells": 4096,
                "single_cue_footprint_ranks": {"thermal": 1, "terrain": 1, "rf": 1},
            },
            "infiltration": {"cost_reduction": 0.3},
            "pattern_of_life": {"tempo": "high"},
        }
    )
    assert len(notes) == 7
    assert any("2 rendezvous" in n for n in notes)
    assert any("capture window" in n for n in notes)
    assert any("rank 1 of 4096" in n for n in notes)
    assert any("centre cell itself ranks 80" in n for n in notes)
    assert any("5656.9 m from the injected facility centre" in n for n in notes)
    assert any("fusion was not what found the base" in n for n in notes)
    assert any("cuts cost by 30.0%" in n for n in notes)


def test_evidence_notes_reports_fusion_as_necessary_when_it_is() -> None:
    """The single-cue note is derived from the ranks, not stapled on.

    Feeding ranks where no cue is individually decisive must flip the wording,
    which is what makes the claim in the debrief a report rather than a slogan.
    """
    notes = _evidence_notes(
        {
            "hidden_base_discovery": {
                "footprint_rank": 3,
                "footprint_cells": 80,
                "centroid_rank": 9,
                "num_candidate_cells": 4096,
                "single_cue_footprint_ranks": {"thermal": 7, "terrain": 4, "rf": 12},
            },
        }
    )
    assert any("fusion was necessary" in n for n in notes)
    assert not any("fusion was not what found" in n for n in notes)


def test_gadget_registry_registration() -> None:
    registry = GadgetRegistry()
    result = register_gadgets(registry)
    assert result is registry
    names = registry.gadgets_for("you_only_live_twice")
    assert {
        "rendezvous_solver",
        "intercept_budget",
        "capture_solver",
        "lair_detector",
        "discovery_engine",
        "search_ranker",
        "route_planner",
        "emitter_locator",
        "pattern_analyzer",
    } <= set(names)
    # The gadgets resolve to callables.
    assert callable(registry.lookup("you_only_live_twice", "rendezvous_solver"))
    assert callable(registry.lookup("you_only_live_twice", "route_planner"))
    assert callable(registry.lookup("you_only_live_twice", "emitter_locator"))
    assert self_film() == "you_only_live_twice"


def test_fallback_gadgets_import() -> None:
    assert "you_only_live_twice" in FALLBACK_GADGETS
    assert FALLBACK_GADGETS.films() == ("you_only_live_twice",)


def test_mission_registry_accepts_provider() -> None:
    registry = MissionRegistry()
    registry.register(MissionProvider())
    assert "you_only_live_twice" in registry
    assert registry.lookup("you_only_live_twice").film == "you_only_live_twice"
