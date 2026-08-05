---
title: "docs — VOLCANO documentation hub"
type: "docs_guide"
version: "0.2.0"
---

# docs (you_only_live_twice — VOLCANO)

Documentation for the *You Only Live Twice* (1967) BOND film package: seven
deterministic special-agent capabilities (orbital rendezvous, orbital capture
and phasing, concealed-lair detection, Bayesian hidden-base discovery,
infiltration routing, TDOA emitter localization, pattern-of-life analysis)
exposed through the frozen BOND-API `MissionProvider` protocol.

## What is in here

| File | Purpose | Read it when |
| --- | --- | --- |
| `README.md` | This index | First |
| `AGENTS.md` | Working procedure for agents: what is frozen, the order of operations for a change, and the traps specific to this package | Before making any change |
| `agent_instructions.md` | The hard operational constraints — scope, layering, determinism, manuscript token rules, lineage | Before making any change |
| `architecture.md` | Module-by-module description of `src/`, how the pieces compose through `scenario.py`, and how `mission.py` implements the frozen `MissionProvider` | When you need to know what a module actually computes |
| `testing_philosophy.md` | The no-mock / real-data / determinism doctrine as it applies to these seven capabilities, and what each kind of test proves | Before writing or judging a test |
| `_generated/COUNTS.md` | Live test and coverage counts from the enforced gate | When you need a measured number — never hardcode one in prose |

## Documentation that lives outside this directory

| Location | Holds |
| --- | --- |
| `../README.md` | Package overview, capability table, quick-start commands |
| `../AGENTS.md` | The layer contract and the verification gate |
| `../TODO.md` | Real remaining work and declared integration points |
| `../manuscript/README.md`, `../manuscript/AGENTS.md`, `../manuscript/SYNTAX.md` | The manuscript's own file inventory, token protocol and syntax reference |

## Ground rules in one paragraph

Scope is exactly this directory; the tree is local-only and is never pushed.
No mock framework anywhere — real data and real computation, fixed seed 1967.
Business logic lives in `src/`, `scripts/` are thin orchestrators. Every number
in the manuscript arrives as a `{{TOKEN}}` from
`src/you_only_live_twice/manuscript_variables.py`; none is hand-authored. The
enforced gate is `uv run pytest tests/ --cov=src --cov-fail-under=90` with
`ruff` and `mypy` green.

Start with `AGENTS.md`, then `agent_instructions.md`.
