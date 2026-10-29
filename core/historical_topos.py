"""USGS historical topographic sheets that cover a point, from a bundled offline index."""
from contextlib import closing
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

DATA = Path(__file__).resolve().parents[1]/'atlas/gui/data/us_historical_topo_index.sqlite'
BASE = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/'


def _connect():
    return closing(sqlite3.connect(DATA.resolve().as_uri() + '?mode=ro&immutable=1', uri=True))


@lru_cache(maxsize=1)
def source():
    with _connect() as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='source'").fetchone()[0])


def _urls(folder_state, scale, tif_state, filename, original):
    if original:
        return json.loads(original)
    quoted = quote(filename, safe="'(),&+=;@!$*")
    stem = quoted.removesuffix('_geo.pdf')
    return (f'{BASE}PDF/{folder_state}/{scale}/{quoted}', f'{BASE}PDF/{folder_state}/{scale}/{stem}_tn.jpg',
            f'{BASE}GeoTIFF/{tif_state}/{stem}_geo.tif' if tif_state else '')


def covering(latitude, longitude):
    """Every sheet whose footprint contains the point, oldest first."""
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (latitude, longitude)):
        raise ValueError('Use numeric coordinates.')
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError('Use valid coordinates.')
    with _connect() as db:
        rows = db.execute('SELECT scan_id,name,folder_state,folder_scale,tif_state,date_on_map,survey_year,imprint_year,'
                          'publishers,filename,original_urls FROM maps '
                          'WHERE south<=? AND north>=? AND west<=? AND east>=?',
                          (latitude, latitude, longitude, longitude)).fetchall()
    sheets = []
    for scan_id, name, state, scale, tif_state, date, survey, imprint, publishers, filename, original in rows:
        pdf, thumbnail, geotiff = _urls(state, scale, tif_state, filename, original)
        sheets.append({'scan_id': scan_id, 'name': name, 'scale': int(scale), 'date': date or survey or imprint or '',
                       'survey_year': survey, 'imprint_year': imprint, 'publishers': publishers,
                       'pdf_url': pdf, 'thumbnail_url': thumbnail, 'geotiff_url': geotiff})
    sheets.sort(key=lambda sheet: (sheet['date'] or '9999', sheet['scale'], sheet['scan_id']))
    return sheets


def summary(latitude, longitude):
    """Counts and highlights for a place: total sheets, year span and the oldest few."""
    sheets = covering(latitude, longitude)
    years = sorted(int(s['date'][:4]) for s in sheets if s['date'][:4].isdigit())
    return {'total': len(sheets), 'earliest': years[0] if years else None, 'latest': years[-1] if years else None,
            'oldest': sheets[:3], 'sheets': sheets}
