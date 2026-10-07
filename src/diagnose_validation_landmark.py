"""Attribute candidate-rule exclusions near the Iyana Oworo search landmark."""
import json
from contextlib import ExitStack
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_window,geometry_mask
from prepare_sentinel1_pair import ROOT,save_json,sha256

def main():
    folder=ROOT/"docs/validation"; base=ROOT/"data/processed/sentinel1"
    out=folder/"iyana_oworo_rule_diagnostic.json"
    if out.exists(): raise FileExistsError("Preserve previous diagnostic")
    names=["lagos_20240621_sigma0_db.tif","lagos_20240703_sigma0_db.tif","lagos_candidate_exploratory_raw.tif","lagos_candidate_exploratory_clean.tif"]
    paths=[base/n for n in names]
    manifest=json.loads((ROOT/"docs/acquisition/manifest.json").read_text())
    for p in paths: assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"]
    buffers=gpd.read_file(folder/"evidence_search_areas.gpkg",layer="search_buffers")
    results=[]
    with ExitStack() as stack:
        b,a,raw,clean=[stack.enter_context(rasterio.open(p)) for p in paths]
        assert buffers.crs==b.crs
        for ds in (a,raw,clean): assert (ds.crs,ds.shape,ds.transform)==(b.crs,b.shape,b.transform)
        for feature in buffers.sort_values("radius_m").itertuples():
            w=geometry_window(b,[feature.geometry])
            inside=geometry_mask([feature.geometry],out_shape=(int(w.height),int(w.width)),transform=b.window_transform(w),invert=True)
            bv=b.read(1,window=w)[inside]; av=a.read(1,window=w)[inside]
            r=raw.read(1,window=w)[inside]; c=clean.read(1,window=w)[inside]
            valid=(r!=255)
            before=(bv>-21); dark=(av<=-21); drop=((av-bv)<=-3)
            expected=valid&before&dark&drop
            assert np.array_equal(expected,r==1)
            assert not np.any((c==1)&(r!=1))
            stages=[int(valid.sum()),int((valid&before).sum()),int((valid&before&dark).sum()),int(expected.sum()),int((c==1).sum())]
            row=dict(radius_m=int(feature.radius_m),all_pixels=len(r),eligible=stages[0],june_brighter=stages[1],then_july_dark=stages[2],then_drop_ge3=stages[3],after_cleanup=stages[4],removed_by_cleanup=int(((r==1)&(c!=1)).sum()),individual_conditions=dict(june_brighter=int((valid&before).sum()),july_dark=int((valid&dark).sum()),drop_ge3=int((valid&drop).sum())))
            for key,values in [("june_vh_db",bv[valid]),("july_vh_db",av[valid]),("delta_vh_db",(av-bv)[valid])]:
                row[key]=dict(zip(["p05","median","p95"],[float(v) for v in np.percentile(values,[5,50,95])]))
            results.append(row)
    report=dict(scope="Arbitrary source-linked search circles, not independently labelled flood locations",counts=results,checks=["Four input hashes matched","Grids matched","Reconstructed rule exactly matches raw candidates in every window","Clean is subset of raw"],limitations=["Sequential attrition depends on test order; individual condition counts also provided","No recording time or flooded road geometry established","This is diagnostic development evidence, not held-out accuracy assessment"])
    save_json(out,report)
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
