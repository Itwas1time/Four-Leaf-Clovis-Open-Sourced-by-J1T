from dash import dcc, html

def library():
    return html.Div([
        html.P('Explore published fossil identifications, reported sites and geological context. Choose all fossil groups or focus on dinosaurs. Occurrence records and taxonomic names have separate views.',className='atlas-help'),
        html.Div([
            html.Div([html.Label('Search taxon, site, formation or reference',htmlFor='dinosaur-query',className='atlas-small-label'),
                      dcc.Input(id='dinosaur-query',type='search',value='',debounce=True,maxLength=160,placeholder='Try Trilobita, Mammuthus or Morrison',className='atlas-search-input')]),
            html.Div([html.Label('View',htmlFor='dinosaur-view',className='atlas-small-label'),
                      dcc.Dropdown(id='dinosaur-view',value='occurrences',clearable=False,options=[{'label':'Published fossil occurrences','value':'occurrences'},{'label':'Taxonomic names & sites','value':'taxa'}])]),
            html.Div([html.Label('Search in',htmlFor='dinosaur-scope',className='atlas-small-label'),
                      dcc.Dropdown(id='dinosaur-scope',value='all',clearable=False,options=[{'label':'All record fields','value':'all'},{'label':'Taxonomic names only','value':'names'}])]),
            html.Div([html.Label('Fossil group',htmlFor='dinosaur-lineage',className='atlas-small-label'),
                      dcc.Dropdown(id='dinosaur-lineage',value='fossils',clearable=False,options=[{'label':'All fossil groups in this collection','value':'fossils'},{'label':'Non-avian dinosaurs','value':'nonavian'},{'label':'Fossil birds (Aves)','value':'avian'},{'label':'All Dinosauria','value':'all'}])]),
            html.Div([html.Label('Recorded country code',htmlFor='dinosaur-country',className='atlas-small-label'),
                      dcc.Dropdown(id='dinosaur-country',value='all',clearable=False,options=[{'label':'All recorded countries','value':'all'}])]),
            html.Div([html.Label('Recorded state / province',htmlFor='dinosaur-state',className='atlas-small-label'),
                      dcc.Dropdown(id='dinosaur-state',value='all',clearable=False,options=[{'label':'All recorded states / provinces','value':'all'}])]),
        ],className='clovis-library-filters'),
        html.P('Place words in the search box can also match names and references. Country and state filters use the source’s recorded location fields. Original region labels stay separate; blank locations remain unknown.',className='atlas-help'),
        html.P(id='dinosaur-coverage',role='status',className='clovis-library-coverage'),
        html.P(id='dinosaur-count',role='status',className='atlas-help'),
        html.Div([html.Div([html.Div(id='dinosaur-cards',className='clovis-library-list'),
                           html.Div([html.Button('Previous',id='dinosaur-previous',n_clicks=0,className='atlas-secondary-button'),
                                     html.Span(id='dinosaur-page-label'),html.Button('Next',id='dinosaur-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
                  html.Article(id='dinosaur-detail',className='clovis-library-detail')],className='clovis-library-split'),
        dcc.Store(id='dinosaur-page',data=1),dcc.Store(id='dinosaur-selected'),
    ],id='library-dinosaurs',style={'display':'none'})
