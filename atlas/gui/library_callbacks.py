"""Read authoritative local reference records; no client-supplied record text."""
from urllib.parse import urlsplit
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, html, no_update

from core.reference_catalog import catalog_stats, search_objects, get_object, facts, collection_key, MET_GROUPS, SI_GROUPS
from core.state_fossil_library import state_reading
from core.reference_media import museum_image
from core.reference_notes import reference_entry
from core.fieldbook import EMPTY_BOOK, merge_entries
from core.us_places import STATE_NAMES
from atlas.gui.library_ui import reading_nav


def _url(value, hosts):
    if not isinstance(value,str) or len(value)>2000 or any(ord(c)<32 for c in value):
        return ''
    try:
        parsed=urlsplit(value)
        return value if (parsed.scheme=='https' and parsed.hostname in hosts and not parsed.username
                         and not parsed.password and parsed.port in (None,443)) else ''
    except ValueError:
        return ''


@callback(Output('library-object-material','options'),Output('library-object-material','value'),
          Output('library-object-era','disabled'),Output('library-object-group-label','children'),
          Input('library-object-collection','value'))
def collection_filters(collection):
    si=collection_key(collection)=='si'
    groups=SI_GROUPS if si else MET_GROUPS
    return [{'label':label,'value':key} for key,label in groups.items()],'all',si,'Source text tags' if si else 'Object group'


@callback(Output('library-objects','style'),Output('library-states','style'),Output('library-fossils','style'),Output('library-newspapers','style'),Output('library-units','style'),Output('library-guides','style'),Output('library-projects','style'),Output('library-minerals','style'),Output('library-radiocarbon','style'),Output('library-data-packs','style'),Output('library-dinosaurs','style'),Input('library-section','value'))
def library_section(section):
    show,hide={}, {'display':'none'}
    keys = ('objects','states','fossils','newspapers','units','guides','projects','minerals','radiocarbon','packs','dinosaurs')
    section = section if section in keys else 'objects'
    return tuple(show if section == key else hide for key in keys)


@callback(Output('library-section','value'),Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'),prevent_initial_call=True)
def open_state_chapter(clicks):
    trigger=callback_context.triggered_id
    destination={'state-chapter':'states','town-newspapers':'newspapers','town-units':'units','object-guides':'guides'}
    return destination.get(trigger.get('key'),no_update) if isinstance(trigger,dict) and isinstance(clicks,list) and any(type(n) is int and n>0 for n in clicks) else no_update


@callback(Output('library-state','value'), Input('resident-state','value'))
def follow_selected_state(state):
    return state if isinstance(state,str) and state in STATE_NAMES else no_update


@callback(Output('library-state-reading','children'), Input('library-state','value'))
def read_state(state):
    if not isinstance(state,str) or state not in STATE_NAMES:
        return html.P('Choose a state for its fossil groups, geological setting and recorded examples.',className='atlas-help')
    reading=state_reading(state)
    if not isinstance(reading,dict):
        return html.P('This state chapter is not in this snapshot.',className='atlas-help')
    cards=[]
    for fact in reading.get('facts',[])[:8]:
        links=[]
        for source in fact.get('sources',[])[:5]:
            url=source.get('url','')
            # These URLs come from the authored chapter, never an imported note.
            try:
                parsed=urlsplit(url)
                safe=parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port in (None,443)
            except (ValueError,TypeError):
                safe=False
            if safe:
                links.extend([html.A(source.get('title','Source'),href=url,target='_blank',rel='noopener noreferrer'),html.Span(' · ')])
        cards.append(html.Article([html.P(fact.get('text','')),html.Div(links[:-1])],className='clovis-library-fact'))
    return [html.H3(reading.get('title',STATE_NAMES[state])),*cards,
            html.P('Statewide learning context · Sources reviewed '+reading.get('reviewed',''),className='atlas-help')]


@callback(Output('library-object-cards','children'),Output('library-object-count','children'),
          Output('library-object-page','data'),Output('library-object-page-label','children'),
          Output('library-object-previous','disabled'),Output('library-object-next','disabled'),
          Output('library-object-source','children'),
          Input('library-object-query','value'),Input('library-object-material','value'),
          Input('library-object-previous','n_clicks'),Input('library-object-next','n_clicks'),Input('library-object-era','value'),Input('library-object-collection','value'),
          State('library-object-page','data'))
def object_results(query,category,previous,next_clicks,era,collection,page):
    query=query if isinstance(query,str) and len(query)<=120 else ''
    collection=collection_key(collection)
    categories=SI_GROUPS if collection=='si' else MET_GROUPS
    category=category if isinstance(category,str) and category in categories else 'all'
    page=page if type(page) is int and 1<=page<=100000 else 1
    trigger=callback_context.triggered_id
    page=max(1,page-1) if trigger=='library-object-previous' else page+1 if trigger=='library-object-next' else 1
    result=search_objects(collection=collection,query=query,category=category,page=page,era=era if isinstance(era,str) else 'historic')
    rows=result['rows']
    cards=[html.Button([
        html.Strong(row['title']),
        html.Small(' · '.join(value for value in (row.get('date',''),row.get('material','') or row.get('object_type','')) if value)),
    ],id={'type':'library-object-open','index':row['id']},n_clicks=0,className='clovis-library-record') for row in rows]
    if not cards:
        cards=[html.P('No records match these filters. Try a shorter term or another group.',className='atlas-help')]
    stats=catalog_stats(collection)
    label=f"{result['total']:,} matching reference objects"
    institution='Smithsonian' if collection=='si' else 'Met'
    source=f"{stats['distinct_records']:,} distinct {institution} records · CC0 metadata · Snapshot {stats.get('snapshot_date','')}"
    if collection=='si':
        source+=' · Text tags come from titles and object types. This snapshot has no explicit object dates or reference images.'
    return cards,label,result['page'],f"{result['page']:,} / {result['pages']:,}",result['page']<=1,result['page']>=result['pages'],source


@callback(Output('library-object-selected','data'),
          Input({'type':'library-object-open','index':ALL},'n_clicks'),
          Input('library-object-query','value'),Input('library-object-material','value'),
          Input('library-object-previous','n_clicks'),Input('library-object-next','n_clicks'),
          Input('library-object-era','value'),Input('library-object-collection','value'), prevent_initial_call=True)
def choose_object(clicks,query,category,previous,next_clicks,era,collection):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict):
        return None
    if not isinstance(clicks,list) or len(clicks)>24 or any(type(n) is not int or n<0 for n in clicks) or not any(clicks):
        return no_update
    record=get_object(trigger.get('index'))
    return record['id'] if record and record['id'].startswith(collection_key(collection)+':') else no_update


@callback(Output('library-object-detail','children'),Input('library-object-selected','data'))
def read_object(selected):
    if not isinstance(selected,str) or len(selected)>123:
        return html.P('Choose a record to read its materials, date and dimensions. These are museum reference objects, not records of finds at your town.')
    row=get_object(selected)
    if not row:
        return html.P('Choose a record from the current collection.')
    detail_facts=[]
    for label,value in facts(row):
        detail_facts.extend([html.Dt(label),html.Dd(value)])
    children=[reading_nav('library-object-query'),html.H3(row['title'])]
    if row.get('is_public_domain') is True:
        children.extend([html.Button('Load reference photograph',id={'type':'library-object-image-open','index':row['id']},n_clicks=0,className='atlas-secondary-button'),
                         html.Div(id={'type':'library-object-image','index':row['id']},**{'data-library-image':'museum'})])
    children.append(html.Dl(detail_facts,className='clovis-library-facts'))
    url=_url(row.get('source_url'),{'www.metmuseum.org','metmuseum.org','n2t.net','collections.si.edu','www.si.edu','si.edu'})
    if url:
        children.append(html.A('Museum source record',href=url,target='_blank',rel='noopener noreferrer'))
    children.extend([
        html.Button('Save reference to fieldbook',id='library-object-save',n_clicks=0,className='atlas-primary-button'),
        html.Div(id='library-object-save-status',role='status',className='atlas-help'),
        html.Button('Open fieldbook →',id={'type':'workbench-action','target':'notebook','key':'library-reference'},n_clicks=0,className='atlas-secondary-button'),
        html.P('Catalog dates describe this museum object; resemblance does not date your own find.',className='atlas-help')])
    return children


@callback(Output({'type':'library-object-image','index':MATCH},'children'),Input({'type':'library-object-image-open','index':MATCH},'n_clicks'),
          State({'type':'library-object-image-open','index':MATCH},'id'), prevent_initial_call=True)
def show_object_image(clicks,button):
    selected=button.get('index') if isinstance(button,dict) else None
    if not clicks or not isinstance(selected,str) or len(selected)>123:
        return no_update
    row=get_object(selected)
    if not row:
        return no_update
    image,status=museum_image(row)
    return [html.Img(src=image,alt=row['title']+' · museum reference photograph',className='clovis-library-image',referrerPolicy='no-referrer'),
            html.Small(status)] if image else html.P(status,role='status',className='atlas-help')


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-object-save-status','children'),
          Input('library-object-save','n_clicks'),State('library-object-selected','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def save_reference(clicks,selected,book):
    if not clicks or not isinstance(selected,str) or len(selected)>123:
        return no_update,no_update
    record=get_object(selected)
    if not record:
        return no_update,'Choose a reference from the library.'
    try:
        merged=merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(record)])
        return merged,'Reference saved with its source. Your observations remain separate.'
    except (ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
