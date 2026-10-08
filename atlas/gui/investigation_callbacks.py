"""Connect in-app evidence tools to guided observations and the existing fieldbook."""
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core.evidence_board import note_context as geological_note_context
from core.fieldbook import EMPTY_BOOK, merge_entries, validate_book
from core.historical_maps import validated_note_context
from core.investigations import MISSIONS, investigation_entry
from core.resident_context import current_report
from core.us_places import get_place, search_places


@callback(Output('workflow-mode','value',allow_duplicate=True), Output('resident-tool','value'),
          Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'), prevent_initial_call=True)
def open_workbench_tool(clicks):
    target = callback_context.triggered_id
    if not isinstance(target, dict) or not any(clicks or []):
        return no_update, no_update
    value = target.get('target')
    if value == 'inspect':
        return 'inspect', no_update
    return ('resident', value) if value in ('map','archive','missions') else (no_update, no_update)


@callback(Output('resident-state','value'), Output('resident-place','options',allow_duplicate=True),
          Output('resident-place','disabled',allow_duplicate=True),Output('resident-place','value'),
          Output('resident-build','n_clicks'), Input('resident-demo','n_clicks'),
          Input('resident-state','value'), State('resident-place','value'),
          State('resident-build','n_clicks'), prevent_initial_call=True)
def explore_example(clicks, state, geoid, previous):
    if callback_context.triggered_id == 'resident-state':
        return no_update, no_update, no_update, no_update if get_place(geoid,state) else None, no_update
    if callback_context.triggered_id != 'resident-demo' or not clicks:
        return no_update, no_update, no_update, no_update, no_update
    town = next(row for row in search_places('OH','Cincinnati') if row['label']=='Cincinnati city, OH')
    previous = previous if type(previous) is int and 0 <= previous < 10_000_000 else 0
    return 'OH', [town], False, town['value'], previous + 1


@callback(Output('resident-welcome','style'), Output('resident-evidence-overview','children'),
          Input('resident-report-store','data'), Input('resident-state','value'), Input('resident-place','value'),
          Input('resident-history','value'), Input('resident-online','value'), Input('workflow-mode','value'))
def report_overview(token,state,geoid,history,online,mode):
    report = current_report(token,state,geoid,history,online)
    welcome = {'display':'none'} if report or mode != 'resident' else {'display':'block'}
    if report is None:
        return welcome, html.P('Build your town evidence, or open Historical maps to investigate a source directly.',className='atlas-help')
    items = [('Rock maps',str(report['unit_count'])),('Reviewed fossil guides',str(len(report.get('guides',[])))),('Discovery odds','Unknown')]
    return welcome, html.Div([
        html.Div([html.Strong(value),html.Span(label)],className='clovis-evidence-metric') for label,value in items
    ],className='clovis-evidence-metrics')


@callback(Output('mission-type','value'), Output('resident-tool','value',allow_duplicate=True),
          Output('workflow-mode','value',allow_duplicate=True), Output('mission-source','value'), Output('mission-date','value'),
          Output('mission-notes','value'), Output('archive-save-status','children'),
          Input({'type':'mission-start','mission':ALL},'n_clicks'), Input('archive-record-note','n_clicks'),
          Input('geology-record-note','n_clicks'),
          State('archive-note-context','data'),State('geology-note-context','data'),
          State('resident-report-store','data'), State('resident-state','value'),State('resident-place','value'),
          State('resident-history','value'),State('resident-online','value'), prevent_initial_call=True)
def start_investigation(clicks,archive_clicks,geology_clicks,archive_context,geology_context,token,state,geoid,history,online):
    trigger = callback_context.triggered_id
    empty = (no_update,)*7
    if trigger == 'archive-record-note':
        context = validated_note_context(archive_context,state,geoid)
        if context is None:
            return (*empty[:6], 'Select a current map or open your own image before recording its evidence.')
        source = (context['title']+' — '+context['source'])[:1000]
        return 'history','missions','resident',source,context['date'][:120],context['notes'][:1500], 'Map evidence moved to your investigation. Review it and save to the fieldbook.'
    if trigger == 'geology-record-note':
        report = current_report(token,state,geoid,history,online)
        contexts = [geological_note_context(report,f'unit-{u["map_id"]}') for u in report.get('units',[])] if report else []
        if not isinstance(geology_context,dict) or geology_context not in contexts:
            return empty
        source = (geology_context['title']+' — '+geology_context['source'])[:1000]
        return 'rocks','missions','resident',source,geology_context['date'][:120],'',no_update
    if isinstance(trigger,dict) and trigger.get('mission') in MISSIONS and any(clicks or []):
        mission = trigger['mission']
        report = current_report(token,state,geoid,history,online)
        unit = report.get('units',[None])[0] if report and report.get('units') else None
        source = (unit['name']+' — '+unit['reference'])[:1000] if unit and mission=='rocks' else ''
        date = unit.get('interval','') if unit and mission=='rocks' else ''
        return mission,'missions','resident',source,date,'',no_update
    return empty


@callback(Output('mission-evidence','children'),Output('mission-steps','options'),Output('mission-steps','value'),
          Output('mission-notes','placeholder'), Input('mission-type','value'),
          Input('resident-report-store','data'),Input('resident-state','value'),Input('resident-place','value'),
          Input('resident-history','value'),Input('resident-online','value'))
def investigation_guide(mission,token,state,geoid,history,online):
    guide = MISSIONS.get(mission) if isinstance(mission,str) else None
    guide = guide or MISSIONS['rocks']
    place = get_place(geoid,state)
    report = current_report(token,state,geoid,history,online)
    evidence = [html.H3(guide['title']),html.P(guide['prompt'])]
    if place:
        evidence.append(html.P(f"Working around {place['name']}, {place['state']}. Record only broad public place context."))
    else:
        evidence.append(html.P('Choose a town in the place setup before saving this investigation.'))
    if mission=='rocks' and report and report.get('units'):
        evidence.append(html.P('Your current map materials: '+ '; '.join(unit['lithology'] or unit['name'] for unit in report['units'][:3])))
    return evidence, [{'label':step,'value':i} for i,step in enumerate(guide['steps'])],[],guide['prompt']


@callback(Output('mission-save','disabled'),Input('mission-notes','value'),Input('resident-state','value'),Input('resident-place','value'))
def can_save_investigation(notes,state,geoid):
    return not (get_place(geoid,state) and isinstance(notes,str) and notes.strip())


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('mission-save-status','children'),
          Input('mission-save','n_clicks'), State('fieldbook-store','data'),State('mission-type','value'),
          State('resident-state','value'),State('resident-place','value'),State('mission-source','value'),
          State('mission-date','value'),State('mission-notes','value'),State('mission-outcome','value'),
          State('mission-steps','value'),prevent_initial_call=True)
def save_investigation(clicks,book,mission,state,geoid,source,date,notes,outcome,steps):
    if not clicks:
        return no_update,no_update
    try:
        row = investigation_entry(mission,state,geoid,source or '',date or '',notes or '',outcome,steps)
        merged = merge_entries(book or EMPTY_BOOK,[row])
        return merged, f"Saved to your fieldbook · {len(merged['entries'])} saved records."
    except (ValueError,TypeError,UnicodeError,RecursionError) as exc:
        return no_update,str(exc)


@callback(Output('fieldbook-metrics','children'),Input('fieldbook-store','data'))
def fieldbook_progress(book):
    try:
        rows = validate_book(book or EMPTY_BOOK)['entries']
    except ValueError:
        return []
    metrics = [('Saved records',len(rows)),('Source investigations',sum(r['kind']=='investigation' for r in rows)),
               ('Object observations',sum(r['kind']=='find' for r in rows)),('Follow-up records',sum('follow_up' in r['summary'] and '· follow-up' in r['title'] for r in rows))]
    return [html.Div([html.Strong(str(value)),html.Span(label)]) for label,value in metrics]
