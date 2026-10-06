"""Exploratory darkening candidates; not a validated flood classification."""
import csv
import json
from contextlib import ExitStack
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import sieve
from rasterio.vrt import WarpedVRT
from prepare_sentinel1_pair import ROOT, save_json, sha256

def candidate(before, after, delta, valid, dark, drop):
    return valid & (before > dark) & (after <= dark) & (delta <= drop)

def remove_small(raw, size):
    # Full-scene connectivity avoids tile seams. Intersect to prevent filling holes.
    return (sieve(raw.astype("uint8"), size=size, connectivity=8) == 1) & raw

def main():
    folder=ROOT/"data/processed/sentinel1"
    inputs=[folder/n for n in ["lagos_20240621_sigma0_db.tif","lagos_20240703_sigma0_db.tif","lagos_delta_sigma0_db.tif","lagos_pair_positive_mask.tif"]]
    inputs.append(ROOT/"data/interim/water/lagos_jrc_occurrence_1984_2021.tif")
    names=["lagos_candidate_threshold_agreement.tif","lagos_candidate_exploratory_raw.tif","lagos_candidate_exploratory_clean.tif"]
    outputs=[folder/n for n in names]
    report_path=ROOT/"docs/acquisition/sentinel1_threshold_report.json"
    csv_path=ROOT/"docs/acquisition/sentinel1_threshold_sensitivity.csv"
    if any(p.exists() for p in outputs+[report_path,csv_path]):
        raise FileExistsError("Preserve existing results before rerunning")
    manifest_path=ROOT/"docs/acquisition/manifest.json"
    manifest=json.loads(manifest_path.read_text())
    for p in inputs:
        assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"], str(p)
    settings=[(dark,drop) for dark in (-18,-21,-24) for drop in (-2,-3,-4)]
    rows=[dict(july_vh_max_db=d,june_vh_min_exclusive_db=d,delta_vh_max_db=c,raw_pixels=0,water_ge90_pixels=0,water_unknown_pixels=0,retained_pixels=0,vv_decrease_pixels=0) for d,c in settings]
    support_count=eligible_count=water_count=unknown_count=0
    with ExitStack() as stack:
        before,after,change,mask=[stack.enter_context(rasterio.open(p)) for p in inputs[:4]]
        for ds in (after,change,mask):
            assert (ds.crs,ds.shape,ds.transform)==(before.crs,before.shape,before.transform)
        src=stack.enter_context(rasterio.open(inputs[4]))
        water=stack.enter_context(WarpedVRT(src,crs=before.crs,transform=before.transform,width=before.width,height=before.height,resampling=Resampling.nearest,src_nodata=src.nodata,nodata=255))
        agreement=np.full(before.shape,255,dtype="uint8")
        baseline=np.zeros(before.shape,dtype="bool")
        for _,w in before.block_windows(1):
            b=before.read(1,window=w); a=after.read(1,window=w)
            delta=change.read(window=w); valid=mask.read(1,window=w)==1
            occ=water.read(1,window=w)
            known=occ<=100
            eligible=valid & known & (occ<90)
            support_count+=int(valid.sum()); eligible_count+=int(eligible.sum())
            water_count+=int((valid & known & (occ>=90)).sum())
            unknown_count+=int((valid & ~known).sum())
            votes=np.zeros(valid.shape,dtype="uint8")
            for row,(dark,drop) in zip(rows,settings):
                raw=candidate(b,a,delta[0],valid,dark,drop)
                retained=raw & eligible
                row["raw_pixels"]+=int(raw.sum())
                row["water_ge90_pixels"]+=int((raw & known & (occ>=90)).sum())
                row["water_unknown_pixels"]+=int((raw & ~known).sum())
                row["retained_pixels"]+=int(retained.sum())
                row["vv_decrease_pixels"]+=int((retained & (delta[1]<0)).sum())
                votes+=retained
                if (dark,drop)==(-21,-3):
                    baseline[w.toslices()]=retained
            agreement[w.toslices()]=np.where(eligible,votes,255)
        profile=before.profile.copy()
        profile.update(count=1,dtype="uint8",nodata=255,compress="deflate",predictor=1)
    assert support_count==eligible_count+water_count+unknown_count
    for row in rows:
        assert row["raw_pixels"]==row["water_ge90_pixels"]+row["water_unknown_pixels"]+row["retained_pixels"]
        row["retained_area_km2"]=row["retained_pixels"]*0.0001
        row["percent_eligible"]=100*row["retained_pixels"]/eligible_count
    cleanup=[]
    clean=None
    for size in (9,25,100):
        filtered=remove_small(baseline,size)
        assert not np.any(filtered & ~baseline)
        cleanup.append(dict(min_component_pixels=size,area_threshold_m2=size*100,retained_pixels=int(filtered.sum()),retained_area_km2=float(filtered.sum())*0.0001))
        if size==25: clean=filtered
    for path,values in zip(outputs,[agreement,np.where(agreement==255,255,baseline).astype("uint8"),np.where(agreement==255,255,clean).astype("uint8")]):
        partial=path.with_suffix(".part.tif")
        with rasterio.open(partial,"w",**profile) as dst:
            dst.write(values,1)
            dst.set_band_description(1,"threshold agreement 0..9;255=excluded" if path==outputs[0] else "0=not selected;1=exploratory candidate;255=excluded")
            dst.update_tags(status="EXPLORATORY, UNVALIDATED; not flood extent",water_exclusion="JRC occurrence >=90%; unknown excluded",rule="June VH > T AND July VH <= T AND delta VH <= D",preview="T=-21 dB,D=-3 dB; clean minimum 25 pixels,8-connected; not optimized")
        partial.replace(path)
        with rasterio.open(path) as check:
            assert check.crs==profile["crs"] and check.transform==profile["transform"]
            np.testing.assert_array_equal(check.read(1),values)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),status="exploratory, not validated flood extent",common_positive_pixels=support_count,excluded_historical_water_pixels=water_count,excluded_unknown_water_pixels=unknown_count,eligible_pixels=eligible_count,eligible_area_km2=eligible_count*0.0001,thresholds=rows,cleanup_preview=cleanup,preview_settings=dict(july_vh_max_db=-21,delta_vh_max_db=-3,june_vh_min_exclusive_db=-21,min_component_pixels=25,connectivity=8),checks=["input SHA256 matched manifest","grids matched","water partitions matched counts","cleanup never adds candidates","all three raster outputs reopened and compared exactly"],limitations=["Thresholds are deliberately illustrative, not calibrated or selected for accuracy.","VV decrease is reported as supporting information, not required.","Darkening rule can miss urban or vegetated flooding with increased backscatter.","No terrain filter or independent validation applied.","JRC v1.4 limitations and prior coverage loss remain.","Visual patch has no recorded coordinates; statistics are study-area-wide."])
    save_json(report_path,report)
    with csv_path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for p in outputs+[report_path,csv_path]:
        manifest[p.relative_to(ROOT).as_posix()]=dict(source=[s.relative_to(ROOT).as_posix() for s in inputs],sha256=sha256(p),bytes=p.stat().st_size,created_utc=report["created_utc"],processing="Exploratory threshold sensitivity; see sentinel1_threshold_report.json")
    save_json(manifest_path,manifest)
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
