import sqlite3
import re
from dash import ALL, Input, Output, State, callback, callback_context, clientside_callback, html, no_update
from atlas.gui.workspace_activation import when_opened
from core.fieldbook import EMPTY_BOOK, validate_book, new_entry, follow_up_entry, readable_text
from atlas.gui.reading_merge import merge_entries
from core.find_inspection import inspect_find
from core.expert_questions import question_first_markdown
from core.resident_context import current_report


def summary_text(key, value):
    """Present old and new stored snapshots without changing their contents."""
    if key != 'maps':
        return value
    status, separator, units = value.partition(':')
    labels = {'not_requested':'Online rock maps were off', 'unavailable':'Online rock maps unavailable',
              'no_coverage':'No online map coverage returned', 'available':'Mapped units'}
    if status not in labels:
        return value
    return labels[status] + (': ' + units.strip() if separator and units.strip() else '')


@callback(Output('fieldbook-store','data'),Output('fieldbook-status','children'),
          Output('resident-save-status','children'),Output('find-save-status','children'),
          Input('resident-save','n_clicks'),Input('find-save','n_clicks'),Input('fieldbook-imported','data'),Input('fieldbook-followup-save','n_clicks'),
          State('fieldbook-store','data'),State('resident-report-store','data'),State('resident-state','value'),
          State('resident-place','value'),State('resident-history','value'),State('resident-online','value'),
          State('find-material','value'),State('find-features','value'),State('find-setting','value'),State('find-size','value'),State('find-notes','value'),
          State('fieldbook-selected','value'),State('fieldbook-followup','value'),State('find-town','value'),
          State('find-photo-files','data'),State({'type':'find-photo-caption','index':ALL},'id'),
          State({'type':'find-photo-caption','index':ALL},'value'),State('find-photo-transfer','data'),
          prevent_initial_call=True)
def save_notes(resident_clicks,find_clicks,imported,followup_clicks,book,token,state,geoid,history,online,material,features,setting,size,notes,selected,followup,town_context,photos=None,caption_ids=None,captions=None,transfer=None):
    try:
        book=validate_book(book or EMPTY_BOOK)
        trigger=callback_context.triggered_id
        if trigger=='resident-save':
            report=current_report(token,state,geoid,history,online)
            if report is None: raise ValueError('Explore this town again before saving a current report.')
            rows=[new_entry('town',report)]
        elif trigger=='find-save':
            from core.local_photos import PhotoStore,captioned_refs
            if isinstance(transfer,dict) and transfer.get('busy'):
                raise ValueError('Wait for the photo to finish saving before saving this observation.')
            photos=captioned_refs(photos or [],caption_ids or [],captions or [],'find')
            PhotoStore().check(photos)
            report=inspect_find(material,features,setting,size or '',notes or '',
                                town_context=town_context, state=state, geoid=geoid)
            if not report['features'] and not report['size'].strip() and not report['notes'].strip() and report['setting']=='unknown' and not photos:
                raise ValueError('Record at least one observation before saving.')
            rows=[new_entry('find',report,photos)]
        elif trigger=='fieldbook-imported':
            if not isinstance(imported,dict) or set(imported)!={'book','nonce'}:
                raise ValueError('Choose a fieldbook JSON or photo-inclusive ZIP backup.')
            restored=validate_book(imported['book'])
            rows=restored['entries']
        elif trigger=='fieldbook-followup-save':
            row,_=selected_rows(book,selected)
            if not row: raise ValueError('Select saved notes before adding a follow-up.')
            rows=[follow_up_entry(row,followup)]
        else: return no_update,no_update,no_update,no_update
        merged=merge_entries(book,rows)
        message='Saved locally. Open Fieldbook to read or compare.'
        return merged,message,message if trigger=='resident-save' else no_update,message if trigger=='find-save' else no_update
    except (ValueError,TypeError,UnicodeError,RecursionError,OSError,sqlite3.Error) as exc:
        return no_update,str(exc),str(exc) if callback_context.triggered_id=='resident-save' else no_update,str(exc) if callback_context.triggered_id=='find-save' else no_update


@callback(Output('fieldbook-store','data',allow_duplicate=True),
          Output('fieldbook-status','children',allow_duplicate=True),
          Input('fieldbook-reconciled','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def reconcile_workspace(imported, current):
    """Replace browser copies only when they match committed workspace originals."""
    try:
        from core.workspace_storage import WorkspaceStorage
        from core.large_readings import is_reference
        if not isinstance(imported,dict) or set(imported) != {'book','nonce'}:
            raise ValueError('The workspace response could not be read.')
        current=validate_book(current or EMPTY_BOOK)
        incoming=validate_book(imported['book'])
        store=WorkspaceStorage()
        by_id={row['id']:row for row in incoming['entries']}
        rows=[]
        for old in current['entries']:
            new=by_id.pop(old['id'],None)
            if new is None:
                rows.append(old)
                continue
            old_full=store.resolve_reading(old)
            new_full=store.resolve_reading(new)
            if {k:v for k,v in old_full.items() if k!='created'} != {k:v for k,v in new_full.items() if k!='created'}:
                raise ValueError('A reading changed while the workspace was syncing. Your browser copy was preserved.')
            rows.append({**new,'created':old['created']} if is_reference(new) else old)
        for row in by_id.values():
            store.resolve_reading(row)
            rows.append(row)
        result=validate_book({'version':max(current['version'],incoming['version']),'entries':rows})
        if result == current:
            return no_update,no_update
        return result,'Readings synchronized with the local workspace.'
    except (ValueError,TypeError,UnicodeError,RecursionError,OSError,sqlite3.Error) as exc:
        return no_update,str(exc)


@when_opened('notebook', Output('fieldbook-selected','options'),Output('fieldbook-compare','options'),
          Output('fieldbook-list','children'),Input('fieldbook-store','data'))
def list_notes(book):
    try: rows=validate_book(book or EMPTY_BOOK)['entries']
    except ValueError: return [],[],html.P('This saved fieldbook could not be read. Restore a valid backup to a fresh browser profile.')
    titles = [row['title'] for row in rows]
    labels = []
    for row in rows:
        label = row['title']
        if titles.count(label) > 1:
            source = row['summary'].get('source') or row['created']
            # Show the distinguishing identifier before a long shared title;
            # dropdown triggers truncate their visible trailing text on phones.
            qualifier = ' · '.join(reversed(source.rsplit(' · ', 1)))
            label = qualifier[:320] + ('…' if len(qualifier)>320 else '') + ' · ' + label
        labels.append(label)
    options=[{'label':('note ' + row['id'][:8] + ' · ' if labels.count(label)>1 else '') + label,
              'value':row['id']} for row,label in zip(rows,labels)]
    cards=[html.Button([html.Strong(row['title']),html.P('Saved '+row['created'][:10]+' · '+_note_label(row)),
                         html.P(' · '.join(summary_text(key,value) for key,value in row['summary'].items() if key!='place')[:400])],id={'type':'fieldbook-open','index':row['id']},n_clicks=0,className='atlas-fieldbook-card') for row in rows]
    return options,options,cards or html.P('Explore a town or Inspect a find, then choose Save to fieldbook. Your investigations will appear here.',className='atlas-resident-intro')


def _note_label(row):
    if row['summary'].get('follow_up'):
        return 'Follow-up note'
    source=row['summary'].get('source')
    if isinstance(source,str) and source.startswith(('ADS via DataCite · ', 'DANS via DataCite · ')):
        return 'Metadata reference'
    mission=row['summary'].get('mission')
    if mission=='Published research source':
        return 'Published research reference'
    if isinstance(mission,str) and mission.startswith('Published ') and mission.endswith(' reference'):
        return mission
    if mission in ('Expert question','Expert response','Museum reference','Fossil reference','Newspaper reference','Geology reference','Object guide','Archaeology publication','Mineral reference','Government source reference'):
        return mission
    return {'town':'Town context','find':'Object observations','investigation':'Guided investigation'}[row['kind']]


@callback(Output('fieldbook-selected','value'), Input({'type':'fieldbook-open','index':ALL},'n_clicks'),
          State('fieldbook-store','data'), prevent_initial_call=True)
def open_note(clicks,book):
    trigger=callback_context.triggered_id
    if (not isinstance(trigger,dict) or not isinstance(clicks,list) or len(clicks)>50
            or any(type(value) is not int or value<0 for value in clicks) or not any(clicks)): return no_update
    try: row,_=selected_rows(book,trigger.get('index'))
    except ValueError: return no_update
    return row['id'] if row else no_update


def selected_rows(book,selected,other=None):
    rows=validate_book(book or EMPTY_BOOK)['entries']
    from core.workspace_storage import WorkspaceStorage
    store=WorkspaceStorage()
    first=next((r for r in rows if r['id']==selected),None)
    second=next((r for r in rows if r['id']==other),None)
    return (store.resolve_reading(first) if first else None,
            store.resolve_reading(second) if second else None)


def linked_sources(book, row):
    """Resolve compact follow-ups while bounding malformed or cyclic links."""
    by_id={item['id']: item for item in book['entries']}
    seen={row['id']}
    sources=[]
    while True:
        match=re.search(r'\nClovis source entry: ([a-f0-9]{24})\n\Z', row['markdown'])
        if not match:
            return sources, False
        identifier=match.group(1)
        if identifier in seen or identifier not in by_id:
            return sources, True
        seen.add(identifier)
        from core.workspace_storage import WorkspaceStorage
        row=WorkspaceStorage().resolve_reading(by_id[identifier])
        sources.append(row)


@when_opened('notebook', Output('fieldbook-title','children'),Output('fieldbook-text','children'),Output('fieldbook-comparison','children'),
          Output('fieldbook-print','disabled'),Output('fieldbook-note-download','disabled'),
          Output('fieldbook-read-full','disabled'),
          Input('fieldbook-store','data'),Input('fieldbook-selected','value'),Input('fieldbook-compare','value'))
def read_notes(book,selected,other):
    try: row,compare=selected_rows(book,selected,other)
    except (ValueError,OSError,sqlite3.Error): return 'This saved reading is unavailable. Restore its complete workspace backup.','',[],True,True,True
    if not row: return 'Choose an investigation.','',[],True,True,True
    table=[]
    if compare and compare['id']!=row['id']:
        fields=dict.fromkeys([*row['summary'],*compare['summary']])
        table=html.Div([html.H3('What changed between these notes?'),
            html.Table([html.Thead(html.Tr([html.Th('Observation'),html.Th(row['title']),html.Th(compare['title'])])),
                        html.Tbody([html.Tr([html.Th(key.capitalize()),html.Td(summary_text(key,row['summary'].get(key,'Not recorded'))),html.Td(summary_text(key,compare['summary'].get(key,'Not recorded')))]) for key in fields])]),
            html.P('These are recorded observations and report snapshots, not verified identities or independent confirmations.',className='atlas-help')],className='atlas-fieldbook-compare')
    from core.publication_catalog import saved_reading
    reading=saved_reading(row)
    text=reading if reading is not None else readable_text(question_first_markdown(row))
    try:
        sources, missing=linked_sources(book,row)
    except (ValueError,OSError,sqlite3.Error):
        sources, missing=[], True
    for source in sources:
        source_text=saved_reading(source) or readable_text(question_first_markdown(source))
        text += '\n\nOriginal saved source: ' + source['title'] + '\n\n' + source_text
    if missing:
        text += '\n\nA linked source is missing or circular. Restore its complete backup.'
    return row['title'],text,table,False,False,False


@callback(Output('fieldbook-download','data'),Input('fieldbook-note-download','n_clicks'),
          State('fieldbook-store','data'),State('fieldbook-selected','value'),prevent_initial_call=True)
def export_notes(note_clicks,book,selected):
    try:
        book=validate_book(book or EMPTY_BOOK)
        row,_=selected_rows(book,selected)
        if not row: return no_update
        content=question_first_markdown(row)
        if '## Complete native workbook snapshot JSON' in row['markdown']:
            from core.publication_catalog import saved_reading
            content=saved_reading(row)+'\n\n## Original retained snapshot\n\n'+content
        sources, missing=linked_sources(book,row)
        for source in sources:
            source_text=question_first_markdown(source)
            if '## Complete native workbook snapshot JSON' in source['markdown']:
                from core.publication_catalog import saved_reading
                source_text=saved_reading(source)+'\n\n## Original retained snapshot\n\n'+source_text
            content += '\n\n## Original saved source\n\n' + source_text
        if missing:
            content += '\n\nA linked source is missing or circular; restore its complete backup.\n'
        return {'content':content,'filename':'clovis-saved-notes.md','type':'text/markdown'}
    except (ValueError,OSError,sqlite3.Error): return no_update


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
