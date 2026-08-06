# Testing Philosophy — you_only_live_twice (VOLCANO)

Why the VOLCANO suite is built the way it is, and what a green run actually
proves here. This is the doctrine as it applies to *this* package's seven
capabilities — not a generic statement of testing virtue.

## The three rules

1. **No mock framework.** `MagicMock`, `mocker.patch` and `unittest.mock` are
   prohibited outright. Every test runs the real numerical code over real
   arrays.
2. **Real data, real computation.** Scenes, orbits and activity schedules are
   *generated* by the same fixed-seed builders the mission uses. There is no
   fixture file of pre-baked answers that could drift away from the code.
3. **Deterministic.** Every generator takes an explicit seed (1967, the film's
   release year). No test depends on wall-clock time, machine ordering, or an
   unseeded RNG.

## Why no mocks is cheap here

The usual argument for mocking is that the real dependency is slow, remote or
non-deterministic. None of that applies: the entire domain core is pure
numpy over grids of at most 64×64 and time grids of at most 1440 steps, with no
network, no filesystem, and no clock. The full suite runs in a few seconds. A
mock would buy nothing and would cost the only thing the suite is for — the
guarantee that the mathematics was actually executed.

The one place a stand-in appears is the BOND-API protocol boundary, and even
there the rule holds: a test double must be a *real implementation* of the
protocol with deterministic behaviour, never a recording mock. If a test needs
a provider, it constructs one.

## What each kind of test is asked to prove

A test that only checks a shape or a type is close to worthless here — an
array of the right shape full of wrong numbers passes it. So the suite is
written around properties that a broken implementation would actually fail:

| Technique | Where it is used | What a failure would mean |
| --- | --- | --- |
| **Closed-form anchors** | `posterior_expected_effort` against a point mass (E[K]=1) and a uniform posterior (E[K]=(N+1)/2); a hand-computed asymmetric case | The estimator's algebra is wrong, not merely its plumbing |
| **Round-trip inversion** | TDOA: place an emitter, generate exact range differences, convert seconds→metres, then solve — the Gauss–Newton fix must return the injected point to sub-millimetre accuracy. This proves solver/forward-model consistency **only**; it is an identity, not a measurement, and the mission's reported error comes from *noisy* timings instead | The forward model and the inverse solver disagree |
| **Recovering an injected truth** | `test_pipeline_recovers_a_moved_injected_lair` carves the shelf at an offset chosen by the test, then requires the fused-anomaly peak *and* the Bayesian posterior peak to land inside **that** footprint — the `LAIR_FOOTPRINT_CELLS`-of-`DISCOVERY_CANDIDATE_CELLS`-cells target carried by the manuscript tokens, never a hand-copied constant.) The truth is the scene-construction geometry, never a detector output | Detection has stopped tracking the injected lair, or a "truth" has been redefined as the estimate |
| **Guaranteed inequalities** | A* cost ≤ greedy-baseline cost, which needs *both* that the baseline searches the same 4-connected space **and** that it reaches the goal — A* minimises over goal-reaching walks only. `test_greedy_baseline_must_reach_the_goal_to_bound_astar` pins a grid where a non-backtracking greedy stops early and reports a cheaper truncated walk | The search is not optimal, the baseline is not in the same space, or the baseline is not comparing the same journey |
| **Monotonicity / normalization** | Posteriors sum to 1; discovery curves are cumulative and non-decreasing; priors are strictly positive | Probability mass is being created or destroyed |
| **Determinism** | Calling a generator twice returns an identical result; `rank_search_order` ties break by (row, col) | An unseeded draw or a set/dict ordering leak has crept in |
| **Error paths** | Non-2-D inputs, non-positive σ, mismatched shapes, impassable start/goal, degenerate TDOA geometry, non-convergence | A bad input silently produces a plausible-looking wrong answer |

### The comparator must be honest

The infiltration result is a *relative* claim (A* beats a greedy baseline), and
a relative claim is only as good as its comparator. The baseline is therefore
deliberately not crippled: it searches the same 4-connected neighbourhood over
the same cost field with the same goal heuristic, and it reaches the same goal.
It loses because it commits to locally cheapest steps and pays to retrace out
of dead ends, which is a real algorithmic difference — not because it was
handed a worse map.

A comparator can also be dishonest by being *too weak in the wrong direction*.
An earlier version of `greedy_baseline_path` broke out of dead ends and
returned a truncated walk. Its cost was then the cost of a shorter journey,
which can be **below** the optimal cost of the full journey, so
`cost_reduction` could go negative and the documented "non-negative by
construction" guarantee was simply false. The fix was to make the baseline
finish the journey, and the test now pins the exact grid that exposed it.

### A ground truth may not be derived from the estimate

The largest correctness risk in this package is not a wrong number but a
circular one. If the "true" base location is defined as the argmax of the same
anomaly maps the posterior is built from, then "the posterior ranks the true
base first" is an arithmetic identity that no bug can break. This package
carried exactly that defect: `build_scenario` set the true site to
`argmax(0.5*thermal_z + 0.5*terrain_z)` and generated the RF cue at that same
cell, so rank 1 was green by construction.

The rule now is that ground truth comes from the *scene generator's*
parameters — the cone centre plus a fixed lair offset, fixed before any sensor
map exists — and every downstream truth (the discovery `true_cell`, the RF
emitter, the infiltration goal, the TDOA emitter) is that injected site.
`scenario["detected_site"]` keeps the detector's own answer under a separate
name, and the gap between them is reported (`detector_offset_m`), not defined
away. The consequence is that the honest result is weaker than the one this
package used to print: the pipeline recovers the lair *footprint*, not its
centre cell, and the manuscript now says so.

### Gates must be able to fail

Four gates in this package could easily be vacuous, so all four are built to
bite. The last two replace assertions that could not fail:

- **The lair-recovery gate.** `test_detect_concealed_lair_recovers_injected_lair`
  used to assert `top.contains(centre) or top.fused_score > 3.0`. The fused
  score (token `LAIR_TOP_FUSED_SCORE`) made the second disjunct hold
  unconditionally, so a detector pointing anywhere on the map would still have
  passed. It now asserts that the
  fused-score argmax is a member of the injected footprint set — and
  `test_pipeline_recovers_a_moved_injected_lair` re-carves the lair somewhere
  else and requires the peak to follow, so a detector returning a fixed cell
  fails.
- **The baseline-bound gate.** `test_greedy_baseline_must_reach_the_goal_to_bound_astar`
  pins a 6×6 grid on which the previous non-backtracking greedy terminated at
  `(2, 3)` with cost 5.0 against an optimal cost of 10.0 — a reduction of −1.0.
  The assertion is that the baseline ends on the goal *and* costs at least the
  optimum; before the fix it went red.

- **The manuscript token gate.** `test_all_manuscript_tokens_are_generated`
  scans `manuscript/[0-9]*.md` for `{{TOKEN}}` references and fails if any is
  not produced by `generate_variables()`. It asserts `used > 0` first, so it
  cannot pass by finding nothing. (During this package's Phase-5 pass, renaming
  one token made it fail immediately — the gate is live, not decorative.)
- **The protocol surface check.** `scripts/00_preflight.py` verifies the
  provider is a runtime instance of the frozen protocol, that the slug matches,
  that the objective count is what the plan expects, and that gadgets register
  non-empty. It returns a non-zero exit code on any failure, and the smoke test
  asserts on that exit code.
- **The terrain-weighted prior gate (V1).**
  `test_terrain_weighted_prior_alone_ranks_the_footprint_first` asserts the
  prior *with no likelihood-ratio cues at all* already ranks the injected
  footprint first. This is the one gate a corrupted or misregistered prior
  would break, because the cue-dominated posterior is so concentrated that
  rolling the prior a few cells leaves its footprint rank at 1; the gate also
  proves the prior is non-trivial (not a silent uniform) by asserting its
  argmax lies inside the footprint.
- **The footprint-mass negative control (V2).**
  `DISCOVERY_FOOTPRINT_POSTERIOR` renders 1.0 only because every cue points at
  the lair; no *single* cue misregistration moves it.
  `test_footprint_posterior_mass_can_fall_under_cue_misregistration` rolls all
  three likelihood-ratio maps and asserts the footprint mass collapses below
  1e-10, proving the reported 1.0 is a measured concentration, not an artefact
  that cannot move.

## Coverage

The enforced gate is **90 % line *and* branch** on `src/`:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
```

Branch coverage matters more than line coverage here because most of the risk
lives in conditionals: window open/close transitions, the impassable mask, the
`inf` return when phasing geometry never closes, the "no path exists" raise.
Live measured numbers are recorded in `docs/_generated/COUNTS.md` and are never
hardcoded into prose — if you need to cite the figure, cite the gate.

Coverage is a floor, not a goal. A module at 100 % with only shape assertions
would be worse tested than one at 92 % with closed-form anchors.

## Adding a test

1. Write the test first, expressing a property that would fail if the
   mathematics were wrong.
2. Use a fixed seed and real arrays; never reach for a mock.
3. Cover the error branches as well as the happy path.
4. If the change moves a number the manuscript prints, add or update the token
   in `manuscript_variables.py` and let the cross-reference test confirm it.
5. Run the full gate plus `ruff` and `mypy` before committing.
