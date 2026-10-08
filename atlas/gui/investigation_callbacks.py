"""Connect in-app evidence tools to guided observations and the existing fieldbook."""
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core.evidence_board import note_context as geological_note_context
from core.fieldbook import EMPTY_BOOK, merge_entries, validate_book
from core.historical_maps import validated_note_context
from core.investigations import MISSIONS, investigation_entry
from core.resident_context import current_report
from core.us_places import get_place
from core.example_catalog import get_example, pick_example
from core.town_knowledge import knowledge_for_place


@callback(Output('workflow-mode','value',allow_duplicate=True), Output('resident-tool','value'),
          Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'), prevent_initial_call=True)
def open_workbench_tool(clicks):
    target = callback_context.triggered_id
    if not isinstance(target, dict) or not any(clicks or []):
        return no_update, no_update
    value = target.get('target')
    if value == 'inspect':
        return 'inspect', no_update
    if value == 'notebook':
        return 'notebook', no_update
    return ('resident', value) if value in ('map','archive','missions','library') else (no_update, no_update)


@callback(Output('resident-state','value'), Output('resident-place','options',allow_duplicate=True),
          Output('resident-place','disabled',allow_duplicate=True),Output('resident-place','value'),
          Output('resident-build','n_clicks'), Output('resident-history','value'),
          Output('resident-example-store','data'), Output('resident-tool','value',allow_duplicate=True),
          Input('resident-demo','n_clicks'), Input('resident-state','value'),
          Input('resident-place','value'), Input('resident-example-dismiss','n_clicks'),
          State('resident-build','n_clicks'), State('resident-example-store','data'), prevent_initial_call=True)
def explore_example(clicks, state, geoid, dismissed, previous, saved):
    trigger = callback_context.triggered_id
    empty = (no_update,)*8
    old_id = saved.get('id') if isinstance(saved,dict) else None
    old = get_example(old_id)
    if trigger != 'resident-demo':
        clear = trigger=='resident-example-dismiss' or (old and (old['state'],old['geoid'])!=(state,geoid))
        selected = no_update if get_place(geoid,state) else None
        return no_update,no_update,no_update,selected,no_update,no_update,({'id':old_id,'active':False} if clear else no_update),no_update
    if not clicks:
        return empty
    example = pick_example(old_id)
    town = {'label':example['label'],'value':example['geoid']}
    previous = previous if type(previous) is int and 0 <= previous < 10_000_000 else 0
    return example['state'],[town],False,town['value'],previous+1,'unknown',{'id':example['id'],'active':True},'map'


@callback(Output('resident-example-panel','style'), Output('resident-example-summary','children'),
          Input('resident-example-store','data'),Input('resident-state','value'),
          Input('resident-place','value'),Input('workflow-mode','value'))
def show_example(saved,state,geoid,mode):
    example = get_example(saved.get('id')) if isinstance(saved,dict) and saved.get('active') is True else None
    if not example or mode!='resident' or (example['state'],example['geoid'])!=(state,geoid):
        return {'display':'none'},[]
    return {'display':'flex'},[html.Details([
        html.Summary([
            html.Span(f"Example {example['number']}/100",className='clovis-example-topic'),
            html.Span(example['question'],className='clovis-example-title'),
        ]),
        html.P(example['prompt'],className='clovis-example-summary'),
    ],className='clovis-example-guidance',key=example['id'])]


@callback(Output('resident-evidence-overview','children'),
          Input('resident-report-store','data'), Input('resident-state','value'), Input('resident-place','value'),
          Input('resident-history','value'), Input('resident-online','value'), Input('workflow-mode','value'))
def report_overview(token,state,geoid,history,online,mode):
    report = current_report(token,state,geoid,history,online)
    place=get_place(geoid,state)
    if place is None:
        return html.P('Build your town evidence, or open Historical maps to investigate a source directly.',className='atlas-help')
    knowledge=report.get('knowledge') if report else None
    knowledge=knowledge if isinstance(knowledge,dict) else knowledge_for_place(place)
    stats=knowledge['maps']
    regional=knowledge['regional_maps']
    children=[]
    offline_units=knowledge.get('usgs_units',[])
    if offline_units:
        children.append(html.Div([html.Strong('Regional geology · Offline USGS map'),
            *[html.P([html.Strong(unit['name']+': '),' · '.join(v for v in (unit.get('age',''),unit.get('geomaterial','')) if v)]) for unit in offline_units[:2]],
            html.Button('Read mapped units →',id={'type':'workbench-action','target':'library','key':'town-units'},n_clicks=0,className='atlas-secondary-button')],className='clovis-town-catalog'))
    if stats['maps']:
        label=f"{stats['maps']:,} dated town maps"
        text=f"Sanborn editions indexed to this town · {stats.get('earliest') or ''} to {stats.get('latest') or ''}"
    else:
        label=f"{regional['maps']:,} historic state maps"
        text='Browse the statewide collection. This snapshot has no exact town-name match.'
    children.append(html.Div([html.Strong(label),html.Span(text),
        html.Button('Read the old maps →',id={'type':'workbench-action','target':'archive','key':'town-catalog'},n_clicks=0,className='atlas-secondary-button')],className='clovis-town-catalog'))
    news=knowledge.get('newspapers')
    if news and news['titles']:
        first=knowledge.get('newspaper_records',[])
        children.append(html.Div([html.Strong(f"{news['titles']:,} newspaper title records"),
            html.P((first[0]['title']+' · '+first[0].get('publication_dates','')) if first else 'Publication timelines and languages recorded by LOC'),
            html.Small('Partial directory snapshot · no article text'),
            html.Button('Read newspaper history →',id={'type':'workbench-action','target':'library','key':'town-newspapers'},n_clicks=0,className='atlas-secondary-button')],className='clovis-town-catalog'))
    chapter=knowledge.get('chapter')
    if isinstance(chapter,dict) and chapter.get('facts'):
        children.append(html.Div([html.Strong(chapter['name']+' fossil story'),html.P(chapter['facts'][0]['text']),
            html.Button('Read the state chapter →',id={'type':'workbench-action','target':'library','key':'state-chapter'},n_clicks=0,className='atlas-secondary-button')],className='clovis-town-catalog'))
    if report and report.get('geology_status')=='available':
        items=[('Mapped units',str(report['unit_count'])),('Formation guides',str(len(report.get('guides',[]))))]
        children.append(html.Div([html.Div([html.Strong(value),html.Span(label)],className='clovis-evidence-metric') for label,value in items],className='clovis-evidence-metrics'))
    elif report:
        children.append(html.P('Live rock maps are off.' if report.get('geology_status')=='not_requested' else 'Live rock maps could not load; bundled sources remain available.',className='atlas-help'))
    children.append(html.P('Town and state context · Backyard discovery odds are not estimated.',className='clovis-scope-note'))
    return children


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
    followups = {r['id'] for r in rows if r['summary'].get('mission') not in ('Expert question','Expert response')
                 and 'follow_up' in r['summary'] and '· follow-up' in r['title']}
    questions = sum(r['summary'].get('mission')=='Expert question' and r['id'] not in followups for r in rows)
    responses = sum(r['summary'].get('mission')=='Expert response' and r['id'] not in followups for r in rows)
    metrics = [('Saved records',len(rows)), ('Notes & investigations',len(rows)-questions-responses-len(followups)),
               ('Questions',questions), ('Responses & follow-ups',responses+len(followups))]
    return [html.Div([html.Strong(str(value)),html.Span(label)]) for label,value in metrics]
