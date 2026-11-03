# src/ — the VOLCANO pure core, one adapter, and the derivation layer

`src/you_only_live_twice/`, the installable package. The boundary between the three bands is
enforced, not stylistic.

## Layout

| Module | What it does |
| --- | --- |
| `rendezvous_windows.py` | Circular two-body propagation, line-of-sight range and elevation, contiguous window search, coplanar Hohmann delta-v |
| `orbital_capture.py` | Capture envelope (range + relative speed), velocity-matching burn, phasing lead angle and wait time |
| `terrain_anomaly.py` | Gaussian background modelling, standardized-residual anomaly scoring, weighted fusion, connected-component lair detection |
| `hidden_base_discovery.py` | Bayesian cue fusion (thermal/terrain/RF), posterior map, deterministic search order, effort and discovery curve |
| `infiltration_planning.py` | Slope/thermal/guard cost fields, A* route against a same-space greedy baseline that also reaches the goal |
| `emitter_localization.py` | TDOA hyperbolic multilateration via Gauss–Newton |
| `pattern_of_life.py` | Poisson diurnal activity model, histograms, autocorrelation periodicity, peak windows, tempo, duty cycle |
| `scenario.py` | The single source: `solve_mission` plus the scenario descriptor |
| `mission.py` | Thin BOND-API `MissionProvider` adapter and gadget registration |
| `figures.py`, `manuscript_variables.py` | Derivation layer — no domain logic; only `manuscript_variables.py` reads protocol identity |

## Rules

- **The eight domain modules import the standard library and `numpy` only, and must import without
  BOND-API.** That is what makes the core testable on its own.
- **`scenario.solve_mission` is the single source of every outcome.** Both `mission.execute` and the
  manuscript token generator consume it, so the prose and the numbers cannot disagree. Do not add a
  second path to a result.
- **Scenario inputs follow the same discipline.** `scenario.scenario_descriptor()` is at once the
  object the provenance `input_hash` covers and the source of the `{{SETUP_*}}` tokens, so a reported
  parameter cannot drift from the simulated one. A new parameter is a named module-level constant
  placed in the descriptor.
- **Determinism**: fixed seeds, no untracked RNG, no wall-clock in any persisted artifact.
- **`mission.py` is the only module that registers gadgets** (the rendezvous solver, intercept budget,
  capture solver, lair detector, discovery engine, search ranker, route planner, emitter locator,
  pattern analyzer) with the `GadgetRegistry`.
- **Type hints and docstrings throughout**; `ruff check`, `ruff format` and `mypy` are green here.
