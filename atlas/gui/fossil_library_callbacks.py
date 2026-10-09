"""Read fossil facts from the bundled source catalog, not client-supplied text."""
from atlas.gui.library_activation import require_section
from functools import lru_cache
from dash import ALL,MATCH,Input,Output,State,callback,callback_context,html,no_update
from core.fossil_reference_catalog import catalog_stats,search_taxa,search_fossils,get_fossil
from core.fossil_notes import facts,reference_entry,text
from core.fieldbook import EMPTY_BOOK,merge_entries
from atlas.gui.library_callbacks import _url
from core.reference_media import smithsonian_image
from atlas.gui.library_ui import reading_nav


@lru_cache(maxsize=1)
def stats():
    return catalog_stats()


@callback(Output('library-fossil-cards','children'),Output('library-fossil-count','children'),
          Output('library-fossil-page','data'),Output('library-fossil-page-label','children'),
          Output('library-fossil-previous','disabled'),Output('library-fossil-next','disabled'),Output('library-fossil-source','children'),
          Input('library-fossil-query','value'),Input('library-fossil-view','value'),
          Input('library-fossil-previous','n_clicks'),Input('library-fossil-next','n_clicks'),State('library-fossil-page','data'), Input("library-section", "value"))
def results(query,view,previous,next_clicks,page, section="fossils"):
    require_section(section, "fossils")
    query=query if isinstance(query,str) and len(query)<=120 else ''
    page=page if type(page) is int and 1<=page<=100000 else 1
    trigger=callback_context.triggered_id
    page=max(1,page-1) if trigger=='library-fossil-previous' else page+1 if trigger=='library-fossil-next' else 1
    grouped=view!='specimens'
    found=(search_taxa if grouped else search_fossils)(query=query,page=page)
    cards=[]
    for row in found['rows']:
        sample=row.get('sample_record_ids',[]) if grouped else [row['id']]
        if not sample:
            continue
        title=row['taxon_name'] if grouped else row['title']
        subtitle=f"{row['specimen_count']:,} cataloged specimens · {row.get('taxon_group','')}" if grouped else text(row.get('geological_age')) or row.get('specimen_number','')
        cards.append(html.Button([html.Strong(title),html.Small(subtitle)],id={'type':'library-fossil-open','index':sample[0]},n_clicks=0,className='clovis-library-record'))
    if not cards:
        cards=[html.P('No matching references. Try a scientific name, broader classification, or Specimen records for ages and formations.',className='atlas-help')]
    summary=stats()
    source=f"{summary['distinct_records']:,} Smithsonian fossil specimens · {summary['distinct_taxon_names']:,} recorded taxon names · CC0 metadata · Snapshot {summary.get('snapshot_date','')}"
    label=f"{found['total']:,} matching "+('taxon groups' if grouped else 'specimen records')
    return cards,label,found['page'],f"{found['page']:,} / {found['pages']:,}",found['page']<=1,found['page']>=found['pages'],source


@callback(Output('library-fossil-selected','data'),Input({'type':'library-fossil-open','index':ALL},'n_clicks'),
          Input('library-fossil-query','value'),Input('library-fossil-view','value'),
          Input('library-fossil-previous','n_clicks'),Input('library-fossil-next','n_clicks'),prevent_initial_call=True)
def select(clicks,query,view,previous,next_clicks):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict):
        return None
    if not isinstance(clicks,list) or len(clicks)>24 or any(type(n) is not int or n<0 for n in clicks) or not any(clicks):
        return no_update
    row=get_fossil(trigger.get('index'))
    return row['id'] if row else no_update


@callback(Output('library-fossil-detail','children'),Input('library-fossil-selected','data'))
def read(selected):
    if not isinstance(selected,str) or len(selected)>166:
        return html.P('Select a taxon to read a sample specimen, or choose an individual specimen record.')
    row=get_fossil(selected)
    if not row:
        return html.P('Choose a reference from the current catalog.')
    detail=[]
    for label,value in facts(row):
        detail.extend([html.Dt(label),html.Dd(value)])
    source=_url(row.get('source_url'),{'n2t.net','collections.si.edu','www.si.edu','si.edu'})
    children=[reading_nav('library-fossil-query'),html.H3(row['title']),html.P('Sample catalog specimen · '+row.get('specimen_number',''),className='atlas-help')]
    children.append(html.Button('Search these specimens',id='library-fossil-search-specimens',n_clicks=0,className='atlas-secondary-button'))
    image=smithsonian_image(row)
    if image:
        children.extend([html.Button('Load reference photograph',id={'type':'library-fossil-image-open','index':row['id']},n_clicks=0,className='atlas-secondary-button'),
                         html.Div(id={'type':'library-fossil-image','index':row['id']},**{'data-library-image':'fossil'})])
    children.append(html.Dl(detail,className='clovis-library-facts'))
    if source:
        children.append(html.A('Smithsonian source specimen',href=source,target='_blank',rel='noopener noreferrer'))
    children.extend([html.Button('Save fossil reference to fieldbook',id='library-fossil-save',n_clicks=0,className='atlas-primary-button'),
                     html.Div(id='library-fossil-save-status',role='status',className='atlas-help'),
                     html.Button('Open fieldbook →',id={'type':'workbench-action','target':'notebook','key':'fossil-reference'},n_clicks=0,className='atlas-secondary-button'),
                     html.P('Source specimen context · This record is not a fossil occurrence at your selected town.',className='atlas-help')])
    return children


@callback(Output('library-fossil-query','value'),Output('library-fossil-view','value'),
          Input('library-fossil-search-specimens','n_clicks'),State('library-fossil-selected','data'),prevent_initial_call=True)
def search_specimens(clicks,selected):
    if not clicks or not isinstance(selected,str) or len(selected)>166:
        return no_update,no_update
    row=get_fossil(selected)
    return (row['taxon_name'][:120],'specimens') if row else (no_update,no_update)


@callback(Output({'type':'library-fossil-image','index':MATCH},'children'),Input({'type':'library-fossil-image-open','index':MATCH},'n_clicks'),
          State({'type':'library-fossil-image-open','index':MATCH},'id'),prevent_initial_call=True)
def photograph(clicks,button):
    selected=button.get('index') if isinstance(button,dict) else None
    if not clicks or not isinstance(selected,str) or len(selected)>166:
        return no_update
    row=get_fossil(selected)
    image=smithsonian_image(row)
    return [html.Img(src='/api/reference/fossil-image/'+row['id'],alt=row['title']+' · museum specimen reference',className='clovis-library-image',referrerPolicy='no-referrer'),html.Small('CC0 reference image · Smithsonian')] if image else no_update


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-fossil-save-status','children'),
          Input('library-fossil-save','n_clicks'),State('library-fossil-selected','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks,selected,book):
    if not clicks or not isinstance(selected,str) or len(selected)>166:
        return no_update,no_update
    row=get_fossil(selected)
    if not row:
        return no_update,'Choose a specimen from the current library.'
    try:
        return merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(row)]),'Fossil reference saved with its source.'
    except (ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
