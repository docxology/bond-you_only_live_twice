# tests/ — real data and computation, no mock framework

`conftest.py` and eleven `test_*.py` modules: one per domain module, plus the smoke and integration
checks.

## What each part holds

| Test module | Subject |
| --- | --- |
| `test_rendezvous_windows.py`, `test_orbital_capture.py` | The orbital modules |
| `test_terrain_anomaly.py`, `test_hidden_base_discovery.py` | Detection and the Bayesian search |
| `test_infiltration_planning.py`, `test_emitter_localization.py`, `test_pattern_of_life.py` | Routing, multilateration, activity |
| `test_figures.py`, `test_manuscript_variables.py` | The derivation layer |
| `test_scripts_smoke.py` | Each script still runs |
| `test_mission.py` | The BOND-API adapter — the integration surface |

## Rules

- **No mock framework.** No `MagicMock`, `mocker.patch` or `unittest.mock` anywhere. Real data and
  real computation; where a stand-in is needed it implements the real protocol.
- **The gate is `uv run pytest tests/ --cov=src --cov-fail-under=90`** — 90% floor, line **and**
  branch.
- **A test here must prove something**, not that a call returned. A validation branch that no test
  can reach is either given the test that fires it, in the same pass, or removed.
- **Determinism is checked, not assumed**: fixed seeds, and no wall-clock in a persisted artifact.
- **The manuscript tokens are tested against the mission's own output**, so a token cannot drift from
  the value `scenario.solve_mission` produced.
- **`test_mission.py` is the module that needs the recorded `bond-api` copy under `vendor/`**; the
  domain modules' tests run without it.
- **If the suite cannot import `bond_api` under `uv run pytest`,** run it as
  `uv run python -m pytest`: a stale console script left in `.venv/bin` by an earlier interpreter
  outlives that interpreter. Gate through the interpreter.
