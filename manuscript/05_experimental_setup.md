# Experimental Setup

The scenario is fixed in `src/you_only_live_twice/scenario.py`, which exports
every input as a named constant and assembles them into one JSON descriptor.
That descriptor is simultaneously (a) the object the provenance `input_hash` is
taken over and (b) the source of the parameter tokens in the tables below, so a
parameter reported here cannot drift from the parameter actually simulated.
Paper identity is declared in `manuscript/config.yaml`; all derived values are
computed by `src/you_only_live_twice/manuscript_variables.py`.

## Mission identity

| Parameter | Value |
| --- | --- |
| Random seed | {{SCENARIO_SEED}} |
| Provenance input hash (16 hex) | {{MISSION_INPUT_HASH}} |

## Orbital geometry

| Parameter | Chaser | Target |
| --- | --- | --- |
| Altitude (km) | {{SETUP_CHASER_ALT_KM}} | {{SETUP_TARGET_ALT_KM}} |
| Inclination (°) | {{SETUP_CHASER_INC_DEG}} | {{SETUP_TARGET_INC_DEG}} |
| RAAN (°) | {{SETUP_CHASER_RAAN_DEG}} | {{SETUP_TARGET_RAAN_DEG}} |
| Initial phase (rad) | {{SETUP_CHASER_PHASE_RAD}} | {{SETUP_TARGET_PHASE_RAD}} |

## Search envelopes

| Parameter | Value |
| --- | --- |
| Rendezvous horizon / step (s) | {{SETUP_RDV_HORIZON_S}} / {{SETUP_RDV_STEP_S}} |
| Rendezvous max range (km) | {{SETUP_RDV_MAX_RANGE_KM}} |
| Rendezvous min elevation (°) | {{SETUP_RDV_MIN_ELEV_DEG}} |
| Capture max range (km) | {{SETUP_CAPTURE_MAX_RANGE_KM}} |
| Capture max relative speed (m/s) | {{SETUP_CAPTURE_MAX_SPEED_M_S}} |
| Capture step (s) | {{SETUP_CAPTURE_STEP_S}} |

## Scene, sensors and cost model

| Parameter | Value |
| --- | --- |
| Volcano grid (cells per side) | {{SETUP_GRID_CELLS}} |
| Cone radius (cells) / height (m) | {{SETUP_CONE_RADIUS_CELLS}} / {{SETUP_CONE_HEIGHT_M}} |
| Lair thermal excess (K) | {{SETUP_LAIR_HEAT_K}} |
| Activity rate (events/h) over horizon (h) | {{SETUP_ACTIVITY_RATE_PER_H}} over {{SETUP_ACTIVITY_HOURS}} |
| Discovery cue mean $\mu$ / prior weight $\beta$ | {{SETUP_DISCOVERY_MU_HOT}} / {{SETUP_DISCOVERY_BETA}} |
| Discovery RF source power | {{SETUP_DISCOVERY_RF_POWER}} |
| Infiltration weights (slope / thermal / guard) | {{SETUP_INFIL_SLOPE_WEIGHT}} / {{SETUP_INFIL_THERMAL_WEIGHT}} / {{SETUP_INFIL_GUARD_WEIGHT}} |
| TDOA sensor ring radius (m) / count | {{SETUP_EMITTER_RING_RADIUS_M}} / {{SETUP_EMITTER_SENSORS}} |
| TDOA receiver timing jitter $\sigma_t$ (ns, 1σ) | {{SETUP_EMITTER_TIME_NOISE_NS}} |
| TDOA error-envelope max jitter (ns) / realizations per level | {{SETUP_EMITTER_SWEEP_MAX_NS}} / {{SETUP_EMITTER_SWEEP_REALIZATIONS}} |
| Injected lair footprint (cells) | {{LAIR_FOOTPRINT_CELLS}} |

## Rendering pipeline

The manuscript is rendered entirely from the deterministic scenario:

1. `scripts/z_generate_manuscript_variables.py` writes
   `output/data/manuscript_variables.json` ({{BOND_NUM_DATACLASSES}} protocol
   dataclasses, {{BOND_NUM_PROVIDER_METHODS}} provider methods).
2. `scripts/render_figures.py` writes the {{NUM_FIGURES}} figures under
   `output/figures/`.
3. Prose substitutes every token reference with its computed value, so numbers stay in lock-step with the scenario.

## Software environment

- Package version {{BOND_VERSION}} (`{{BOND_IDENTITY}}`, film
  {{BOND_FILM_YEAR}}).
- Python {{PYTHON_VERSION}} on {{SYSTEM}}; numpy, matplotlib, pyyaml, and the
  frozen `bond-api` protocol.
- Generated {{GENERATION_TIMESTAMP}}.

## Test gate

The suite runs `pytest` with `--cov=src --cov-fail-under=90` (line **and**
branch). Live test counts and the achieved coverage percentage come from the
gate run itself (recorded locally under the gitignored `docs/_generated/`), not
hardcoded here.
