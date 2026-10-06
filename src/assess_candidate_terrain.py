"""Projected DSM slope sensitivity and exact candidate review polygons."""
import json
from collections import defaultdict
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import shapes, rasterize
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape
from shapely.ops import unary_union
from prepare_sentinel1_pair import ROOT, save_json, sha256

def horn_slope(z, spacing=30):
    z=np.asarray(z,dtype="float64")
    a,b,c=z[:-2,:-2],z[:-2,1:-1],z[:-2,2:]
    d,e,f=z[1:-1,:-2],z[1:-1,1:-1],z[1:-1,2:]
    g,h,i=z[2:,:-2],z[2:,1:-1],z[2:,2:]
    good=np.logical_and.reduce([np.isfinite(v) for v in (a,b,c,d,e,f,g,h,i)])
    dx=((c+2*f+i)-(a+2*d+g))/(8*spacing)
    dy=((g+2*h+i)-(a+2*b+c))/(8*spacing)
    result=np.full(z.shape,-9999,dtype="float32")
    result[1:-1,1:-1]=np.where(good,np.degrees(np.arctan(np.hypot(dx,dy))),-9999)
    return result

def components(cells):
    remaining=set(cells); ids={}; n=0
    for start in sorted(remaining):
        if start not in remaining: continue
        n+=1; remaining.remove(start); todo=[start]
        while todo:
            r,c=todo.pop(); ids[r,c]=n
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    p=(r+dr,c+dc)
                    if p in remaining:
                        remaining.remove(p); todo.append(p)
    return ids

def main():
    folder=ROOT/"data/processed/sentinel1"
    dem_path=ROOT/"data/interim/dem/lagos_copernicus_dem30.tif"
    csv_path=folder/"lagos_candidate_review_points.csv"
    mask_path=folder/"lagos_candidate_exploratory_clean.tif"
    slope_path=folder/"lagos_dsm_slope_30m.tif"
    vector_path=folder/"lagos_candidate_review_polygons.gpkg"
    table_path=ROOT/"docs/acquisition/sentinel1_candidate_polygons.csv"
    report_path=ROOT/"docs/acquisition/sentinel1_slope_report.json"
    outputs=[slope_path,vector_path,table_path,report_path]
    if any(p.exists() for p in outputs): raise FileExistsError("Preserve previous outputs before rerunning")
    manifest_path=ROOT/"docs/acquisition/manifest.json"
    manifest=json.loads(manifest_path.read_text())
    inputs=[dem_path,csv_path,mask_path]
    for p in inputs:
        assert sha256(p)==manifest[p.relative_to(ROOT).as_posix()]["sha256"]
    with rasterio.open(dem_path) as src:
        tr,width,height=calculate_default_transform(src.crs,"EPSG:32631",src.width,src.height,*src.bounds,resolution=30)
        z=np.full((height,width),-9999,dtype="float32")
        reproject(rasterio.band(src,1),z,src_transform=src.transform,src_crs=src.crs,src_nodata=src.nodata,dst_transform=tr,dst_crs="EPSG:32631",dst_nodata=-9999,resampling=Resampling.bilinear)
    z[z==-9999]=np.nan
    slope=horn_slope(z)
    profile=dict(driver="GTiff",width=width,height=height,count=1,dtype="float32",crs="EPSG:32631",transform=tr,nodata=-9999,tiled=True,compress="deflate",predictor=3)
    with rasterio.open(slope_path,"w",**profile) as dst:
        dst.write(slope,1); dst.set_band_description(1,"DSM slope in degrees, Horn 3x3, 30m")
    pts=pd.read_csv(csv_path)
    with rasterio.open(mask_path) as src:
        clean=src.read(1); transform=src.transform; crs=src.crs
        rows=pts["row"].to_numpy(); cols=pts["column"].to_numpy()
        assert np.array_equal(clean[rows,cols]==1,pts.retained_after_cleanup==1)
        assert int((clean==1).sum())==int((pts.retained_after_cleanup==1).sum())
        x,y=rasterio.transform.xy(transform,rows,cols)
    rr,cc=rasterio.transform.rowcol(tr,x,y)
    rr=np.asarray(rr);cc=np.asarray(cc)
    sampled=np.full(len(pts),np.nan)
    inside=(rr>=0)&(rr<height)&(cc>=0)&(cc<width)
    sampled[inside]=slope[rr[inside],cc[inside]]
    sampled[sampled==-9999]=np.nan
    pts["slope_deg"]=sampled
    sensitivity={}
    for name,frame in [("raw",pts),("clean",pts[pts.retained_after_cleanup==1])]:
        s=frame.slope_deg.to_numpy()
        sensitivity[name]={"pixels":len(s),"unknown_slope_pixels":int((~np.isfinite(s)).sum()),"median_slope_deg":float(np.nanmedian(s)),"cutoffs":[dict(max_slope_deg=t,retained_pixels=int((s<=t).sum()),retained_area_km2=float((s<=t).sum())*0.0001) for t in (2,5,10)]}
    selected=pts[pts.retained_after_cleanup==1].copy()
    mapping=components(zip(selected["row"],selected["column"]))
    selected["patch_id"]=[mapping[r,c] for r,c in zip(selected["row"],selected["column"])]
    labels=np.zeros(clean.shape,dtype="int32")
    for (r,c),label in mapping.items(): labels[r,c]=label
    parts=defaultdict(list)
    # Four-connected pieces are unioned by the eight-connected ID, preserving
    # diagonal contacts as valid multipart polygons rather than self-touching rings.
    for geom,label in shapes(labels,mask=labels>0,transform=transform,connectivity=4):
        parts[int(label)].append(shape(geom))
    records=[]
    measures=["june_vh_db","june_vv_db","july_vh_db","july_vv_db","delta_vh_db","delta_vv_db","dsm_elevation_m","slope_deg"]
    for pid,frame in selected.groupby("patch_id",sort=True):
        geom=unary_union(parts[int(pid)])
        assert geom.is_valid and abs(geom.area-len(frame)*100)<0.01
        row=dict(patch_id=f"C{pid:04d}",pixels=len(frame),area_m2=len(frame)*100,area_ha=len(frame)*0.01,status="exploratory_unvalidated",geometry=geom)
        for name in measures:
            row[name+"_median"]=float(frame[name].median()) if frame[name].notna().any() else None
        row["slope_known_pixels"]=int(frame.slope_deg.notna().sum())
        row["vv_decrease_pct"]=100*float((frame.delta_vv_db<0).mean())
        records.append(row)
    gdf=gpd.GeoDataFrame(records,crs=crs)
    assert int(gdf.pixels.sum())==len(selected)
    # Exact raster-vector roundtrip, including component IDs.
    back=rasterize([(geom,int(pid[1:])) for geom,pid in zip(gdf.geometry,gdf.patch_id)],out_shape=clean.shape,transform=transform,dtype="int32")
    assert np.array_equal(back,labels)
    gdf.to_file(vector_path,layer="candidate_patches",driver="GPKG")
    check=gpd.read_file(vector_path,layer="candidate_patches")
    assert len(check)==len(gdf) and check.geometry.is_valid.all()
    assert abs(check.geometry.area.sum()-len(selected)*100)<0.01
    gdf.drop(columns="geometry").to_csv(table_path,index=False)
    report=dict(status="provisional; no slope cutoff selected or applied",method="DSM reprojected bilinearly to EPSG:32631 at 30m; Horn 3x3 slope in degrees; require nine valid samples; one-cell edge nodata; nearest slope-cell sampling at SAR pixel centers",sensitivity=sensitivity,patch_count=len(gdf),polygon_area_km2=float(gdf.area_m2.sum())/1e6,minimum_patch_pixels=int(gdf.pixels.min()),maximum_patch_pixels=int(gdf.pixels.max()),checks=["input hashes match","candidate point/mask consistency","valid polygon geometry","exact component-ID raster/vector roundtrip","GeoPackage reopen and area conservation"],limitations=["DSM slope can reflect buildings/vegetation.","30m slope cannot resolve street-scale drainage.","Sensitivity does not repeat cleanup after slope screening.","Unknown slope is separate from failing slope cutoff.","Polygons represent original clean candidates, not slope-filtered or confirmed flood extent."])
    save_json(report_path,report)
    for p in outputs:
        manifest[p.relative_to(ROOT).as_posix()]=dict(source=[v.relative_to(ROOT).as_posix() for v in inputs],sha256=sha256(p),bytes=p.stat().st_size,processing="Slope sensitivity and unfiltered clean candidate review polygons; see sentinel1_slope_report.json")
    save_json(manifest_path,manifest)
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
