"""Review historical water occurrence within C0079 without changing candidates."""
import json
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_window, geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from prepare_sentinel1_pair import ROOT, save_json, sha256

def main():
    folder=ROOT/"data/processed/sentinel1"
    paths=[folder/"lagos_candidate_review_polygons.gpkg",folder/"lagos_candidate_exploratory_clean.tif",ROOT/"data/interim/water/lagos_jrc_occurrence_1984_2021.tif"]
    out=ROOT/"docs/acquisition/sentinel1_C0079_water_review.json"
    if out.exists(): raise FileExistsError("Preserve existing review before rerunning")
    mp=ROOT/"docs/acquisition/manifest.json"
    manifest=json.loads(mp.read_text())
    for p in paths: assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"]
    patch=gpd.read_file(paths[0],layer="candidate_patches")
    patch=patch[patch.patch_id=="C0079"]
    assert len(patch)==1
    with rasterio.open(paths[1]) as grid, rasterio.open(paths[2]) as water:
        geom=list(patch.to_crs(grid.crs).geometry)
        w=geometry_window(grid,geom)
        inside=geometry_mask(geom,out_shape=(int(w.height),int(w.width)),transform=grid.window_transform(w),invert=True)
        assert inside.sum()==int(patch.iloc[0].pixels)==2200
        assert np.all(grid.read(1,window=w)[inside]==1)
        with WarpedVRT(water,crs=grid.crs,transform=grid.transform,width=grid.width,height=grid.height,resampling=Resampling.nearest,src_nodata=water.nodata,nodata=255) as aligned:
            vals=aligned.read(1,window=w)[inside]
    known=vals[vals<=100]
    assert len(known)==2200 and np.all(known<90)
    counts={str(t):int((known>=t).sum()) for t in (1,10,25,50,75,90)}
    result=dict(patch_id="C0079",pixels=2200,area_ha=22,method="JRC occurrence nearest resampling to original SAR grid; polygon pixel-center inclusion",known_pixels=len(known),min=int(known.min()),median=float(np.median(known)),max=int(known.max()),pixels_at_or_above_occurrence_percent=counts,histogram={str(int(v)):int(c) for v,c in zip(*np.unique(known,return_counts=True))},checks=["Input hashes matched manifest","Polygon covers 2200 pixel centers, all clean candidates","All occurrence values valid and below existing 90% exclusion"],interpretation="Historical-water-margin concern; not proof of July 2024 inundation or a confirmed false positive. No classification modified.")
    save_json(out,result)
    manifest[out.relative_to(ROOT).as_posix()]=dict(source=[p.relative_to(ROOT).as_posix() for p in paths],sha256=sha256(out),bytes=out.stat().st_size,processing=result["method"])
    save_json(mp,manifest)
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
