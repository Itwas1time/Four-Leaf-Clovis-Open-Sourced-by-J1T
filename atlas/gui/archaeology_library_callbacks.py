"""Search and cite archaeology project publications from bundled source data."""
import math
import sqlite3

from dash import ALL, Input, Output, State, callback, callback_context, html, no_update

from atlas.gui.library_ui import reading_nav
from core.archaeology_project_catalog import PAGE_SIZE, catalog_stats, search_projects, get_project, facts, project_entry
from core.fieldbook import EMPTY_BOOK, merge_entries


@callback(Output('library-project-country','options'), Output('library-project-coverage','children'),
          Input('library-section','value'))
def project_coverage(section):
    if section != 'projects':
        return no_update, no_update
    try:
        summary = catalog_stats()
        options = [{'label':'All country contexts','value':'all'},
                   *[{'label':name,'value':name} for name in summary['countries']],
                   {'label':'Country context not recorded','value':'unrecorded'}]
        retrieved = summary['retrieved'][:10]
        coverage = (f"{summary['records']:,} publications · Open Context · snapshot {retrieved}. "
                    f"Source query checked: {summary['source_records_observed']:,} of {summary['source_records_expected']:,} records. "
                    + summary['coverage_note'])
        if summary['excluded_license_records']:
            excluded = len(summary['excluded_license_records'])
            coverage += f" {excluded} {'record' if excluded == 1 else 'records'} excluded because the reuse license was not supported."
        return options, coverage
    except (OSError, ValueError, sqlite3.Error):
        return [{'label':'All country contexts','value':'all'}], 'This installation has no readable archaeology publication catalog.'


@callback(Output('library-project-cards','children'), Output('library-project-count','children'),
          Output('library-project-page','data'), Output('library-project-page-label','children'),
          Output('library-project-previous','disabled'), Output('library-project-next','disabled'),
          Input('library-project-query','value'), Input('library-project-country','value'),
          Input('library-project-previous','n_clicks'), Input('library-project-next','n_clicks'),
          State('library-project-page','data'))
def project_results(query, country, previous, next_clicks, page):
    trigger = callback_context.triggered_id
    page = page if type(page) is int and page > 0 else 1
    if trigger == 'library-project-previous':
        page = max(1, page - 1)
    elif trigger == 'library-project-next':
        page += 1
    else:
        page = 1
    try:
        rows, total, page = search_projects(query or '', country or 'all', page)
    except (OSError, ValueError, sqlite3.Error):
        return [], 'The publication search could not run. Check the catalog installation and search input.', 1, '', True, True
    cards = [html.Button([
        html.Strong(row['title']),
        html.Small((row['country'] or 'Country context not recorded') + ' · Published ' + (row['published'] or 'date not recorded')),
        html.Small('; '.join(row['subjects']) or 'Data publication'),
    ], id={'type':'library-project-open','index':row['id']}, n_clicks=0,
        className='clovis-library-record') for row in rows]
    last = max(1, math.ceil(total / PAGE_SIZE))
    count = f'{total:,} matching publications in this snapshot.'
    if not rows:
        cards = html.P('No matching publication in this snapshot. Try another term or country. Missing results do not establish that a dig or study never existed.', className='atlas-help')
    return cards, count, page, f'{page} / {last}', page <= 1, page >= last


@callback(Output('library-project-selected','data'),
          Input({'type':'library-project-open','index':ALL},'n_clicks'),
          Input('library-project-query','value'), Input('library-project-country','value'),
          Input('library-project-page','data'), prevent_initial_call=True)
def select_project(clicks, query, country, page):
    trigger = callback_context.triggered_id
    if isinstance(trigger, dict) and isinstance(clicks, list) and any(type(n) is int and n > 0 for n in clicks):
        identifier = trigger.get('index')
        return {'id':identifier,'query':query or '', 'country':country or 'all', 'page':page} if get_project(identifier) else None
    if isinstance(trigger, str):
        return None
    return no_update


def current_project(selection, query, country, page):
    if (not isinstance(selection,dict) or set(selection) != {'id','query','country','page'} or
            selection['query'] != (query or '') or selection['country'] != (country or 'all') or
            selection['page'] != page):
        return None
    rows, _, _ = search_projects(query or '', country or 'all', page)
    return next((row for row in rows if row['id'] == selection['id']), None)


@callback(Output('library-project-detail','children'), Input('library-project-selected','data'),
          Input('library-project-query','value'), Input('library-project-country','value'), Input('library-project-page','data'))
def read_project(selection, query, country, page):
    try:
        record = current_project(selection, query, country, page)
    except (OSError, ValueError, sqlite3.Error):
        record = None
    if not record:
        return html.P('Choose a publication to read its source metadata.')
    facts_list = []
    for label, value in facts(record):
        facts_list.extend([html.Dt(label), html.Dd(value)])
    children = [reading_nav('library-project-query'), html.H3(record['title']),
                html.Dl(facts_list, className='clovis-library-facts')]
    if record['description']:
        children += [html.H4('Source description'), html.P(record['description'])]
    elif record['description_withheld']:
        children += [html.P('The source description contains location details. Read it at the publisher.', className='atlas-help')]
    else:
        children += [html.P('No short source description is recorded.', className='atlas-help')]
    children += [html.P('The time span describes the dataset’s archaeological coverage. Publication and modification dates describe this record. Current fieldwork and participation availability are not established.', className='atlas-help'),
                 html.Div([html.A('Open published project & data', href=record['source_url'], target='_blank', rel='noopener noreferrer'),
                           html.A('Metadata license', href=record['license_url'], target='_blank', rel='noopener noreferrer')], className='clovis-guide-citations')]
    if record['citation_url']:
        children.append(html.A('Citation identifier (DOI)', href=record['citation_url'], target='_blank', rel='noopener noreferrer'))
    children += [html.P('Source metadata selected and rendered as plain text by Clovis. These fields retain the linked metadata license.', className='atlas-help'),
                 html.Button('Save publication to fieldbook', id='library-project-save', n_clicks=0, className='atlas-primary-button'),
                 html.P(id='library-project-save-status', role='status', className='atlas-help')]
    return children


@callback(Output('fieldbook-store','data',allow_duplicate=True), Output('library-project-save-status','children'),
          Input('library-project-save','n_clicks'), State('library-project-selected','data'),
          State('fieldbook-store','data'), State('library-project-query','value'),
          State('library-project-country','value'), State('library-project-page','data'), prevent_initial_call=True)
def save_project(clicks, selection, book, query, country, page):
    if not clicks:
        return no_update, no_update
    try:
        record = current_project(selection, query, country, page)
        if not record:
            raise ValueError('Choose a publication in the current search.')
        entry = project_entry(record['id'])
        updated = merge_entries(book or EMPTY_BOOK, [entry])
        return updated, 'Publication saved. Open Fieldbook to read, compare or export its source.'
    except (OSError, ValueError, sqlite3.Error):
        return no_update, 'This publication could not be saved. Check the selected record and fieldbook capacity.'
