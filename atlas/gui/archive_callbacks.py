"""Archive callbacks: uploaded image content is used only by a client callback."""
from dash import ALL, Input, Output, State, callback, clientside_callback, html, no_update
from core.historical_maps import search_maps, map_sheets, public_url, remember_archive, current_archive
from core.us_places import get_place


@callback(Output('archive-town','children'),Output('archive-search','disabled'),Input('resident-state','value'),Input('resident-place','value'))
def town_label(state, geoid):
    town=get_place(geoid,state)
    return (f"{town['name']}, {town['state']}" if town else 'Choose a town in the place controls'), not bool(town)


@callback(Output('archive-results','data'),Output('archive-status','children'),Output('archive-cards','children'),Output('archive-record','options'),Output('archive-record','value'),
          Input('archive-search','n_clicks'),Input('resident-state','value'),Input('resident-place','value'),prevent_initial_call=True)
def find_maps(clicks,state,geoid):
    from dash import ctx
    if ctx.triggered_id!='archive-search' or not clicks:
        return [],'Town changed. Search maps for the current town.',[],[],None
    try: result=search_maps(state,geoid)
    except ValueError as exc: return [],str(exc),[],[],None
    rows=result['results']
    cards=[html.Button(className='archive-card',id={'type':'archive-card','record':r['id']},n_clicks=0,children=[html.Strong(r['title']),html.P(r['date']+' · '+r['source']),html.Small('Open this map →')]) for r in rows]
    return remember_archive(rows,state,geoid),result['message'],cards,[{'label':r['title']+' · '+r['date'],'value':r['id']} for r in rows],rows[0]['id'] if rows else None


@callback(Output('archive-selected','data'),Output('archive-sheets','data'),Output('archive-sheet','options'),Output('archive-sheet','value'),Output('archive-sheet-status','children'),Output('archive-source-record','children'),
          Input('archive-record','value'),State('archive-results','data'),State('resident-state','value'),State('resident-place','value'))
def select_record(item_id,token,state,geoid):
    rows=current_archive(token,state,geoid)
    rows=rows[:12] if isinstance(rows,list) else []
    row=next((r for r in rows if isinstance(r,dict) and r.get('id')==item_id),None)
    if not row: return None,[],[],None,'',''
    selected={k:str(row.get(k,''))[:400] for k in ('id','title','date','source')}
    selected['url']=public_url(row.get('url'))
    selected['image']=public_url(row.get('image'),True)
    sheets,status=map_sheets(item_id)
    if not sheets and selected['image']: sheets=[{'label':'Record preview','image':selected['image']}]
    selected['sheets']=sheets
    source=html.A('Source record and rights information',href=selected['url'],target='_blank',rel='noopener noreferrer') if selected['url'] else ''
    return {'token':remember_archive(selected,state,geoid)},sheets,[{'label':s['label'],'value':i} for i,s in enumerate(sheets)],0 if sheets else None,status+' Rights and reuse must be checked in the source record; digitization does not establish clearance.',source


@callback(Output('archive-note-context','data'),Input('archive-selected','data'),Input('archive-notes','value'),Input('archive-local-title','value'),Input('resident-state','value'),Input('resident-place','value'),Input('archive-source-mode','data'),Input('archive-sheet','value'))
def note_context(selected,notes,local,state,geoid,mode,sheet=None):
    place=get_place(geoid,state)
    if not place or not isinstance(mode,dict) or mode.get('state')!=state or mode.get('geoid')!=geoid or mode.get('mode') not in ('local','archive'): return None
    def text(v,n): return v[:n] if isinstance(v,str) else ''
    selected=current_archive(selected.get('token'),state,geoid) if isinstance(selected,dict) else {}
    selected=selected if isinstance(selected,dict) else {}
    is_local=mode['mode']=='local'
    if not is_local and not selected: return None
    sheet_label=''
    if not is_local and isinstance(selected.get('sheets'),list):
        sheets=selected['sheets']
        if type(sheet) is not int or not 0<=sheet<len(sheets): return None
        sheet_label=' · '+text(sheets[sheet].get('label'),80)
    value={'title':(text(local,240) or 'Browser-local map image (title not supplied)') if is_local else text(selected.get('title'),400),
            'date':'' if is_local else text(selected.get('date'),80),
            'source':'Browser-local map image; title and source are user-reported' if is_local else public_url(selected.get('url')),
            'notes':text(notes,1500)}
    value['title']+=sheet_label
    return {'token':remember_archive(value,state,geoid),**value}


clientside_callback(
    """function(upload, sheet, zin, zout, fit, rotate, state, geoid, sheets, selected) {
        return window.clovisArchive.view(upload,sheet,sheets,selected,zin,zout,fit,rotate,state,geoid);
    }""",Output('archive-image-event','data'),Input('archive-upload','contents'),Input('archive-sheet','value'),Input('archive-zoom-in','n_clicks'),Input('archive-zoom-out','n_clicks'),Input('archive-fit','n_clicks'),Input('archive-rotate','n_clicks'),Input('resident-state','value'),Input('resident-place','value'),Input('archive-sheets','data'),Input('archive-selected','data'))


clientside_callback("""function(clicks) {const t=window.dash_clientside.callback_context.triggered_id;return t && typeof t==='object' && clicks.some(n=>n>0)?t.record:window.dash_clientside.no_update;}""",
    Output('archive-record','value',allow_duplicate=True),Input({'type':'archive-card','record':ALL},'n_clicks'),prevent_initial_call=True)
