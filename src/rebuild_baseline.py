"""Rebuild baseline and diagnostics in an isolated copy and compare reviewed outputs."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import numpy as np
import rasterio
from run_baseline import ROOT, STAGES, checksum
from pipeline_config import DEFAULT, load_config

def export_snap_pair(snap_run, date, destination, canonical_june_transform=None):
    """Create the two-band linear-Sigma0 input from one completed SNAP DIMAP."""
    import rasterio
    source_dim=snap_run/f"S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
    source_data=source_dim.with_suffix(".data")
    if not source_dim.is_file() or not source_data.is_dir():
        raise FileNotFoundError("Missing SNAP terrain-corrected DIMAP: "+str(source_dim))
    band_paths=[source_data/"Sigma0_VH.img",source_data/"Sigma0_VV.img"]
    with rasterio.open(band_paths[0]) as first, rasterio.open(band_paths[1]) as second:
        if (first.crs,first.transform,first.width,first.height)!=(second.crs,second.transform,second.width,second.height):
            raise ValueError("SNAP VH/VV grids differ for "+date)
        profile=first.profile.copy()
        profile.update(driver="GTiff",count=2,dtype="float32",compress="deflate",predictor=3,
                       tiled=True,blockxsize=512,blockysize=512,BIGTIFF="IF_SAFER")
        if date=="20240621" and canonical_june_transform is not None:
            if not np.allclose(tuple(first.transform),tuple(canonical_june_transform),rtol=0,atol=1e-8):
                raise ValueError("June SNAP export grid differs from the declared reference grid")
            profile["transform"]=canonical_june_transform
        temporary=destination.with_suffix(".part.tif")
        destination.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(temporary,"w",**profile) as out:
            out.set_band_description(1,"Sigma0_VH")
            out.set_band_description(2,"Sigma0_VV")
            out.update_tags(source_dimap=str(source_dim),units="linear sigma0",
                            reference_grid="Saved June grid coordinates; metadata-only sub-nanometre rounding normalization")
            for _,window in first.block_windows(1):
                out.write(first.read(1,window=window).astype("float32"),1,window=window)
                out.write(second.read(1,window=window).astype("float32"),2,window=window)
    temporary.replace(destination)
    return source_dim,band_paths

def compare_rasters(reference, rebuilt, compare_descriptions=True):
    with rasterio.open(reference) as a, rasterio.open(rebuilt) as b:
        transform_delta=max(abs(x-y) for x,y in zip(a.transform,b.transform))
        grid_equal=(a.crs==b.crs and np.allclose(tuple(a.transform),tuple(b.transform),rtol=0,atol=1e-8)
                    and a.shape==b.shape and a.count==b.count and a.dtypes==b.dtypes and a.nodata==b.nodata)
        if not grid_equal: return {"grid_equal":False,"equal":False}
        differing=0;max_difference=0.0
        for _,window in a.block_windows(1):
            x=a.read(window=window);y=b.read(window=window)
            same=(x==y)|(np.isnan(x)&np.isnan(y))
            differing+=int(np.count_nonzero(~same))
            if not same.all():
                delta=np.abs(x.astype("float64")-y.astype("float64"))
                finite=delta[np.isfinite(delta)]
                if finite.size: max_difference=max(max_difference,float(finite.max()))
        descriptions_equal=a.descriptions==b.descriptions
        return {"grid_equal":True,"max_transform_difference":transform_delta,"band_descriptions_equal":descriptions_equal,
                "differing_band_pixels":differing,"max_absolute_difference":max_difference,
                "equal":differing==0 and (descriptions_equal or not compare_descriptions)}


def compare_output(reference, rebuilt):
    suffix=reference.suffix.lower()
    if suffix==".tif": return compare_rasters(reference,rebuilt)
    if suffix==".csv":
        import pandas as pd
        a=pd.read_csv(reference);b=pd.read_csv(rebuilt)
        if list(a.columns)!=list(b.columns) or a.shape!=b.shape: return {"method":"CSV values; numeric tolerance 1e-8","equal":False,"reason":"columns or shape differ"}
        details={}; equal=True
        for column in a.columns:
            if pd.api.types.is_numeric_dtype(a[column]) and pd.api.types.is_numeric_dtype(b[column]):
                x=a[column].to_numpy(dtype="float64");y=b[column].to_numpy(dtype="float64")
                ok=bool(np.allclose(x,y,rtol=0,atol=1e-8,equal_nan=True))
                delta=np.abs(x-y); finite=delta[np.isfinite(delta)]
                details[column]={"equal_within_tolerance":ok,"max_absolute_difference":float(finite.max()) if finite.size else 0.0}
            else:
                ok=bool(a[column].equals(b[column]));details[column]={"equal":ok}
            equal=equal and ok
        return {"method":"column comparison; numeric tolerance 1e-8","columns":details,"equal":equal}
    if suffix==".json":
        a=json.loads(reference.read_text(encoding="utf-8"))
        b=json.loads(rebuilt.read_text(encoding="utf-8"))
        for obj in (a,b): obj.pop("created_utc",None)
        def compare_json(x,y,path="$",differences=None):
            differences=differences if differences is not None else []
            if type(x) in (int,float) and type(y) in (int,float):
                if not np.isclose(x,y,rtol=0,atol=1e-8): differences.append(path)
            elif type(x)!=type(y): differences.append(path)
            elif isinstance(x,dict):
                if x.keys()!=y.keys(): differences.append(path)
                else:
                    for key in x: compare_json(x[key],y[key],path+"."+key,differences)
            elif isinstance(x,list):
                if len(x)!=len(y): differences.append(path)
                else:
                    for i,(left,right) in enumerate(zip(x,y)): compare_json(left,right,f"{path}[{i}]",differences)
            elif x!=y: differences.append(path)
            return differences
        differences=compare_json(a,b)
        return {"method":"JSON content excluding created_utc; numeric tolerance 1e-8","equal":not differences,"differing_paths":differences[:25]}
    if suffix==".gpkg":
        import fiona
        import geopandas as gpd
        import pandas as pd
        layers=fiona.listlayers(reference)
        if layers!=fiona.listlayers(rebuilt): return {"equal":False,"reason":"layer names differ"}
        details={}
        for layer in layers:
            a=gpd.read_file(reference,layer=layer);b=gpd.read_file(rebuilt,layer=layer)
            key="patch_id" if "patch_id" in a.columns else "shape_id"
            if not a[key].is_unique or not b[key].is_unique: raise ValueError("Nonunique vector comparison key")
            a=a.sort_values(key).reset_index(drop=True);b=b.sort_values(key).reset_index(drop=True)
            attrs=True
            try: pd.testing.assert_frame_equal(a.drop(columns=a.geometry.name),b.drop(columns=b.geometry.name),check_exact=True)
            except AssertionError: attrs=False
            geometry=(len(a)==len(b) and a.crs==b.crs and bool(a.geometry.geom_equals_exact(b.geometry,tolerance=1e-8).all()))
            details[layer]={"features":len(a),"attributes_equal":attrs,"geometry_equal":geometry}
        return {"method":"key-sorted exact attributes and geometry; database timestamps ignored",
                "layers":details,"equal":all(v["attributes_equal"] and v["geometry_equal"] for v in details.values())}
    raise ValueError("Unsupported comparison: "+str(reference))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--config",type=Path,default=DEFAULT,help="Validated settings copied into the isolated run")
    parser.add_argument("--snap-run",type=Path,help="Use terrain-corrected products from outputs/snap_runs/<run-id> instead of manual GeoTIFF/DIM inputs")
    args=parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.run_id):
        parser.error("run-id must contain only letters, digits, underscore or hyphen")
    selected_config=load_config(args.config)
    snap_run=args.snap_run
    if snap_run is not None and not snap_run.is_absolute(): snap_run=ROOT/snap_run
    if snap_run is not None and not snap_run.is_dir(): parser.error("--snap-run directory does not exist")
    run=ROOT/"outputs/runs"/args.run_id
    run.mkdir(parents=True,exist_ok=False)
    report={"run_id":args.run_id,"started_utc":datetime.now(timezone.utc).isoformat(),
      "validation_status":"unresolved; exploratory baseline only","status":"running",
      "python":sys.version,"platform":platform.platform(),
      "packages":{p:importlib.metadata.version(p) for p in ("numpy","rasterio","geopandas","shapely","pyproj","pandas","fiona")},
      "gdal":rasterio.__gdal_version__,"inputs":{},"scripts":{},"stages":[],"comparisons":{}}
    report["configuration"]=selected_config
    report["snap_run"]=(str(snap_run) if snap_run is not None else None)
    report["configuration_source_sha256"]=checksum(args.config)
    (run/"config").mkdir()
    (run/"config/baseline.json").write_text(json.dumps(selected_config,indent=2)+"\n",encoding="utf-8")
    report_path=run/"rebuild_report.json"
    def save(): report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    try:
        manifest_path=ROOT/"docs/acquisition/manifest.json"
        manifest_hash=checksum(manifest_path)
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        generated={p for stage in STAGES.values() for p in stage["outputs"]}
        inputs=sorted({p for stage in STAGES.values() for p in stage["inputs"]}-generated)
        snap_sources={}
        if snap_run is not None:
            with rasterio.open(ROOT/"data/interim/sentinel1/S1A_20240621_TC_linear.tif") as reference_grid_ds:
                canonical_june_transform=reference_grid_ds.transform
            for rel in inputs:
                match=re.fullmatch(r"data/interim/sentinel1/S1A_(\d{8})_TC_linear\.tif",rel)
                dim_match=re.fullmatch(r"data/interim/sentinel1/S1A_(\d{8})_Orb_TNR_Cal_Spk_TC\.dim",rel)
                if match:
                    date=match.group(1); source_dim,band_paths=export_snap_pair(snap_run,date,run/rel,canonical_june_transform)
                    snap_sources[rel]=(source_dim,band_paths)
                elif dim_match:
                    date=dim_match.group(1); source_dim=snap_run/f"S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
                    if not source_dim.is_file(): raise FileNotFoundError("Missing SNAP terrain-corrected DIMAP: "+str(source_dim))
                    snap_sources[rel]=(source_dim,[])
        references={p:checksum(ROOT/p) for p in sorted(generated)}
        report["reference_hashes"]=references
        for rel in inputs:
            source=ROOT/rel
            if rel in snap_sources:
                snap_dim,band_paths=snap_sources[rel]
                if rel.endswith(".tif"):
                    source_path=run/rel
                    source_hashes={str(path):checksum(path) for path in band_paths}
                    snap_input_check=compare_rasters(ROOT/rel,source_path,compare_descriptions=False)
                    report.setdefault("snap_input_comparisons",{})[rel]=snap_input_check
                else:
                    source_path=snap_dim
                    source_hashes={str(source_path):checksum(source_path)}
                    dest=run/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source_path,dest)
                digest=checksum(source_path)
                manifest[rel]={"sha256":digest,"bytes":source_path.stat().st_size,
                               "source":"SNAP raw-ZIP pair run","source_files":source_hashes}
            else:
                digest=checksum(source)
                expected=manifest.get(rel,{}).get("sha256")
                if expected and digest!=expected: raise ValueError("Input mismatch: "+rel)
                dest=run/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,dest)
                if checksum(dest)!=digest: raise ValueError("Copy mismatch: "+rel)
                source_path=source
                manifest[rel]={**manifest.get(rel,{}),"sha256":digest,"bytes":source.stat().st_size}
            report["inputs"][rel]={"sha256":digest,"source_path":str(source_path),"bytes":source_path.stat().st_size,
                                    **({"source_files":source_hashes} if rel in snap_sources else {})}
        (run/"src").mkdir()
        for name in dict.fromkeys([stage["script"] for stage in STAGES.values()]+["pipeline_config.py"]):
            source=ROOT/"src"/name;shutil.copy2(source,run/"src"/name)
            report["scripts"][name]=checksum(source)
        (run/"docs/acquisition").mkdir(parents=True,exist_ok=True)
        (run/"docs/acquisition/manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        save()
        for name,stage in STAGES.items():
            for rel in stage["outputs"]: (run/rel).parent.mkdir(parents=True,exist_ok=True)
            print("Running "+name,flush=True)
            with (run/(name+".log")).open("w",encoding="utf-8") as log:
                proc=subprocess.run([sys.executable,str(run/"src"/stage["script"])],cwd=run,stdout=log,stderr=subprocess.STDOUT)
            report["stages"].append({"name":name,"exit_code":proc.returncode,"log":name+".log"})
            save()
            if proc.returncode: raise RuntimeError("Stage failed: "+name+"; inspect run log")
        for rel in sorted(generated):
            report["comparisons"][rel]=compare_output(ROOT/rel,run/rel)
        report["original_outputs_unchanged"]=all(checksum(ROOT/p)==h for p,h in references.items())
        report["original_manifest_unchanged"]=checksum(manifest_path)==manifest_hash
        report["source_inputs_unchanged"]=all(checksum(Path(item["source_path"]))==item["sha256"] for item in report["inputs"].values())
        input_equal=all(v.get("equal",False) for v in report.get("snap_input_comparisons",{}).values())
        passed=all(v["equal"] for v in report["comparisons"].values()) and input_equal and all(report[k] for k in ("original_outputs_unchanged","original_manifest_unchanged","source_inputs_unchanged"))
        report["status"]="passed" if passed else "comparison_failed"
    except Exception as exc:
        report["status"]="failed";report["error"]=str(exc);raise
    finally:
        report["finished_utc"]=datetime.now(timezone.utc).isoformat();save()
    print(json.dumps({"status":report["status"],"outputs_compared":len(report["comparisons"]),"report":str(report_path)},indent=2),flush=True)
    return 0 if passed else 1
if __name__=="__main__":sys.exit(main())
