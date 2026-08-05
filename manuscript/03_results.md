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

## Orbital capture

Adding the capture envelope (range + relative-speed constraint) yields
{{CAPTURE_NUM_WINDOWS}} capture window(s), the first opening at
{{CAPTURE_FIRST_START_S}} seconds and lasting
{{CAPTURE_FIRST_DURATION_S}} seconds; the grapple still needs a
velocity-matching burn of {{CAPTURE_GRAPPLE_DV_M_S}} m/s. The phasing solution
requires a {{CAPTURE_PHASING_LEAD_DEG}}° lead angle, reached after a
{{CAPTURE_PHASING_WAIT_S}} second wait. Figure [@fig:capture] shows the range
and relative-speed profile with the capture window shaded.

![Orbital capture: slant range (top) and relative speed (bottom) vs time, with the grapple window shaded.](../output/figures/orbital_capture.png){#fig:capture}

## Concealed-lair detection

The thermal and terrain anomaly fusion surfaces
{{LAIR_NUM_CANDIDATES}} candidate region(s); the strongest covers
{{LAIR_TOP_AREA_CELLS}} cells with a fused score of
{{LAIR_TOP_FUSED_SCORE}} (thermal {{LAIR_TOP_THERMAL_SCORE}}, terrain
{{LAIR_TOP_TERRAIN_SCORE}}). Figure [@fig:lair] shows the raw scenes and the
fused anomaly map with the top candidate boxed.

![Concealed-lair detection: thermal scene, terrain scene, and fused anomaly score with the top candidate region marked.](../output/figures/concealed_lair_detection.png){#fig:lair}

## Hidden-base discovery

Fusing the thermal, terrain and RF cues with a terrain-weighted prior over the
{{DISCOVERY_CANDIDATE_CELLS}} candidate sites ranks the true base first
(rank {{DISCOVERY_TRUE_RANK}}) with posterior probability
{{DISCOVERY_TRUE_POSTERIOR}}; the search finds it within ten sites with
probability {{DISCOVERY_P_FIRST_10}}. Independently of that ground truth, the
posterior-weighted expected effort — the mean number of sites a greedy search
inspects, $\sum_k k\,P(c_k)$ — is {{DISCOVERY_EXPECTED_EFFORT_CELLS}} cell(s)
against a uniform-prior expectation of half the field. Figure [@fig:discovery]
shows the posterior map, a single concentrated peak on the true base.

![Hidden-base discovery: posterior probability map with the true base marked.](../output/figures/hidden_base_discovery.png){#fig:discovery}

## Infiltration planning

The slope/thermal/guard cost surface routes the agent from the rim to the lair
in {{INFILTRATION_PATH_LENGTH}} steps at a total cost of
{{INFILTRATION_ROUTE_COST}}, against a greedy baseline of
{{INFILTRATION_BASELINE_COST}} — a {{INFILTRATION_REDUCTION_PCT}} % cost
reduction (fraction {{INFILTRATION_REDUCTION}}) — accruing a thermal exposure
of {{INFILTRATION_EXPOSURE}} over {{INFILTRATION_EXPANDED}} expanded cells.
Figure
[@fig:infiltration] shows the cost field and the optimal route.

![Infiltration route: movement-cost field with the optimal route (red), entry (green), lair (cyan) and guard posts (orange).](../output/figures/infiltration_route.png){#fig:infiltration}

## Emitter localization

Passive TDOA multilateration over {{EMITTER_SENSORS}} sensors fixes the base's
transmitter to within {{EMITTER_ERROR_M}} m in {{EMITTER_ITERATIONS}}
iterations, confirming the radio-derived site matches the imagery-derived
site.

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

The BOND-API provider (codename {{BOND_CODENAME}}) executes all seven
capabilities in a single deterministic run against {{BOND_NUM_DATACLASSES}}
frozen protocol dataclasses across {{BOND_NUM_PROVIDER_METHODS}} provider
methods, returning full provenance.
