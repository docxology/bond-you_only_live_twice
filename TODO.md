# TODO — you_only_live_twice (VOLCANO)

*You Only Live Twice* (1967), mission codename **VOLCANO**: a pure, deterministic
computation core of seven analytical capabilities (rendezvous windows, orbital
capture, concealed-lair detection, hidden-base discovery, infiltration planning,
TDOA emitter localization, pattern of life) behind the frozen BOND-API
`MissionProvider` protocol. **Latest measured gate:** see the Round-2 section
below (123 passed, 0 failed, 0 skipped, 100.00 % line+branch coverage on
`src/`; `ruff` + `mypy` clean; `scripts/00_preflight.py` exits 0). Counts are
not restated here — re-run the gate. The adversarial
audit's eight findings (four SEVERE, four MODERATE) were all closed in `dd88b56`
— the anti-circularity gate, the moved-lair positive control, the goal-reaching
greedy baseline and the noisy-TDOA error are live and were spot-checked this
session. What remains open is below.

Items that are done do not live here. Built capabilities are described in
`README.md` and `docs/architecture.md`.

## Open work

**Status:** C1, C2, V1–V4 and E8 were closed in Round-2 (section below), and
E6's noise axis is closed while its geometry axis stays open; E1, E2–E5 remain
open and E7 was deferred. The entries below are kept as written for the record —
read the Round-2 section before starting one.

Fifteen items. Three (V1, V2, E1) come directly from the audit's unresolved
findings and are the highest-value entries in this file.

### Correctness

**C1 — `docs/testing_philosophy.md` claims a test that does not exist.**
The "Error paths" row (`docs/testing_philosophy.md:47`) lists
"degenerate TDOA geometry, non-convergence" among the covered error branches,
and `docs/AGENTS.md:110-112` repeats that `localize_tdoa` "raises rather than
returning a bad fix … on singular geometry **or non-convergence**". The singular
case is tested (`tests/test_emitter_localization.py:101`); the non-convergence
raise at `src/you_only_live_twice/emitter_localization.py:159` is **not** — it
is one of the 13 uncovered statements and `rg -n "converge" tests/` returns
nothing. A documented safety property is therefore unbound.
*Done when:* a test drives `localize_tdoa` to exhaust `max_iter` (e.g. a tiny
`max_iter` with a far initial guess, or a geometry that oscillates) and asserts
`ValueError("TDOA Gauss-Newton failed to converge")`; `emitter_localization.py`
reaches 100 % and the doc row becomes true. If the path is genuinely
unreachable with valid inputs, the two doc rows must be amended instead — do not
leave both as they are.
*Command:* `uv run pytest tests/test_emitter_localization.py --cov=src/you_only_live_twice/emitter_localization.py --cov-report=term-missing`
— expect no `159` in `Missing`.

**C2 — Two defensive statements are unreachable, not merely untested.**
`src/you_only_live_twice/hidden_base_discovery.py:186` (`return float("inf")`
after the rank loop) cannot execute: the guard at line 178 already returns `inf`
for a zero-posterior cell, and any cell with positive posterior is present in
`rank_search_order`, which enumerates every cell. Likewise
`src/you_only_live_twice/scenario.py:315`
(`raise ValueError("the injected footprint is not in the search order")`) cannot
execute for any footprint that is a subset of the grid, which the scene
generator guarantees. Both permanently occupy the uncovered set and imply a
failure mode that does not exist.
*Done when:* each is either deleted (with a comment stating why the loop is
exhaustive) or converted into an assertion that documents the invariant, and the
two lines leave the `Missing` column.
*Command:* `uv run pytest tests/ --cov=src --cov-report=term-missing -q` — expect
neither `186` under `hidden_base_discovery.py` nor `315` under `scenario.py`.

### Verification

**V1 — The terrain-weighted prior is effectively unbound by the suite.**
*(from the audit's unresolved findings.)* Measured this session with a mutation
probe on a scratch copy of the tree: injecting
`weights = np.roll(weights, N, axis=1)` immediately before the return of
`terrain_weighted_priors` (`src/you_only_live_twice/hidden_base_discovery.py:60`)
leaves the suite **fully green at N = 2, 3 and 5** (107 passed each time) and
turns exactly **one** test red at N = 9 —
`tests/test_hidden_base_discovery.py:257`
(`assert _footprint_rank(priors / float(priors.sum()), footprint) == 1`, which
degrades to rank 2). Every posterior, footprint-mass, rank and discovery-curve
assertion stays green at all four offsets, because the likelihood-ratio product
(1e7–1e10) dominates the prior entirely. So a corrupted or misregistered prior
is invisible to the gates until it is badly wrong, and "the terrain-weighted
prior contributes to the find" is asserted nowhere.
*Done when:* a prior-specific gate exists that fails for a small
misregistration (target: N = 2 turns a test red) — e.g. assert the prior's own
argmax lies in the injected footprint, or assert `_footprint_rank(prior_only)`
against a tolerance tighter than "rank 1 vs rank 2". If the honest conclusion is
that the prior does not affect this scene's outcome, say so explicitly in
`docs/testing_philosophy.md` and in the scope section rather than leaving the
question open.
*Command:* reproduce the probe — copy the tree to a scratch dir, apply the roll
at N = 2, run `uv run pytest tests/ -q`, and expect a failure. It currently
passes.

**V2 — `DISCOVERY_FOOTPRINT_POSTERIOR` renders `1.0` with no negative control.**
*(from the audit's unresolved findings.)* The token is `1.0`
(`output/data/manuscript_variables.json`), produced by
`src/you_only_live_twice/scenario.py:346,353` and printed in
`manuscript/03_results.md` ("the footprint carries posterior mass
{{DISCOVERY_FOOTPRINT_POSTERIOR}} — the mass outside it falls below the reported
precision"). The mass outside the 80-cell footprint is exactly `0.0` in double
precision. `tests/test_hidden_base_discovery.py:209` pins
`> 1.0 - 5e-7`, matching the 6-dp token, and
`test_posterior_follows_a_moved_injected_lair` proves the mass tracks a moved
truth — but **nothing in the suite shows the number can fall**. A reader has no
in-repo evidence that `1.0` is a measured concentration rather than an artefact.
*Done when:* a negative control exists that misregisters one cue map relative to
the carved footprint (roll `lr_rf` or `lr_thermal` by a fixed offset) and asserts
the footprint mass drops materially — e.g. `< 0.5` — with the measured degraded
value recorded in `docs/testing_philosophy.md` under "Gates must be able to
fail".
*Command:* `uv run pytest tests/test_hidden_base_discovery.py -q -k misregist`
— currently collects 0 tests (`rg -n "misregist" tests/` is empty).

**V3 — `build_discovery_scene`'s documented default is never exercised.**
`src/you_only_live_twice/hidden_base_discovery.py:231-232` is the
`true_cell is None` branch that defaults the ground truth to
`volcano["lair_center"]`; the docstring at lines 221-223 documents it. Since
`dd88b56`, `scenario.build_scenario` always passes `true_cell=lair_site`
explicitly, so line 232 is uncovered and the documented default has no test.
*Done when:* a test calls `build_discovery_scene(volcano, thermal_z, terrain_z)`
with `true_cell` omitted and asserts the returned `true_cell` equals
`tuple(volcano["lair_center"])`.
*Command:* `uv run pytest tests/ --cov=src --cov-report=term-missing -q` — expect
`232` gone from the `hidden_base_discovery.py` `Missing` column.

**V4 — Eight untested guard clauses and partial branches.**
The uncovered set beyond C1/C2/V3 is, verbatim from today's run:
`hidden_base_discovery.py` 59 (prior weights not positive-finite), 106
(posterior scores not positive-finite), 139→141 (`max_cells is not None`), 229
(thermal/terrain shape mismatch); `infiltration_planning.py` 115 (LOS ray
passing through the post or the cell itself), 169 (`impassable` shape
mismatch); `pattern_of_life.py` 105→113, 171 (empty ACF search → `nan`), 211
(empty histogram → `0.0`); `terrain_anomaly.py` 80 (even `size` bumped to odd);
`figures.py` 288→298; `scenario.py` 313→312; `manuscript_variables.py` 108
(the `now is None` default date). `docs/testing_philosophy.md:47` states that
error paths are covered "so a bad input silently produces a plausible-looking
wrong answer" cannot happen — these are the exceptions.
*Done when:* each listed guard has a `pytest.raises` or value assertion, or is
justified in place; coverage rises above 99 % without the floor being touched.
*Command:* `uv run pytest tests/ --cov=src --cov-report=term-missing -q` and
diff the `Missing` column against the list above.

### Documentation

**D1 — Three measured numbers are hand-authored in `docs/` prose.**
`docs/AGENTS.md:83` ("~5.7 cells from the injected centre"),
`docs/testing_philosophy.md:43` ("80 of 4096 cells") and
`docs/testing_philosophy.md:94` ("The fused score is 8.55"). All three are
accurate today (`LAIR_DETECTOR_OFFSET_CELLS = 5.66`,
`DISCOVERY_FOOTPRINT_CELLS = 80`, `DISCOVERY_CANDIDATE_CELLS = 4096`,
`LAIR_TOP_FUSED_SCORE = 8.55`), but the `{{TOKEN}}` discipline that protects the
manuscript (`AGENTS.md:59-61`) does not extend to `docs/`, so any scenario change
silently falsifies them. The manuscript itself is clean — every number there is
a token.
*Done when:* each is either replaced with a pointer to the token name (e.g.
"the value of `{{LAIR_DETECTOR_OFFSET_CELLS}}`") or covered by a check that reads
`output/data/manuscript_variables.json` and fails on drift.
*Command:* `rg -n "5\.7 cells|80 of 4096|is 8\.55" docs/` — expect no hits, or a
new test in `tests/` that fails when the corresponding token moves.

### Extension

Genuine future work; none of it is a defect in what ships today.

**E1 — Swept-ensemble detection envelope.** *(from the audit's unresolved
findings.)* Every reported number comes from one deterministic scene, one noise
level and one emitter–sensor geometry. Footprint recovery is demonstrated at
five injected lair positions (three detector offsets in
`tests/test_terrain_anomaly.py`, two discovery offsets in
`tests/test_hidden_base_discovery.py:229`), which is a positive control for
tracking, not a detection-performance envelope. Build a deterministic sweep over
camouflage strength (`SETUP_LAIR_HEAT_K`), cue noise (`rf_noise`, thermal σ) and
lair geometry, and report recovery rate versus each axis.
*Acceptance:* a new module produces a recovery-rate curve; the manuscript
reports at least one swept result through tokens; the current single-scene
numbers survive unchanged as the ensemble's centre point.
*Command:* `uv run pytest tests/ -k ensemble` plus a new figure in
`FIGURE_FILENAMES`.

**E2 — Perturbation-aware propagator.** `rendezvous_windows.py` propagates pure
circular two-body motion. Add J2 (and optionally drag), keeping the two-body
solver as the deterministic baseline.
*Acceptance:* a J2 run shifts window start times measurably versus the two-body
baseline, both are exposed, and the manuscript reports the difference through
tokens.

**E3 — Sub-step window edges.** Window `start_s` / `end_s` are quantised to
`RENDEZVOUS_DT_S = 60.0` (`src/you_only_live_twice/scenario.py:93`). Refine
bracketed edges by bisection or a spline on the constraint function.
*Acceptance:* halving the step size changes reported edges by less than the
refinement tolerance, proving the result is no longer step-dependent.

**E4 — Out-of-plane capture.** `orbital_capture.py` models the coplanar phasing
problem only. Add the plane-change component to the velocity-matching budget so
the grapple Δv is not understated for the RAAN offset the scenario carries.
*Acceptance:* reported Δv rises for a non-zero RAAN difference and matches a
hand-computed vector-difference check.

**E5 — Dynamic infiltration.** `infiltration_planning.py` is a static
4-connected A* over a fixed cost surface. Extend to moving guard posts with
replanning, keeping the static solver as the deterministic baseline.
*Acceptance:* a moving-guard scenario produces a different route than the static
plan, and the static case remains bit-identical (`INFILTRATION_ROUTE_COST`
unchanged at 73.834).

**E6 — TDOA noise / GDOP characterisation.** `localize_tdoa` runs at exactly one
jitter level (`EMITTER_TIME_NOISE_S = 1.0e-8`,
`src/you_only_live_twice/scenario.py:135`), yielding `EMITTER_ERROR_M = 3.7912`.
`manuscript/07_scope_and_related_work.md` already states this is "one operating
point, not an accuracy envelope". Add a deterministic sweep and report error
growth against the geometric dilution of precision predicted by the 5-sensor
ring.
*Acceptance:* measured error scales with predicted GDOP across the sweep, with
the relationship asserted rather than eyeballed.

**E7 — Delegate provenance hashing to `bond-utilities`.**
`scenario.scenario_input_hash` (`src/you_only_live_twice/scenario.py:590-595`)
duplicates, byte for byte, `bond_utilities.mission_io.hash_payload`
(canonical JSON with `sort_keys` + compact separators, then SHA-256). The sibling
package exists at `../bond-utilities` but is
not a dependency here — only `bond-api` is (`pyproject.toml:21,30`). *(The
previous TODO named `mission_io.record_provenance_outcome`; no such function
exists — the real surface is `hash_payload`, `validate_record`, `save_record`.)*
*Acceptance:* `uv add bond-utilities` as a path dependency plus the swap in
`scenario.py`, with `scenario_input_hash()` returning the **same** digest before
and after — capture the current value first and assert on it.
*Command:* `uv run python -c "from you_only_live_twice.scenario import scenario_input_hash; print(scenario_input_hash())"`
before and after; the strings must match.

**E8 — Emitter-localization figure.** Six figures are rendered
(`FIGURE_FILENAMES`, `src/you_only_live_twice/figures.py:59-66`); emitter
localization is the only capability reported numerically with no figure
(`manuscript/03_results.md`, "Emitter localization"). A sensor-ring plot with
the TDOA hyperbolae, the converged fix, the injected emitter and the imagery
candidate would complete the set and make `EMITTER_IMAGERY_OFFSET_M = 5655.5`
legible.
*Acceptance:* the new filename is added to `FIGURE_FILENAMES` (which the
manuscript's figure count reads), the figure appears in `03_results.md` with a
`{#fig:emitter}` label, and `docs/_generated/COUNTS.md` reports 7 figures.

## Known limitations (not bugs)

Deliberately out of scope or accepted. Recording them here so they are not
re-litigated. The first four were forced by the adversarial audit: the original
claims were stronger and false, and were softened to these.

- **Footprint recovery, not centroid recovery.** Both the anomaly peak and the
  posterior peak land on the carved *rim*, `LAIR_DETECTOR_OFFSET_M = 5656.9` m
  from the injected centre; the centre cell ranks 80 with posterior 1.08e-15.
  This is the expected behaviour of a high-pass anomaly score. The supported
  claim is membership in the injected 80-of-4096-cell footprint, and only that.
  Pinned by `test_injected_centre_cell_is_not_recovered` so it cannot silently
  be re-strengthened.
- **Fusion was not what found the base.** Every single cue, *and the
  terrain-weighted prior on its own*, already ranks the footprint first
  (`DISCOVERY_SINGLE_CUE_RANKS = prior_only 1, rf 1, terrain 1, thermal 1`). The
  scene demonstrates consistent multi-cue evidence, not weak-signal fusion, and
  `manuscript/04_conclusion.md` and `07_scope_and_related_work.md` say so.
- **One scene, one noise level, one geometry.** All reported numbers characterise
  a single deterministic scenario. This is not a detection-performance envelope;
  E1 and E6 are what a real envelope would require. Stated explicitly in
  `manuscript/04_conclusion.md` (third limitation) and
  `07_scope_and_related_work.md`.
- **`DISCOVERY_FOOTPRINT_POSTERIOR` renders `1.0`.** The mass outside the
  footprint is 0.0 in double precision. The prose is bounded to "falls below the
  reported precision" rather than asserting an absolute-zero property that is not
  portably guaranteeable, and the test pins `> 1 - 5e-7` to match the 6-dp token.
  V2 above is what would make the number self-evidently non-trivial; the current
  wording is honest without it.
- **The RF cue is synthesised at the injected emitter.** `_rf_power_map`
  (`hidden_base_discovery.py:189-202`) centres the RF field on `true_cell` and
  adds fixed-seed noise. That is the scene's forward model, exactly as the
  thermal and terrain fields are generated from the carved shelf — it is not the
  circular-truth defect the audit removed (truth is no longer a detector output),
  but it does mean "RF alone ranks the footprint first" is a property of the
  generator's SNR choice, not a sensor result.
- **The manuscript generation date is a frozen string** (`2026-08-04`,
  `manuscript_variables.py:107-108`) and `Provenance.wall_time_s` is held at
  `0.0` (`mission.py:193`). Deliberate: no wall-clock may enter a persisted
  artifact.
- **The `MissionProvider` surface is frozen fleet-wide.** `film`, `brief`,
  `recon`, `plan`, `execute`, `debrief`, `register_gadgets()` and
  `FALLBACK_GADGETS` may be deepened, never reshaped. `solve_mission`'s results
  dict is additive-only.
- **No dependency on a sibling film package, the coordinator, or the
  orchestrator.** The BOND layer topology forbids it; E7's `bond-utilities` is a
  shared-utility layer, not a peer.
- **Published package repo.** `origin` is
  `github.com/docxology/bond-you_only_live_twice`; commits go to `main`.
- **No mocks, no untracked randomness.** `MagicMock` / `mocker.patch` /
  `unittest.mock` are prohibited outright; deterministic stand-ins must implement
  the real protocol.

```bash
# from the repo root

uv run pytest tests/ --cov=src --cov-fail-under=90
#   → 107 passed, 0 failed, 0 skipped; TOTAL 97.97 % (line+branch); floor 90 %

uv run ruff check src/ scripts/ tests/
#   → All checks passed!
uv run ruff format --check src/ scripts/ tests/
#   → 28 files already formatted

uv run mypy src/ scripts/
#   → Success: no issues found in 16 source files

uv run python scripts/00_preflight.py
#   → 4 PASS lines, "[VOLCANO] preflight OK", exit 0

rg -n "template[_]code_project" . || echo CLEAN
#   → CLEAN (exemplar lineage must be zero)

git status --short
#   → empty after commit
```

Artifact regeneration (must leave the tokens and figures unchanged for an
unchanged scenario):

```bash
uv run python scripts/z_generate_manuscript_variables.py   # 94 tokens → output/data/
uv run python scripts/render_figures.py                    # 6 PNGs → output/figures/
uv run python scripts/run_mission.py                       # full protocol run
```

Live counts are recorded under the gitignored `docs/_generated/` and regenerated
from the gate — never hardcode them in prose. If a number above moves, the gate
moved: find out why before updating the file.


---

## Round-2 (2026-08-06)

Round-2 improvement pass. **Baseline (measured before edits):**
`uv run pytest tests/ --cov=src --cov-fail-under=90` → **107 passed, 0 failed,
0 skipped, 97.97 % line+branch on `src/`**; `ruff check` + `ruff format
--check` clean; `mypy` clean over 16 source files. **Final:** **123 passed, 0
failed, 0 skipped, 100.00 % line+branch on `src/`**; `ruff check` + `format`
clean (28 files); `mypy` clean; `scripts/00_preflight.py` → `preflight OK`; 101
manuscript tokens; 8 figures rendered. The scenario descriptor gained two
fields (the TDOA sweep levels / realizations), so `input_hash` changed — the
manuscript's `{{MISSION_INPUT_HASH}}` follows automatically.

### Correctness / test-gap closures (with the gate that now pins them)

- **C1 — TDOA non-convergence now tested.** `localize_tdoa` exhausted its
  iteration budget (`max_iter=1`, `tol=1e-30`) and asserted
  `ValueError("TDOA Gauss-Newton failed to converge")`. The doc row in
  `testing_philosophy.md` ("error paths … non-convergence") is now true.
  → `test_localize_tdoa_raises_on_non_convergence`.
- **C2 — two unreachable defensive statements removed.** `expected_discovery_effort`
  now locates the true cell directly (`order.index(true_cell)+1`), deleting the
  dead `return inf`; `scenario._footprint_rank`'s unreachable `ValueError`
  became a documented `AssertionError` invariant, and is now *reachable and
  pinned* by a negative control passing an out-of-grid footprint.
  → `test_footprint_rank_raises_for_out_of_grid_footprint`.
- **V3 — the documented `build_discovery_scene` default is exercised.** Calling
  it without `true_cell` returns the volcano scene's lair centre.
  → `test_build_discovery_scene_defaults_true_cell_to_the_lair_centre`.
- **V1 — prior gate.** `test_terrain_weighted_prior_alone_ranks_the_footprint_first`
  asserts the *prior alone* (no cues) ranks the injected footprint first and is
  non-uniform. This is the gate that binds the terrain-weighted prior to the
  find — the cue-dominated posterior alone is blind to a corrupted prior.
- **V2 — footprint-mass negative control.**
  `test_footprint_posterior_mass_can_fall_under_cue_misregistration` rolls all
  three likelihood-ratio maps and shows the `1.0` footprint mass collapses
  below `1e-10`, proving the reported concentration is measured, not an
  artefact.
- **V4 — every untested guard clause covered:** non-finite prior weights
  (HBD 59), non-finite posterior scores (HBD 106), the `max_cells=None` default
  (HBD 139→141), discovery shape mismatch (HBD 229), impassable shape mismatch
  (infiltr 169), empty-ACF-search NaN (POL 171), empty-histogram duty cycle
  (POL 211), the schedule attempt-cap termination (POL 105→113), the odd-kernel
  size bump (terrain 80), and the `now=None` default date
  (manuscript_variables 108).
- **Dead LOS endpoint guard removed (adjacent to C2).** The
  `if (r,c)==post or (r,c)==cell: continue` in `_line_occluded` is provably
  unreachable — the integer-rounded sampler over `k∈[1, steps-1]` never lands
  on either endpoint — so it was deleted with a comment, and
  `infiltration_planning.py` reached 100 %. Likewise the dead `true_cell is
  not None` guard in `plot_hidden_base_discovery` was removed.
- **D1 — no hand-authored numbers left in `docs/`.** The three measured
  constants (`~5.7 cells`, `80 of 4096`, `is 8.55`) are now pointers to the
  manuscript tokens (`LAIR_DETECTOR_OFFSET_CELLS`, `LAIR_FOOTPRINT_CELLS` /
  `DISCOVERY_CANDIDATE_CELLS`, `LAIR_TOP_FUSED_SCORE`), matching the token
  discipline that already protects the manuscript.

### Extension depth added this round

- **E6 (partial) — TDOA accuracy envelope.** New `tdoa_error_sweep` in
  `emitter_localization.py`: for each timing-jitter level it solves
  `realizations=24` fixed-seed noisy TDOA problems and reports the mean error,
  turning "one operating point" into a deterministic error-vs-jitter curve
  (0→41.3 m over 0→200 ns). Wired through `scenario._solve_emitter` (additive
  `sweep` key), descriptor, tokens (`EMITTER_SWEEP_*`) and prose, with the
  monotonicity pinned by `test_tdoa_error_sweep_is_deterministic_and_monotone`.
  Error-vs-*geometry* and a swept sensor-ring remain out of scope (E6's
  remaining half).
- **E8 — the missing figure is now drawn.** `plot_emitter_localization`
  (TDOA sensor ring + range-difference hyperbolae + fix/truth/imagery markers)
  and `plot_emitter_error_sweep` (the envelope) were added to `FIGURE_FILENAMES`,
  the render script and both figure tests. Figure count goes 6 → 8, and
  `03_results.md` / `05_experimental_setup.md` / `06_reproducibility.md` /
  `07_scope_and_related_work.md` were updated to carry the new figures and
  tokens.
- Manuscript made more genuinely comprehensive: the emitter section now reports
  the envelope (not just the operating point), the abstract and conclusion
  mention it, and the scope section's emitter limitation was softened to "error
  vs *geometry* out of scope" (the noise axis is now characterised).

### Left for a future round

- **E1** — the detection-performance ensemble (swept camouflage / noise / lair
  geometry recovery-rate curve) remains open; the single-scene discovery
  numbers are unchanged and still stated as one operating point.
- **E7** — delegating `scenario_input_hash` to `bond-utilities.hash_payload`
  (a path-dependency add) was intentionally deferred; the byte-identical local
  sha256 remains in `scenario.py`.
- **E2/E3/E4/E5** — J2 propagation, spline window edges, out-of-plane capture,
  dynamic infiltration all remain future extensions.
- The `attempts < 200_000` cap in `build_weekly_activity_schedule` is now
  covered by a termination test but is still a hard safety bound (not a
  modelling choice).
