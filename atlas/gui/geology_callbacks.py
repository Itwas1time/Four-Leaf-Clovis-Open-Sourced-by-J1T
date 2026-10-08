"""Read only current server reports; tile opt-in never queries browser coordinates."""
from dash import ALL, Input, Output, callback, callback_context
import dash_leaflet as dl
from core.evidence_board import evidence_board, note_context
from core.resident_context import current_report
from atlas.gui.geology_ui import TILE_URL, evidence_card, evidence_detail
from atlas.gui.learning_ui import glossary_results


@callback(Output('geology-word-results','children'), Input('geology-word-search','value'))
def explain_geology_word(query):
    return glossary_results(query)


@callback(Output('resident-evidence-cards', 'children'), Output('resident-evidence-status', 'children'),
          Input('resident-report-store', 'data'), Input('resident-state', 'value'),
          Input('resident-place', 'value'), Input('resident-history', 'value'), Input('resident-online', 'value'))
def render_evidence(token, state, geoid, history, online):
    board = evidence_board(current_report(token, state, geoid, history, online))
    cards = [evidence_card(card) for card in board['cards']]
    if not cards:
        cards = ['No current mapped unit cards. An offline report or missing coverage cannot establish an absence of finds.']
    elif not any(card['kind'] == 'Reviewed formation guide' for card in board['cards']):
        cards.append('No reviewed formation guide matched these units. This is a catalogue gap, not evidence of no fossils.')
    checked = f" Checked {board['checked_at']}." if board.get('checked_at') else ''
    return cards, board['status'] + checked


@callback(Output('resident-evidence-detail', 'children'),
          Output('geology-note-context', 'data'), Output('geology-record-note', 'disabled'),
          Input({'type': 'resident-evidence-card', 'key': ALL}, 'n_clicks'),
          Input('resident-report-store', 'data'), Input('resident-state', 'value'),
          Input('resident-place', 'value'), Input('resident-history', 'value'), Input('resident-online', 'value'))
def select_evidence(clicks, token, state, geoid, history, online):
    selected = callback_context.triggered_id
    report = current_report(token, state, geoid, history, online)
    board = evidence_board(report)
    key = selected.get('key') if isinstance(selected, dict) and any(clicks or []) else None
    context = note_context(report, key)
    return evidence_detail(next((card for card in board['cards'] if card['id'] == key), None)), context, context is None


@callback(Output('resident-geology-layer', 'children'), Output('resident-geology-status', 'children'),
          Input('resident-geology-toggle', 'value'), Input('resident-geology-opacity', 'value'),
          Input('resident-report-store', 'data'), Input('resident-state', 'value'),
          Input('resident-place', 'value'), Input('resident-history', 'value'), Input('resident-online', 'value'),
          Input('resident-tool', 'value'), Input('workflow-mode', 'value'))
def show_geology_overlay(enabled, opacity, token, state, geoid, history, online, tool, mode):
    if not isinstance(enabled, list) or enabled != ['geology']:
        return [], 'Geology overlay off. No Macrostrat map tiles requested.'
    report = current_report(token, state, geoid, history, online)
    if mode != 'resident' or tool != 'map':
        return [], 'Geology overlay paused outside the town map tool.'
    if report is None:
        return [], 'Build a current town report to enable the geology overlay.'
    if online != ['geology']:
        return [], 'Online geology is off. Enable it and rebuild the town report before showing tiles.'
    if report.get('geology_status') != 'available':
        return [], 'No current mapped geology is available for this town; overlay paused.'
    if isinstance(opacity, bool) or not isinstance(opacity, (int, float)):
        opacity = 0.5
    opacity = max(0.15, min(0.85, opacity))
    layer = dl.TileLayer(url=TILE_URL, opacity=opacity, maxZoom=18,
                         attribution='Geology © <a href="https://macrostrat.org/">Macrostrat</a> · original map providers · CC BY 4.0')
    return [layer], 'Overlay enabled; tiles are requested directly from Macrostrat. Blank tiles or a loading failure do not establish no coverage. Interpret units using the original references below.'
