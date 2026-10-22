import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("runner",Path(__file__).resolve().parents[1]/"src/run_baseline.py")
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class PreflightTests(unittest.TestCase):
    def test_missing_partial_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"docs/acquisition").mkdir(parents=True)
            (root/"docs/acquisition/manifest.json").write_text(json.dumps({"input":{"sha256":"bad"}}))
            stages={"one":{"inputs":["input"],"outputs":["a","b"]}}
            self.assertEqual(runner.inspect(root,stages)["one"]["state"],"missing_inputs")
            (root/"input").write_text("data");(root/"a").write_text("partial")
            result=runner.inspect(root,stages,True)["one"]
            self.assertEqual(result["state"],"partial_outputs")
            self.assertEqual(result["checksum_mismatches"],["input"])
            self.assertEqual(result["unregistered_assets"],["a"])
if __name__=="__main__": unittest.main()
