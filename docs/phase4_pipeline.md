# Phase 4 - Pythonize the GIS Workflow

Started: 2026-10-08. Status: complete for the current Lagos event; broader multi-event support remains future work.

## Scope and scientific status

Phase 4 in the implementation plan concerns reproducibility, not GeoAI training. Following the user's instruction to proceed, this phase automates the existing exploratory baseline despite the unresolved Phase 3 validation gate. It does not certify flood detection or authorize Phase 5 training. July 3 MODIS classifications were insufficient at every sampled Lagos pixel; independent quantitative validation remains unavailable.

## Pipeline stages

The existing scripts already perform substantial processing. The new src/run_baseline.py entry point exposes six stages in dependency order:

| Stage | Implementation | Purpose |
|---|---|---|
| align | prepare_sentinel1_pair.py | Align SNAP terrain-corrected linear exports, clip to AOI, preserve common validity |
| change | analyze_sentinel1_change.py | Derive positive-support masks, dB bands and July-minus-June changes |
| candidates | explore_sentinel1_thresholds.py | Evaluate thresholds, exclude historical water, remove small components |
| audit | audit_sentinel1_candidates.py | Generate candidate pixel review table and backscatter/DSM statistics |
| terrain | assess_candidate_terrain.py | Calculate slope sensitivity and exact candidate review polygons |
| lga | summarize_lga_change.py | Summarize observed radar changes and candidate areas by LGA |

The original methods are retained: exploratory preview VH threshold -21 dB, change <= -3 dB, June VH > -21 dB, JRC occurrence >=90 excluded, unknown water excluded, and minimum 25 pixels with 8-connectivity. Outputs remain unvalidated candidates.

## Commands

Run from the project root in PowerShell:

~~~powershell
.\.venv\Scripts\python.exe src/run_baseline.py
.\.venv\Scripts\python.exe src/run_baseline.py --verify
~~~

The first command reports file presence and stage readiness. The second checks available SHA-256 entries in the manifest. Unregistered assets are explicitly listed; presence alone is not content verification.

For a stage whose inputs exist and whose outputs do not:

~~~powershell
.\.venv\Scripts\python.exe src/run_baseline.py --run align
.\.venv\Scripts\python.exe src/run_baseline.py --run change
.\.venv\Scripts\python.exe src/run_baseline.py --run candidates
.\.venv\Scripts\python.exe src/run_baseline.py --run audit
.\.venv\Scripts\python.exe src/run_baseline.py --run terrain
.\.venv\Scripts\python.exe src/run_baseline.py --run lga
~~~

Each invocation runs one stage. A run checks available input hashes first and refuses any existing stage output. Missing inputs, incomplete output sets and hash mismatches fail the check. There is no automatic deletion, overwrite or assumption that existing outputs can be safely skipped.

## Current boundary of automation

The six-stage analytical rebuild can use the manually exported terrain-corrected inputs or the DIMAP products generated from the raw ZIPs by `run_snap_pair.py`. In SNAP mode, the isolated rebuild exports VH/VV GeoTIFF inputs, aligns June to the saved reference-grid coordinates, runs all six analytical stages, and compares the regenerated outputs with the reviewed baseline. Terrain sensitivity, polygon generation and LGA summaries are integrated through their existing scripts. Independent evidence and historical-water review remain separate diagnostics. Terrain filtering has not been applied to the candidate baseline.

## Remaining Phase 4 work

1. Default event and supported parameter configuration are implemented; broader multi-event input mapping remains future work.
2. Review whether additional independent-evidence and water-review diagnostics need pipeline integration.
3. Terrain, polygon and LGA stages now have declared dependencies; maintain them as methods evolve.
4. All six stages now have execution logs and processing-script hashes in isolated runs.
5. The raw-ZIP SNAP graph has been verified against the manual workflow for both dates and both Sigma0 bands; the isolated end-to-end rebuild reproduces all 24 reviewed outputs.
6. Retain the unresolved validation status in every report.

The core baseline has now been regenerated successfully. The current-event computational workflow is reproducible; this establishes computational reproducibility, not scientific validation.


## Isolated rebuild result - 2026-10-08

Run phase4_20261008 passed. All 11 generated rasters match the reviewed baseline exactly in pixel values, grids, nodata, data types and band descriptions. This covers two linear rasters, the common-valid mask, two dB rasters, delta, positive-support mask, coverage diagnostic and three candidate/threshold rasters. All 12 unit tests passed, including deliberately altered pixel/nodata and shifted-grid checks.

Original baseline files, source inputs and the project acquisition manifest retained their pre-run hashes. The run used physical input copies, its own manifest and copied processing scripts in outputs/runs/phase4_20261008/. It captures source hashes (including previously unregistered SNAP exports and DIM files), script hashes, Python/library/GDAL versions and individual stage logs. These new source hashes document the files used now; they do not retrospectively verify their earlier provenance.

The durable [rebuild report](acquisition/phase4_rebuild_report.json) records the checks. Full stage logs and rebuilt artifacts remain under the ignored outputs/runs directory. Numerical raster content is compared exactly; timestamped report bytes and TIFF encoding bytes are not required to match.

To reproduce in a new directory:

~~~powershell
.\.venv\Scripts\python.exe src/rebuild_baseline.py --run-id phase4_repeat_01
~~~

Use a new run ID each time. Existing run directories are refused, including failed runs, which remain available for diagnosis. The tool copies the current event's declared inputs and executes align, change, candidates, audit, terrain and lga in order, stopping on any failure. It does not yet support a configurable new event, rerun SNAP from raw ZIPs.


## Diagnostic integration and reproduction - 2026-10-10

The six-stage isolated run phase4_diagnostics_20261010_verified passed all 24 output comparisons:

- 12 rasters: exact pixels, grids, data types, nodata and band descriptions.
- 4 CSV tables: exact file content.
- 2 GeoPackages: all keyed attributes and geometries match exactly, including 400 candidate patches and 20 LGA features; database metadata is not compared byte-for-byte.
- 6 JSON reports: complete content matches after excluding only the top-level creation timestamp.

The first diagnostic run reproduced the analytical outputs but found three additional QA fields in the original alignment report. These checks are now executable in prepare_sentinel1_pair.py: full common-mask consistency, band/nodata checks and verification of 26,804,975 common-valid pixels. A fresh full run then reproduced those fields as well. The first run remains in outputs/runs/phase4_diagnostics_20261010 for diagnosis; it is not represented as a passing report comparison.

All 16 tests passed. They include changed vector attributes/geometries, altered raster pixels/nodata, shifted grids, dependency ordering, JSON timestamp versus substantive changes, and incorrect common-valid support. Fiona 1.10.1, already declared in requirements.txt, was installed in the project environment for GeoPackage layer inspection. The verified run records its dependency versions.

Original inputs, baseline outputs and the main acquisition manifest retained their pre-run hashes. See the [diagnostic rebuild report](acquisition/phase4_diagnostics_rebuild_report.json). Stage logs, copied scripts/inputs and generated artifacts remain in the isolated run directory.

This completes terrain/polygon/LGA integration for the existing event. Slope remains a sensitivity diagnostic; no slope cutoff was applied and polygons remain exploratory candidates. No independent validation or GeoAI training was performed. Next work is explicit event/parameter configuration and a decision on the manual SNAP preprocessing boundary.


## Event and parameter configuration - 2026-10-10

[config/baseline.json](../config/baseline.json) is the default settings file. The loader rejects unknown keys, unsupported event/method changes, duplicate or non-finite sweep values, invalid cleanup sizes, preview values outside their sweep, and more than 254 threshold combinations (255 is reserved for excluded pixels).

Editable settings are:

- Candidate darkening and drop threshold sweeps.
- The selected darkening/drop thresholds.
- Cleanup sensitivity sizes and selected minimum patch size.
- Terrain slope sensitivity cutoffs.

Changing slope cutoffs changes diagnostic summaries, not the candidate mask. Connectivity remains eight; historical-water exclusion remains 90%; grid spacing remains 10 m in EPSG:32631. The selected drop must remain <= -3 dB because the current LGA diagnostic checks candidates against its 3 dB decrease count. Less restrictive sensitivity thresholds may still be included in the sweep.

Event ID, dates and AOI are explicit in the file, but only LAG_2024_07 with the existing June 21/July 3 inputs is supported. Other stages still use event-specific filenames, June/July labels and Lagos assumptions. A different date/AOI is rejected rather than silently processing the old files. Multi-event input mapping remains future work.

### Isolated configuration use

Keep the default configuration as the reviewed baseline. Pass a separate JSON file for a supported parameter variant:

~~~powershell
.\.venv\Scripts\python.exe src/rebuild_baseline.py --run-id config_check_01 --config config/baseline.json
~~~

The runner validates settings before creating the run, writes the resolved JSON to its own config/baseline.json, copies the configuration loader with the processing scripts, and records the resolved settings plus the original configuration file hash in the run report. Processing stages read this run-local configuration.

The rebuild tool remains a comparison against the reviewed baseline. Changed settings may legitimately produce comparison_failed and a nonzero exit code even when all processing stages succeed; consult the individual comparisons and stage logs. That status does not measure flood accuracy. The current candidate-audit code also requires a nonempty candidate selection; extreme parameter choices may fail that stage.

The single-stage run_baseline.py entry point reads the repository's default configuration. Use an isolated rebuild for parameter variants, preserving the reviewed outputs.


### Configuration verification result

Run phase4_config_20261010 reproduced all 24 reviewed outputs with the default JSON configuration. Original inputs, outputs and the main manifest retained their hashes. All 22 tests passed, including an isolated import test that confirms both extraction and auditing consume an alternate run-local rule (-24 dB, -4 dB, 100 pixels) rather than repository defaults. That import test verifies configuration routing; it is not a full-data evaluation of the alternate rule.

See the [configuration rebuild report](acquisition/phase4_config_rebuild_report.json). The six-stage analytical rebuild still begins at manual SNAP exports. Raw-ZIP preprocessing has a separate graph runner, but it is not yet accepted or integrated into that rebuild. Multi-event support is also future work. Independent flood validation remains unresolved.


## SNAP graph trial review - 2026-10-11

Both graph_trial_01 logs end with done and no GPT process remained at inspection. Full-scene comparisons were made between the new DIMAP Sigma0 band images and the corresponding manual linear GeoTIFF exports. Both dates have matching raster dimensions, EPSG:32631 and transforms within 1e-8 map units; the DIM metadata declares source zero as nodata. Band order was taken from the original DIM metadata.

| Date | VH pixels beyond numerical tolerance | VV pixels beyond numerical tolerance | Zero/nodata support differences per band |
|---|---:|---:|---:|
| June 21 | 159,834,786 | 160,546,902 | 49 |
| July 3 | 161,147,169 | 161,729,374 | 71 |

Numerical comparison used numpy.isclose with rtol=1e-5 and atol=1e-7 on linear Sigma0, with manual exports as the first argument. This is a diagnostic tolerance, not a scientific acceptance criterion. Total compared pixels per band were 702,943,110 for June and 703,057,806 for July, including zero/nodata pixels. There were no differences in finite/non-finite support. The report also contains exact-difference counts, maxima and means.

Saved processing-parameter comparison found a calibration auxFile mismatch for June: manual Latest Auxiliary File versus graph Product Auxiliary File. July's saved processing parameters matched across the compared processing operators, yet its pixels also differed. Therefore the June setting difference cannot, by itself, explain the two-date result. Matching listed parameters does not establish identical intermediate values, auxiliary data or execution behavior.

The graph executed successfully, but has not been accepted as a numerical replacement for the manual baseline. Existing inputs and reviewed outputs were not modified. A July stage-by-stage comparison below locates the first pixel-value divergence at terrain correction; its cause remains unresolved. No flood-accuracy conclusion follows from this comparison.

See [full-scene comparison](acquisition/snap_graph_trial_01_comparison.json) and src/compare_snap_trial.py. The script currently targets graph_trial_01 and refuses to overwrite its report.


### Graph settings clarification

The user clarified that the XML mapProjection is correct and that both VH and VV were selected in Calibration; the first screenshot clipped the list control. The graph and manual DIM metadata agree on UTM Zone 31 / WGS84 (EPSG:32631), selected VH/VV polarizations, thermal-noise settings, Refined Lee settings and terrain resampling/grid settings.

One confirmed parameter mismatch remains: Calibration auxFile is Product Auxiliary File in the graph and July manual DIM, but Latest Auxiliary File in the June manual DIM. The June graph run therefore has a plausible calibration provenance difference. July's compared parameters match, yet its pixel values also differ, so auxiliary-file selection cannot explain the full discrepancy.

The comparison report was corrected to reflect this clarification. The July stage comparison below shows exact agreement through Refined Lee and the first value differences at terrain correction; the cause remains unresolved.

### Raw-ZIP SNAP graph diagnostic - 2026-10-11

To locate the first processing-stage difference, a diagnostic graph reran the July 3 ZIP and wrote checkpoints after thermal-noise removal, calibration, and Refined Lee filtering, plus the normal terrain-corrected output. The corresponding manual DIMAP products were available for direct pixel comparison. Both bands matched exactly at each of the first three checkpoints: 491,414,658 pixels per band, with equal dimensions and georeferencing. This confirms that the graph reproduces the manual inputs to terrain correction bit for bit; a wrong manual setting is not evident in those stages.

The first pixel-value differences appear after terrain correction. The manual and graph outputs have the same 24,519 Ã— 28,674 grid, 10 m spacing, and semantically equivalent EPSG:32631 CRS; their WKT labels differ. The manual DIMAP and its GeoTIFF export yield the same reported differences against the graph product, so GeoTIFF export does not explain them. The recorded terrain-correction settings in both DIM histories match, including Copernicus 30 m DEM, bilinear image and DEM resampling, UTM Zone 31 / WGS84, sea nodata masking, and both Sigma0 bands.

| Band | Pixels outside tolerance | Pixels with abs. diff > 0.1 | Mean abs. diff | Maximum abs. diff (UTM 31N pixel center) |
|---|---:|---:|---:|---|
| VH | 161,147,169 / 703,057,806 | 21 | 0.00000531 | 0.72099 (546,245.75 E; 710,111.42 N) |
| VV | 161,729,374 / 703,057,806 | 3,706 | 0.00003335 | 18.27811 (632,265.75 E; 720,581.42 N) |

The tolerance (`rtol=1e-5`, `atol=1e-7`) is only a comparison diagnostic. The VV difference exceeds 1.0 at 105 pixels; VH has no pixels above 1.0. At the largest VV difference, manual and graph values are 412.714 and 394.436, respectively. These values are localized outliers within the scene; their cause and local context still need inspection. The available processing histories do not show a terrain-correction parameter mismatch, so they do not substantiate the hypothesis that the manual run used incorrect recorded settings. The DEM cache tiles present locally were last modified on October 4, but the manual run has no DEM-tile checksums; this is suggestive, not proof, that both runs used identical DEM bytes. The exact cause of terrain-correction differences remains unresolved, and the graph is not accepted as a numerical replacement for the reviewed manual products.


The diagnostic can be rerun for July 3 with SNAP GPT from the project root:

~~~powershell
$run = "outputs/snap_runs/graph_trial_02_stages"
& "C:\Program Files\esa-snap\bin\gpt.exe" graphs/sentinel1_preprocess_stages.xml `
  -Pinput="data/raw/sentinel1/S1A_IW_GRDH_1SDV_20240703T053017_20240703T053046_054592_06A521_9E4B.zip" `
  -Poutput="$run/S1A_20240703_Orb_TNR_Cal_Spk_TC.dim" `
  -PstageOrbit="$run/S1A_20240703_Orb.dim" `
  -PstageTNR="$run/S1A_20240703_Orb_TNR.dim" `
  -PstageCal="$run/S1A_20240703_Orb_TNR_Cal.dim" `
  -PstageSpk="$run/S1A_20240703_Orb_TNR_Cal_Spk.dim" `
  -q 4 -c 1G
~~~

The saved stage graph and scripts are [sentinel1_preprocess_stages.xml](../graphs/sentinel1_preprocess_stages.xml), [compare_snap_stages.py](../src/compare_snap_stages.py), [compare_snap_tc_dim.py](../src/compare_snap_tc_dim.py), and [compare_snap_tc.py](../src/compare_snap_tc.py). The [stage report](acquisition/snap_graph_trial_02_stage_comparison.json), [direct DIMAP comparison](acquisition/snap_graph_trial_02_tc_dim_comparison.json), and [GeoTIFF comparison](acquisition/snap_graph_trial_02_tc_value_comparison.json) preserve the full statistics. The temporary SNAP outputs remain under the ignored `outputs/snap_runs/graph_trial_02_stages/` directory.





### Terrain-correction repeatability check - 2026-10-15

The saved July 3 graph and manual Refined Lee DIMAP inputs were compared at the file level. Both 1,965,658,632-byte Sigma0 images, their headers, all five tie-point-grid image/header pairs, and both vector-data CSVs have identical SHA-256 hashes. Their `.dim` wrappers differ materially: the graph output after Thermal Noise Removal records `orbit_state_vector_file=-` and 17 original orbit vectors (05:29:09–05:31:49), while the manual product records the Sentinel Precise EOF file and 49 precise vectors (05:30:07–05:30:55). The graph Apply-Orbit-File checkpoint itself contains those same 49 precise vectors as the manual product.

Terrain correction was run a second time with the same graph, SNAP GPT, and graph-produced Refined Lee DIMAP source. The two output band `.img` files match the first graph-on-graph run byte-for-byte. That establishes repeatability for the graph run under the current environment. Separately, running the same graph against the manual Refined Lee DIMAP reproduces the manual terrain-corrected bands exactly (703,057,806 pixels per band, zero differing pixels).

A controlled metadata probe copied only `orbit_state_vector_file` and `Orbit_State_Vectors` from the graph Apply-Orbit-File checkpoint into a diagnostic copy of the graph Refined Lee `.dim` wrapper, leaving every backing raster and tie-point-grid file unchanged. Terrain correction then matched the manual output exactly in both bands (703,057,806 pixels per band; zero differing pixels). Reapplying Apply-Orbit-File to the already processed graph product did not restore the precise vectors and retained the original terrain-correction discrepancy. This strongly identifies Thermal Noise Removal resetting the precise orbit metadata as the cause. The raw-ZIP graph still needs a reproducible metadata-preservation step before it can replace manual outputs. See the [orbit metadata probe report](acquisition/snap_graph_trial_05_orbit_metadata_probe.json), [repeatability report](acquisition/snap_graph_trial_04_tc_repeat_comparison.json), [manual-input check](acquisition/snap_graph_trial_03_manual_disk_input_comparison.json), and [graph-input check](acquisition/snap_graph_trial_03_tc_disk_input_comparison.json).


### Raw-ZIP pair run with precise-orbit metadata preservation - 2026-10-16

The updated [pair runner](../src/run_snap_pair.py) completed the June 21 and July 3 raw ZIPs. It runs the saved intermediate graph, restores the precise orbit provenance and 49 orbit vectors from each Apply-Orbit-File checkpoint into a diagnostic copy of the Refined Lee DIMAP metadata, then runs terrain correction. The resume option allowed the run to continue after a Python metadata-insertion bug without repeating the already completed June intermediate processing.

Both terrain-corrected outputs match their manual SNAP products exactly for both Sigma0_VH and Sigma0_VV: each date has zero differing pixels, zero zero-mask differences, and zero pixels outside tolerance. This verifies that preserving the precise orbit metadata before terrain correction reproduces the existing manual products for this pair. The run took 8.42 minutes for June terrain correction and 8.54 minutes for July; intermediate graph time was 10.95 minutes for June and 20.50 minutes for July.

The generated products, logs, and complete per-stage report are in `outputs/snap_runs/graph_trial_05_orbit_metadata_fix/`. The report is [run_report.json](../outputs/snap_runs/graph_trial_05_orbit_metadata_fix/run_report.json). These results validate reproducibility against the manual outputs, not flood classification accuracy.

### End-to-end raw-ZIP rebuild - 2026-10-16

`src/rebuild_baseline.py` now accepts `--snap-run`. In an isolated run directory it exports both Sigma0 bands from each terrain-corrected SNAP DIMAP product, uses the saved June reference-grid coordinates to avoid sub-nanometre transform-rounding changes during July resampling, and then runs the existing six analytical stages. The source SNAP products, reviewed inputs, baseline outputs and main acquisition manifest are left unchanged.

Run it with a new ID for each rebuild:

~~~powershell
.\.venv\Scripts\python.exe src/rebuild_baseline.py `
  --run-id phase4_snap_repeat_01 `
  --snap-run outputs/snap_runs/graph_trial_05_orbit_metadata_fix
~~~

Run `phase4_snap_end_to_end_02` passed. Both exported inputs matched their manual GeoTIFFs pixel for pixel, with equal CRS, dimensions, and transforms after a 1e-8 m comparison tolerance. The six analytical stages completed and all 24 reviewed outputs matched: raster pixels and metadata, table values, JSON content, vector attributes and geometry. The comparison tolerances are recorded in the report. The original baseline outputs and acquisition manifest remained unchanged. See the [end-to-end rebuild report](../outputs/runs/phase4_snap_end_to_end_02/rebuild_report.json).

This completes the reproducible pipeline for the current Lagos event. It does not resolve independent flood validation or support a claim of flood-detection accuracy. Phase 5 model training remains deferred until Phase 3 validation has a defensible reference target. Multi-event input mapping is future work.
