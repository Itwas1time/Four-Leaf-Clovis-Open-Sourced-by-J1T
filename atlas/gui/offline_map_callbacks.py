"""Render local context for the visible map without fetching a tile provider."""
import sqlite3
from dash import Input,Output,State,no_update,callback
from math import cos,floor,isfinite,log2,radians
import dash_leaflet as dl
from atlas.gui.map_layers import _client_function
from atlas.gui.workspace_activation import when_opened
from core.offline_map import context,ATTRIBUTION
from core.us_places import get_place


@callback(Output('main-map','viewport',allow_duplicate=True),Input('offline-regional-view','n_clicks'),
          State('resident-place','value'),State('resident-state','value'),State('main-map','center'),prevent_initial_call=True)
def regional_view(clicks,geoid,state,center):
    if not clicks:return no_update
    place=get_place(geoid,state)
    center=[place['latitude'],place['longitude']] if place else center
    if (not isinstance(center,(tuple,list)) or len(center)!=2
        or any(type(v) not in (int,float) or not isfinite(v) for v in center)
        or not -85<=center[0]<=85):
        return no_update
    zoom=max(3,min(9,floor(log2(156543.03392*cos(radians(center[0]))/(500000*0.00028)))))
    return {'center':center,'zoom':zoom,'transition':'setView'}


@when_opened(('map','research'),Output('offline-local-context','children'),Output('offline-context-note','children'),
             Input('main-map','bounds'),Input('main-map','zoom'),Input('basemap-selector','value'),
             Input('workflow-mode','value'),Input('resident-tool','value'),State('resident-place','value'))
def local_context(bounds,zoom,basemap,mode,tool,selected):
    if mode!='research' and not (mode=='resident' and tool=='map'):
        return no_update,no_update
    if basemap!='offline':
        return [],'Online map selected. Offline county and town context is available without a connection.'
    try:
        result=context(bounds,zoom,selected)
    except (ValueError,OSError,sqlite3.Error):
        return [],'Offline coastlines. Choose a town for local context; no streets or property detail.'
    layers=[dl.GeoJSON(data=result['counties'],id='offline-counties',
        options={'style':{'color':'#697b68','weight':1.3,'fillOpacity':0}},
        onEachFeature=_client_function('offlineCountyLabel'),attribution=ATTRIBUTION)]
    for row in result['towns']:
        layers.append(dl.CircleMarker(center=[row['latitude'],row['longitude']],radius=3,
            color='#ffffff',weight=1,fillColor='#3b6153',fillOpacity=1,
            children=dl.Tooltip(row['name']+', '+row['state'],permanent=True,direction='right',
                                className='clovis-offline-place-label')))
    return layers,result['note']
