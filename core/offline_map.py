"""Bounded local map context from public Census outlines and place points."""
from contextlib import closing
import gzip
import json
from math import cos,isfinite,radians
from pathlib import Path
import sqlite3

from core.us_places import places_in_bounds

DATA=Path(__file__).resolve().parents[1]/'atlas/gui/data/offline_counties_2025.sqlite'
ATTRIBUTION='U.S. Census Bureau · 2025 county/equivalent outlines (1:500,000) and public place points'
EMPTY={'type':'FeatureCollection','features':[]}


def _bounds(bounds):
    if not isinstance(bounds,(list,tuple)) or len(bounds)!=2:
        raise ValueError('Use the current map extent.')
    try:
        south,west=bounds[0]
        north,east=bounds[1]
        values=(south,west,north,east)
        if any(type(value) not in (int,float) or not isfinite(value) for value in values):
            raise ValueError()
        if not -90<=south<north<=90 or not west<east or east-west>360:
            raise ValueError()
    except (TypeError,ValueError):
        raise ValueError('Use a finite geographic map extent.') from None
    return south,west,north,east


def context(bounds,zoom,selected=None):
    south,west,north,east=_bounds(bounds)
    if type(zoom) not in (int,float) or not isfinite(zoom) or not 0<=zoom<=22:
        raise ValueError('Use the current map zoom.')
    # Honour the source's intended display scale. At close zooms, points still
    # orient the reader; approximate county lines must not resemble parcel data.
    metres_per_pixel=156543.03392*cos(radians((south+north)/2))/2**zoom
    counties=[]
    county_scale=metres_per_pixel/0.00028>=500000
    if zoom>=6 and county_scale:
        with closing(sqlite3.connect(DATA.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
            rows=db.execute('SELECT feature FROM counties WHERE north>=? AND south<=? AND east>=? AND west<=? ORDER BY geoid LIMIT 161',
                            (south,north,west,east)).fetchall()
        if len(rows)<=160:
            counties=[json.loads(gzip.decompress(row[0])) for row in rows]
    towns=places_in_bounds((south,west,north,east),selected=selected,zoom=zoom) if zoom>=6 else []
    if counties:
        note='Offline county outlines and public town points. No streets or property detail.'
    elif zoom<6:
        note='Offline coastlines. Zoom in for U.S. county outlines and town names. No streets or property detail.'
    elif not county_scale:
        note='Close offline view: zoom out with Show regional view for available county and town context. No streets or property detail.'
    elif towns:
        note='Offline town points. Zoom in for county outlines. No streets or property detail.'
    else:
        note='Offline coastlines. County and town context covers U.S. Census areas. No streets or property detail.'
    return {'counties':{'type':'FeatureCollection','features':counties},'towns':towns,
            'county_detail':bool(counties),'regional_zoom':zoom<6,
            'note':note}
