# you_only_live_twice — VOLCANO

**You Only Live Twice (1967)** · mission codename **VOLCANO**. Special-agent
mission software in the PROJECT BOND suite: a pure, deterministic computation
core with seven analytical capabilities, exposed to the frozen BOND-API
`MissionProvider` protocol.

## Capabilities

### Film concept → software payload

*You Only Live Twice* turns on two technical ideas: an adversary platform that
**captures a spacecraft out of orbit**, and a **base concealed inside a
volcano**. This package implements both as real mathematics, plus the
intelligence work that connects them — you cannot strike a base you have not
found, routed into, and learned the rhythm of.

| Capability | Module | Concept |
| --- | --- | --- |
| Rendezvous / intercept windows | `rendezvous_windows.py` | Two-body orbital mechanics: propagate circular orbits to ECI states, score line-of-sight range and elevation, find contiguous windows, Hohmann delta-v budget |
| Orbital capture & phasing | `orbital_capture.py` | Capture envelope (range **and** relative speed), velocity-matching grapple burn, phasing lead angle and wait time |
| Concealed-lair detection | `terrain_anomaly.py` | Standardized-residual thermal (one-tailed) and terrain (magnitude) anomaly scoring against a smoothed background, fused and connected-component labelled |
| Hidden-base discovery | `hidden_base_discovery.py` | Bayesian cue fusion (thermal / terrain / RF Gaussian likelihood ratios over a terrain-weighted prior), posterior map, deterministic search order, discovery curve, realised and posterior-expected search effort |
| Infiltration planning | `infiltration_planning.py` | Slope / thermal / guard-line-of-sight cost fields with a lava mask, deterministic 4-connected A* against a same-space greedy baseline |
| Emitter localization | `emitter_localization.py` | TDOA hyperbolic multilateration by Taylor-series (Gauss–Newton) estimation, plus the receiver-side seconds→metres conversion |
| Pattern of life | `pattern_of_life.py` | Inhomogeneous-Poisson activity, weekly / daily histograms, autocorrelation dominant period, peak operating windows, tempo, duty cycle |

Four further modules bind the above into a package:

| Module | Role |
| --- | --- |
| `scenario.py` | The deterministic mission: `build_scenario()` assembles every input from named constants and fixed seeds, `solve_mission()` runs all seven capabilities, `scenario_descriptor()` / `scenario_input_hash()` provide provenance |
| `mission.py` | The thin BOND-API `MissionProvider` adapter and the gadget registration |
| `figures.py`, `manuscript_variables.py` | Derivation only: six deterministic PNGs, and the manuscript `{{TOKEN}}` map |

## MissionProvider surface

`mission.py` exposes the frozen BOND-API protocol; the orchestrator discovers
this package by slug and drives it without knowing any internals:

```python
from you_only_live_twice.mission import MissionProvider, register_gadgets

p = MissionProvider()
p.film                       # "you_only_live_twice"  (discovery slug, codename VOLCANO)
brief    = p.brief()         # MissionBrief: 6 objectives, 4 assets, 2 constraints
report   = p.recon(request)  # ReconReport: findings
plan     = p.plan(brief)     # MissionPlan: 7 steps
outcome  = p.execute(plan)   # MissionOutcome: all 7 capability results + Provenance
debrief  = p.debrief(outcome)# Debrief: lessons + evidence lines derived from results
register_gadgets(registry)   # 9 gadgets: rendezvous_solver, intercept_budget,
                             # capture_solver, lair_detector, discovery_engine,
                             # search_ranker, route_planner, emitter_locator,
                             # pattern_analyzer
```

`FALLBACK_GADGETS` is a pre-populated registry for scripts and tests. This
surface is frozen across the BOND fleet — deepen inside the package, never
change its shape.

## Layout

```
src/you_only_live_twice/
  rendezvous_windows.py  orbital_capture.py  terrain_anomaly.py
  hidden_base_discovery.py  infiltration_planning.py  emitter_localization.py
  pattern_of_life.py  scenario.py  mission.py  figures.py  manuscript_variables.py
scripts/
  run_mission.py  00_preflight.py  render_figures.py  z_generate_manuscript_variables.py
manuscript/  docs/  tests/
```

The domain core is infrastructure-free and importable without BOND-API; only
`mission.py` (and `figures.py` / `manuscript_variables.py`) depend on the
frozen protocol. All computation flows through a single analysis source
(`scenario.solve_mission`) shared by the adapter and the manuscript tokens, so
the outcome the coordinator sees and the numbers the manuscript prints cannot
disagree.

## Quick start

```bash
cd projects/working/bond/you_only_live_twice
uv sync --extra dev

# Run the whole mission through the protocol:
uv run python scripts/run_mission.py

# Per-phase CLI:
uv run python scripts/run_mission.py recon
uv run python scripts/run_mission.py execute

# Regenerate artifacts:
uv run python scripts/z_generate_manuscript_variables.py
uv run python scripts/render_figures.py

# Quality gate:
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/
uv run mypy src/ scripts/
```

The enforced floor is **90 % line and branch coverage** on `src/`, with zero
failures and zero skips. Measured counts are recorded in
`docs/_generated/COUNTS.md` rather than quoted in prose, so no figure here can
go stale.

Deterministic: fixed seed 1967, no wall-clock in persisted artifacts, real
computation only (no mocks). Local-only tree — never pushed.

## Documentation

| Read | For |
| --- | --- |
| `AGENTS.md` | The layer contract and the verification gate |
| `docs/AGENTS.md` | Working procedure: what is frozen, the order of operations, package-specific traps |
| `docs/agent_instructions.md` | The hard operational rules |
| `docs/architecture.md` | Module-by-module architecture and the `MissionProvider` mapping |
| `docs/testing_philosophy.md` | The no-mock / real-data / determinism doctrine as it applies here |
| `manuscript/` | The paper, its `{{TOKEN}}` protocol and its bibliography |
| `TODO.md` | Real remaining work and declared integration points |
