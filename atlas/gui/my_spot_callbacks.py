"""Exact spot from device location or a tap on the map (core/my_spot.py).

The spot is kept in the browser's local storage. It reaches only this local Clovis server, to pick
the nearest town and to answer the cemetery and old-map cards for the spot instead of the town point.
"""
import sqlite3

import dash_leaflet as dl
from dash import Input, Output, State, callback, clientside_callback, no_update

from core import known_cemeteries, my_spot
from core.us_places import get_place, search_places

IDLE = ("Your exact spot stays on this computer. Cemetery and old-map answers then describe your spot, "
        "not the town centre.")

# Device location. The browser asks the person first; nothing is sent anywhere but this computer.
clientside_callback(
    """
    function(clicks) {
        var skip = window.dash_clientside.no_update;
        if (!clicks) { return [skip, skip]; }
        if (!navigator.geolocation) {
            return [skip, 'This browser cannot share a location. Use Pick on the map instead.'];
        }
        return new Promise(function(resolve) {
            navigator.geolocation.getCurrentPosition(function(position) {
                resolve([{lat: position.coords.latitude, lon: position.coords.longitude,
                          accuracy_m: position.coords.accuracy, source: 'gps'}, 'Location found.']);
            }, function(error) {
                resolve([skip, 'Location unavailable (' + error.message + '). Use Pick on the map instead.']);
            }, {enableHighAccuracy: true, timeout: 20000, maximumAge: 60000});
        });
    }
    """,
    Output('my-spot', 'data', allow_duplicate=True), Output('my-spot-status', 'children', allow_duplicate=True),
    Input('my-spot-locate', 'n_clicks'), prevent_initial_call=True)


@callback(Output('my-spot-picking', 'data'), Output('my-spot-status', 'children', allow_duplicate=True),
          Output('my-spot-pick', 'children'), Output('resident-tool', 'value', allow_duplicate=True),
          Input('my-spot-pick', 'n_clicks'), State('my-spot-picking', 'data'), prevent_initial_call=True)
def toggle_picking(clicks, picking):
    if not clicks:
        return no_update, no_update, no_update, no_update
    if picking is True:
        return False, 'Picking cancelled.', 'Pick on the map', no_update
    return True, 'Tap the map where you are. Zoom in first for a precise spot.', 'Cancel picking', 'map'


@callback(Output('my-spot', 'data', allow_duplicate=True), Output('my-spot-picking', 'data', allow_duplicate=True),
          Output('my-spot-pick', 'children', allow_duplicate=True),
          Input('main-map', 'clickData'), State('my-spot-picking', 'data'), prevent_initial_call=True)
def pick_on_map(click, picking):
    if picking is not True or not isinstance(click, dict) or not isinstance(click.get('latlng'), dict):
        return no_update, no_update, no_update
    spot = my_spot.clean({'lat': click['latlng'].get('lat'), 'lon': click['latlng'].get('lng'), 'source': 'map'})
    return (spot, False, 'Pick on the map') if spot else (no_update, no_update, no_update)


@callback(Output('my-spot', 'data', allow_duplicate=True), Input('my-spot-clear', 'n_clicks'), prevent_initial_call=True)
def clear_spot(clicks):
    return None if clicks else no_update


@callback(Output('resident-state', 'value', allow_duplicate=True),
          Output('resident-place', 'options', allow_duplicate=True),
          Output('resident-place', 'value', allow_duplicate=True),
          Input('my-spot', 'data'), State('resident-state', 'value'), State('resident-place', 'value'),
          prevent_initial_call=True)
def town_for_spot(spot, state, geoid):
    """A new spot selects its nearest town, unless the chosen town already fits it."""
    spot = my_spot.clean(spot)
    place = get_place(geoid, state)
    if spot is None or (place and my_spot.for_place(spot, place)):
        return no_update, no_update, no_update
    town = my_spot.nearest_place(spot['lat'], spot['lon'])
    if town is None:
        return no_update, no_update, no_update
    return town['state'], search_places(town['state'], '', town['geoid']), town['geoid']


@callback(Output('my-spot-status', 'children'), Output('my-spot-clear', 'style'),
          Input('my-spot', 'data'), Input('resident-state', 'value'), Input('resident-place', 'value'),
          Input('workflow-mode', 'value'), prevent_initial_call=True)  # landing stays light; Explore shows it
def spot_status(spot, state, geoid, mode=None):
    spot = my_spot.clean(spot)
    if spot is None:
        return IDLE, {'display': 'none'}
    place = get_place(geoid, state)
    shown = {'display': 'inline-block'}
    if place and my_spot.for_place(spot, place):
        return f"Your spot: {my_spot.describe(spot)}. Answers below describe it.", shown
    if place:
        return (f"Your saved spot is more than {my_spot.NEAR_TOWN_KM} km from {place['name']}, so answers use "
                "the town point. Clear it or pick a new spot.", shown)
    if my_spot.nearest_place(spot['lat'], spot['lon']) is None:
        return f"Your spot ({my_spot.describe(spot)}) is outside the US towns Clovis covers.", shown
    return f"Your spot: {my_spot.describe(spot)}.", shown


@callback(Output('main-map', 'viewport', allow_duplicate=True), Input('my-spot', 'data'), prevent_initial_call=True)
def center_on_spot(spot):
    spot = my_spot.clean(spot)
    return {'center': [spot['lat'], spot['lon']], 'zoom': 13, 'transition': 'flyTo'} if spot else no_update


@callback(Output('my-spot-layer', 'children'),
          Input('my-spot', 'data'), Input('workflow-mode', 'value'),
          Input('resident-state', 'value'), Input('resident-place', 'value'), prevent_initial_call=True)
def spot_layer(spot, mode, state, geoid):
    """Your spot, and the named cemeteries near it (or near the town point), on the map."""
    if mode != 'resident':
        return []
    place = get_place(geoid, state)
    spot = my_spot.for_place(spot, place) if place else my_spot.clean(spot)
    if spot is None and place is None:
        return []
    lat, lon = (spot['lat'], spot['lon']) if spot else (place['latitude'], place['longitude'])
    layer = []
    try:
        rows, _ = known_cemeteries.nearby(lat, lon)
    except (OSError, sqlite3.Error, ValueError):
        rows = []
    for row in rows:
        layer.append(dl.CircleMarker(center=[row['latitude'], row['longitude']], radius=5, color='#ffffff', weight=1.5,
                                     fillColor='#6b5b4b', fillOpacity=0.9,
                                     children=dl.Tooltip(f"{row['name']} · cemetery (USGS GNIS)")))
    if spot:
        if spot.get('accuracy_m'):
            layer.append(dl.Circle(center=[lat, lon], radius=spot['accuracy_m'], color='#b5542c', weight=1,
                                   fillOpacity=0.08))
        layer.append(dl.CircleMarker(center=[lat, lon], radius=9, color='#ffffff', weight=3, fillColor='#b5542c',
                                     fillOpacity=1, children=dl.Tooltip('Your spot (kept on this computer)',
                                                                       permanent=True, direction='top')))
    return layer


@callback(Output('town-sheet', 'data'), Output('town-sheet-print', 'disabled'),
          Input('resident-state', 'value'), Input('resident-place', 'value'), Input('my-spot', 'data'),
          prevent_initial_call=True)
def town_sheet(state, geoid, spot):
    """The one-page summary of the town cards (or the person's spot), ready to print."""
    from core import town_cards
    place = get_place(geoid, state)
    if place is None:
        return None, True
    title, text = town_cards.one_page(place, state, my_spot.for_place(spot, place))
    return {'title': title, 'text': text}, False


clientside_callback(
    """function(clicks, sheetData) {
        if (!clicks || !sheetData) return window.dash_clientside.no_update;
        let sheet = document.getElementById('clovis-print-sheet');
        if (!sheet) { sheet = document.createElement('article'); sheet.id = 'clovis-print-sheet'; document.body.appendChild(sheet); }
        sheet.replaceChildren();
        const brand = document.createElement('p'); brand.textContent = 'clovis · A little curiosity, Dig deeper.';
        const heading = document.createElement('h1'); heading.textContent = sheetData.title;
        const body = document.createElement('pre'); body.textContent = sheetData.text;
        sheet.append(brand, heading, body);
        window.print();
        return clicks;
    }""",
    Output('town-sheet-printed', 'data'), Input('town-sheet-print', 'n_clicks'), State('town-sheet', 'data'),
    prevent_initial_call=True)


@callback(Output('my-spot-picking', 'data', allow_duplicate=True),
          Output('my-spot-status', 'children', allow_duplicate=True),
          Output('my-spot-pick', 'children', allow_duplicate=True),
          Input({'type': 'workbench-action', 'target': 'map', 'key': 'start-roam'}, 'n_clicks'),
          prevent_initial_call=True)
def roam_picks_a_spot(clicks):
    """"Just curious? Wander the map" starts ready to explore any spot you tap."""
    if not clicks:
        return no_update, no_update, no_update
    return True, 'Tap anywhere on the map to see who lived there, nearby cemeteries and old maps of that spot.', 'Cancel picking'
