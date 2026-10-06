"""Audit exploratory candidates against backscatter and Copernicus DSM elevation."""
import csv
import json
from contextlib import ExitStack
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform
from prepare_sentinel1_pair import ROOT, save_json, sha256

def describe(values):
    v=np.asarray(values,dtype="float64")
    v=v[np.isfinite(v)]
    if not v.size:
        return {"count":0}
    q=np.percentile(v,[5,25,50,75,95])
    return dict(count=int(v.size),min=float(v.min()),p05=float(q[0]),p25=float(q[1]),median=float(q[2]),p75=float(q[3]),p95=float(q[4]),max=float(v.max()),mean=float(v.mean()))

def main():
    folder=ROOT/"data/processed/sentinel1"
    paths=[folder/n for n in ["lagos_candidate_exploratory_raw.tif","lagos_candidate_exploratory_clean.tif","lagos_20240621_sigma0_db.tif","lagos_20240703_sigma0_db.tif","lagos_delta_sigma0_db.tif"]]
    paths.append(ROOT/"data/interim/dem/lagos_copernicus_dem30.tif")
    report_path=ROOT/"docs/acquisition/sentinel1_candidate_audit.json"
    points_path=ROOT/"data/processed/sentinel1/lagos_candidate_review_points.csv"
    if report_path.exists() or points_path.exists():
        raise FileExistsError("Preserve previous audit before rerunning")
    manifest_path=ROOT/"docs/acquisition/manifest.json"
    manifest=json.loads(manifest_path.read_text())
    for p in paths:
        assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"],str(p)
    names=["june_vh_db","june_vv_db","july_vh_db","july_vv_db","delta_vh_db","delta_vv_db","dsm_elevation_m"]
    records=[]
    with ExitStack() as stack:
        raw,clean,before,after,change=[stack.enter_context(rasterio.open(p)) for p in paths[:5]]
        for ds in (clean,before,after,change):
            assert (ds.crs,ds.shape,ds.transform)==(raw.crs,raw.shape,raw.transform)
        dem=stack.enter_context(rasterio.open(paths[5]))
        elev=stack.enter_context(WarpedVRT(dem,crs=raw.crs,transform=raw.transform,width=raw.width,height=raw.height,resampling=Resampling.bilinear,src_nodata=dem.nodata,nodata=-9999))
        for _,w in raw.block_windows(1):
            r=raw.read(1,window=w)
            c=clean.read(1,window=w)
            assert np.all((c!=1)|(r==1))
            keep=r==1
            if not keep.any(): continue
            b=before.read(window=w)[:,keep]; a=after.read(window=w)[:,keep]; d=change.read(window=w)[:,keep]
            z=elev.read(1,window=w)[keep].astype("float64")
            z[z==-9999]=np.nan
            assert np.all(np.isfinite(b)) and np.all(b!=-9999)
            assert np.all(b[0]>-21) and np.all(a[0]<=-21) and np.all(d[0]<=-3)
            np.testing.assert_allclose(d,a-b,atol=1e-5,rtol=0)
            rr,cc=np.nonzero(keep)
            rr+=int(w.row_off); cc+=int(w.col_off)
            x,y=rasterio.transform.xy(raw.transform,rr,cc)
            lon,lat=transform(raw.crs,"EPSG:4326",x,y)
            records.append(np.column_stack([rr,cc,lon,lat,c[keep]==1,b.T,a.T,d.T,z]))
    data=np.concatenate(records)
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"scope":"Entire study area; not an exact Festac/Trade Fair neighborhood selection","terrain_method":"Copernicus 30m DSM bilinearly sampled on existing 10m SAR grid; elevations, not water depths or bare-earth heights","groups":{}}
    for label,select in [("raw",np.ones(len(data),dtype=bool)),("clean",data[:,4]==1)]:
        subset=data[select]
        stats={name:describe(subset[:,5+i]) for i,name in enumerate(names)}
        z=subset[:,-1]
        report["groups"][label]=dict(pixels=len(subset),area_km2=len(subset)*0.0001,statistics=stats,vv_decreased_pixels=int((subset[:,10]<0).sum()),dem_missing_pixels=int((~np.isfinite(z)).sum()),dem_elevation_counts={str(t):int((np.isfinite(z)&(z<=t)).sum()) for t in (0,2,5,10,20)})
    expected=json.loads((ROOT/"docs/acquisition/sentinel1_threshold_report.json").read_text())
    assert report["groups"]["raw"]["pixels"]==next(x["retained_pixels"] for x in expected["thresholds"] if x["july_vh_max_db"]==-21 and x["delta_vh_max_db"]==-3)
    assert report["groups"]["clean"]["pixels"]==next(x["retained_pixels"] for x in expected["cleanup_preview"] if x["min_component_pixels"]==25)
    report["checks"]=["registered input hashes match","grids match","clean is subset of raw","every raw candidate satisfies preview rule","delta matches dates","counts match threshold report"]
    report["limitations"]=["Selection already requires VH decrease; its summary is not independent confirmation.","DSM includes surface objects; no slope, elevation cutoff, or terrain filtering applied.","Resampling does not improve DEM resolution.","No event-time pixel labels or independent accuracy metrics available."]
    with points_path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f); writer.writerow(["row","column","longitude","latitude","retained_after_cleanup"]+names)
        for row in data:
            writer.writerow([int(row[0]),int(row[1]),row[2],row[3],int(row[4])]+[float(v) if np.isfinite(v) else "" for v in row[5:]])
    save_json(report_path,report)
    for p in (report_path,points_path):
        manifest[p.relative_to(ROOT).as_posix()]=dict(source=[s.relative_to(ROOT).as_posix() for s in paths],created_utc=report["created_utc"],sha256=sha256(p),bytes=p.stat().st_size,processing="Candidate backscatter/DSM audit; no further filtering")
    save_json(manifest_path,manifest)
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
