import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parents[1]
manual = gdal.Open(str(ROOT / 'data/interim/sentinel1/S1A_20240703_TC_linear.tif'), gdal.GA_ReadOnly)
graph_base = ROOT / 'outputs/snap_runs/graph_trial_02_stages/S1A_20240703_Orb_TNR_Cal_Spk_TC.data'
report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'stage': 'Terrain correction', 'date': '20240703', 'comparison': 'manual linear GeoTIFF vs graph DIMAP bands', 'diagnostic_only': True, 'bands': {}}
manual_srs = osr.SpatialReference(); manual_srs.ImportFromWkt(manual.GetProjection())
for band_i, name in enumerate(('Sigma0_VH', 'Sigma0_VV'), 1):
    graph = gdal.Open(str(graph_base / f'{name}.img'), gdal.GA_ReadOnly)
    graph_srs = osr.SpatialReference(); graph_srs.ImportFromWkt(graph.GetProjection())
    grid = (manual.RasterXSize == graph.RasterXSize and manual.RasterYSize == graph.RasterYSize
            and manual_srs.IsSame(graph_srs)
            and np.allclose(manual.GetGeoTransform(), graph.GetGeoTransform(), rtol=0, atol=1e-8))
    item = {'grid_equal_semantically': bool(grid), 'shape': [manual.RasterYSize, manual.RasterXSize], 'pixels': 0,
            'exact_different_pixels': 0, 'zero_mask_differences': 0, 'nonfinite_mask_differences': 0,
            'outside_tolerance_pixels': 0, 'max_absolute_difference': 0.0, 'absolute_difference_sum': 0.0, 'finite_pairs': 0}
    if not grid: raise RuntimeError(f'{name}: grid mismatch')
    for row in range(0, manual.RasterYSize, 256):
        n = min(256, manual.RasterYSize-row)
        a = manual.GetRasterBand(band_i).ReadAsArray(0,row,manual.RasterXSize,n)
        b = graph.GetRasterBand(1).ReadAsArray(0,row,graph.RasterXSize,n)
        finite = np.isfinite(a) & np.isfinite(b)
        diff = np.abs(a[finite].astype(np.float64)-b[finite].astype(np.float64))
        item['pixels'] += a.size
        item['exact_different_pixels'] += int(np.count_nonzero(~((a==b)|(np.isnan(a)&np.isnan(b)))))
        item['zero_mask_differences'] += int(np.count_nonzero((a==0)!=(b==0)))
        item['nonfinite_mask_differences'] += int(np.count_nonzero(np.isfinite(a)!=np.isfinite(b)))
        item['outside_tolerance_pixels'] += int(np.count_nonzero(~np.isclose(a,b,rtol=1e-5,atol=1e-7,equal_nan=True)))
        item['finite_pairs'] += int(finite.sum())
        if diff.size: item['max_absolute_difference'] = max(item['max_absolute_difference'], float(diff.max()))
        item['absolute_difference_sum'] += float(diff.sum())
    item['mean_absolute_difference'] = item.pop('absolute_difference_sum') / item['finite_pairs'] if item['finite_pairs'] else None
    report['bands'][name] = item
    print(name, json.dumps(item), flush=True)
out = ROOT / 'docs/acquisition/snap_graph_trial_02_tc_value_comparison.json'
out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(out)
