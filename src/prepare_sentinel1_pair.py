"""Prepare matched linear-Sigma0 Lagos rasters from SNAP TC exports.

The original exports remain unchanged. Source zero is nodata, as declared in
their matching SNAP DIMAP metadata. Output nodata is -9999, including outside
Lagos. Negative noise-corrected values are retained, not log-transformed.
"""
import hashlib
import json
import math
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, from_bounds

ROOT = Path(__file__).resolve().parents[1]
NODATA = -9999.0
DATES = ("20240621", "20240703")


def save_json(path, value):
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aligned_window(bounds, transform):
    fractional = from_bounds(*bounds, transform=transform)
    left, top = math.floor(fractional.col_off), math.floor(fractional.row_off)
    right = math.ceil(fractional.col_off + fractional.width)
    bottom = math.ceil(fractional.row_off + fractional.height)
    return Window(left, top, right-left, bottom-top)


def band_metadata(dim):
    tree = ET.parse(dim)
    result = []
    for info in tree.findall(".//Spectral_Band_Info"):
        name = info.findtext("BAND_NAME")
        if name:
            result.append((int(info.findtext("BAND_INDEX")),
                           name, info.findtext("NO_DATA_VALUE_USED"),
                           float(info.findtext("NO_DATA_VALUE"))))
    result.sort()
    if len(result) != 2 or {r[1] for r in result} != {"Sigma0_VH", "Sigma0_VV"}:
        raise ValueError("Expected two Sigma0 bands in " + str(dim))
    if any(r[2].lower() != "true" or r[3] != 0 for r in result):
        raise ValueError("Source zero-nodata assumption not supported by DIMAP")
    return [r[1] for r in result]


def prepare():
    source_dir = ROOT / "data/interim/sentinel1"
    target_dir = ROOT / "data/processed/sentinel1"
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = ROOT / "docs/acquisition/sentinel1_alignment_report.json"
    paths = [source_dir / f"S1A_{date}_TC_linear.tif" for date in DATES]
    labels = [band_metadata(source_dir / f"S1A_{date}_Orb_TNR_Cal_Spk_TC.dim") for date in DATES]
    outputs = [target_dir / f"lagos_{date}_sigma0_linear.tif" for date in DATES]
    common_path = target_dir / "lagos_pair_valid_mask.tif"
    if any(p.exists() for p in outputs + [common_path]):
        raise FileExistsError("Prepared outputs already exist; preserve/review them before rerunning")
    partials = [p.with_suffix(".part.tif") for p in outputs + [common_path]]
    state = gpd.read_file(ROOT / "data/interim/boundaries/lagos_state.geojson")
    counts = {"aoi_pixels": 0, "common_valid_pixels": 0,
              "valid_pixels_both_bands_per_date": [0, 0],
              "nonpositive_valid_values_per_date_band": [[0, 0], [0, 0]]}
    stats = [[{"min": float("inf"), "max": float("-inf")} for _ in range(2)] for _ in DATES]
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(p)) for p in paths]
        ref = sources[0]
        for s in sources:
            if s.crs != rasterio.crs.CRS.from_epsg(32631) or s.count != 2 or s.dtypes != ("float32", "float32"):
                raise ValueError("Expected two-band Float32 EPSG:32631 exports")
            if not np.allclose(s.res, (10, 10), atol=1e-7, rtol=0):
                raise ValueError("Expected 10 metre spacing")
            if abs(s.transform.b) > 1e-10 or abs(s.transform.d) > 1e-10:
                raise ValueError("Rotated grids require explicit review")
        state = state.to_crs(ref.crs)
        geometries = list(state.geometry)
        window = aligned_window(state.total_bounds, ref.transform)
        transform = ref.window_transform(window)
        width, height = int(window.width), int(window.height)
        profile = dict(driver="GTiff", width=width, height=height, count=2,
                       dtype="float32", crs=ref.crs, transform=transform, nodata=NODATA,
                       tiled=True, blockxsize=512, blockysize=512, compress="deflate",
                       predictor=3, BIGTIFF="IF_SAFER")
        readers = [stack.enter_context(WarpedVRT(s, crs=ref.crs, transform=transform,
                   width=width, height=height, src_nodata=0, nodata=NODATA,
                   resampling=Resampling.nearest if i == 0 else Resampling.bilinear,
                   dtype="float32", warp_mem_limit=128)) for i, s in enumerate(sources)]
        writers = [stack.enter_context(rasterio.open(p, "w", **profile)) for p in partials[:2]]
        mask_profile = dict(profile, count=1, dtype="uint8", nodata=255, predictor=1)
        mask_writer = stack.enter_context(rasterio.open(partials[2], "w", **mask_profile))
        mask_writer.set_band_description(1, "1=both dates/bands valid; 0=missing data; 255=outside Lagos")
        for i, writer in enumerate(writers):
            for b, label in enumerate(labels[i], 1):
                writer.set_band_description(b, label)
            writer.update_tags(source=str(paths[i].relative_to(ROOT)), units="linear sigma0",
                               source_nodata="0, confirmed from matching SNAP DIMAP",
                               resampling="nearest (reference grid)" if i == 0 else "bilinear",
                               reference_grid=DATES[0], aoi_mask="pixel center in Lagos state")
        print(f"Preparing {width} x {height} common grid in EPSG:32631", flush=True)
        block_count = 0
        for _, block in writers[0].block_windows(1):
            shape = (int(block.height), int(block.width))
            inside = geometry_mask(geometries, out_shape=shape,
                       transform=writers[0].window_transform(block), invert=True)
            counts["aoi_pixels"] += int(inside.sum())
            valid_dates = []
            for i, reader in enumerate(readers):
                values = reader.read(window=block)
                valid = np.isfinite(values) & (values != NODATA) & inside[np.newaxis, :, :]
                valid_dates.append(valid.all(axis=0))
                counts["valid_pixels_both_bands_per_date"][i] += int(valid_dates[-1].sum())
                for b in range(2):
                    v = values[b][valid[b]]
                    if v.size:
                        stats[i][b]["min"] = min(stats[i][b]["min"], float(v.min()))
                        stats[i][b]["max"] = max(stats[i][b]["max"], float(v.max()))
                        counts["nonpositive_valid_values_per_date_band"][i][b] += int((v <= 0).sum())
                values[~valid] = NODATA
                writers[i].write(values, window=block)
            common = valid_dates[0] & valid_dates[1]
            counts["common_valid_pixels"] += int(common.sum())
            mask_writer.write(np.where(inside, common.astype("uint8"), 255).astype("uint8"), 1, window=block)
            block_count += 1
            if block_count % 50 == 0:
                print(f"Processed {block_count} blocks", flush=True)
        grid = dict(crs=str(ref.crs), transform=list(transform), width=width, height=height,
                    reference_window=list(window.flatten()), nodata=NODATA)
        source_grids = [dict(path=p.relative_to(ROOT).as_posix(), crs=str(s.crs),
                            transform=list(s.transform), nodata=s.nodata, bands=labels[i])
                        for i, (p, s) in enumerate(zip(paths, sources))]
    if counts["common_valid_pixels"] == 0:
        raise ValueError("No common valid Lagos coverage")
    # Check actual serialized grids and a reference-grid sample before promoting outputs.
    with ExitStack() as stack:
        prepared = [stack.enter_context(rasterio.open(p)) for p in partials]
        first = prepared[0]
        for dataset in prepared[1:]:
            if (dataset.crs, dataset.transform, dataset.width, dataset.height) != (first.crs, first.transform, first.width, first.height):
                raise ValueError("Prepared grids differ")
        with rasterio.open(paths[0]) as original:
            for _, block in first.block_windows(1):
                data = first.read(window=block)
                valid = data != NODATA
                if valid.any():
                    source_window = Window(window.col_off + block.col_off, window.row_off + block.row_off, block.width, block.height)
                    reference = original.read(window=source_window, boundless=True, fill_value=0)
                    if not np.allclose(data[valid], reference[valid], atol=1e-7, rtol=1e-6):
                        raise ValueError("Reference-grid sample changed unexpectedly")
                    break
    for partial, target in zip(partials, outputs + [common_path]):
        partial.replace(target)
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), source_grids=source_grids,
                  target_grid=grid, band_statistics=stats, counts=counts,
                  common_valid_aoi_fraction=counts["common_valid_pixels"]/counts["aoi_pixels"],
                  checks={"identical_output_grids": True, "reference_sample_preserved": True},
                  notes=["Original exports unchanged; source zero interpreted as nodata using SNAP metadata.",
                         "July 3 bilinearly resampled once onto the June 21 grid; June 21 pixel positions retained.",
                         "Individual rasters retain their own validity; use the common mask for pair comparisons.",
                         "Negative/zero valid values retained after resampling; mask nonpositive values before dB conversion.",
                         "No flood classification or subpixel geolocation validation performed."])
    manifest_path = ROOT / "docs/acquisition/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for p in outputs + [common_path]:
        manifest[p.relative_to(ROOT).as_posix()] = dict(
            source=[s["path"] for s in source_grids], created_utc=report["created_utc"],
            bytes=p.stat().st_size, sha256=sha256(p), crs=grid["crs"],
            processing="Shared June 21 grid, nodata-aware resampling and Lagos polygon mask; see alignment report")
    save_json(manifest_path, manifest)
    save_json(report_path, report)
    print(json.dumps({"counts": counts, "common_valid_aoi_fraction": report["common_valid_aoi_fraction"],
                      "outputs": [str(p.relative_to(ROOT)) for p in outputs + [common_path]]}, indent=2), flush=True)


if __name__ == "__main__":
    prepare()
