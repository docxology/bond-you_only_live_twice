---
name: you-only-live-twice
description: Code-centric optimization research exemplar — gradient descent, convergence analysis, automated figures, dashboard, and publication-quality PDF.
version: 0.1.0
author: docxology
license: MIT
tags: [exemplar, code, optimization, thin-orchestrator]
---

# you-only-live-twice

Project-scoped skill for the in-repo exemplar at
`projects/working/bond/you_only_live_twice/`. Load this when working inside the project.

## When to Use

- Working inside the `you_only_live_twice` exemplar — running scripts, editing source,
  or regenerating outputs.
- Forking this exemplar as the starting scaffold for a new research project.
- Validating that the exemplar's contracts (thin-orchestrator, layer boundaries,
  no-mocks testing) still hold after changes.

## Quick Reference

```bash
# From the repository root
uv run pytest projects/working/bond/you_only_live_twice/tests --cov=projects/working/bond/you_only_live_twice/src --cov-fail-under=90
uv run python scripts/pipeline/stage_02_analysis.py --project templates/you_only_live_twice
uv run python scripts/pipeline/stage_03_render.py --project templates/you_only_live_twice
uv run python scripts/pipeline/stage_04_validate.py --project templates/you_only_live_twice
uv run python scripts/pipeline/stage_05_copy.py --project templates/you_only_live_twice
```

## Pitfalls

- **Keep scripts thin.** Business logic belongs in `src/` or shared
  `infrastructure/`, not in `scripts/`.
- **No mocks.** All tests must use real data, real files, and real
  computation.
- **Outputs are disposable.** Never hand-edit `output/` — regenerate from
  source and config.
- **Keep tracked benchmarks deterministic.** Serialize reproducible inputs,
  objective values, and checks; keep wall-clock timing as a runtime-only
  diagnostic.
- **Run from the repo root.** Commands assume the template monorepo root
  as working directory unless the child `AGENTS.md` states otherwise.

## Cross-refs

- Project contract: [`AGENTS.md`](../../../AGENTS.md)
- README: [`README.md`](../../../README.md)
- TODO: [`TODO.md`](../../../TODO.md)
- Exemplar roster: [`projects/AGENTS.md`](../../../../../AGENTS.md)
