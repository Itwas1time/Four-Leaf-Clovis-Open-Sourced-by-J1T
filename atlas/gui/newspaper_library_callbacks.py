"""Local title chronology; town scope always uses cataloged names."""
import sqlite3
from dash import ALL,Input,Output,State,callback,callback_context,html,no_update
from core.newspaper_catalog import search_titles,get_title
from core.sanborn_catalog import census_town
from core.us_places import get_place
from core.newspaper_notes import facts,reference_entry
from core.fieldbook import EMPTY_BOOK,merge_entries
from atlas.gui.library_callbacks import _url
from atlas.gui.library_ui import reading_nav


@callback(Output('library-newspaper-scope','value'),Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'),prevent_initial_call=True)
def town_scope(clicks):
    trigger=callback_context.triggered_id
    return 'town' if isinstance(trigger,dict) and trigger.get('key')=='town-newspapers' and any(clicks or []) else no_update


@callback(Output('library-newspaper-cards','children'),Output('library-newspaper-count','children'),
          Output('library-newspaper-page','data'),Output('library-newspaper-page-label','children'),
          Output('library-newspaper-previous','disabled'),Output('library-newspaper-next','disabled'),
          Input('library-newspaper-query','value'),Input('library-newspaper-scope','value'),
          Input('library-newspaper-previous','n_clicks'),Input('library-newspaper-next','n_clicks'),
          Input('resident-state','value'),Input('resident-place','value'),State('library-newspaper-page','data'))
def results(query,scope,previous,next_clicks,state,geoid,page):
    query=query if isinstance(query,str) and len(query)<=120 else ''
    page=page if type(page) is int and 1<=page<=100000 else 1
    trigger=callback_context.triggered_id
    page=max(1,page-1) if trigger=='library-newspaper-previous' else page+1 if trigger=='library-newspaper-next' else 1
    place=get_place(geoid,state)
    if scope in ('state','town') and not state or scope=='town' and not place:
        return [],'Choose a state or town in the place controls, or browse All indexed titles.',1,'',True,True
    try:
        found=search_titles(state=state if scope in ('state','town') else '',
                            town=census_town(place['name']) if scope=='town' and place else '',query=query,page=page)
    except (ValueError,OSError,sqlite3.Error) as exc:
        message=str(exc) if isinstance(exc,ValueError) else 'The local newspaper catalog is unavailable. Other reference tools remain available.'
        return [],message,1,'',True,True
    label='All indexed U.S. titles' if found['scope']=='national' else f"{place['name']}, {state}" if found['scope']=='town' and place else f'State catalog · {state}'
    if scope=='town' and not found['exact_town']:
        label=f'No exact town-name match in this snapshot · Showing {state} state titles'
    if found.get('snapshot_complete') is False:
        label+=f" · Partial LOC snapshot ({found.get('source_pages_observed',0)}/{found.get('source_pages_expected',0)} pages)"
    cards=[html.Button([html.Strong(row['title']),html.Small(' · '.join(v for v in (row.get('publication_dates',''),row.get('languages','')) if v))],
                       id={'type':'library-newspaper-open','index':row['id']},n_clicks=0,className='clovis-library-record') for row in found['rows']]
    if not cards:
        cards=[html.P('No titles match. Try a shorter title, another language or wider coverage.',className='atlas-help')]
    return cards,f"{label} · {found['total']:,} title records",found['page'],f"{found['page']:,} / {max(1,found['pages']):,}",found['page']<=1,found['page']>=found['pages']


@callback(Output('library-newspaper-selected','data'),Input({'type':'library-newspaper-open','index':ALL},'n_clicks'),
          Input('library-newspaper-query','value'),Input('library-newspaper-scope','value'),
          Input('library-newspaper-previous','n_clicks'),Input('library-newspaper-next','n_clicks'),
          Input('resident-state','value'),Input('resident-place','value'),prevent_initial_call=True)
def select(clicks,*inputs):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict):
        return None
    if not isinstance(clicks,list) or len(clicks)>24 or any(type(n) is not int or n<0 for n in clicks) or not any(clicks):
        return no_update
    row=get_title(trigger.get('index'))
    return row['id'] if row else no_update


@callback(Output('library-newspaper-detail','children'),Input('library-newspaper-selected','data'))
def read(selected):
    if not isinstance(selected,str) or len(selected)>20:
        return html.P('Select a title to read its publication timeline and catalog facts.')
    row=get_title(selected)
    if not row:
        return html.P('Choose a title from the current catalog.')
    detail=[]
    for label,value in facts(row):
        detail.extend([html.Dt(label),html.Dd(value)])
    source=_url(row.get('url'),{'www.loc.gov','loc.gov'})
    children=[reading_nav('library-newspaper-query'),html.H3(row['title']),html.Dl(detail,className='clovis-library-facts')]
    if source:
        children.append(html.A('LOC title and holdings record',href=source,target='_blank',rel='noopener noreferrer'))
    children.extend([html.Button('Save title reference to fieldbook',id='library-newspaper-save',n_clicks=0,className='atlas-primary-button'),
                     html.Div(id='library-newspaper-save-status',role='status',className='atlas-help'),
                     html.Button('Open fieldbook →',id={'type':'workbench-action','target':'notebook','key':'newspaper-reference'},n_clicks=0,className='atlas-secondary-button'),
                     html.P('Publication dates describe the newspaper title. This partial catalog contains no article text; missing titles may be on unharvested pages.',className='atlas-help')])
    return children


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-newspaper-save-status','children'),
          Input('library-newspaper-save','n_clicks'),State('library-newspaper-selected','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks,selected,book):
    if not clicks or not isinstance(selected,str) or len(selected)>20:
        return no_update,no_update
    row=get_title(selected)
    if not row:
        return no_update,'Choose a title from the current catalog.'
    try:
        return merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(row)]),'Newspaper title reference saved with its source.'
    except (ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
