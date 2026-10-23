"""Local notebook actions resolve saved records by project and stable ID."""
import sqlite3
import hashlib
import time
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html, no_update
from atlas.gui.workspace_activation import when_opened
from core.dig_records import (DigBook, KINDS, COMMON, EXTRA,
    MEASUREMENT_ROLES, ANALYSIS_STATUS, QUANTITY_KINDS, QUANTITY_QUALIFIERS)
from core.fieldbook import readable_text

FIELDS = ('kind', 'code', 'unit', 'context', 'context-type', 'description', 'interpretation',
          'recorder', 'date', 'material', 'count', 'bag', 'sample-type', 'method',
          'depth', 'depth-unit', 'datum', 'citation', 'url', 'sources',
          'sample','role','analysis-status','portion','quantity-kind','qualifier','quantity','quantity-unit','mesh-size','mesh-unit')
KEYS = ('kind', 'code', 'unit_id', 'context_id', 'context_type', 'description', 'interpretation',
        'recorder', 'observed_date', 'material', 'count', 'bag', 'sample_type', 'method',
        'depth', 'depth_unit', 'datum', 'citation', 'url', 'source_ids',
        'sample_id','role','analysis_status','portion','quantity_kind','qualifier','quantity','quantity_unit','mesh_size','mesh_unit')


def _message(error):
    return str(error) if isinstance(error, ValueError) else 'The local record could not be saved. Check the project and try again.'


@when_opened('notebook', Output('fieldbook-reading-controls', 'style'), Output('fieldbook-reading-workspace', 'style'),
          Output('fieldbook-reading-inspector', 'style'), Output('dig-workspace', 'style'),
          Output('dig-inspector', 'style'), Output('dig-controls-help', 'style'),
          Output('dig-workspace', 'data-notebook-visible'), Input('fieldbook-section', 'value'))
def notebook_section(section):
    show, hide = {}, {'display': 'none'}
    return (hide, hide, hide, show, show, show, 'true') if section == 'dig' else (show, show, show, hide, hide, hide, 'false')


@when_opened('notebook', Output('dig-project', 'options'), Output('dig-project', 'value'),
          Input('dig-refresh', 'data'), Input('dig-project-request', 'data'), State('dig-project', 'value'))
def project_options(_refresh, requested, selected):
    try:
        options = [{'label': row['code'] + ' · ' + row['title'], 'value': row['id']} for row in DigBook().projects()]
        known = {row['value'] for row in options}
        changed = any(item['prop_id'] == 'dig-project-request.data' for item in callback_context.triggered)
        value = requested if changed else selected
        value = value if isinstance(value, str) and value in known else None
        # Refreshing records must not emit an unchanged project value: that
        # also triggers open_editor and can clear a newly opened source/draft.
        return options, value if value != selected else no_update
    except (ValueError, OSError, sqlite3.Error):
        return [], None


@callback(Output('dig-saved-selection','data',allow_duplicate=True), Output('dig-open-handled','data'),
          Input('dig-open-request','data'), Input('dig-project','value'), State('dig-open-handled','data'),
          prevent_initial_call=True)
def open_requested_source(request, project, handled):
    if (not isinstance(request,dict) or set(request)!={'project_id','id','nonce'}
            or request['project_id']!=project or not isinstance(request['nonce'],str)
            or len(request['nonce'])!=32 or any(char not in '0123456789abcdef' for char in request['nonce'])
            or request['nonce']==handled):
        return no_update,no_update
    try:
        row=DigBook().get(project,request['id'])
        if row is not None and row['data']['kind']=='source':
            return {'id':row['id'],'project_id':project,'revision':row['revision'],'open_request':request['nonce']},request['nonce']
    except (ValueError,OSError,sqlite3.Error):
        pass
    return no_update,no_update


@when_opened('notebook', Output('dig-project-picker', 'style'), Output('dig-project-records', 'style'),
          Output('dig-export', 'style'), Output('dig-project-start', 'open'),
          Output('dig-project-prompt', 'children'), Output('dig-project-prompt', 'style'),
          Output('dig-workspace', 'data-project-ready'),
          Input('dig-project', 'value'), Input('dig-project', 'options'))
def project_workflow(selected, options):
    options = options if isinstance(options, list) else []
    known = {row['value'] for row in options if isinstance(row, dict) and isinstance(row.get('value'), str)}
    ready = isinstance(selected, str) and selected in known
    show, hide = {}, {'display': 'none'}
    prompt = ('Choose a project above to read or add records, or start another project.'
              if known else 'Start a project below, or restore a project backup.')
    return (show if known else hide, show if ready else hide, show if ready else hide,
            not known, prompt, hide if ready else show, 'true' if ready else 'false')


@callback(Output('dig-refresh', 'data'), Output('dig-status', 'children'), Output('dig-project-request', 'data'),
          Input('dig-project-create', 'n_clicks'), Input('dig-upload-restored','data'),
          State('dig-project-code', 'value'), State('dig-project-title', 'value'), prevent_initial_call=True)
def create_or_restore(_clicks, uploaded, code, title):
    try:
        book = DigBook()
        if callback_context.triggered_id == 'dig-project-create':
            project = book.create_project(code, title)
            message = 'Project created. Add the units and contexts recorded by your project.'
            identifier = project['id']
        else:
            if (not isinstance(uploaded,dict) or set(uploaded)!={'project_id','added','advanced','nonce'}
                    or type(uploaded['added']) is not int or type(uploaded['advanced']) is not int
                    or uploaded['added']<0 or uploaded['advanced']<0
                    or not any(row['id']==uploaded['project_id'] for row in book.projects())):
                raise ValueError('Choose a project ZIP through Restore project backup.')
            identifier=uploaded['project_id']
            message=f"Restored {uploaded['added']} new records and {uploaded['advanced']} later revisions. Matching records were kept once."
        return time.time_ns(), message, identifier
    except (ValueError, OSError, sqlite3.Error) as error:
        return no_update, _message(error), no_update


def _captured_raa_record(selected,project):
    from core import raa_fieldwork_catalog as raa
    if not isinstance(selected,dict) or selected.get('project_id')!=project:
        raise ValueError('Choose a saved source in this project.')
    record=DigBook().get(project,selected.get('id'))
    reference=record['data'].get('atlas_reference') if record else None
    if not reference or not reference['atlas_id'].startswith('raa|'):
        raise ValueError('Choose a captured Swedish assignment source.')
    payload=raa.captured_payload(reference['entry'])
    expected='raa|'+payload['uuid']+'~'+hashlib.sha256(raa.canonical(payload)).hexdigest()
    if reference['atlas_id']!=expected:
        raise ValueError('The saved source identifier differs from its captured edition.')
    return {'source':'raa','id':expected,'original':{'uuid':payload['uuid'],'original':payload}}


@callback(Output('dig-raa-map-view','children'),Input('dig-raa-map-open','n_clicks'),
          State('dig-selection','data'),State('dig-project','value'),prevent_initial_call=True)
def captured_raa_map(clicks,selected,project):
    if type(clicks) is not int or clicks<1:
        return no_update
    try:
        from atlas.gui.published_location_ui import render
        return render(_captured_raa_record(selected,project),map_id='dig-captured-source-map')
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as error:
        return html.P(_message(error),className='atlas-help')


@callback(Output('dig-raa-source-download','data'),Input('dig-raa-source-open','n_clicks'),
          State('dig-selection','data'),State('dig-project','value'),prevent_initial_call=True)
def captured_raa_download(clicks,selected,project):
    if type(clicks) is not int or clicks<1:
        return no_update
    try:
        from core import raa_fieldwork_catalog as raa
        original=_captured_raa_record(selected,project)['original']
        return dcc.send_bytes(raa.canonical(original['original']),
            'captured-raa-'+original['uuid']+'.json',type='application/json')
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
        return no_update


@when_opened('notebook', Output('dig-record-list', 'children'), Output('dig-record-count', 'children'), Output('dig-page', 'data'),
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


@when_opened('notebook', Output('dig-selection', 'data'), Output('dig-edit-label', 'children'),
          *[Output('dig-' + field, 'value') for field in FIELDS],
          Input({'type': 'dig-record-open', 'index': ALL}, 'n_clicks'), Input('dig-project', 'value'),
          Input('dig-new', 'n_clicks'), Input('dig-saved-selection', 'data'),
          Input({'type':'dig-linked-open','index':ALL},'n_clicks'),
          Input({'type':'dig-add-measurement','index':ALL},'n_clicks'))
def open_editor(clicks, project, _new, saved, linked_clicks=None, measurement_clicks=None):
    trigger = callback_context.triggered_id
    changed = {item.get('prop_id') for item in getattr(callback_context, 'triggered', []) if isinstance(item, dict)}
    # A record-list refresh can add zero-click pattern controls in the same
    # browser update as a saved-source request. Honor the explicit selection
    # even when a newly rendered control is the first reported trigger.
    if ('dig-saved-selection.data' in changed and isinstance(saved, dict)
            and saved.get('project_id') == project):
        trigger = 'dig-saved-selection'
    row = None
    parent_sample=None
    try:
        if isinstance(trigger,dict) and trigger.get('type')=='dig-add-measurement':
            if not any(type(value) is int and value>0 for value in measurement_clicks or []):
                return (no_update,) * (len(FIELDS)+2)
            parent_sample=DigBook().get(project,trigger.get('index'))
            if parent_sample is None or parent_sample['data']['kind']!='sample':
                return (no_update,) * (len(FIELDS)+2)
        elif isinstance(trigger, dict) and trigger.get('type') in ('dig-record-open','dig-linked-open'):
            if not any((linked_clicks if trigger['type']=='dig-linked-open' else clicks) or []):
                return (no_update,) * (len(FIELDS) + 2)
            row = DigBook().get(project, trigger['index'])
        elif trigger == 'dig-saved-selection' and isinstance(saved, dict) and saved.get('project_id') == project:
            row = DigBook().get(project, saved.get('id'))
    except (ValueError, OSError, sqlite3.Error):
        if isinstance(trigger,dict) and trigger.get('type')=='dig-add-measurement':
            return (no_update,) * (len(FIELDS)+2)
        row = None
    defaults = {**COMMON, **{key: value for fields in EXTRA.values() for key, value in fields.items()}, 'kind': 'unit', 'code': ''}
    data = row['data'] if row else defaults
    if parent_sample:
        data={**defaults,'kind':'measurement','sample_id':parent_sample['id']}
    selected = {'id': row['id'], 'project_id': project, 'revision': row['revision']} if row else None
    label = f"Editing {data['code']} · revision {row['revision']}. Saving a correction keeps earlier revisions." if row else 'New record. Codes stay linked to stable IDs when corrected.'
    if parent_sample:
        label='New measurement for sample '+parent_sample['data']['code']+'. Save it with its own observation code.'
    values = [data.get(key, defaults.get(key)) for key in KEYS]
    values[FIELDS.index('depth-unit')] = values[FIELDS.index('depth-unit')] or None
    return selected, label, *values


@callback(Output('dig-status', 'children', allow_duplicate=True),
          Output('dig-saved-selection', 'data'), Input('dig-save', 'n_clicks'), State('dig-project', 'value'),
          State('dig-selection', 'data'), *[State('dig-' + field, 'value') for field in FIELDS],
          State('dig-photo-files','data'),State('dig-photo-owner','data'),
          State({'type':'dig-photo-caption','index':ALL},'id'),State({'type':'dig-photo-caption','index':ALL},'value'),
          State('dig-photo-transfer','data'),prevent_initial_call=True)
def save_editor(clicks,project,selected,*values):
    _,message,saved=save_record(clicks,project,selected,*values)
    return message,saved


@callback(Output('dig-refresh','data',allow_duplicate=True),Input('dig-selection','data'),prevent_initial_call=True)
def refresh_selected_record(selected):
    # Apply the saved revision to the editor before rebuilding pattern controls.
    # Refreshing the list in the save response could supersede that editor update
    # with a zero-click request, leaving the just-saved form on its old revision.
    return time.time_ns() if isinstance(selected,dict) else no_update


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
        if len(values)>len(FIELDS):
            from core.local_photos import captioned_refs
            photos,owner,caption_ids,captions,transfer=values[len(FIELDS):]
            if isinstance(transfer,dict) and transfer.get('busy'):
                raise ValueError('Wait for the photo to finish saving before saving this record.')
            old=DigBook().get(project,identifier) if identifier else None
            if photos or old and 'photos' in old['data']:
                if owner!={'project_id':project,'id':identifier}:
                    raise ValueError('Wait for this record’s photos to finish opening before saving.')
                value['photos']=captioned_refs(photos or [],caption_ids or [],captions or [],'dig')
        row = DigBook().save(project, value, identifier, revision)
        return time.time_ns(), f"Saved {row['data']['code']} · revision {row['revision']} on this computer.", {'id': row['id'], 'project_id': project, 'revision': row['revision']}
    except (ValueError, OSError, sqlite3.Error) as error:
        return no_update, _message(error), no_update


@when_opened('notebook', *[Output(identifier, 'style') for identifier in ('dig-unit-field', 'dig-context-field', 'dig-context-type-field',
                                                         'dig-find-fields', 'dig-bag-field', 'dig-sample-fields', 'dig-depth-fields', 'dig-source-fields',
                                                         'dig-material-field','dig-method-field','dig-measurement-fields')],
          Input('dig-kind', 'value'))
def record_fields(kind):
    groups = ({'context'}, {'find', 'sample'}, {'context'}, {'find'}, {'find', 'sample','measurement'}, {'sample'}, {'context', 'find', 'sample'}, {'source'},
              {'find','measurement'},{'sample','measurement'},{'measurement'})
    return tuple({} if isinstance(kind, str) and kind in group else {'display': 'none'} for group in groups)


def register_picker(identifier, kind, multiple=False):
    @when_opened('notebook', Output(identifier, 'options'), Input(identifier, 'search_value'), Input('dig-project', 'value'),
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
register_picker('dig-sample', 'sample')


@when_opened('notebook', Output('dig-measurement-page','data'),
          Input({'type':'dig-measurements-page','sample':ALL,'index':ALL},'n_clicks'),
          Input('dig-selection','data'),Input('dig-project','value'))
def measurement_page(clicks,selected,project):
    if not isinstance(selected,dict) or selected.get('project_id')!=project:
        return None
    trigger=callback_context.triggered_id
    page=1
    if isinstance(trigger,dict):
        if not any(type(value) is int and value>0 for value in clicks or []):
            return no_update
        page=trigger.get('index')
        if (trigger.get('sample')!=selected.get('id') or type(page) is not int or not 1<=page<=20_000):
            return no_update
    return {'project_id':project,'sample_id':selected.get('id'),'page':page}


def _record_facts(book,project,data):
    facts=[]
    terms={'role':MEASUREMENT_ROLES,'analysis_status':ANALYSIS_STATUS,
           'quantity_kind':QUANTITY_KINDS,'qualifier':QUANTITY_QUALIFIERS}
    for key,value in data.items():
        if key in ('kind','code','description','interpretation','source_ids','atlas_reference','photos'):
            continue
        if key in ('unit_id','context_id','sample_id'):
            linked=book.get(project,value) if value else None
            value=linked['data']['code'] if linked else 'Unknown / not recorded'
        elif key in terms:
            value=terms[key].get(value,value)
        label={'portion':'Portion / fraction','observed_date':'Observation / processing date',
               'quantity_unit':'Original quantity unit','mesh_unit':'Original mesh unit'}.get(key,key.replace('_id','').replace('_',' ').title())
        facts.extend([html.Dt(label),html.Dd(str(value) if value is not None and value!='' else 'Not recorded')])
    return facts


def _sample_measurements(book,project,row,page):
    result=book.measurements(project,row['id'],page=page)
    cards=[]
    for child in result['rows']:
        data=child['data']
        quantity=(QUANTITY_QUALIFIERS[data['qualifier']]+' '+data['quantity']+' '+data['quantity_unit']) if data['quantity'] else 'Quantity not recorded'
        cards.append(html.Button([html.Strong(data['code']),html.Small(MEASUREMENT_ROLES[data['role']]),
            html.Small(' · '.join(value for value in (data['portion'],data['material'],quantity,ANALYSIS_STATUS[data['analysis_status']]) if value))],
            id={'type':'dig-linked-open','index':child['id']},n_clicks=0,className='clovis-library-record'))
    def button(label,target,disabled):
        return html.Button(label,id={'type':'dig-measurements-page','sample':row['id'],'index':target},
                           disabled=disabled,n_clicks=0,className='atlas-secondary-button')
    return html.Section([html.H4(f"Sample measurements · {result['total']} records"),
        html.Button('Add measurement for this sample',id={'type':'dig-add-measurement','index':row['id']},n_clicks=0,className='atlas-secondary-button'),
        *(cards or [html.P('No measurements recorded. Create a sample measurement / processing record and choose this sample.')]),
        html.Div([button('Previous',max(1,result['page']-1),result['page']<=1),
            html.Span(f"{result['page']} of {result['pages']}"),
            button('Next',result['page']+1,result['page']>=result['pages'])],className='clovis-library-pagination')])


@when_opened('notebook', Output('dig-record-detail', 'children'), Input('dig-selection', 'data'), Input('dig-refresh', 'data'), State('dig-project', 'value'),
          Input('dig-measurement-page','data'))
def record_detail(selected, _refresh, project, measurement_page=None):
    try:
        if not isinstance(selected, dict) or selected.get('project_id') != project:
            return html.P('Choose a saved record to read its links and revisions.', className='atlas-help')
        book = DigBook()
        row = book.get(project, selected.get('id'))
        if not row:
            return html.P('This record is not in the selected project.')
        data = row['data']
        facts = _record_facts(book,project,data)
        related=[]
        from atlas.gui.photo_ui import gallery
        photo_cache={}
        if data.get('photos'):related.append(html.Section([html.H4('Photos recorded with this revision'),*gallery(data['photos'],cache=photo_cache)]))
        if 'atlas_reference' in data:
            reference=data['atlas_reference']
            citation_text=readable_text(reference['entry']['markdown'])
            if reference['atlas_id'].startswith('raa|'):
                from core.raa_fieldwork_catalog import reading_text
                citation_text=reading_text(reference['entry'])
            related.append(html.Details([html.Summary('Captured Atlas citation'),
                html.P('Captured '+reference['entry']['created'],className='atlas-help'),
                html.Button('Read full citation',id='dig-read-full',n_clicks=0,className='atlas-primary-button',
                            **{'aria-haspopup':'dialog'}),
                html.Pre(citation_text,id='dig-cited-note-text'),
                html.P('Atlas source ID: '+reference['atlas_id'],className='atlas-help')],open=True))
            if reference['atlas_id'].startswith('raa|'):
                related.append(html.Div([
                    html.Button('Show captured source geometry',id='dig-raa-map-open',n_clicks=0,className='atlas-secondary-button'),
                    html.Button('Download captured source record',id='dig-raa-source-open',n_clicks=0,className='atlas-secondary-button'),
                    html.P('Uses the edition saved with this project, even when the original collection is unavailable.',className='atlas-help'),
                    html.Div(id='dig-raa-map-view')]))
        if data['kind']=='measurement':
            related.append(html.Button('Open linked sample',id={'type':'dig-linked-open','index':data['sample_id']},n_clicks=0,className='atlas-secondary-button'))
        elif data['kind']=='sample':
            page=measurement_page.get('page',1) if isinstance(measurement_page,dict) and measurement_page.get('project_id')==project and measurement_page.get('sample_id')==row['id'] else 1
            related.append(_sample_measurements(book,project,row,page))
        sources = []
        for identifier in data['source_ids']:
            source = book.get(project, identifier)
            if source:
                source_data = source['data']
                sources.append(html.Div([html.Strong(source_data['code']), html.P(source_data['citation']),
                                         html.Button('Read source document',id={'type':'dig-linked-open','index':identifier},n_clicks=0,className='atlas-secondary-button'),
                                         html.A('Open source', href=source_data['url'], target='_blank', rel='noopener noreferrer') if source_data['url'] else None]))
        history = book.history(project, row['id'])
        return [html.H3(data['code'] + ' · ' + KINDS[data['kind']],id='dig-record-title'), html.P(f"Revision {row['revision']} · {row['updated']}", className='atlas-help'),
                html.H4('Observed description'), html.Pre(data['description'] or 'Not recorded'),
                html.H4('Interpretation / uncertainty'), html.Pre(data['interpretation'] or 'Not recorded'), html.Dl(facts),*related,
                html.H4('Supporting source documents'), *(sources or [html.P('Not recorded')]),
                html.Details([html.Summary(f"Revision history · {len(history)} versions"),
                              *[html.Div([html.Strong(f"Revision {item['revision']} · {item['updated']}"),
                                          html.Pre(item['data']['description'] or 'No description'),
                                          html.Pre(item['data']['interpretation'] or 'No interpretation'),
                                          *gallery(item['data'].get('photos',[]),cache=photo_cache),
                                          html.Dl(_record_facts(book,project,item['data'])) if data['kind']=='measurement' else None]) for item in history[-20:]],
                              html.P('The backup retains every field in every revision. This reader shows the latest 20 descriptions and interpretations, with full measurement fields for sample measurements.', className='atlas-help')]),
                html.P('Stable record ID: ' + row['id'], className='atlas-help')]
    except (ValueError, OSError, sqlite3.Error) as error:
        return html.P(_message(error))


@when_opened('notebook', Output('dig-relations', 'children'), Output('dig-relation-void-id', 'options'), Input('dig-project', 'value'), Input('dig-refresh', 'data'), Input('dig-relation-query', 'value'))
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
