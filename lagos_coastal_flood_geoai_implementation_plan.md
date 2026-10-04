# Lagos Coastal Flood GeoAI — Implementation Plan

## Project Objective

Build a reproducible GeoAI pipeline that detects, analyzes, and predicts flood risk in Lagos using Earth-observation and geospatial data, initially centered on the **July 3–4, 2024 Lagos flood event**, with an architecture capable of expanding to Nigeria's other coastal states.

The project should answer four questions:

1. **What flooded?** — Flood detection
2. **How well can we detect it?** — GeoAI + validation
3. **Where is most susceptible?** — Flood susceptibility
4. **What is at risk?** — Exposure / risk intelligence

The project is designed first as a technically strong GeoAI portfolio project and later as the foundation for a flood-intelligence product or service.

---

## Phase 0 — Project Foundation

### Goal

Make the project reproducible from day one.

### Repository Structure

```text
lagos-flood-intelligence/
├── README.md
├── docs/
│   ├── methodology.md
│   ├── data_catalog.md
│   └── events/
│       └── LAG_2024_07.md
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── qgis/
├── notebooks/
├── src/
├── models/
├── outputs/
│   ├── maps/
│   ├── metrics/
│   └── figures/
├── tests/
├── docker/
└── requirements.txt
```

### Event Definition

```text
Event ID: LAG_2024_07
Event: Lagos July 2024 Flood
Primary Date: July 3, 2024
AOI: Lagos State, Nigeria

Initial validation locations:
- Iyana Oworo
- Lekki
- Ibeju-Lekki

Initial hazard classification:
- Pluvial / urban flooding
- Potential lagoon/coastal interaction
```

### Deliverable

- Git repository
- Event documentation
- Initial methodology document

---

# Phase 1 — Data Acquisition

## Goal

Assemble the minimum dataset required to reconstruct the July 2024 flood event.

## 1.1 Administrative Boundaries

Acquire:

```text
Nigeria
└── Lagos State
    └── LGA boundaries
```

Potential sources include geoBoundaries, HDX/OCHA, and authoritative Nigerian sources where available.

## 1.2 Sentinel-1 SAR

Identify Sentinel-1 acquisitions immediately before and during/after the July 3, 2024 flood.

Preferred characteristics:

```text
Mission: Sentinel-1
Product: GRD
Mode: IW
Polarization: VV + VH
Orbit: Same relative orbit where possible
```

Record for every scene:

- Scene ID
- Acquisition date/time
- Orbit
- Relative orbit
- Ascending/descending pass
- Polarization
- Spatial resolution
- Source/download location

The before and after scenes should be geometrically and observationally comparable.

## 1.3 Supporting Datasets

| Dataset | Purpose |
|---|---|
| Sentinel-2 | Optical imagery and land context |
| NASADEM / Copernicus DEM | Elevation and terrain |
| JRC Global Surface Water | Permanent-water masking |
| GPM / CHIRPS | Rainfall |
| ESA WorldCover | Land cover |
| OpenStreetMap | Buildings, roads and infrastructure |
| WorldPop | Population |
| River/drainage datasets | Hydrological context |

### Data Catalog

Create `docs/data_catalog.md` containing:

- Dataset
- Source
- Acquisition date
- Spatial resolution
- CRS
- License
- Purpose
- Processing performed

### Deliverable

A documented, reproducible project dataset.

---

# Phase 2 — QGIS Baseline Flood Detection

## Goal

Produce the first scientifically defensible flood map **without machine learning**.

This becomes the baseline against which GeoAI models are evaluated.

## 2.1 SAR Preprocessing

Apply the same preprocessing to before and after Sentinel-1 scenes.

```text
Sentinel-1 GRD
      ↓
Apply orbit information
      ↓
Border-noise removal
      ↓
Radiometric calibration
      ↓
Speckle filtering
      ↓
Terrain correction
      ↓
Convert backscatter to dB
      ↓
Clip to Lagos AOI
```

Retain:

```text
VV_before
VH_before
VV_after
VH_after
```

## 2.2 Change Detection

Calculate change layers such as:

```text
ΔVV = VV_after - VV_before
ΔVH = VH_after - VH_before
```

Also investigate ratio-based change detection.

Significant decreases in radar backscatter become candidate flood pixels.

## 2.3 Thresholding

Convert the change result into a binary candidate mask:

```text
0 = Non-flood
1 = Potential flood
```

Test objective or reproducible threshold-selection approaches rather than relying only on visual selection.

## 2.4 Permanent-Water Removal

Use JRC Global Surface Water to distinguish existing water bodies from newly inundated areas.

```text
Detected Water
      -
Permanent Water
      =
Potential Flood
```

This is particularly important around Lagos Lagoon.

## 2.5 Terrain Filtering

Use DEM-derived:

- Elevation
- Slope

to remove detections that are physically implausible.

## 2.6 Post-processing

Investigate:

- Connected-component filtering
- Minimum mapping units
- Morphological operations
- Removal of isolated pixels

### Major Deliverable #1

**July 2024 Lagos Flood Extent — SAR Baseline**

Export:

- GeoTIFF flood raster
- GeoPackage/vector flood extent
- Publication-quality map
- Flooded-area statistics

---

# Phase 3 — Validation

## Goal

Determine whether the detected flooding corresponds to independently observed flooding.

## Validation Sources

Build evidence from:

- NEMA reports
- GDACS/GloFAS
- News reports
- Geolocated photographs/video
- Scientific publications
- Independent satellite-derived flood products

## Validation Dataset

Create:

```text
validation_points.gpkg
```

Suggested attributes:

```text
location
latitude
longitude
date
source
source_url
flood_observed
confidence
notes
```

Example:

```text
Location: Iyana Oworo
Date: 2024-07-03
Flood observed: Yes
Confidence: High
Evidence: Geolocated road inundation imagery
```

## Metrics

Where sufficient labels are available, calculate:

- Precision
- Recall
- F1
- Intersection over Union (IoU)
- False-positive rate
- False-negative rate

Manually investigate major false positives and false negatives.

### Major Deliverable #2

**Validated SAR baseline flood-detection methodology**

### Hard Gate

Do **not** proceed to GeoAI simply because the baseline pipeline runs.

If the baseline cannot reasonably reproduce the documented event, investigate the imagery, acquisition timing, preprocessing, thresholding, water mask and validation methodology first.

---

# Phase 4 — Pythonize the GIS Workflow

## Goal

Turn the exploratory QGIS workflow into a reproducible processing pipeline.

## Technology

- Python
- Rasterio
- GeoPandas
- GDAL
- NumPy
- Xarray / Rioxarray
- Shapely
- PyProj

Potential pipeline:

```text
Raw data
   ↓
preprocess.py
   ↓
change_detection.py
   ↓
water_mask.py
   ↓
terrain_filter.py
   ↓
postprocess.py
   ↓
validate.py
   ↓
Flood GeoTIFF
```

QGIS then becomes primarily a tool for:

- Exploration
- QA/QC
- Visual inspection
- Cartography

### Deliverable

A reproducible flood-processing pipeline that can regenerate the baseline results.

---

# Phase 5 — GeoAI Flood Segmentation

## Goal

Determine whether GeoAI improves flood detection over the SAR baseline.

## 5.1 Training Dataset

Generate spatial image tiles, initially around:

```text
256 × 256 pixels
```

Potential channels:

```text
1. VV before
2. VH before
3. VV after
4. VH after
5. ΔVV
6. ΔVH
7. DEM
8. Slope
```

Target:

```text
0 = Non-flood
1 = Flood
```

Avoid random tile splitting where adjacent tiles appear across training and testing datasets.

Use spatially separated:

- Training regions
- Validation regions
- Test regions

## 5.2 Model Experiments

### Experiment 1
Rule-based SAR baseline

### Experiment 2
U-Net

### Experiment 3
SegFormer

Later experiments may compare:

```text
SAR
vs.
SAR + DEM
vs.
SAR + DEM + Sentinel-2
vs.
SAR + DEM + rainfall
```

## 5.3 Evaluation

Compare models using:

| Model | Flood IoU | F1 | Precision | Recall | Inference Time |
|---|---:|---:|---:|---:|---:|
| SAR Baseline | | | | | |
| U-Net | | | | | |
| SegFormer | | | | | |

If a simpler method outperforms the GeoAI model, report that result rather than forcing an AI-based conclusion.

### Major Deliverable #3

**GeoAI Flood Segmentation Benchmark**

---

# Phase 6 — Historical Flood Frequency

## Goal

Move beyond a single event and characterize recurrent flooding.

Identify documented historical Lagos flood events and process appropriate Sentinel-1 observations.

Potential years include:

```text
2017
2018
2019
2020
2021
2022
2023
2024
...
```

Do not automatically process every year. First establish documented events and suitable satellite observations.

Stack individual flood masks:

```text
Flood_1
Flood_2
Flood_3
...
Flood_N
   ↓
Historical Flood Cube
   ↓
Flood Frequency
```

Generate:

- Flood count
- Flood frequency
- Flood persistence
- Recurrence hotspots
- Seasonal patterns where possible

### Major Deliverable #4

**Lagos Historical Flood Frequency Map**

---

# Phase 7 — Flood Susceptibility Modeling

## Goal

Move from detecting observed floods to estimating where flooding is structurally more likely.

## Candidate Features

- Elevation
- Slope
- Flow accumulation
- Topographic Wetness Index (TWI)
- Distance to river
- Distance to coast
- Rainfall
- Land cover
- Impervious surface
- Historical flood frequency

## Target

Historical flood occurrence or another defensible flood-inventory label.

## Models

Start with:

1. Logistic Regression — baseline
2. Random Forest
3. XGBoost

Deep learning should only be introduced if there is evidence it solves a problem these approaches do not.

## Explainability

Use feature importance and/or SHAP to explain susceptibility predictions.

Example:

```text
Flood susceptibility: 0.87

Primary drivers
---------------------
Low elevation       +0.24
Flood history       +0.21
High rainfall       +0.17
River proximity     +0.13
Impervious surface  +0.08
```

### Major Deliverable #5

**Lagos Flood Susceptibility Model**

---

# Phase 8 — Exposure Intelligence

## Goal

Determine what is located within detected or predicted flood areas.

Overlay flood hazard with:

- Population
- Buildings
- Roads
- Schools
- Hospitals
- Power infrastructure
- Industrial assets
- Other critical infrastructure

Calculate statistics by LGA or another meaningful administrative unit:

- Flooded area
- Population exposed
- Buildings exposed
- Road kilometers exposed
- Critical facilities exposed

Conceptually:

```text
HAZARD
   +
EXPOSURE
   +
VULNERABILITY
   ↓
RISK
```

Do not label simple hazard/exposure overlays as full **risk** unless vulnerability is represented defensibly.

### Major Deliverable #6

**Lagos Flood Exposure Assessment**

---

# Phase 9 — Bayelsa Transfer Test

## Goal

Test whether the methodology and GeoAI model generalize beyond Lagos.

Bayelsa provides a deliberately different environment:

```text
Lagos
- Dense urban environment
- Impervious surfaces
- Drainage flooding
- Coastal/lagoon interaction
- High asset concentration

Bayelsa
- Deltaic environment
- Wetlands
- Rivers and creeks
- Low elevation
- Dispersed settlements
```

## Generalization Experiment

First test without retraining:

```text
TRAIN
Lagos
   ↓
TEST
Bayelsa
```

Measure performance degradation.

Then:

```text
Lagos model
    +
Bayelsa samples
    ↓
Fine-tuning
    ↓
Retest
```

Research question:

> **How transferable are GeoAI flood-detection models across contrasting Nigerian coastal environments?**

### Major Deliverable #7

**Cross-region GeoAI Generalization Study**

---

# Phase 10 — Productization

## Goal

Convert the validated research pipeline into the foundation of a flood-intelligence product/service.

Potential architecture:

```text
                   Web UI
                     │
                     ↓
                  FastAPI
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
       PostGIS     MinIO      Worker
                                │
                     ┌──────────┼─────────┐
                     ↓          ↓         ↓
                   U-Net     XGBoost   Exposure
                     │
                     ↓
                  GeoTIFF
                     │
                     ↓
                  Map Tiles
```

Potential containerized services:

- API
- Processing worker
- PostGIS
- MinIO
- GeoAI inference
- Susceptibility inference
- Exposure analysis

Potential user workflow:

```text
Select:
Lagos
July 2024
    ↓
Receive:
- Flood extent
- Flood probability
- Historical flood frequency
- Population exposure
- Building exposure
- Infrastructure exposure
- Model confidence
```

This phase begins only after the analytical pipeline has been validated.

---

# Project Milestones

| Milestone | Output |
|---|---|
| M1 | Project repository + event definition |
| M2 | Complete EO/geospatial dataset |
| M3 | QGIS SAR baseline flood map |
| M4 | Validated baseline |
| M5 | Reproducible Python pipeline |
| M6 | U-Net/SegFormer benchmark |
| M7 | Historical flood-frequency map |
| M8 | Flood-susceptibility model |
| M9 | Exposure assessment |
| M10 | Lagos → Bayelsa generalization |
| M11 | Product prototype |

---

# Immediate Execution Scope

Until the first hard gate is passed, the active project consists only of **Phases 0–3**.

Execute in this order:

1. Create repository.
2. Create `LAG_2024_07` event record.
3. Define and acquire Lagos AOI.
4. Identify exact Sentinel-1 scenes immediately before and after/during the July 3, 2024 event.
5. Acquire DEM.
6. Acquire JRC permanent-water data.
7. Collect independent validation evidence.
8. Preprocess Sentinel-1 scenes.
9. Perform SAR change detection.
10. Remove permanent water.
11. Apply terrain filtering.
12. Post-process flood mask.
13. Export `lagos_flood_extent_202407.tif`.
14. Validate the result against independent evidence.
15. Document failures, uncertainties and limitations.

**Do not start U-Net until Step 14 has produced a credible baseline.**

---

# Portfolio Positioning

The completed project should support a technical description similar to:

> Developed a reproducible Earth-observation pipeline for coastal flood intelligence in Nigeria, combining Sentinel-1 SAR change detection, GeoAI segmentation, historical flood observations, terrain and rainfall predictors, and infrastructure/population exposure analysis. Evaluated spatial and cross-region generalization between Lagos and Bayelsa and deployed the resulting models as a containerized geospatial service.

---

# Core Engineering Principle

The project should progress in this order:

```text
PROVE THE SCIENCE
       ↓
AUTOMATE THE PIPELINE
       ↓
BENCHMARK GEOAI
       ↓
ADD PREDICTION
       ↓
ADD EXPOSURE
       ↓
TEST GENERALIZATION
       ↓
PRODUCTIZE
```

Do not reverse this sequence.

The first success criterion is not a neural network or dashboard.

It is:

> **Can the pipeline independently reproduce a documented July 2024 Lagos flood event from Earth-observation data and defend the result against independent evidence?**
