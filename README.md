# Lagos Flood Risk Analysis

A project focused on analyzing and understanding flood risk patterns across Lagos, Nigeria. The analysis combines relevant geospatial, environmental, and infrastructure indicators to identify high-risk areas and support decision-making for flood mitigation and resilience planning.

## Overview

This project is intended to help assess:

- Areas with the highest flood susceptibility
- The relationship between rainfall, elevation, drainage, and urban exposure
- Vulnerable communities and infrastructure at risk
- Spatial patterns that can inform preparedness and planning

## Project Goals

- Map flood-prone locations in Lagos
- Quantify risk factors using available data
- Visualize hotspots and vulnerable zones
- Provide a reproducible analytical workflow for further research and planning

## Repository Structure

```text
lagos-flood-risk-analysis/
├── README.md
├── requirements.txt
├── .gitignore
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
├── TR_220824_LagosFloods.pdf
└── lagos_coastal_flood_geoai_implementation_plan.md
```

## Data and Sources

This project may use a mix of:

- Rainfall and hydrological data
- Elevation and terrain information
- Land-use / urban exposure data
- Infrastructure and population indicators
- Published flood reports and reference material such as `TR_220824_LagosFloods.pdf`
- GDACS Floods Report: https://www.gdacs.org/Floods/report.aspx?episodeid=10&eventid=1102720&eventtype=FL&utm_source=chatgpt.com

## Workflow

1. Collect and clean flood-related datasets for Lagos.
2. Prepare spatial and tabular inputs for analysis.
3. Run exploratory data analysis and risk assessment procedures.
4. Visualize vulnerable zones and summarize findings.
5. Document recommendations for flood mitigation and planning.

## Suggested Tools

- Python
- Jupyter Notebook
- Pandas
- GeoPandas
- NumPy
- Matplotlib / Seaborn
- QGIS or similar GIS tooling

## Getting Started

1. Clone or open the repository.
2. Create a Python environment.
3. Install the project dependencies from `requirements.txt`.
4. Review the event record in `docs/events/LAG_2024_07.md`.
5. Explore the project files and begin the analysis workflow.

Example Python setup:

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
.venv\Scripts\activate     # On Windows
pip install -r requirements.txt
```

## Event Record

- 2022-08-24 — Flood risk reference document `TR_220824_LagosFloods.pdf` was recorded as the source material for the project.
- 2026-10-03 — Project documentation and README were initialized to define the scope, workflow, and analytical objectives.

### Events of Interest

- Primary event → July 3–4, 2024
- Secondary validation event → July 2021

### Event Details

- EVENT_ID: `LAG_2024_07`
- Location: Lagos State, Nigeria
- Event: Major rainfall flooding
- Primary date: 03 July 2024
- Analysis window: ~late June – early/mid July 2024
- Reported locations:
  - Lekki
  - Ibeju-Lekki
  - Iyana Oworo
  - other Lagos districts
- Hazard: Primarily pluvial/urban flooding, with coastal/lagoon interactions worth investigating
- Independent evidence:
  - NEMA
  - GDACS/GloFAS
  - news reports
  - geolocated imagery/video
- Satellite: Sentinel-1
- Supporting EO: Sentinel-2, GPM / CHIRPS, NASADEM, JRC Global Surface Water
- Objective: Detect and quantify July 2024 flood extent using Sentinel-1 SAR and compare against independent observations.

## Notes

This project is designed as a research and analysis workspace for Lagos flood risk assessment. It can be extended with additional datasets, scenario testing, and more advanced spatial modeling as needed.

## License

This project does not currently include a specific license. If you plan to share or publish the work, consider adding an appropriate open-source license.
