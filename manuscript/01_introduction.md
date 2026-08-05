# Introduction

In *You Only Live Twice* (1967), the adversary's base is a volcano that swallows
spacecraft whole, and the mission is won by knowing *where* the enemy is and
*when* they act. The VOLCANO package turns that intelligence problem into
seven computational ones an agent can solve ahead of time with deterministic,
reproducible mathematics:

1. **When can we reach them?** Orbit geometry decides the rendezvous windows.
2. **How do we capture them?** Phasing decides when the capsule can be
   grappled and its velocity matched.
3. **Where are they hiding?** A concealed base leaks heat and flattens terrain,
   even when painted to look like a mountain.
4. **Does the evidence point to one site?** Bayesian fusion turns heterogeneous
   sensor cues into a search plan — and reports whether any single cue would
   have sufficed, rather than assuming fusion was what found the base.
5. **How do we get in?** A*, not guesswork, plans the infiltration route.
6. **Where is their transmitter?** TDOA multilateration fixes the base's radio.
7. **How do they operate?** A base keeps a rhythm; activity events reveal it.

The package is built in the BOND suite's style: a pure, infrastructure-free
domain core (the seven capabilities), a thin BOND-API adapter exposing it as a
`MissionProvider` (codename {{BOND_CODENAME}}), and a manuscript that
hydrates every numeric claim from a fixed scenario rather than from prose.

## Reader's guide

- `rendezvous_windows.py` — orbital mechanics for rendezvous / intercept
  window solving.
- `orbital_capture.py` — capture envelope, velocity-matching burn, phasing.
- `terrain_anomaly.py` — thermal + terrain anomaly scoring for lair detection.
- `hidden_base_discovery.py` — Bayesian cue fusion and search planning.
- `infiltration_planning.py` — terrain/thermal/guard cost surfaces and A*.
- `emitter_localization.py` — TDOA hyperbolic emitter localization.
- `pattern_of_life.py` — weekly activity analysis.
- `mission.py` — the VOLCANO `MissionProvider`.
- `scripts/run_mission.py` — a thin CLI for every mission phase
  (`brief` / `recon` / `plan` / `execute` / `debrief`).

The remainder of the manuscript details the methodology (Section 2), the
results (Section 3), the experimental setup (Section 5), and reproducibility
(Section 6).
