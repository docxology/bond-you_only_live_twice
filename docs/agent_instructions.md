# Agent Instructions — you_only_live_twice (VOLCANO)

Operational constraints for agents editing this package. Read this first.

## Scope and safety

- Work **only** inside `projects/working/bond/you_only_live_twice/`. Do not
  touch sibling BOND packages, bond root files, or the template repo.
- This is a **local-only** working tree. There is no remote; never push.
- Commit path-scoped with `git add -A` **inside this repo only**.

## Layering

- `src/you_only_live_twice/rendezvous_windows.py`, `terrain_anomaly.py`,
  `pattern_of_life.py`, `scenario.py` are the **pure domain core**:
  infrastructure-free and importable **without** BOND-API.
- `src/you_only_live_twice/mission.py` is the **thin adapter** between the core
  and the frozen `bond_api` protocol (the `MissionProvider`).
- `src/you_only_live_twice/figures.py` and `manuscript_variables.py` depend on
  the protocol / scenario but hold no mission logic.
- `scripts/` contains thin orchestrators only — business logic belongs in `src/`.

Do not let the domain core import `bond_api`, `infrastructure`, or anything
outside its own module.

## Determinism & testing

- No mock framework (no `MagicMock` / `mocker.patch` / `unittest.mock`). Real
  computation + data only.
- Fixed seeds everywhere; no untracked RNG; no wall-clock in persisted
  artifacts.
- Gate: `uv run pytest tests/ --cov=src --cov-fail-under=90` (line **and**
  branch), plus `ruff check` / `ruff format` and `mypy` green on `src/` and
  `scripts/`.

## Manuscript

- Manuscript numbers flow from `manuscript/config.yaml` +
  `src/you_only_live_twice/manuscript_variables.py`. Never hand-author metrics
  in prose; use `{{TOKEN}}` and keep the live cross-reference test green.

## Lineage

- Do not reintroduce exemplar lineage strings. Verification grep:
  `rg -n "template[_]code_project"` (bracket-split so a doc cannot trip its own
  gate).
