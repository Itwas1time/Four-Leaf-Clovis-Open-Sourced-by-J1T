"""Old USGS topographic sheets laid over the map at the person's place.

A sheet is fetched once from the USGS Historical Topographic Map Collection (public domain), reprojected
to the web map, cropped to its printed map edge (the scan's paper margin is dropped) and saved as an image in
"Clovis Local". After that first view it works offline. Only the public sheet file is requested; the
person's spot is never sent anywhere.
"""
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from core import historical_topos

MAX_SIDE = 2400  # pixels on the longer side: ~6 m per pixel on a 1:24,000 sheet, ~12 m on 1:62,500
GDAL_ENV = {'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif',
            'GDAL_HTTP_TIMEOUT': '60', 'GDAL_HTTP_MAX_RETRY': '2'}


def cache_dir():
    root = Path(os.environ.get('CLOVIS_DERIVED_PATH') or Path.home() / 'Clovis Local' / 'derived')
    return root / 'topo-overlays'


def sheet(scan_id):
    """Index row for one sheet: printed map edge (neatline) bounds, label and GeoTIFF address."""
    if type(scan_id) is not int or not 0 < scan_id < 10**9:
        raise ValueError('Choose a sheet from the list.')
    with closing(sqlite3.connect(historical_topos.DATA.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        row = db.execute('SELECT scan_id,name,folder_state,folder_scale,tif_state,date_on_map,survey_year,imprint_year,'
                         'filename,original_urls,west,south,east,north FROM maps WHERE scan_id=?', (scan_id,)).fetchone()
    if row is None:
        raise ValueError('Choose a sheet from the list.')
    (scan_id, name, state, scale, tif_state, date, survey, imprint, filename, original, west, south, east, north) = row
    _, _, geotiff = historical_topos._urls(state, scale, tif_state, filename, original)
    return {'scan_id': scan_id, 'name': name, 'scale': int(scale), 'date': date or survey or imprint or '',
            'geotiff_url': geotiff, 'bounds': [[south, west], [north, east]]}


def cached(scan_id):
    path = cache_dir() / f'{scan_id}.webp'
    return path if path.is_file() else None


def overlay(scan_id):
    """The sheet as a map overlay: {'path', 'bounds', ...}. Renders (online, once) when not cached."""
    info = sheet(scan_id)
    path = cached(scan_id)
    if path is None:
        if not info['geotiff_url']:
            raise ValueError('USGS has no georeferenced image for this sheet.')
        path = _render(info)
    return {**info, 'path': path}


def _render(info):
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject, transform_bounds

    (south, west), (north, east) = info['bounds']
    x0, y0, x1, y1 = transform_bounds('EPSG:4326', 'EPSG:3857', west, south, east, north)
    aspect = (x1 - x0) / (y1 - y0)
    width, height = (MAX_SIDE, max(1, round(MAX_SIDE / aspect))) if aspect >= 1 else (max(1, round(MAX_SIDE * aspect)), MAX_SIDE)
    transform = from_bounds(x0, y0, x1, y1, width, height)
    url = info['geotiff_url']
    url = '/vsicurl/' + url if url.startswith('https://') else url  # local files: tests and downloaded sheets
    with rasterio.Env(**GDAL_ENV):
        with rasterio.open(url) as probe:
            full_width, factors = probe.width, probe.overviews(1)
        # The coarsest overview that still has at least as many pixels across the map as the output.
        level = None
        for index, factor in enumerate(factors):
            if full_width * 0.85 / factor >= width:
                level = index
        with rasterio.open(url, **({'overview_level': level} if level is not None else {})) as src:
            bands = src.count
            out = np.zeros((max(bands, 1), height, width), dtype='uint8')
            for band in range(1, bands + 1):
                reproject(rasterio.band(src, band), out[band - 1], dst_transform=transform, dst_crs='EPSG:3857',
                          resampling=Resampling.bilinear)
            colormap = src.colormap(1) if bands == 1 else None
    if bands >= 3:
        rgb = np.moveaxis(out[:3], 0, -1)
    elif colormap:
        lut = np.zeros((256, 3), dtype='uint8')
        for value, color in colormap.items():
            lut[value] = color[:3]
        rgb = lut[out[0]]
    else:
        rgb = np.repeat(out[0][..., None], 3, axis=2)
    alpha = np.where(rgb.sum(axis=2) > 0, 255, 0).astype('uint8')  # outside the scanned sheet stays see-through
    target = cache_dir() / f"{info['scan_id']}.webp"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    Image.fromarray(np.dstack([rgb, alpha]), 'RGBA').save(temporary, format='WEBP', quality=82, method=4)
    os.replace(temporary, target)
    return target


def register_routes(server):
    from flask import Response, send_file

    @server.get('/topo-overlay/<int:scan_id>.webp')
    def topo_overlay_image(scan_id):
        path = cached(scan_id)
        if path is None:
            return Response('Open this sheet from the map first.', status=404, mimetype='text/plain')
        return send_file(path, mimetype='image/webp', max_age=86400)
