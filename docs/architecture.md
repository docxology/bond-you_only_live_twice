# Architecture — you_only_live_twice (VOLCANO)

The package is layered so the scientific core stays pure and the protocol stays
thin.

```
src/you_only_live_twice/
  rendezvous_windows.py   pure: orbital mechanics (windows + Hohmann delta-v)
  terrain_anomaly.py      pure: thermal/terrain anomaly scoring + lair detection
  pattern_of_life.py      pure: weekly activity / pattern-of-life analysis
  scenario.py             pure: deterministic shared scenario + input hash
  figures.py              renders the three report figures (Agg, deterministic)
  manuscript_variables.py hydrates manuscript {{TOKEN}}s from config + scenario
  mission.py              thin BOND-API MissionProvider adapter + gadget registry
scripts/
  run_mission.py          per-phase CLI (brief/recon/plan/execute/debrief)
  00_preflight.py         protocol-surface + provider + gadget checks
  render_figures.py       regenerates output/figures/*
  z_generate_manuscript_variables.py  writes output/data/manuscript_variables.json
```

## Boundaries

- **Pure core** (`rendezvous_windows`, `terrain_anomaly`, `pattern_of_life`,
  `scenario`) imports only stdlib + numpy. No `bond_api`, no `infrastructure`.
- **Protocol adapter** (`mission.py`) is the only module implementing the
  BOND-API `MissionProvider`; it never computes, it delegates to the core.
- **Derivation** (`figures.py`, `manuscript_variables.py`) consume the scenario
  and its outputs; they contain no domain logic.

This makes the core independently testable and lets the orchestrator discover
VOLCANO by slug via `bond_api.discovery` (`you_only_live_twice.mission`).
