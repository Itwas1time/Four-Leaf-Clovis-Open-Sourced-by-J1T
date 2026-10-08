"""Local question packets and attributed responses; no sending integration."""
import re
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core.fieldbook import EMPTY_BOOK, validate_book, merge_entries, readable_text
from core.expert_questions import prepare_question, response_entry, question_first_markdown


def source_row(book, selected):
    rows = validate_book(EMPTY_BOOK if book is None else book)['entries']
    row = next((item for item in rows if item['id'] == selected), None)
    if row is None:
        raise ValueError('Select saved notes before preparing a question.')
    return row


def current_packet(book, selected, question, comparison, detail, draft):
    row = source_row(book, selected)
    packet = prepare_question(row, question, comparison, detail)
    if not isinstance(draft, dict) or draft != {'source_id':row['id'], 'packet_id':packet['id']}:
        raise ValueError('Preview the current question before saving or downloading it.')
    return packet


def related_records(book, selected):
    """Navigate saved snapshot links; imported records are still user-supplied."""
    rows = validate_book(EMPTY_BOOK if book is None else book)['entries']
    links = {}
    for row in rows:
        if row['summary'].get('mission') not in ('Expert question', 'Expert response'):
            continue
        parents = re.findall(r'^### Preserved saved snapshot fields\n\nParent record: ([a-f0-9]{24})\n\nOriginal title:', row['markdown'], re.M)
        if parents:
            links[row['id']] = parents[-1]
    family = {selected}
    for _ in rows:
        before = len(family)
        for child, parent in links.items():
            if child in family or parent in family:
                family.update((child, parent))
        if len(family) == before:
            break
    matches = [row for row in rows if row['id'] in family]
    if len(matches) < 2:
        return []
    return html.Details([
        html.Summary(f'Related saved records · {len(matches)}'),
        html.Div([html.Button(row['title'], id={'type':'expert-thread-open', 'index':row['id']},
                              n_clicks=0, disabled=row['id']==selected, className='atlas-secondary-button')
                  for row in matches], className='clovis-expert-actions'),
    ], className='clovis-expert-disclosure')


@callback(Output('expert-tools','style'), Output('expert-source-title','children'),
          Output('expert-response-panel','style'), Output('expert-question-panel','style'), Output('expert-related-records','children'),
          Input('fieldbook-store','data'), Input('fieldbook-selected','value'))
def expert_selection(book, selected):
    try:
        row = source_row(book, selected)
    except ValueError:
        return {'display':'none'}, '', {'display':'none'}, {'display':'none'}, []
    response_visible = row['summary'].get('mission') == 'Expert question'
    question_visible = row['summary'].get('mission') not in ('Expert question', 'Expert response')
    return ({}, 'Selected notes: ' + row['title'], {} if response_visible else {'display':'none'},
            {} if question_visible else {'display':'none'}, related_records(book, selected))


@callback(Output('fieldbook-selected','value',allow_duplicate=True),
          Input({'type':'expert-thread-open','index':ALL},'n_clicks'), State('fieldbook-store','data'),
          prevent_initial_call=True)
def open_related(clicks, book):
    trigger = callback_context.triggered_id
    if (not isinstance(trigger, dict) or not isinstance(clicks, list) or len(clicks)>50
            or any(type(value) is not int or value<0 for value in clicks) or not any(clicks)):
        return no_update
    try:
        return source_row(book, trigger.get('index'))['id']
    except ValueError:
        return no_update


@callback(Output('expert-question-preview','children'), Output('expert-question-draft','data'),
          Output('expert-question-status','children'), Output('expert-download','disabled'), Output('expert-save','disabled'),
          Input('expert-prepare','n_clicks'), Input('fieldbook-store','data'), Input('fieldbook-selected','value'),
          Input('expert-question','value'), Input('expert-comparison','value'), Input('expert-detail','value'))
def preview_question(clicks, book, selected, question, comparison, detail):
    if callback_context.triggered_id != 'expert-prepare' or not clicks:
        return '', None, '', True, True
    try:
        row = source_row(book, selected)
        packet = prepare_question(row, question, comparison, detail)
        draft = {'source_id':row['id'], 'packet_id':packet['id']}
        return readable_text(question_first_markdown(packet)), draft, 'Review the packet. Photos are separate and are not included.', False, False
    except (ValueError, TypeError, UnicodeError) as exc:
        return '', None, str(exc), True, True


@callback(Output('expert-download-file','data'), Input('expert-download','n_clicks'),
          State('fieldbook-store','data'), State('fieldbook-selected','value'), State('expert-question','value'),
          State('expert-comparison','value'), State('expert-detail','value'), State('expert-question-draft','data'),
          prevent_initial_call=True)
def download_question(clicks, book, selected, question, comparison, detail, draft):
    if not clicks:
        return no_update
    try:
        packet = current_packet(book, selected, question, comparison, detail, draft)
        return {'content':question_first_markdown(packet), 'filename':'clovis-question-packet.md', 'type':'text/markdown'}
    except (ValueError, TypeError, UnicodeError):
        return no_update


@callback(Output('fieldbook-store','data',allow_duplicate=True),
          Output('fieldbook-selected','value',allow_duplicate=True), Output('expert-save-status','children'),
          Input('expert-save','n_clicks'), State('fieldbook-store','data'), State('fieldbook-selected','value'),
          State('expert-question','value'), State('expert-comparison','value'), State('expert-detail','value'),
          State('expert-question-draft','data'), prevent_initial_call=True)
def save_question(clicks, book, selected, question, comparison, detail, draft):
    if not clicks:
        return no_update, no_update, no_update
    try:
        packet = current_packet(book, selected, question, comparison, detail, draft)
        merged = merge_entries(EMPTY_BOOK if book is None else book, [packet])
        return merged, packet['id'], 'Question saved. Select it to record an attributed response.'
    except (ValueError, TypeError, UnicodeError) as exc:
        return no_update, no_update, str(exc)


@callback(Output('fieldbook-store','data',allow_duplicate=True),
          Output('fieldbook-selected','value',allow_duplicate=True), Output('expert-response-status','children'),
          Input('expert-response-save','n_clicks'), State('fieldbook-store','data'), State('fieldbook-selected','value'),
          State('expert-attribution','value'), State('expert-response-date','value'), State('expert-response','value'),
          State('expert-uncertainty','value'), prevent_initial_call=True)
def save_response(clicks, book, selected, attribution, response_date, response, uncertainty):
    if not clicks:
        return no_update, no_update, no_update
    try:
        row = source_row(book, selected)
        recorded = response_entry(row, attribution, response_date, response, uncertainty)
        merged = merge_entries(EMPTY_BOOK if book is None else book, [recorded])
        return merged, recorded['id'], 'Attributed response saved separately. Original notes and question are preserved.'
    except (ValueError, TypeError, UnicodeError) as exc:
        return no_update, no_update, str(exc)
