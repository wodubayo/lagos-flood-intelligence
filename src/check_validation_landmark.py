"""Inspect SAR support near a source-linked landmark, not reference labels."""
import json
import hashlib
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import Point
from rasterio.features import geometry_window,geometry_mask
from prepare_sentinel1_pair import ROOT,save_json
def main():
    folder=ROOT/"docs/validation"
    outputs=[folder/"iyana_oworo_support_check.json",folder/"evidence_search_areas.gpkg"]
    if any(p.exists() for p in outputs): raise FileExistsError("Preserve existing diagnostic outputs")
    snapshot=json.loads((folder/"phase2_baseline_snapshot.json").read_text())
    for item in snapshot["artifacts"]:
        h=hashlib.sha256()
        with (ROOT/item["path"]).open("rb") as f:
            for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
        assert h.hexdigest()==item["sha256"],item["path"]
    # Place coordinates embedded in Google Maps link cited by AFP; not the
    # viewport coordinates and not an independently established flooded point.
    anchor=gpd.GeoDataFrame([dict(lead_id="L001",role="search_landmark_not_flood_label",source_url="https://factcheck.afp.com/doc.afp.com.364R47J",geometry=Point(3.3962023,6.5550189))],crs=4326)
    projected=anchor.to_crs(32631)
    records=[]; buffers=[]
    base=ROOT/"data/processed/sentinel1"
    with rasterio.open(base/"lagos_pair_positive_mask.tif") as support,rasterio.open(base/"lagos_candidate_exploratory_clean.tif") as clean:
        assert (support.crs,support.transform,support.shape)==(clean.crs,clean.transform,clean.shape)
        for radius in (100,250,500):
            geom=projected.geometry.iloc[0].buffer(radius)
            w=geometry_window(clean,[geom])
            inside=geometry_mask([geom],out_shape=(int(w.height),int(w.width)),transform=clean.window_transform(w),invert=True)
            s=support.read(1,window=w)[inside]; c=clean.read(1,window=w)[inside]
            row=dict(radius_m=radius,pixels=int(len(s)),positive_sar_pixels=int((s==1).sum()),eligible_pixels=int((c!=255).sum()),candidate_pixels=int((c==1).sum()),eligible_not_selected_pixels=int((c==0).sum()),excluded_pixels=int((c==255).sum()))
            assert row["pixels"]==row["candidate_pixels"]+row["eligible_not_selected_pixels"]+row["excluded_pixels"]
            records.append(row)
            buffers.append(dict(lead_id="L001",radius_m=radius,role="search_buffer_not_flood_extent",geometry=geom))
    anchor.to_file(outputs[1],layer="search_landmark",driver="GPKG")
    gpd.GeoDataFrame(buffers,crs=32631).to_file(outputs[1],layer="search_buffers",driver="GPKG")
    report=dict(landmark_longitude=3.3962023,landmark_latitude=6.5550189,coordinate_source="Place coordinates in Google Maps URL linked by AFP; direct Maps retrieval failed",status="search aid only, not validated coordinates of flooded pixels",radii_are="arbitrary review windows, not measured spatial uncertainty or flood boundaries",baseline_hashes_verified=len(snapshot["artifacts"]),counts=records,limitations=["Exact footage recording time unresolved","No reference labels or accuracy metrics","Counts depend on arbitrary buffer radius","No candidate pixels is not proof of no flooding"])
    save_json(outputs[0],report)
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
