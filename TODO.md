# TODO — you_only_live_twice (VOLCANO)

Forward-only backlog for the *You Only Live Twice* (1967) film package.

## Built (phase-2)

- **Pure domain core** (`src/you_only_live_twice/`):
  - `rendezvous_windows.py` — circular orbital propagation, line-of-sight range
    & elevation, contiguous rendezvous-window search, coplanar Hohmann
    delta-v / transfer-time budget.
  - `terrain_anomaly.py` — volcano-camouflage scene generator, Gaussian
    background modelling, standardized-residual thermal (one-tailed) + terrain
    (magnitude) anomaly scoring, weighted fusion, connected-component
    concealed-lair detection.
  - `pattern_of_life.py` — deterministic diurnal-rate activity schedule,
    weekly/daily histograms, autocorrelation dominant period, peak windows,
    tempo classification, duty cycle.
  - `scenario.py` — the single deterministic mission scenario + provenance
    input hash.
- **Protocol adapter** (`mission.py`): implements the frozen `bond_api`
  `MissionProvider` (slug `you_only_live_twice`, codename VOLCANO), registers
  four gadgets with the `GadgetRegistry`.
- **Derivation**: `figures.py` (3 deterministic PNGs), `manuscript_variables.py`
  (token hydration from `manuscript/config.yaml` + scenario).
- **Thin scripts**: `run_mission.py` (per-phase CLI),
  `00_preflight.py`, `render_figures.py`, `z_generate_manuscript_variables.py`.
- **Tests**: per-concept real-data tests, mission/protocol test, manuscript
  cross-reference test, scripts smoke test — zero mocks.

## Built (phase-4 · deep improvement)

- **Four new pure-domain modules**:
  - `orbital_capture.py` — capture envelope (range + relative-speed), velocity-
    matching grapple burn, phasing lead angle & wait time (classic phasing
    problem).
  - `hidden_base_discovery.py` — Bayesian naive-Bayes cue fusion
    (thermal/terrain/RF Gaussian likelihood ratios), posterior map,
    deterministic search order, expected effort, discovery curve.
  - `infiltration_planning.py` — slope/thermal/guard line-of-sight cost fields,
    deterministic 4-connected A* vs a same-space greedy baseline (non-negative
    reduction proven).
  - `emitter_localization.py` — TDOA hyperbolic multilateration via
    Gauss–Newton (converges to metre accuracy noise-free).
- **Deepened internals**: `mission.py` now executes all seven capabilities via
  the single source `scenario.solve_mission()`; registers nine gadgets;
  brief/plan extended to six objectives / seven steps (protocol public shape
  unchanged — `brief/recon/plan/execute/debrief` + `register_gadgets`).
- **Derivation**: `figures.py` now renders six deterministic PNGs (added
  capture, discovery posterior, infiltration route); `manuscript_variables.py`
  hydrates 49 `{{TOKEN}}`s, all from the single analysis source.
- **Manuscript** updated: methodology (7 sections), results (7 subsections +
  6 figures), abstract, conclusion; references.bib extended with Bate/Mueller/
  White, Cormen et al., Pearl, Skolnik. Scripts `render_figures.py` and
  `run_mission.py` extended; preflight verifies 6 objectives.

## Declared integration points

- **`bond-utilities.mission_io.record_provenance_outcome`** — once the shared
  provenance helper ships as an importable dependency, mission outcomes should
  delegate persistence to it instead of embedding provenance inline.
  Acceptance: `uv add bond-utilities` + swap in `mission.py` with no behaviour
  change.
- **Perturbation-aware propagator** — extend `rendezvous_windows` with J2/drag
  for realistic low-Earth intercepts; keep the current two-body solver as the
  deterministic baseline.
- **Spline-refined window edges** — once a window is bracketed by the grid
  search, refine `start_s`/`end_s` to sub-step precision.
- **Dynamic infiltration** — extend `infiltration_planning` to moving guard
  posts / replanning; keep the static A* as the deterministic baseline.

## Not planned

- Any remote / push (local-only tree).
- Mocks, untracked randomness, or wall-clock in persisted artifacts.
