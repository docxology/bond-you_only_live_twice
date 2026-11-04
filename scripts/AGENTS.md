# scripts/ — preflight, the mission driver, the figures and the token generator

`00_preflight.py`, `run_mission.py`, `render_figures.py`, `z_generate_manuscript_variables.py`.

## Rules

- **Thin orchestrators only.** Each script bootstraps `sys.path` and delegates to
  `src/you_only_live_twice/`. No mathematics that determines an output belongs here.
- **`00_preflight.py` verifies the VOLCANO provider satisfies the frozen BOND-API surface** and is
  part of the gate; run it before the mission.
- **`z_generate_manuscript_variables.py` runs LAST.** It derives every `{{TOKEN}}` from the mission's
  own measured output; run first, it would publish tokens from stale or absent measurements.
- **`render_figures.py` writes deterministic figures** into `output/figures/`; same inputs, same
  bytes. Change a generator, never the rendered file.
- **Exit codes are the report.** A phase that failed exits non-zero — never describe it as done.
- **Live counts are measured, never written here.** Measured totals and coverage live under the
  git-ignored `docs/_generated/`; do not hardcode them into prose.
- **Scope is this repository.** Never write into sibling BOND packages, the suite root, or the
  template repository.
- `run_mission.py` and `00_preflight.py` need the recorded `bond-api` copy under `vendor/`; the pure
  core does not.
