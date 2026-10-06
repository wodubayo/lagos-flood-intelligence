# Phase 1 — acquisition runbook

Status on 2026-10-04: public baseline inputs and both selected Sentinel-1 archives are acquired and verified. Ancillary exposure/drainage data and event-time suitability remain outstanding. Initial Phase 2 preprocessing has started; see [the preprocessing record](phase2_preprocessing.md) for SNAP preparation, aligned Lagos rasters and valid-data coverage.

## Environment

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-phase1.txt
```

The existing `.venv` already contains the tested Phase 1 packages. This small environment does not yet install all notebook/ML dependencies from the general `requirements.txt`.

## Public acquisition

```powershell
.\.venv\Scripts\python.exe src\acquire_phase1.py core
```

The command acquires boundaries, searches Sentinel-1, downloads three DEM tiles, crops JRC water layers, inventories Sentinel-2, and crops 25 daily CHIRPS rasters plus two WorldCover tiles. Individual steps can be rerun:

```powershell
.\.venv\Scripts\python.exe src\acquire_phase1.py boundaries
.\.venv\Scripts\python.exe src\acquire_phase1.py scenes
.\.venv\Scripts\python.exe src\acquire_phase1.py terrain
.\.venv\Scripts\python.exe src\acquire_phase1.py water
.\.venv\Scripts\python.exe src\acquire_phase1.py optical
.\.venv\Scripts\python.exe src\acquire_phase1.py rainfall
.\.venv\Scripts\python.exe src\acquire_phase1.py landcover
```

Source files are reused only when their recorded SHA-256 matches. Interrupted downloads retain a `.part` file and restart on the next run. The boundary source revision is pinned by the saved provider metadata. Searches are refreshed when rerun, so preserve/commit a catalog snapshot used for an analysis. Run steps serially because they update a shared manifest.

## How the Sentinel-1 scene IDs were found

The scene IDs are provider-assigned product names returned by ASF's catalog. We obtained them by searching for imagery around the Lagos flood event, then comparing acquisition conditions and geographic coverage.

### 1. Define the area and search window

The acquisition script used the bounding rectangle of the downloaded Lagos State boundary for its ASF search, then filtered the returned footprints against the actual state polygon.

| Search parameter | Value |
|---|---|
| Satellite | Sentinel-1A |
| Start | June 15, 2024, 00:00:00 UTC |
| End | July 16, 2024, 00:00:00 UTC |
| Product | GRD_HD: high-resolution Ground Range Detected |
| Mode | IW: Interferometric Wide swath |
| Polarization | VV + VH |
| Spatial filter | Intersects the Lagos bounding rectangle |

The complete API URL, coordinates and parameters are preserved in [sentinel1_query.json](acquisition/sentinel1_query.json). The [acquisition script](../src/acquire_phase1.py) performs this search through the [ASF Search API](https://docs.asf.alaska.edu/api/keywords/).

### 2. Compare the returned scenes

The saved search contains **7 scenes** intersecting Lagos. The script compared before-event scenes with during/after-event scenes, requiring the same satellite, relative orbit, flight direction, mode, polarization and product type.

Four candidate pairs were found. Ranking prioritizes pairs covering at least 80% of the state, then the earliest event observation, shortest temporal baseline and largest common footprint. The 80% threshold is a project selection rule, not an official sensor requirement.

See [all search results](acquisition/sentinel1_search.geojson), [the scene inventory](acquisition/sentinel1_scenes.csv), and [candidate pairs](acquisition/sentinel1_pairs.json).

### 3. Select the candidate pair

Before-event scene:

```text
S1A_IW_GRDH_1SDV_20240621T053018_20240621T053047_054417_069F0A_10B1
```

Event-day scene:

```text
S1A_IW_GRDH_1SDV_20240703T053017_20240703T053046_054592_06A521_9E4B
```

Both use **descending relative orbit 95**, IW mode and VV/VH polarization. They are approximately **12 days apart**, and their common catalog footprints cover **91.46% of the Lagos AOI**. Matching observation conditions makes the scenes more comparable for radar change detection; preprocessing and valid-pixel inspection are still required.

A July 15 alternative has slightly greater footprint coverage but is much later than the event. The event-day pair is therefore preferred. The decision and coverage fraction are recorded in [sentinel1_selected_pair.json](acquisition/sentinel1_selected_pair.json).

### 4. Read a scene ID

Using the July 3 scene as an example:

| Component | Meaning |
|---|---|
| `S1A` | Sentinel-1A satellite |
| `IW` | Interferometric Wide swath acquisition mode |
| `GRDH` | Ground Range Detected, high-resolution class |
| `1SDV` | Processing level 1; standard product; dual VV/VH polarization |
| `20240703T053017` | Acquisition start: July 3, 2024, 05:30:17 UTC |
| `20240703T053046` | Acquisition end: July 3, 2024, 05:30:46 UTC |
| `054592` | Absolute orbit number |
| `06A521` | Mission data-take identifier |
| `9E4B` | Product unique identifier |

The filename contains the **absolute orbit**, not relative orbit 95. The relative orbit is available in the catalog/product metadata. These fields follow the [official Sentinel-1 naming convention](https://sentiwiki.copernicus.eu/web/s1-products).

### 5. Reproduce the search in Vertex

To discover scenes yourself, select **Sentinel-1** in Vertex's Geographic Search, define the Lagos AOI, and apply the dates and filters above. Drawing a different AOI or using different date endpoints can change the results.

To retrieve the already-selected pair, choose **List Search**, select **Scene**, paste the two full IDs above on separate lines, and search. Select each scene's **GRD_HD** ZIP product. List Search retrieves known scenes; the geographic query is how we originally discovered them. See the [Vertex user guide](https://docs.asf.alaska.edu/vertex/manual/).

**Scientific limitation:** the July 3 acquisition was at **06:30:17 WAT (Lagos time)**. An event-day date does not prove floodwater was present at that time. Independently timestamped evidence is still needed to establish flood onset and persistence. Areas outside the paired coverage must remain unobserved/nodata, not be labeled non-flood.


## Sentinel-1 download

ASF requires a free [NASA Earthdata account](https://urs.earthdata.nasa.gov/). Sign in to [ASF Vertex](https://search.asf.alaska.edu/) and complete its Earthdata authorization. Use the exact scene IDs in [the catalog](data_catalog.md).

Two options:

1. Download both recommended ZIP archives through Vertex into `data/raw/sentinel1/`, keeping their original filenames. Verify their sizes and MD5 against `acquisition/sentinel1_scenes.csv` before using them. Register browser downloads using `python src/register_sentinel1.py`; this checks provider size/MD5, ZIP CRC, SAFE metadata and required VV/VH components before updating the manifest.
2. Generate an Earthdata bearer token in your account and provide it locally as `EARTHDATA_TOKEN`, then run:

```powershell
.\.venv\Scripts\python.exe src\acquire_phase1.py sar-download
```

The script reads the token from the environment, downloads the recommended pair, checks archive sizes/provider MD5, and records SHA-256. Do not put tokens in source code or chat. Authentication-dependent downloading has not yet been exercised in this project; the inventory and unauthenticated downloads have been tested.

If the provider rejects a token, use Vertex rather than changing SSL verification or embedding credentials in URLs. The two selected archives total about 2.97 GB; allow additional disk space for SAFE extraction and later preprocessing.

## Verify and inspect

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src\validate_phase1.py
.\.venv\Scripts\python.exe -m pip check
```

QA checks source/derived checksums, valid boundary geometries/counts, readable rasters, finite valid values, JRC ranges, and the daily rainfall count. It does not prove scientific suitability or flood occurrence. The tests protect local-time event classification, same-orbit/pass pairing, footprint intersection, and preference for event-day coverage over tiny later coverage gains.

Load these files in QGIS for spatial inspection:

- `data/interim/boundaries/lagos_state.geojson`
- `data/interim/boundaries/lagos_lgas.geojson`
- `data/interim/boundaries/sentinel1_pair_coverage.geojson`
- `data/interim/dem/lagos_copernicus_dem30.tif`
- `data/interim/water/lagos_jrc_occurrence_1984_2021.tif`
- `data/interim/landcover/lagos_worldcover2021_N06E003.tif` and the adjacent `N06E000` tile

Use EPSG:32631 for local area/distance calculations. The acquired rasters remain on their native grids; do not calculate pixel-wise change until Phase 2 has aligned them appropriately.

## Before Phase 2

- Completed 2026-10-04: both candidate SAR archives downloaded, verified and registered.
- Establish whether flooding was present at **06:30 WAT on July 3**, rather than assuming it from the calendar date.
- Inspect the 8.54% of the AOI outside the paired footprint and resolve scope/coverage explicitly.
- Investigate the 5.57% state/LGA outline mismatch before reporting LGA statistics.
- Resolve the remaining OSM, WorldPop and drainage entries in the data catalog, or explicitly document their deferral from the minimum baseline dataset.
- Review JRC v1.4 caveats and define sensitivity checks for the permanent-water mask.

No flood extent, validation accuracy, neural-network result, or statewide exposure estimate is produced by Phase 1.

## What is ESA SNAP?

**SNAP** stands for **Sentinel Application Platform**. It is ESA's free software for viewing and processing satellite imagery.

For this project, SNAP's Microwave Toolbox provides the tools to calibrate, reduce noise, and geographically correct our Sentinel-1 radar images. We will process both acquisition dates consistently, then compare the prepared images and map potential flooding in QGIS.

SNAP prepares the satellite measurements for analysis; the resulting change map still needs independent evidence to establish whether it represents flooding.

Reference: [ESA SNAP overview](https://eo4society.esa.int/resources/snap/).

## Next: prepare the SAR baseline

The downloaded ZIPs passed integrity and metadata checks on 2026-10-04. The report is in [sentinel1_download_verification.json](acquisition/sentinel1_download_verification.json). ISO metadata passed XML parsing and has local SHA-256 records; no provider checksum was available for those sidecars.

1. Install ESA SNAP with Sentinel-1 processing support if it is not already available. QGIS is available locally; SNAP was not found in the standard Program Files location.
2. Open both original GRD ZIP products in SNAP and inspect their footprints, VV/VH bands and acquisition metadata. Preserve the source archives.
3. Define and document the same preprocessing settings for both dates: precise orbit information, appropriate border/thermal-noise handling, radiometric calibration, speckle treatment, and terrain correction. Inspect existing processing flags before applying noise corrections.
4. Export calibrated VV/VH backscatter on a common grid in EPSG:32631, using the same DEM, pixel spacing and grid alignment. Preserve nodata and document conversion from linear backscatter to dB. Ten-metre pixel spacing is not ten-metre independent spatial resolution.
5. Load the four outputs (VV/VH before and event day) in QGIS for alignment and coverage checks before calculating change.

Use the [ESA Sentinel-1 time-series tutorial](https://step.esa.int/docs/tutorials/S1TBX%20Time-series%20analysis%20with%20Sentinel-1.pdf) as a processing reference. Exact parameters must be recorded when the preprocessing workflow is established; this checklist is not an executed processing graph.

In parallel, collect independently timestamped evidence of flooding at the July 3 overpass (06:30 WAT). Integrity verification establishes that the files are intact, not that they capture peak inundation. The baseline remains exploratory until this timing question is resolved.
