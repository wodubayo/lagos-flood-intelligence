# Data Catalog

## Overview

This document records the core datasets required for Lagos flood mapping and analysis. It is intended to support reproducibility and traceability for the July 2024 event study.

## Core Dataset Inventory

| Dataset | Purpose | Source | Spatial Resolution | Notes |
|---|---|---|---|---|
| Sentinel-1 GRD | Flood detection via SAR backscatter change | Copernicus | 10 m | Primary event dataset |
| Sentinel-2 | Land-cover and optical context | Copernicus | 10–60 m | Supports validation and interpretation |
| GPM / CHIRPS | Rainfall | NASA / Climate data products | 10 km / 0.05° | Hydrometeorological context |
| NASADEM | Elevation and terrain | NASA | 1 arc-second | Slope and terrain filtering |
| JRC Global Surface Water | Permanent water mask | JRC | 30 m | Distinguishes water from flood |
| OpenStreetMap | Infrastructure context | OSM | Variable | Roads, structures, drainage |
| WorldPop | Population exposure | WorldPop | 100 m | Risk and exposure analysis |
| Administrative boundaries | Lagos state and local area delineation | geoBoundaries / HDX / national sources | Variable | Project AOI definition |

## Required Processing Records

For each dataset, maintain:

- Dataset name
- Source URL or provider
- Download date
- Spatial resolution
- CRS
- License / access conditions
- Processing steps performed
- Output file path
- QA/QC notes

## Initial Data Folder Layout

```text
data/
├── raw/
├── interim/
└── processed/
```

## Future Extensions

Additional datasets may be added for:

- Drainage network analysis
- Coastal and lagoon inundation modeling
- Socio-economic vulnerability assessment
- Flood-return estimates and scenario modeling
