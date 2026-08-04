# you_only_live_twice — VOLCANO

**You Only Live Twice (1967)** · mission codename **VOLCANO**. Special-agent
mission software in the PROJECT BOND suite: a pure, deterministic computation
core with three analytical capabilities, exposed to the frozen BOND-API
`MissionProvider` protocol.

## Capabilities

| Capability | Module | Concept |
| --- | --- | --- |
| Rendezvous / intercept windows | `rendezvous_windows.py` | two-body orbital mechanics: propagate circular orbits, find contiguous windows, Hohmann delta-v budget |
| Concealed-lair detection | `terrain_anomaly.py` | thermal + terrain anomaly scoring (volcano-camouflage case) |
| Pattern of life | `pattern_of_life.py` | weekly activity histogram, daily profile, dominant period, peak windows, tempo |

## Layout

```
src/you_only_live_twice/
  rendezvous_windows.py  terrain_anomaly.py  pattern_of_life.py  scenario.py
  mission.py             figures.py          manuscript_variables.py
scripts/
  run_mission.py  00_preflight.py  render_figures.py  z_generate_manuscript_variables.py
manuscript/  docs/  tests/
```

The domain core is infrastructure-free and importable without BOND-API; only
`mission.py` (and `figures.py` / `manuscript_variables.py`) depend on the
frozen protocol.

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

Deterministic: fixed seed, no wall-clock in persisted artifacts, real
computation only (no mocks). Local-only tree — never pushed.

See `AGENTS.md` for the layer contract and `TODO.md` for integration points.
