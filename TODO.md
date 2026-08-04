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

## Not planned

- Any remote / push (local-only tree).
- Mocks, untracked randomness, or wall-clock in persisted artifacts.
