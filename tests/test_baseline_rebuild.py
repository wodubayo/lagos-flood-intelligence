import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from rebuild_baseline import compare_rasters

class RasterComparisonTests(unittest.TestCase):
    def test_detects_pixel_and_grid_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a.tif",Path(tmp)/"b.tif"
            profile=dict(driver="GTiff",height=2,width=2,count=1,dtype="float32",crs="EPSG:32631",transform=from_origin(0,20,10,10),nodata=-9999)
            def write(path,values,options):
                with rasterio.open(path,"w",**options) as dst: dst.write(np.array(values,dtype="float32"),1)
            values=[[1,-9999],[3,4]]
            write(a,values,profile);write(b,values,profile)
            self.assertTrue(compare_rasters(a,b)["equal"])
            rounded={**profile,"transform":from_origin(5.820766091346741e-11,20,10,10)}
            write(b,values,rounded)
            result=compare_rasters(a,b)
            self.assertTrue(result["grid_equal"])
            self.assertTrue(result["equal"])
            write(b,[[1,0],[3,4]],profile)
            self.assertEqual(compare_rasters(a,b)["differing_band_pixels"],1)
            write(b,values,{**profile,"transform":from_origin(10,20,10,10)})
            self.assertFalse(compare_rasters(a,b)["grid_equal"])

class DiagnosticComparisonTests(unittest.TestCase):
    def test_json_ignores_only_creation_time(self):
        import json
        from rebuild_baseline import compare_output
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a.json",Path(tmp)/"b.json"
            a.write_text(json.dumps({"created_utc":"old","count":10}))
            b.write_text(json.dumps({"created_utc":"new","count":10}))
            self.assertTrue(compare_output(a,b)["equal"])
            b.write_text(json.dumps({"created_utc":"new","count":11}))
            self.assertFalse(compare_output(a,b)["equal"])

    def test_vector_attribute_and_geometry_changes(self):
        import geopandas as gpd
        from shapely.geometry import Point
        from rebuild_baseline import compare_output
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            frame=gpd.GeoDataFrame({"patch_id":["C1"],"pixels":[25]},geometry=[Point(0,0)],crs=32631)
            a=root/"a.gpkg";frame.to_file(a,layer="patches",driver="GPKG")
            b=root/"b.gpkg";frame.to_file(b,layer="patches",driver="GPKG")
            self.assertTrue(compare_output(a,b)["equal"])
            frame["pixels"]=26
            c=root/"c.gpkg";frame.to_file(c,layer="patches",driver="GPKG")
            self.assertFalse(compare_output(a,c)["equal"])
            frame["pixels"]=25;frame.geometry=[Point(1,0)]
            d=root/"d.gpkg";frame.to_file(d,layer="patches",driver="GPKG")
            self.assertFalse(compare_output(a,d)["equal"])

    def test_stage_order_resolves_internal_dependencies(self):
        from run_baseline import STAGES
        producers={p:name for name,stage in STAGES.items() for p in stage["outputs"]}
        seen=set()
        for name,stage in STAGES.items():
            for path in stage["inputs"]:
                if path in producers: self.assertIn(producers[path],seen)
            seen.add(name)




class AlignmentQATests(unittest.TestCase):
    def test_full_mask_check_detects_invalid_support(self):
        from prepare_sentinel1_pair import verify_prepared_outputs
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[root/"before.tif",root/"after.tif"];mask=root/"mask.tif"
            profile=dict(driver="GTiff",height=1,width=2,count=2,dtype="float32",crs="EPSG:32631",transform=from_origin(0,10,10,10),nodata=-9999)
            for path in paths:
                with rasterio.open(path,"w",**profile) as d:
                    d.write(np.array([[[1,-9999]],[[2,-9999]]],dtype="float32"))
                    d.set_band_description(1,"Sigma0_VH");d.set_band_description(2,"Sigma0_VV")
            mp={**profile,"count":1,"dtype":"uint8","nodata":255}
            with rasterio.open(mask,"w",**mp) as d: d.write(np.array([[1,255]],dtype="uint8"),1)
            self.assertEqual(verify_prepared_outputs(paths,mask)["common_pixel_count_verified"],1)
            with rasterio.open(mask,"w",**mp) as d: d.write(np.array([[1,1]],dtype="uint8"),1)
            with self.assertRaises(ValueError): verify_prepared_outputs(paths,mask)

if __name__=="__main__": unittest.main()
