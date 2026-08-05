---
title: "Manuscript directory: you_only_live_twice (VOLCANO)"
type: "manuscript_guide"
version: "0.1.0"
---

# Manuscript (projects/working/bond/you_only_live_twice/manuscript)

Agent rules for the VOLCANO manuscript: file roles, the `{{TOKEN}}` protocol,
and the figure protocol.

## File inventory

| File | Role | Tokens / figures |
| --- | --- | --- |
| `00_abstract.md` | Abstract; result summary | all headline result tokens |
| `01_introduction.md` | Mission setup, reader's guide | none |
| `02_methodology.md` | Mathematics of the seven capabilities | none |
| `03_results.md` | All results + all figures | figure refs `rendezvous`, `capture`, `lair`, `discovery`, `infiltration`, `pattern` |
| `04_conclusion.md` | Summary | none |
| `05_experimental_setup.md` | Scenario params, environment | setup + env tokens |
| `06_reproducibility.md` | Determinism, artifacts, test gate | provenance tokens |
| `07_scope_and_related_work.md` | Scope, related work | none |
| `99_references.md` | Bibliography | none |
| `config.yaml` | Paper metadata, mission scenario | — |
| `references.bib` | BibTeX bibliography | — |
| `preamble.md` | LaTeX injections | — |
| `SYNTAX.md` | Syntax reference (excluded from token scan) | — |

## Token protocol

Numbers must be injected as `{{TOKEN}}`, never hand-authored. The authoritative
map is the return value of `src/you_only_live_twice/manuscript_variables.py::
generate_variables()`. The live cross-reference test
`tests/test_manuscript_variables.py::test_all_manuscript_tokens_are_generated`
gates completeness by scanning `[0-9]*.md` only (guide files legitimately
contain literal placeholders).

## Figure protocol

The six figures live under `output/figures/` and are cross-referenced with
`{#fig:label}` labels: `rendezvous`, `capture`, `lair`, `discovery`,
`infiltration`, `pattern`. See `SYNTAX.md`.

## Editing workflow

1. Change behaviour → update the affected module and its test.
2. Add/adjust any token in `manuscript_variables.generate_variables()` and the
   matching assertion in `tests/test_manuscript_variables.py`.
3. Reference the token in prose as `{{TOKEN}}`.
4. Re-run `scripts/z_generate_manuscript_variables.py` to refresh the JSON map.
