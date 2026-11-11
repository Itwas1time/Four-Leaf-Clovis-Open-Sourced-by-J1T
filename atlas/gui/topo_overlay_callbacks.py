"""Old USGS topographic sheets over the map at the person's spot or town (core/topo_overlay.py)."""
import sqlite3

import dash_leaflet as dl
from dash import Input, Output, State, callback, no_update

from core import historical_topos, my_spot, topo_overlay
from core.us_places import get_place

HIDDEN, SHOWN = {'display': 'none'}, {'display': 'block'}


def _point(spot, state, geoid):
    place = get_place(geoid, state)
    if place is None:
        return None
    spot = my_spot.for_place(spot, place)
    return (spot['lat'], spot['lon'], 'your spot') if spot else (place['latitude'], place['longitude'], 'the town point')


@callback(Output('topo-year', 'options'), Output('topo-year', 'value'), Output('topo-controls', 'style'),
          Output('topo-status', 'children'),
          Input('resident-state', 'value'), Input('resident-place', 'value'), Input('my-spot', 'data'),
          Input('workflow-mode', 'value'), prevent_initial_call=True)
def topo_choices(state, geoid, spot, mode):
    point = _point(spot, state, geoid) if mode == 'resident' else None
    if point is None:
        return [], None, HIDDEN, ''
    lat, lon, where = point
    try:
        sheets = [sheet for sheet in historical_topos.covering(lat, lon) if sheet['geotiff_url']]
    except (OSError, sqlite3.Error, ValueError):
        sheets = []
    if not sheets:
        return [], None, HIDDEN, ''
    options = [{'label': f"{sheet['date'] or 'Undated'} · {sheet['name']} · 1:{sheet['scale']:,}"
                         + (' · saved' if topo_overlay.cached(sheet['scan_id']) else ''),
                'value': sheet['scan_id']} for sheet in sheets]
    return options, None, SHOWN, (f"{len(sheets)} USGS sheets cover {where}, "
                                  f"{sheets[0]['date'] or 'undated'}–{sheets[-1]['date'] or 'undated'}.")


@callback(Output('topo-overlay-layer', 'children'), Output('topo-status', 'children', allow_duplicate=True),
          Input('topo-year', 'value'), Input('topo-opacity', 'value'), prevent_initial_call=True)
def show_sheet(scan_id, opacity):
    if not isinstance(scan_id, int):
        return [], no_update
    opacity = opacity if isinstance(opacity, (int, float)) and 0.2 <= opacity <= 1 else 0.85
    first_time = topo_overlay.cached(scan_id) is None
    try:
        sheet = topo_overlay.overlay(scan_id)
    except ValueError as exc:
        return [], str(exc)
    except Exception:  # network, GDAL or image errors: say so plainly, keep the map working
        return [], ('This sheet could not be fetched from USGS. It needs internet the first time; '
                    'sheets you have opened before work offline.')
    note = (f"{sheet['date']} {sheet['name']} sheet, 1:{sheet['scale']:,}. USGS Historical Topographic Map Collection "
            "(public domain). " + ('Saved on this computer; it now works offline.' if first_time else 'Works offline.'))
    return [dl.ImageOverlay(url=f'/topo-overlay/{scan_id}.webp', bounds=sheet['bounds'], opacity=opacity,
                            id='topo-overlay-image')], note
