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

Measured against the injected facility — a {{LAIR_FOOTPRINT_CELLS}}-cell shelf
carved at a location fixed by the scene geometry, before any sensor map is
computed — the detector's peak falls inside the footprint
({{LAIR_DETECTED_IN_FOOTPRINT}}) but **not** on its centre: it sits
{{LAIR_DETECTOR_OFFSET_CELLS}} cells ({{LAIR_DETECTOR_OFFSET_M}} m) away. That
offset is the expected behaviour of a high-pass anomaly score, which peaks on
the rim of a carved shelf where the discontinuity against the smooth background
model is largest, not at its centroid. The detector localizes the *facility*,
not its centre point, and only the first of those claims is supported here.

![Concealed-lair detection: thermal scene, terrain scene, and fused anomaly score with the top candidate region marked.](../output/figures/concealed_lair_detection.png){#fig:lair}

## Hidden-base discovery

The ground truth for this section is the injected lair — its centre cell and
its {{DISCOVERY_FOOTPRINT_CELLS}}-cell carved footprint — both fixed by the
scene's construction parameters and *not* derived from any anomaly map the
posterior consumes. The RF cue is generated at that injected site, so no cue is
centred on the detector's own answer.

Fusing the thermal, terrain and RF cues with a terrain-weighted prior over the
{{DISCOVERY_CANDIDATE_CELLS}} candidate sites, a greedy posterior-order search
first enters the injected footprint at rank {{DISCOVERY_FOOTPRINT_RANK}}, and
the footprint carries posterior mass {{DISCOVERY_FOOTPRINT_POSTERIOR}} — the
mass outside it falls below the reported precision. The footprint is
{{DISCOVERY_FOOTPRINT_CELLS}} of {{DISCOVERY_CANDIDATE_CELLS}} cells, so this
is a real hit rather than an arithmetic certainty.

The stricter question — does the posterior peak land on the injected *centre
cell*? — is answered **no**. The centre cell ranks
{{DISCOVERY_CENTROID_RANK}} with posterior {{DISCOVERY_CENTROID_POSTERIOR}},
and the peak sits {{DISCOVERY_PEAK_OFFSET_M}} m from it, for the same
rim-versus-centroid reason as above. This paper claims footprint-level
recovery only; cell-level recovery of the centroid is not established.

Fusion was also not what made the find. Scoring each cue on its own (prior x
that single likelihood-ratio map) gives footprint ranks
{{DISCOVERY_SINGLE_CUE_RANKS}} — every individual cue, and the terrain-weighted
prior by itself, already ranks the footprint first. In this scene the cues are
strong, not weak; fusion sharpens the posterior and adds redundancy, and the
claim that the base could only be found by combining weak sensors would be
false here.

Independently of any ground truth, the posterior-weighted expected effort — the
mean number of sites a greedy search inspects, $\sum_k k\,P(c_k)$ — is
{{DISCOVERY_EXPECTED_EFFORT_CELLS}} cell(s) against a uniform-prior expectation
of half the field, and the search finds a footprint cell within ten sites with
probability {{DISCOVERY_P_FIRST_10}}. Figure [@fig:discovery] shows the
posterior map with the injected footprint, the injected centre, and the
posterior peak marked separately.

![Hidden-base discovery: posterior probability map with the injected lair footprint, the injected centre (ground truth) and the posterior peak (estimate) marked separately.](../output/figures/hidden_base_discovery.png){#fig:discovery}

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
transmitter to within {{EMITTER_ERROR_M}} m of the injected emitter in
{{EMITTER_ITERATIONS}} iterations. The receivers report arrival-time
differences carrying a {{EMITTER_TIME_NOISE_NS}} ns (1σ) timing jitter, applied
before the conversion to ranges, so this error is an achieved accuracy that can
degrade — not the machine-zero a noise-free round trip through the same forward
model returns by construction.

The radio and imagery chains share no measurement, so comparing them is a
genuine cross-modal check, and they do **not** agree on a cell: the TDOA fix
lands {{EMITTER_IMAGERY_OFFSET_M}} m from the imagery-derived candidate, which
is essentially the whole {{EMITTER_TRUTH_IMAGERY_OFFSET_M}} m by which the
anomaly peak is itself displaced from the facility centre. The two modalities
agree on the facility and disagree on the point within it, by the full width of
that rim-versus-centroid offset; the radio fix is the accurate one, because the
emitter is where the transmitter was injected and the anomaly peak is not.

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
