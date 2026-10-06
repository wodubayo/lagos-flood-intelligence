"""Reproducible Phase 1 acquisition for LAG_2024_07 (run from project root)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import geopandas as gpd
import numpy as np
import requests
import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.windows import from_bounds, Window
from shapely.geometry import box, mapping, shape
from shapely.ops import transform
from pyproj import Transformer
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
INTERIM = ROOT / 'data/interim'
META = ROOT / 'docs/acquisition'
SESSION = requests.Session()
SESSION.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
SESSION.headers['User-Agent'] = 'lagos-flood-intelligence/phase1'
EVENT_START = datetime.fromisoformat('2024-07-03T00:00:00+01:00')
EVENT_END = datetime.fromisoformat('2024-07-05T00:00:00+01:00')


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def record(path, source, **metadata):
    manifest_path = META / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    key = path.relative_to(ROOT).as_posix()
    manifest[key] = dict(source=source, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                         bytes=path.stat().st_size, sha256=checksum(path), **metadata)
    save_json(manifest_path, manifest)


def download(url, path, **metadata):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        manifest_path = META / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        previous = manifest.get(path.relative_to(ROOT).as_posix())
        if previous and previous['source'] == url and previous['sha256'] == checksum(path):
            print(f'Cached {path.name}', flush=True)
            return path
        raise RuntimeError(f'Unverified existing file: {path}; move aside before retrying')
    print(f'Downloading {path.name}', flush=True)
    tmp = path.with_suffix(path.suffix + '.part')
    with SESSION.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        with tmp.open('wb') as stream:
            for chunk in response.iter_content(1024 * 1024):
                stream.write(chunk)
    if tmp.stat().st_size == 0:
        raise RuntimeError(f'Empty download: {url}')
    if metadata.get('expected_bytes') is not None and tmp.stat().st_size != metadata['expected_bytes']:
        raise RuntimeError(f'Download size mismatch: {path.name}')
    if metadata.get('expected_md5'):
        h = hashlib.md5()
        with tmp.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        if h.hexdigest() != metadata['expected_md5']:
            raise RuntimeError(f'Download checksum mismatch: {path.name}')
    tmp.replace(path)
    record(path, url, **metadata)
    return path


def aoi():
    return gpd.read_file(INTERIM / 'boundaries/lagos_state.geojson').to_crs(4326)


def boundaries():
    frames = {}
    for level in ('ADM0', 'ADM1', 'ADM2'):
        meta_path = META / f'geoboundaries_NGA_{level}.json'
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text())
        else:
            response = SESSION.get(f'https://www.geoboundaries.org/api/current/gbOpen/NGA/{level}/', timeout=60)
            response.raise_for_status()
            metadata = response.json()
            save_json(meta_path, metadata)
        # geoBoundaries returns commit-pinned URLs, retained for reproducibility.
        url = metadata['gjDownloadURL'].replace('https://github.com/', 'https://media.githubusercontent.com/media/').replace('/raw/', '/')
        existing = RAW / f'boundaries/NGA_{level}.geojson'
        if existing.exists() and existing.read_bytes()[:42].startswith(b'version https://git-lfs.github.com/spec/v1'):
            existing.replace(existing.with_suffix('.lfs-pointer'))
        path = download(url, RAW / f'boundaries/NGA_{level}.geojson',
                        license=metadata['boundaryLicense'], year=metadata['boundaryYearRepresented'], crs='EPSG:4326')
        frames[level] = gpd.read_file(path).to_crs(4326)
    state = frames['ADM1'][frames['ADM1'].shapeName.str.casefold().eq('lagos')].copy()
    if len(state) != 1 or not state.is_valid.all():
        raise RuntimeError('Expected one valid Lagos state geometry')
    # ADM2 has no parent attribute: assign by largest area overlap in local UTM.
    state_utm = state.to_crs(32631).geometry.iloc[0]
    candidates = frames['ADM2'][frames['ADM2'].intersects(state.geometry.iloc[0])].copy()
    projected = candidates.to_crs(32631)
    fractions = projected.intersection(state_utm).area / projected.area
    lgas = candidates[fractions > 0.5].copy()
    if len(lgas) != 20 or not lgas.is_valid.all():
        raise RuntimeError(f'Expected 20 valid Lagos LGAs; found {len(lgas)}')
    out = INTERIM / 'boundaries'
    out.mkdir(parents=True, exist_ok=True)
    for frame, name in ((state, 'lagos_state'), (lgas, 'lagos_lgas')):
        target = out / f'{name}.geojson'
        frame.to_file(target, driver='GeoJSON')
        record(target, 'geoBoundaries NGA gbOpen, see pinned metadata', crs='EPSG:4326',
               processing='State name selection; LGAs assigned by >50% overlap in EPSG:32631')
    save_json(META / 'aoi_summary.json', dict(bbox=state.total_bounds.tolist(), lga_count=len(lgas),
        lga_names=sorted(lgas.shapeName.tolist()), area_km2=state_utm.area / 1e6,
        lga_union_coverage=float(projected.loc[lgas.index].geometry.union_all().intersection(state_utm).area/state_utm.area),
        analysis_crs='EPSG:32631', source_crs='EPSG:4326'))
    print(f'Acquired Lagos state and {len(lgas)} LGAs; bbox={state.total_bounds}', flush=True)


def event_period(timestamp):
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return 'before' if dt < EVENT_START else ('during' if dt < EVENT_END else 'after')


def rank_pairs(features, geometry):
    project = Transformer.from_crs(4326, 32631, always_xy=True).transform
    area = transform(project, geometry)
    pairs = []
    for before in features:
        b = before['properties']
        if event_period(b['startTime']) != 'before':
            continue
        for after in features:
            a = after['properties']
            if event_period(a['startTime']) == 'before':
                continue
            keys = ('platform', 'pathNumber', 'flightDirection', 'polarization', 'beamModeType', 'processingLevel')
            if any(b.get(k) != a.get(k) for k in keys):
                continue
            overlap = transform(project, shape(before['geometry'])).intersection(transform(project, shape(after['geometry']))).intersection(area)
            coverage = overlap.area / area.area
            if coverage < 0.01:
                continue
            bt = datetime.fromisoformat(b['startTime'].replace('Z', '+00:00'))
            at = datetime.fromisoformat(a['startTime'].replace('Z', '+00:00'))
            pairs.append(dict(before=b['sceneName'], after=a['sceneName'], before_utc=b['startTime'],
                              after_utc=a['startTime'], relative_orbit=a['pathNumber'],
                              pass_direction=a['flightDirection'], frame_before=b.get('frameNumber'),
                              frame_after=a.get('frameNumber'), common_aoi_fraction=coverage,
                              baseline_days=(at-bt).total_seconds()/86400,
                              after_days_from_event_start=(at-EVENT_START).total_seconds()/86400,
                              period=event_period(a['startTime'])))
    # Prefer broad state coverage, then the earliest event observation. Tiny footprint
    # differences must not promote a scene 12 days later over the event-day scene.
    return sorted(pairs, key=lambda p: (p['common_aoi_fraction'] < 0.8,
                                       p['after_days_from_event_start'], p['baseline_days'],
                                       -p['common_aoi_fraction']))


def scenes():
    geometry = aoi().geometry.iloc[0]
    params = dict(platform='Sentinel-1A', processingLevel='GRD_HD', beamMode='IW', polarization='VV+VH',
                  start='2024-06-15T00:00:00Z', end='2024-07-16T00:00:00Z',
                  intersectsWith=geometry.envelope.wkt, output='geojson', maxResults=1000)
    response = SESSION.get('https://api.daac.asf.alaska.edu/services/search/param', params=params, timeout=120)
    response.raise_for_status()
    result = response.json()
    if len(result['features']) >= 1000:
        raise RuntimeError('Search limit reached: narrow or paginate search')
    save_json(META / 'sentinel1_query.json', dict(url=response.url, parameters=params))
    result['features'] = [f for f in result['features'] if shape(f['geometry']).intersection(geometry).area > 0]
    save_json(META / 'sentinel1_search.geojson', result)
    record(META / 'sentinel1_search.geojson', response.url, processing='ASF catalog search; exact AOI intersection filter')
    rows = []
    for feature in result['features']:
        p = feature['properties']
        rows.append(dict(scene_id=p['sceneName'], acquisition_utc=p['startTime'], period=event_period(p['startTime']),
                         absolute_orbit=p['orbit'], relative_orbit=p['pathNumber'], pass_direction=p['flightDirection'],
                         polarization=p['polarization'], product=p['processingLevel'], mode=p['beamModeType'],
                         pixel_spacing_m=10, nominal_resolution_m='20 x 22 (IW GRD high resolution)',
                         bytes=p['bytes'], url=p['url'], md5=p.get('md5sum', '')))
    if not rows:
        raise RuntimeError('No Sentinel-1 scenes intersect Lagos')
    with (META / 'sentinel1_scenes.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r:r['acquisition_utc']))
    pairs = rank_pairs(result['features'], geometry)
    save_json(META / 'sentinel1_pairs.json', pairs)
    if pairs:
        selected = pairs[0]
        lookup = {f['properties']['sceneName']: shape(f['geometry']) for f in result['features']}
        common = lookup[selected['before']].intersection(lookup[selected['after']]).intersection(geometry)
        coverage = gpd.GeoDataFrame({'region': ['pair_coverage', 'not_observed_by_pair']},
                                   geometry=[common, geometry.difference(common)], crs=4326)
        coverage_path = INTERIM / 'boundaries/sentinel1_pair_coverage.geojson'
        coverage.to_file(coverage_path, driver='GeoJSON')
        record(coverage_path, [selected['before'], selected['after']],
               processing='Intersection of catalog footprints and Lagos AOI; not valid-pixel or flood coverage')
        save_json(META / 'sentinel1_selected_pair.json', dict(**selected,
            total_download_bytes=sum(f['properties']['bytes'] for f in result['features'] if f['properties']['sceneName'] in (selected['before'], selected['after'])),
            selection_rule='Coverage >=80% first, then earliest event observation, shortest baseline, largest coverage',
            status='Candidate only; requires acquisition-time evidence and GRD valid-data coverage inspection'))
    print(f'Found {len(rows)} scenes and {len(pairs)} comparable pairs', flush=True)
    for pair in pairs[:5]:
        print(json.dumps(pair), flush=True)


def crop_raster(url, path, **metadata):
    """Save a native-grid AOI crop; preserve source nodata, no reprojection."""
    manifest_path = META / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    old = manifest.get(path.relative_to(ROOT).as_posix())
    if path.exists() and old and old['source'] == url and old['sha256'] == checksum(path):
        print(f'Cached {path.name}', flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Reading AOI window: {url}', flush=True)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif,.cog',
                      GDAL_HTTP_TIMEOUT='120', GDAL_HTTP_MAX_RETRY='3'):
        with rasterio.open(url) as source:
            frame = aoi().to_crs(source.crs)
            fractional = from_bounds(*frame.total_bounds, transform=source.transform)
            left, top = math.floor(fractional.col_off), math.floor(fractional.row_off)
            window = Window(left, top, math.ceil(fractional.col_off + fractional.width)-left,
                            math.ceil(fractional.row_off + fractional.height)-top)
            window = window.intersection(Window(0, 0, source.width, source.height))
            data = source.read(window=window)
            profile = source.profile.copy()
            profile.update(driver='GTiff', height=data.shape[1], width=data.shape[2],
                           transform=source.window_transform(window), compress='deflate', tiled=True,
                           blockxsize=256, blockysize=256)
            profile.pop('photometric', None)
            tmp = path.with_suffix('.part.tif')
            with rasterio.open(tmp, 'w', **profile) as dest:
                dest.write(data)
                dest.update_tags(source_url=url)
            crs, res, nodata = str(source.crs), source.res, source.nodata
    with rasterio.open(tmp) as source:
        clipped, affine = mask(source, frame.geometry, crop=True)
        profile = source.profile.copy()
        profile.update(height=clipped.shape[1], width=clipped.shape[2], transform=affine)
        with rasterio.open(path, 'w', **profile) as dest:
            dest.write(clipped)
            dest.update_tags(source_url=url)
    tmp.unlink()
    record(path, url, crs=crs, resolution=list(res), nodata=nodata, processing='Native-grid AOI crop; no resampling', **metadata)


def terrain():
    west, south, east, north = aoi().total_bounds
    files = []
    for lat in range(math.floor(south), math.ceil(north)):
        for lon in range(math.floor(west), math.ceil(east)):
            tile = f'Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM'
            url = f'https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/{tile}/{tile}.tif'
            files.append(download(url, RAW / f'dem/{tile}.tif',
                                  license='Copernicus DEM license; https://registry.opendata.aws/copernicus-dem/',
                                  epoch='2011-2015 acquisitions, 2021 release', vertical_datum='EGM2008',
                                  crs='EPSG:4326', resolution='1 arc-second'))
    datasets = [rasterio.open(f) for f in files]
    try:
        values, affine = merge(datasets, bounds=(west, south, east, north))
        profile = datasets[0].profile.copy()
        profile.update(height=values.shape[1], width=values.shape[2], transform=affine, compress='deflate')
        path = INTERIM / 'dem/lagos_copernicus_dem30.tif'
        path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(path, 'w', **profile) as dest:
            dest.write(values)
        record(path, [f.relative_to(ROOT).as_posix() for f in files], crs='EPSG:4326',
               vertical_datum='EGM2008', processing='Mosaic cropped to Lagos bounding box; native grid; DSM, not bare-earth DTM')
    finally:
        for dataset in datasets:
            dataset.close()


def water():
    # Pre-event 1984-2021 baseline avoids incorporating the target flood into the water mask.
    for layer in ('occurrence', 'seasonality'):
        url = f'https://storage.googleapis.com/global-surface-water/downloads2021/{layer}/{layer}_0E_10Nv1_4_2021.tif'
        crop_raster(url, INTERIM / f'water/lagos_jrc_{layer}_1984_2021.tif',
                    license='Copernicus free use, attribution EC JRC/Google; Pekel et al. 2016',
                    epoch='1984-2021 occurrence; 2021 seasonality',
                    caveat='JRC reports occurrence/seasonality issues in v1.4; retain for sensitivity analysis, not an unquestioned mask')


def optical():
    params = {'collections': ['sentinel-2-l2a'], 'bbox': aoi().total_bounds.tolist(),
              'datetime': '2024-06-15T00:00:00Z/2024-07-15T23:59:59Z', 'limit': 100}
    url = 'https://earth-search.aws.element84.com/v1/search'
    response = SESSION.post(url, json=params, timeout=120)
    response.raise_for_status()
    result = response.json()
    features = result['features']
    while True:
        nxt = next((link for link in result.get('links', []) if link['rel'] == 'next'), None)
        if not nxt:
            break
        response = SESSION.request(nxt.get('method', 'GET'), nxt['href'], json=nxt.get('body'), timeout=120)
        response.raise_for_status()
        result = response.json()
        features.extend(result['features'])
    save_json(META / 'sentinel2_search.json', dict(query=params, source=url, features=features))
    print(f'Inventoried {len(features)} Sentinel-2 tiles (not downloaded or cloud-masked)', flush=True)


def rainfall():
    day = datetime(2024, 6, 21)
    while day <= datetime(2024, 7, 15):
        stamp = day.strftime('%Y.%m.%d')
        url = f'https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/2024/chirps-v2.0.{stamp}.cog'
        crop_raster(url, INTERIM / f'rainfall/chirps_{day:%Y%m%d}_lagos.tif',
                    license='Public domain; https://chc.ucsb.edu/data/chirps', epoch=day.strftime('%Y-%m-%d'),
                    units='mm/day', caveat='0.05 degree grid; daily totals cannot establish flood timing at 06:30 WAT')
        day += timedelta(days=1)


def landcover():
    for tile in ('N06E000', 'N06E003'):
        url = f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif'
        crop_raster(url, INTERIM / f'landcover/lagos_worldcover2021_{tile}.tif',
                    license='CC BY 4.0; ESA WorldCover 2021 v200', epoch='2021',
                    caveat='Pre-event land cover; urban development between 2021 and 2024 is not represented')


def sar_download():
    """Download the recommended event pair using an explicitly supplied Earthdata token."""
    token = os.environ.get('EARTHDATA_TOKEN')
    if not token:
        raise RuntimeError('Set EARTHDATA_TOKEN locally to an Earthdata bearer token; never put it in source control or chat')
    pairs = json.loads((META / 'sentinel1_pairs.json').read_text())
    if not pairs:
        raise RuntimeError('No comparable pair found')
    selected = {pairs[0]['before'], pairs[0]['after']}
    features = json.loads((META / 'sentinel1_search.geojson').read_text())['features']
    # Authorization only for ASF downloads; requests strips it on cross-host redirects.
    SESSION.headers['Authorization'] = f'Bearer {token}'
    try:
        for f in features:
            p = f['properties']
            if p['sceneName'] in selected:
                target = download(p['url'], RAW / f"sentinel1/{p['sceneName']}.zip", expected_bytes=p['bytes'], expected_md5=p['md5sum'])
                h = hashlib.md5()
                with target.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024*1024), b''):
                        h.update(block)
                if target.stat().st_size != p['bytes'] or h.hexdigest() != p['md5sum']:
                    raise RuntimeError(f'ASF checksum/size mismatch: {target}')
    finally:
        SESSION.headers.pop('Authorization', None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['boundaries', 'scenes', 'terrain', 'water', 'optical', 'rainfall', 'landcover', 'sar-download', 'core'])
    args = parser.parse_args()
    steps = dict(boundaries=boundaries, scenes=scenes, terrain=terrain, water=water, optical=optical,
                 rainfall=rainfall, landcover=landcover, **{'sar-download': sar_download})
    for step in (['boundaries', 'scenes', 'terrain', 'water', 'optical', 'rainfall', 'landcover'] if args.step == 'core' else [args.step]):
        print(f'--- {step} ---', flush=True)
        steps[step]()


if __name__ == '__main__':
    main()
