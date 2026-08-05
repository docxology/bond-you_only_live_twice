# Scope and Related Work

## Scope

The VOLCANO package covers seven special-agent analytical capabilities over a
single fixed scenario. Its scope is deliberately bounded:

* **Orbital mechanics** assumes circular two-body orbits; eccentric,
  perturbed, or multi-body motion (J2, drag, third-body) is out of scope.
  Window finding is a deterministic grid search, not an optimizer.
* **Orbital capture** models the coplanar phasing problem; out-of-plane plane
  changes and finite-burn effects are not modelled.
* **Lair detection** scores a synthetic volcano-camouflage scene. It
  demonstrates the anomaly-scoring *method* on real synthetic data; it is not a
  claim about any real imagery.
* **Hidden-base discovery** uses a naive-Bayes fusion of Gaussian sensor cues;
  it does not model correlated or missing measurements.
* **Infiltration planning** is a static 4-connected A* over a fixed cost
  surface; it does not model dynamic guards or replanning.
* **Emitter localization** solves noise-free/lightly-noised TDOA; heavy
  multipath and timing bias are out of scope.
* **Pattern of life** uses a diurnal-rate Poisson model of activity. It
  recovers the model's injected rhythm; it does not claim general time-series
  universality.

Nothing here is fielded operational software — it is a rigorous, reproducible
exemplar of the underlying mathematics, in keeping with the BOND suite's
research-exemplar contract.

## Related work

The methodology draws on established, citable foundations rather than novel
claims:

* Orbital-element → ECI conversion, circular propagation, the Hohmann
  transfer, and the phasing problem follow standard treatments of
  astrodynamics [@vallado2013; @bate1971].
* Rendezvous / proximity geometry and operational feasibility windows are
  standard in human and robotic spaceflight mission design [@wertz2011].
* Anomaly scoring by standardized residual against a smoothed background is the
  classical approach to thermal and terrain change detection [@hughes1971].
* Bayesian cue fusion for a hidden-site hypothesis set follows Pearl's belief
  updating framework [@pearl1988]; passive RF emitter location by TDOA
  follows the classical passive-geolocation treatment [@skolnik2001].
* Infiltration routing is textbook best-first search / A* [@cormen2009].
* Pattern-of-life / tempo analysis of activity point processes is the
  mainstream approach in surveillance and operations research [@waltz1998].

The self-consistency guarantee — every manuscript number computed from a fixed
seed and token-injected — follows the template's reproducible-research
convention documented in the BOND suite.

## Limitations and future work

Integration points for later BOND capabilities are recorded in `TODO.md`: a
perturbation-aware propagator, a spline-refined window edge detector, and
binding to the shared `bond-utilities` provenance helper once that dependency
ships.
