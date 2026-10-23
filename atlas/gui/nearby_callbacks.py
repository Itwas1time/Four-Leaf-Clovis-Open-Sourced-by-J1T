"""Published records near the chosen town, from installed collections' own coordinates."""
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from atlas.gui.workspace_activation import when_opened
from core.nearby_records import nearby
from core.resident_context import current_report
from core.us_places import get_place

RADIUS_KM = 30
ATLAS_SOURCES = {'environments': 'environments', 'site_registers': 'site_registers', 'dinosaurs': 'dinosaurs', 'finland': 'finland'}


@when_opened(('map', 'archive', 'missions'), Output('resident-nearby', 'children'), Output('resident-nearby-poll', 'disabled'),
             Input('resident-report-store', 'data'), Input('resident-state', 'value'), Input('resident-place', 'value'),
             Input('resident-nearby-poll', 'n_intervals'),
             State('resident-history', 'value'), State('resident-online', 'value'))
def nearby_records(token, state, geoid, _ticks, history, online):
    place = get_place(geoid, state)
    if place is None or current_report(token, state, geoid, history, online) is None:
        return [], True
    try:
        # This selector contains U.S. Census places. Do not prepare the national
        # Finnish register for a U.S. town investigation.
        result = nearby(place['latitude'], place['longitude'], RADIUS_KM,
                        sources=('environments','site_registers','dinosaurs'))
    except (ValueError, OSError):
        return [html.P('Nearby published records could not be read.', className='atlas-help')], True
    children = [html.H3(f'Nearby published evidence · {RADIUS_KM} km'),
                html.P(f"Distances from the public Census point for {place['name']}, {place['state']}. "
                       'Positions are the publishers\' own, often approximate. These are not finds or property locations.',
                       className='atlas-help')]
    for group in result['groups']:
        children.append(html.Details([
            html.Summary(f"{group['label']} · {group['total']:,} reference locations"),
            html.P(group['note'], className='atlas-help'),
            html.Ul([html.Li([html.Strong(row['label']), html.Span(f" · about {row['distance_km']} km · {row['note']} "),
                              html.Button('Find in Atlas', n_clicks=0, className='atlas-secondary-button',
                                          id={'type': 'nearby-find', 'index': group['source'] + '|' + row['ref']+'|'+str(row['point_id'])})])
                     for row in group['rows']]),
        ], open=True))
    if not result['groups'] and not result['preparing'] and not result['errors']:
        children.append(html.P(f'No installed collection publishes coordinates within {RADIUS_KM} km of this town.',
                               className='atlas-help'))
    if result['preparing']:
        children.append(html.P('Preparing nearby records for ' + ', '.join(result['preparing'])
                               + ' (first use only). You can continue reading the ready sources.', className='atlas-help', role='status'))
    for source,message in result['errors'].items():
        from core.nearby_records import LABELS
        children.append(html.P(LABELS[source]+': '+message,className='atlas-help',role='status'))
    children.append(html.P(result['coverage'], className='atlas-help'))
    return children, not result['preparing']


@callback(Output('resident-tool', 'value', allow_duplicate=True), Output('atlas-source', 'value', allow_duplicate=True),
          Output('atlas-kind', 'value', allow_duplicate=True), Output('atlas-query', 'value', allow_duplicate=True),
          Output('atlas-context','data',allow_duplicate=True),
          Input({'type': 'nearby-find', 'index': ALL}, 'n_clicks'), prevent_initial_call=True)
def find_in_atlas(clicks):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return (no_update,)*5
    parts=str(trigger.get('index','')).split('|')
    if len(parts)!=3:
        return (no_update,)*5
    source,reference,_point=parts
    if source not in ATLAS_SOURCES or not reference:
        return (no_update,)*5
    if source=='finland':
        reference=reference.partition('/')[2].partition('~')[0]
    return 'library', ATLAS_SOURCES[source], 'all', reference[:120], None
