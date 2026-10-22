import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from osgeo import gdal

gdal.UseExceptions()
root=Path(__file__).resolve().parents[1]
base=root/'data/interim/sentinel1/S1A_20240703_Orb_TNR_Cal_Spk_TC.data'
comp=root/'outputs/snap_runs/graph_trial_02_stages/S1A_20240703_Orb_TNR_Cal_Spk_TC.data'
meta=json.loads((root/'docs/acquisition/snap_graph_trial_02_tc_dim_comparison.json').read_text(encoding='utf-8-sig'))
report={'checked_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Local-window characterization around maximum TC value differences; diagnostic only','windows':{}}
for band, info in meta['bands'].items():
    row,col=info['max_difference_pixel_row_col']
    ads=gdal.Open(str(base/f'{band}.img')); bds=gdal.Open(str(comp/f'{band}.img'))
    a=ads.GetRasterBand(1); b=bds.GetRasterBand(1)
    item={'max_pixel_row_col':[row,col],'windows':{}}
    for size in (3,9,31,101):
        rad=size//2; x0=max(0,col-rad); y0=max(0,row-rad); w=min(size,ads.RasterXSize-x0); h=min(size,ads.RasterYSize-y0)
        av=a.ReadAsArray(x0,y0,w,h).astype('float64'); bv=b.ReadAsArray(x0,y0,w,h).astype('float64'); d=np.abs(av-bv); finite=np.isfinite(d); q=d[finite]
        item['windows'][str(size)]={'pixels':int(q.size),'mean_abs_diff':float(q.mean()),'max_abs_diff':float(q.max()),'count_gt_0.1':int(np.count_nonzero(q>0.1)),'count_gt_1':int(np.count_nonzero(q>1.0)),'manual_center':float(av[row-y0,col-x0]),'graph_center':float(bv[row-y0,col-x0]),'manual_local_max':float(np.nanmax(av)),'graph_local_max':float(np.nanmax(bv))}
    report['windows'][band]=item
    print(band,json.dumps(item),flush=True)
out=root/'docs/acquisition/snap_graph_trial_02_tc_outlier_windows.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(out)

