# TODO — you_only_live_twice (VOLCANO)

Forward-only backlog for the *You Only Live Twice* (1967) film package. Items
that are done do not live here — the built capabilities are described in
`README.md` and `docs/architecture.md`. This file holds only work that is still
open.

## Open — modelling depth

- [ ] **Perturbation-aware propagator.** `rendezvous_windows` currently
      propagates pure circular two-body motion. Add J2 (and optionally drag)
      so low-Earth intercept windows are realistic, keeping the two-body solver
      as the deterministic baseline to compare against.
      *Acceptance:* a J2 run shifts window start times measurably versus the
      two-body baseline, both are exposed, and the manuscript reports the
      difference through tokens.

- [ ] **Sub-step window edges.** Window `start_s` / `end_s` are quantised to
      the search step (`RENDEZVOUS_DT_S`). Once a window is bracketed by the
      grid search, refine its edges by bisection or a spline on the constraint
      function.
      *Acceptance:* halving the step size changes reported edges by less than
      the refinement tolerance, proving the result is no longer step-dependent.

- [ ] **Out-of-plane capture.** `orbital_capture` models the coplanar phasing
      problem only. Add the plane-change component to the velocity-matching
      budget so the grapple Δv is not understated for the RAAN offset the
      scenario actually carries.
      *Acceptance:* the reported Δv rises for a non-zero RAAN difference and
      matches a hand-computed vector-difference check.

- [ ] **Dynamic infiltration.** `infiltration_planning` is a static A* over a
      fixed cost surface. Extend to moving guard posts with replanning, keeping
      the static solver as the deterministic baseline.
      *Acceptance:* a moving-guard scenario produces a different route than the
      static plan, and the static case remains bit-identical.

- [ ] **Noise-regime characterisation for TDOA.** `localize_tdoa` is exercised
      noise-free and lightly noised. Add a deterministic sweep over measurement
      noise and report error growth against the geometric dilution of precision
      predicted by the sensor ring.
      *Acceptance:* measured error scales with predicted GDOP across the sweep,
      with the relationship asserted rather than eyeballed.

## Open — integration

- [ ] **`bond-utilities.mission_io.record_provenance_outcome`.** Mission
      outcomes currently construct provenance inline in `mission.execute`.
      Once the shared helper ships as an importable dependency, delegate
      persistence to it.
      *Acceptance:* `uv add bond-utilities` plus the swap in `mission.py`, with
      no change to the outcome's public shape and no change to `input_hash`.

## Open — reporting

- [ ] **Emitter-localization figure.** Six figures are rendered; emitter
      localization is reported numerically only. A sensor-ring plot with the
      TDOA hyperbolae and the converged fix would complete the set.
      *Acceptance:* the new filename is added to `FIGURE_FILENAMES` (which the
      manuscript's figure count reads), and the figure appears in
      `03_results.md` with a `{#fig:emitter}` label.

## Not planned

- Any remote or push — this is a local-only tree.
- Mocks, untracked randomness, or wall-clock values in persisted artifacts.
- Any dependency on a sibling film package, the coordinator, or the
  orchestrator (the BOND layer topology forbids it).
- Changes to the public shape of the `MissionProvider` surface or the gadget
  registration — those are frozen fleet-wide.
