Now let me write the manuscript SYNTAX.md, AGENTS.md and README.md, then the top-level docs.

<｜DSML｜tool_calls>
<｜DSML｜invoke name="write_file">
<｜DSML｜parameter name="content" string="true"># Manuscript Syntax Reference (VOLCANO)

This guide describes the markdown that composes the manuscript. It illustrates
*token* and *figure* syntax with literal `{{TOKEN}}` / `{{VARIABLE}}`
placeholders and is intentionally excluded from the live cross-reference token
scan (which reads `[0-9]*.md` numbered prose sections only).

## {{TOKEN}} variable protocol

Numeric values that come from the deterministic scenario **must** use
`{{VARIABLE_NAME}}` syntax. Hardcoding a number that will change if the
scenario is edited is a correctness bug.

The pipeline:

1. `scripts/z_generate_manuscript_variables.py` calls
   `src/you_only_live_twice/manuscript_variables.py::generate_variables()`.
2. It writes the full `{TOKEN: value}` map to
   `output/data/manuscript_variables.json`.
3. Prose in `[0-9]*.md` refers to tokens as `{{TOKEN}}`, which are substituted
   at render time. Every token used in a numbered section must exist in the
   generated map (enforced by a live cross-reference test).

Example of adding a token: add a key to `generate_variables()`, add an
assertion in `tests/test_manuscript_variables.py`, then reference `{{MY_TOKEN}}`
in prose.

## Figure syntax

Figures are referenced with Pandoc image syntax plus a `#fig:` label:

```markdown
![Caption.](../output/figures/rendezvous_windows.png){#fig:rendezvous}
```

and cross-referenced in prose as `[@fig:rendezvous]` (parenthetical) or
`@fig:rendezvous` (narrative). The VOLCANO figures:

- `rendezvous_windows.png` → `{#fig:rendezvous}`
- `concealed_lair_detection.png` → `{#fig:lair}`
- `pattern_of_life.png` → `{#fig:pattern}`

## Citations

BibTeX keys in `references.bib` are cited with Pandoc syntax, e.g. `[@vallado2013]`.
