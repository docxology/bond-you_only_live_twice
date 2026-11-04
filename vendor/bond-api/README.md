# bond-api — BOND-API: the frozen mission protocol contract

**BOND-API** (codename **THE PROTOCOL**) is Layer 1 of the BOND suite: the
single contract every film package implements and every coordinator consumes.
This package freezes that contract so the 27 film agents code against a
stable, tested surface instead of a moving one.

## Film → concept mapping

The BOND suite gives each package a film and a codename, and the mapping is
not decoration — it names the job.

| Element | Value |
|---|---|
| Codename | **THE PROTOCOL** |
| Reference film | **SABLE** (`films/sable/`) — the protocol's own smoke film, invented for this layer rather than borrowed from a title, because it must exist before any real film does |
| Concept | *Q Branch's specification, not Q Branch's gadgets.* A field agent can improvise; the briefing format cannot. This package is the briefing format. |
| Consequence | Everything here is additive-only. A change to a field name is felt by all 27 films and every sibling layer at once. |

## Modules

| Module | Role |
|---|---|
| `src/bond_api/protocol.py` | The freeze: 11 frozen dataclasses covering the full mission lifecycle (`Asset`, `Constraint`, `Finding`, `Step`, `ReconRequest`, `MissionBrief`, `ReconReport`, `MissionPlan`, `Provenance`, `MissionOutcome`, `Debrief`), the runtime-checkable `MissionProvider` contract, `run_mission()`, and `protocol_surface()`. Pure stdlib. |
| `src/bond_api/serialization.py` | Deterministic, tagged JSON round-trips for every protocol object — `to_json`/`from_json`, `to_dict`/`from_dict`, the published `SERIALIZATION_TAG`, and `SerializationError`. No pickling. |
| `src/bond_api/discovery.py` | Slug-based film discovery on `sys.path`: `load_provider()` (strict, one film) and `discover()` (tolerant, many films), plus `DiscoveryError`. |
| `src/bond_api/registry.py` | `GadgetRegistry` (film → named gadgets) and `MissionRegistry` (slug → provider); insertion-ordered and deterministic. |
| `src/bond_api/capabilities.py` | Capability helpers layered on the freeze: soft brief validation (`brief_issues`/`validate_brief`), plan-step schema checks (`plan_schema_issues`/`require_plan_schema`), SHA-256 provenance hashing (`fingerprint`/`hash_provenance`/`derive_provenance`), debrief normalization (`normalize_lessons`/`normalize_debrief`). |
| `src/bond_api/manuscript_variables.py` | Token hydration for the manuscript: `generate_variables()`, `load_manuscript_config()`, `read_coverage_floor()`, `require_surface()`, `resolve_manuscript_tree()`. |
| `films/sable/mission.py` | The reference film: a real, deterministic provider implementing all five stages. |
| `scripts/00_preflight.py` | Thin orchestrator — verifies the package imports and its surface is intact. |
| `scripts/demo_mission.py` | Thin orchestrator — discovers a film and runs brief → recon → plan → execute → debrief. |
| `scripts/z_generate_manuscript_variables.py` | Thin orchestrator — hydrates manuscript tokens (strict by default). |
| `tests/` | Zero-mock suite over `src/` and the real reference film. |

## Quickstart

```bash
# From this directory
uv sync --extra dev

# Run the suite (the enforced gate: line + branch coverage on src/)
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90

# Verify the environment
uv run python scripts/00_preflight.py

# Run the reference film end-to-end (discovery → brief → recon → plan → execute → debrief)
uv run python scripts/demo_mission.py

# Hydrate manuscript tokens (strict: an unresolved token exits non-zero)
uv run python scripts/z_generate_manuscript_variables.py

# Code quality (all three must pass)
uv run --extra dev ruff check src/ scripts/ films/ tests/
uv run --extra dev ruff format --check src/ scripts/ films/ tests/
uv run --extra dev mypy src/ scripts/ films/
```

Measured coverage and test counts are not quoted here on purpose: they are
whatever the command above prints. The number that is *enforced* is the
`fail_under` floor declared in `pyproject.toml`, and the manuscript reads that
floor from the same place rather than restating it.

## The MissionProvider surface

A film package is a top-level module named by its slug (e.g. `sable`) exposing
`mission.MissionProvider` — a class with a `film` attribute and five stages:

| Stage | Signature |
|---|---|
| brief | `brief() -> MissionBrief` |
| recon | `recon(request: ReconRequest) -> ReconReport` |
| plan | `plan(brief: MissionBrief) -> MissionPlan` |
| execute | `execute(plan: MissionPlan) -> MissionOutcome` |
| debrief | `debrief(outcome: MissionOutcome) -> Debrief` |

`MissionProvider` is a structural `typing.Protocol`, so a film satisfies it by
shape — no base class, no import-time coupling beyond the dataclasses it
returns. Every artifact is a frozen dataclass validated at construction, and
every outcome carries `Provenance` (package version, seed, input hash, wall
time) so results are auditable without re-running the film.

Coordinators find providers with `discover()`, hold them in a
`MissionRegistry`, and move artifacts across process boundaries with
`to_json` / `from_json`. On top of the frozen surface,
`bond_api.capabilities` adds validation, schema enforcement, provenance
fingerprinting, and debrief normalization — none of which change a field.

Minimal conforming film:

```python
from bond_api.protocol import Debrief, MissionBrief, MissionOutcome, MissionPlan, ReconReport, ReconRequest

class MissionProvider:
    film = "my_slug"

    def brief(self) -> MissionBrief: ...
    def recon(self, request: ReconRequest) -> ReconReport: ...
    def plan(self, brief: MissionBrief) -> MissionPlan: ...
    def execute(self, plan: MissionPlan) -> MissionOutcome: ...
    def debrief(self, outcome: MissionOutcome) -> Debrief: ...
```

`films/sable/mission.py` is the fully worked version of this shape; copy it.

## Implementation rules (from `AGENTS.md`)

- **Pure core**: `src/bond_api/` is dependency-free logic (stdlib, plus
  `pyyaml` in the config adapter only). Scripts are thin orchestrators —
  enforced by an `ast`-based test, not by review.
- **No mocks**: tests use real data, real files, real subprocesses.
- **Deterministic**: fixed seeds, no untracked random reliance; `to_json` is
  byte-deterministic. The manuscript generator reads no wall clock, so
  regenerating `output/` twice on one interpreter writes identical bytes —
  bound by `tests/test_regeneration_determinism.py`. (`PYTHON_VERSION` is the
  one environment-derived token, so a different interpreter changes those
  bytes by design.)
- **Frozen contract**: additive changes only. Renaming a field, tightening
  validation, or changing a default is a versioned migration, never a silent
  edit.
- **No hand-authored metrics**: every number in the manuscript arrives as a
  `{{TOKEN}}` from `manuscript_variables.py` + `config.yaml` + `pyproject.toml`.

## Layout

```
src/bond_api/          The package (protocol · serialization · discovery · registry · capabilities · manuscript variables)
films/sable/           Reference film implementing the contract
scripts/               Thin orchestrators
tests/                 Zero-mock test suite
manuscript/            Protocol manuscript + config.yaml (token-hydrated)
docs/                  Agent-facing documentation hub
data/                  claim_ledger.yaml and dataset notes
output/                Disposable generated artifacts — regenerate, never hand-edit
```

## Status

The protocol layer is frozen and complete for version `0.1.0`: contract,
serialization, discovery, registries, capability helpers, reference film,
manuscript, and a zero-mock suite that clears the enforced coverage floor
(run the gate above to see the current figure). Downstream packages — bond-coordinator,
bond-orchestrator, bond-cli, and the film packages — code against this
contract. Remaining integration points are tracked in [`TODO.md`](TODO.md).
