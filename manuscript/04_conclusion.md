# Conclusion

The VOLCANO package demonstrates that a single-agent mission intelligence
problem — where to intercept, how to capture, where the enemy hides, how to get
in, how to localize its radio, and how it operates — can be answered with
deterministic, reproducible mathematics rather than guesswork. Each of the
seven capabilities is a real computation over real data:

* the **rendezvous / intercept solver** turns orbital elements into actionable
  windows and $\Delta v$ budgets;
* the **orbital capture** model turns a capture into a phasing problem with a
  well-defined lead angle, wait time, and velocity-matching burn;
* the **concealed-lair detector** fuses thermal and terrain anomaly scoring to
  surface a volcano-camouflaged structure, landing inside the injected
  footprint but {{LAIR_DETECTOR_OFFSET_M}} m from its centre;
* the **hidden-base discovery** engine turns those cues plus passive RF into a
  posterior and a search plan that reaches the injected footprint at rank
  {{DISCOVERY_FOOTPRINT_RANK}};
* the **infiltration planner** finds a provably optimal (A*) route that
  measurably beats a greedy baseline over the same search space;
* the **emitter locator** fixes the base's transmitter by TDOA to
  {{EMITTER_ERROR_M}} m from noisy receiver timings;
* the **pattern-of-life analyzer** extracts a base's operating rhythm from a
  week of activity events.

Three limitations are worth stating plainly rather than leaving to a reader to
discover. First, the anomaly detector and the Bayesian posterior recover the
lair's *footprint*, not its centre cell: both peak on the carved rim,
{{DISCOVERY_PEAK_OFFSET_M}} m off the injected centroid, and the centroid ranks
{{DISCOVERY_CENTROID_RANK}} in the search order. Second, fusion is not what
finds the base in this scene — each cue alone already ranks the footprint first
({{DISCOVERY_SINGLE_CUE_RANKS}}), so this is a demonstration of consistent
multi-cue evidence, not of weak-signal fusion. Third, the scene is synthetic
and single: these numbers characterise one deterministic scenario, not a
detection performance envelope, which would need a swept ensemble of scenes
with varied camouflage, noise and lair geometry. A partial exception is the
emitter localiser, whose deterministic error-versus-jitter envelope
({{EMITTER_SWEEP_POINTS}} levels, {{EMITTER_SWEEP_REALIZATIONS}} realizations
each) is now reported alongside the operating point; the fixed emitter–sensor
geometry and the single base scene remain single-scenario.

Because every result flows from a fixed seed through token-injected prose, the
manuscript and the computation can never drift apart: re-running the analysis
re-hydrates every number in this document. The package is one film in the BOND
suite, exposing its capabilities through the frozen BOND-API mission protocol
so any coordinator can drive it without knowing its internals, and keeping its
pure domain core importable without the protocol at all.
