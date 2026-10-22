"""Validated configuration for the supported Lagos event and exploratory parameters."""
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/"config/baseline.json"
FIXED_EVENT={"id":"LAG_2024_07","before_date":"20240621","after_date":"20240703","aoi":"Lagos State"}
FIXED_METHOD={"crs":"EPSG:32631","pixel_spacing_m":10,"jrc_exclusion_pct":90,"connectivity":8,"lga_decrease_db":3}

def validate(config):
    if set(config)!={"schema_version","event","fixed_method","candidates","terrain"} or config["schema_version"]!=1:
        raise ValueError("Unsupported configuration schema")
    if config["event"]!=FIXED_EVENT or config["fixed_method"]!=FIXED_METHOD:
        raise ValueError("Only the current Lagos event/grid/method is supported; changing dates or CRS needs a new input mapping")
    c=config["candidates"]
    if set(c)!={"dark_thresholds_db","drop_thresholds_db","preview_dark_db","preview_drop_db","cleanup_sizes_pixels","preview_min_pixels"}:
        raise ValueError("Unknown or missing candidate settings")
    if set(config["terrain"])!={"slope_cutoffs_deg"}: raise ValueError("Unknown terrain settings")
    def numbers(values):
        return isinstance(values,list) and bool(values) and all(type(v) in (int,float) and math.isfinite(v) for v in values) and len(set(values))==len(values)
    for key in ("dark_thresholds_db","drop_thresholds_db","cleanup_sizes_pixels"):
        if not numbers(c[key]): raise ValueError("Expected nonempty unique finite numbers: "+key)
    if any(v>=0 for v in c["drop_thresholds_db"]): raise ValueError("Drop thresholds must be negative")
    if len(c["dark_thresholds_db"])*len(c["drop_thresholds_db"])>254: raise ValueError("Agreement counts exceed uint8 capacity")
    if any(type(v)!=int or v<1 for v in c["cleanup_sizes_pixels"]): raise ValueError("Cleanup sizes must be positive integers")
    for preview,grid in (("preview_dark_db","dark_thresholds_db"),("preview_drop_db","drop_thresholds_db"),("preview_min_pixels","cleanup_sizes_pixels")):
        if type(c[preview]) not in (int,float) or c[preview] not in c[grid]: raise ValueError("Preview setting must belong to its grid: "+preview)
    if type(c["preview_min_pixels"])!=int: raise ValueError("Preview size must be integer")
    if c["preview_drop_db"]>-3: raise ValueError("Preview drop must be <= -3 dB for the current LGA candidate/decrease invariant")
    slopes=config["terrain"]["slope_cutoffs_deg"]
    if not numbers(slopes) or any(not 0<=v<=90 for v in slopes): raise ValueError("Slope cutoffs must be between 0 and 90")
    return config

def load_config(path=DEFAULT):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))
CONFIG=load_config()
