"""Common local search, authoritative record reading and evidence navigation."""
import sqlite3
import json
import time
from uuid import uuid4
from urllib.parse import urlsplit
from dash import ALL, MATCH, Input, Output, State, callback, callback_context, dcc, html, no_update
from core import atlas_catalog as catalog, excavation_catalog, environment_catalog, zooarchaeology_catalog, assemblage_catalog, site_register_catalog
from core.fieldbook import EMPTY_BOOK, MAX_ENTRY_BYTES
from atlas.gui.reading_merge import merge_entries
from core.data_packs import PackStore
from core import pleiades_catalog
from core import project_references
from core import ads_metadata_catalog
from core import amcr_catalog
from core import dans_metadata_catalog
from core import raa_fieldwork_catalog
from core import france_fieldwork_catalog
from core import finland_register_catalog
from core.dig_records import DigBook
from core.atlas_search_ideas import chosen_query
from atlas.gui.atlas_ui import search_help
from atlas.gui.offline_reference_ui import control as local_source_control
from atlas.gui.library_ui import reading_nav
from atlas.gui.published_location_ui import control as location_control, render as location_map

ERRORS = (ValueError, OSError, sqlite3.Error, TypeError, KeyError)
PACK_SOURCES = {"radiocarbon-world": "dates", "dinosaur-sites": "dinosaurs", "neolithic-assemblages": "assemblages",
                "excavations-surveys": "contexts", "dated-environments": "environments", "anatolian-zooarchaeology": "specimens",
                "excavation-assemblages": "field_assemblages", "north-american-sites": "site_registers", "ancient-places": "places",
                'ads-research-metadata': 'ads', 'amcr-native-metadata': 'amcr',
                'dans-archaeology-metadata': 'dans', 'raa-fieldwork':'raa', 'france-fieldwork':'france',
                'finland-antiquities':'finland'}


@callback(Output('atlas-france-filters','style'),Output('atlas-france-method','options'),
          Output('atlas-france-method','value'),Output('atlas-france-field','value'),
          Output('atlas-context','data',allow_duplicate=True),Output('atlas-france-status','children'),
          Input('atlas-source','value'),Input('atlas-kind','value'),Input('atlas-france-method','value'),
          Input('atlas-france-field','value'),Input('atlas-clear-context','n_clicks'),
          Input('data-pack-refresh','data'),State('atlas-context','data'),prevent_initial_call=True)
def france_filters(source,kind,method,field,_clear,_refresh,context):
    options=[{'label':'All original categories','value':''},
        {'label':france_fieldwork_catalog.EXCAVATION_LABEL,'value':'excavation'}]
    if source!='france' or kind not in ('all','archaeology'):
        return {'display':'none'},options,no_update,no_update,no_update,''
    try:
        clear=callback_context.triggered_id=='atlas-clear-context'
        method,field=('', 'all') if clear else (method or '',field or 'all')
        france_fieldwork_catalog.validate_parameters(method=method,field=field)
        options.extend({'label':row['label']+f" · {row['records']:,}",'value':row['value']}
            for row in france_fieldwork_catalog.choices())
        parameters={'collection':'france','field':field}
        if method:parameters['method']=method
        label=france_fieldwork_catalog.EXCAVATION_LABEL if method=='excavation' else method or 'All original categories'
        value={'parameters':parameters,'label':'France · regional operations · '+label+' · '+france_fieldwork_catalog.FIELDS[field]}
        return {},options,'' if clear else no_update,'all' if clear else no_update,no_update if context==value else value,''
    except ERRORS:
        return {},options,no_update,no_update,no_update,'The French operation collection could not be read. Check Manage offline collections.'


@callback(Output('atlas-finland-filters','style'),Output('atlas-finland-class','options'),Output('atlas-finland-dating','options'),
          Output('atlas-finland-class','value'),Output('atlas-finland-dating','value'),Output('atlas-finland-field','value'),
          Output('atlas-context','data',allow_duplicate=True),Output('atlas-finland-status','children'),
          Input('atlas-source','value'),Input('atlas-kind','value'),Input('atlas-finland-class','value'),
          Input('atlas-finland-dating','value'),Input('atlas-finland-field','value'),Input('atlas-clear-context','n_clicks'),
          Input('data-pack-refresh','data'),State('atlas-context','data'),prevent_initial_call=True)
def finland_filters(source,kind,site_class,dating,field,_clear,_refresh,context):
    classes=[{'label':'All original classes','value':''}]
    datings=[{'label':'All original dating values','value':''}]
    if source!='finland' or kind not in ('all','archaeology'):
        return {'display':'none'},classes,datings,no_update,no_update,no_update,no_update,''
    try:
        clear=callback_context.triggered_id=='atlas-clear-context'
        site_class,dating,field=('','','all') if clear else (site_class or '',dating or '',field or 'all')
        finland_register_catalog.validate_parameters(site_class=site_class,dating=dating,field=field)
        known=[]
        message=''
        for column,selected,options in (('site_class',site_class,classes),('dating',dating,datings)):
            rows=finland_register_catalog.choices(column)
            options.extend({'label':row['label']+f" · {row['records']:,}",'value':row['value']} for row in rows if row['value'])
            if selected:
                known.append(selected)
                if selected not in {row['value'] for row in rows}:
                    options.append({'label':'Original value absent from this snapshot · '+selected,'value':selected})
                    message='A selected original value is absent from this snapshot. Results have not been broadened.'
        parameters={'collection':'finland','field':field}
        if site_class:parameters['site_class']=site_class
        if dating:parameters['dating']=dating
        value={'parameters':parameters,'label':'Finland · Antiquities Record · '+finland_register_catalog.FIELDS[field]
            +(' · '+' · '.join(known) if known else '')}
        return ({},classes,datings,'' if clear else no_update,'' if clear else no_update,'all' if clear else no_update,
                no_update if context==value else value,message)
    except ERRORS:
        return {},classes,datings,no_update,no_update,no_update,no_update,'The Finnish register collection could not be read. Check Manage offline collections.'


@callback(Output('atlas-raa-filters','style'),Output('atlas-raa-method','options'),Output('atlas-raa-state','options'),
          Output('atlas-raa-method','value'),Output('atlas-raa-state','value'),Output('atlas-raa-ground','value'),Output('atlas-raa-field','value'),
          Output('atlas-context','data',allow_duplicate=True),Output('atlas-raa-status','children'),
          Input('atlas-source','value'),Input('atlas-kind','value'),Input('atlas-raa-method','value'),Input('atlas-raa-state','value'),
          Input('atlas-raa-ground','value'),Input('atlas-raa-field','value'),Input('atlas-clear-context','n_clicks'),
          Input('data-pack-refresh','data'),State('atlas-context','data'),prevent_initial_call=True)
def raa_filters(source,kind,method,status,ground,field,_clear,_refresh,context):
    methods=[{'label':'All original types','value':''}]
    statuses=[{'label':'All recorded statuses','value':''}]
    if source!='raa' or kind not in ('all','archaeology'):
        return {'display':'none'},methods,statuses,no_update,no_update,no_update,no_update,no_update,''
    try:
        clear=callback_context.triggered_id=='atlas-clear-context'
        method,status,ground,field=('', '', 'all', 'all') if clear else (method or '',status or '',ground or 'all',field or 'all')
        raa_fieldwork_catalog.validate_parameters(method=method,status=status,ground=ground,field=field)
        known=[]
        message=''
        for column,selected,options in (('method',method,methods),('status',status,statuses)):
            rows=raa_fieldwork_catalog.choices(column)
            options.extend({'label':row['label']+f" · {row['records']:,}",'value':row['value']} for row in rows)
            values={row['value'] for row in rows}
            if selected:
                known.append(selected)
                if selected not in values:
                    options.append({'label':'Original value absent from this snapshot · '+selected,'value':selected})
                    message='A selected original value is absent from this snapshot. Results have not been broadened.'
        parameters={'collection':'raa','ground':ground,'field':field}
        if method: parameters['method']=method
        if status: parameters['status']=status
        value={'parameters':parameters,'label':'Sweden · RAÄ assignments · '+raa_fieldwork_catalog.FIELDS[field]
            +' · '+raa_fieldwork_catalog.GROUND[ground]+(' · '+' · '.join(known) if known else '')}
        return {},methods,statuses,'' if clear else no_update,'' if clear else no_update,'all' if clear else no_update,'all' if clear else no_update,no_update if context==value else value,message
    except ERRORS:
        return {},methods,statuses,no_update,no_update,no_update,no_update,no_update,'The Swedish assignment collection could not be read. Check Manage offline collections.'


@callback(Output('atlas-source', 'options'), Output('atlas-source', 'value', allow_duplicate=True),
          Input('atlas-kind', 'value'), Input('data-pack-refresh', 'data'), State('atlas-source', 'value'),
          prevent_initial_call=True)
def source_choices(kind, _refresh, selected):
    sources = catalog.available_sources()
    known = {key: sources[key] for key in catalog.GROUPS.get(kind, ()) if key in sources}
    options = [{'label': 'All sources for this evidence', 'value': 'all'},
               *[{'label': label, 'value': key} for key, label in known.items()]]
    return options, no_update if selected in ('all', *known) else 'all'


@callback(Output('atlas-amcr-filters', 'style'), Output('atlas-amcr-method', 'options'),
          Output('atlas-amcr-method', 'disabled'), Output('atlas-amcr-method', 'value'),
          Output('atlas-amcr-scope', 'value'), Output('atlas-amcr-field', 'value'),
          Output('atlas-context', 'data', allow_duplicate=True), Output('atlas-amcr-status', 'children'),
          Input('atlas-source', 'value'), Input('atlas-kind', 'value'), Input('atlas-amcr-scope', 'value'),
          Input('atlas-amcr-method', 'value'), Input('atlas-amcr-field', 'value'),
          Input('atlas-clear-context', 'n_clicks'), Input('data-pack-refresh', 'data'),
          State('atlas-context', 'data'), prevent_initial_call=True)
def amcr_filters(source, kind, scope, method, field, _clear, _refresh, context):
    options = [{'label': 'All methods', 'value': ''}]
    if source != 'amcr' or kind not in ('all', 'archaeology'):
        return {'display': 'none'}, options, False, no_update, no_update, no_update, no_update, ''
    try:
        clear = callback_context.triggered_id == 'atlas-clear-context'
        scope, method, field = ('all', '', 'evidence') if clear else (scope or 'all', method or '', field or 'evidence')
        method = '' if scope == 'sites' else method
        amcr_catalog.validate_parameters(scope=scope, method=method, field=field)
        types = amcr_catalog.methods()
        options.extend({'label': row['label'] + f" · {row['records']:,}", 'value': row['value']} for row in types)
        known = {row['value']: row['label'] for row in types}
        status = ''
        if method and method not in known:
            options.append({'label': 'Type absent from this snapshot', 'value': method})
            status = 'That native type is absent from this snapshot. Choose a listed type; results have not been broadened.'
        parameters = {'collection': 'amcr', 'scope': scope, 'field': field}
        if method:
            parameters['method'] = method
        value = {'parameters': parameters, 'label': 'AMCR · ' + amcr_catalog.SCOPES[scope] + ' · '
            + amcr_catalog.FIELDS[field] + (' · ' + known.get(method, method) if method else '')}
        return {}, options, scope == 'sites', '' if clear or scope == 'sites' else no_update, 'all' if clear else no_update, 'evidence' if clear else no_update, no_update if context == value else value, status
    except ERRORS:
        return {}, options, False, no_update, no_update, no_update, no_update, 'The AMCR collection could not be read. Check Manage offline collections.'


@callback(Output('atlas-ads-filters', 'style'), Output('atlas-ads-type', 'options'),
          Output('atlas-ads-type', 'value'), Output('atlas-ads-field', 'value'),
          Output('atlas-context', 'data', allow_duplicate=True), Output('atlas-ads-status', 'children'),
          Input('atlas-source', 'value'), Input('atlas-kind', 'value'), Input('atlas-ads-type', 'value'),
          Input('atlas-ads-field', 'value'), Input('atlas-clear-context', 'n_clicks'), Input('data-pack-refresh', 'data'),
          State('atlas-context', 'data'), prevent_initial_call=True)
def ads_filters(source, kind, resource_type, field, _clear, _refresh, context):
    options = [{'label': 'All source types', 'value': ''}]
    if source != 'ads' or kind not in ('all', 'archaeology'):
        return {'display': 'none'}, options, no_update, no_update, no_update, ''
    try:
        types = ads_metadata_catalog.resource_types()
        options.extend({'label': item['label'] + f" · {item['records']:,}", 'value': item['value']} for item in types)
        clear = callback_context.triggered_id == 'atlas-clear-context'
        resource_type, field = ('', 'all') if clear else (resource_type or '', field or 'all')
        ads_metadata_catalog.validate_parameters(resource_type=resource_type, field=field)
        known = {item['value']: item['label'] for item in types}
        status = ''
        if resource_type and resource_type not in known:
            options.append({'label': 'Type absent from this snapshot · choose All source types', 'value': resource_type})
            status = 'That source type is absent from this snapshot. Choose a listed type; the search has not been broadened.'
        parameters = {'collection': 'ads'}
        labels = []
        if resource_type:
            parameters['resource_type'] = resource_type
            labels.append(known.get(resource_type, 'Unavailable source type'))
        if field != 'all':
            parameters['field'] = field
            labels.append(ads_metadata_catalog.FIELDS[field])
        value = {'parameters': parameters, 'label': 'ADS metadata · ' + ' · '.join(labels)} if labels else None
        return {}, options, '' if clear else no_update, 'all' if clear else no_update, no_update if context == value else value, status
    except ERRORS:
        return {}, options, no_update, no_update, no_update, 'The ADS collection could not be read. Check Manage offline collections.'


@callback(Output('atlas-dans-filters', 'style'), Output('atlas-dans-subject', 'options'),
          Output('atlas-dans-subject', 'value'), Output('atlas-dans-field', 'value'),
          Output('atlas-context', 'data', allow_duplicate=True), Output('atlas-dans-status', 'children'),
          Input('atlas-source', 'value'), Input('atlas-kind', 'value'), Input('atlas-dans-subject', 'value'),
          Input('atlas-dans-field', 'value'), Input('atlas-clear-context', 'n_clicks'),
          Input('data-pack-refresh', 'data'), Input('atlas-dans-subject', 'search_value'),
          State('atlas-context', 'data'), prevent_initial_call=True)
def dans_filters(source, kind, subject, field, _clear, _refresh, search, context):
    options = [{'label': 'All original subjects', 'value': ''}]
    if source != 'dans' or kind not in ('all', 'archaeology'):
        return {'display': 'none'}, options, no_update, no_update, no_update, ''
    try:
        clear = callback_context.triggered_id == 'atlas-clear-context'
        subject, field = ('', 'research') if clear else (subject or '', field or 'research')
        previous = context.get('parameters', {}) if isinstance(context, dict) else {}
        shared = previous.get('shared_legacy', '') if not clear and isinstance(previous, dict) and previous.get('collection') == 'dans' else ''
        dans_metadata_catalog.validate_parameters(subject=subject, field=field, shared_legacy=shared)
        rows = dans_metadata_catalog.subjects((search or '')[:120], selected=subject)
        options.extend({'label': row['label'] + f" · {row['records']:,}", 'value': row['value']} for row in rows)
        known = {row['value']: row['label'] for row in rows}
        status = ''
        if subject and subject not in known:
            options.append({'label': 'Subject absent from this snapshot', 'value': subject})
            status = 'This original subject is absent from this snapshot. Results have not been broadened.'
        parameters = {'collection': 'dans', 'field': field}
        if subject:
            parameters['subject'] = subject
        if shared:
            parameters['shared_legacy'] = shared
        value = {'parameters': parameters, 'label': 'DANS · ' + dans_metadata_catalog.FIELDS[field]
            + (' · ' + known.get(subject, 'Unavailable original subject') if subject else '')
            + (' · Shared original identifier ' + shared + ' · possible overlap' if shared else '')}
        return {}, options, '' if clear else no_update, 'research' if clear else no_update, no_update if context == value else value, status
    except ERRORS:
        return {}, options, no_update, no_update, no_update, 'The DANS collection could not be read. Check Manage offline collections.'


@callback(Output("library-section", "value", allow_duplicate=True),
          Input("atlas-return", "n_clicks"), Input("atlas-manage-packs", "n_clicks"), prevent_initial_call=True)
def navigate(_return, _manage):
    return "packs" if callback_context.triggered_id == "atlas-manage-packs" else "atlas"


@callback(Output("resident-tool", "value", allow_duplicate=True), Input("header-place-button", "n_clicks"),
          State("resident-tool", "value"), Input("start-town", "n_clicks"), prevent_initial_call=True)
def choose_town(clicks, tool, start=None):
    return "map" if (clicks or start) and tool == "library" else no_update


def _parameters(query, kind, source, context):
    return {"query": query or "", "kind": kind or "all", "source": source or "all",
            "context": context.get("parameters") if isinstance(context, dict) else None}


@callback(Output('atlas-search-ideas','children'), Output('atlas-search-note','children'), Input('atlas-query','value'),
          prevent_initial_call=True)
def query_ideas(query):
    return search_help(query)


@callback(Output('atlas-town-hint','children'), Input('atlas-query','value'), prevent_initial_call=True)
def town_hint(query):
    """A town name is better answered by its offline town report than by records that mention the word."""
    from core.us_places import exact_towns
    towns = exact_towns(query, limit=13)
    if not towns:
        return []
    shown = towns[:12]
    note = ('Add a state to narrow the list, for example "' + query.strip() + ', Ohio".' if len(towns) > 12
            else 'The report uses public town points and maps, not property or find locations.')
    return html.Div([
        html.P(['"', query.strip(), '" is also a US town name. Open its offline town report for mapped geology, '
                'historical maps and published evidence:'], className='atlas-help'),
        html.Div([html.Button(town['label'], id={'type': 'atlas-town', 'index': town['geoid']}, n_clicks=0,
                              className='atlas-secondary-button') for town in shown], className='clovis-pack-actions'),
        html.P(note, className='atlas-help')], className='clovis-atlas-town-hint')


@callback(Output('workflow-mode','value',allow_duplicate=True), Output('resident-tool','value',allow_duplicate=True),
          Output('resident-state','value',allow_duplicate=True), Output('resident-place','options',allow_duplicate=True),
          Output('resident-place','disabled',allow_duplicate=True), Output('resident-place','value',allow_duplicate=True),
          Output('resident-build','n_clicks',allow_duplicate=True),
          Input({'type':'atlas-town','index':ALL},'n_clicks'), State('resident-build','n_clicks'), prevent_initial_call=True)
def open_town_report(clicks, built):
    from core.us_places import get_place, STATE_NAMES
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return (no_update,) * 7
    geoid = trigger.get('index')
    place = next((get_place(geoid, state) for state in STATE_NAMES if get_place(geoid, state)), None)
    if place is None:
        return (no_update,) * 7
    option = {'label': place['name'] + ', ' + place['state'], 'value': place['geoid']}
    previous = built if type(built) is int and built >= 0 else 0
    return 'resident', 'map', place['state'], [option], False, place['geoid'], previous + 1


@callback(Output('atlas-query','value',allow_duplicate=True),
          Input({'type':'atlas-search-idea','index':ALL},'n_clicks'),
          State({'type':'atlas-search-idea','index':ALL},'id'), State('atlas-query','value'), prevent_initial_call=True)
def choose_query_idea(clicks, identifiers, query):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict) or set(trigger)!={'type','index'} or trigger['type']!='atlas-search-idea':
        return no_update
    if not isinstance(clicks,list) or not isinstance(identifiers,list) or len(clicks)!=len(identifiers):
        return no_update
    if not any(identifier==trigger and type(count) is int and count>0 for identifier,count in zip(identifiers or [],clicks or [])):
        return no_update
    target=chosen_query(query or '',trigger['index'])
    return target if target is not None else no_update


def _source_link(url, label):
    try:
        parsed = urlsplit(url)
        if (isinstance(url, str) and len(url) <= 2000 and parsed.scheme == "https" and parsed.hostname
                and not parsed.username and not parsed.password and parsed.port in (None, 443)
                and not any(ord(char) < 33 for char in url)):
            return html.A(label, href=url, target="_blank", rel="noopener noreferrer")
    except (ValueError, TypeError):
        pass
    return None


@callback(Output("atlas-cards", "children"), Output("atlas-count", "children"), Output("atlas-page", "data"),
          Output("atlas-page-label", "children"), Output("atlas-previous", "disabled"), Output("atlas-next", "disabled"),
          Output("atlas-coverage", "children"), Output("atlas-context-label", "children"), Output("atlas-context-banner", "style"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-previous", "n_clicks"), Input("atlas-next", "n_clicks"),
          Input("data-pack-refresh", "data"), State("atlas-page", "data"),
          running=[(Output('atlas-search-status','children'),'Searching local collections…','')])
def results(query, kind, source, context, _previous, _next, _refresh, page):
    try:
        page = page if type(page) is int and page >= 1 else 1
        trigger = callback_context.triggered_id
        page = max(1, page - 1) if trigger == "atlas-previous" else page + 1 if trigger == "atlas-next" else 1
        result = catalog.search(page=page, **_parameters(query, kind, source, context))
        cards = [html.Button([html.Small(row["evidence"], className="clovis-atlas-evidence"),
                              html.Strong(row["title"]), html.Small(row["subtitle"]), html.Small(row["source_label"])],
                             id={"type": "atlas-open", "index": row["id"]}, n_clicks=0,
                             className="clovis-library-record") for row in result["rows"]]
        if not cards:
            limits = context.get('parameters', {}) if isinstance(context, dict) else {}
            if source == 'finland':
                cards=[html.P('No register sites match these class, dating and text limits. The register is incomplete; a missing site does not establish an absence of archaeology. Try another original field, a whole municipality name, or clear these limits.')]
            elif source == 'france':
                cards=[html.P('No operation-table rows match these category and text limits. This regional table is incomplete; missing place names do not establish an absence of archaeology. Try another original field or clear these limits.')]
            elif source == 'raa':
                cards=[html.P('No assignment editions match these original type, status, geometry and text limits. Coverage is incomplete. Missing geometry or place text does not establish no archaeology. Clear these limits or search another original field.')]
            elif source == 'dans':
                cards = [html.P('No DOI metadata resources match these limits. Missing subjects, place fields or untranslated source wording do not establish an absence of archaeology. Try another text field or original subject, or clear these limits.')]
            elif source == 'ads' and limits.get('field') == 'places':
                cards = [html.P('No records match these source-type and recorded-place-text limits. Missing place metadata is not evidence that there are no sites or excavations there. Try Titles only or All metadata in Search text in.')]
            elif source == 'amcr':
                cards = [html.P('No readable editions match these limits. Fieldwork acquisition is incomplete; denied and deleted source headers are not readable records. Missing metadata does not establish absence of archaeology. Try another record kind or text field, or clear these limits.')]
                headers = amcr_catalog.header_status(query or '')
                if headers:
                    cards.insert(0, html.Div([html.Strong('Original identifier found in retained source headers'),
                        html.Ul([html.Li(row['label'] + ' · Metadata edition ' + row['datestamp']) for row in headers]),
                        html.P('These retained headers are source evidence, not additional finds or events. Current limits may exclude a readable edition. Denied/deleted editions have no readable content in this snapshot; the provider may have newer metadata.'),
                        _source_link('https://api.aiscr.cz/id/' + amcr_catalog.native_identifier(query or ''), 'Check current provider metadata (online)')]))
        coverage = [html.P("Records include different evidence types. Counts describe source records; observations may overlap between collections.", className="atlas-help"),
                    html.Ul([html.Li(f'{row["label"]}: {row["records"]:,} matching records') for row in result["coverage"]])]
        if result["missing"]:
            coverage.append(html.Ul([html.Li(row["label"] + ": " + row["reason"]) for row in result["missing"]]))
        label = f'{result["total"]:,} matching source records'
        if result["missing"]:
            label += f' · {len(result["missing"])} collection(s) unavailable; see Search coverage'
        return (cards or [html.P("No records match. Try a shorter name or broaden the evidence or source.")], label,
                result["page"], f'{result["page"]:,} of {result["pages"]:,}', result["page"] <= 1,
                result["page"] >= result["pages"], coverage,
                context.get("label", "Associated source evidence") if isinstance(context, dict) else "",
                {} if context else {"display": "none"})
    except ERRORS as error:
        return [], str(error) if isinstance(error, ValueError) else "The atlas could not read this search. Check offline collections.", 1, "", True, True, [], "", {"display": "none"}


@callback(Output("atlas-selected", "data"), Input({"type": "atlas-open", "index": ALL}, "n_clicks"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-page", "data"), Input("data-pack-refresh", "data"))
def select(clicks, query, kind, source, context, page, _refresh):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return None
    try:
        parameters = _parameters(query, kind, source, context)
        result = catalog.search(page=page, **parameters)
        identifier = trigger["index"]
        if any(row["id"] == identifier for row in result["rows"]):
            return {"id": identifier, "page": page, "parameters": parameters}
    except ERRORS:
        pass
    return None


def current(selected, query, kind, source, context, page):
    parameters = _parameters(query, kind, source, context)
    if not isinstance(selected, dict) or selected.get("parameters") != parameters or selected.get("page") != page:
        return None
    result = catalog.search(page=page, **parameters)
    identifier = selected.get("id")
    return catalog.get_record(identifier) if any(row["id"] == identifier for row in result["rows"]) else None


def _facts(rows):
    return html.Dl([node for label, value in rows for node in (html.Dt(label), html.Dd(value))], className="clovis-library-facts")


def _reading_facts(record):
    if record['source']=='finland':
        # Every original row's attributes remain in the register-rows disclosure
        # and the saved citation; lead with the site summary.
        return [(label,value) for label,value in record['facts'] if ' · fid ' not in label]
    if record['source']=='france':
        # Lead with the operation evidence. Complete provenance and exact field
        # names remain in the edition disclosure and unchanged saved citation.
        native=dict(zip(record['original']['original']['headers'],record['original']['original']['values'],strict=True))
        names=[("Type d'autorisation",'Operation category'),('Commune','Recorded municipality'),
            ('Lieu-dit','Recorded place'),('Date demarrage','Recorded start date'),('Date fin','Recorded end date'),
            ('Date remise RFO','Recorded report submission'),('Annee','Original realization year'),
            ('numero SDA','Local SDA operation code'),('numero SRA','Original SRA code'),
            ('Emprise m²','Original stated project area (m²)'),('Date prescription','Prescription date'),
            ('Date reception prescription','Prescription received'),('Amenageur - Maitre d\'ouvrage','Original developer'),
            ('Type amenageur','Developer type'),('Statut amenageur (public/privé)','Developer status'),
            ('Nature amenagement','Original development type')]
        rows=[]
        for key,label in names:
            value=native[key] if native[key]!='' else 'Not recorded (empty source field)'
            if key=="Type d'autorisation":
                value+=' · '+france_fieldwork_catalog.TYPES.get(value,'Original value')
            rows.append((label+' · '+key,value))
        return rows
    if record["source"] == "site_registers":
        # Complete identifiers, rights and locators remain in the edition
        # disclosures and saved citation; lead with the site's recorded evidence.
        provenance = {"Published site identifier", "Table rights (source)", "Original CSV record", "Original file SHA-256"}
        return [(label, value) for label, value in record["facts"] if label not in provenance]
    if record["source"] != "specimens":
        return record["facts"]
    names = {"Published context": "Context", "Related person(s)": "Contributors",
             "Has Biological Taxonomy [Label]": "Published taxon",
             "Has Biological Taxonomy [Source value]": "Recorded taxon",
             "Has anatomical identification [Label]": "Anatomical element",
             "Has anatomical identification [Source value]": "Recorded element"}
    rows = []
    for label, value in record["facts"]:
        # Exact source terms, ontology URIs and full provenance remain in the
        # original edition panels and saved reference.
        if label == "Source edition" or label.endswith(" [URI]"):
            continue
        header, separator, table = label.partition(" · ")
        if separator:
            label = header.removesuffix(" [Source]") + " · " + table.rsplit("/", 1)[-1]
        rows.append((names.get(label, label), value))
    return rows


@callback(Output("atlas-detail", "children"), Input("atlas-selected", "data"),
          Input("atlas-query", "value"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          Input("atlas-context", "data"), Input("atlas-page", "data"), Input("data-pack-refresh", "data"))
def reader(selected, query, kind, source, context, page, _refresh):
    try:
        row = current(selected, query, kind, source, context, page)
        if row is None:
            return html.P("Choose a result to read its evidence, context and source.")
        children = [reading_nav("atlas-query"), html.P(row["evidence"], className="clovis-atlas-evidence"),
                    html.H3(row["title"]), html.P(row["source_label"], className="atlas-help"), _facts(_reading_facts(row))]
        if row['source']=='publications':
            children.append(html.A('Read complete source offline',href='/reference/publication/'+row['original']['id'],
                target='_blank',rel='noopener noreferrer',className='atlas-secondary-button'))
            children.append(html.A('Download complete study for offline reading',href='/reference/publication/panama-0335678/bundle',
                className='atlas-secondary-button'))
        if row['source']=='guides':
            for guide_source in row['original']['sources']:
                children.extend(local_source_control(guide_source['url'],'atlas-guide'))
        if row["description"]:
            if row['source'] in ('ads', 'dans'):
                children.append(html.H4('Description in the retrieved metadata'))
                children.append(html.P('Descriptions may discuss old totals or planned phases. This metadata snapshot does not establish current project completeness.', className='atlas-help'))
            children.append(html.P(row["description"]))
        links = catalog.relationships(row)
        if links:
            def button(link):
                return html.Button(f'{link["total"]:,} · {link["label"]}',
                                   id={"type": "atlas-related", "index": link["key"]},
                                   n_clicks=0, className="atlas-secondary-button")
            main_keys = ("animals", "plants", "dates", "phases", "sites", "county", "parent", "children", "source-rows", "subject", "outgoing", "incoming", "collection", "country-state")
            main = [link for link in links if link["key"] in main_keys or
                    row['source'] == 'dans' and link['key'].startswith('shared-legacy:') or
                    row["source"] == "field_assemblages" and link["key"].partition(":")[0] in ("recording", "analysis", "locus", "refit", "pottery-bag", "layer", "recovery", "unit", "trench") or
                    row["source"] == "environments" and link["parameters"]["view"] in ("observation", "sample", "age", "date")][:4]
            more = [link for link in links if link not in main]
            children.append(html.Div([html.H4('Records with shared identifiers' if row['source'] == 'dans' else 'Associated evidence'),
                *([html.P('A shared original identifier flags possible overlap. Keep both DOI records and their versions separate. Following the link keeps your subject and metadata field, and clears the search words.', className='atlas-help')] if row['source'] == 'dans' else []),
                *[button(link) for link in main]], className="clovis-atlas-related"))
            if more:
                children.append(html.Details([html.Summary("More associated evidence"),
                    html.Div([button(link) for link in more], className="clovis-atlas-related")]))
        if row['source'] in ('ads', 'dans'):
            metadata_catalog = dans_metadata_catalog if row['source'] == 'dans' else ads_metadata_catalog
            original = row['original']
            attributes = original['source']['attributes']
            rights = attributes.get('rightsList') or []
            children.append(html.Details([html.Summary('Linked resource rights'),
                html.P('The metadata is CC0. These declarations apply to linked resource content, which is not included here.', className='atlas-help'),
                *[html.Pre(metadata_catalog.literal(item)) for item in rights],
                *([] if rights else [html.P('No linked resource rights declaration recorded; no content license inferred.')])]))
            children.append(html.Details([html.Summary('Source location fields'), location_control(row['id'], label='Plot metadata coordinate fields'),
                html.P('Source coordinates and place words do not establish an excavation footprint or find location. Missing coordinates stay missing.', className='atlas-help'),
                html.Pre(metadata_catalog.literal(attributes.get('geoLocations')))]))
            if row['source'] == 'dans':
                children.append(html.Details([html.Summary('Original subjects, identifiers and dates'),
                    html.P('Original wording and source dates remain separate. Metadata dates and publication years are not automatically fieldwork dates.', className='atlas-help'),
                    _facts([(label, metadata_catalog.literal(attributes.get(key))) for label, key in (
                        ('Subjects and schemes', 'subjects'), ('Alternate identifiers', 'alternateIdentifiers'),
                        ('Resource dates', 'dates'))])]))
            children.append(html.Details([html.Summary('Original metadata and retrieval evidence'),
                _facts([('Original object SHA-256', original['source_sha256']),
                    ('Original response SHA-256', original['receipt']['sha256']),
                    ('Page / object ordinal', str(original['source_page']) + ' / ' + str(original['source_ordinal'])),
                    ('Retrieved', original['receipt']['retrieved_utc']), ('Retrieved URL', original['receipt']['url'])]),
                html.Button('Download original metadata', id='atlas-' + row['source'] + '-original', n_clicks=0, className='atlas-secondary-button'),
                _source_link('https://api.datacite.org/dois/' + original['doi'], 'Open current DataCite metadata (online)'),
                html.Pre(json.dumps(original['source'], ensure_ascii=False, indent=2))]))
        elif row['source']=='finland':
            original=row['original']['original']
            children.append(html.Details([html.Summary('Original register rows, geometry and export edition'),
                html.P('Every original point, area and sub-site row, with its GeoPackage geometry bytes, remains in the saved citation. The unchanged national export ZIP is retained in the offline collection.',className='atlas-help'),
                location_control(row['id'],'Show published register geometry'),
                _facts([('Export edition',original['source']['receipt']['last_modified']+' · retrieved '+original['source']['receipt']['retrieved_utc']),
                    ('Original export SHA-256',original['source']['receipt']['sha256']),
                    ('Rows',', '.join(feature['layer']+' fid '+str(feature['fid']) for feature in original['features']))]),
                html.Pre(json.dumps([feature['attributes'] for feature in original['features']],ensure_ascii=False,indent=2))]))
        elif row['source']=='france':
            children.append(html.Details([html.Summary('Complete original row and catalog edition'),
                html.P('Every original CSV field, row ordinal, source receipt and native catalog response remain in saved citations. Original CSV bytes are retained in the offline collection. No report or image is bundled.',className='atlas-help'),
                _facts(row['facts'][:7]),
                html.Pre(json.dumps(row['original']['original'],ensure_ascii=False,indent=2))]))
        elif row['source']=='raa':
            original=row['original']
            payload=original['original']
            children.append(html.Details([html.Summary('Original metadata, geometry and source edition'),
                html.P('All original geometry rows and attribute variants remain in the complete downloadable edition and captured project citation. Original national GeoPackages are retained in the offline collection.',className='atlas-help'),
                location_control(row['id'],'Show original assignment and disturbed-ground geometry'),
                html.Button('Download complete source record',id='atlas-raa-original',n_clicks=0,className='atlas-secondary-button'),
                _facts([('Source snapshot · '+name,receipt['last_modified']+' · retrieved '+receipt['retrieved_utc']+' · SHA-256 '+receipt['sha256']) for name,receipt in payload['source_receipts'].items()]),
                html.Pre(json.dumps(payload['variants'],ensure_ascii=False,indent=2))]))
            if original['archive_base64_bytes']>450_000:
                children.append(html.P('This geometry edition is large. Use a dig project below to retain its complete citation and a portable project backup.',className='atlas-help'))
        elif row['source'] == 'amcr':
            original = row['original']
            children.append(html.Details([html.Summary('Complete native record and source evidence'),
                _facts([('Original response SHA-256', original['receipt']['sha256']),
                    ('Parsed edition SHA-256', original['edition_sha256']), ('Record ordinal', str(original['source_ordinal'])),
                    ('Retrieved', original['receipt']['retrieved_utc']), ('Response URL', original['receipt']['url'])]),
                html.P('The source-page download contains the exact original response, including other records on that page. Parsed XML below regenerates namespace prefixes and formatting.', className='atlas-help'),
                html.Button('Download original response page', id='atlas-amcr-original', n_clicks=0, className='atlas-secondary-button'),
                html.Pre(original['parsed_xml']),
                *[html.Details([html.Summary('Supporting native vocabulary · ' + term['id']), html.Pre(term['xml'])]) for term in original['vocabulary']]]))
        elif row["source"] == "site_registers":
            original = row["original"]
            text = site_register_catalog.value_text
            children.append(html.Details([html.Summary("Published locations by source edition"),
                location_control(row["id"]),
                html.P(original["summary"]["location_note"], className="atlas-help")]))
            editions = []
            for edition in original["editions"]:
                metadata = edition["metadata"]
                attribution = [(label, "; ".join(item.get("label", item.get("id", "")) for item in metadata.get(key, [])))
                    for key, label in (("dc-terms:creator", "Table creators"), ("dc-terms:contributor", "Table contributors"))]
                attribution.extend((label, metadata.get(key) or "Not recorded") for key, label in
                    (("dc-terms:issued", "Table issued"), ("dc-terms:modified", "Table modified")))
                if edition["project"]:
                    attribution.append(("Source project rights", site_register_catalog.rights_text(edition["project"])))
                fragments = [html.Details([html.Summary("Adjacent unbound CSV fragment · record " + str(fragment["ordinal"])),
                    html.P("Native adjacent values remain separate. They are not assigned to the table's headers or repaired into the preceding site.", className="atlas-help"),
                    _facts(("Native column " + str(index + 1), text(value)) for index, value in enumerate(fragment["values"]))])
                    for fragment in edition["adjacent_fragments"]]
                editions.append(html.Details([html.Summary(metadata["label"]),
                    _facts(site_register_catalog.edition_facts(edition)), _facts(attribution),
                    html.Details([html.Summary("Original source fields"),
                        html.P(f'Original CSV record {edition["ordinal"]}; file lines {edition["line_start"]}–{edition["line_end"]}.', className="atlas-help"),
                        _facts(site_register_catalog.original_fields(edition))]),
                    *fragments, _source_link(edition["source_url"], "Read original source table")]))
            children.append(html.Details([html.Summary(f'{len(editions)} original table editions'), *editions]))
        elif row["source"] == "field_assemblages":
            original = row["original"]
            text = assemblage_catalog.value_text
            attributes = original["cells"]["attributes"]
            children.append(html.Details([html.Summary("Original source fields"),
                html.P(assemblage_catalog.source_locator(original), className="atlas-help"),
                html.P("Original file SHA-256: " + original["file"]["sha256"], className="atlas-help"),
                *([html.P(attributes["header_binding_basis"], className="atlas-help")] if attributes.get("header_binding_basis") else []),
                _facts(original["fields"]), _source_link(original["file"]["source_url"], "Read original source file")]))
            if attributes.get("display_headers") is not None:
                children.append(html.Details([html.Summary("Original header tokens"),
                    _facts(("Original header column " + str(index + 1), text(value)) for index, value in enumerate(original["headers"])),
                    html.P("These are the source's literal header tokens. The readable binding above is identified separately.", className="atlas-help")]))
            if attributes.get("instrument_header") is not None:
                children.append(html.Details([html.Summary("Original instrument line"),
                    _facts([("First line", text(attributes["instrument_header"])), ("Data line", text(attributes["original_line"]))])]))
            formulas = [cell for cell in original["cells"]["cells"] if "formula" in cell]
            if formulas:
                children.append(html.Details([html.Summary("Stored formulas and publisher results"),
                    _facts((cell["ref"], "Formula: " + text(cell["formula"]) + " · stored result: " + text(cell["cached_result"])) for cell in formulas),
                    html.P("Clovis retains stored expressions and results without recalculating the source workbook.", className="atlas-help")]))
            if original["merged_anchors"]:
                children.append(html.Details([html.Summary("Merged source cells"),
                    _facts((item["range"] + " · original anchor " + item["ref"], text(item["value"])) for item in original["merged_anchors"]),
                    html.P("Original row blanks remain blank; these values belong to the source's merged-cell anchors.", className="atlas-help")]))
            if original["associations"]:
                children.append(html.Details([html.Summary("How source records are associated"),
                    _facts((item["label"], item["basis"]) for item in original["associations"])]))
            children.append(html.Details([html.Summary("Source edition and attribution"),
                _facts([("Contributors", "; ".join(original["edition"]["contributors"])),
                        ("Institutions", "; ".join(original["edition"]["institutions"])),
                        ("Source edition", original["edition"]["edition"])]),
                _source_link(original["edition"]["citation_url"], "Read cited publication or dataset")]))
            if "Latitude (WGS-84)" in original["headers"] and "Longitude (WGS-84)" in original["headers"]:
                children.append(html.Details([html.Summary("Published location"), location_control(row["id"])]))
        elif row["source"] == "specimens":
            original = row["original"]
            editions = original["editions"]
            if original["kind"] == "context":
                representative = original["representative"]
                fields = [(header, zooarchaeology_catalog.value_text(value))
                          for header, value in zip(representative["headers"], representative["values"])
                          if header.startswith("Context (") or header in ("Context URI", "Project URI", "Project name", "Related person(s)")]
                children.append(html.Details([html.Summary("Original context reference"), _facts(fields),
                    html.P("These fields come from a specimen table row. Read the linked original rows for the separately recorded specimens and measurements.", className="atlas-help"),
                    _source_link(representative["table"]["source_url"], "Read this original source table")]))
            for edition in editions:
                table = edition["table"]
                children.append(html.Details([html.Summary(table["path"] + " · row " + str(edition["ordinal"])),
                    html.P("Original table SHA-256: " + table["sha256"], className="atlas-help"),
                    _facts(edition["fields"]), _source_link(table["source_url"], "Read original source table")]))
        elif row["source"] == "environments":
            original = row["original"]
            text = environment_catalog.value_text
            children.append(html.Details([html.Summary("Original source fields"),
                                         _facts((key, text(value)) for key, value in original["source"].items())]))
            context_fields = [(key, values) for key, values in original["associated"].items()
                              if key in ("sample", "dataset", "analysis", "chronology") and values]
            if context_fields:
                children.append(html.Details([html.Summary("Sample and collection context"),
                    *[html.Details([html.Summary(key.capitalize()), _facts((name, text(value)) for name, value in values.items())]) for key, values in context_fields]]))
            locations = environment_catalog.location_fields(original)
            if locations:
                children.append(html.Details([html.Summary("Published location"), location_control(row["id"]), *[_facts(fields) for fields in locations]]))
            if original["age_assignments"]:
                models = []
                for assignment in original["age_assignments"]:
                    chronology = assignment["chronology"]
                    models.append(html.Details([html.Summary(chronology.get("chronologyname") or "Chronology " + str(assignment["source"]["chronologyid"])),
                        _facts((key, text(value)) for key, value in assignment["source"].items()),
                        _facts((key, text(value)) for key, value in chronology.items()),
                        _facts((key, text(value)) for key, value in assignment["age_type"].items())]))
                children.append(html.Details([html.Summary(f'{original["age_assignments_total"]:,} sample age assignments'), *models,
                    html.P("These are age assignments from the original models. Dating measurements remain separate.", className="atlas-help"),
                    *([html.P(f'Showing {len(models):,} of {original["age_assignments_total"]:,} assignments. Open the associated age evidence to read the others.', className="atlas-help")]
                      if original["age_assignments_total"] > len(models) else [])]))
            meanings = [(key, values) for key, values in original["associated"].items()
                        if key in ("variable", "taxon", "variable_units", "element", "variable_context", "control_type", "date_type") and values]
            if meanings or original["uncertainties"] or original.get("radiocarbon"):
                children.append(html.Details([html.Summary("Variable meanings and measurement details"),
                    *[html.Details([html.Summary(key.replace("_", " ").capitalize()), _facts((name, text(value)) for name, value in values.items())]) for key, values in meanings],
                    *[_facts((key, text(value)) for key, value in row.items()) for row in original["uncertainties"]],
                    *[_facts((key, text(value)) for key, value in meaning[group].items())
                      for meaning in original["uncertainty_meanings"] for group in ("unit", "basis")],
                    _facts((key, text(value)) for key, value in original.get("radiocarbon", {}).items())]))
            if original["publications"] or original["dataset_dois"]:
                children.append(html.Details([html.Summary("Source publications and dataset identifiers"),
                    *[html.Div([html.P(publication.get("citation") or "Publication " + publication["publicationid"]),
                        _facts((key, text(publication[key])) for key in ("publicationid", "articletitle", "booktitle", "year", "journal", "volume", "issue", "pages", "publisher", "doi", "url") if key in publication),
                        _source_link(publication.get("url"), "Read source publication")]) for publication in original["publications"]],
                    *[_facts((key, text(value)) for key, value in row.items()) for row in original["dataset_dois"]]]))
        elif row["source"] == "assemblages":
            original = row["original"]
            children.append(html.Details([html.Summary("Original source fields"), _facts(original["source"].items())]))
            for key, title in (("animal_recovery", "Animal recovery methods"), ("plant_sampling", "Plant sampling phase"),
                               ("plant_recovery", "Plant recovery methods")):
                fields = original["associated"].get(key)
                if fields:
                    children.append(html.Details([html.Summary(title), _facts(fields.items())]))
        elif row["source"] == "contexts":
            original = row["original"]
            locations = excavation_catalog.location_time_fields(original)
            if locations:
                children.append(html.Details([html.Summary("Published location and time"),
                    *[_facts(fields) for fields in locations],
                    html.P("Location references and precision retain the publisher's wording. Source ISO years use 0000 for 1 BCE.", className="atlas-help")]))
            for observation in original["observations"]:
                children.append(html.Details([html.Summary(observation.get("label", observation["id"])),
                    _facts(excavation_catalog.observation_fields(observation, original["definitions"]))]))
            if original["tables"]:
                children.append(html.Details([html.Summary("Original published table fields"), *[
                    html.Details([html.Summary(table["title"]),
                                  html.Dl([node for key, value in table["fields"].items() for node in
                                           (html.Dt(key.split(" [", 1)[0], title=key), html.Dd(value if value != "" else "Not recorded"))],
                                          className="clovis-library-facts"),
                                  _source_link(table["uri"], "Read source table")]) for table in original["tables"]]]))
            definitions = excavation_catalog.definition_fields(original)
            if definitions:
                children.append(html.Details([html.Summary("Field meanings and units"), *[
                    html.Div([html.H4(group["label"]), _facts(group["fields"]),
                              _source_link(group["source_uri"], "Read original field definition")]) for group in definitions]]))
        elif row["source"] == "places":
            original = row["original"]["source"]
            text = pleiades_catalog.value_text
            children.append(html.Details([html.Summary("Published names"), *[
                html.Details([html.Summary(name.get("romanized") or name.get("attested") or name["id"]),
                    _facts((key, text(name.get(key))) for key in ("attested", "romanized", "language", "nameType", "associationCertainty", "start", "end", "attestations"))])
                for name in original["names"]]]))
            children.append(html.Details([html.Summary("Published location records"), location_control(row["id"]), *[
                html.Details([html.Summary(location.get("title") or location["id"]),
                    _facts((key, text(location.get(key))) for key in ("description", "locationType", "associationCertainty", "accuracy_value", "accuracy", "start", "end", "attestations", "provenance"))])
                for location in original["locations"]]]))
            children.append(html.Details([html.Summary("Native connections and bibliography"), *[
                html.Details([html.Summary(link.get("title") or link["id"]),
                    _facts((key, text(link.get(key))) for key in ("connectsTo", "connectionType", "associationCertainty", "start", "end", "attestations"))])
                for link in original["connections"]],
                *[html.P(pleiades_catalog.plain(reference.get("formattedCitation") or reference.get("shortTitle")))
                  for reference in original["references"]]]))
            children.append(html.Details([html.Summary("Source attribution and complete original data"),
                _facts([("Creators", pleiades_catalog.authors(original, "creators")),
                        ("Contributors", pleiades_catalog.authors(original, "contributors")),
                        ("Native copyright notice", original["rights"]),
                        ("Native place-object SHA-256", row["original"]["source_sha256"])]),
                _source_link(row["original"]["license_url"], "Read this record's licence"),
                html.A("Download complete native JSON", href="/atlas/source/pleiades/" + original["id"] + ".json", className="atlas-secondary-button"),
                html.P("The download retains every original field, numeric token, citation and editing-history entry. Dates for names and locations remain separate; editing history dates refer to the gazetteer resource.", className="atlas-help")]))
        elif row["source"] == "dinosaurs":
            original = row["original"].get("source")
            if original:
                children.append(html.Details([html.Summary("Original occurrence fields"), _facts(row["original"].get("source_fields",list(original.items())))]))
                children.append(html.Details([html.Summary("Published location"), location_control(row["id"])]))
        children += [html.Details([html.Summary("Evidence conventions"), *[html.P(note) for note in row["notes"]]]),
                     _source_link(row["source_url"], "Read original source"), html.P(row["license"], className="atlas-help"),
                     html.Button("Save source to fieldbook", id="atlas-save", n_clicks=0, className="atlas-primary-button"),
                     html.Div(id="atlas-save-status", role="status", className="atlas-help")]
        return children
    except ERRORS:
        return html.P("Choose a record from the current atlas search.")


@callback(Output({"type": "atlas-location-view", "index": MATCH}, "children"),
          Input({"type": "atlas-location-open", "index": MATCH}, "n_clicks"),
          State("atlas-selected", "data"), State("atlas-query", "value"), State("atlas-kind", "value"),
          State("atlas-source", "value"), State("atlas-context", "data"), State("atlas-page", "data"),
          State({"type": "atlas-location-open", "index": MATCH}, "id"),
          prevent_initial_call=True)
def published_map(clicks, selected, query, kind, source, context, page, button):
    if not clicks:
        return no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row is not None and isinstance(button, dict) and button.get("index") == row["id"]:
            return location_map(row)
    except ERRORS:
        pass
    return html.P("Choose a record from the current atlas search.", className="atlas-help")


@callback(Output("atlas-context", "data"), Output("atlas-query", "value", allow_duplicate=True),
          Input({"type": "atlas-related", "index": ALL}, "n_clicks"),
          Input("atlas-clear-context", "n_clicks"), Input("atlas-kind", "value"), Input("atlas-source", "value"),
          State("atlas-selected", "data"), State("atlas-query", "value"), State("atlas-context", "data"),
          State("atlas-page", "data"), prevent_initial_call=True)
def associated(clicks, _clear, kind, source, selected, query, context, page):
    trigger = callback_context.triggered_id
    if trigger in ("atlas-clear-context", "atlas-kind", "atlas-source"):
        if source in ('ads', 'amcr', 'dans','raa','france','finland'):
            # Source controls reset their visible values and limits together.
            return no_update, no_update
        return None, no_update
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return no_update, no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row:
            for link in catalog.relationships(row):
                if link["key"] == trigger["index"]:
                    # The originating search term need not occur in its linked deposit.
                    parameters = dict(link['parameters'])
                    label = row['title'] + ' · ' + link['label']
                    if row['source'] == 'dans':
                        previous = context.get('parameters', {}) if isinstance(context, dict) else {}
                        if previous.get('collection') == 'dans':
                            parameters.update({key: previous[key] for key in ('subject', 'field') if key in previous})
                        label += ' · Subject and metadata field retained; search words cleared'
                    return {'parameters': parameters, 'label': label}, ""
    except ERRORS:
        pass
    return no_update, no_update


@callback(Output('atlas-raa-download','data'),Input('atlas-raa-original','n_clicks'),
          State('atlas-selected','data'),State('atlas-query','value'),State('atlas-kind','value'),State('atlas-source','value'),
          State('atlas-context','data'),State('atlas-page','data'),prevent_initial_call=True)
def original_raa_record(clicks,selected,query,kind,source,context,page):
    if type(clicks) is not int or clicks<1:
        return no_update
    try:
        record=current(selected,query,kind,source,context,page)
        if record is not None and record['source']=='raa':
            original=record['original']
            return dcc.send_bytes(raa_fieldwork_catalog.canonical(original['original']),
                'raa-assignment-'+original['uuid']+'-'+original['edition_sha256'][:12]+'.json',type='application/json')
    except ERRORS:
        pass
    return no_update


@callback(Output('atlas-ads-download', 'data'), Input('atlas-ads-original', 'n_clicks'),
          State('atlas-selected', 'data'), State('atlas-query', 'value'), State('atlas-kind', 'value'),
          State('atlas-source', 'value'), State('atlas-context', 'data'), State('atlas-page', 'data'),
          prevent_initial_call=True)
def original_ads_metadata(clicks, selected, query, kind, source, context, page):
    if type(clicks) is not int or clicks < 1:
        return no_update
    try:
        record = current(selected, query, kind, source, context, page)
        if record is not None and record['source'] == 'ads':
            original = record['original']
            return dcc.send_bytes(original['native'], 'ads-metadata-' + original['source_sha256'][:16] + '.json', type='application/json')
    except ERRORS:
        pass
    return no_update


@callback(Output('atlas-dans-download', 'data'), Input('atlas-dans-original', 'n_clicks'),
          State('atlas-selected', 'data'), State('atlas-query', 'value'), State('atlas-kind', 'value'),
          State('atlas-source', 'value'), State('atlas-context', 'data'), State('atlas-page', 'data'),
          prevent_initial_call=True)
def original_dans_metadata(clicks, selected, query, kind, source, context, page):
    if type(clicks) is not int or clicks < 1:
        return no_update
    try:
        record = current(selected, query, kind, source, context, page)
        if record is not None and record['source'] == 'dans':
            original = record['original']
            return dcc.send_bytes(original['native'], 'dans-metadata-' + original['source_sha256'][:16] + '.json', type='application/json')
    except ERRORS:
        pass
    return no_update


@callback(Output('atlas-amcr-download', 'data'), Input('atlas-amcr-original', 'n_clicks'),
          State('atlas-selected', 'data'), State('atlas-query', 'value'), State('atlas-kind', 'value'),
          State('atlas-source', 'value'), State('atlas-context', 'data'), State('atlas-page', 'data'), prevent_initial_call=True)
def original_amcr_page(clicks, selected, query, kind, source, context, page):
    if type(clicks) is not int or clicks < 1:
        return no_update
    try:
        record = current(selected, query, kind, source, context, page)
        if record is not None and record['source'] == 'amcr':
            original = record['original']
            return dcc.send_bytes(original['native_page'], 'amcr-response-' + original['receipt']['sha256'][:16] + '.xml', type='application/xml')
    except ERRORS:
        pass
    return no_update


@callback(Output("atlas-source", "value"), Output("atlas-kind", "value"),
          Input({"type": "data-pack-open", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def open_pack(clicks):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return no_update, no_update
    identifier = trigger.get("index")
    try:
        if identifier in PACK_SOURCES and PackStore().status(identifier)["state"] == "installed":
            return PACK_SOURCES[identifier], "all"
    except ERRORS:
        pass
    return no_update, no_update


@callback(Output("fieldbook-store", "data", allow_duplicate=True), Output("atlas-save-status", "children"),
          Input("atlas-save", "n_clicks"), State("atlas-selected", "data"), State("atlas-query", "value"),
          State("atlas-kind", "value"), State("atlas-source", "value"), State("atlas-context", "data"),
          State("atlas-page", "data"), State("fieldbook-store", "data"), prevent_initial_call=True)
def save(clicks, selected, query, kind, source, context, page, book):
    if not clicks:
        return no_update, no_update
    try:
        row = current(selected, query, kind, source, context, page)
        if row is None:
            return no_update, "Choose a record from the current search."
        entry = catalog.reference_entry(row["id"])
        if len(entry['markdown'].encode('utf-8')) > MAX_ENTRY_BYTES:
            return no_update, ('This complete citation is too large for the browser fieldbook. '
                'Open Use in a dig project, choose a saved project and use Save and open project source. '
                'Create a project in Fieldbook → Dig records if needed.')
        return merge_entries(EMPTY_BOOK if book is None else book, [entry]), "Source reference saved to fieldbook."
    except (*ERRORS, UnicodeError):
        return no_update, "The source could not be saved. Check the selected record and fieldbook capacity."


@callback(Output('atlas-dig-tools','style'), Input('atlas-selected','data'))
def project_tools(selected):
    return {} if isinstance(selected,dict) and selected.get('id') else {'display':'none'}


@callback(Output('atlas-dig-project','options'), Output('atlas-dig-project','value'),
          Input('atlas-selected','data'), Input('dig-refresh','data'),
          State('atlas-dig-project','value'), State('dig-project','value'))
def project_choices(_selected, _refresh, chosen, active):
    try:
        options=[{'label':row['code']+' · '+row['title'],'value':row['id']} for row in DigBook().projects()]
        known={row['value'] for row in options}
        value=chosen if isinstance(chosen,str) and chosen in known else active if isinstance(active,str) and active in known else None
        return options,value
    except ERRORS:
        return [],None


@callback(Output('atlas-dig-status','children'), Output('dig-status','children',allow_duplicate=True),
          Output('dig-refresh','data',allow_duplicate=True), Output('dig-project-request','data',allow_duplicate=True),
          Output('dig-open-request','data'), Output('workflow-mode','value',allow_duplicate=True),
          Output('fieldbook-section','value',allow_duplicate=True),
          Input('atlas-dig-capture','n_clicks'), State('atlas-selected','data'), State('atlas-query','value'),
          State('atlas-kind','value'), State('atlas-source','value'), State('atlas-context','data'), State('atlas-page','data'),
          State('atlas-dig-project','value'), State('atlas-dig-code','value'), prevent_initial_call=True,
          running=[(Output('atlas-dig-capture','disabled'),True,False),
                   (Output('atlas-dig-capture','children'),'Saving source…','Save and open project source')])
def capture_project_source(clicks, selected, query, kind, source, context, page, project, code):
    if type(clicks) is not int or clicks<1:
        return (no_update,)*7
    try:
        row=current(selected,query,kind,source,context,page)
        if row is None:
            raise ValueError('Choose a record from the current Atlas search.')
        result=project_references.capture(project,code,row['id'])
        saved=result['record']
        message=('Saved ' if result['created'] else 'Opened existing source ')+saved['data']['code']+' in your local project.'
        request={'project_id':project,'id':saved['id'],'nonce':uuid4().hex}
        return message,message,time.time_ns(),project,request,'notebook','dig'
    except (*ERRORS,UnicodeError) as error:
        message=str(error) if isinstance(error,ValueError) else 'The source could not be saved. Check the selected record and local project.'
        return message,*(no_update,)*6
