# Phase 2: Sentinel-1 preprocessing and change analysis

## Purpose and current status

Phase 2 prepares comparable radar measurements for the July 2024 Lagos flood investigation and develops an initial flood-extent baseline. This chapter records completed methods and measured results; it will be extended as classification and quality assessment proceed.

**Status: preprocessing, grid alignment, coverage diagnostics, continuous dB change and an exploratory candidate-threshold comparison are complete. Final flood classification is still pending.** These outputs are radar measurements, not a validated flood map.

## Input data

The two verified Sentinel-1A IW GRD acquisitions have VV and VH polarization, descending geometry, relative orbit 95 and frame 571, separated by 12 days:

| Role | Acquisition start (UTC) | Product identifier |
|---|---|---|
| Before-event reference | 2024-06-21 05:30:18 | S1A_IW_GRDH_1SDV_20240621T053018_20240621T053047_054417_069F0A_10B1 |
| Event-date candidate | 2024-07-03 05:30:17 | S1A_IW_GRDH_1SDV_20240703T053017_20240703T053046_054592_06A521_9E4B |

July 3 acquisition began at **06:30:17 WAT**. Flood presence at that time has not yet been established independently; the event-date label must not be interpreted as proof of inundation.

The processing area is the Lagos State polygon acquired in Phase 1. Source selection, archive verification and ancillary-data provenance are described in [Phase 1](phase1_acquisition.md) and the [manifest](acquisition/manifest.json).

## SNAP preprocessing

Both acquisitions were processed using the following sequence. Settings were checked against the saved SNAP DIMAP metadata.

| Operation | Settings and result |
|---|---|
| Apply Orbit File | Precise orbit correction for each acquisition |
| Thermal Noise Removal | Both VH and VV; noise removal enabled; negative values retained |
| Calibration | Linear Sigma0 for VH and VV; dB output disabled |
| Speckle filtering | Refined Lee on both calibrated bands |
| Range-Doppler Terrain Correction | Copernicus 30m Global DEM, automatic download; bilinear DEM and image resampling; 10 m output spacing; WGS 84 / UTM zone 31N (EPSG:32631) |
| Terrain-correction masks/options | Mask areas without elevation enabled; selected source bands exported; additional radiometric normalization disabled |
| Export | Two-band Float32 GeoTIFFs: band 1 VH, band 2 VV |

The final terrain-corrected products use EPSG:32631. Terrain correction changed the displayed orientation from radar geometry to map geometry. Visual comparison with OpenStreetMap in QGIS confirmed the expected orientation; this is a qualitative check, not a measurement of subpixel registration accuracy.

SNAP standard-grid alignment remained disabled and was not exposed in the dialog used. The exports therefore had different grid origins despite matching CRS and pixel spacing. This was resolved in Python without another terrain-correction run.

## Nodata restoration, alignment and clipping

The exported files, `data/interim/sentinel1/S1A_YYYYMMDD_TC_linear.tif`, lacked standard GeoTIFF nodata tags and band descriptions. Their matching DIMAP files explicitly declared zero as nodata and identified the VH, VV band order.

The script [prepare_sentinel1_pair.py](../src/prepare_sentinel1_pair.py) performed these steps:

1. Check both DIMAP files for the expected bands and zero-nodata declaration.
2. Interpret source zero as missing without changing the original exports.
3. Snap the Lagos bounding rectangle outward to the June 21 reference grid.
4. Preserve June 21 pixel positions and bilinearly resample July 3 onto that grid, excluding source nodata.
5. Mask outside the Lagos polygon using pixel-center inclusion.
6. Write explicit nodata of -9999, band descriptions and a common-data mask.

All prepared rasters share **18,466 columns by 3,659 rows**, EPSG:32631 and 10 m spacing. The upper-left grid corner is easting 466697.41337032366 m, northing 740645.1080341006 m. Pixel spacing is not a claim of independent 10 m spatial resolution.

The common-data mask requires valid measurements on both dates in both polarizations. Valid nonpositive measurements remain in the linear products; they are excluded separately before logarithmic conversion.

## Coverage findings

The rasterized study area contains 37,601,742 pixel centers. Counts below use this common denominator.

| Coverage measure | Pixels | Percentage of AOI |
|---|---:|---:|
| Common valid linear measurements | 26,804,975 | 71.29% |
| Missing inside the catalog pair footprint | 7,580,384 | 20.16% |
| Missing outside the catalog pair footprint | 3,216,383 | 8.55% |
| Common valid pixels outside catalog footprint | 0 | 0.00% |
| Common strictly positive measurements usable for dB | 26,715,236 | 71.05% |

The catalog pair footprint intersects approximately 91.46% of the vector AOI. This describes scene geometry, whereas the 71.29% figure describes actual valid observations after processing. Vector areas and raster pixel-center counts also differ slightly at boundaries.

To investigate the discrepancy, JRC 1984-2021 water occurrence was resampled with nearest-neighbor interpolation onto the analysis grid. Of the 7,580,384 missing pixels inside the footprint, **4,869,439 (64.24%)** overlap JRC occurrence of at least 90%. The remaining 2,710,945 are below that occurrence level. This overlap is consistent with water-related masking being relevant, but does not establish its cause. The original scene data and SNAP no-elevation/sea mask still require inspection to attribute the losses.

The 90% cutoff was used only to describe coverage. **No permanent-water removal has been applied to the change layers.** JRC v1.4 has documented occurrence/seasonality limitations; see Phase 1 for the retained baseline and source caveats.

Missing areas are unobserved, not non-flooded. Later area summaries must report their valid observation denominator and must not extrapolate these results to all of Lagos.

## dB conversion and temporal change

The script [analyze_sentinel1_change.py](../src/analyze_sentinel1_change.py) first checked the registered SHA-256 hashes of its inputs. Conversion uses one shared support: all four measurements (two dates, two polarizations) must be finite, valid and strictly positive.

For calibrated power measurements:

```text
Sigma0_dB = 10 * log10(Sigma0_linear)
Delta_dB = Sigma0_dB(July 3) - Sigma0_dB(June 21)
         = 10 * log10(Sigma0_linear(July 3) / Sigma0_linear(June 21))
```

This excludes an additional **89,739 pixels**, reducing AOI coverage by approximately 0.24 percentage points. Nonpositive values were not clamped to a small positive number. Excluded pixels are -9999 in all dB and change bands.

Negative change indicates decreased radar backscatter; positive change indicates increased backscatter. Neither sign alone proves flooding.

Across the 26,715,236 common positive pixels:

| Polarization | Mean change (dB) | Standard deviation (dB) | Minimum (dB) | Maximum (dB) |
|---|---:|---:|---:|---:|
| VH | +0.262 | 1.985 | -49.512 | +59.326 |
| VV | +0.642 | 2.163 | -32.327 | +44.277 |

These are descriptive statistics over observed pixels, not flood thresholds or flood-area estimates. Extreme changes warrant inspection, particularly where positive linear values are close to zero.

## Output inventory

All raster outputs below are in `data/processed/sentinel1/`.

| Filename | Contents |
|---|---|
| lagos_20240621_sigma0_linear.tif | Aligned/clipped June 21 Sigma0; VH, VV |
| lagos_20240703_sigma0_linear.tif | Aligned/clipped July 3 Sigma0; VH, VV |
| lagos_pair_valid_mask.tif | 1: common valid; 0: missing inside AOI; 255: outside AOI |
| lagos_20240621_sigma0_db.tif | June 21 dB on shared positive support; VH, VV |
| lagos_20240703_sigma0_db.tif | July 3 dB on shared positive support; VH, VV |
| lagos_delta_sigma0_db.tif | July 3 minus June 21 dB; VH, VV |
| lagos_pair_positive_mask.tif | 1: all four measurements valid and positive; 0: excluded inside AOI; 255: outside |
| lagos_coverage_diagnostic.tif | 1: common valid inside footprint; 2: missing inside; 3: missing outside; 4: common valid outside; 255: outside AOI |

Float products use -9999 nodata; mask products use 255 nodata. Outputs preserve the original SNAP exports.

## Reproducibility and verification

Run from the project root using the project environment:

```powershell
.\.venv\Scripts\python.exe src\prepare_sentinel1_pair.py
.\.venv\Scripts\python.exe src\analyze_sentinel1_change.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The processing outputs already exist. Both processing scripts refuse to overwrite them; preserve an earlier run before deliberately regenerating outputs.

Evidence and machine-readable results:

- [Alignment report](acquisition/sentinel1_alignment_report.json): source metadata, grids, counts and alignment checks.
- [Change report](acquisition/sentinel1_change_report.json): coverage categories, statistics and histograms.
- [Change validation](acquisition/sentinel1_change_validation.json): independent block-by-block raster verification.
- [Manifest](acquisition/manifest.json): source relationships and output SHA-256 hashes.

Six unit tests passed before change processing, including known power-ratio conversion and exclusion of nonpositive, missing and nonfinite values. The exported dB/change rasters were also checked block by block against the linear inputs, using an independent log-ratio calculation with an absolute tolerance of 0.00001 dB. Grid equality, mask consistency and nodata placement were checked across every block.

## QGIS review and remaining work

Load the two dB products, the change product and both diagnostic masks. Use **Zoom to Layer** if the canvas is blank.

For the two dates, select Singleband gray, use the same polarization and apply identical display limits. For the change raster, use Singleband pseudocolor with a diverging ramp centered at zero; -6 to +6 dB is an initial display range only, not a detection threshold. Review VH and VV separately. Style diagnostic masks by their categorical values, with 255 transparent. Keep OpenStreetMap available for geographic context.

Before Phase 2 can be closed:

1. Inspect change patterns, extreme values and coverage gaps, including the source no-elevation/sea masking.
2. Choose and document a reproducible flood-candidate rule and threshold sensitivity analysis.
3. Align and apply justified permanent-water and terrain filters, recording their effect on valid area and candidate extent.
4. Apply documented spatial cleanup and produce candidate raster/vector outputs, maps and area statistics.
5. Carry unresolved event-time suitability and geolocation limitations into the independent validation gate.

Flood presence at the acquisition time, urban detection limitations and independent accuracy assessment remain unresolved. Speckle filtering and interpolation can affect narrow features. Retain the original products for sensitivity analysis. Phase 3 validation must precede treating candidate flood labels as reliable training or reference data.


## Exploratory candidate threshold comparison

### Visual observation

During QGIS review, the user identified a coherent red patch in the southwestern portion of the displayed area, west of Lagos Lagoon. It persisted with weaker visual contrast in VV. Using identical grayscale limits (-25 to -5 dB), July VH appeared darker than June. This is recorded as **visually identified backscatter decrease; flood cause unverified**. These displays derive from the same measurements and are not independent evidence. No coordinates or neighborhood boundary were recorded, so the numerical results below cannot be attributed to that particular patch.

For change visualization, white stops at -3, 0 and +3 dB suppressed small displayed changes, with red at -6 and blue at +6 dB. This was a display adjustment only; original raster values were retained.

### Rule and experimental settings

[explore_sentinel1_thresholds.py](../src/explore_sentinel1_thresholds.py) tests nine deliberately illustrative combinations, not thresholds calibrated against reference flood labels:

```text
June VH > T
AND July VH <= T
AND (July VH - June VH) <= D
AND common positive-data support
AND known JRC occurrence < 90%

T in {-18, -21, -24} dB
D in {-2, -3, -4} dB
```

The June condition rejects pixels already below the chosen darkness cutoff. It can also omit real inundation over already-dark surfaces. Changing T changes both the June and July conditions, so configurations are not necessarily nested. VV decrease is summarized as supporting information, not a required condition.

The decrease-based approach targets newly dark radar returns; it cannot capture all urban flooding. Flooding near buildings or vegetation can instead increase backscatter, as discussed in [NASA's dual-polarimetric flood-mapping research](https://ntrs.nasa.gov/citations/20190034113). No thresholds in this experiment are attributed to that publication.

Nearest-neighbor JRC alignment and a >=90% occurrence exclusion were applied only to these candidate products. They do not modify the continuous dB/change layers. From 26,715,236 positive-support pixels, 7,879 historical-water pixels were excluded and none had unknown JRC values. The eligible denominator is **26,707,357 pixels (2,670.7357 square kilometres)**. The small additional exclusion does not imply little water in Lagos: much historical water was already absent from the valid SAR support. JRC v1.4 source caveats still apply.

### Threshold sensitivity results

Areas below are candidate pixel counts multiplied by 100 square metres, expressed in square kilometres, after historical-water exclusion and before spatial cleanup.

| July VH cutoff T (dB) | Change cutoff D (dB) | Candidate area (km2) | Candidates also decreasing in VV |
|---|---|---:|---:|
| -18 | -2 | 34.9335 | 62.0% |
| -18 | -3 | 22.9363 | 65.4% |
| -18 | -4 | 12.9665 | 69.3% |
| -21 | -2 | 8.4618 | 68.5% |
| -21 | -3 | 6.3641 | 71.9% |
| -21 | -4 | 4.4601 | 76.1% |
| -24 | -2 | 3.8060 | 63.4% |
| -24 | -3 | 2.9617 | 67.1% |
| -24 | -4 | 2.2347 | 71.2% |

The 2.2347-34.9335 km2 range demonstrates sensitivity to the rule settings. It is neither an uncertainty interval nor a validated estimate of flood extent. Threshold-agreement values count how many of these nine related configurations select a pixel; they are not probabilities or independent votes.

### Spatial cleanup and review products

For illustration, the middle parameter combination (T=-21 dB, D=-3 dB) was retained as a **review preview**, not an optimized final model. It selected 63,641 pixels (6.3641 km2) after water exclusion; 45,758 also decreased in VV.

Connected-component cleanup used eight-neighbor connectivity over the full raster, avoiding tile seams. The sieve result was intersected with the original candidate mask so it could remove detections without filling holes or adding candidate pixels.

| Minimum component pixels | Nominal area cutoff (m2) | Retained candidate area (km2) |
|---|---:|---:|
| 9 | 900 | 4.4289 |
| 25 | 2,500 | 3.1252 |
| 100 | 10,000 | 1.6598 |

Small-component removal may discard real narrow or fragmented floods. The 25-pixel preview is solely a convenient review product; terrain filtering and independent validation remain pending.

New files in `data/processed/sentinel1/`:

- `lagos_candidate_threshold_agreement.tif`: 0-9 configurations selecting each eligible pixel; 255 excluded.
- `lagos_candidate_exploratory_raw.tif`: middle-setting candidates before cleanup.
- `lagos_candidate_exploratory_clean.tif`: same candidates after removing components smaller than 25 pixels.
- Matching `.qml` styles for the raw and clean previews: red candidates, transparent nonselected/excluded areas.

For binary products, 1 means selected candidate, 0 means eligible but not selected, and 255 means excluded or unobserved. Zero must not be interpreted as verified non-flood.

Load the clean preview above OSM and turn off the continuous change and date rasters. The adjacent QML file supplies the intended style when QGIS loads it; if needed, use Layer Properties > Style > Load Style to select it. Review the known patch and compare the raw preview to see which fragments cleanup removed. QML XML structure was checked programmatically; GUI rendering has not been tested in this session.

### Reproduction and checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe src\explore_sentinel1_thresholds.py
```

The script refuses to overwrite existing experiment outputs. All eight unit tests passed, including threshold-boundary/persistent-dark exclusions and cleanup tests for isolated pixels, holes and diagonal connectivity. Input hashes, grids, exclusion-count partitions and removal-only cleanup were checked. All three exported rasters were reopened and compared exactly with the calculated arrays.

Full counts and parameters are in the [threshold report](acquisition/sentinel1_threshold_report.json) and [sensitivity CSV](acquisition/sentinel1_threshold_sensitivity.csv). Inputs and result hashes are registered in the [manifest](acquisition/manifest.json).

**Phase 2 remains in progress.** Next work is spatial review, investigation of coverage losses, terrain-filter assessment and justified final rule selection. Candidate polygons, final map/area reporting and independent event-time validation are not yet complete.


## Candidate backscatter, elevation and evidence audit

The user compared raw and clean candidates in QGIS around Festac, Satellite Town and Trade Fair Complex. A few more detections were visible in the raw layer. This is a qualitative local observation: the full study-area cleanup reduction remains 6.3641 to 3.1252 km2. A precise polygon for the visually identified patch has not been recorded.

[audit_sentinel1_candidates.py](../src/audit_sentinel1_candidates.py) audited every raw candidate and its cleanup-retention flag. Before/after and change values were read from the existing rasters. Copernicus 30m DSM elevations were sampled with bilinear interpolation onto the same grid, explicitly handling nodata. This operation does not improve the DEM's native resolution. No slope or elevation filter was imposed.

The following are study-area-wide medians; the median of pixelwise differences need not equal the difference between the two date medians.

| Selection | Pixels | June VH (dB) | July VH (dB) | VH change (dB) | VV change (dB) | VV also decreased | DSM elevation (m) |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw | 63,641 | -17.75 | -22.59 | -4.86 | -1.38 | 71.9% | 4.02 |
| clean | 31,252 | -17.48 | -23.15 | -5.65 | -2.25 | 82.3% | 3.92 |

All candidate pixels had valid sampled DSM elevation. For cleaned candidates, 24,163 of 31,252 (77.3%) had DSM elevations <=5 m, and 28,687 (91.8%) were <=10 m. These are descriptive cutoffs, not acceptance rules. The DSM is a surface-height product that can include vegetation and buildings; its heights are not flood depths. No comparison to an independently sampled dry control set has been made.

Selection already requires a VH drop, so the strong negative VH summary is expected by construction. VV agreement and low elevations provide context but do not confirm cause. The existing candidate rasters have not been altered by this audit.

The [independent evidence review](events/LAG_2024_07_evidence_review.md) records reports around Trade Fair and broader impacts in Satellite Town/Amuwo-Odofin. Reports support further investigation but do not establish flooding at the candidate pixels at 06:30 WAT. The review also identifies June 26 rainfall between the reference and event-date acquisitions, limiting attribution solely to the July 3 storm.

### Audit outputs and reproducibility

- [Machine-readable audit](acquisition/sentinel1_candidate_audit.json): distributions, elevation counts and checks.
- `data/processed/sentinel1/lagos_candidate_review_points.csv`: every raw candidate pixel center, EPSG:4326 longitude/latitude, raster row/column, cleanup-retention flag, both dates' VH/VV, changes and DSM elevation. These are candidate sample locations, not reference labels.
- [Evidence review](events/LAG_2024_07_evidence_review.md): source dates, supported claims, location/time limitations and validation needs.

```powershell
.\.venv\Scripts\python.exe src\audit_sentinel1_candidates.py
```

The script refuses to overwrite its outputs. Input hashes and grids matched; every raw candidate passed the original rule; the clean mask was a subset; changes matched date differences; and counts matched the threshold report. Audit outputs are registered in the manifest.

The CSV can be added to QGIS as delimited text using longitude as X, latitude as Y and EPSG:4326. This allows values to be inspected at specific candidate locations without inferring neighborhood statistics from a screenshot.

**Decision:** retain the exploratory label and existing thresholds for review. Elevation summaries alone do not justify applying a height cutoff, and available news reports do not justify finalizing the map. Slope/terrain assessment, independently timed reference observations and a documented final classification rule remain outstanding.


## Slope sensitivity and candidate review polygons

### Terrain method

[assess_candidate_terrain.py](../src/assess_candidate_terrain.py) reprojected the existing Copernicus DSM to EPSG:32631 with bilinear resampling at 30 m spacing. Slope was calculated with a Horn 3-by-3 weighted gradient and expressed as degrees:

```text
dz/dx = ((NE + 2E + SE) - (NW + 2W + SW)) / (8 * 30)
dz/dy = ((SW + 2S + SE) - (NW + 2N + NE)) / (8 * 30)
slope = atan(sqrt((dz/dx)^2 + (dz/dy)^2)) * 180/pi
```

All nine cells must be valid; the outer one-cell border and neighborhoods touching nodata remain nodata. This follows the conservative neighborhood handling described in [GDAL's slope documentation](https://gdal.org/en/stable/programs/gdaldem.html). The computation uses project NumPy code, not a GDAL command invocation.

Candidate pixel centers were assigned the nearest cell from the 30 m slope raster. Slope was not calculated on an artificially refined 10 m elevation grid. DSM gradients may include buildings and vegetation, and cannot resolve street-scale drainage or establish inundation.

### Measured sensitivity

These are hypothetical pixel-retention counts, not newly classified flood areas. Thresholds of 2, 5 and 10 degrees are exploratory alternatives, not accuracy-calibrated settings. Spatial cleanup was not repeated after screening, so retained fragments could be smaller than the earlier 25-pixel minimum.

| Maximum slope | Raw candidates retained (km2) | Clean candidates retained (km2) |
|---|---:|---:|
| No slope screen | 6.3641 | 3.1252 |
| 2 degrees | 4.9093 | 2.6356 |
| 5 degrees | 5.9743 | 3.0166 |
| 10 degrees | 6.3426 | 3.1245 |

Median sampled slope was 0.72 degrees for raw candidates and 0.50 degrees for clean candidates. One raw candidate pixel had unknown slope; all clean candidate pixels had valid slope. Unknown slope is excluded from retention counts but is not treated as steep or non-flooded.

**Decision:** no final slope cutoff has been selected or applied. At 5 degrees, 30,166 of 31,252 clean candidate pixels remain (96.5%). This documents that most current candidates have low DSM slopes; it does not establish flood cause.

### Polygon export

The original clean candidate raster was exported to **400 review features**, totaling **3.1252 km2**. Each feature represents an eight-connected candidate component. Four-connected polygon pieces were unioned by component ID, preserving diagonal contacts as valid multipart geometry. The smallest feature contains 25 pixels (0.25 ha); the largest contains 2,200 pixels (22 ha).

Features have reproducible scan-order IDs C0001-C0400, pixel counts, area in square metres/hectares, median before/after VH and VV, median VH/VV changes, median DSM elevation, median slope, known-slope counts and the percentage of pixels decreasing in VV. IDs are specific to this raster version and may change if the classification changes.

The feature status is **exploratory_unvalidated**. The polygons have not been slope-filtered and must not be labelled confirmed flood extent. Median change per feature need not equal the difference of its date medians.

Outputs:

- `data/processed/sentinel1/lagos_dsm_slope_30m.tif`: degrees, EPSG:32631, -9999 nodata.
- `data/processed/sentinel1/lagos_candidate_review_polygons.gpkg`: layer `candidate_patches`, EPSG:32631.
- [Polygon attributes CSV](acquisition/sentinel1_candidate_polygons.csv).
- [Slope report](acquisition/sentinel1_slope_report.json): counts, method, limitations and verification.
- Output hashes and source relationships are registered in the [manifest](acquisition/manifest.json).

### Verification and QGIS review

Ten unit tests passed, including a known 45-degree plane, slope nodata propagation and diagonal component connectivity. All polygons are valid, and rasterizing their component IDs exactly reproduced the source component-label raster. The GeoPackage was reopened and checked for feature count, geometry validity and total area conservation.

Reproduce from the project root (existing outputs are protected against overwrite):

```powershell
.\.venv\Scripts\python.exe src\assess_candidate_terrain.py
```

In QGIS, add the GeoPackage above OSM and turn off the candidate rasters to avoid duplicate displays. Give the polygons a bright outline or fill. Open the attribute table and sort `area_ha` descending to inspect larger patches first. Use `patch_id` to record each location's review notes; the largest patch is not necessarily the most credible.

**Current Phase 2 status:** slope sensitivity and provisional polygon export are complete. Final rule selection, any chosen terrain filtering with renewed cleanup, a final cartographic layout distinguishing excluded/unobserved areas, and independent validation remain outstanding. Existing evidence does not support a confirmed flood map or an accuracy claim.


## C0079: Ologe Lagoon historical-water review

Review completed on 2026-10-05. The user's QGIS view places C0079 (22 ha) along the eastern Ologe Lagoon margin. Its yellow selection obscured the underlying occurrence raster, so grayscale appearance was not used to assign numerical values.

[review_c0079_water.py](../src/review_c0079_water.py) verified input hashes, rasterized the polygon using pixel-center inclusion on the original SAR grid, and sampled JRC occurrence with the same nearest-neighbor alignment used by candidate screening. All 2,200 pixel centers were clean candidates with valid occurrence values.

**Historical occurrence minimum/median/maximum: 0% / 69% / 88%.**

| Occurrence cutoff | Pixels at or above cutoff | Fraction of patch |
|---|---:|---:|
| 1% | 2,162 | 98.3% |
| 10% | 2,160 | 98.2% |
| 25% | 2,081 | 94.6% |
| 50% | 1,806 | 82.1% |
| 75% | 812 | 36.9% |
| 90% | 0 | 0.0% |

This explains why the entire patch passed the existing >=90% historical-water exclusion, despite substantial overlap with historically observed water. The median 69% is a historical occurrence value, not a probability of July 2024 flooding.

Flag C0079 as **historical-water-margin concern; flood status unresolved**. The measurements support investigating changing shoreline/water conditions rather than interpreting this feature directly as newly inundated land. They do not establish a specific cause or conclusively prove a false positive. Original candidate geometry and classification remain unchanged.

The occurrence dataset is coarser than the 10 m analysis grid, so these are not 2,200 independent historical observations. JRC v1.4 limitations and its pre-event temporal coverage still apply. Do not lower a global cutoff solely to remove this feature; evaluate historical-water sensitivity across candidates and retain independently timed validation requirements.

See [the numerical report and occurrence histogram](acquisition/sentinel1_C0079_water_review.json), registered in the manifest. Reproduce with:

```powershell
.\.venv\Scripts\python.exe src\review_c0079_water.py
```

The script protects existing reports from overwrite. Next review priority is to compare historical-water overlap across the other candidate polygons, including candidates away from lagoon margins, before choosing a final water-exclusion rule.


## Historical-water review across all candidate polygons

On 2026-10-05, [review_candidate_water.py](../src/review_candidate_water.py) extended the C0079 diagnostic to all 400 existing clean candidate features. It used the same nearest-neighbor JRC occurrence alignment, polygon pixel-center inclusion and original 10 m SAR grid. All 31,252 candidate pixels had valid occurrence samples below 90%, consistent with the already-applied exclusion.

### Polygon review flags

| Flag | Definition | Polygon count |
|---|---|---:|
| no_recorded_water | All sampled occurrence values equal zero | 338 |
| some_historical_water | Some occurrence above zero, but fewer than half the pixels have occurrence >=50% | 59 |
| majority_occ_ge50 | At least half the pixels have occurrence >=50% | 3 |

The three majority-overlap features are C0078 (0.35 ha, 60.0% of pixels at occurrence >=50%), C0079 (22 ha, 82.1%) and C0113 (0.36 ha, 100%). These flags describe historical-water overlap, not flood truth or confirmed false positives. Zero recorded occurrence is not proof that a location was dry in 2024, nor does it prove distance from a water margin.

### Exclusion sensitivity

Each row hypothetically removes pixels at or above the stated occurrence cutoff from the existing clean candidates. This is not a full rerun of classification or spatial cleanup, and areas are not validated flood extent.

| Exclude occurrence >= | Excluded candidate area (km2) | Retained candidate area (km2) |
|---|---:|---:|
| 1% | 0.5300 | 2.5952 |
| 10% | 0.4811 | 2.6441 |
| 25% | 0.3866 | 2.7386 |
| 50% | 0.2339 | 2.8913 |
| 75% | 0.0830 | 3.0422 |
| 90% (existing rule) | 0.0000 additional | 3.1252 |

No alternative cutoff was selected. A lower cutoff can remove intermittent historical water but can also omit genuine new flooding within historically water-prone areas. These measurements alone cannot select an optimal rule. Coarse resampled JRC cells are not independent 10 m observations; the earlier JRC v1.4 caveats remain.

### Review exports and verification

- `data/processed/sentinel1/lagos_candidate_water_review.gpkg`, layer `candidate_water_review`: original polygon geometry and radar/terrain attributes, plus occurrence minimum/median/maximum, cutoff overlap counts/percentages and `water_review_flag`.
- [Per-polygon CSV](acquisition/sentinel1_polygon_water_review.csv).
- [Sensitivity report](acquisition/sentinel1_water_sensitivity.json), including aggregated occurrence histogram.

Input hashes matched the manifest, polygon counts matched source candidate pixels, all samples passed validity/existing-cutoff checks, and C0079 exactly reproduced its earlier review. The exported GeoPackage was reopened and checked for valid unchanged geometries and matching overlap attributes. All three exports are registered with hashes and provenance.

Reproduce using:

```powershell
.\.venv\Scripts\python.exe src\review_candidate_water.py
```

Existing outputs are protected against overwrite. Original candidate classification and source polygons were not modified.

In QGIS, use the new GeoPackage for review, hiding the original polygon layer to avoid duplicate displays. Categorize by `water_review_flag` or inspect the occurrence fields in the attribute table. For a contrasting case, select **C0373 (15.01 ha)**, the largest feature with zero sampled historical occurrence. C0379 (10.73 ha) and C0386 (8.48 ha) are additional examples. These are review priorities, not verified dry or flooded sites.

Phase 2 remains provisional: a justified final water/terrain rule and independently timed validation are still outstanding.


## Consolidated provisional handoff (2026-10-05)

The initial visual review is consolidated into a reproducible checkpoint for independent validation. This preserves the exploratory candidate result; it does not close all Phase 2 requirements or establish a validated flood map.

### C0373 visual review

The user located C0373 (15.01 ha) in a coastal strip near the Atlantic in the southeastern portion of the displayed study area, with multiple nearby candidates. They reported no obvious match to the specific affected locations discussed in the reviewed reports. The screenshot alone does not establish land cover at acquisition time or exact administrative location.

Record **coastal candidate; no matched event evidence; reference label unknown**. Its sampled JRC occurrence is zero, but neither that fact nor absence from reporting proves dry conditions or flooding. Other surface changes remain possible; no cause has been established.

### Current review decisions

| Patch | Finding | Reference label | Action |
|---|---|---|---|
| C0079 | Eastern Ologe Lagoon margin; substantial historical-water overlap | Unknown | Seek dated shoreline/inundation evidence |
| C0373 | Coastal candidate; no matched event evidence in reviewed sources | Unknown | Seek dated imagery and a precise independent observation |

Neither feature is removed or promoted to confirmed flood. These intentionally selected review cases are not a representative accuracy sample.

### Preserved result and outstanding work

The retained baseline comprises 400 components / 3.1252 km2, from the illustrative VH rule, >=90% historical-water exclusion and 25-pixel cleanup. No slope cutoff is applied. Original rasters and polygons are unchanged.

The [baseline snapshot](validation/phase2_baseline_snapshot.json) records file hashes and settings. The [review register](validation/candidate_review_register.csv) links the two cases to polygon IDs and representative coordinates. Coordinates identify candidates, not independent flood observations.

Completed: preprocessing, grid/nodata checks, coverage diagnostics, dB change, exploratory threshold and cleanup comparisons, DSM slope sensitivity, candidate polygons, historical-water review and source limitations.

Outstanding: justified final rule selection, any resulting reprocessing, final cartographic layout explicitly showing unobserved/excluded areas, and independent validation. The next work is defined in [Phase 3: Independent validation](phase3_validation.md). Do not keep tuning thresholds merely to match anecdotal reports or visual expectations.
