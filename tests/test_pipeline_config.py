import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pipeline_config import CONFIG, load_config, validate

class ConfigurationTests(unittest.TestCase):
    def test_supported_parameter_change_and_file_loading(self):
        c=copy.deepcopy(CONFIG)
        c["candidates"]["preview_dark_db"]=-24
        c["candidates"]["preview_min_pixels"]=100
        c["terrain"]["slope_cutoffs_deg"]=[1,4,8]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"custom.json";p.write_text(json.dumps(c))
            self.assertEqual(load_config(p),c)

    def test_rejects_unsupported_event_and_method(self):
        for group,key,value in [("event","after_date","20240715"),("fixed_method","crs","EPSG:4326")]:
            c=copy.deepcopy(CONFIG);c[group][key]=value
            with self.assertRaises(ValueError):validate(c)

    def test_rejects_invalid_candidate_settings(self):
        changes=[("preview_dark_db",-99),("preview_drop_db",-2),("cleanup_sizes_pixels",[0,25]),("drop_thresholds_db",[-3,float("nan")]),("dark_thresholds_db",[-21,-21]),("preview_min_pixels",True)]
        for key,value in changes:
            with self.subTest(key=key):
                c=copy.deepcopy(CONFIG);c["candidates"][key]=value
                with self.assertRaises(ValueError):validate(c)

    def test_rejects_agreement_overflow(self):
        c=copy.deepcopy(CONFIG)
        c["candidates"]["dark_thresholds_db"]=list(range(-40,-20))
        c["candidates"]["drop_thresholds_db"]=list(range(-20,0))
        with self.assertRaises(ValueError):validate(c)

    def test_rejects_unknown_settings(self):
        c=copy.deepcopy(CONFIG);c["candidates"]["typo"]=25
        with self.assertRaises(ValueError):validate(c)

    def test_isolated_stages_read_run_local_configuration(self):
        import shutil
        import subprocess
        c=copy.deepcopy(CONFIG)
        c["candidates"].update(preview_dark_db=-24,preview_drop_db=-4,preview_min_pixels=100)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"src").mkdir();(root/"config").mkdir()
            (root/"config/baseline.json").write_text(json.dumps(c))
            source=Path(__file__).resolve().parents[1]/"src"
            for name in ("pipeline_config.py","prepare_sentinel1_pair.py","explore_sentinel1_thresholds.py","audit_sentinel1_candidates.py"):
                shutil.copy2(source/name,root/"src"/name)
            command="import explore_sentinel1_thresholds as e; import audit_sentinel1_candidates as a; assert (e.DARK,e.DROP,e.MIN_PIXELS)==(-24,-4,100); assert (a.DARK,a.DROP,a.MIN_PIXELS)==(-24,-4,100)"
            subprocess.run([sys.executable,"-c",command],cwd=root/"src",check=True,capture_output=True)

if __name__=="__main__":unittest.main()
