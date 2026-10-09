"""Read the reviewed material guides with fact-level sources."""
from atlas.gui.library_activation import require_section
from dash import ALL,Input,Output,State,callback,callback_context,html,no_update
from core.object_material_guides import search_guides,get_guide,guide_stats
from core.object_guide_notes import reference_entry
from core.fieldbook import EMPTY_BOOK,merge_entries
from atlas.gui.library_callbacks import _url
from atlas.gui.library_ui import reading_nav


@callback(Output('library-guide-cards','children'),Output('library-guide-count','children'),
          Output('library-guide-page','data'),Output('library-guide-page-label','children'),
          Output('library-guide-previous','disabled'),Output('library-guide-next','disabled'),
          Input('library-guide-query','value'),Input('library-guide-category','value'),
          Input('library-guide-previous','n_clicks'),Input('library-guide-next','n_clicks'),State('library-guide-page','data'), Input("library-section", "value"))
def results(query,category,previous,next_clicks,page, section="guides"):
    require_section(section, "guides")
    page=page if type(page) is int and 1<=page<=10000 else 1
    trigger=callback_context.triggered_id
    page=max(1,page-1) if trigger=='library-guide-previous' else page+1 if trigger=='library-guide-next' else 1
    found=search_guides(query,category,page)
    cards=[html.Button([html.Strong(row['title']),html.Small(row['summary'])],id={'type':'library-guide-open','index':row['id']},n_clicks=0,className='clovis-library-record') for row in found['rows']]
    if not cards:
        cards=[html.P('No guide matches. Try a shorter feature name or All object guides.',className='atlas-help')]
    stats=guide_stats()
    return cards,f"{found['total']} matching guides · {stats['total_facts']} fact-level source notes",found['page'],f"{found['page']} / {found['pages']}",found['page']<=1,found['page']>=found['pages']


@callback(Output('library-guide-selected','data'),Input({'type':'library-guide-open','index':ALL},'n_clicks'),
          Input('library-guide-query','value'),Input('library-guide-category','value'),
          Input('library-guide-previous','n_clicks'),Input('library-guide-next','n_clicks'),prevent_initial_call=True)
def select(clicks,*inputs):
    trigger=callback_context.triggered_id
    if not isinstance(trigger,dict):
        return None
    if not isinstance(clicks,list) or len(clicks)>8 or any(type(n) is not int or n<0 for n in clicks) or not any(clicks):
        return no_update
    guide=get_guide(trigger.get('index'))
    return guide['id'] if guide else no_update


@callback(Output('library-guide-detail','children'),Input('library-guide-selected','data'))
def read(selected):
    guide=get_guide(selected)
    if not guide:
        return html.P('Choose a guide for facts you can compare with an object and questions you can answer by looking closely.')
    children=[reading_nav('library-guide-query'),html.H3(guide['title']),html.P(guide['summary'])]
    for fact in guide['facts']:
        links=[]
        for source in fact['sources']:
            url=_url(source['url'],{'www.nps.gov','nps.gov','home.nps.gov','pubs.nps.gov','npgallery.nps.gov','sha.org','www.sha.org','secure-sha.org','www.secure-sha.org','www.usmint.gov','usmint.gov','www.si.edu','si.edu','americanhistory.si.edu','naturalhistory.si.edu'})
            if url:
                links.append(html.A(source['name'],href=url,target='_blank',rel='noopener noreferrer'))
        children.append(html.Div([html.P(fact['text']),html.Div(links,className='clovis-guide-citations')],className='clovis-library-fact'))
    children+=[html.H4('Look for these details'),html.Ul([html.Li(question) for question in guide['questions']]),
               html.H4('Record what you can see'),html.Ul([html.Li(prompt) for prompt in guide['record']]),
               html.Button('Inspect an object →',id={'type':'workbench-action','target':'inspect','key':'guide-inspect'},n_clicks=0,className='atlas-primary-button'),
               html.Button('Save guide to fieldbook',id='library-guide-save',n_clicks=0,className='atlas-secondary-button'),
               html.Div(id='library-guide-save-status',role='status',className='atlas-help'),
               html.Button('Open fieldbook →',id={'type':'workbench-action','target':'notebook','key':'guide-reference'},n_clicks=0,className='atlas-secondary-button')]
    return children


@callback(Output('library-guide-category','value'),Input({'type':'workbench-action','target':ALL,'key':ALL},'n_clicks'),State('find-material','value'),prevent_initial_call=True)
def inspection_category(clicks,material):
    trigger=callback_context.triggered_id
    return {'glass':'glass','pottery':'ceramics','metal':'metals','stone':'stone'}.get(material,'all') if isinstance(trigger,dict) and trigger.get('key')=='object-guides' and any(clicks or []) else no_update


@callback(Output('fieldbook-store','data',allow_duplicate=True),Output('library-guide-save-status','children'),
          Input('library-guide-save','n_clicks'),State('library-guide-selected','data'),State('fieldbook-store','data'),prevent_initial_call=True)
def save(clicks,selected,book):
    if not clicks:
        return no_update,no_update
    guide=get_guide(selected)
    if not guide:
        return no_update,'Choose a guide from the library.'
    try:
        return merge_entries(EMPTY_BOOK if book is None else book,[reference_entry(guide)]),'Source guide saved separately from your object observations.'
    except (ValueError,TypeError,UnicodeError) as exc:
        return no_update,str(exc)
