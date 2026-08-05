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
| **Round-trip inversion** | TDOA: place an emitter, generate exact range differences, convert seconds→metres, then solve — the Gauss–Newton fix must return the injected point to sub-millimetre accuracy | The forward model and the inverse solver disagree |
| **Recovering an injected truth** | The lair shelf is cut into a known cell; the anomaly detector, the Bayesian posterior, the infiltration goal and the emitter fix must all land on that same cell | A capability has silently drifted onto a different "base" |
| **Guaranteed inequalities** | A* cost ≤ greedy-baseline cost over the *same* 4-connected space, so the reported reduction is non-negative by optimality rather than by a weak comparator | Either the search is not optimal or the baseline is not in the same space |
| **Monotonicity / normalization** | Posteriors sum to 1; discovery curves are cumulative and non-decreasing; priors are strictly positive | Probability mass is being created or destroyed |
| **Determinism** | Calling a generator twice returns an identical result; `rank_search_order` ties break by (row, col) | An unseeded draw or a set/dict ordering leak has crept in |
| **Error paths** | Non-2-D inputs, non-positive σ, mismatched shapes, impassable start/goal, degenerate TDOA geometry, non-convergence | A bad input silently produces a plausible-looking wrong answer |

### The comparator must be honest

The infiltration result is a *relative* claim (A* beats a greedy baseline), and
a relative claim is only as good as its comparator. The baseline is therefore
deliberately not crippled: it searches the same 4-connected neighbourhood over
the same cost field with the same goal heuristic. It loses because it is
monotone and cannot backtrack, which is a real algorithmic difference — not
because it was handed a worse map.

### Gates must be able to fail

Two gates in this package could easily be vacuous, so both are built to bite:

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
