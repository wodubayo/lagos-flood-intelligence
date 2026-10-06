# Phase 3: Independent validation

## Status and purpose

Validation preparation started on 2026-10-05. No independently labelled evaluation samples, accuracy metrics or validated flood extent are available yet.

The Phase 2 handoff is an exploratory radar-change baseline: 400 clean candidate components totaling 3.1252 km2, with 71.05% of the Lagos AOI having comparable positive radar measurements before historical-water exclusion. Neither the candidate area nor the observation coverage is an accuracy measure.

## Preserved baseline

The [baseline snapshot](validation/phase2_baseline_snapshot.json) records the exact paths and SHA-256 hashes of candidate rasters, polygons and supporting reports. This is a provenance checkpoint, not a separate backup or a read-only lock. Existing candidate outputs remain unchanged.

The working rule is June VH > -21 dB, July VH <= -21 dB, and change <= -3 dB, on common positive support; JRC occurrence >=90% is excluded. Components smaller than 25 pixels were removed with eight-neighbor connectivity. No slope cutoff has been applied. These settings remain exploratory and are not selected for validated accuracy.

## Review register

[The validation register](validation/candidate_review_register.csv) starts with C0079 and C0373. Both have unknown reference labels. They were selected during visual review and are **diagnostic cases, not a representative or held-out accuracy sample**.

- C0079: historical-water-margin concern at eastern Ologe Lagoon; historical overlap does not establish its July 2024 state.
- C0373: coastal candidate in the southeastern displayed study area; no matched event evidence in the sources reviewed. Zero recorded historical occurrence does not establish dry conditions in 2024.

Coordinates in the register are representative points inside the candidate polygons, calculated from their geometry. They are not coordinates of independent flood observations. Refer to the source GeoPackage and patch_id for the full footprint.

## Evidence collection protocol

For each independent observation, record an evidence ID, original source URL or local file, event date/time and timezone, location or geometry, estimated spatial uncertainty in metres, label (flooded, dry, ambiguous or unknown), and a rationale. Leave unavailable values blank; do not infer a precise observation time from article publication time.

The target overpass began at 2024-07-03 06:30:17 WAT / 05:30:17 UTC. Record how the observation time relates to this acquisition and whether transient flooding or intervening events limit comparison. Evidence spanning June 26 and July 3 cannot automatically be assigned to one event.

Prefer original dated imagery or observations with identifiable landmarks and location precision appropriate to the candidate being assessed. Search both the reviewed locations and reported affected areas, including locations where the algorithm detected nothing. Absence from a news report is not a dry label. A current basemap is context, not a dated reference image.

Use a separate evidence row for each source or observation; do not overwrite conflicting evidence. The empty [reference-observation template](validation/reference_observations.csv) defines the fields. No observations have yet been entered.

## Evaluation design

Before calculating accuracy, specify whether the evaluation unit is a point, pixel or polygon and define the spatial/time matching rules. Sample independently labelled flooded and dry locations from both candidate and eligible noncandidate areas. Keep excluded or unobserved SAR areas separate.

Stratify relevant contexts such as built-up areas, open land and historical-water margins. Document sampling probabilities or restrictions so any accuracy estimate has a clear population. Avoid treating adjacent pixels or repeated reports of one observation as independent samples.

Keep threshold-development evidence separate from held-out evaluation. Because C0079 and C0373 already informed method review, they should not be treated as untouched test cases. If new evidence changes the rule, version the revised baseline and assess it on independent data.

## Completion criteria

- Usable dated and geolocated reference observations with documented uncertainty.
- Explicit handling of mismatched dates, ambiguous observations and missing SAR coverage.
- A documented evaluation sample and separation from tuning.
- Appropriate accuracy measures with sample counts and uncertainty, plus error review.
- A decision to accept, revise or reject the baseline for its intended use.

Until these are satisfied, do not use the candidate map as confirmed flood labels for machine learning. Phase 2's final rule and cartographic deliverables remain outstanding; the project is moving into evidence collection without declaring those requirements complete.
