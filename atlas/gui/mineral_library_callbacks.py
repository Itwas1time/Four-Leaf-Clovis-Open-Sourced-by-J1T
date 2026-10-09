"""Read canonical mineral records and save only the current search selection."""
from atlas.gui.library_activation import require_section
import sqlite3
from urllib.parse import urlsplit
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update

from core import mineral_property_catalog as catalog
from core.fieldbook import EMPTY_BOOK, merge_entries
from core.mineral_notes import MAX_PROPERTIES, property_notes, reference_entry, value_text
from atlas.gui.library_ui import reading_nav


def source_link(value, label):
    try:
        parsed = urlsplit(value)
        safe = (isinstance(value,str) and len(value) <= 2000 and parsed.scheme == 'https' and parsed.hostname
                and not parsed.username and not parsed.password and parsed.port in (None,443)
                and not any(ord(c) < 32 for c in value))
    except (ValueError,TypeError):
        safe = False
    return html.A(label,href=value,target='_blank',rel='noopener noreferrer') if safe else html.Span(label+' · Link unavailable')


@callback(Output('library-mineral-cards','children'),Output('library-mineral-count','children'),
          Output('library-mineral-page','data'),Output('library-mineral-page-label','children'),
          Output('library-mineral-previous','disabled'),Output('library-mineral-next','disabled'),
          Output('library-mineral-coverage','children'),Input('library-mineral-query','value'),
          Input('library-mineral-previous','n_clicks'),Input('library-mineral-next','n_clicks'),State('library-mineral-page','data'), Input("library-section", "value"))
def results(query, previous, next_clicks, page, section="minerals"):
    require_section(section, "minerals")
    page = page if type(page) is int and 1 <= page <= 10000 else 1
    trigger = callback_context.triggered_id
    page = max(1,page-1) if trigger == 'library-mineral-previous' else page+1 if trigger == 'library-mineral-next' else 1
    query = query if isinstance(query,str) and len(query) <= 160 else ''
    try:
        stats = catalog.catalog_stats()
        found = catalog.search_minerals(query,page)
    except (OSError,sqlite3.Error):
        return [],'The mineral catalog is unavailable.',1,'',True,True,''
    cards = [html.Button([html.Strong(row['name']),html.Small(' · '.join(value for value in (row['kind'],row['formula']) if value))],
                         id={'type':'library-mineral-open','index':row['id']},n_clicks=0,className='clovis-library-record') for row in found['rows']]
    if not cards:
        cards = [html.P('No mineral records match this search. Try a name, formula or property.',className='atlas-help')]
    coverage = (f"{stats['distinct_records']:,} mineral records · {stats['fact_count']:,} source statements · Wikidata snapshot {stats['snapshot_date']}. "
                'Source values, units and qualifiers are retained. This is a reference catalog; local specimens are not identified.')
    return cards,f"{found['total']:,} matching records",found['page'],f"{found['page']:,} / {found['pages']:,}",found['page']<=1,found['page']>=found['pages'],coverage


@callback(Output('library-mineral-selected','data'),Input({'type':'library-mineral-open','index':ALL},'n_clicks'),
          Input('library-mineral-query','value'),Input('library-mineral-page','data'),prevent_initial_call=True)
def select(clicks, query, page):
    trigger = callback_context.triggered_id
    if isinstance(trigger,dict) and isinstance(clicks,list) and any(type(value) is int and value > 0 for value in clicks):
        return {'id':trigger.get('index'),'query':query or '', 'page':page}
    return None if isinstance(trigger,str) else no_update


def current_record(selected, query, page):
    if (not isinstance(query,str) or len(query) > 160 or type(page) is not int or not 1 <= page <= 10000
            or not isinstance(selected,dict) or set(selected) != {'id','query','page'}
            or selected['query'] != (query or '') or selected['page'] != page):
        return None
    rows = catalog.search_minerals(query or '',page)['rows']
    identifier = next((row['id'] for row in rows if row['id'] == selected['id']),None)
    return catalog.get_mineral(identifier) if identifier else None


@callback(Output('library-mineral-detail','children'),Input('library-mineral-selected','data'),
          Input('library-mineral-query','value'),Input('library-mineral-page','data'))
def read(selected, query, page):
    try:
        record = current_record(selected,query,page)
    except (OSError,sqlite3.Error,ValueError,TypeError):
        record = None
    if record is None:
        return html.P('Choose a mineral to read its recorded properties and sources.')
    children = [reading_nav('library-mineral-query'),html.H3(record['name']),
                html.P(record['kind'],className='atlas-help')]
    for fact in record['properties'][:MAX_PROPERTIES]:
        details = [html.H4(fact['name']),html.P(value_text(fact))]
        notes = property_notes(fact)
        if notes:
            details.append(html.Dl([node for label,value in notes for node in (html.Dt(label),html.Dd(value))],className='clovis-library-facts'))
        details.append(source_link(record['source_url']+'#'+fact['property_id'],'Wikidata statement'))
        if fact['source_url'] != record['source_url']+'#'+fact['property_id']:
            details.append(source_link(fact['source_url'],'Recorded source'))
        if fact['sources']:
            details.append(html.Details([html.Summary('Recorded references'),
                *[html.P(source['name']+': '+value_text(source)) for source in fact['sources']]]))
        children.append(html.Section(details,className='clovis-mineral-property'))
    if len(record['properties']) > MAX_PROPERTIES:
        children.append(html.P(f'Showing the first {MAX_PROPERTIES} of {len(record["properties"])} statements. The source retains the complete record.',className='atlas-help'))
    children.extend([source_link(record['source_url'],'Open Wikidata mineral record'),
        html.P(record['license']+' · Values and units have not been converted.',className='atlas-help'),
        html.Button('Save mineral reference to fieldbook',id='library-mineral-save',n_clicks=0,className='atlas-primary-button'),
        html.Div(id='library-mineral-save-status',className='atlas-help',role='status')])
    return children


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-mineral-save-status','children'),
          Input('library-mineral-save','n_clicks'),State('library-mineral-selected','data'),State('library-mineral-query','value'),
          State('library-mineral-page','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks, selected, query, page, book):
    if not clicks:
        return no_update,no_update
    try:
        record = current_record(selected,query,page)
        if record is None:
            return no_update,'Choose a record from the current mineral search.'
        return merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(record['id'])]),'Mineral reference saved with its source statements.'
    except (OSError,sqlite3.Error,ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
