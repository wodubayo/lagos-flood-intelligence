# Phase 3: Independent validation

## Status and purpose

Validation preparation started on 2026-10-05; source screening and the first landmark diagnostic began on 2026-10-06. No independently labelled evaluation samples, accuracy metrics or validated flood extent are available yet.

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

Use a separate evidence row for each source or observation; do not overwrite conflicting evidence. The [reference-observation register](validation/reference_observations.csv) contains one contextual video observation. It is not eligible for accuracy assessment because capture time and exact flooded geometry remain unresolved.

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


## Phase 3 first evidence pass ? 2026-10-06

Phase 3 evidence collection is now underway. The baseline's eight registered artifact hashes were rechecked and matched the handoff snapshot. No thresholds, candidate geometry or reference labels were changed.

### Source leads and duplication

The [evidence lead register](validation/evidence_leads.csv) contains six leads, covering Iyana Oworo, an airport approach road and Trade Fair. Leads are not accepted reference observations. At this first pass the reference-observation CSV was empty; the subsequent user-frame review below adds contextual evidence only.

[AFP's July 23 fact-check](https://factcheck.afp.com/doc.afp.com.364R47J) traces a miscaptioned flood clip to Galaxy TV and reports matching the Iyana Oworo footbridge. This supplies a stronger location trail, but not a capture time. The linked [Galaxy TV video](https://www.youtube.com/watch?v=a7lOCyItoMM) could not be fetched by the browsing tool; it has not been independently viewed in this work.

[Punch](https://punchng.com/video-downpour-causes-flood-in-lagos-community/) and [Tribune](https://tribuneonlineng.com/gridlock-as-heavy-rainfall-floods-expressway-at-iyana-oworo/) reported flooding on July 3 in the same corridor. [PrimeBusiness](https://www.primebusiness.africa/video-heavy-rain-causes-flooding-traffic-gridlock-in-parts-of-lagos/) supplies additional video links and an airport-road lead. These may reuse footage or reporting; the Iyana Oworo records are provisionally grouped as possibly dependent, not counted as four independent flooded observations. No direct dry-reference evidence was established in this pass.

### Landmark search layer and SAR support

The place coordinates embedded in the Google Maps link cited by AFP are longitude 3.3962023, latitude 6.5550189. Direct Maps retrieval failed. These identify a **search landmark**, not a verified flooded pixel, camera location or surveyed reference point.

[check_validation_landmark.py](../src/check_validation_landmark.py) checked circles of 100, 250 and 500 m around that point. Radii are arbitrary search windows, not estimates of location error and not flood extents. Counts use pixel centers on the original candidate grid:

| Search radius | Eligible SAR pixels | Clean candidate pixels | Excluded pixels |
|---|---:|---:|---:|
| 100 m | 314 | 0 | 0 |
| 250 m | 1,959 | 0 | 0 |
| 500 m | 7,841 | 0 | 0 |

This is a **possible omission investigation**, not a measured false negative: reports describe flooding but the specific flooded road pixels and their state at 06:30:17 WAT remain unverified. The result cannot distinguish a rule limitation, an event-time mismatch or a spatial mismatch without further evidence. No accuracy metric is calculated.

QGIS search layers are in `docs/validation/evidence_search_areas.gpkg`:

- `search_landmark`: EPSG:4326 point with source and search-only role.
- `search_buffers`: EPSG:32631 review circles, explicitly not flood boundaries.

The [support-check report](validation/iyana_oworo_support_check.json) records methods, baseline verification and counts. Run the project Python environment with `src/check_validation_landmark.py` to reproduce; existing outputs are protected.

### Next evidence task

Open the Galaxy TV footage or the linked PrimeBusiness videos, identify the footbridge and road landmarks, and delineate only the visibly inundated road segment. Establish the original recording date/time or a defensible interval; the July 3 article timestamps are not recording times. Record evidence uncertainty before querying candidate coverage at the actual observed location.

Do not alter thresholds in response to this lead yet. Any rule revision based on this diagnostic case makes it development evidence, not an untouched accuracy test. Independent dry observations and a separate evaluation sample are still required.


## Iyana Oworo rule-stage diagnostic — 2026-10-06

[diagnose_validation_landmark.py](../src/diagnose_validation_landmark.py) compared the raw and clean candidates and reconstructed the working VH rule within the existing search circles.

| Radius | Eligible pixels | June VH > -21 | Also July VH <= -21 | Also decrease >=3 dB (raw) | Clean candidates |
|---|---:|---:|---:|---:|---:|
| 100 m | 314 | 314 | 0 | 0 | 0 |
| 250 m | 1,959 | 1,959 | 0 | 0 | 0 |
| 500 m | 7,841 | 7,836 | 13 | 2 | 0 |

The sequential columns depend on the order of conditions. Within 250 m, 35 pixels individually decreased by at least 3 dB, but none met the absolute July darkness cutoff. Within 500 m, the only two raw candidates were removed by cleanup. Thus the absence of clean candidates is not primarily a cleanup effect in these windows.

Within 250 m, median June VH was -13.07 dB, July VH -12.42 dB, and pixelwise change +0.46 dB. These are whole-window summaries, not measurements of the flooded road shown in footage. A median increase does not identify its cause or establish flooding; the exact footprint and acquisition-time state remain unknown.

Four input hashes and all grids matched. The reconstructed rule exactly reproduced raw candidate pixels in each window, and the clean mask was a subset. See [the numerical diagnostic](validation/iyana_oworo_rule_diagnostic.json). Candidate classification and thresholds remain unchanged.

The follow-up YouTube retrieval failed again, and the web search did not establish an exact recording time. Do not substitute article posting time for capture time. The next task is visual inspection of accessible footage, matching its road/footbridge landmarks, and recording timing uncertainty. A user-supplied frame or locally available clip can support that inspection, but a screenshot by itself does not authenticate its date.

Reproduce with the project Python environment and `src/diagnose_validation_landmark.py`. The script protects the existing report from overwrite.


## User-provided video frame review ? 2026-10-06

Observation **OBS_IYANA_VIDEO_001** records visibly inundated roadway and partly submerged vehicles. The user reports the relevant segment as **00:04-00:20**, a displayed video date of **July 4, 2024**, and narration naming **Iyana Oworo** and **Olopo Meji**.

Provenance is separated: the assistant inspected the supplied still; segment, displayed date and narration come from the user. The full video has not been independently played here. The frame is present in the conversation but has no archived project-file path. The displayed date is recorded as user-reported publication metadata, never as capture time.

The register's flooded label describes conditions at the unknown recording time ONLY. The evaluation_role is context_only_not_accuracy_sample and temporal_match_to_overpass is unresolved_exclude_from_accuracy. Observation date/time, coordinates, geometry and measured spatial uncertainty remain blank rather than invented. This is not a verified flood point at the July 3 06:30 WAT overpass.

[AFP](https://factcheck.afp.com/doc.afp.com.364R47J) attributes the clip to Iyana Oworo and reports a footbridge match, as well as circulation in a July 3 report. That suggests a route for resolving the later displayed upload date; it does not independently prove that this exact 00:04-00:20 segment was recorded before the overpass. Retrieval of AFP's comparison image failed, so an independent visual bridge match has not been claimed.

### Next spatial check

Load docs/validation/evidence_search_areas.gpkg in QGIS, choosing search_landmark and search_buffers. Keep OSM underneath, and zoom to the 100 m search circle near the Iyana Oworo bus-stop landmark. Compare the road alignment, elevated structure and pedestrian bridge with the supplied frame. These are search aids, not a flood polygon. If the structures do not match, widen the search along the named corridor instead of forcing the match.

Once the road segment is matched, save a separate observed-location geometry with documented uncertainty. Do not label entire buffers flooded or assign camera coordinates to all visible water. Timing must still be resolved, or this observation must remain excluded from overpass accuracy calculations.


## Proposed bridge coordinate — 2026-10-06

The user supplied 6.5518951, 3.3970649 in EPSG:4326. Interpreted as latitude then longitude, this is recorded as MATCH_IYANA_001 at **longitude 3.3970649, latitude 6.5518951**. It is a proposed pedestrian-bridge match, not the camera position or a verified flooded point. It lies 358.3 m from the earlier source-linked search landmark. Prior small-buffer statistics must not be attributed to this new location.

[check_proposed_bridge.py](../src/check_proposed_bridge.py) preserves the proposed point in [a separate GeoPackage](validation/proposed_bridge_match.gpkg), with layers proposed_bridge and diagnostic_windows. The [diagnostic report](validation/proposed_bridge_diagnostic.json) records the values and checks.

| Radius | Eligible pixels | Raw candidates | Clean candidates | Median VH change (dB) | Median VV change (dB) |
|---|---:|---:|---:|---:|---:|
| 50 m | 78 | 0 | 0 | +1.35 | +2.19 |
| 100 m | 311 | 0 | 0 | +1.56 | +2.15 |
| 250 m | 1,955 | 2 | 0 | +0.58 | +1.31 |

All sampled pixels in these windows were eligible. Within 100 m none met the July VH <= -21 dB criterion or the >=3 dB decrease criterion. Thus the darkening rule does not select this vicinity. The positive median changes summarize mixed surfaces and do not establish a scattering mechanism or flooding.

Input hashes and grids matched; reconstructed conditions reproduced the raw candidates; clean was a subset of raw; the exported point was reopened and checked. Candidate outputs and thresholds remain unchanged.

OBS_IYANA_VIDEO_001 remains contextual evidence only. Its exact-observation coordinates remain blank: the proposed bridge point is tracked separately rather than masquerading as the flooded road geometry. Camera direction, flooded carriageway and recording time remain unresolved. The arbitrary diagnostic radii are not measured spatial uncertainty.

Next establish which ground-level road segment is visible relative to the pedestrian bridge and curved flyover, using a wider video frame or identifiable landmarks. Do not mark the whole bridge buffer flooded. Even a successful spatial match will not settle the temporal relationship to the July 3 06:30 WAT acquisition.


## Geolocation limit and next evidence lead ? 2026-10-06

AFP's bridge comparison image could not be retrieved: the browsing tool failed and a normal HTTP request returned 403. No image was saved, no alternative access was attempted after that response, and no independent carriageway/camera-direction match is claimed.

The supplied frame plus named-corridor attribution support keeping Iyana Oworo as contextual flood evidence. MATCH_IYANA_001 remains a proposed bridge location. The exact inundated road geometry and overpass-time state remain unresolved. Further visual zooming alone will not settle those issues. Do not turn its empty candidate windows into a scored false negative.

Lead **L007** adds [Punch's July 3 White Sand Estate report](https://punchng.com/flood-sacks-lagos-schools-homes/). It describes a reporter visit, residents' accounts and school closure in Isheri-Osun. Rain is reported to have begun around 03:00, but that is not a measured inundation onset. The displayed 12:39 article time is not the visit time. School identity is withheld and no precise flooded-house coordinates are supplied. This is a new location lead, not an accepted reference label.

Next evidence work should identify a verifiable road/building in the original estate imagery and establish its observation time. Do not place an estate-centroid point and label it flooded. Reposts of this article count as the same source family. Independently documented dry locations are still needed; neither urban appearance nor absence of reports supplies dry labels.

The review now has seven leads, one contextual video observation and zero overpass-matched accuracy samples. Thresholds, reference coordinates and candidate outputs remain unchanged.


## White Sand Estate image availability review

The original [Punch report](https://punchng.com/flood-sacks-lagos-schools-homes/) was revisited for L007. The live article returned HTTP 200, but all three published image links returned HTTP 404. The header was tested at both the indexed host and its live-page CDN URL; neither supplied an image. No image was inspected or archived, and no location match was inferred.

[Retrieval results](validation/whitesand_image_sources.json) preserve the exact URLs and statuses. The article text supports estate-level reported flooding. Its reported 03:00 rainfall start does not establish flooding at a particular pixel before 06:30 WAT; neither the school nor photographed road segment is precisely identified.

L007 is now flagged context_only_insufficient_for_pixel_accuracy. No observation coordinates or flooded/dry pixel labels were added. The White Sand geolocation task cannot advance from the available article alone; a surviving original image/clip with recognizable landmarks or another independently located observation is required.

### Validation checkpoint

Current evidence supports a qualitative event-consistency discussion, not quantitative map accuracy. There are no accepted overpass-matched flood or dry samples. Diagnostic radar checks near proposed landmarks are not a substitute for such samples.

Preserve these unresolved cases and the existing candidate map. Do not report precision, recall, F1 or flood-area accuracy, and do not use the candidates as verified training labels. Practical next inputs are original dated field observations, georeferenced event imagery, or a suitable independently produced reference map with documented observation time. Any coarser or differently timed reference must be evaluated at its supported scale and time, rather than treated as exact 10 m truth.

If suitable reference data remain unavailable, Phase 3 should report validation as incomplete with contextual evidence only. That is a limitation of the study, not evidence that the detector is correct or incorrect.


## LGA-level geographic consistency check ? 2026-10-06

The user reported conspicuous change around Alimosho and the western neighborhoods reviewed earlier. To test this systematically, [summarize_lga_change.py](../src/summarize_lga_change.py) compared all 20 project LGAs without adding flood labels or changing the candidate rule.

### Denominators and method

Each LGA was rasterized by pixel-center inclusion and intersected with the existing Lagos state AOI mask. Valid coverage equals common-positive SAR pixels divided by LGA pixels within that AOI. VH/VV medians and change percentages use the common-positive support. A decrease of at least 3 dB means July-minus-June <= -3 dB. This descriptive cutoff is not a flood classification.

Existing clean candidate area is reported separately. Its percentage field in the CSV uses candidate-eligible pixels after historical-water exclusion, not the broader positive-SAR denominator. Ranks describe only observed areas; there is no extrapolation into gaps.

### Results

| LGA | Valid coverage (%) | Median VH change (dB) | Median VV change (dB) | VH decrease area (km2) | VH decrease (% valid) | VV decrease (% valid) | Clean candidate area (km2) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Amuwo Odofin | 80.03 | -0.13 | +0.53 | 9.3410 | 10.23 | 5.69 | 0.1122 |
| Ibeju Lekki | 92.11 | -0.33 | -0.07 | 30.4200 | 7.94 | 4.65 | 1.9815 |
| Oshodi/Isolo | 99.43 | -0.23 | +0.80 | 4.1666 | 7.76 | 3.16 | 0.0177 |
| Ajeromi/Ifelodun | 99.85 | -0.20 | +0.84 | 0.8877 | 7.12 | 2.70 | 0.0000 |
| Badagry | 22.23 | +0.32 | +0.19 | 6.9230 | 7.10 | 6.40 | 0.4041 |
| Lagos Mainland | 92.05 | -0.22 | +0.72 | 1.2988 | 7.00 | 3.52 | 0.0000 |
| Surulere | 100.00 | -0.35 | +0.97 | 1.3763 | 6.88 | 2.56 | 0.0059 |
| Mushin | 100.00 | -0.07 | +1.06 | 0.8684 | 5.11 | 1.88 | 0.0009 |
| Eti Osa | 90.27 | -0.03 | +0.16 | 7.4098 | 4.62 | 3.61 | 0.0282 |
| Epe | 69.49 | +0.04 | +0.02 | 40.6573 | 4.45 | 3.76 | 0.3999 |
| Shomolu | 99.43 | -0.11 | +0.86 | 0.4505 | 4.40 | 1.44 | 0.0000 |
| Apapa | 61.48 | +0.71 | +1.45 | 0.7197 | 3.13 | 2.09 | 0.0167 |
| Alimosho | 99.93 | +0.78 | +1.85 | 5.0442 | 2.76 | 1.38 | 0.0426 |
| Ojo | 88.60 | +0.61 | +0.89 | 4.1723 | 2.73 | 2.36 | 0.0257 |
| Kosofe | 99.75 | +0.64 | +1.44 | 1.2403 | 2.03 | 1.18 | 0.0388 |
| Lagos Island | 98.24 | +0.61 | +1.19 | 0.0852 | 1.72 | 0.95 | 0.0000 |
| Ikeja | 100.00 | +0.87 | +1.81 | 0.6823 | 1.67 | 0.91 | 0.0113 |
| Ifako/Ijaye | 100.00 | +0.93 | +2.33 | 0.4223 | 1.32 | 0.44 | 0.0000 |
| Ikorodu | 89.34 | +1.16 | +1.52 | 4.2562 | 1.15 | 0.90 | 0.0341 |
| Agege | 100.00 | +0.87 | +1.95 | 0.1275 | 1.04 | 0.36 | 0.0000 |

Alimosho has 99.93% valid coverage. Its VH decrease area is 5.0442 km2 (2.76% of valid pixels), ranking sixth by area and thirteenth by fraction. Median VH and VV changes are positive (+0.78 and +1.85 dB). This does not support the narrower hypothesis that Alimosho leads in large decreases; it does not test every possible definition of strongest change, nor exclude localized flooding.

Amuwo Odofin has the highest observed VH decrease fraction (10.23%), while Epe has the largest observed decrease area (40.6573 km2). Epe's larger area and incomplete coverage affect interpretation. Badagry's apparently high fraction represents only 22.23% valid coverage and must not be interpreted as a whole-LGA estimate.

The western-area hypothesis therefore remains worth investigating, especially around Amuwo Odofin, but location-specific evidence is still required. The named neighborhoods are not interchangeable with LGA polygons. This analysis does not independently confirm White Sand Estate's administrative assignment or its acquisition-time flooding.

### Boundary audit and verification

The project LGA polygons leave 2,093,691 state-AOI pixel centers (209.3691 km2) outside their union. Among them, 160,929 have common-positive observations (16.0929 km2), including 56 clean candidate pixels (0.0056 km2). No AOI pixel centers belonged to multiple LGAs. Unassigned pixels were retained as a separate audit category; totals were not forced into a neighboring LGA.

All input hashes matched the manifest; grids matched; 20 unique LGA geometries were valid; sampled change values were finite and not nodata. Valid, AOI and candidate totals reconciled with state totals plus unassigned pixels. The GeoPackage was reopened and checked.

Outputs:

- [All-LGA CSV](validation/lga_change_summary.csv), including counts, denominators and ranks.
- [QGIS GeoPackage](validation/lga_change_summary.gpkg), layer lga_change_summary.
- [Audit/report](validation/lga_change_report.json).
- SHA-256 hashes and source relationships in the acquisition manifest.

Reproduce using the project Python environment and src/summarize_lga_change.py. Existing outputs are protected.

For QGIS review, load lga_change_summary and use graduated symbology on vh_decrease_ge3_pct_valid, checking valid_coverage_pct in the attribute table. Label the map as radar decrease among observed pixels, not flood extent or flood probability. Medians summarize mixed land cover and can obscure localized changes.

This is a geographic consistency analysis only. It supplies no reference labels, confusion matrix or accuracy score.


## Western-area evidence check

Follow-up searches around Amuwo Odofin, Festac and Ago Palace did not establish a precisely located, overpass-matched observation in this pass.

- L008: [BusinessDay's July 7 retrospective](https://businessday.ng/news/article/misery-spreads-as-rain-sacks-lagos-residents/) includes an Amuwo-Odofin resident's account, but the estate is unnamed and the timing spans recent rains.
- L009: [BusinessDay's July 4 print edition, page 35](https://cdn.businessday.ng/wp-content/uploads/2024/07/BD_20240704.pdf) reports July 3 impacts along Ago Palace Way, described as Isolo-Oshodi. This is corridor-level evidence, not an exact flood footprint in Amuwo Odofin.
- A search hit mentioning King's Royal Estate / 91 Road was rejected as a flood-location lead: the surrounding [July 11 article](https://businessday.ng/news/article/lagos-housing-worsens-as-floods-sack-homeowners/) discusses demolition there. A search snippet alone could have misleadingly associated that address with flooding.

No positive or negative accuracy labels were created. The 10.23% VH-decrease figure for Amuwo Odofin remains an observed radar-change fraction, not a validated flood fraction.

### Practical validation gate

The next useful input is a precisely located, dated independent observation or a documented reference dataset, rather than more QGIS display changes. A road name helps narrow a search but cannot label every pixel along that road. If such evidence cannot be obtained, retain the current study as an exploratory change-mapping baseline and explicitly report quantitative validation as not completed. Do not tune thresholds against the same contextual reports and then call agreement independent accuracy.

## Public reference archive screening (2026-10-06)

Available validation evidence is restricted to public internet sources; no field observations were supplied. A targeted search of NASA, Copernicus Emergency Management Service, UNOSAT, the International Charter, GDACS and research literature did not establish an independent, acquisition-matched flood footprint for Lagos on July 3, 2024. This is a search result, not proof that no suitable dataset exists. Search-index descriptions were used where pages could not be retrieved; no reference raster was downloaded or inspected in this pass.

| Archive / source | Finding | Validation decision |
|---|---|---|
| [NASA MODIS flood product](https://doi.org/10.5067/MODIS/MCDWD_L3_NRT.061) | NASA describes historical MCDWD_L3 collection 6.1 coverage including 2024, approximately 250 m pixels, and 1-, 2- and 3-day composites. The [July 3 archive directory](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3/2024/185/) could not be retrieved by the browser. Exact Lagos granules and clear observations remain unverified. | Priority for a coarse optical cross-check; not yet accepted as a reference. |
| [CEMS on-demand mapping archive](https://emergency.copernicus.eu/news/tags/on-demand-mapping/) | Indexed results located September 2024 Borno flooding; no July Lagos activation was identified in this search. | No suitable event product established; catalogue search was not exhaustive. |
| [UNOSAT Nigeria product 3961](https://unosat.org/products/3961) | Indexed record concerns September 2024 Nigeria flooding; direct page requires JavaScript. The [Maiduguri assessment](https://unosat.org/static/unosat_filesystem/3967/UNOSAT_Preliminary_Assessment_Report_FL20240902NGA_Maiduguri_13Sep2024.pdf) also concerns September. | Wrong event/location for the Lagos July comparison. |
| [International Charter activation 910](https://download.disasterscharter.org/activations/flood-in-nigeria-activation-910-) | Indexed results describe September 2024 Dikwa, Borno products; direct retrieval failed. | Wrong event/location; no July Lagos product established. |
| [GDACS event 1102720](https://www.gdacs.org/Floods/report.aspx?episodeid=10&eventid=1102720&eventtype=FL) / [Copernicus Global Flood Monitoring](https://global-flood.emergency.copernicus.eu/news/214-global-flood-monitoring-annual-product-and-service-qa-report-2024/) | GDACS has a Nigeria event spanning June-July 2024. GFM uses Sentinel-1; exact Lagos daily coverage and scene lineage were not verified. | Potential method comparison. A product using the same input acquisition is not independent sensor validation. |
| Research literature search | No independently labelled July 3 Lagos reference dataset was established. Seasonal susceptibility or radar-derived masks do not by themselves provide acquisition-time truth. | No research-derived labels admitted. |

### Next check and acceptance criteria

The next concrete archive check is MODIS MCDWD_L3 for July 2-4, 2024, comparing the one-day layer with composite layers and their quality information. NASA's [product guide](https://www.earthdata.nasa.gov/s3fs-public/2024-04/MCDWD_UserGuide_RevD.pdf) documents the product structure. Before using any result:

1. Confirm file dates, Lagos coverage, product version, class definitions and usable cloud-free observations; record source URLs and checksums.
2. Compare observation/composite timing with Sentinel-1's July 3 acquisition at 05:30:17 UTC (06:30:17 WAT). A July 3 daily product does not establish flooding at that earlier instant.
3. Keep missing/cloud-obscured observations distinct from observed non-flooded areas. Do not treat an absent flood flag as evidence of dry land without valid observations.
4. Compare spatial support at the coarser product scale. Resampling 250 m labels to 10 m does not create independent 10 m truth.
5. Use any accepted coarse comparison as supporting evidence with stated limitations; do not convert it automatically into neighborhood-scale accuracy labels.

### Current reportable outcome

Phase 3 has produced evidence screening, location diagnostics and geographic consistency checks. Quantitative accuracy validation remains incomplete: no defensible confusion matrix, precision, recall or IoU is available. The mapped patches remain exploratory candidates. Internet reports support event context, with unresolved location/time uncertainty, and have not been promoted into pixel-level reference labels.

The project can be written up as an exploratory Sentinel-1 change-mapping study with an explicit validation limitation. Thresholds should not be relaxed merely to increase agreement with the same reports used during exploration.

## MODIS archive availability check (2026-10-06)

Direct HTTPS requests successfully retrieved all three NASA directory listings, resolving the earlier browser retrieval failure. Each lists one h18v08 MCDWD_L3 collection 061 file for the requested day. Tile selection uses the product's geographic 10-degree grid (expected 0-10 E, 0-10 N), not the MODIS sinusoidal grid; the HDF geolocation must still be checked after download. See the [NASA grid documentation](https://modis-land.gsfc.nasa.gov/MODLAND_grid.html).

| Observation/product date | Download file | Listed bytes |
|---|---|---:|
| 2024-07-02 | [MCDWD_L3.A2024184.h18v08.061.2025277150034.hdf](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3/2024/184/MCDWD_L3.A2024184.h18v08.061.2025277150034.hdf) | 11,892,495 |
| 2024-07-03 | [MCDWD_L3.A2024185.h18v08.061.2025277150043.hdf](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3/2024/185/MCDWD_L3.A2024185.h18v08.061.2025277150043.hdf) | 7,509,801 |
| 2024-07-04 | [MCDWD_L3.A2024186.h18v08.061.2025277150051.hdf](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3/2024/186/MCDWD_L3.A2024186.h18v08.061.2025277150051.hdf) | 8,963,374 |

The 2025 processing timestamp in these filenames is distinct from the 2024 product date. These are historical reprocessed products.

An unauthenticated request for the July 3 file redirected through NASA's license/profile route to Earthdata sign-in. The final HTTP 200 response was HTML, not an HDF file. No raster was saved or analysed. The archive listing establishes file availability, not cloud-free coverage or flooding.

### Download handoff

Sign in to NASA Earthdata in your browser, open the three links above, and save the HDF files without renaming them in:

    data/raw/validation/modis/

The destination folder has been created. Credentials remain in your browser; they should not be pasted into chat or committed to the project.

After download, verify file size, HDF readability and checksums, then inspect geolocation, flood class definitions and valid-observation layers over the Lagos AOI. Compare one-day results against the two-/three-day composites only with their differing temporal support stated. The July 3 product cannot by itself establish conditions at the Sentinel-1 overpass of 05:30:17 UTC.

Availability metadata and access outcome are saved in [modis_archive_check.json](validation/modis_archive_check.json). Cloud/observation quality and flood agreement remain unassessed. No accuracy labels or scores were created.

## MODIS file verification and quality result (2026-10-06)

All three downloaded HDF files match the archive-listed byte sizes and open successfully with QGIS 3.44.15's GDAL HDF4 reader. SHA-256 hashes are registered in the acquisition manifest. Metadata confirms July 2, 3 and 4 product dates, tile bounds 0-10 E / 0-10 N, algorithm package 6.1.1 and local version 6.1.5. Processing dates in 2025 are not observation dates.

The project Rasterio build cannot read HDF4 directly. [check_modis_quality.py](../src/check_modis_quality.py) uses the installed GDAL utilities to extract all 15 layers per date to native-grid GeoTIFF crops, then Rasterio to calculate statistics. There is no raster resampling. The 45 crops are in data/processed/validation/modis/. Bounding-box crops include pixels outside the state, while statistics use only pixel centers inside the state polygon.

The native grid is 0.0020833333 degrees. GDAL reports an unspecified datum based on Clarke 1866, not EPSG:4326. The script retains that CRS and transforms the boundary with PROJ; unresolved datum uncertainty is retained, rather than silently assigning WGS84. These geographic-grid pixel fractions are not exact geodesic area fractions.

### Results

Each layer contains 70,910 sampled AOI pixel centers. Sufficient-data percentages below count flood classes 0-3; class 255 is insufficient data.

| Product date | 1-day with cloud-shadow screening | 1-day without screening | 2-day | 3-day |
|---|---:|---:|---:|---:|
| July 2 | 0.83% | 0.83% | 0.70% | 0.20% |
| July 3 | 0.00% | 0.00% | 0.00% | 0.00% |
| July 4 | 2.69% | 2.71% | 0.00% | 0.00% |

July 3 has zero valid observations in both one-day valid-count layers at every sampled AOI pixel. Total counts are one at 70,906 pixels and zero at four pixels: input observations existed over almost the whole AOI, but none qualified as valid in these layers. This demonstrates insufficient usable observations; it does not establish a cloud-only cause. Global metadata fields such as QAPERCENTCLOUDCOVER=0 and an automatic quality flag of Passed do not override these spatial quality results (the automatic flag's own explanation says Always Passed).

The one-day flood class identifies one pixel on July 2 and 39 on July 4. These isolated product detections are not confirmed flood labels for our July 3 Sentinel-1 acquisition. The remaining unobserved pixels cannot be treated as non-flooded. Composite thresholds differ, so usable coverage need not increase monotonically from one to three days.

Class meanings follow the [NASA product guide](https://www.earthdata.nasa.gov/s3fs-public/2025-04/MCDWD_VCDWD_UserGuide_RevE_04.22.25.pdf): 0 no water, 1 reference surface water, 2 recurring flood, 3 unusual flood, 255 insufficient data. Classification and valid-count totals are reported separately; they are not assumed interchangeable.

### Validation decision

Reject these MODIS dates as a quantitative reference for the July 3 Lagos flood extent. No confusion matrix or agreement score was calculated: the event-day reference has no usable classifications. This is a documented reference-data limitation, not evidence that flooding did not occur or that Sentinel-1 succeeded or failed.

The archive search and MODIS feasibility check are complete. Independent quantitative validation remains incomplete. The defensible Phase 3 write-up is an evidence review with an explicit absence of acquisition-matched reference data; the Sentinel-1 outputs remain exploratory candidates.

Detailed metadata, class/count histograms, native CRS, input/output hashes and limitations are in [modis_quality_report.json](validation/modis_quality_report.json). The earlier archive check is retained as a historical record of the pre-download state.

Reproduce with the project Python environment and src/check_modis_quality.py; --gdal-bin can specify another HDF4-enabled GDAL installation. Existing outputs are protected against overwrite.
