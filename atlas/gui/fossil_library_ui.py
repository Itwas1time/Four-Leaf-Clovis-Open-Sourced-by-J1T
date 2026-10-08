"""Fossil specimen taxonomy and factual catalog reader."""
from dash import dcc,html


def library():
    return html.Div([
        html.Label('Search fossil names and classifications',htmlFor='library-fossil-query',className='atlas-small-label'),
        dcc.Input(id='library-fossil-query',value='',type='search',debounce=True,maxLength=120,
                  placeholder='Try Trilobita, Brachiopoda or Diplodocus',className='atlas-search-input'),
        dcc.RadioItems(id='library-fossil-view',value='taxa',inline=True,
                      options=[{'label':'Group by taxon','value':'taxa'},{'label':'Specimen records','value':'specimens'}],className='clovis-library-tabs'),
        html.P('Grouped names reduce repeated specimens. Specimen searches also include recorded ages and formations.',className='atlas-help'),
        html.P(id='library-fossil-count',role='status',className='atlas-help'),
        html.Div([
            html.Div([html.Div(id='library-fossil-cards',className='clovis-library-list'),
                      html.Div([html.Button('Previous',id='library-fossil-previous',n_clicks=0,className='atlas-secondary-button'),
                                html.Span(id='library-fossil-page-label'),html.Button('Next',id='library-fossil-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
            html.Article(id='library-fossil-detail',className='clovis-library-detail',children=html.P('Choose a specimen reference to read its taxonomy and geological context.')),
        ],className='clovis-library-split'),
        html.P(id='library-fossil-source',className='atlas-help'),
        dcc.Store(id='library-fossil-page',data=1),dcc.Store(id='library-fossil-selected'),
    ],id='library-fossils',style={'display':'none'})
