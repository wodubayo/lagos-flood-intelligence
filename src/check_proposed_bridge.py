"""Diagnostic around user-picked proposed bridge match; no reference label."""
import json
from contextlib import ExitStack
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import Point
from rasterio.features import geometry_window,geometry_mask
from prepare_sentinel1_pair import ROOT,save_json,sha256
def main():
    folder=ROOT/"docs/validation";base=ROOT/"data/processed/sentinel1"
    output=folder/"proposed_bridge_diagnostic.json";gpkg=folder/"proposed_bridge_match.gpkg"
    if output.exists() or gpkg.exists(): raise FileExistsError("Preserve previous diagnostic")
    point=gpd.GeoDataFrame([dict(match_id="MATCH_IYANA_001",observation_id="OBS_IYANA_VIDEO_001",role="proposed_bridge_not_flood_point",source="user_QGIS_pick",geometry=Point(3.3970649,6.5518951))],crs=4326)
    p=point.to_crs(32631).geometry.iloc[0]
    old=gpd.GeoSeries([Point(3.3962023,6.5550189)],crs=4326).to_crs(32631).iloc[0]
    paths=[base/n for n in ["lagos_20240621_sigma0_db.tif","lagos_20240703_sigma0_db.tif","lagos_candidate_exploratory_raw.tif","lagos_candidate_exploratory_clean.tif"]]
    manifest=json.loads((ROOT/"docs/acquisition/manifest.json").read_text())
    for path in paths: assert sha256(path)==manifest[path.relative_to(ROOT).as_posix()]["sha256"]
    rows=[];buffers=[]
    with ExitStack() as stack:
        before,after,raw,clean=[stack.enter_context(rasterio.open(path)) for path in paths]
        for ds in (after,raw,clean): assert (ds.crs,ds.transform,ds.shape)==(before.crs,before.transform,before.shape)
        for radius in (50,100,250):
            geom=p.buffer(radius);w=geometry_window(raw,[geom])
            mask=geometry_mask([geom],out_shape=(int(w.height),int(w.width)),transform=raw.window_transform(w),invert=True)
            r=raw.read(1,window=w)[mask];c=clean.read(1,window=w)[mask];b=before.read(window=w)[:,mask];a=after.read(window=w)[:,mask]
            eligible=r!=255
            expected=eligible&(b[0]>-21)&(a[0]<=-21)&((a[0]-b[0])<=-3)
            assert np.array_equal(expected,r==1)
            assert np.all((c!=1)|(r==1))
            row=dict(radius_m=radius,pixels=len(r),eligible_pixels=int(eligible.sum()),excluded_pixels=int((~eligible).sum()),july_vh_le_minus21=int((eligible&(a[0]<=-21)).sum()),vh_decrease_ge3=int((eligible&((a[0]-b[0])<=-3)).sum()),raw_candidates=int((r==1).sum()),clean_candidates=int((c==1).sum()))
            for i,pol in enumerate(("vh","vv")):
                row[pol+"_june_median_db"]=float(np.median(b[i,eligible])) if eligible.any() else None
                row[pol+"_july_median_db"]=float(np.median(a[i,eligible])) if eligible.any() else None
                row[pol+"_change_median_db"]=float(np.median((a-b)[i,eligible])) if eligible.any() else None
            rows.append(row);buffers.append(dict(radius_m=radius,role="diagnostic_window_not_flood_extent",geometry=geom))
    point.to_file(gpkg,layer="proposed_bridge",driver="GPKG")
    gpd.GeoDataFrame(buffers,crs=32631).to_file(gpkg,layer="diagnostic_windows",driver="GPKG")
    check=gpd.read_file(gpkg,layer="proposed_bridge")
    assert check.crs.to_epsg()==4326 and check.geometry.iloc[0].equals(point.geometry.iloc[0])
    report=dict(match_id="MATCH_IYANA_001",latitude=6.5518951,longitude=3.3970649,coordinate_interpretation="User supplied latitude,longitude in WGS84; stored geometry x=longitude,y=latitude",role="proposed bridge match only; exact flooded carriageway, camera direction and recording time unresolved",distance_from_prior_search_landmark_m=float(p.distance(old)),counts=rows,checks=["Input hashes/grids match","Raw candidate rule reproduced","Clean subset of raw","Exported WGS84 point reopened and verified"],limitations=["Buffer radii are arbitrary, not location error estimates","Statistics summarize mixed surfaces, not the observed flooded road","No ground-truth label or false-negative claim assigned"])
    save_json(output,report)
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
