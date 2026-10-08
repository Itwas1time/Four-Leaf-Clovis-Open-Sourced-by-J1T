import base64
import json
from dash import ALL, Input, Output, State, callback, callback_context, clientside_callback, html, no_update
from core.fieldbook import EMPTY_BOOK, validate_book, merge_entries, new_entry, follow_up_entry, readable_text
from core.find_inspection import inspect_find
from core.resident_context import current_report
from core.web_security import validate_json


def summary_text(key, value):
    """Present old and new stored snapshots without changing their contents."""
    if key != 'maps':
        return value
    status, separator, units = value.partition(':')
    labels = {'not_requested':'Rock maps were off', 'unavailable':'Rock maps unavailable',
              'no_coverage':'No map coverage returned', 'available':'Mapped units'}
    if status not in labels:
        return value
    return labels[status] + (': ' + units.strip() if separator and units.strip() else '')


@callback(Output('fieldbook-store','data'),Output('fieldbook-status','children'),
          Output('resident-save-status','children'),Output('find-save-status','children'),
          Input('resident-save','n_clicks'),Input('find-save','n_clicks'),Input('fieldbook-import','contents'),Input('fieldbook-followup-save','n_clicks'),
          State('fieldbook-store','data'),State('resident-report-store','data'),State('resident-state','value'),
          State('resident-place','value'),State('resident-history','value'),State('resident-online','value'),
          State('find-material','value'),State('find-features','value'),State('find-setting','value'),State('find-size','value'),State('find-notes','value'),
          State('fieldbook-selected','value'),State('fieldbook-followup','value'),
          prevent_initial_call=True)
def save_notes(resident_clicks,find_clicks,imported,followup_clicks,book,token,state,geoid,history,online,material,features,setting,size,notes,selected,followup):
    try:
        book=validate_book(book or EMPTY_BOOK)
        trigger=callback_context.triggered_id
        if trigger=='resident-save':
            report=current_report(token,state,geoid,history,online)
            if report is None: raise ValueError('Explore this town again before saving a current report.')
            rows=[new_entry('town',report)]
        elif trigger=='find-save':
            report=inspect_find(material,features,setting,size or '',notes or '')
            if not report['features'] and not report['size'].strip() and not report['notes'].strip() and report['setting']=='unknown':
                raise ValueError('Record at least one observation before saving.')
            rows=[new_entry('find',report)]
        elif trigger=='fieldbook-import':
            if not isinstance(imported,str) or len(imported)>1_000_050 or ';base64,' not in imported: raise ValueError('Choose a Clovis JSON fieldbook under 750 KB.')
            raw=base64.b64decode(imported.split(';base64,',1)[1],validate=True)
            if len(raw)>750000: raise ValueError('Choose a fieldbook under 750 KB.')
            validate_json(raw)
            restored=validate_book(json.loads(raw))
            rows=restored['entries']
        elif trigger=='fieldbook-followup-save':
            row=next((r for r in book['entries'] if r['id']==selected),None)
            if not row: raise ValueError('Select saved notes before adding a follow-up.')
            rows=[follow_up_entry(row,followup)]
        else: return no_update,no_update,no_update,no_update
        merged=merge_entries(book,rows)
        count=len(merged['entries'])
        message=f'Saved locally · {count} record(s). Open Fieldbook to read or compare.'
        return merged,message,message if trigger=='resident-save' else no_update,message if trigger=='find-save' else no_update
    except (ValueError,TypeError,UnicodeError,RecursionError) as exc:
        return no_update,str(exc),str(exc) if callback_context.triggered_id=='resident-save' else no_update,str(exc) if callback_context.triggered_id=='find-save' else no_update


@callback(Output('fieldbook-selected','options'),Output('fieldbook-compare','options'),
          Output('fieldbook-list','children'),Input('fieldbook-store','data'))
def list_notes(book):
    try: rows=validate_book(book or EMPTY_BOOK)['entries']
    except ValueError: return [],[],html.P('This saved fieldbook could not be read. Restore a valid backup to a fresh browser profile.')
    options=[{'label':row['title'],'value':row['id']} for row in rows]
    cards=[html.Button([html.Strong(row['title']),html.P(row['created'][:10]+' · '+{'town':'Town context','find':'Object observations','investigation':'Guided investigation'}[row['kind']]),
                         html.P(' · '.join(summary_text(key,value) for key,value in row['summary'].items() if key!='place')[:400])],id={'type':'fieldbook-open','index':row['id']},n_clicks=0,className='atlas-fieldbook-card') for row in rows]
    return options,options,cards or html.P('Explore a town or Inspect a find, then choose Save to fieldbook. Your investigations will appear here.',className='atlas-resident-intro')


@callback(Output('fieldbook-selected','value'), Input({'type':'fieldbook-open','index':ALL},'n_clicks'),
          State('fieldbook-store','data'), prevent_initial_call=True)
def open_note(clicks,book):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict) or not any(clicks): return no_update
    try: row,_=selected_rows(book,trigger.get('index'))
    except ValueError: return no_update
    return row['id'] if row else no_update


def selected_rows(book,selected,other=None):
    rows=validate_book(book or EMPTY_BOOK)['entries']
    return next((r for r in rows if r['id']==selected),None),next((r for r in rows if r['id']==other),None)


@callback(Output('fieldbook-title','children'),Output('fieldbook-text','children'),Output('fieldbook-comparison','children'),
          Output('fieldbook-print','disabled'),Output('fieldbook-note-download','disabled'),
          Input('fieldbook-store','data'),Input('fieldbook-selected','value'),Input('fieldbook-compare','value'))
def read_notes(book,selected,other):
    try: row,compare=selected_rows(book,selected,other)
    except ValueError: return 'Choose an investigation.','',[],True,True
    if not row: return 'Choose an investigation.','',[],True,True
    table=[]
    if compare and compare['id']!=row['id']:
        fields=dict.fromkeys([*row['summary'],*compare['summary']])
        table=html.Div([html.H3('What changed between these notes?'),
            html.Table([html.Thead(html.Tr([html.Th('Observation'),html.Th(row['title']),html.Th(compare['title'])])),
                        html.Tbody([html.Tr([html.Th(key.capitalize()),html.Td(summary_text(key,row['summary'].get(key,'Not recorded'))),html.Td(summary_text(key,compare['summary'].get(key,'Not recorded')))]) for key in fields])]),
            html.P('These are recorded observations and report snapshots, not verified identities or independent confirmations.',className='atlas-help')],className='atlas-fieldbook-compare')
    return row['title'],readable_text(row['markdown']),table,False,False


@callback(Output('fieldbook-download','data'),Input('fieldbook-export','n_clicks'),Input('fieldbook-note-download','n_clicks'),
          State('fieldbook-store','data'),State('fieldbook-selected','value'),prevent_initial_call=True)
def export_notes(export_clicks,note_clicks,book,selected):
    try:
        book=validate_book(book or EMPTY_BOOK)
        if callback_context.triggered_id=='fieldbook-note-download':
            row,_=selected_rows(book,selected)
            return {'content':row['markdown'],'filename':'clovis-saved-notes.md','type':'text/markdown'} if row else no_update
        return {'content':json.dumps(book,ensure_ascii=False,indent=2),'filename':'clovis-fieldbook.json','type':'application/json'}
    except ValueError: return no_update


clientside_callback(
    """function(clicks, title, text) {
        if (!clicks || !text) return window.dash_clientside.no_update;
        let sheet = document.getElementById('clovis-print-sheet');
        if (!sheet) { sheet = document.createElement('article'); sheet.id = 'clovis-print-sheet'; document.body.appendChild(sheet); }
        sheet.replaceChildren();
        const brand = document.createElement('p'); brand.textContent = 'clovis · A little curiosity, Dig deeper.';
        const heading = document.createElement('h1'); heading.textContent = title;
        const notes = document.createElement('pre'); notes.textContent = text;
        sheet.append(brand, heading, notes);
        window.print();
        return clicks;
    }""",
    Output('fieldbook-print-status','data'),Input('fieldbook-print','n_clicks'),
    State('fieldbook-title','children'),State('fieldbook-text','children'),prevent_initial_call=True)
