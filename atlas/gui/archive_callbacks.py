"""Archive callbacks: uploaded image content is used only by a client callback."""
import sqlite3
from dash import ALL, Input, Output, State, callback, clientside_callback, html, no_update
from core.historical_maps import search_maps, map_sheets, public_url, remember_archive, current_archive
from core.us_places import get_place
from core.sanborn_catalog import search_catalog, catalog_stats, census_town


@callback(Output('archive-town','children'),Output('archive-search','disabled'),Input('resident-state','value'),Input('resident-place','value'))
def town_label(state, geoid):
    town=get_place(geoid,state)
    return (f"{town['name']}, {town['state']}" if town else 'Choose a town in the place controls'), not bool(town)


@callback(Output('archive-results','data'),Output('archive-status','children'),Output('archive-cards','children'),Output('archive-record','options'),Output('archive-record','value'),
          Output('archive-catalog-page','data'),Output('archive-catalog-page-label','children'),Output('archive-catalog-prev','disabled'),Output('archive-catalog-next','disabled'),Output('archive-catalog-coverage','children'),
          Input('archive-search','n_clicks'),Input('resident-state','value'),Input('resident-place','value'),Input('archive-catalog-scope','value'),Input('archive-catalog-order','value'),Input('archive-catalog-prev','n_clicks'),Input('archive-catalog-next','n_clicks'),Input('archive-catalog-bundled','n_clicks'),State('archive-catalog-page','data'))
def find_maps(clicks,state,geoid,scope='town',order='oldest',previous=0,next_click=0,bundled=0,page=0):
    from dash import ctx
    online = ctx.triggered_id == 'archive-search' and bool(clicks)
    empty = (None,'Choose a state or town to browse historical maps.',[],[],None,0,'',True,True,'')
    coverage = ''
    try:
        summary = catalog_stats()
        coverage = [f"Offline Sanborn catalog: {summary['records']:,} US atlas records · {summary['town_state_pairs']:,} catalog town/state names · 50 states + DC. Metadata: {summary['snapshot']}. Public domain; coverage is incomplete. ",html.A('Source and coverage',href='https://data.labs.loc.gov/sanborn/',target='_blank',rel='noopener noreferrer')]
        if online:
            result = search_maps(state,geoid)
            paging = (0,'Online search results',True,True,coverage)
        else:
            place = get_place(geoid,state)
            town = census_town(place['name']) if place else ''
            current_page = page if type(page) is int and 0 <= page <= 10000 else 0
            if ctx.triggered_id == 'archive-catalog-next': current_page += 1
            elif ctx.triggered_id == 'archive-catalog-prev': current_page = max(0,current_page-1)
            else: current_page = 0
            result = search_catalog(state,town,current_page,scope,order)
            label = f"Exact catalog town name: {town}, {state}" if result['exact_town'] else f"Statewide catalog: {state}"
            if scope == 'town' and town and not result['exact_town']:
                label = f"No exact catalog name match for {town}, {state}. Showing statewide records"
            result['message'] = f"{label} · {result['total']:,} atlas records. Catalog names do not establish complete map extent. Select a record to inspect its date and source."
            paging = (result['page'],f"Page {result['page']+1} of {result['pages']}",result['page']==0,result['page']+1>=result['pages'],coverage)
    except ValueError as exc:
        return (None,str(exc),[],[],None,0,'',True,True,coverage)
    except (OSError, sqlite3.Error):
        if not online:
            return (None,'Bundled catalog is unavailable. Search more maps online or open your own image.',[],[],None,0,'',True,True,'')
        result = search_maps(state,geoid)
        paging = (0,'Online search results',True,True,'Bundled catalog unavailable.')
    rows=result['results']
    cards=[html.Button(className='archive-card',id={'type':'archive-card','record':r['id']},n_clicks=0,children=[html.Strong(r['title']),html.P(r['date']+' · '+r['source']),html.P(r.get('description','')) if r.get('catalog') else None,html.Small('Open preview and source →' if r.get('image') else 'Open catalog source →')]) for r in rows]
    return (remember_archive(rows,state,geoid),result['message'],cards,[{'label':r['title']+' · '+r['date'],'value':r['id']} for r in rows],rows[0]['id'] if online and rows else None,*paging)


@callback(Output('archive-selected','data'),Output('archive-sheets','data'),Output('archive-sheet','options'),Output('archive-sheet','value'),Output('archive-sheet-status','children'),Output('archive-source-record','children'),
          Input('archive-record','value'),State('archive-results','data'),State('resident-state','value'),State('resident-place','value'))
def select_record(item_id,token,state,geoid):
    rows=current_archive(token,state,geoid)
    rows=rows[:12] if isinstance(rows,list) else []
    row=next((r for r in rows if isinstance(r,dict) and r.get('id')==item_id),None)
    if not row: return None,[],[],None,'',''
    return _open_record(row,state,geoid,online=not row.get('catalog'))


def _open_record(row,state,geoid,online=False):
    item_id = row['id']
    selected={k:str(row.get(k,''))[:400] for k in ('id','title','date','source')}
    selected['url']=public_url(row.get('url'))
    selected['image']=public_url(row.get('image'),True)
    selected['catalog']=bool(row.get('catalog'))
    if online:
        sheets,status=map_sheets(item_id)
    else:
        sheets=[]
        status='Bundled metadata opened without an online API request. Use Load map sheets online for the full atlas.' if selected['image'] else 'No preview in this metadata snapshot. Catalog record only; no sheet viewed. Open the catalog source; online access may have changed since January 2024.'
    if not sheets and selected['image']: sheets=[{'label':'Record preview','image':selected['image']}]
    selected['sheets']=sheets
    source=html.A('Source record and rights information',href=selected['url'],target='_blank',rel='noopener noreferrer') if selected['url'] else ''
    rights=' The Library of Congress identifies its online Sanborn collection as public domain.' if selected['catalog'] else ' Rights and reuse must be checked in the source record; digitization does not establish clearance.'
    return {'token':remember_archive(selected,state,geoid)},sheets,[{'label':s['label'],'value':i} for i,s in enumerate(sheets)],0 if sheets else None,status+rights,source


@callback(Output('archive-load-sheets','disabled'),Input('archive-selected','data'),Input('resident-state','value'),Input('resident-place','value'))
def sheets_button(selected,state,geoid):
    row=current_archive(selected.get('token'),state,geoid) if isinstance(selected,dict) else None
    return not isinstance(row,dict) or not row.get('id')


@callback(Output('archive-selected','data',allow_duplicate=True),Output('archive-sheets','data',allow_duplicate=True),Output('archive-sheet','options',allow_duplicate=True),Output('archive-sheet','value',allow_duplicate=True),Output('archive-sheet-status','children',allow_duplicate=True),Output('archive-source-record','children',allow_duplicate=True),Input('archive-load-sheets','n_clicks'),State('archive-selected','data'),State('resident-state','value'),State('resident-place','value'),prevent_initial_call=True)
def load_selected_sheets(clicks,selected,state,geoid):
    row=current_archive(selected.get('token'),state,geoid) if isinstance(selected,dict) else None
    if not clicks or not isinstance(row,dict) or not row.get('id'):
        return (no_update,)*6
    return _open_record(row,state,geoid,online=True)


@callback(Output('archive-note-context','data'),Input('archive-selected','data'),Input('archive-notes','value'),Input('archive-local-title','value'),Input('resident-state','value'),Input('resident-place','value'),Input('archive-source-mode','data'),Input('archive-sheet','value'))
def note_context(selected,notes,local,state,geoid,mode,sheet=None):
    place=get_place(geoid,state)
    if not place: return None
    def text(v,n): return v[:n] if isinstance(v,str) else ''
    selected=current_archive(selected.get('token'),state,geoid) if isinstance(selected,dict) else {}
    selected=selected if isinstance(selected,dict) else {}
    catalog_only=selected.get('catalog') is True and not selected.get('image') and selected.get('sheets')==[]
    metadata_only=mode is None and catalog_only
    if not metadata_only and (not isinstance(mode,dict) or mode.get('state')!=state or mode.get('geoid')!=geoid or mode.get('mode') not in ('local','archive')): return None
    is_local=not metadata_only and mode['mode']=='local'
    if not is_local and not selected: return None
    sheet_label=''
    if not is_local and isinstance(selected.get('sheets'),list) and selected['sheets']:
        sheets=selected['sheets']
        if type(sheet) is not int or not 0<=sheet<len(sheets): return None
        sheet_label=' · '+text(sheets[sheet].get('label'),80)
    value={'title':(text(local,240) or 'Browser-local map image (title not supplied)') if is_local else text(selected.get('title'),400),
            'date':'' if is_local else text(selected.get('date'),80),
            'source':'Browser-local map image; title and source are user-reported' if is_local else public_url(selected.get('url')),
            'notes':text(notes,1500)}
    value['title']+=sheet_label
    if catalog_only and not is_local:
        value['title']+=' · Catalog record only; no sheet viewed'
    return {'token':remember_archive(value,state,geoid),**value}


clientside_callback(
    """function(upload, sheet, zin, zout, fit, rotate, state, geoid, sheets, selected) {
        return window.clovisArchive.view(upload,sheet,sheets,selected,zin,zout,fit,rotate,state,geoid);
    }""",Output('archive-image-event','data'),Input('archive-upload','contents'),Input('archive-sheet','value'),Input('archive-zoom-in','n_clicks'),Input('archive-zoom-out','n_clicks'),Input('archive-fit','n_clicks'),Input('archive-rotate','n_clicks'),Input('resident-state','value'),Input('resident-place','value'),Input('archive-sheets','data'),Input('archive-selected','data'))


clientside_callback("""function(clicks) {const t=window.dash_clientside.callback_context.triggered_id;return t && typeof t==='object' && clicks.some(n=>n>0)?t.record:window.dash_clientside.no_update;}""",
    Output('archive-record','value',allow_duplicate=True),Input({'type':'archive-card','record':ALL},'n_clicks'),prevent_initial_call=True)
