"""Historical-water sensitivity of all existing clean candidate polygons."""
import json
from datetime import datetime, timezone
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_window, geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from prepare_sentinel1_pair import ROOT, save_json, sha256

def main():
    folder=ROOT/"data/processed/sentinel1"
    inputs=[folder/"lagos_candidate_review_polygons.gpkg",folder/"lagos_candidate_exploratory_clean.tif",ROOT/"data/interim/water/lagos_jrc_occurrence_1984_2021.tif",ROOT/"docs/acquisition/sentinel1_C0079_water_review.json"]
    outputs=[folder/"lagos_candidate_water_review.gpkg",ROOT/"docs/acquisition/sentinel1_polygon_water_review.csv",ROOT/"docs/acquisition/sentinel1_water_sensitivity.json"]
    if any(p.exists() for p in outputs): raise FileExistsError("Preserve existing water-review outputs before rerunning")
    mp=ROOT/"docs/acquisition/manifest.json"; manifest=json.loads(mp.read_text())
    for p in inputs: assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"]
    gdf=gpd.read_file(inputs[0],layer="candidate_patches")
    cutoffs=(1,10,25,50,75,90)
    summaries=[]; histogram=np.zeros(101,dtype="int64")
    with rasterio.open(inputs[1]) as grid, rasterio.open(inputs[2]) as water:
        assert gdf.crs==grid.crs
        with WarpedVRT(water,crs=grid.crs,transform=grid.transform,width=grid.width,height=grid.height,resampling=Resampling.nearest,src_nodata=water.nodata,nodata=255) as aligned:
            for number,row in enumerate(gdf.itertuples(),1):
                geom=[row.geometry]; w=geometry_window(grid,geom)
                mask=geometry_mask(geom,out_shape=(int(w.height),int(w.width)),transform=grid.window_transform(w),invert=True)
                assert int(mask.sum())==row.pixels and np.all(grid.read(1,window=w)[mask]==1)
                values=aligned.read(1,window=w)[mask]; known=values[values<=100]
                assert len(known)==row.pixels and np.all(known<90)
                histogram+=np.bincount(known,minlength=101)
                record=dict(patch_id=row.patch_id,occ_min=int(known.min()),occ_median=float(np.median(known)),occ_max=int(known.max()),water_known_pixels=len(known))
                for t in cutoffs:
                    count=int((known>=t).sum())
                    record[f"occ_ge{t}_pixels"]=count
                    record[f"occ_ge{t}_pct"]=100*count/row.pixels
                record["water_review_flag"]="majority_occ_ge50" if record["occ_ge50_pct"]>=50 else ("some_historical_water" if record["occ_ge1_pixels"] else "no_recorded_water")
                summaries.append(record)
                if number%100==0: print(f"Reviewed {number} polygons",flush=True)
    import pandas as pd
    result=gdf.merge(pd.DataFrame(summaries),on="patch_id",validate="one_to_one")
    total=int(result.pixels.sum())
    assert total==31252 and histogram.sum()==total
    previous=json.loads(inputs[3].read_text())
    selected=result[result.patch_id=="C0079"].iloc[0]
    for t in cutoffs: assert int(selected[f"occ_ge{t}_pixels"])==previous["pixels_at_or_above_occurrence_percent"][str(t)]
    sensitivity=[]
    for t in cutoffs:
        excluded=int(result[f"occ_ge{t}_pixels"].sum())
        sensitivity.append(dict(exclude_occurrence_ge=t,excluded_pixels=excluded,excluded_area_km2=excluded*0.0001,retained_pixels=total-excluded,retained_area_km2=(total-excluded)*0.0001,polygons_with_any_overlap=int((result[f"occ_ge{t}_pixels"]>0).sum()),polygons_with_majority_overlap=int((result[f"occ_ge{t}_pct"]>=50).sum()),polygons_fully_excluded=int((result[f"occ_ge{t}_pixels"]==result.pixels).sum())))
    result.to_file(outputs[0],layer="candidate_water_review",driver="GPKG")
    check=gpd.read_file(outputs[0],layer="candidate_water_review").sort_values("patch_id").reset_index(drop=True)
    original=result.sort_values("patch_id").reset_index(drop=True)
    assert len(check)==400 and check.geometry.is_valid.all()
    assert all(a.equals(b) for a,b in zip(check.geometry,original.geometry))
    np.testing.assert_array_equal(check.occ_ge50_pixels,original.occ_ge50_pixels)
    result.drop(columns="geometry").to_csv(outputs[1],index=False)
    flags={str(k):int(v) for k,v in result.water_review_flag.value_counts().items()}
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),scope="400 existing clean candidates only; not a rerun of full classification",candidate_pixels=total,area_km2=total*0.0001,flags=flags,cutoffs=sensitivity,occurrence_histogram=histogram.tolist(),checks=["Input hashes matched","All polygon samples match clean candidates and area counts","All historical water samples known and <90","C0079 reproduces prior independent review","GeoPackage reopened with valid unchanged geometries and checked attributes"],limitations=["Hypothetical pixel exclusions; spatial cleanup not repeated.","No new cutoff selected; classification and original files unchanged.","Review flags describe historical overlap, not flood truth.","No-recorded-water does not mean reliably dry in 2024.","Coarse JRC values are resampled; samples are not independent.","JRC v1.4 limitations remain."])
    save_json(outputs[2],report)
    for p in outputs: manifest[p.relative_to(ROOT).as_posix()]=dict(source=[s.relative_to(ROOT).as_posix() for s in inputs],sha256=sha256(p),bytes=p.stat().st_size,created_utc=report["created_utc"],processing=report["scope"])
    save_json(mp,manifest)
    print(json.dumps({k:v for k,v in report.items() if k!="occurrence_histogram"},indent=2))
if __name__=="__main__": main()
