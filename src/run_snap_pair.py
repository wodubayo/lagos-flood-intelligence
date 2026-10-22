from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GPT = Path(r"C:\Program Files\esa-snap\bin\gpt.exe")
INTERMEDIATE_GRAPH = ROOT / "graphs/sentinel1_preprocess_intermediates.xml"
TC_GRAPH = ROOT / "graphs/sentinel1_terrain_correction_only.xml"
BANDS = ("Sigma0_VH", "Sigma0_VV")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def named_child(parent: ET.Element, tag: str, name: str) -> ET.Element | None:
    return next(
        (item for item in list(parent)
         if local_name(item.tag) == tag and item.get("name") == name),
        None,
    )


def dataset_abstracted_metadata(root: ET.Element) -> ET.Element:
    dataset_sources = next(
        (node for node in root.iter() if local_name(node.tag) == "Dataset_Sources"),
        None,
    )
    if dataset_sources is None:
        raise ValueError("DIMAP has no Dataset_Sources element")
    metadata = named_child(dataset_sources, "MDElem", "metadata")
    abstracted = named_child(metadata, "MDElem", "Abstracted_Metadata") if metadata is not None else None
    if abstracted is None:
        raise ValueError("DIMAP has no Dataset_Sources Abstracted_Metadata")
    return abstracted


def restore_precise_orbit_metadata(orbit_dim: Path, speckle_dim: Path) -> tuple[Path, dict[str, Any]]:
    orbit_tree = ET.parse(orbit_dim)
    speckle_tree = ET.parse(speckle_dim)
    orbit_metadata = dataset_abstracted_metadata(orbit_tree.getroot())
    speckle_metadata = dataset_abstracted_metadata(speckle_tree.getroot())

    orbit_vectors = named_child(orbit_metadata, "MDElem", "Orbit_State_Vectors")
    speckle_vectors = named_child(speckle_metadata, "MDElem", "Orbit_State_Vectors")
    orbit_file = named_child(orbit_metadata, "MDATTR", "orbit_state_vector_file")
    speckle_file = named_child(speckle_metadata, "MDATTR", "orbit_state_vector_file")
    if any(node is None for node in (orbit_vectors, speckle_vectors, orbit_file, speckle_file)):
        raise ValueError("DIMAP is missing orbit provenance or orbit-vector metadata")

    vector_times = [
        next((child.text for child in vector if local_name(child.tag) == "MDATTR" and child.get("name") == "time"), None)
        for vector in list(orbit_vectors)
        if local_name(vector.tag) == "MDElem"
    ]
    vector_times = [value for value in vector_times if value]
    if not vector_times:
        raise ValueError("Orbit checkpoint contains no timestamped orbit vectors")
    if not orbit_file.text or "Sentinel Precise" not in orbit_file.text:
        raise ValueError(f"Orbit checkpoint is not marked as precise: {orbit_file.text!r}")

    parent = speckle_metadata
    index = next(i for i, child in enumerate(list(parent)) if local_name(child.tag) == "MDElem" and child.get("name") == "Orbit_State_Vectors")
    parent.remove(speckle_vectors)
    parent.insert(index, copy.deepcopy(orbit_vectors))
    speckle_file.text = orbit_file.text

    fixed_dim = speckle_dim.with_name(f"{speckle_dim.stem}_orbit_metadata_fixed{speckle_dim.suffix}")
    speckle_tree.write(fixed_dim, encoding="UTF-8", xml_declaration=True)
    return fixed_dim, {
        "source_orbit_file": orbit_file.text.strip(),
        "orbit_vector_count": len(vector_times),
        "first_vector_time": vector_times[0],
        "last_vector_time": vector_times[-1],
        "fixed_dim": str(fixed_dim.relative_to(ROOT)),
    }


def run_gpt(command: list[str], cwd: Path, log_path: Path, label: str) -> float:
    print(f"[{label}] starting; log: {log_path.relative_to(ROOT)}", flush=True)
    started = time.monotonic()
    offset = 0
    last_percent = None
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            time.sleep(2)
            try:
                with log_path.open("r", encoding="utf-8", errors="replace") as reader:
                    reader.seek(offset)
                    chunk = reader.read()
                    offset = reader.tell()
                percentages = re.findall(r"(\d{1,3})%", chunk)
                if percentages and percentages[-1] != last_percent:
                    last_percent = percentages[-1]
                    print(f"[{label}] SNAP progress {last_percent}%", flush=True)
            except OSError:
                pass
    elapsed = time.monotonic() - started
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)
    if not log_path.is_file() or log_path.stat().st_size == 0:
        raise RuntimeError(f"SNAP produced an empty log for {label}")
    print(f"[{label}] completed in {elapsed / 60:.1f} min", flush=True)
    return elapsed


def compare_to_manual(generated_dim: Path, manual_dim: Path) -> dict[str, Any]:
    import numpy as np
    from osgeo import gdal, osr

    result: dict[str, Any] = {"manual_product": str(manual_dim.relative_to(ROOT)), "bands": {}}
    for band_name in BANDS:
        generated_path = generated_dim.with_suffix(".data") / f"{band_name}.img"
        manual_path = manual_dim.with_suffix(".data") / f"{band_name}.img"
        actual = gdal.Open(str(generated_path), gdal.GA_ReadOnly)
        expected = gdal.Open(str(manual_path), gdal.GA_ReadOnly)
        if actual is None or expected is None:
            raise RuntimeError(f"Unable to open comparison input for {band_name}")
        actual_srs, expected_srs = osr.SpatialReference(), osr.SpatialReference()
        actual_srs.ImportFromWkt(actual.GetProjection())
        expected_srs.ImportFromWkt(expected.GetProjection())
        same_grid = (
            actual.RasterXSize == expected.RasterXSize
            and actual.RasterYSize == expected.RasterYSize
            and actual_srs.IsSame(expected_srs)
            and np.allclose(actual.GetGeoTransform(), expected.GetGeoTransform(), rtol=0, atol=1e-8)
        )
        if not same_grid:
            raise RuntimeError(f"Output grid differs from manual product for {band_name}")
        stats: dict[str, Any] = {
            "pixels": actual.RasterXSize * actual.RasterYSize,
            "exact_different_pixels": 0,
            "zero_mask_differences": 0,
            "outside_tolerance_pixels": 0,
            "max_absolute_difference": 0.0,
            "mean_absolute_difference": 0.0,
            "grid_equal_semantically": True,
        }
        total_abs = 0.0
        finite_count = 0
        for row in range(0, actual.RasterYSize, 256):
            height = min(256, actual.RasterYSize - row)
            got = actual.GetRasterBand(1).ReadAsArray(0, row, actual.RasterXSize, height)
            ref = expected.GetRasterBand(1).ReadAsArray(0, row, expected.RasterXSize, height)
            finite = np.isfinite(got) & np.isfinite(ref)
            diff = np.abs(got.astype("float64") - ref.astype("float64"))
            stats["exact_different_pixels"] += int(np.count_nonzero(~((got == ref) | (np.isnan(got) & np.isnan(ref)))))
            stats["zero_mask_differences"] += int(np.count_nonzero((got == 0) != (ref == 0)))
            stats["outside_tolerance_pixels"] += int(np.count_nonzero(~np.isclose(got, ref, rtol=1e-5, atol=1e-7, equal_nan=True)))
            if finite.any():
                valid_diff = diff[finite]
                total_abs += float(valid_diff.sum())
                finite_count += int(finite.sum())
                stats["max_absolute_difference"] = max(stats["max_absolute_difference"], float(valid_diff.max()))
        stats["mean_absolute_difference"] = total_abs / finite_count if finite_count else None
        result["bands"][band_name] = stats
        print(
            f"[compare {band_name}] exact differences={stats['exact_different_pixels']:,}; "
            f"outside tolerance={stats['outside_tolerance_pixels']:,}; "
            f"max abs difference={stats['max_absolute_difference']:.8g}",
            flush=True,
        )
        actual = expected = None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the two-scene SNAP pair with precise-orbit metadata preserved before terrain correction.")
    parser.add_argument("--run-id", default="graph_trial_05_orbit_metadata_fix")
    parser.add_argument("--gpt", type=Path, default=DEFAULT_GPT)
    parser.add_argument("--resume", action="store_true", help="resume an existing run directory")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("--run-id may contain only letters, digits, underscores, and hyphens")
    if not args.gpt.is_file() or not INTERMEDIATE_GRAPH.is_file() or not TC_GRAPH.is_file():
        raise FileNotFoundError("Check the SNAP GPT executable and both saved graph XML files.")

    jobs = []
    for date in ("20240621", "20240703"):
        matches = list((ROOT / "data/raw/sentinel1").glob(f"S1A_IW_GRDH_1SDV_{date}T*.zip"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one raw ZIP for {date}; found {len(matches)}")
        jobs.append((date, matches[0]))

    run = ROOT / "outputs/snap_runs" / args.run_id
    report_path = run / "run_report.json"
    if run.exists():
        if not args.resume:
            raise FileExistsError(f"Run directory already exists: {run}; choose a new --run-id or pass --resume")
        if not report_path.is_file():
            raise FileNotFoundError(f"Cannot resume without run report: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        if report.get("run_id") != args.run_id:
            raise ValueError("Existing run report id does not match --run-id")
        report["previous_error"] = report.pop("error", None)
        report["resumed_utc"] = datetime.now(timezone.utc).isoformat()
        report["status"] = "running"
    else:
        run.mkdir(parents=True, exist_ok=False)
        report = {
            "run_id": args.run_id,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "snap_gpt": str(args.gpt),
            "intermediate_graph": str(INTERMEDIATE_GRAPH.relative_to(ROOT)),
            "terrain_correction_graph": str(TC_GRAPH.relative_to(ROOT)),
            "dates": {},
        }

    def save_report() -> None:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save_report()
    try:
        for date, source in jobs:
            print(f"\n=== {date}: {source.name} ===", flush=True)
            date_record: dict[str, Any] = report["dates"].setdefault(date, {"source_zip": str(source.relative_to(ROOT)), "stages": {}})
            date_record["status"] = "running"
            date_record.setdefault("stages", {})
            save_report()
            orbit_dim = run / f"S1A_{date}_Orb.dim"
            spk_dim = run / f"S1A_{date}_Orb_TNR_Cal_Spk.dim"
            intermediates_exist = all(path.is_file() and path.with_suffix(".data").is_dir() for path in (orbit_dim, spk_dim))
            if intermediates_exist:
                if "intermediates" not in date_record["stages"]:
                    date_record["stages"]["intermediates"] = {"status": "recovered_existing_outputs", "log": f"{date}_intermediates.log"}
                print(f"[{date}] reusing completed Orbit and Refined Lee products", flush=True)
            else:
                command = [
                    str(args.gpt), str(INTERMEDIATE_GRAPH),
                    f"-Pinput={source}",
                    f"-PstageOrbit={orbit_dim}",
                    f"-PstageSpk={spk_dim}",
                    "-q", "4", "-c", "1G",
                ]
                elapsed = run_gpt(command, ROOT, run / f"{date}_intermediates.log", f"{date} intermediates")
                date_record["stages"]["intermediates"] = {"status": "passed", "minutes": round(elapsed / 60, 2), "log": f"{date}_intermediates.log"}
            if not orbit_dim.is_file() or not orbit_dim.with_suffix(".data").is_dir() or not spk_dim.is_file() or not spk_dim.with_suffix(".data").is_dir():
                raise RuntimeError(f"Expected SNAP intermediate missing for {date}")
            save_report()

            fixed_dim, orbit_info = restore_precise_orbit_metadata(orbit_dim, spk_dim)
            date_record["orbit_metadata_restore"] = orbit_info
            date_record["stages"]["orbit_metadata_restore"] = {"status": "passed"}
            save_report()
            tc_dim = run / f"S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
            tc_command = [
                str(args.gpt), str(TC_GRAPH),
                f"-Pinput={fixed_dim}",
                f"-Poutput={tc_dim}",
                "-q", "4", "-c", "1G",
            ]
            elapsed = run_gpt(tc_command, ROOT, run / f"{date}_terrain_correction.log", f"{date} terrain correction")
            date_record["stages"]["terrain_correction"] = {"status": "passed", "minutes": round(elapsed / 60, 2), "log": f"{date}_terrain_correction.log"}
            if not tc_dim.is_file() or not tc_dim.with_suffix(".data").is_dir():
                raise RuntimeError(f"Expected TC output missing: {tc_dim}")

            manual_dim = ROOT / f"data/interim/sentinel1/S1A_{date}_Orb_TNR_Cal_Spk_TC.dim"
            if manual_dim.is_file():
                date_record["manual_comparison"] = compare_to_manual(tc_dim, manual_dim)
            else:
                date_record["manual_comparison"] = {"status": "skipped", "reason": f"Manual product not found: {manual_dim.relative_to(ROOT)}"}
            date_record["status"] = "passed"
            date_record["output_dim"] = str(tc_dim.relative_to(ROOT))
            save_report()
            print(f"=== {date}: complete ===", flush=True)

        report["status"] = "passed"
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_report()
        print(f"\nBoth scenes finished. Run report: {report_path.relative_to(ROOT)}", flush=True)
        return 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_report()
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SNAP pair run failed: {exc}", file=sys.stderr, flush=True)
        raise


