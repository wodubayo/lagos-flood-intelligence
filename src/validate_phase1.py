"""Check acquired files and emit a reproducible Phase 1 QA report."""
import json
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from acquire_phase1 import ROOT, META, INTERIM, checksum, save_json


def main():
    manifest = json.loads((META / 'manifest.json').read_text())
    failures = []
    required = ['dem/lagos_copernicus_dem30.tif',
                'water/lagos_jrc_occurrence_1984_2021.tif',
                'water/lagos_jrc_seasonality_1984_2021.tif',
                'landcover/lagos_worldcover2021_N06E000.tif',
                'landcover/lagos_worldcover2021_N06E003.tif']
    for name in required:
        if not (INTERIM / name).is_file():
            failures.append(f'Missing required baseline raster: {name}')
    for name, metadata in manifest.items():
        path = ROOT / name
        if not path.exists() or checksum(path) != metadata['sha256']:
            failures.append(f'Checksum mismatch/missing file: {name}')
    state = gpd.read_file(INTERIM / 'boundaries/lagos_state.geojson')
    lgas = gpd.read_file(INTERIM / 'boundaries/lagos_lgas.geojson')
    if len(state) != 1 or len(lgas) != 20 or not state.is_valid.all() or not lgas.is_valid.all():
        failures.append('Boundary count/geometry check failed')
    summaries = []
    for path in sorted(INTERIM.rglob('*.tif')):
        with rasterio.open(path) as source:
            clipped, _ = mask(source, state.to_crs(source.crs).geometry, crop=True, filled=False)
            valid = clipped.compressed()
            if valid.size == 0 or not np.isfinite(valid).all():
                failures.append(f'No valid pixels/nonfinite values: {path.name}')
            lo, hi = (float(valid.min()), float(valid.max())) if valid.size else (None, None)
            if 'occurrence' in path.name and valid.size and (lo < 0 or hi > 100):
                failures.append(f'Invalid occurrence values: {path.name}')
            if 'seasonality' in path.name and valid.size and (lo < 0 or hi > 12):
                failures.append(f'Invalid seasonality values: {path.name}')
            summaries.append(dict(path=path.relative_to(ROOT).as_posix(), crs=str(source.crs),
                                  width=source.width, height=source.height, nodata=source.nodata,
                                  valid_aoi_pixels=int(valid.size), min=lo, max=hi,
                                  mean=float(valid.mean()) if valid.size else None))
    rain = [r for r in summaries if '/rainfall/' in r['path']]
    if len(rain) != 25:
        failures.append(f'Expected 25 daily rainfall rasters, found {len(rain)}')
    pair = json.loads((META / 'sentinel1_selected_pair.json').read_text())
    sar_present = all(f"data/raw/sentinel1/{pair[key]}.zip" in manifest for key in ('before', 'after'))
    report = dict(checksummed_files=len(manifest), raster_count=len(summaries), rasters=summaries,
                  selected_sar_archives_in_manifest=sar_present,
                  failures=failures, warnings=[
                      'LGA union differs from state outline; investigate coastal/water gaps before LGA area accounting.',
                      'Sentinel-1 pair coverage is catalog footprint coverage, not confirmed valid pixels.',
                      'Integrity checks do not establish flood presence or complete Phase 1; review the outstanding-data catalog.',
                      'JRC v1.4 known occurrence/seasonality issues require mask sensitivity analysis.',
                      'Raster means are pixel means, not area-weighted statistics.'])
    save_json(META / 'qa_report.json', report)
    print(json.dumps(dict(checksummed_files=len(manifest), raster_count=len(summaries), failures=failures), indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
