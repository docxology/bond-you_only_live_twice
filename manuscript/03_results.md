# Results

All results come from the deterministic VOLCANO scenario (seed
{{SCENARIO_SEED}}, provenance hash {{MISSION_INPUT_HASH}}) and are injected as
tokens — none are hand-authored.

## Rendezvous / intercept windows

Over a one-day horizon the geometry admits {{RENDEZVOUS_NUM_WINDOWS}}
rendezvous window(s). The first opens at {{RENDEZVOUS_FIRST_START_S}} seconds
after mission start and lasts {{RENDEZVOUS_FIRST_DURATION_S}} seconds, peaking
at a target elevation of {{RENDEZVOUS_FIRST_ELEV_DEG}}°. Figure
[@fig:rendezvous] shows the slant-range and elevation evolution with the
accepted window shaded.

![Rendezvous geometry: slant range (top) and target elevation (bottom) vs time, with the viable window shaded.](../output/figures/rendezvous_windows.png){#fig:rendezvous}

For an intercept, a coplanar Hohmann transfer burns a total of
{{RENDEZVOUS_DELTA_V_M_S}} m/s and takes {{RENDEZVOUS_TRANSFER_TIME_S}}
seconds.

## Concealed-lair detection

The thermal and terrain anomaly fusion surfaces
{{LAIR_NUM_CANDIDATES}} candidate region(s); the strongest covers
{{LAIR_TOP_AREA_CELLS}} cells with a fused score of
{{LAIR_TOP_FUSED_SCORE}} (thermal {{LAIR_TOP_THERMAL_SCORE}}, terrain
{{LAIR_TOP_TERRAIN_SCORE}}). Figure [@fig:lair] shows the raw scenes and the
fused anomaly map with the top candidate boxed.

![Concealed-lair detection: thermal scene, terrain scene, and fused anomaly score with the top candidate region marked.](../output/figures/concealed_lair_detection.png){#fig:lair}

## Pattern of life

A week of {{PATTERN_NUM_EVENTS}} base events resolves into
{{PATTERN_NUM_PEAK_WINDOWS}} daily operating window(s)
({{PATTERN_PEAK_WINDOWS}}), a dominant period of
{{PATTERN_DOMINANT_PERIOD_H}} hours, a duty cycle of
{{PATTERN_DUTY_CYCLE}}, and a {{PATTERN_TEMPO}} operational tempo. Figure
[@fig:pattern] visualizes the weekly and daily rhythms with the peak windows
shaded.

![Pattern of life: weekly activity histogram (top) and mean daily profile with detected peak windows (bottom).](../output/figures/pattern_of_life.png){#fig:pattern}

## End-to-end mission

The BOND-API provider (codename {{BOND_CODENAME}}) executes all three
capabilities in a single deterministic run against {{BOND_NUM_DATACLASSES}}
frozen protocol dataclasses across {{BOND_NUM_PROVIDER_METHODS}} provider
methods, returning full provenance.
