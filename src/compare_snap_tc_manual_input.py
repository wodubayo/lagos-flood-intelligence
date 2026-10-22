import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()
ROOT=Path(__file__).resolve().parents[1]
manual_base=ROOT/'data/interim/sentinel1/S1A_20240703_Orb_TNR_Cal_Spk_TC.data'
graph_base=ROOT/'outputs/snap_runs/graph_trial_03_tc_isolation/S1A_20240703_manual_disk_Spk_TC.data'
report={'checked_utc':datetime.now(timezone.utc).isoformat(),'stage':'Terrain correction','date':'20240703','comparison':'manual SNAP DIMAP vs graph SNAP DIMAP directly','diagnostic_only':True,'absolute_difference_threshold_counts':{},'bands':{}}
for name in ('Sigma0_VH','Sigma0_VV'):
    a=gdal.Open(str(manual_base/f'{name}.img')); b=gdal.Open(str(graph_base/f'{name}.img'))
    sa=osr.SpatialReference(); sa.ImportFromWkt(a.GetProjection()); sb=osr.SpatialReference(); sb.ImportFromWkt(b.GetProjection())
    same=(a.RasterXSize==b.RasterXSize and a.RasterYSize==b.RasterYSize and sa.IsSame(sb) and np.allclose(a.GetGeoTransform(),b.GetGeoTransform(),rtol=0,atol=1e-8))
    if not same: raise RuntimeError(f'{name} grid mismatch')
    s={'grid_equal_semantically':True,'shape':[a.RasterYSize,a.RasterXSize],'pixels':0,'exact_different_pixels':0,'zero_mask_differences':0,'outside_tolerance_pixels':0,'max_absolute_difference':0.0,'max_difference_pixel_row_col':None,'max_difference_pixel_center_xy':None,'max_difference_values_manual_graph':None,'threshold_counts':{str(t):0 for t in (1e-4,1e-3,0.01,0.1,1.0)},'sum_abs':0.0,'finite_pairs':0}
    gt=a.GetGeoTransform()
    for row in range(0,a.RasterYSize,256):
      n=min(256,a.RasterYSize-row); x=a.GetRasterBand(1).ReadAsArray(0,row,a.RasterXSize,n); y=b.GetRasterBand(1).ReadAsArray(0,row,b.RasterXSize,n)
      finite=np.isfinite(x)&np.isfinite(y); d=np.abs(x.astype('float64')-y.astype('float64')); d_valid=d[finite]
      s['pixels']+=x.size; s['exact_different_pixels']+=int(np.count_nonzero(~((x==y)|(np.isnan(x)&np.isnan(y))))); s['zero_mask_differences']+=int(np.count_nonzero((x==0)!=(y==0))); s['outside_tolerance_pixels']+=int(np.count_nonzero(~np.isclose(x,y,rtol=1e-5,atol=1e-7,equal_nan=True))); s['finite_pairs']+=int(finite.sum()); s['sum_abs']+=float(d_valid.sum())
      for t in (1e-4,1e-3,0.01,0.1,1.0): s['threshold_counts'][str(t)]+=int(np.count_nonzero(d_valid>t))
      if d_valid.size:
        local=np.nanargmax(np.where(finite,d,np.nan)); rr,cc=np.unravel_index(local,d.shape); vmax=float(d[rr,cc])
        if vmax>s['max_absolute_difference']:
          gr=row+rr; s['max_absolute_difference']=vmax; s['max_difference_pixel_row_col']=[int(gr),int(cc)]; s['max_difference_pixel_center_xy']=[gt[0]+(cc+0.5)*gt[1]+(gr+0.5)*gt[2],gt[3]+(cc+0.5)*gt[4]+(gr+0.5)*gt[5]]; s['max_difference_values_manual_graph']=[float(x[rr,cc]),float(y[rr,cc])]
    s['mean_absolute_difference']=s.pop('sum_abs')/s['finite_pairs'] if s['finite_pairs'] else None
    report['bands'][name]=s;print(name,json.dumps(s),flush=True)
out=ROOT/'docs/acquisition/snap_graph_trial_03_manual_disk_input_comparison.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(out)

