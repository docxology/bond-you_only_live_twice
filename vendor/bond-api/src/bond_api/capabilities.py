"""Capability helpers that deepen THE PROTOCOL without changing it.

Phase 4 adds well-tested helpers **on top of** the frozen contract, so the
film fleet and sibling layers keep working unchanged:

* **MissionBrief validation** — :func:`brief_issues` / :func:`validate_brief`
  return *advisory* issues (duplicate asset names, duplicate constraint
  kinds, duplicate objectives, whitespace-slack asset names) beyond the hard
  invariants the constructor already enforces. Coordinators use the report to
  pre-flight a film's brief before dispatching.
* **Plan-step schema checks** — :func:`plan_schema_issues` /
  :func:`require_plan_schema` verify a plan has no duplicate step names, no
  malformed param keys, JSON-serializable params, and (optionally) exactly
  the expected step names in order.
* **Provenance hashing** — :func:`fingerprint` is a deterministic SHA-256 over
  the canonical JSON encoding of arbitrary parts; :func:`hash_provenance`
  fingerprints a full provenance record; :func:`derive_provenance` builds a
  provenance whose ``input_hash`` is derived from the mission's inputs.
* **Debrief normalization** — :func:`normalize_lessons` /
  :func:`normalize_debrief` strip, drop, and dedupe lessons while preserving
  first-occurrence order, and re-validate the outcome.

Every existing protocol type, field, and ``run_mission`` flow is untouched.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

from bond_api.protocol import Debrief, MissionBrief, MissionOutcome, MissionPlan, Provenance
from bond_api.serialization import SerializationError, to_json

__all__ = [
    "BriefReport",
    "brief_issues",
    "derive_provenance",
    "fingerprint",
    "hash_provenance",
    "normalize_debrief",
    "normalize_lessons",
    "plan_schema_issues",
    "require_plan_schema",
    "validate_brief",
]

#: Public capability helper names (consumed by manuscript variables).
CAPABILITY_NAMES = (
    "brief_issues",
    "derive_provenance",
    "fingerprint",
    "hash_provenance",
    "normalize_debrief",
    "normalize_lessons",
    "plan_schema_issues",
    "require_plan_schema",
    "validate_brief",
)


@dataclass(frozen=True)
class BriefReport:
    """Outcome of a soft brief validation: the brief plus any advisory issues."""

    brief: MissionBrief
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """True when the brief raised no advisory issues."""
        return not self.issues


def brief_issues(brief: MissionBrief) -> tuple[str, ...]:
    """Return advisory validation issues for a mission brief.

    Unlike the constructor's hard invariants (which raise), these checks
    report problems a coordinator may want to tolerate or escalate:
    duplicate asset names, duplicate constraint kinds, duplicate objectives,
    and asset names with leading/trailing whitespace.
    """
    issues: list[str] = []

    asset_names = [asset.name for asset in brief.assets]
    duplicate_assets = sorted({name for name in asset_names if asset_names.count(name) > 1})
    if duplicate_assets:
        issues.append(f"duplicate asset names: {', '.join(duplicate_assets)}")

    constraint_kinds = [constraint.kind for constraint in brief.constraints]
    duplicate_kinds = sorted({kind for kind in constraint_kinds if constraint_kinds.count(kind) > 1})
    if duplicate_kinds:
        issues.append(f"duplicate constraint kinds: {', '.join(duplicate_kinds)}")

    if len(set(brief.objectives)) != len(brief.objectives):
        issues.append("duplicate objectives")

    slack_assets = sorted(name for name in asset_names if name != name.strip())
    if slack_assets:
        issues.append(f"asset names with leading/trailing whitespace: {', '.join(slack_assets)}")

    return tuple(issues)


def validate_brief(brief: MissionBrief) -> BriefReport:
    """Validate a mission brief softly, returning a :class:`BriefReport`."""
    return BriefReport(brief=brief, issues=brief_issues(brief))


def plan_schema_issues(
    plan: MissionPlan,
    expected_steps: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Return plan-step schema issues: duplicates, param sanity, expected names.

    When ``expected_steps`` is given, the plan's step names must match it
    exactly (same names, same order) — the strict schema check coordinators
    use to verify a film's plan honors the declared contract.
    """
    issues: list[str] = []

    names = [step.name for step in plan.steps]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        issues.append(f"duplicate step names: {', '.join(duplicates)}")

    for step in plan.steps:
        if any(not isinstance(key, str) or not key.strip() for key in step.params):
            issues.append(f"step {step.name!r} has a non-string or blank param key")
        try:
            to_json(step.params)
        except SerializationError:
            issues.append(f"step {step.name!r} params are not JSON-serializable")

    if expected_steps is not None and tuple(names) != expected_steps:
        issues.append(f"step names {tuple(names)} do not match expected {expected_steps}")

    return tuple(issues)


def require_plan_schema(plan: MissionPlan, expected_steps: tuple[str, ...] | None = None) -> None:
    """Require a plan to satisfy its schema, raising ``ValueError`` otherwise."""
    issues = plan_schema_issues(plan, expected_steps)
    if issues:
        raise ValueError("; ".join(issues))


def fingerprint(*parts: Any) -> str:
    """Deterministic SHA-256 over the canonical JSON encoding of ``parts``.

    Canonical means key-sorted with fixed indentation (see
    :func:`bond_api.serialization.to_json`), so identical parts always
    produce the same fingerprint. Use it for provenance input hashes and audit
    chains. Parts must be JSON-serializable (a
    :class:`~bond_api.serialization.SerializationError` propagates otherwise).

    Evidence, not assertion: ``tests/test_golden_determinism.py`` pins the
    digest of fixed inputs to checked-in literals and re-derives them in a
    freshly spawned interpreter under ``PYTHONHASHSEED=random``, which is what
    "across processes" means. Cross-*platform* stability follows from SHA-256
    plus a byte-stable encoding, and is checked wherever the suite runs — but
    the suite cannot assert a platform it has never executed on.
    """
    digest = hashlib.sha256()
    for part in parts:
        digest.update(to_json(part).encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def hash_provenance(provenance: Provenance) -> str:
    """Fingerprint a full provenance record (all four fields)."""
    return fingerprint(
        provenance.package_version,
        provenance.seed,
        provenance.input_hash,
        provenance.wall_time_s,
    )


def derive_provenance(
    *,
    package_version: str,
    seed: int,
    inputs: Iterable[Any] = (),
    wall_time_s: float = 0.0,
) -> Provenance:
    """Build a :class:`Provenance` whose ``input_hash`` is derived from ``inputs``.

    The derived hash makes outcomes auditable without re-running the film:
    the same inputs plus the same seed produce the same provenance record.
    """
    return Provenance(
        package_version=package_version,
        seed=seed,
        input_hash=fingerprint(*inputs),
        wall_time_s=wall_time_s,
    )


def normalize_lessons(lessons: Iterable[str]) -> tuple[str, ...]:
    """Normalize lessons: strip whitespace, drop empties, dedupe in order.

    First occurrence wins; ordering is preserved, so normalized debriefs are
    deterministic and stable across repeated normalization.
    """
    seen: set[str] = set()
    normalized: list[str] = []
    for lesson in lessons:
        cleaned = lesson.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return tuple(normalized)


def normalize_debrief(debrief: Debrief) -> Debrief:
    """Return a new :class:`Debrief` with normalized lessons and a valid outcome.

    The outcome is re-validated explicitly (a non-``MissionOutcome`` raises
    ``ValueError``) and the lessons are passed through :func:`normalize_lessons`.
    The original debrief is never mutated — frozen dataclasses make that
    impossible by construction.
    """
    if not isinstance(debrief.outcome, MissionOutcome):
        raise ValueError("Debrief.outcome must be a MissionOutcome")
    return Debrief(outcome=debrief.outcome, lessons=normalize_lessons(debrief.lessons))
