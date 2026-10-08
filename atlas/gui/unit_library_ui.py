"""Offline unit descriptions mapped to public town points."""
from dash import dcc,html


def library():
    return html.Div([
        html.Label('Search rock units, geological ages or map descriptions',htmlFor='library-unit-query',className='atlas-small-label'),
        dcc.Input(id='library-unit-query',type='search',value='',debounce=True,maxLength=120,
                  placeholder='Try limestone, alluvium or Cambrian',className='atlas-search-input'),
        dcc.RadioItems(id='library-unit-scope',value='town',inline=True,
                      options=[{'label':'Selected town','value':'town'},{'label':'Selected state','value':'state'},
                               {'label':'All national units','value':'national'}],className='clovis-library-tabs'),
        html.P(id='library-unit-count',role='status',className='atlas-help'),
        html.Div([
            html.Div([html.Div(id='library-unit-cards',className='clovis-library-list'),
                      html.Div([html.Button('Previous',id='library-unit-previous',n_clicks=0,className='atlas-secondary-button'),
                                html.Span(id='library-unit-page-label'),html.Button('Next',id='library-unit-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
            html.Article(id='library-unit-detail',className='clovis-library-detail',children=html.P('Choose a mapped unit to read the national description and source-map records.')),
        ],className='clovis-library-split'),
        html.P('USGS national map v2 (2026) · 1:500,000 scale. Town results describe the public Census point. Separate map themes are not a measured profile beneath a yard.',className='atlas-help'),
        dcc.Store(id='library-unit-page',data=1),dcc.Store(id='library-unit-selected'),
    ],id='library-units',style={'display':'none'})
