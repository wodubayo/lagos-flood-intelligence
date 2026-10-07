"""Audit MODIS flood products on their native grid; no accuracy labels are generated."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from datetime import datetime, timezone
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--gdal-bin",default=r"C:\Program Files\QGIS 3.44.15\bin")
    args=parser.parse_args()
    report_path=ROOT/"docs/validation/modis_quality_report.json"
    if report_path.exists(): raise FileExistsError(report_path)
    audit=json.loads((ROOT/"docs/validation/modis_archive_check.json").read_text())
    aoi_path=ROOT/"data/interim/boundaries/lagos_state.geojson"
    aoi=gpd.read_file(aoi_path).to_crs(4326)
    west,south,east,north=aoi.total_bounds
    output=ROOT/"data/processed/validation/modis"
    output.mkdir(parents=True,exist_ok=True)
    rows=[]; assets={}
    for item in audit["files"]:
        p=ROOT/"data/raw/validation/modis"/item["filename"]
        assert p.stat().st_size==item["listed_bytes"],p
        info=json.loads(subprocess.check_output([str(Path(args.gdal_bin)/"gdalinfo.exe"),"-json",str(p)],text=True))
        metadata=info["metadata"][""]
        assert metadata["RANGEBEGINNINGDATE"]==item["date"]
        assert metadata["WESTBOUNDINGCOORDINATE"]=="0.000000"
        assert metadata["NORTHBOUNDINGCOORDINATE"]=="10.000000"
        assets[p.relative_to(ROOT).as_posix()]={"source":item["url"],"bytes":p.stat().st_size,"sha256":sha(p)}
        layers={}
        datasets=info["metadata"]["SUBDATASETS"]
        for key,src in datasets.items():
            if not key.endswith("_NAME"): continue
            name=src.rsplit(":",1)[1]
            dest=output/(item["date"].replace("-","")+"_"+name+".tif")
            if dest.exists(): raise FileExistsError(dest)
            subprocess.run([str(Path(args.gdal_bin)/"gdal_translate.exe"),"-q","-of","GTiff",
                "-co","COMPRESS=DEFLATE","-projwin",str(west),str(north),str(east),str(south),
                src,str(dest)],check=True,capture_output=True)
            with rasterio.open(dest) as d:
                assert d.crs.is_geographic
                native_aoi=aoi.to_crs(d.crs)
                assert abs(d.transform.a-1/480)<1e-10
                inside=geometry_mask(native_aoi.geometry,transform=d.transform,out_shape=d.shape,invert=True)
                data=d.read(1)
                values,counts=np.unique(data[inside],return_counts=True)
                stats={"class_or_count_histogram":dict(zip(map(str,values.tolist()),counts.tolist())),
                       "aoi_pixel_centers":int(inside.sum()),"bounds":list(d.bounds),"shape":list(d.shape),"crs_wkt":d.crs.to_wkt()}
                if name.startswith("Flood"):
                    assert set(values.tolist()) <= {0,1,2,3,255}
                    stats["sufficient_data_pct"]=float(np.mean(data[inside]!=255)*100)
                    stats["flood_pixels"]=int(np.sum(data[inside]==3))
                else:
                    stats["positive_count_pct"]=float(np.mean((data[inside]>0)&(data[inside]!=255))*100)
                layers[name]=stats
            assets[dest.relative_to(ROOT).as_posix()]={"source":p.relative_to(ROOT).as_posix(),
                "subdataset":name,"bytes":dest.stat().st_size,"sha256":sha(dest)}
        rows.append({"date":item["date"],"metadata":metadata,"layers":layers})
    report={"checked_utc":datetime.now(timezone.utc).isoformat(),
        "method":"Native geographic grid, bounding-box crops without resampling; statistics restricted to Lagos AOI pixel centers. Crops include pixels outside AOI. GDAL reports an unspecified datum on Clarke 1866; AOI is transformed to that geographic CRS by PROJ, with datum uncertainty retained. No WGS84 override applied.",
        "aoi_sha256":sha(aoi_path),"class_mapping":{"0":"No water","1":"Reference surface water","2":"Recurring flood","3":"Unusual flood","255":"Insufficient data"},
        "limitation":"Product agreement is not acquisition-time ground truth. Daily/composite timing differs from Sentinel-1. No accuracy scores calculated.",
        "files":rows,"assets":assets}
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    manifest_path=ROOT/"docs/acquisition/manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(assets)
    manifest[report_path.relative_to(ROOT).as_posix()]={"source":"src/check_modis_quality.py","bytes":report_path.stat().st_size,"sha256":sha(report_path)}
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    for row in rows:
        for name,stats in row["layers"].items():
            if name.startswith("Flood"): print(row["date"],name,stats["class_or_count_histogram"],round(stats["sufficient_data_pct"],2))
if __name__=="__main__": main()
