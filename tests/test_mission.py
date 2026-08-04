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
    assert len(brief.objectives) == 3
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

    # Determinism: same scalar results and identical provenance.
    assert outcome.provenance == debrief_b.outcome.provenance
    assert outcome.results["rendezvous"] == debrief_b.outcome.results["rendezvous"]
    assert (
        outcome.results["concealed_lair"] == debrief_b.outcome.results["concealed_lair"]
    )
    assert (
        outcome.results["pattern_of_life"]["num_events"]
        == debrief_b.outcome.results["pattern_of_life"]["num_events"]
    )
    assert debrief_a.lessons == debrief_b.lessons

    # All three capabilities present with sane values.
    rv = outcome.results["rendezvous"]
    assert rv["num_windows"] >= 0
    assert rv["delta_v_total_m_s"] > 0.0
    lair = outcome.results["concealed_lair"]
    assert lair["num_candidates"] >= 0
    pat = outcome.results["pattern_of_life"]
    assert pat["num_events"] > 0
    assert pat["tempo"] in {"low", "medium", "high"}


def test_provider_plan_steps() -> None:
    provider = MissionProvider()
    plan = provider.plan(provider.brief())
    assert len(plan.steps) == 3
    names = [s.name for s in plan.steps]
    assert names == ["rendezvous", "lair", "pattern"]
    actions = [s.action for s in plan.steps]
    assert actions == ["solve_windows", "detect_concealed_lair", "pattern_summary"]


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
                "concealed_lair": {},
                "pattern_of_life": {},
            }
        )
        == ()
    )
    # Populated results -> notes include each capability's headline.
    notes = _evidence_notes(
        {
            "rendezvous": {"num_windows": 2, "first_window_start_s": 100.0},
            "concealed_lair": {"top_fused_score": 5.0},
            "pattern_of_life": {"tempo": "high"},
        }
    )
    assert len(notes) == 3
    assert any("2 rendezvous" in n for n in notes)


def test_gadget_registry_registration() -> None:
    registry = GadgetRegistry()
    result = register_gadgets(registry)
    assert result is registry
    names = registry.gadgets_for("you_only_live_twice")
    assert {
        "rendezvous_solver",
        "intercept_budget",
        "lair_detector",
        "pattern_analyzer",
    } <= set(names)
    # The gadgets resolve to callables.
    assert callable(registry.lookup("you_only_live_twice", "rendezvous_solver"))
    assert self_film() == "you_only_live_twice"


def test_fallback_gadgets_import() -> None:
    assert "you_only_live_twice" in FALLBACK_GADGETS
    assert FALLBACK_GADGETS.films() == ("you_only_live_twice",)


def test_mission_registry_accepts_provider() -> None:
    registry = MissionRegistry()
    registry.register(MissionProvider())
    assert "you_only_live_twice" in registry
    assert registry.lookup("you_only_live_twice").film == "you_only_live_twice"
