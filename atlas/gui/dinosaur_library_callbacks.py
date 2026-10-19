from atlas.gui.library_activation import require_section
import sqlite3
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core import dinosaur_catalog as catalog
from core.fieldbook import EMPTY_BOOK, merge_entries
from atlas.gui.library_ui import reading_nav

def parameters(query,country,lineage,view,scope,state='all'):
    if scope not in ('all','names'):
        raise ValueError('Choose a search scope.')
    result={'query':query or '', 'country':country or 'all', 'lineage':lineage, 'view':view, 'names_only':scope=='names'}
    if state and state!='all':
        if not isinstance(state,str) or not state.startswith('region:'):
            raise ValueError('Choose a recorded state or province.')
        result['state']=state.removeprefix('region:')
    return result


@callback(Output('dinosaur-state','options'),Output('dinosaur-state','value'),
          Input('dinosaur-country','value'),Input('dinosaur-lineage','value'),
          Input('data-pack-refresh','data'),Input('library-section','value'),State('dinosaur-state','value'))
def regions(country,lineage,_refresh,section,state):
    require_section(section,'dinosaurs')
    base=[{'label':'All recorded states / provinces','value':'all'}]
    try:
        rows=catalog.states(country=country or 'all',lineage=lineage)
        options=base+[{'label':f'{row["label"]} · {row["records"]:,} occurrences','value':row['value']} for row in rows]
        selected=state if state in {row['value'] for row in options} else 'all'
        return options,selected
    except (ValueError,OSError,sqlite3.Error,TypeError):
        return base,'all'

@callback(Output('dinosaur-country','options'),Input('data-pack-refresh','data'), Input("library-section", "value"),Input('dinosaur-lineage','value'))
def countries(_refresh, section="dinosaurs",lineage='nonavian'):
    require_section(section, "dinosaurs")
    try:
        return [{'label':'All recorded countries','value':'all'},*[
            {'label':f'{row["label"]} · {row["records"]:,} occurrences','value':row['value']} for row in catalog.countries(lineage)]]
    except (ValueError,OSError,KeyError,sqlite3.Error):
        return [{'label':'All recorded countries','value':'all'}]

@callback(Output('dinosaur-cards','children'),Output('dinosaur-count','children'),Output('dinosaur-page','data'),
          Output('dinosaur-page-label','children'),Output('dinosaur-previous','disabled'),Output('dinosaur-next','disabled'),
          Output('dinosaur-coverage','children'),Input('dinosaur-query','value'),Input('dinosaur-country','value'),
          Input('dinosaur-lineage','value'),Input('dinosaur-view','value'),Input('dinosaur-scope','value'),Input('dinosaur-previous','n_clicks'),
          Input('dinosaur-next','n_clicks'),Input('data-pack-refresh','data'),State('dinosaur-page','data'), Input("library-section", "value"),Input('dinosaur-state','value'))
def results(query,country,lineage,view,scope,_previous,_next,_refresh,page, section="dinosaurs",state='all'):
    require_section(section, "dinosaurs")
    try:
        page = page if type(page) is int and page>=1 else 1
        trigger = callback_context.triggered_id
        page = max(1,page-1) if trigger=='dinosaur-previous' else page+1 if trigger=='dinosaur-next' else 1
        result = catalog.search(page=page,**parameters(query,country,lineage,view,scope,state))
        if not result['installed']:
            return html.P('Install Dinosaur taxa and fossil sites from Data collections to explore these records.'),'Collection not installed',1,'',True,True,catalog.definition()['coverage']
        summary = catalog.stats()
        cards = []
        for row in result['rows']:
            if view=='occurrences':
                source = catalog.result_context(row)
                title = row['accepted_name'] or row['identified_name'] or 'Occurrence '+row['occurrence_no']
                detail = ' · '.join(value for value in (source.get('collection_name',''),row['country'],row['state'],row['formation']) if value)
                note = 'Occurrence '+row['occurrence_no']+' · Collection '+row['collection_no']
            else:
                title = row['name']
                detail = f'{row["rank"]} · {row["n_occurrences"]:,} selected published occurrences'
                note = 'Snapshot accepted name: '+row['accepted_name']
            cards.append(html.Button([html.Strong(title),html.Small(detail),html.Small(note)],id={'type':'dinosaur-open','index':row['id']},n_clicks=0,className='clovis-library-record'))
        label = 'published occurrences' if view=='occurrences' else 'original taxonomic names'
        if lineage=='fossils':
            coverage=f'{summary["records"]:,} occurrences · {summary["collections"]:,} collection IDs · {summary["taxa"]:,} original taxonomic names across ranks, including synonyms · snapshot {summary["source_release"]}. Counts are distinct from specimen or species counts.'
        else:
            dinosaur_records=summary.get('dinosaur_occurrences',summary['records'])
            dinosaur_taxa=summary.get('dinosaur_taxa',summary['taxa'])
            coverage = f'{dinosaur_records:,} Dinosauria occurrences · {dinosaur_taxa:,} original Dinosauria taxonomic names across ranks, including synonyms · snapshot {summary["source_release"]}. Counts are distinct from specimen or species counts.'
        return cards or html.P('No records match these filters.'),f'{result["total"]:,} matching {label}',result['page'],f'{result["page"]} of {result["pages"]}',result['page']<=1,result['page']>=result['pages'],coverage
    except (ValueError,OSError,sqlite3.Error,TypeError):
        return html.P('The installed collection could not be read. Check it in Data collections.'),'Search unavailable',1,'',True,True,''

@callback(Output('dinosaur-selected','data'),Input({'type':'dinosaur-open','index':ALL},'n_clicks'),
          Input('dinosaur-query','value'),Input('dinosaur-country','value'),Input('dinosaur-lineage','value'),
          Input('dinosaur-view','value'),Input('dinosaur-scope','value'),Input('dinosaur-page','data'),Input('data-pack-refresh','data'),Input('dinosaur-state','value'))
def select(clicks,query,country,lineage,view,scope,page,_refresh,state='all'):
    trigger = callback_context.triggered_id
    if not isinstance(trigger,dict) or not any(type(value) is int and value>0 for value in clicks or []):
        return None
    try:
        values = parameters(query,country,lineage,view,scope,state)
        result = catalog.search(page=page,**values)
        if any(row['id']==trigger['index'] for row in result['rows']):
            return {'id':trigger['index'],'page':page,'parameters':values}
    except (ValueError,OSError,sqlite3.Error,TypeError):
        pass
    return None

def current(selected,query,country,lineage,view,scope,page,state='all'):
    values = parameters(query,country,lineage,view,scope,state)
    if not isinstance(selected,dict) or selected.get('parameters')!=values or selected.get('page')!=page:
        return None
    result = catalog.search(page=page,**values)
    return catalog.get_record(selected.get('id')) if any(row['id']==selected.get('id') for row in result['rows']) else None

@callback(Output('dinosaur-detail','children'),Input('dinosaur-selected','data'),Input('dinosaur-query','value'),
          Input('dinosaur-country','value'),Input('dinosaur-lineage','value'),Input('dinosaur-view','value'),
          Input('dinosaur-scope','value'),Input('dinosaur-page','data'),Input('data-pack-refresh','data'),Input('dinosaur-state','value'))
def reader(selected,query,country,lineage,view,scope,page,_refresh,state='all'):
    try:
        record = current(selected,query,country,lineage,view,scope,page,state)
        if record is None:
            return html.P('Choose a published occurrence or taxonomic name to read its source context.')
        summary = catalog.stats()
        title=(record['accepted_name'] or record['identified_name'] or 'Occurrence '+record['occurrence_no']) if record['kind']=='occ' else record['name']
        detail = [reading_nav('dinosaur-query'),html.H3(title),
                  html.Dl([node for label,value in catalog.facts(record) for node in (html.Dt(label),html.Dd(value))],className='clovis-library-facts')]
        if record['kind']=='taxon':
            detail.extend([html.H4('Published occurrences in this snapshot'),
                           *[html.P(f'{row["accepted_name"]} · collection {row["collection_no"]} · {row["country"]} {row["state"]} · occurrence {row["occurrence_no"]}') for row in record['occurrences']],
                           html.P('Showing up to 24 associated occurrences. Search the accepted name in the occurrence view to browse more.',className='atlas-help'),
                           html.Details([html.Summary(f'{len(record["variants"])} source name variants'),*[html.P(f'{row.get("taxon_name","")} · variant {row.get("taxon_no","")} · {row.get("taxon_rank","")}') for row in record['variants']]])])
        detail.extend([html.P(summary['location_note'],className='atlas-help'),html.P(summary['count_note'],className='atlas-help'),
                       html.Details([html.Summary('All retained source fields'),html.Dl([node for key,value in record.get('source_fields',list(record['source'].items())) for node in (html.Dt(key.replace('_',' ')),html.Dd(value if value!='' else 'Not recorded (blank)'))],className='clovis-library-facts')]),
                       html.A('Original PBDB record',href=catalog.source_url(record),target='_blank',rel='noopener noreferrer'),
                       html.P(summary['citation']),html.A('Frozen collection & reuse rights',href=summary['citation_url'],target='_blank',rel='noopener noreferrer'),
                       html.Button('Save fossil reference to fieldbook',id='dinosaur-save',n_clicks=0,className='atlas-primary-button'),
                       html.Div(id='dinosaur-save-status',role='status',className='atlas-help')])
        return detail
    except (ValueError,OSError,sqlite3.Error,TypeError):
        return html.P('Choose a record from the current installed collection search.')

@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('dinosaur-save-status','children'),
          Input('dinosaur-save','n_clicks'),State('dinosaur-selected','data'),State('dinosaur-query','value'),
          State('dinosaur-country','value'),State('dinosaur-lineage','value'),State('dinosaur-view','value'),
          State('dinosaur-scope','value'),State('dinosaur-page','data'),State('fieldbook-store','data'),State('dinosaur-state','value'),prevent_initial_call=True)
def save(clicks,selected,query,country,lineage,view,scope,page,book,state='all'):
    if not clicks:
        return no_update,no_update
    try:
        row = current(selected,query,country,lineage,view,scope,page,state)
        if row is None:
            return no_update,'Choose a record from the current search.'
        return merge_entries(EMPTY_BOOK if book is None else book,[catalog.reference_entry(row['id'])]),'Fossil reference saved with its published site, source precision and reference.'
    except (ValueError,OSError,sqlite3.Error,TypeError,UnicodeError):
        return no_update,'The reference could not be saved. Check the selected record and fieldbook capacity.'
