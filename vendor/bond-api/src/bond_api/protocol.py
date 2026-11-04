"""BOND-API protocol: the frozen contract every film package implements.

BOND-API (codename *THE PROTOCOL*) is Layer 1 of the BOND suite. It defines:

* the frozen dataclasses covering the full mission lifecycle — brief, recon,
  plan, execute, debrief — plus the provenance every outcome must carry;
* :class:`MissionProvider`, the runtime-checkable structural contract that
  every film package (``<slug>/mission.py``) implements;
* :func:`run_mission`, the deterministic five-stage flow used by scripts and
  coordinators to drive any provider.

The protocol is deliberately dependency-free (stdlib only): any film package
can implement it without importing infrastructure, and any coordinator can
consume it without knowing a film's internals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, is_dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "Asset",
    "CODENAME",
    "Constraint",
    "Debrief",
    "Finding",
    "IDENTITY",
    "MISSION_FLOW",
    "MissionBrief",
    "MissionOutcome",
    "MissionPlan",
    "MissionProvider",
    "Provenance",
    "ReconReport",
    "ReconRequest",
    "Step",
    "protocol_surface",
    "run_mission",
]

#: Manuscript identity of this package (BOND-API, codename THE PROTOCOL).
IDENTITY = "BOND-API"
CODENAME = "THE PROTOCOL"

#: The five provider stages, in execution order.
MISSION_FLOW = ("brief", "recon", "plan", "execute", "debrief")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_non_empty(value: Any, label: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be a non-empty string")


def _require_tuple_of(value: Any, label: str, element_type: type) -> None:
    _require(isinstance(value, tuple), f"{label} must be a tuple")
    for item in value:
        _require(isinstance(item, element_type), f"{label} entries must be {element_type.__name__} instances")


def _require_number(value: Any, label: str, *, minimum: float = 0.0, integer_only: bool = False) -> None:
    if integer_only:
        _require(
            isinstance(value, int) and not isinstance(value, bool),
            f"{label} must be a non-boolean integer",
        )
    else:
        _require(
            isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{label} must be a non-boolean number",
        )
        # A non-finite float passes the >= minimum check (inf >= 0 is True)
        # but cannot be serialized to RFC 8259 JSON (see bond_api.serialization).
        # Reject it here so a Provenance that could never round-trip cannot
        # be constructed in the first place. NaN fails `>= minimum` already,
        # so this narrows the hole to +/-inf.
        if isinstance(value, float) and not math.isfinite(value):
            _require(False, f"{label} must be a finite number")
    _require(value >= minimum, f"{label} must be >= {minimum}")


@dataclass(frozen=True)
class Asset:
    """An asset attached to a mission brief: typed, named, with an opaque payload.

    ``payload`` is intentionally untyped: films may attach any JSON-serializable
    value (dict, list, tuple, primitive, nested protocol object) and rely on
    :mod:`bond_api.serialization` to round-trip it.
    """

    kind: str
    name: str
    payload: Any = None

    def __post_init__(self) -> None:
        _require_non_empty(self.kind, "Asset.kind")
        _require_non_empty(self.name, "Asset.name")


@dataclass(frozen=True)
class Constraint:
    """A mission constraint: a kind (e.g. ``determinism``) and a free-form detail."""

    kind: str
    detail: str = ""

    def __post_init__(self) -> None:
        _require_non_empty(self.kind, "Constraint.kind")


@dataclass(frozen=True)
class Finding:
    """A single recon finding: a label and the evidence captured for it."""

    label: str
    detail: str = ""

    def __post_init__(self) -> None:
        _require_non_empty(self.label, "Finding.label")


@dataclass(frozen=True)
class Step:
    """A single mission plan step: a name, an action, and optional parameters."""

    name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "Step.name")
        _require_non_empty(self.action, "Step.action")
        _require(isinstance(self.params, dict), "Step.params must be a dict")


@dataclass(frozen=True)
class ReconRequest:
    """A request for reconnaissance: what the mission needs to learn."""

    goal: str

    def __post_init__(self) -> None:
        _require_non_empty(self.goal, "ReconRequest.goal")


@dataclass(frozen=True)
class MissionBrief:
    """The frozen mission definition a film declares for itself.

    ``objectives`` must be non-empty: a mission with no objectives is
    meaningless. ``assets`` and ``constraints`` may be empty tuples.
    """

    film: str
    codename: str
    objectives: tuple[str, ...]
    assets: tuple[Asset, ...] = field(default_factory=tuple)
    constraints: tuple[Constraint, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_non_empty(self.film, "MissionBrief.film")
        _require_non_empty(self.codename, "MissionBrief.codename")
        _require(isinstance(self.objectives, tuple), "MissionBrief.objectives must be a tuple")
        _require(bool(self.objectives), "MissionBrief.objectives must not be empty")
        for objective in self.objectives:
            _require(
                isinstance(objective, str) and bool(objective.strip()),
                "MissionBrief.objectives entries must be non-empty strings",
            )
        _require_tuple_of(self.assets, "MissionBrief.assets", Asset)
        _require_tuple_of(self.constraints, "MissionBrief.constraints", Constraint)


@dataclass(frozen=True)
class ReconReport:
    """The output of reconnaissance: an ordered tuple of findings."""

    findings: tuple[Finding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_tuple_of(self.findings, "ReconReport.findings", Finding)


@dataclass(frozen=True)
class MissionPlan:
    """The output of planning: an ordered tuple of steps."""

    steps: tuple[Step, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_tuple_of(self.steps, "MissionPlan.steps", Step)


@dataclass(frozen=True)
class Provenance:
    """Execution provenance every mission outcome must carry.

    ``seed`` is the deterministic RNG seed (0 disables randomness), and
    ``input_hash`` is a stable fingerprint of the mission inputs so outcomes
    can be audited without re-running the film.
    """

    package_version: str
    seed: int
    input_hash: str
    wall_time_s: float = 0.0

    def __post_init__(self) -> None:
        _require_non_empty(self.package_version, "Provenance.package_version")
        _require_number(self.seed, "Provenance.seed", integer_only=True)
        _require_non_empty(self.input_hash, "Provenance.input_hash")
        _require_number(self.wall_time_s, "Provenance.wall_time_s")


@dataclass(frozen=True)
class MissionOutcome:
    """The result of executing a mission plan: success flag, results, provenance."""

    success: bool
    results: dict[str, Any]
    provenance: Provenance

    def __post_init__(self) -> None:
        _require(isinstance(self.success, bool), "MissionOutcome.success must be a bool")
        _require(isinstance(self.results, dict), "MissionOutcome.results must be a dict")
        _require(isinstance(self.provenance, Provenance), "MissionOutcome.provenance must be a Provenance")


@dataclass(frozen=True)
class Debrief:
    """The final stage of a mission: the outcome plus lessons learned."""

    outcome: MissionOutcome
    lessons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require(isinstance(self.outcome, MissionOutcome), "Debrief.outcome must be a MissionOutcome")
        _require(isinstance(self.lessons, tuple), "Debrief.lessons must be a tuple")
        for lesson in self.lessons:
            _require(
                isinstance(lesson, str) and bool(lesson.strip()),
                "Debrief.lessons entries must be non-empty strings",
            )


@runtime_checkable
class MissionProvider(Protocol):
    """Structural contract every film package implements.

    A film package is a top-level module named by its slug exposing
    ``mission.MissionProvider`` (see :mod:`bond_api.discovery`). Instances
    declare ``film`` (the slug they answer to) and the five lifecycle stages,
    each returning the protocol dataclass named in its annotation.
    """

    film: str

    # The stub bodies below are typing markers, never executed — coverage.py
    # arc analysis on single-line `...` bodies is version-sensitive, so mark
    # them explicitly excluded rather than chase a moving branch count.
    def brief(self) -> MissionBrief: ...  # pragma: no cover
    def recon(self, request: ReconRequest) -> ReconReport: ...  # pragma: no cover
    def plan(self, brief: MissionBrief) -> MissionPlan: ...  # pragma: no cover
    def execute(self, plan: MissionPlan) -> MissionOutcome: ...  # pragma: no cover
    def debrief(self, outcome: MissionOutcome) -> Debrief: ...  # pragma: no cover


def run_mission(provider: MissionProvider, request: ReconRequest) -> Debrief:
    """Execute the full five-stage mission flow against a provider.

    Deterministic by construction: the flow itself makes no random draws and
    performs no I/O; everything else is up to the film, which the protocol
    requires to be deterministic too.

    The recon stage is executed for its contract obligations (a film must be
    able to answer a :class:`ReconRequest`) but its :class:`ReconReport` is
    intentionally not threaded into ``plan``: the frozen contract declares
    ``plan(brief) -> MissionPlan``, so a film that needs recon evidence while
    planning must carry it itself. Callers that want the report drive the five
    stages directly, as ``scripts/demo_mission.py`` does.
    """
    brief = provider.brief()
    provider.recon(request)
    plan = provider.plan(brief)
    outcome = provider.execute(plan)
    return provider.debrief(outcome)


def protocol_surface() -> dict[str, str | tuple[str, ...]]:
    """Canonical, deterministic inventory of the frozen protocol surface.

    Returns the identity, the sorted dataclass names, and the provider flow.
    Manuscript variables and preflight checks consume this rather than
    hardcoding names.
    """
    return {
        "identity": IDENTITY,
        "codename": CODENAME,
        "dataclasses": tuple(
            sorted(name for name, member in globals().items() if isinstance(member, type) and is_dataclass(member))
        ),
        "provider_methods": MISSION_FLOW,
    }
