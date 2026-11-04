# AGENTS.md — you_only_live_twice (VOLCANO)

Project rules for agents working in this package. **Scope = exactly this
directory.** Published at `github.com/docxology/bond-you_only_live_twice`;
commit on `main`, path-scoped (`git add -A` in this repo only).

Deeper guidance lives under `docs/`: `docs/AGENTS.md` (working procedure and
package-specific traps), `docs/agent_instructions.md` (the hard rules),
`docs/architecture.md` (module-by-module architecture and the `MissionProvider`
mapping), `docs/testing_philosophy.md` (what a test here must prove).

## Layer contract

| Surface | Rule |
| --- | --- |
| `rendezvous_windows.py`, `orbital_capture.py`, `terrain_anomaly.py`, `hidden_base_discovery.py`, `infiltration_planning.py`, `emitter_localization.py`, `pattern_of_life.py`, `scenario.py` | Pure domain core — stdlib + numpy only, importable **without** BOND-API |
| `mission.py` | Thin BOND-API `MissionProvider` adapter + gadget registration |
| `figures.py`, `manuscript_variables.py` | Derivation layer (no domain logic; only `manuscript_variables.py` reads protocol identity) |
| `scripts/` | Thin orchestrators only |
| Live counts | Measured by the gate run; recorded locally under the gitignored `docs/_generated/`; never hardcode measured totals/coverage in prose |

## Capability summary

- `rendezvous_windows.py` — circular two-body propagation, line-of-sight range
  & elevation, contiguous window search, coplanar Hohmann delta-v.
- `orbital_capture.py` — capture envelope (range + relative-speed), velocity-
  matching burn, phasing lead angle / wait time.
- `terrain_anomaly.py` — Gaussian background modelling, standardized-residual
  anomaly scoring (thermal one-tailed, terrain magnitude), weighted fusion,
  connected-component lair detection.
- `hidden_base_discovery.py` — Bayesian cue fusion (thermal/terrain/RF),
  posterior map, deterministic search order, effort & discovery curve.
- `infiltration_planning.py` — slope/thermal/guard cost fields, A* route vs a
  same-space greedy baseline that also *reaches the goal* (it backtracks out of
  dead ends), which is what makes the reduction non-negative.
- `emitter_localization.py` — TDOA hyperbolic multilateration via Gauss–Newton.
- `pattern_of_life.py` — Poisson diurnal activity model, weekly/daily
  histograms, autocorrelation periodicity, peak windows, tempo, duty cycle.

All seven capabilities are computed by the single source
`scenario.solve_mission`, which both `mission.execute` and the manuscript
token generator consume so outcomes and prose can never disagree. Scenario
*inputs* follow the same discipline: `scenario.scenario_descriptor()` is at
once the object the provenance `input_hash` covers and the source of the
manuscript's `{{SETUP_*}}` parameter tokens, so a reported parameter cannot
drift from the simulated one. Add a new parameter as a named module-level
constant and put it in the descriptor.

## Standards

- No mock framework (`MagicMock` / `mocker.patch` / `unittest.mock`) anywhere.
  Real data + computation only; deterministic fakes implement the real protocol.
- ≥90% line **and** branch coverage on `src/`:
  `uv run pytest tests/ --cov=src --cov-fail-under=90`.
- Deterministic: fixed seeds, no untracked RNG, no wall-clock in persisted
  artifacts.
- Type hints + docstrings; `ruff check` + `ruff format` and `mypy` green on
  `src/` and `scripts/`.
- Manuscript numbers injected from `manuscript/config.yaml` +
  `src/you_only_live_twice/manuscript_variables.py` — never hand-author metrics
  in prose.

## Protocol integration

`mission.py` implements the frozen BOND-API `MissionProvider` (see the
`bond-api` path dependency in `pyproject.toml`). The orchestrator discovers
VOLCANO by slug `you_only_live_twice` via `bond_api.discovery`; the provider
registers its gadgets (rendezvous solver, intercept budget, capture solver,
lair detector, discovery engine, search ranker, route planner, emitter locator,
pattern analyzer) with the `GadgetRegistry`.

## Verification gate

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
rg -n "template[_]code_project" . || echo CLEAN   # lineage must be zero
git status --short                                 # clean after commit
```
