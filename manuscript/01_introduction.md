# Introduction

In *You Only Live Twice* (1967), the adversary's base is a volcano that swallows
spacecraft whole, and the mission is won by knowing *where* the enemy is and
*when* they act. The VOLCANO package turns that intelligence problem into three
computational ones an agent can solve ahead of time with deterministic,
reproducible mathematics:

1. **When can we reach them?** A space capsule must be intercepted while it is
   in view. Orbit geometry decides the windows.
2. **Where are they hiding?** A concealed base leaks heat and flattens terrain,
   even when painted to look like a mountain.
3. **How do they operate?** A base keeps a rhythm; activity events reveal it.

The package is built in the BOND suite's style: a pure, infrastructure-free
domain core (the three capabilities), a thin BOND-API adapter exposing it as a
`MissionProvider` (codename {{BOND_CODENAME}}), and a manuscript that
hydrates every numeric claim from a fixed scenario rather than from prose.

## Reader's guide

- `src/you_only_live_twice/rendezvous_windows.py` — orbital mechanics for
  rendezvous / intercept window solving.
- `src/you_only_live_twice/terrain_anomaly.py` — thermal + terrain anomaly
  scoring for concealed-lair detection.
- `src/you_only_live_twice/pattern_of_life.py` — weekly activity analysis.
- `src/you_only_live_twice/mission.py` — the VOLCANO `MissionProvider`.
- `scripts/run_mission.py` — a thin CLI for every mission phase
  (`brief` / `recon` / `plan` / `execute` / `debrief`).

The remainder of the manuscript details the methodology (Section 2), the
results (Section 3), the experimental setup (Section 5), and reproducibility
(Section 6).
