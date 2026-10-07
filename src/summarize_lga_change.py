"""LGA change consistency summary; not flood accuracy evaluation."""
import json
from contextlib import ExitStack
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask,geometry_window
from prepare_sentinel1_pair import ROOT,save_json,sha256

def main():
    base=ROOT/"data/processed/sentinel1";outdir=ROOT/"docs/validation"
    inputs=[ROOT/"data/interim/boundaries/lagos_lgas.geojson"]+[base/n for n in ["lagos_delta_sigma0_db.tif","lagos_pair_positive_mask.tif","lagos_candidate_exploratory_clean.tif"]]
    outputs=[outdir/"lga_change_summary.csv",outdir/"lga_change_summary.gpkg",outdir/"lga_change_report.json"]
    if any(p.exists() for p in outputs): raise FileExistsError("Preserve prior outputs")
    manifest_path=ROOT/"docs/acquisition/manifest.json";manifest=json.loads(manifest_path.read_text())
    for p in inputs: assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"],str(p)
    boundaries=gpd.read_file(inputs[0])
    assert len(boundaries)==20 and boundaries.shapeID.is_unique
    rows=[]
    with ExitStack() as stack:
        delta,positive,candidates=[stack.enter_context(rasterio.open(p)) for p in inputs[1:]]
        assert all((d.crs,d.shape,d.transform)==(delta.crs,delta.shape,delta.transform) for d in (positive,candidates))
        boundaries=boundaries.to_crs(delta.crs)
        assert boundaries.geometry.is_valid.all()
        membership=np.zeros(delta.shape,dtype="uint8")
        for lga in boundaries.itertuples():
            w=geometry_window(delta,[lga.geometry])
            inside=geometry_mask([lga.geometry],out_shape=(int(w.height),int(w.width)),transform=delta.window_transform(w),invert=True)
            p=positive.read(1,window=w);c=candidates.read(1,window=w)
            aoi=inside&(p!=255);valid=inside&(p==1);eligible=inside&(c!=255)
            membership[w.toslices()]+=aoi.astype("uint8")
            v=delta.read(window=w)[:,valid]
            assert np.all(np.isfinite(v)) and np.all(v!=-9999)
            n=int(valid.sum());den=int(aoi.sum())
            record=dict(lga=lga.shapeName,shape_id=lga.shapeID,aoi_pixels=den,aoi_area_km2=den*0.0001,valid_pixels=n,valid_area_km2=n*0.0001,valid_coverage_pct=100*n/den if den else None,candidate_eligible_pixels=int(eligible.sum()),clean_candidate_pixels=int(((c==1)&inside).sum()))
            for band,pol in enumerate(("vh","vv")):
                count=int((v[band]<=-3).sum())
                record[pol+"_median_change_db"]=float(np.median(v[band])) if n else None
                record[pol+"_decrease_ge3_pixels"]=count
                record[pol+"_decrease_ge3_area_km2"]=count*0.0001
                record[pol+"_decrease_ge3_pct_valid"]=100*count/n if n else None
            both=int(((v[0]<=-3)&(v[1]<=-3)).sum())
            record["both_decrease_ge3_pixels"]=both
            record["both_decrease_ge3_pct_valid"]=100*both/n if n else None
            record["clean_candidate_area_km2"]=record["clean_candidate_pixels"]*0.0001
            record["clean_candidate_pct_eligible"]=100*record["clean_candidate_pixels"]/record["candidate_eligible_pixels"] if record["candidate_eligible_pixels"] else None
            assert record["clean_candidate_pixels"]<=record["vh_decrease_ge3_pixels"]<=n<=den
            rows.append(record)
            print(lga.shapeName,flush=True)
        audit=dict(state_aoi_pixels=0,state_valid_pixels=0,aoi_pixels_outside_lga_union=0,valid_pixels_outside_lga_union=0,aoi_pixels_in_multiple_lgas=0,state_candidate_pixels=0,candidate_pixels_outside_lga_union=0)
        for _,w in positive.block_windows(1):
            p=positive.read(1,window=w);c=candidates.read(1,window=w);m=membership[w.toslices()]
            audit["state_aoi_pixels"]+=int((p!=255).sum())
            audit["state_valid_pixels"]+=int((p==1).sum())
            audit["aoi_pixels_outside_lga_union"]+=int(((p!=255)&(m==0)).sum())
            audit["valid_pixels_outside_lga_union"]+=int(((p==1)&(m==0)).sum())
            audit["aoi_pixels_in_multiple_lgas"]+=int((m>1).sum())
            audit["state_candidate_pixels"]+=int((c==1).sum())
            audit["candidate_pixels_outside_lga_union"]+=int(((c==1)&(m==0)).sum())
    table=pd.DataFrame(rows)
    if audit["aoi_pixels_in_multiple_lgas"]==0:
        assert table.aoi_pixels.sum()+audit["aoi_pixels_outside_lga_union"]==audit["state_aoi_pixels"]
        assert table.valid_pixels.sum()+audit["valid_pixels_outside_lga_union"]==audit["state_valid_pixels"]
        assert table.clean_candidate_pixels.sum()+audit["candidate_pixels_outside_lga_union"]==audit["state_candidate_pixels"]
    metrics={"vh_decrease_ge3_area_km2":False,"vh_decrease_ge3_pct_valid":False,"vv_decrease_ge3_pct_valid":False,"vh_median_change_db":True,"clean_candidate_area_km2":False}
    for metric,ascending in metrics.items():
        table[metric+"_rank"]=table[metric].rank(method="min",ascending=ascending).astype("Int64")
    table.to_csv(outputs[0],index=False)
    mapped=boundaries.merge(table,left_on="shapeID",right_on="shape_id",validate="one_to_one")
    mapped.to_file(outputs[1],layer="lga_change_summary",driver="GPKG")
    reread=gpd.read_file(outputs[1],layer="lga_change_summary")
    assert len(reread)==20 and reread.geometry.is_valid.all()
    report=dict(scope="LGA polygons intersected with rasterized Lagos state AOI, pixel centers; common-positive VH/VV support",interpretation="geographic consistency, not flood validation",boundary_audit=audit,alimosho=table[table.lga=="Alimosho"].iloc[0].to_dict(),top_vh_decrease_area=table.sort_values("vh_decrease_ge3_area_km2",ascending=False)[["lga","vh_decrease_ge3_area_km2","vh_decrease_ge3_pct_valid","valid_coverage_pct"]].head(5).to_dict("records"),top_vh_decrease_fraction=table.sort_values("vh_decrease_ge3_pct_valid",ascending=False)[["lga","vh_decrease_ge3_area_km2","vh_decrease_ge3_pct_valid","valid_coverage_pct"]].head(5).to_dict("records"),checks=["Input hashes match","20 unique valid LGA geometries","All sampled changes finite and not nodata","Counts reconcile to state totals when no overlaps","GeoPackage reopened"],limitations=["Ranking describes observed pixels, not missing portions of LGAs","Pixel changes are not independent samples","3 dB is a descriptive cutoff, not a flood label","Neighborhoods are not equated to administrative units","Boundary gaps reported separately; no invented assignment"])
    save_json(outputs[2],report)
    for path in outputs:
        manifest[path.relative_to(ROOT).as_posix()]=dict(source=[p.relative_to(ROOT).as_posix() for p in inputs],sha256=sha256(path),bytes=path.stat().st_size,processing="LGA geographic-consistency summary, not accuracy")
    save_json(manifest_path,manifest)
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
