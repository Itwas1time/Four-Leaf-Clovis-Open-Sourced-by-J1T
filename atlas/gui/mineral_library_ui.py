"""Search source mineral properties and read attributed statements."""
from dash import dcc, html


def library():
    return html.Div([
        html.Label('Search mineral names, formulas or properties',htmlFor='library-mineral-query',className='atlas-small-label'),
        dcc.Input(id='library-mineral-query',type='search',value='',debounce=True,maxLength=160,
                  placeholder='Try quartz, calcite or SiO',className='atlas-search-input'),
        html.P(id='library-mineral-coverage',className='clovis-library-coverage',role='status'),
        html.P(id='library-mineral-count',className='atlas-help',role='status'),
        html.Div([
            html.Div([html.Div(id='library-mineral-cards',className='clovis-library-list'),
                html.Div([html.Button('Previous',id='library-mineral-previous',n_clicks=0,className='atlas-secondary-button'),
                          html.Span(id='library-mineral-page-label'),
                          html.Button('Next',id='library-mineral-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
            html.Article(id='library-mineral-detail',className='clovis-library-detail'),
        ],className='clovis-library-split'),
        dcc.Store(id='library-mineral-page',data=1),dcc.Store(id='library-mineral-selected'),
    ],id='library-minerals',style={'display':'none'})
