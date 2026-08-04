# Experimental Setup

The scenario is fixed and declared in `manuscript/config.yaml`. All derived
values are computed by `src/you_only_live_twice/manuscript_variables.py` and
injected as tokens.

## Scenario parameters

| Parameter | Value |
| --- | --- |
| Random seed | {{SCENARIO_SEED}} |
| Provenance input hash (16 hex) | {{MISSION_INPUT_HASH}} |
| Chaser altitude | 550 km (inclination 98.2°, RAAN 45.0°) |
| Target altitude | 800 km (inclination 98.2°, RAAN 45.5°, phase 1.9 rad) |
| Rendezvous window horizon | 86 400 s (one day) |
| Volcano scene | 64×64 grid, cone radius 20 cells, height 2000 m |
| Activity schedule | base rate 4 events/h over 168 h (seed-derived) |

## Rendering pipeline

The manuscript is rendered entirely from the deterministic scenario:

1. `scripts/z_generate_manuscript_variables.py` writes
   `output/data/manuscript_variables.json` ({{BOND_NUM_DATACLASSES}} protocol
   dataclasses, {{BOND_NUM_PROVIDER_METHODS}} provider methods).
2. `scripts/render_figures.py` writes the three figures under
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
branch). Live test counts and the achieved coverage percentage are tracked in
`docs/_generated/COUNTS.md`, not hardcoded here.
