# Agent Instructions — you_only_live_twice (VOLCANO)

Hard operational constraints for agents editing this package. Read this before
touching a file. `docs/AGENTS.md` covers the *procedure*; this file is the
*rules*.

## Scope and safety

- Work **only** inside this repository. Do not touch a sibling BOND package
  (the only protocol dependency here is the recorded copy in `vendor/bond-api`),
  or the template repo.
- This repo is published at `github.com/docxology/bond-you_only_live_twice`;
  commit and push on `main`.
- Commit path-scoped with `git add -A` **inside this repo only**.

## Layering

The package has three layers, and the direction of dependency is strictly
downward.

**Pure domain core** — infrastructure-free, stdlib + numpy only, importable
**without** BOND-API:

- `rendezvous_windows.py` — circular two-body propagation, line-of-sight range
  and elevation, contiguous window search, coplanar Hohmann Δv budget.
- `orbital_capture.py` — capture envelope (range **and** relative speed),
  velocity-matching grapple burn, phasing lead angle and wait time.
- `terrain_anomaly.py` — volcano-camouflage scene, standardized-residual
  thermal (one-tailed) and terrain (magnitude) anomaly scoring, weighted
  fusion, connected-component lair detection.
- `hidden_base_discovery.py` — terrain-weighted priors, Gaussian cue
  likelihood ratios, posterior fusion, deterministic search order, discovery
  curve, realised and posterior-expected search effort.
- `infiltration_planning.py` — slope / thermal / guard-exposure cost fields,
  deterministic 4-connected A*, same-space greedy baseline that backtracks so
  it always reaches the goal (a truncated baseline would not bound A*).
- `emitter_localization.py` — sensor-ring layout, exact TDOA range
  differences, seconds→metres conversion, Gauss–Newton multilateration. The
  mission solves *noisy* timings; a noise-free solve is a forward-model round
  trip and reports 0.0 by construction.
- `pattern_of_life.py` — inhomogeneous-Poisson activity, weekly and daily
  histograms, autocorrelation periodicity, peak windows, tempo, duty cycle.
- `scenario.py` — the deterministic scenario, the single analysis source
  (`solve_mission`), the provenance descriptor and its hash.

**Protocol adapter** — `mission.py` is the *only* module implementing the
frozen `bond_api` `MissionProvider`. It delegates; it does not compute.

**Derivation** — `figures.py` and `manuscript_variables.py` consume the
scenario and its outputs. They hold no domain logic.

`scripts/` contains thin orchestrators only — business logic belongs in `src/`.

Do not let the domain core import `bond_api`, `infrastructure`, matplotlib, or
anything under `scripts/`.

## Frozen protocol surface

`mission.py` must keep exposing, unchanged in public shape: the `film` slug,
`brief` / `recon` / `plan` / `execute` / `debrief`, `register_gadgets()` and
`FALLBACK_GADGETS`. `bond-cli`, the coordinator reconcile and the orchestrator
consume them across packages. Deepen inside the package; never break
discovery. `scripts/00_preflight.py` is the local check.

## Determinism & testing

- No mock framework (no `MagicMock` / `mocker.patch` / `unittest.mock`). Real
  computation and real data only; a test double must be a real implementation
  of the protocol, never a recording mock.
- Fixed seeds everywhere (the mission seed is 1967); no untracked RNG; no
  wall-clock in a persisted artifact.
- Prefer tests a wrong implementation would fail: closed-form anchors,
  round-trip inversion, injected-truth recovery, guaranteed inequalities. A
  shape assertion proves almost nothing here — see
  `docs/testing_philosophy.md`.
- Gate: `uv run pytest tests/ --cov=src --cov-fail-under=90` (line **and**
  branch), plus `ruff check` / `ruff format` and `mypy` green on `src/` and
  `scripts/`.

## Error handling

Never swallow a failure. `localize_tdoa` raises on singular geometry and on
non-convergence, `astar_path` raises when no route exists, and
`phasing_wait_time` returns `inf` when the geometry never closes — all
deliberately. Do not wrap these in a bare `except` or coerce them to a
plausible-looking default; in mission software a silent wrong answer is worse
than a loud failure.

## Manuscript

- Manuscript numbers flow from `src/you_only_live_twice/manuscript_variables.py`
  (metrics and scenario parameters) plus `manuscript/config.yaml` (identity
  only). Never hand-author a metric in prose; use `{{TOKEN}}` and keep the live
  cross-reference test green.
- Scenario parameters reach the manuscript as `{{SETUP_*}}` tokens derived from
  `scenario_descriptor()` — the same object the provenance hash covers. Never
  hand-copy a parameter out of `config.yaml` into prose.
- `references.bib` must contain only real, checkable publications. If you are
  not confident an entry is real, remove it rather than ship it.

## Lineage

- Do not reintroduce exemplar lineage strings. Verification grep:
  `rg -n "template[_]code_project"` (bracket-split so a doc cannot trip its own
  gate).
