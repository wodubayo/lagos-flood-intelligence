# Methodology

## Project Scope

This project focuses on the July 3–4, 2024 flood event in Lagos State, Nigeria, with a reproducible GeoAI workflow designed to scale to other coastal flood-prone areas in Nigeria.

## Objectives

1. Detect flood extent using Earth observation and geospatial data.
2. Validate detections against independent evidence.
3. Quantify flood susceptibility using terrain, hydrology, and land-cover indicators.
4. Assess exposure and risk for affected populations and assets.

## Event Definition

- Event ID: LAG_2024_07
- Event: Lagos July 2024 Flood
- Primary date: July 3, 2024
- Location: Lagos State, Nigeria
- Validation event: July 2021
- Initial validation locations: Lekki, Ibeju-Lekki, Iyana Oworo

## Analytical Workflow

### 1. Data acquisition

Collect Sentinel-1 SAR scenes before and after the event, together with supporting EO datasets such as Sentinel-2, CHIRPS/GPM rainfall, NASADEM, and JRC Global Surface Water.

### 2. Baseline flood mapping

Create a SAR-based flood extent map using change detection, thresholding, permanent-water masking, and terrain filtering.

### 3. Validation

Compare flood map outputs against NEMA reporting, GDACS data, news reports, and geolocated imagery/video evidence.

### 4. Susceptibility and exposure modeling

Integrate terrain, rainfall, land cover, and infrastructure data to identify vulnerable and exposed areas.

### 5. Reporting

Produce geospatial outputs, quantitative metrics, and maps for reproducible analysis and stakeholder communication.

## Quality Considerations

- Ensure consistent spatial reference systems and temporal comparability.
- Document source provenance, acquisition dates, and processing steps.
- Separate permanent water from flood inundation.
- Validate outputs against independent evidence to reduce false positives.

## Expected Outputs

- Flood extent raster and vector layers
- Validation summary against independent records
- Flood susceptibility maps
- Risk/exposure summaries
- Reproducible analysis notebooks and scripts
