# Architecture — you_only_live_twice (VOLCANO)

How the VOLCANO package is put together: what each module in `src/` computes,
how the pieces compose into one mission, and how `mission.py` satisfies the
frozen BOND-API `MissionProvider` contract.

## The one-sentence shape

Seven independent pure-math modules compute the film's concepts; `scenario.py`
binds them into a single deterministic mission; `mission.py` adapts that one
result to the BOND protocol; `figures.py` and `manuscript_variables.py` derive
the report artifacts from the *same* result, so the outcome the coordinator
sees and the numbers the manuscript prints cannot disagree.

```
    ┌──────────── pure domain core (stdlib + numpy only) ────────────┐
    │ rendezvous_windows   orbital_capture      terrain_anomaly      │
    │ hidden_base_discovery  infiltration_planning                   │
    │ emitter_localization   pattern_of_life                         │
    └───────────────────────────┬───────────────────────────────────-┘
                                │ (imported by)
                          scenario.py
            build_scenario()  →  solve_mission()   ← SINGLE ANALYSIS SOURCE
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
   mission.py              figures.py         manuscript_variables.py
 (BOND MissionProvider)  (8 deterministic PNGs)  ({{TOKEN}} hydration)
        │                       │                        │
        └────────── scripts/ (thin orchestrators only) ───┘
```

## Module by module

### Pure domain core

These import only the standard library and numpy. None imports `bond_api`,
`infrastructure`, matplotlib, or anything under `scripts/`. Each is
independently testable and importable without the protocol.

| Module | What it computes |
| --- | --- |
| `rendezvous_windows.py` | Circular two-body orbital mechanics. `CircularOrbit` (built from altitude / inclination / RAAN / initial phase), `mean_motion`, `circular_state` (perifocal → ECI), `range_and_elevation` (slant range plus elevation above the chaser's local horizontal), `find_rendezvous_windows` (contiguous intervals satisfying a range **and** an elevation constraint, by deterministic time-grid search), `hohmann_transfer` (two-impulse coplanar Δv budget and transfer time). |
| `orbital_capture.py` | The capture problem on top of that propagation core. `relative_state` / `relative_speed` (ECI relative position and velocity), `capture_windows` (intervals where the capsule is simultaneously inside the grapple range **and** slow enough — a physically different condition from line-of-sight rendezvous), `velocity_matching_budget` (the grapple burn equals the relative-speed magnitude), `phasing_lead_angle` (λ = (π − n_t·T_t) mod 2π) and `phasing_wait_time` (first non-negative solution of φ(t) ≡ λ, returning `inf` when the geometry never changes). Imports `rendezvous_windows` for the shared propagator. |
| `terrain_anomaly.py` | Concealed-lair detection. `build_volcano_scene` (fixed-seed Gaussian cone, a flat lair shelf cut into the flank, thermal lapse rate plus a noise floor), `thermal_anomaly_mask` (one-tailed standardized residual against a Gaussian-smoothed background — we look for *excess* heat), `terrain_anomaly_mask` (magnitude residual, because a lair may be a raised shelf *or* a cut depression), weighted fusion, and `detect_concealed_lair` (connected-component labelling of the thresholded fused map, ranked by peak fused score). |
| `hidden_base_discovery.py` | Bayesian search over candidate sites. `terrain_weighted_priors` (P(c) ∝ 1 + β·max(0, z_terrain)), `gaussian_likelihood_ratio` (LR(z) = exp(μz/σ²), so a neutral cell maps to 1), `fuse_posteriors` (normalized product of prior and cue LRs), `rank_search_order` (descending posterior, ties broken by row then column so the plan is byte-reproducible), `discovery_probability_curve` (cumulative find probability), `expected_discovery_effort` (the **realised** rank of a known true site) and `posterior_expected_effort` (the **posterior-weighted** E[K] = Σ k·P(c_k), which assumes no ground truth). `build_discovery_scene` assembles priors plus thermal / terrain / RF cues into the posterior. |
| `infiltration_planning.py` | Route planning under detection risk. `slope_magnitude` (gradient hypotenuse), `thermal_exposure_field` (positive thermal-anomaly risk, normalized), `guard_exposure_field` (per-cell count of guard posts with an unoccluded sight line, via a digital-elevation line-of-sight test), `combined_cost_field` (1 + weighted slope / thermal / guard, with an impassable-lava mask at ∞), `astar_path` (4-connected A* with an admissible Manhattan heuristic and an insertion counter for deterministic tie-breaking), `greedy_baseline_path` (a greedy depth-first walk over the *same* search space that retraces out of dead ends, so it always reaches the goal and its cost really is an upper bound on A*'s), and `plan_infiltration` (the full route report including the cost reduction). |
| `emitter_localization.py` | Passive RF geolocation. `build_sensor_posts` (equally spaced sensor ring), `tdoa_measurements` (exact range differences dᵢ = ‖e − sᵢ‖ − ‖e − s₀‖), `time_differences_to_ranges` (the one place the speed of light is used — converting receiver seconds to metres), `localize_tdoa` (Taylor-series / Gauss–Newton on the normal equations; raises on singular geometry or non-convergence rather than returning a silent bad fix), `localization_error`, and `tdoa_error_sweep` (a deterministic mean-error vs timing-jitter accuracy envelope over fixed-seed realizations). |
| `pattern_of_life.py` | Base rhythm analysis. `build_weekly_activity_schedule` (inhomogeneous Poisson events by rejection sampling against a two-peak diurnal rate envelope), `hourly_histogram` (7×24), `daily_activity_profile` (mean over days), dominant-period detection by normalized autocorrelation, `peak_activity_windows` (contiguous hours above a percentile), tempo classification and duty cycle. `pattern_summary` returns the whole report. |

### Composition layer

`scenario.py` is the **single analysis source**, in two halves:

- `build_scenario()` assembles every *input* — the two orbits, the volcano
  scene, the week of activity, the thermal / terrain Z-maps, the discovery
  scene, the infiltration geometry, the emitter sensor ring — from named
  module-level constants and fixed-seed generators. It also fixes the one
  *shared* ground truth — and keeps it strictly separate from any estimate.
  `lair_site` and `lair_footprint` are the injected lair's centre and carved
  extent, set by the scene generator's geometry (cone centre plus
  `lair_offset_cells`) before any anomaly map exists; the discovery scene's
  `true_cell`, the RF cue's source, the infiltration goal and the emitter
  position all use that injected site, so the capabilities describe one base.
  `detected_site` — the argmax of the fused anomaly Z-maps — is the detector's
  *answer*, carried alongside under its own name. It is a different cell, and
  `detector_offset_m` reports the gap. Earlier versions used the argmax as the
  ground truth, which made "the posterior finds the true base" an identity
  rather than a measurement; do not reintroduce that.
- `solve_mission(scenario)` runs all seven capabilities and returns one results
  dict.

`scenario_descriptor()` is the JSON-serializable description of every input.
It is simultaneously the object `scenario_input_hash()` fingerprints for
provenance **and** the source of the manuscript's `{{SETUP_*}}` tokens — one
object, so a reported parameter cannot drift from the simulated one.

### Derivation layer

- `figures.py` — eight deterministic PNGs under `output/figures/`, enumerated by
  `FIGURE_FILENAMES` (the manuscript's figure count derives from that tuple),
  including the emitter sensor-ring/hyperbola plot and the emitter
  error-vs-jitter envelope plot.
  Forces the Agg backend at import time.
- `manuscript_variables.py` — hydrates the full `{{TOKEN}}` map from
  `manuscript/config.yaml` (identity only) plus `solve_mission` and
  `scenario_descriptor` (every number). Nothing numeric is hand-authored.

## How `mission.py` implements the frozen `MissionProvider`

`mission.py` is an adapter: it computes nothing itself, it translates. The
BOND-API protocol is frozen — the phase methods and their dataclass signatures
are consumed by `bond-cli`, the coordinator's reconcile pass and the
orchestrator across all packages, so their public shape must not change.

| Protocol member | VOLCANO implementation |
| --- | --- |
| `film` (class attribute) | `"you_only_live_twice"` — the discovery slug. The orchestrator finds this package by importing `you_only_live_twice.mission` and reading this attribute. |
| `brief() -> MissionBrief` | Declares codename `VOLCANO`, six objectives (rendezvous, capture, lair detection, base localization, infiltration, pattern of life), four `Asset`s (orbital geometry, imagery, activity schedule, TDOA sensors) and two `Constraint`s (determinism, no exemplar lineage). Pure declaration — no computation. |
| `recon(ReconRequest) -> ReconReport` | Returns `Finding`s echoing the caller's goal plus what the mission actually has available: orbits known and phasing solvable, a thermal + terrain scene present, passive sensors bracketing the field, one week of activity, determinism required. |
| `plan(MissionBrief) -> MissionPlan` | Seven `Step`s — `rendezvous`, `capture`, `lair`, `discovery`, `infiltration`, `emitter`, `pattern` — each naming its action and carrying the objective (or asset) it serves. The six-objectives / seven-steps asymmetry is deliberate: emitter localization serves the same objective as discovery. |
| `execute(MissionPlan) -> MissionOutcome` | Calls `build_scenario()` then `solve_mission()`, returning the full results dict plus `steps_completed` and `seed`, wrapped with a `Provenance` carrying the package version, the seed, the scenario `input_hash`, and `wall_time_s = 0.0` (no wall-clock in a persisted artifact). |
| `debrief(MissionOutcome) -> Debrief` | Six standing lessons plus evidence lines derived from the computed results by `_evidence_notes`, so the debrief text moves when the numbers move. |
| `register_gadgets(GadgetRegistry)` | Registers nine named callables from the pure core: `rendezvous_solver`, `intercept_budget`, `capture_solver`, `lair_detector`, `discovery_engine`, `search_ranker`, `route_planner`, `emitter_locator`, `pattern_analyzer`. The module also exposes `FALLBACK_GADGETS`, a pre-populated registry for scripts and tests. |

**Stability rule.** Deepen *inside* the package — add modules, enrich the
`solve_mission` results, add gadgets. Never rename or re-signature the phase
methods, `film`, `register_gadgets` or `FALLBACK_GADGETS`, and never make a
phase method raise on the happy path; cross-package discovery depends on all of
it. `scripts/00_preflight.py` is the local check that the surface still holds.

## Dependency rules

Enforced by review and by the layering above, not by an import hook:

- The pure core must never import `bond_api`, `infrastructure`, matplotlib, or
  anything under `scripts/`.
- Only `mission.py`, `figures.py` and `manuscript_variables.py` may touch
  `bond_api` (the latter two only for `protocol_surface`).
- `scripts/` are thin orchestrators: argv shaping, I/O, printing paths. If a
  script starts computing, the computation belongs in `src/`.
- Per the BOND layer topology this package may depend on `bond-api` and
  `bond-utilities` only — never on another film package, and never on the
  coordinator or the orchestrator.
