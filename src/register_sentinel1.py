"""Verify and register manually downloaded Sentinel-1 archives without extracting them."""
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "docs/acquisition"


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    pair = json.loads((META / "sentinel1_selected_pair.json").read_text())
    features = json.loads((META / "sentinel1_search.geojson").read_text())["features"]
    catalog = {f["properties"]["sceneName"]: f["properties"] for f in features}
    manifest = json.loads((META / "manifest.json").read_text())
    pending = {}
    results = []
    for role in ("before", "after"):
        scene = pair[role]
        expected = catalog[scene]
        path = ROOT / "data/raw/sentinel1" / (scene + ".zip")
        print("Checking " + path.name, flush=True)
        if path.stat().st_size != expected["bytes"]:
            raise RuntimeError("Archive size differs from ASF catalog: " + scene)
        md5, sha = hashlib.md5(), hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                md5.update(block)
                sha.update(block)
        if md5.hexdigest() != expected["md5sum"]:
            raise RuntimeError("Archive MD5 differs from ASF catalog: " + scene)
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError("ZIP CRC failed: " + bad)
            names = archive.namelist()
            safe = [n for n in names if n.endswith("/manifest.safe")]
            if len(safe) != 1:
                raise RuntimeError("Expected one SAFE manifest")
            tree = ET.fromstring(archive.read(safe[0]))
            fields = {}
            keys = {"startTime", "stopTime", "orbitNumber", "relativeOrbitNumber",
                    "pass", "mode", "transmitterReceiverPolarisation"}
            for element in tree.iter():
                name = element.tag.rsplit("}", 1)[-1]
                if name in keys and element.text:
                    fields.setdefault(name, []).append(element.text.strip())
            if str(expected["pathNumber"]) not in fields.get("relativeOrbitNumber", []):
                raise RuntimeError("SAFE relative orbit differs from catalog")
            if expected["flightDirection"] not in fields.get("pass", []):
                raise RuntimeError("SAFE pass differs from catalog")
            if not any(t[:19] == expected["startTime"][:19] for t in fields.get("startTime", [])):
                raise RuntimeError("SAFE acquisition time differs from catalog")
            if "IW" not in fields.get("mode", []):
                raise RuntimeError("SAFE mode is not IW")
            if not {"VV", "VH"}.issubset(fields.get("transmitterReceiverPolarisation", [])):
                raise RuntimeError("SAFE does not contain both VV and VH")
            components = {}
            for pol in ("vv", "vh"):
                components[pol] = {
                    "measurement": [n for n in names if "/measurement/" in n and "-" + pol + "-" in n and n.endswith(".tiff")],
                    "annotation": [n for n in names if "/annotation/" in n and "/calibration/" not in n and "-" + pol + "-" in n and n.endswith(".xml")],
                    "calibration": [n for n in names if "/calibration/calibration-" in n and "-" + pol + "-" in n],
                    "noise": [n for n in names if "/calibration/noise-" in n and "-" + pol + "-" in n],
                }
                if any(not items for items in components[pol].values()):
                    raise RuntimeError("Missing SAFE components for " + pol)
        verified = datetime.now(timezone.utc).isoformat()
        key = path.relative_to(ROOT).as_posix()
        pending[key] = dict(source=expected["url"], bytes=path.stat().st_size,
                            sha256=sha.hexdigest(), md5=md5.hexdigest(), expected_md5=expected["md5sum"],
                            verified_utc=verified, retrieval_method="Manual browser download; exact retrieval time not recorded",
                            processing="No extraction or preprocessing; provider size/MD5, ZIP CRC, SAFE metadata and component checks passed",
                            acquisition_utc=expected["startTime"], relative_orbit=expected["pathNumber"],
                            license="Copernicus Sentinel data terms")
        iso = path.with_suffix(".iso.xml")
        if iso.exists():
            ET.parse(iso)
            pending[iso.relative_to(ROOT).as_posix()] = dict(
                source="User-supplied ASF ISO metadata accompanying " + scene,
                bytes=iso.stat().st_size, sha256=hashlib.sha256(iso.read_bytes()).hexdigest(),
                verified_utc=verified, processing="XML well-formedness checked; no provider checksum available")
        results.append(dict(scene_id=scene, role=role, bytes=path.stat().st_size,
                            md5=md5.hexdigest(), sha256=sha.hexdigest(), zip_crc="passed",
                            safe_metadata=fields, components=components))
        print("Passed: provider size/MD5, ZIP CRC, SAFE metadata, VV/VH components", flush=True)
    manifest.update(pending)
    save(META / "manifest.json", manifest)
    save(META / "sentinel1_download_verification.json",
         dict(verified_utc=datetime.now(timezone.utc).isoformat(), results=results,
              status="Both selected archives verified; scientific suitability remains to be assessed"))
    print("Registered both archives and available ISO metadata.", flush=True)


if __name__ == "__main__":
    main()
