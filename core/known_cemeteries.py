"""Named cemeteries known to USGS GNIS near a point, read from a bundled offline index."""
from contextlib import closing
from functools import lru_cache
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import sqlite3

DATA = Path(__file__).resolve().parents[1]/'atlas/gui/data/us_cemeteries_gnis_2021.sqlite'
EARTH_KM = 6371.0088


def _connect():
    return closing(sqlite3.connect(DATA.resolve().as_uri() + '?mode=ro&immutable=1', uri=True))


@lru_cache(maxsize=1)
def source():
    with _connect() as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='source'").fetchone()[0])


def _distance_km(lat1, lon1, lat2, lon2):
    a = sin(radians(lat2 - lat1) / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_KM * asin(sqrt(a))


def nearby(latitude, longitude, radius_km=8.0, limit=10):
    """Closest named cemeteries within radius_km, nearest first, with their GNIS identifiers."""
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (latitude, longitude, radius_km)):
        raise ValueError('Use numeric coordinates and radius.')
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and 0 < radius_km <= 50) or not 0 < limit <= 50:
        raise ValueError('Use valid coordinates, a radius up to 50 km and up to 50 results.')
    dlat = radius_km / 111.0
    dlon = radius_km / max(111.0 * cos(radians(latitude)), 1e-6)
    with _connect() as db:
        rows = db.execute('SELECT feature_id,name,state,county,latitude,longitude FROM cemeteries '
                          'WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?',
                          (latitude - dlat, latitude + dlat, longitude - dlon, longitude + dlon)).fetchall()
    found = []
    for feature_id, name, state, county, lat, lon in rows:
        distance = _distance_km(latitude, longitude, lat, lon)
        if distance <= radius_km:
            found.append({'gnis_id': feature_id, 'name': name, 'state': state, 'county': county,
                          'latitude': lat, 'longitude': lon, 'distance_km': round(distance, 2)})
    found.sort(key=lambda row: (row['distance_km'], row['gnis_id']))
    return found[:limit], len(found)


def report_lines(place, md=str):
    """Town-report section: named cemeteries near the public town point, with honest limits."""
    try:
        rows, total = nearby(place['latitude'], place['longitude'])
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return ['## Known cemeteries near the town point', '',
                'The offline cemetery index is unavailable. Restore the application files and restart.', '']
    lines = ['## Known cemeteries near the town point', '']
    if rows:
        lines += [f"USGS GNIS names **{total}** cemeteries within 8 km of the public town point"
                  + (f'; the nearest {len(rows)} are listed.' if total > len(rows) else '.'), '']
        lines += [f"- {md(row['name'])}, {md(row['county'])} County: {row['distance_km']:.1f} km "
                  f"(GNIS {row['gnis_id']})" for row in rows]
        lines.append('')
    else:
        lines += ['USGS GNIS names no cemetery within 8 km of the public town point.', '']
    lines += ['Distances are from the town point, not your yard. GNIS lists named cemeteries as of 2021 and is no '
              'longer updated for them. Family, abandoned, unmarked and Native burial places are often missing, so a '
              'missing record does not mean there are no burials. If you are digging in a known burial ground or '
              'cemetery, the law asks you to stop there and contact local authorities.', '',
              'Source: U.S. Geological Survey, Geographic Names Information System, legacy national file '
              '(25 August 2021), public domain.', '']
    return lines
