# Data catalog — LAG_2024_07

Phase 1 acquisition run: **2026-10-03**. The main AOI and public baseline inputs are acquired; Phase 1 is **in progress**, not complete. Update 2026-10-04: both selected Sentinel-1 archives are downloaded and verified against ASF size/MD5, ZIP CRC and SAFE metadata; their ISO XML files are registered too. See [download verification](acquisition/sentinel1_download_verification.json). Optical imagery is inventoried but cloud-obscured. Exposure and drainage sources remain to be acquired.

## Acquired and inventoried inputs

| Dataset | Status and local location | Observation/reference date | Resolution and CRS | Source and license | Purpose / processing |
|---|---|---|---|---|---|
| Nigeria ADM0/ADM1/ADM2 | Acquired: `data/raw/boundaries/` | Source metadata: 2022 | Vector; EPSG:4326 | [geoBoundaries gbOpen](https://www.geoboundaries.org/api.html), GRID3; CC BY 4.0 | Original geometries, pinned source URLs retained |
| Lagos state and 20 LGAs | Acquired: `data/interim/boundaries/lagos_state.geojson`, `lagos_lgas.geojson` | 2022 reference boundaries | Vector; EPSG:4326; area computations in EPSG:32631 | Derived from geoBoundaries/GRID3; CC BY 4.0 | Lagos name selection; ADM2 membership assigned by >50% area overlap with Lagos in local UTM |
| Sentinel-1A IW GRD, VV+VH | 7 scenes inventoried; **selected pair downloaded and verified** in `data/raw/sentinel1/` | Search June 15–July 16, 2024 UTC; candidate pair June 21 / July 3 | 10 m pixel spacing, nominal 20 × 22 m resolution; native GRD radar geometry, not yet terrain-corrected | [ASF catalog](https://docs.asf.alaska.edu/api/keywords/), Copernicus Sentinel free/open data terms; Earthdata login for download | Exact AOI footprint intersection; paired by mission, orbit, pass, mode, polarization and product; no radiometric processing |
| Sentinel-2 L2A | 18 tile records inventoried: `docs/acquisition/sentinel2_search.json`; **imagery not downloaded** | June 15–July 15, 2024 UTC | 10/20/60 m by band; Lagos tiles UTM 31N, inspect individual asset metadata | [Earth Search](https://earth-search.aws.element84.com/v1), Copernicus Sentinel data terms | Catalog search only. July 3 tiles have >99% tile-level cloud cover; no clear optical flood observation established |
| Copernicus DEM GLO-30 | 3 source tiles in `data/raw/dem/`; mosaic `data/interim/dem/lagos_copernicus_dem30.tif` | 2011–2015 acquisition epoch; AWS 2021 release | 1 arc-second (~30 m); EPSG:4326; heights in metres, EGM2008 | [Copernicus DEM on AWS](https://registry.opendata.aws/copernicus-dem/); Copernicus DEM license, attribution required | Native-grid mosaic cropped to state bounding box. This is a DSM, not a bare-earth terrain model |
| JRC GSW v1.4 occurrence | Acquired: `data/interim/water/lagos_jrc_occurrence_1984_2021.tif` | 1984–2021 | ~30 m; EPSG:4326; values 0–100%, nodata retained | [JRC download and release notes](https://global-surface-water.appspot.com/download); Copernicus free use, credit EC JRC/Google and Pekel et al. (2016) | Remote window read and exact AOI mask, native grid; no threshold applied |
| JRC GSW v1.4 seasonality | Acquired: `data/interim/water/lagos_jrc_seasonality_1984_2021.tif` | **2021 only** (filename reflects source release; not a 37-year seasonal average) | ~30 m; EPSG:4326; 0–12 months, nodata retained | Same JRC source/license | Exact AOI subset; no permanent-water decision applied |
| CHIRPS v2 daily rainfall | Acquired: 25 rasters in `data/interim/rainfall/` | June 21–July 15, 2024 inclusive | 0.05° (~5.5 km); EPSG:4326; mm/day | [UCSB CHC](https://chc.ucsb.edu/data/chirps); public domain | Native-grid daily AOI subsets; daily totals cannot establish conditions at the SAR overpass time |
| ESA WorldCover 2021 v200 | Acquired: 2 AOI tile subsets in `data/interim/landcover/` | 2021 | ~10 m; EPSG:4326; categorical classes | [ESA WorldCover](https://esa-worldcover.org/en/data-access); CC BY 4.0 | Native-grid crop/mask. No resampling; does not capture 2021–2024 urban development |

For every downloaded file or derived raster, `docs/acquisition/manifest.json` records its source URL/path, actual retrieval timestamp, byte count, SHA-256, and processing details. Source metadata and catalog queries are saved alongside it. Retrieval time is separate from the observation date. `requirements-phase1.txt` captures the tested Python 3.11 environment. Large data remain excluded from Git; catalog metadata and scripts are retained.

## Candidate SAR pair

| Role | Scene ID | Acquisition UTC / Lagos time | Absolute / relative orbit |
|---|---|---|---|
| Before | `S1A_IW_GRDH_1SDV_20240621T053018_20240621T053047_054417_069F0A_10B1` | June 21, 05:30:18 UTC / 06:30:18 WAT | 54417 / 95 |
| Event-day candidate | `S1A_IW_GRDH_1SDV_20240703T053017_20240703T053046_054592_06A521_9E4B` | July 3, 05:30:17 UTC / 06:30:17 WAT | 54592 / 95 |

Both are descending, IW, GRD_HD, VV+VH, frame 571. Baseline: approximately 12 days. Their common catalog footprint covers **91.46%** of the state AOI. Source archive sizes total **2,974,450,206 bytes** (~2.97 GB decimal). URLs and provider MD5 checksums are in `acquisition/sentinel1_scenes.csv`. The download command validates both size and MD5 before accepting an archive.

Selection prioritizes pairs with >=80% state coverage, then the earliest event observation and shortest baseline. A July 15 descending alternative covers fractionally more area but is 12 days after the event; it is not a substitute for peak-event evidence. The July 3 ascending pair on relative orbit 103 covers only about 3.01% of the state.

**Timing remains a scientific gate:** 06:30 WAT may precede documented peak inundation. The date alone does not establish that floodwater was present at acquisition. Verify flood onset and persistence using independently timestamped evidence, and inspect valid-data coverage after terrain correction. Unobserved areas must stay nodata, never be labeled non-flood.

## QA findings

- One valid state geometry and 20 valid LGA geometries were found.
- State area is approximately 3,760.19 km² in EPSG:32631. This is the area of this specific source geometry, not an authoritative land-area statistic.
- The union of selected LGAs covers **94.43%** of the state polygon. Investigate shoreline/water and boundary differences before aggregating state/LGA areas; do not silently fill the mismatch.
- `data/interim/boundaries/sentinel1_pair_coverage.geojson` distinguishes paired coverage from unobserved area; it is not a flood map.
- Checksums and raster value checks are recorded in `acquisition/qa_report.json`. The initial run checked 40 files and 30 rasters, with no integrity/value failures.
- JRC reports known v1.4 occurrence and seasonality problems. Preserve that limitation and assess sensitivity against corrected pre-event history or independent permanent-water evidence. Do not silently replace the baseline with a 1984–2024 summary, which incorporates the target event year.
- Source grids differ. Reprojection, co-registration, resampling choices, and SAR preprocessing belong to Phase 2. Use nearest-neighbor for categorical masks and handle nodata explicitly.

## Outstanding supporting data

| Dataset | Intended source | Status / decision needed |
|---|---|---|
| Buildings, roads, infrastructure | [OpenStreetMap / Geofabrik](https://download.geofabrik.de/africa/nigeria.html); ODbL | Not acquired. Decide whether a contemporary inventory is sufficient or an event-date historical snapshot is required; do not present a 2026 extract as July 2024 exposure |
| Population | [WorldPop](https://www.worldpop.org/); inspect selected product's license and reference year | Not acquired. Choose and pin a 2024-compatible population-count product and units before exposure analysis |
| Rivers / drainage | [HydroSHEDS / HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers), plus OSM urban drains | Not acquired. Regional rivers do not represent Lagos' engineered urban drainage; record source scale and missing coverage |
| Subdaily rainfall | NASA GPM IMERG, if needed | Optional follow-up to resolve overpass-time rainfall; CHIRPS daily totals already acquired |

These entries are a backlog, not downloaded assets. Phase 1 and milestone M2 remain open until required imagery is available and the remaining supporting-data choices are resolved.

## Reproduce

See [Phase 1 runbook](phase1_acquisition.md). Saved metadata, scene inventories and tests are under `docs/acquisition/`, `src/` and `tests/`.
