import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from osgeo import gdal

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / 'data/interim/sentinel1'
GRAPH = ROOT / 'outputs/snap_runs/graph_trial_02_stages'
REPORT = ROOT / 'docs/acquisition/snap_graph_trial_02_stage_comparison.json'
STAGES = [
    ('TNR', 'S1A_20240703_Orb_TNR', 'S1A_20240703_Orb_TNR', ('Intensity_VH', 'Intensity_VV')),
    ('Calibration', 'S1A_20240703_Orb_TNR_Cal', 'S1A_20240703_Orb_TNR_Cal', ('Sigma0_VH', 'Sigma0_VV')),
    ('Speckle filter', 'S1A_20240703_Orb_TNR_Cal_Spk', 'S1A_20240703_Orb_TNR_Cal_Spk', ('Sigma0_VH', 'Sigma0_VV')),
]

def dataset(path):
    ds = gdal.Open(str(path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f'GDAL could not open {path}')
    return ds

def raster_path(base, band):
    p = Path(base)
    if p.suffix.lower() == '.tif':
        return p
    return p.with_suffix('.data') / f'{band}.img'

def equal_grid(a, b):
    return (a.RasterXSize == b.RasterXSize and a.RasterYSize == b.RasterYSize
            and a.GetProjection() == b.GetProjection()
            and np.allclose(a.GetGeoTransform(), b.GetGeoTransform(), rtol=0, atol=1e-8))

report = {
    'checked_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'July 3 manual SNAP intermediate DIMAP versus stage-output graph DIMAP; TC compared to manual linear GeoTIFF',
    'diagnostic_only': True,
    'graph': 'outputs/snap_runs/graph_trial_02_stages/sentinel1_preprocess_stages.xml',
    'stages': {},
}
for label, manual_name, graph_name, bands in STAGES:
    stage = {'manual': f'data/interim/sentinel1/{manual_name}',
             'graph': f'outputs/snap_runs/graph_trial_02_stages/{graph_name}.dim',
             'bands': {}}
    for band_name in bands:
        a_path = MANUAL / (manual_name if manual_name.endswith('.tif') else f'{manual_name}.dim')
        b_path = GRAPH / f'{graph_name}.dim'
        a = dataset(raster_path(a_path, band_name))
        b = dataset(raster_path(b_path, band_name))
        same_grid = equal_grid(a, b)
        result = {'manual_shape': [a.RasterYSize, a.RasterXSize],
                  'graph_shape': [b.RasterYSize, b.RasterXSize],
                  'grid_equal': same_grid,
                  'pixels': 0, 'exact_different_pixels': 0,
                  'zero_mask_differences': 0, 'nonfinite_mask_differences': 0,
                  'outside_tolerance_pixels': 0, 'max_absolute_difference': 0.0,
                  'absolute_difference_sum': 0.0, 'finite_pairs': 0}
        if same_grid:
            for row in range(0, a.RasterYSize, 256):
                nrows = min(256, a.RasterYSize - row)
                av = a.GetRasterBand(1).ReadAsArray(0, row, a.RasterXSize, nrows)
                bv = b.GetRasterBand(1).ReadAsArray(0, row, b.RasterXSize, nrows)
                finite = np.isfinite(av) & np.isfinite(bv)
                diff = np.abs(av[finite].astype(np.float64) - bv[finite].astype(np.float64))
                result['pixels'] += av.size
                result['exact_different_pixels'] += int(np.count_nonzero(~((av == bv) | (np.isnan(av) & np.isnan(bv)))))
                result['zero_mask_differences'] += int(np.count_nonzero((av == 0) != (bv == 0)))
                result['nonfinite_mask_differences'] += int(np.count_nonzero(np.isfinite(av) != np.isfinite(bv)))
                result['outside_tolerance_pixels'] += int(np.count_nonzero(~np.isclose(av, bv, rtol=1e-5, atol=1e-7, equal_nan=True)))
                result['finite_pairs'] += int(finite.sum())
                if diff.size:
                    result['max_absolute_difference'] = max(result['max_absolute_difference'], float(diff.max()))
                result['absolute_difference_sum'] += float(diff.sum())
            result['mean_absolute_difference'] = (result.pop('absolute_difference_sum') / result['finite_pairs']
                                                    if result['finite_pairs'] else None)
        else:
            result['manual_grid'] = {'geotransform': a.GetGeoTransform(), 'projection': a.GetProjection()[:100]}
            result['graph_grid'] = {'geotransform': b.GetGeoTransform(), 'projection': b.GetProjection()[:100]}
            result.pop('absolute_difference_sum')
        stage['bands'][band_name] = result
        a = None; b = None
    report['stages'][label] = stage
    print(label, json.dumps(stage['bands']), flush=True)
REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(REPORT)

