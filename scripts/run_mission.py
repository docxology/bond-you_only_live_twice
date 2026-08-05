"""Thin mission CLI: drives the VOLCANO mission lifecycle phase by phase.

Each mission phase (brief / recon / plan / execute / debrief) is a subcommand
wrapping the BOND-API provider. Running with an unknown argument defaults to the
full ``run`` flow, which executes all five stages in order via
:func:`bond_api.protocol.run_mission`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap so the package is importable when run as a plain script.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from bond_api.protocol import ReconRequest, run_mission

from you_only_live_twice.mission import MissionProvider

_PHASES = ("brief", "recon", "plan", "execute", "debrief")


def _provider() -> MissionProvider:
    return MissionProvider()


def run_phase(phase: str) -> None:
    """Run one mission phase against the provider and print a compact summary."""
    provider = _provider()
    if phase == "brief":
        brief = provider.brief()
        print(
            f"[VOLCANO] brief  film={brief.film} codename={brief.codename} objectives={len(brief.objectives)}"
        )
    elif phase == "recon":
        report = provider.recon(
            ReconRequest(goal="locate the concealed lair and time the intercept")
        )
        for finding in report.findings:
            print(f"[VOLCANO] recon  {finding.label}: {finding.detail}")
    elif phase == "plan":
        plan = provider.plan(provider.brief())
        for step in plan.steps:
            print(f"[VOLCANO] plan   step={step.name} action={step.action}")
    elif phase == "execute":
        outcome = provider.execute(provider.plan(provider.brief()))
        res = outcome.results
        print(
            f"[VOLCANO] execute success={outcome.success} "
            f"rendezvous_windows={res['rendezvous']['num_windows']} "
            f"capture_windows={res['capture']['num_windows']} "
            f"lair_candidates={res['concealed_lair']['num_candidates']} "
            f"discovery_rank={res['hidden_base_discovery']['true_rank']} "
            f"infiltration_reduction={res['infiltration']['cost_reduction']} "
            f"pattern_tempo={res['pattern_of_life']['tempo']}"
        )
        print(
            f"[VOLCANO] execute provenance input_hash={outcome.provenance.input_hash[:16]} seed={outcome.provenance.seed}"
        )
    elif phase == "debrief":
        debrief = provider.debrief(provider.execute(provider.plan(provider.brief())))
        print(f"[VOLCANO] debrief lessons={len(debrief.lessons)}")
        for lesson in debrief.lessons[:3]:
            print(f"  - {lesson}")
    else:
        raise ValueError(f"unknown phase: {phase}")


def run_full() -> None:
    """Run all five stages in order through the protocol runner."""
    debrief = run_mission(_provider(), ReconRequest(goal="full VOLCANO mission"))
    print(
        f"[VOLCANO] run      success={debrief.outcome.success} steps={debrief.outcome.results['steps_completed']}"
    )
    print(
        f"[VOLCANO] run      windows={debrief.outcome.results['rendezvous']['num_windows']} "
        f"lair_candidates={debrief.outcome.results['concealed_lair']['num_candidates']}"
    )
    print(f"[VOLCANO] run      lessons={len(debrief.lessons)}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "run"
    if command in _PHASES:
        run_phase(command)
        return 0
    # Unknown / missing argument -> full flow (thin-argv shaping convention).
    run_full()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
