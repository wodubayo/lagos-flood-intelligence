"""Phase 4 entry point for the existing exploratory SAR baseline stages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pipeline_config import CONFIG

ROOT = Path(__file__).resolve().parents[1]
SAR = "data/processed/sentinel1/"
DATES = (CONFIG["event"]["before_date"], CONFIG["event"]["after_date"])
WATER = "data/interim/water/lagos_jrc_occurrence_1984_2021.tif"
LINEAR = [SAR+f"lagos_{d}_sigma0_linear.tif" for d in DATES]+[SAR+"lagos_pair_valid_mask.tif"]
CHANGE = [SAR+n for n in ("lagos_20240621_sigma0_db.tif","lagos_20240703_sigma0_db.tif","lagos_delta_sigma0_db.tif","lagos_pair_positive_mask.tif","lagos_coverage_diagnostic.tif")]
STAGES = {
 "align": {"script":"prepare_sentinel1_pair.py",
  "inputs":[f"data/interim/sentinel1/S1A_{d}_TC_linear.tif" for d in DATES]+[f"data/interim/sentinel1/S1A_{d}_Orb_TNR_Cal_Spk_TC.dim" for d in DATES]+["data/interim/boundaries/lagos_state.geojson"],
  "outputs":LINEAR+["docs/acquisition/sentinel1_alignment_report.json"]},
 "change": {"script":"analyze_sentinel1_change.py","inputs":LINEAR+[WATER,"data/interim/boundaries/sentinel1_pair_coverage.geojson"],
  "outputs":CHANGE+["docs/acquisition/sentinel1_change_report.json"]},
 "candidates": {"script":"explore_sentinel1_thresholds.py","inputs":CHANGE[:4]+[WATER],
  "outputs":[SAR+n for n in ("lagos_candidate_threshold_agreement.tif","lagos_candidate_exploratory_raw.tif","lagos_candidate_exploratory_clean.tif")]+["docs/acquisition/sentinel1_threshold_report.json","docs/acquisition/sentinel1_threshold_sensitivity.csv"]}
}

DEM = "data/interim/dem/lagos_copernicus_dem30.tif"
STAGES.update({
 "audit": {"script":"audit_sentinel1_candidates.py",
  "inputs":[SAR+"lagos_candidate_exploratory_raw.tif",SAR+"lagos_candidate_exploratory_clean.tif"]+CHANGE[:3]+[DEM,"docs/acquisition/sentinel1_threshold_report.json"],
  "outputs":[SAR+"lagos_candidate_review_points.csv","docs/acquisition/sentinel1_candidate_audit.json"]},
 "terrain": {"script":"assess_candidate_terrain.py",
  "inputs":[DEM,SAR+"lagos_candidate_review_points.csv",SAR+"lagos_candidate_exploratory_clean.tif"],
  "outputs":[SAR+"lagos_dsm_slope_30m.tif",SAR+"lagos_candidate_review_polygons.gpkg","docs/acquisition/sentinel1_candidate_polygons.csv","docs/acquisition/sentinel1_slope_report.json"]},
 "lga": {"script":"summarize_lga_change.py",
  "inputs":["data/interim/boundaries/lagos_lgas.geojson",SAR+"lagos_delta_sigma0_db.tif",SAR+"lagos_pair_positive_mask.tif",SAR+"lagos_candidate_exploratory_clean.tif"],
  "outputs":["docs/validation/lga_change_summary.csv","docs/validation/lga_change_summary.gpkg","docs/validation/lga_change_report.json"]}
})

def checksum(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def inspect(root, stages, verify=False):
    manifest=json.loads((root/"docs/acquisition/manifest.json").read_text(encoding="utf-8"))
    result={}; cache={}
    for name,stage in stages.items():
        missing=[p for p in stage["inputs"] if not (root/p).is_file()]
        existing=[p for p in stage["outputs"] if (root/p).is_file()]
        errors=[]; unregistered=[]
        if verify:
            for p in stage["inputs"]+stage["outputs"]:
                if not (root/p).is_file(): continue
                expected=manifest.get(p,{}).get("sha256")
                if not expected: unregistered.append(p); continue
                if p not in cache: cache[p]=checksum(root/p)
                if cache[p]!=expected: errors.append(p)
        result[name]={"missing_inputs":missing,"existing_outputs":existing,
          "state":"outputs_present" if len(existing)==len(stage["outputs"]) else "partial_outputs" if existing else "missing_inputs" if missing else "ready",
          "checksum_mismatches":errors,"unregistered_assets":unregistered}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify",action="store_true",help="Check available manifest hashes; report unregistered assets separately.")
    parser.add_argument("--run",choices=STAGES,help="Run one stage only when its inputs exist and none of its outputs exist.")
    args=parser.parse_args()
    selected={args.run:STAGES[args.run]} if args.run else STAGES
    results=inspect(ROOT,selected,args.verify or bool(args.run))
    print(json.dumps({"validation_status":"unresolved; exploratory candidates only","stages":results},indent=2),flush=True)
    if any(r["checksum_mismatches"] or r["missing_inputs"] or r["state"]=="partial_outputs" for r in results.values()): return 1
    if args.run:
        stage=STAGES[args.run]
        if results[args.run]["existing_outputs"]:
            print("Refusing to overwrite existing outputs.",file=sys.stderr);return 2
        for rel in stage["outputs"]: (ROOT/rel).parent.mkdir(parents=True,exist_ok=True)
        return subprocess.run([sys.executable,str(ROOT/"src"/stage["script"])],cwd=ROOT).returncode
    return 0
if __name__=="__main__": sys.exit(main())
