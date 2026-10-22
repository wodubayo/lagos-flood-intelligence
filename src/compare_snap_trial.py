"""Compare completed graph-trial DIMAP band values with manual SNAP GeoTIFFs."""
import json
from pathlib import Path
from datetime import datetime, timezone
from contextlib import ExitStack
import numpy as np
import rasterio
from rasterio.windows import Window
from prepare_sentinel1_pair import ROOT, band_metadata, sha256

def main():
    run=ROOT/"outputs/snap_runs/graph_trial_01"
    report_path=ROOT/"docs/acquisition/snap_graph_trial_01_comparison.json"
    if report_path.exists(): raise FileExistsError(report_path)
    report={"checked_utc":datetime.now(timezone.utc).isoformat(),
      "scope":"Full scene, manual linear GeoTIFF vs graph DIMAP ENVI bands; no resampling",
      "tolerance_diagnostic":{"rtol":1e-5,"atol":1e-7},
      "note":"Tolerance is a numerical diagnostic, not independent flood validation or automatic acceptance.",
      "dates":{}}
    for date in ("20240621","20240703"):
        log=run/(date+".log")
        if not log.read_text().rstrip().endswith("done."): raise ValueError("No completion marker")
        manual=ROOT/f"data/interim/sentinel1/S1A_{date}_TC_linear.tif"
        old_dim=ROOT/f"data/interim/sentinel1/S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
        new_dim=run/f"S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
        names=band_metadata(old_dim)
        if set(band_metadata(new_dim))!=set(names): raise ValueError("Band mismatch")
        result={"manual":manual.relative_to(ROOT).as_posix(),"graph_dim":new_dim.relative_to(ROOT).as_posix(),
                "metadata_sha256":{"manual_dim":sha256(old_dim),"graph_dim":sha256(new_dim)},"bands":{}}
        with ExitStack() as stack:
            ref=stack.enter_context(rasterio.open(manual))
            rebuilt=[stack.enter_context(rasterio.open(new_dim.with_suffix(".data")/(n+".img"))) for n in names]
            grids=all((d.crs,d.shape)==(ref.crs,ref.shape) and np.allclose(tuple(d.transform),tuple(ref.transform),rtol=0,atol=1e-8) for d in rebuilt)
            result["grid_equal_at_1e_minus8_map_units"]=grids
            if not grids: raise ValueError("Grid mismatch; cannot compare directly")
            stats=[dict(total_pixels=0,exact_different_pixels=0,zero_mask_differences=0,nonfinite_mask_differences=0,outside_tolerance_pixels=0,max_absolute_difference=0.0,absolute_difference_sum=0.0,finite_pairs=0) for _ in names]
            for row in range(0,ref.height,128):
                w=Window(0,row,ref.width,min(128,ref.height-row))
                original=ref.read(window=w)
                for i,ds in enumerate(rebuilt):
                    a=original[i];b=ds.read(1,window=w);s=stats[i]
                    finite=np.isfinite(a)&np.isfinite(b)
                    diff=np.abs(a[finite].astype("float64")-b[finite].astype("float64"))
                    s["total_pixels"]+=a.size
                    s["exact_different_pixels"]+=int(np.count_nonzero(~((a==b)|(np.isnan(a)&np.isnan(b)))))
                    s["zero_mask_differences"]+=int(np.count_nonzero((a==0)!=(b==0)))
                    s["nonfinite_mask_differences"]+=int(np.count_nonzero(np.isfinite(a)!=np.isfinite(b)))
                    s["outside_tolerance_pixels"]+=int(np.count_nonzero(~np.isclose(a,b,rtol=1e-5,atol=1e-7,equal_nan=True)))
                    s["finite_pairs"]+=int(finite.sum())
                    if diff.size: s["max_absolute_difference"]=max(s["max_absolute_difference"],float(diff.max()))
                    s["absolute_difference_sum"]+=float(diff.sum())
            for name,s in zip(names,stats):
                s["mean_absolute_difference"]=s.pop("absolute_difference_sum")/s["finite_pairs"] if s["finite_pairs"] else None
                result["bands"][name]=s
        report["dates"][date]=result
        print(date,json.dumps(result["bands"]),flush=True)
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(str(report_path),flush=True)
if __name__=="__main__":main()
