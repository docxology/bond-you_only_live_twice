---
title: "docs — agent working guide for you_only_live_twice (VOLCANO)"
type: "agent_guide"
version: "0.2.0"
---

# AGENTS.md — working inside the VOLCANO package

How an agent should work in this package: what is safe to change, what is
frozen, the order of operations, and the traps specific to this tree. The
package-root `AGENTS.md` carries the layer contract and the verification gate;
this file is the *working procedure*.

## Orientation, in order

1. Read the package-root `README.md` — capability table and quick start.
2. Read `docs/architecture.md` — what each module computes and how
   `mission.py` maps onto the frozen protocol.
3. Read `docs/testing_philosophy.md` — what a test here is expected to prove.
4. Read `docs/agent_instructions.md` — the hard operational constraints.
5. Run the gate **before** changing anything, so you know whether a later
   failure is yours.

## Scope

Work only inside `projects/working/bond/you_only_live_twice/`. Do not touch a
sibling BOND package, the bond root files, or the template repo. This is a
local-only tree with no remote: commit here, never push.

## What is frozen and what is open

| Surface | Status |
| --- | --- |
| `MissionProvider.film`, `brief`, `recon`, `plan`, `execute`, `debrief` | **Frozen public shape.** `bond-cli`, the coordinator reconcile and the orchestrator consume these across packages. Deepen the bodies, never the signatures. |
| `register_gadgets()`, `FALLBACK_GADGETS` | **Frozen.** Gadget *entries* may be added; the registration mechanism may not change. |
| The pure domain modules | **Open.** Add modules, add functions, extend the math. |
| `scenario.solve_mission` results dict | **Additive only.** Adding a key is safe; removing or renaming one breaks the manuscript tokens and the debrief evidence lines at once. |
| Manuscript prose | Open — but every number must be a token. |

## The order of operations for a change

The dependency chain runs one way, so work it in this order or you will chase
your own tail:

```
domain module → its test → scenario.solve_mission → mission/debrief evidence
                                     ↓
                     manuscript_variables tokens → manuscript prose
                                     ↓
                          figures.py → docs → COUNTS.md
```

1. **Change the math** in a pure module under `src/you_only_live_twice/`.
2. **Test it** — closed-form anchor, injected-truth recovery, or a guaranteed
   inequality; plus the error branches.
3. **Wire it into `scenario.py`** if it produces a reported number. Add a named
   module-level constant for any new parameter and put that constant into
   `_scenario_descriptor()` — this is what keeps provenance and the setup
   tables honest. Note that adding a descriptor field changes `input_hash`,
   which is expected and fine.
4. **Add the token** in `manuscript_variables.generate_variables()`, then
   reference it in prose as `{{TOKEN}}`. Never type the number.
5. **Figures**: if you add one, add its filename to `FIGURE_FILENAMES` — the
   manuscript's figure count and the render script both read that tuple.
6. **Docs**: update `docs/architecture.md`'s module table and the root
   `README.md` capability table in the same commit as the code.
7. **Run the gate**, then refresh `docs/_generated/COUNTS.md` from the real
   output.

## Traps specific to this package

- **One shared ground truth.** `build_scenario()` derives `lair_site` from the
  argmax of the fused anomaly Z-map and feeds that *same* cell to the discovery
  scene, the infiltration goal and the emitter position. If you change the
  scene generator, the anomaly weights, or the fusion, that cell can move — and
  the capabilities will still all agree, which is the point. Do not hardcode a
  cell anywhere downstream.
- **Two different "effort" numbers.** `expected_discovery_effort` is the
  *realised* rank of a known true site; `posterior_expected_effort` is the
  posterior-weighted E[K] with no ground truth assumed. They are not
  interchangeable, and quoting the first as the second overstates what the
  search knows.
- **The infiltration reduction is a fraction.** `INFILTRATION_REDUCTION` is in
  [0, 1]; `INFILTRATION_REDUCTION_PCT` is the percentage. Pair the right one
  with a `%` sign.
- **`phasing_wait_time` can legitimately return `inf`** (co-orbital geometry
  that never closes). Anything consuming it must handle that, and
  `scenario.py` does.
- **`localize_tdoa` raises rather than returning a bad fix** on singular
  geometry or non-convergence. Do not wrap it in a bare `except` — a swallowed
  failure here produces a confident wrong position.
- **No wall-clock in a persisted artifact.** `Provenance.wall_time_s` is held
  at 0.0 and the manuscript generation date is a fixed string, deliberately.
- **`config.yaml` is identity only.** Its `mission:` block is an orientation
  aid; the authoritative scenario values live in `scenario.py` and reach prose
  as `{{SETUP_*}}` tokens. Never hand-copy a value out of the YAML into prose.

## Verification before you claim done

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run ruff check src/ scripts/ tests/ && uv run ruff format --check src/ scripts/ tests/
uv run mypy src/ scripts/
uv run python scripts/00_preflight.py     # protocol surface still intact
rg -n "template[_]code_project" .          # exemplar lineage must be zero
git status --short                          # clean after commit
```

Read the output. A command that was not run is not evidence, and an exit code
you did not look at is not a pass.
