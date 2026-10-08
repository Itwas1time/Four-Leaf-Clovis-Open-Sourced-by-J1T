"""Local notebook actions resolve saved records by project and stable ID."""
import base64
import binascii
import sqlite3
import time
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html, no_update
from core.dig_records import DigBook, KINDS, COMMON, EXTRA, MAX_BACKUP_ZIP_BYTES

FIELDS = ('kind', 'code', 'unit', 'context', 'context-type', 'description', 'interpretation',
          'recorder', 'date', 'material', 'count', 'bag', 'sample-type', 'method',
          'depth', 'depth-unit', 'datum', 'citation', 'url', 'sources')
KEYS = ('kind', 'code', 'unit_id', 'context_id', 'context_type', 'description', 'interpretation',
        'recorder', 'observed_date', 'material', 'count', 'bag', 'sample_type', 'method',
        'depth', 'depth_unit', 'datum', 'citation', 'url', 'source_ids')


def _message(error):
    return str(error) if isinstance(error, ValueError) else 'The local record could not be saved. Check the project and try again.'


@callback(Output('fieldbook-reading-controls', 'style'), Output('fieldbook-reading-workspace', 'style'),
          Output('fieldbook-reading-inspector', 'style'), Output('dig-workspace', 'style'),
          Output('dig-inspector', 'style'), Output('dig-controls-help', 'style'), Input('fieldbook-section', 'value'))
def notebook_section(section):
    show, hide = {}, {'display': 'none'}
    return (hide, hide, hide, show, show, show) if section == 'dig' else (show, show, show, hide, hide, hide)


@callback(Output('dig-project', 'options'), Output('dig-project', 'value'),
          Input('dig-refresh', 'data'), Input('dig-project-request', 'data'), State('dig-project', 'value'))
def project_options(_refresh, requested, selected):
    try:
        options = [{'label': row['code'] + ' · ' + row['title'], 'value': row['id']} for row in DigBook().projects()]
        known = {row['value'] for row in options}
        changed = any(item['prop_id'] == 'dig-project-request.data' for item in callback_context.triggered)
        selected = requested if changed else selected
        return options, selected if isinstance(selected, str) and selected in known else None
    except (ValueError, OSError, sqlite3.Error):
        return [], None


@callback(Output('dig-refresh', 'data'), Output('dig-status', 'children'), Output('dig-project-request', 'data'),
          Input('dig-project-create', 'n_clicks'), Input('dig-import', 'contents'),
          State('dig-project-code', 'value'), State('dig-project-title', 'value'), prevent_initial_call=True)
def create_or_restore(_clicks, contents, code, title):
    try:
        book = DigBook()
        if callback_context.triggered_id == 'dig-project-create':
            project = book.create_project(code, title)
            message = 'Project created. Add the units and contexts recorded by your project.'
            identifier = project['id']
        else:
            if not isinstance(contents, str) or len(contents) > 1_600_100:
                raise ValueError('Choose a dig-record ZIP backup of up to 1.2 MB.')
            _, encoded = contents.split(',', 1)
            data = base64.b64decode(encoded, validate=True)
            if len(data) > MAX_BACKUP_ZIP_BYTES:
                raise ValueError('The project backup is too large.')
            result = book.restore_backup(data)
            identifier = result['project_id']
            message = f"Restored {result['added']} new records and {result['advanced']} later revisions. Matching records were kept once."
        return time.time_ns(), message, identifier
    except (ValueError, OSError, sqlite3.Error, binascii.Error) as error:
        return no_update, _message(error), no_update


@callback(Output('dig-record-list', 'children'), Output('dig-record-count', 'children'), Output('dig-page', 'data'),
          Output('dig-page-label', 'children'), Output('dig-prev', 'disabled'), Output('dig-next', 'disabled'),
          Input('dig-project', 'value'), Input('dig-query', 'value'), Input('dig-refresh', 'data'),
          Input('dig-prev', 'n_clicks'), Input('dig-next', 'n_clicks'), State('dig-page', 'data'))
def record_list(project, query, _refresh, _previous, _next, page):
    try:
        if not project:
            return [], 'Choose or create a local project.', 1, '', True, True
        page = page if type(page) is int and page >= 1 else 1
        trigger = callback_context.triggered_id
        page = max(1, page - 1) if trigger == 'dig-prev' else page + 1 if trigger == 'dig-next' else 1
        result = DigBook().records(project, query=query or '', page=page)
        cards = [html.Button([html.Strong(row['data']['code']),
                             html.Small(f"{KINDS[row['data']['kind']]} · revision {row['revision']}"),
                             html.Small(row['data']['description'][:120])],
                            id={'type': 'dig-record-open', 'index': row['id']}, n_clicks=0,
                            className='clovis-library-record') for row in result['rows']]
        return cards or html.P('No records match this search.'), f"{result['total']} matching records", result['page'], f"{result['page']} of {result['pages']}", result['page'] <= 1, result['page'] >= result['pages']
    except (ValueError, OSError, sqlite3.Error) as error:
        return [], _message(error), 1, '', True, True


@callback(Output('dig-selection', 'data'), Output('dig-edit-label', 'children'),
          *[Output('dig-' + field, 'value') for field in FIELDS],
          Input({'type': 'dig-record-open', 'index': ALL}, 'n_clicks'), Input('dig-project', 'value'),
          Input('dig-new', 'n_clicks'), Input('dig-saved-selection', 'data'))
def open_editor(clicks, project, _new, saved):
    trigger = callback_context.triggered_id
    row = None
    try:
        if isinstance(trigger, dict) and trigger.get('type') == 'dig-record-open':
            if not any(clicks):
                return (no_update,) * (len(FIELDS) + 2)
            row = DigBook().get(project, trigger['index'])
        elif trigger == 'dig-saved-selection' and isinstance(saved, dict) and saved.get('project_id') == project:
            row = DigBook().get(project, saved.get('id'))
    except (ValueError, OSError, sqlite3.Error):
        row = None
    defaults = {**COMMON, **{key: value for fields in EXTRA.values() for key, value in fields.items()}, 'kind': 'unit', 'code': ''}
    data = row['data'] if row else defaults
    selected = {'id': row['id'], 'project_id': project, 'revision': row['revision']} if row else None
    label = f"Editing {data['code']} · revision {row['revision']}. Saving a correction keeps earlier revisions." if row else 'New record. Codes stay linked to stable IDs when corrected.'
    values = [data.get(key, defaults.get(key)) for key in KEYS]
    values[FIELDS.index('depth-unit')] = values[FIELDS.index('depth-unit')] or None
    return selected, label, *values


@callback(Output('dig-refresh', 'data', allow_duplicate=True), Output('dig-status', 'children', allow_duplicate=True),
          Output('dig-saved-selection', 'data'), Input('dig-save', 'n_clicks'), State('dig-project', 'value'),
          State('dig-selection', 'data'), *[State('dig-' + field, 'value') for field in FIELDS], prevent_initial_call=True)
def save_record(_clicks, project, selected, *values):
    try:
        raw = dict(zip(KEYS, values))
        kind = raw.get('kind')
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError('Choose a record type.')
        fields = {'kind', 'code', *COMMON, *EXTRA[kind]}
        value = {key: raw[key] for key in fields}
        if 'depth_unit' in value:
            value['depth_unit'] = value['depth_unit'] or ''
        identifier = revision = None
        if selected is not None:
            if not isinstance(selected, dict) or set(selected) != {'id', 'project_id', 'revision'} or selected['project_id'] != project:
                raise ValueError('Reopen the record in its project before saving.')
            identifier, revision = selected['id'], selected['revision']
        row = DigBook().save(project, value, identifier, revision)
        return time.time_ns(), f"Saved {row['data']['code']} · revision {row['revision']} on this computer.", {'id': row['id'], 'project_id': project, 'revision': row['revision']}
    except (ValueError, OSError, sqlite3.Error) as error:
        return no_update, _message(error), no_update


@callback(*[Output(identifier, 'style') for identifier in ('dig-unit-field', 'dig-context-field', 'dig-context-type-field',
                                                         'dig-find-fields', 'dig-bag-field', 'dig-sample-fields', 'dig-depth-fields', 'dig-source-fields')],
          Input('dig-kind', 'value'))
def record_fields(kind):
    groups = ({'context'}, {'find', 'sample'}, {'context'}, {'find'}, {'find', 'sample'}, {'sample'}, {'context', 'find', 'sample'}, {'source'})
    return tuple({} if isinstance(kind, str) and kind in group else {'display': 'none'} for group in groups)


def register_picker(identifier, kind, multiple=False):
    @callback(Output(identifier, 'options'), Input(identifier, 'search_value'), Input('dig-project', 'value'),
              Input('dig-refresh', 'data'), Input('dig-selection', 'data'), State(identifier, 'value'))
    def options(query, project, _refresh, _selected, value):
        try:
            book = DigBook()
            selected = value if multiple and isinstance(value, list) else [value] if value else []
            rows = book.options(project, kind, query or '', selected[0] if selected else None)
            known = {row['value'] for row in rows}
            for selected_id in selected[:20]:
                if selected_id not in known and project:
                    row = book.get(project, selected_id)
                    if row and row['data']['kind'] == kind:
                        rows.append({'value': selected_id, 'label': row['data']['code']})
            return rows
        except (ValueError, OSError, sqlite3.Error):
            return []
    return options


for _identifier, _kind in (('dig-unit', 'unit'), ('dig-context', 'context'), ('dig-relation-a', 'context'), ('dig-relation-b', 'context')):
    register_picker(_identifier, _kind)
register_picker('dig-sources', 'source', True)


@callback(Output('dig-record-detail', 'children'), Input('dig-selection', 'data'), Input('dig-refresh', 'data'), State('dig-project', 'value'))
def record_detail(selected, _refresh, project):
    try:
        if not isinstance(selected, dict) or selected.get('project_id') != project:
            return html.P('Choose a saved record to read its links and revisions.', className='atlas-help')
        book = DigBook()
        row = book.get(project, selected.get('id'))
        if not row:
            return html.P('This record is not in the selected project.')
        data = row['data']
        facts = []
        for key, value in data.items():
            if key in ('kind', 'code', 'description', 'interpretation', 'source_ids'):
                continue
            if key in ('unit_id', 'context_id'):
                linked = book.get(project, value) if value else None
                value = linked['data']['code'] if linked else 'Unknown / not recorded'
            facts.extend([html.Dt(key.replace('_id', '').replace('_', ' ').title()), html.Dd(str(value) if value is not None and value != '' else 'Not recorded')])
        sources = []
        for identifier in data['source_ids']:
            source = book.get(project, identifier)
            if source:
                source_data = source['data']
                sources.append(html.Div([html.Strong(source_data['code']), html.P(source_data['citation']),
                                         html.A('Open source', href=source_data['url'], target='_blank', rel='noopener noreferrer') if source_data['url'] else None]))
        history = book.history(project, row['id'])
        return [html.H3(data['code'] + ' · ' + KINDS[data['kind']]), html.P(f"Revision {row['revision']} · {row['updated']}", className='atlas-help'),
                html.H4('Observed description'), html.Pre(data['description'] or 'Not recorded'),
                html.H4('Interpretation / uncertainty'), html.Pre(data['interpretation'] or 'Not recorded'), html.Dl(facts),
                html.H4('Supporting source documents'), *(sources or [html.P('Not recorded')]),
                html.Details([html.Summary(f"Revision history · {len(history)} versions"),
                              *[html.Div([html.Strong(f"Revision {item['revision']} · {item['updated']}"),
                                          html.Pre(item['data']['description'] or 'No description'),
                                          html.Pre(item['data']['interpretation'] or 'No interpretation')]) for item in history[-20:]],
                              html.P('The backup retains every field in every revision. This reader shows the latest 20 descriptions and interpretations.', className='atlas-help')]),
                html.P('Stable record ID: ' + row['id'], className='atlas-help')]
    except (ValueError, OSError, sqlite3.Error) as error:
        return html.P(_message(error))


@callback(Output('dig-relations', 'children'), Output('dig-relation-void-id', 'options'), Input('dig-project', 'value'), Input('dig-refresh', 'data'), Input('dig-relation-query', 'value'))
def show_relations(project, _refresh, query):
    try:
        if not project:
            return [], []
        book = DigBook()
        relations = sorted(book.relations(project, query or ''), key=lambda row: row['created'], reverse=True)
        items, options = [], []
        for row in relations[:100]:
            a, b = book.get(project, row['subject']), book.get(project, row['object'])
            label = f"{a['data']['code']} {row['kind'].replace('_', ' ')} {b['data']['code']}"
            items.append(html.P(label + (' · voided: ' + row['void']['reason'] if 'void' in row else '') + (' · ' + row['note'] if row['note'] else '')))
            if 'void' not in row:
                options.append({'label': label, 'value': row['id']})
        return [html.P(f"{len(relations)} matching relationships; latest 100 displayed. Search a context code to find earlier records. The backup retains all."), *items], options
    except (ValueError, OSError, sqlite3.Error) as error:
        return html.P(_message(error)), []


@callback(Output('dig-refresh', 'data', allow_duplicate=True), Output('dig-status', 'children', allow_duplicate=True),
          Input('dig-relation-save', 'n_clicks'), Input('dig-relation-void', 'n_clicks'), State('dig-project', 'value'),
          State('dig-relation-a', 'value'), State('dig-relation-kind', 'value'), State('dig-relation-b', 'value'),
          State('dig-relation-note', 'value'), State('dig-relation-void-id', 'value'), prevent_initial_call=True)
def save_relation(_save, _void, project, a, kind, b, note, identifier):
    try:
        book = DigBook()
        if callback_context.triggered_id == 'dig-relation-void':
            book.void_relation(project, identifier, note)
            message = 'Relationship voided; its observation and your correction reason are retained.'
        else:
            book.relate(project, a, kind, b, note or '')
            message = 'Context relationship saved.'
        return time.time_ns(), message
    except (ValueError, OSError, sqlite3.Error) as error:
        return no_update, _message(error)


@callback(Output('dig-download', 'data'), Output('dig-status', 'children', allow_duplicate=True),
          Input('dig-export', 'n_clicks'), State('dig-project', 'value'), prevent_initial_call=True)
def download_project(_clicks, project):
    try:
        if not project:
            raise ValueError('Choose a project before downloading its backup.')
        data = DigBook().backup_bytes(project)
        return dcc.send_bytes(data, 'clovis-dig-records.zip', type='application/zip'), 'Downloaded the project, links, relationships and every saved revision.'
    except (ValueError, OSError, sqlite3.Error) as error:
        return no_update, _message(error)
