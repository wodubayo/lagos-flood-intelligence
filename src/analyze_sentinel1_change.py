"""Coverage diagnostics and common-positive-pixel dB change for LAG_2024_07."""
import json
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from prepare_sentinel1_pair import ROOT, NODATA, save_json, sha256


def db_change(before, after, common_mask):
    """Use one valid support for both dates AND both polarizations."""
    support = (common_mask == 1) & np.all(
        np.isfinite(before) & np.isfinite(after) &
        (before != NODATA) & (after != NODATA) &
        (before > 0) & (after > 0), axis=0)
    b = np.full(before.shape, NODATA, dtype="float32")
    a = np.full(after.shape, NODATA, dtype="float32")
    change = np.full(before.shape, NODATA, dtype="float32")
    b[:, support] = 10 * np.log10(before[:, support].astype("float64"))
    a[:, support] = 10 * np.log10(after[:, support].astype("float64"))
    change[:, support] = a[:, support] - b[:, support]
    return b, a, change, support


def main():
    folder = ROOT / "data/processed/sentinel1"
    sources = [folder / f"lagos_{date}_sigma0_linear.tif" for date in ("20240621", "20240703")]
    mask_path = folder / "lagos_pair_valid_mask.tif"
    occurrence_path = ROOT / "data/interim/water/lagos_jrc_occurrence_1984_2021.tif"
    footprint_path = ROOT / "data/interim/boundaries/sentinel1_pair_coverage.geojson"
    targets = [folder / name for name in (
        "lagos_20240621_sigma0_db.tif", "lagos_20240703_sigma0_db.tif",
        "lagos_delta_sigma0_db.tif", "lagos_pair_positive_mask.tif",
        "lagos_coverage_diagnostic.tif")]
    if any(p.exists() for p in targets):
        raise FileExistsError("Outputs already exist; preserve or relocate before rerunning")
    manifest_path = ROOT / "docs/acquisition/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for p in sources + [mask_path, occurrence_path, footprint_path]:
        entry = manifest[p.relative_to(ROOT).as_posix()]
        if sha256(p) != entry["sha256"]:
            raise ValueError("Input checksum mismatch: " + str(p))
    footprints = gpd.read_file(footprint_path)
    counts = {"aoi": 0, "common_valid": 0, "common_positive": 0, "excluded_nonpositive": 0}
    # Counts partition the AOI. Category 4 diagnoses vector/raster footprint disagreement.
    classes = {i: {"pixels": 0, "jrc_ge90": 0, "jrc_lt90": 0, "jrc_unknown": 0} for i in (1, 2, 3, 4)}
    moments = [{"count": 0, "sum": 0., "sum_sq": 0., "min": float("inf"), "max": float("-inf"),
                "histogram_minus30_to30_step0_5": [0]*120, "below_minus30": 0, "above30": 0} for _ in range(2)]
    partials = [p.with_suffix(".part.tif") for p in targets]
    with ExitStack() as stack:
        before, after = [stack.enter_context(rasterio.open(p)) for p in sources]
        masks = stack.enter_context(rasterio.open(mask_path))
        for d in (after, masks):
            if (d.crs, d.transform, d.shape) != (before.crs, before.transform, before.shape):
                raise ValueError("Input grids differ")
        if before.descriptions != ("Sigma0_VH", "Sigma0_VV") or after.descriptions != before.descriptions:
            raise ValueError("Unexpected band order")
        footprint = list(footprints.to_crs(before.crs).query("region == 'pair_coverage'").geometry)
        water_src = stack.enter_context(rasterio.open(occurrence_path))
        water = stack.enter_context(WarpedVRT(water_src, crs=before.crs, transform=before.transform,
                    width=before.width, height=before.height, resampling=Resampling.nearest,
                    src_nodata=water_src.nodata, nodata=255))
        profile = before.profile.copy()
        profile.update(compress="deflate", predictor=3, BIGTIFF="IF_SAFER")
        db_writers = [stack.enter_context(rasterio.open(p, "w", **profile)) for p in partials[:3]]
        profile.update(count=1, dtype="uint8", nodata=255, predictor=1)
        valid_writer, coverage_writer = [stack.enter_context(rasterio.open(p, "w", **profile)) for p in partials[3:]]
        for i, writer in enumerate(db_writers):
            for b, pol in enumerate(("VH", "VV"), 1):
                writer.set_band_description(b, ("Delta_Sigma0_" if i == 2 else "Sigma0_") + pol + "_dB")
            writer.update_tags(units="dB", formula="after_dB - before_dB" if i == 2 else "10*log10(linear Sigma0)",
                               support="both dates and both polarizations finite and strictly positive",
                               classification="None; continuous radar measurements, not a flood map")
        valid_writer.set_band_description(1, "1=all four values positive/valid; 0=excluded; 255=outside AOI")
        coverage_writer.set_band_description(1, "1=common valid inside footprint;2=missing inside;3=missing outside;4=valid outside;255=outside AOI")
        for number, (_, block) in enumerate(before.block_windows(1), 1):
            bv, av, mask = before.read(window=block), after.read(window=block), masks.read(1, window=block)
            db_b, db_a, delta, good = db_change(bv, av, mask)
            inside = mask != 255
            for writer, array in zip(db_writers, (db_b, db_a, delta)):
                writer.write(array, window=block)
            valid_writer.write(np.where(inside, good, 255).astype("uint8"), 1, window=block)
            fp = geometry_mask(footprint, out_shape=mask.shape,
                               transform=before.window_transform(block), invert=True)
            codes = np.full(mask.shape, 255, dtype="uint8")
            codes[inside & (mask == 1) & fp] = 1
            codes[inside & (mask == 0) & fp] = 2
            codes[inside & (mask == 0) & ~fp] = 3
            codes[inside & (mask == 1) & ~fp] = 4
            coverage_writer.write(codes, 1, window=block)
            w = water.read(1, window=block)
            known = (w >= 0) & (w <= 100)
            for category in classes:
                select = codes == category
                classes[category]["pixels"] += int(select.sum())
                classes[category]["jrc_ge90"] += int((select & known & (w >= 90)).sum())
                classes[category]["jrc_lt90"] += int((select & known & (w < 90)).sum())
                classes[category]["jrc_unknown"] += int((select & ~known).sum())
            counts["aoi"] += int(inside.sum())
            counts["common_valid"] += int((mask == 1).sum())
            counts["common_positive"] += int(good.sum())
            counts["excluded_nonpositive"] += int(((mask == 1) & ~good).sum())
            for b in range(2):
                v = delta[b][good].astype("float64")
                if not v.size:
                    continue
                m = moments[b]
                m["count"] += int(v.size)
                m["sum"] += float(v.sum())
                m["sum_sq"] += float(np.dot(v, v))
                m["min"], m["max"] = min(m["min"], float(v.min())), max(m["max"], float(v.max()))
                hist, _ = np.histogram(v, bins=np.linspace(-30, 30, 121))
                m["histogram_minus30_to30_step0_5"] = (np.array(m["histogram_minus30_to30_step0_5"]) + hist).tolist()
                m["below_minus30"] += int((v < -30).sum())
                m["above30"] += int((v > 30).sum())
            if number % 60 == 0:
                print(f"Processed {number} blocks", flush=True)
    if counts["common_positive"] == 0:
        raise ValueError("No positive comparison pixels")
    for partial, target in zip(partials, targets):
        partial.replace(target)
    for m in moments:
        m["mean"] = m["sum"] / m["count"]
        m["std"] = max(0, m["sum_sq"]/m["count"] - m["mean"]**2)**0.5
    assert sum(c["pixels"] for c in classes.values()) == counts["aoi"]
    for c in classes.values():
        assert c["jrc_ge90"] + c["jrc_lt90"] + c["jrc_unknown"] == c["pixels"]
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), counts=counts, coverage_categories=classes,
        common_positive_aoi_fraction=counts["common_positive"]/counts["aoi"],
        delta_band_order=["VH", "VV"], delta_statistics=moments,
        coverage_labels={"1":"common valid inside catalog footprint","2":"missing inside catalog footprint",
                         "3":"missing outside catalog footprint","4":"common valid outside catalog footprint"},
        interpretation=["JRC >=90% occurrence is only a descriptive diagnostic, not an applied permanent-water mask.",
                        "Rasterized catalog footprint uses pixel centers; differs slightly from vector area coverage.",
                        "Overlap with historical water does not establish why data were masked.",
                        "Positive delta means increased backscatter; negative means decreased backscatter.",
                        "No threshold, water removal, terrain filter, flood classification or independent validation yet."])
    save_json(ROOT / "docs/acquisition/sentinel1_change_report.json", report)
    for p in targets:
        manifest[p.relative_to(ROOT).as_posix()] = dict(
            source=[str(s.relative_to(ROOT)).replace("\\", "/") for s in sources + [mask_path, occurrence_path, footprint_path]],
            created_utc=report["created_utc"], sha256=sha256(p), bytes=p.stat().st_size,
            processing="Coverage diagnostic or common-positive linear-to-dB/change; see sentinel1_change_report.json",
            crs="EPSG:32631")
    save_json(manifest_path, manifest)
    print(json.dumps({"counts":counts, "coverage_categories":classes,
                      "delta_means": [m["mean"] for m in moments]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
