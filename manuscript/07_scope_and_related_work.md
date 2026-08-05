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
  standard in human and robotic spaceflight mission design [@wertz2011;
  @fehse2003].
* Anomaly scoring by standardized residual against a fitted background is the
  classical statistical formulation of anomaly detection, of which the
  RX detector is the canonical imaging instance [@reed1990; @chandola2009].
* Bayesian cue fusion for a hidden-site hypothesis set follows Pearl's belief
  updating framework [@pearl1988]; ordering the resulting posterior into a
  search plan is classical search theory [@stone1975], and combining
  heterogeneous sensors follows the multisensor-fusion literature [@waltz1990].
* Passive RF emitter location by TDOA follows the Taylor-series estimator
  [@foy1976] and the hyperbolic-location literature [@chan1994; @skolnik2001].
* Infiltration routing is textbook best-first search / A* [@hart1968;
  @cormen2009].
* Modelling base activity as an inhomogeneous Poisson point process, and
  reading tempo off its rate envelope, follows standard point-process theory
  [@daley2003].

The self-consistency guarantee — every manuscript number computed from a fixed
seed and token-injected — follows the template's reproducible-research
convention documented in the BOND suite.

## Limitations and future work

Integration points for later BOND capabilities are recorded in `TODO.md`: a
perturbation-aware propagator, a spline-refined window edge detector, and
binding to the shared `bond-utilities` provenance helper once that dependency
ships.
