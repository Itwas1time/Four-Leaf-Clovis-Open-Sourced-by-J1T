"""Read offline USGS unit facts and preserve their exact source context."""
from atlas.gui.library_activation import require_section
from urllib.parse import urlsplit
from dash import ALL,Input,Output,State,callback,callback_context,html,no_update
from core.usgs_unit_library import search_units,units_for_place,get_unit
from core.us_places import get_place,STATE_NAMES
from core.usgs_notes import facts,reference_entry
from core.fieldbook import EMPTY_BOOK,merge_entries
from atlas.gui.library_ui import reading_nav


def _record(selected,state,geoid):
    if not isinstance(selected,dict) or set(selected)!={'id','geoid'}:
        return None,None
    if selected['geoid']:
        place=get_place(geoid,state)
        if not place or selected['geoid']!=geoid:
            return None,None
        return next((row for row in units_for_place(geoid) if row['id']==selected['id']),None),place
    return get_unit(selected['id']),None


def _citation(citation):
    text=citation.get('text','')
    url=citation.get('url','')
    try:
        p=urlsplit(url)
        safe=isinstance(url,str) and len(url)<=2000 and p.scheme=='https' and p.hostname and not p.username and not p.password and p.port in (None,443) and not any(ord(c)<32 for c in url)
    except (ValueError,TypeError):
        safe=False
    return html.P([html.Span(text),html.A(' Source',href=url,target='_blank',rel='noopener noreferrer') if safe else None],className='atlas-help')


@callback(Output('library-unit-cards','children'),Output('library-unit-count','children'),
          Output('library-unit-page','data'),Output('library-unit-page-label','children'),
          Output('library-unit-previous','disabled'),Output('library-unit-next','disabled'),
          Input('library-unit-query','value'),Input('library-unit-scope','value'),
          Input('library-unit-previous','n_clicks'),Input('library-unit-next','n_clicks'),
          Input('resident-state','value'),Input('resident-place','value'),State('library-unit-page','data'), Input("library-section", "value"))
def results(query,scope,previous,next_clicks,state,geoid,page, section="units"):
    require_section(section, "units")
    query=query if isinstance(query,str) and len(query)<=120 else ''
    page=page if type(page) is int and 1<=page<=10000 else 1
    trigger=callback_context.triggered_id
    page=max(1,page-1) if trigger=='library-unit-previous' else page+1 if trigger=='library-unit-next' else 1
    place=get_place(geoid,state)
    if scope=='town':
        if not place:
            return [],'Choose a town in the place controls, or browse All national units.',1,'',True,True
        rows=units_for_place(geoid)
        if query:
            needle=query.casefold()
            rows=[row for row in rows if needle in ' '.join(str(v) for v in row.values()).casefold()]
        label=f"{place['name']}, {state} · {len(rows)} mapped units across separate themes"
        total=len(rows)
        page,pages=1,1
    else:
        if scope=='state' and state not in STATE_NAMES:
            return [],'Choose a state in the place controls, or browse All national units.',1,'',True,True
        found=search_units(state=state if scope=='state' else '',query=query,page=page)
        rows,total,page,pages=(found[k] for k in ('rows','total','page','pages'))
        label=f"{STATE_NAMES[state]} · Units mapped at its Census points" if scope=='state' else 'National unit catalog'
        label+=f' · {total:,} units'
    cards=[html.Button([html.Strong(row['name']),html.Small(' · '.join(v for v in (row.get('layer_label',''),row.get('age',''),row.get('geomaterial','')) if v))],
                       id={'type':'library-unit-open','index':row['id']},n_clicks=0,className='clovis-library-record') for row in rows]
    if not cards:
        cards=[html.P('No units match this search in the selected scope. Try another material, geological age or wider coverage.',className='atlas-help')]
    return cards,label,page,f'{page:,} / {pages:,}',page<=1,page>=pages


@callback(Output('library-unit-selected','data'),Input({'type':'library-unit-open','index':ALL},'n_clicks'),
          Input('library-unit-query','value'),Input('library-unit-scope','value'),
          Input('library-unit-previous','n_clicks'),Input('library-unit-next','n_clicks'),
          Input('resident-state','value'),Input('resident-place','value'),prevent_initial_call=True)
def select(clicks,query,scope,previous,next_clicks,state,geoid):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict):
        return None
    if not isinstance(clicks,list) or len(clicks)>24 or any(type(n) is not int or n<0 for n in clicks) or not any(clicks):
        return no_update
    selected={'id':trigger.get('index'),'geoid':geoid if scope=='town' else None}
    row,_=_record(selected,state,geoid)
    return selected if row else no_update


@callback(Output('library-unit-detail','children'),Input('library-unit-selected','data'),
          Input('resident-state','value'),Input('resident-place','value'))
def read(selected,state,geoid):
    row,place=_record(selected,state,geoid)
    if not row:
        return html.P('Choose a mapped unit to read its description, age and source-map facts.')
    detail=[]
    for label,value in facts(row):
        detail.extend([html.Dt(label),html.Dd(value)])
    children=[reading_nav('library-unit-query'),html.H3(row['name']),html.P(f"Mapped at {place['name']}, {state}'s public town point" if place else 'National synthesis unit · Source units may describe different places',className='atlas-help'),
              html.Dl(detail,className='clovis-library-facts')]
    sources=row.get('source_units',[])
    if sources:
        children.append(html.H4(f'Recorded source-map units ({len(sources)})'))
        for source in sources:
            children.append(html.Details([html.Summary(source.get('source_name') or source.get('source_mapunit') or 'Source-map unit'),
                html.P(' · '.join(v for v in (source.get('source_mapunit',''),source.get('source_age',''),source.get('geomaterial','')) if v),className='atlas-help'),
                html.P(source.get('source_description','') or (
                    'The USGS source table does not provide a description for this mapped source code.'
                    if not source.get('source_name') and not source.get('source_full_name') else '')),
                *[_citation(c) for c in source.get('source_citations',[])[:20]]]))
        if row.get('source_units_truncated'):
            children.append(html.P('Showing the first 100 source units for this national unit. Town scope narrows this to its mapped source units.',className='atlas-help'))
    children.extend([_citation(c) for c in row.get('source_citations',[])[:20]])
    children.extend([html.A('USGS national map and release',href='https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm',target='_blank',rel='noopener noreferrer'),
                     html.Button('Save geology reference to fieldbook',id='library-unit-save',n_clicks=0,className='atlas-primary-button'),
                     html.Div(id='library-unit-save-status',role='status',className='atlas-help'),
                     html.Button('Open fieldbook →',id={'type':'workbench-action','target':'notebook','key':'unit-reference'},n_clicks=0,className='atlas-secondary-button')])
    return children


@callback(Output('library-unit-scope','value'),Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'),prevent_initial_call=True)
def town_scope(clicks):
    trigger=callback_context.triggered_id
    return 'town' if isinstance(trigger,dict) and trigger.get('key')=='town-units' and any(clicks or []) else no_update


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-unit-save-status','children'),
          Input('library-unit-save','n_clicks'),State('library-unit-selected','data'),
          State('resident-state','value'),State('resident-place','value'),State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks,selected,state,geoid,book):
    if not clicks:
        return no_update,no_update
    row,place=_record(selected,state,geoid)
    if not row:
        return no_update,'Choose a current mapped unit from the library.'
    try:
        return merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(row,place)]),'Regional geology saved with its source citations.'
    except (ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
