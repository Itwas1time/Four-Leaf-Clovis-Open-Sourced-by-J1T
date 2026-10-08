"""Practical source readings for examining common historical objects."""
from dash import dcc,html
from core.object_material_guides import CATEGORIES


def library():
    return html.Div([
        html.Div([
            html.Div([html.Label('Search observable features',htmlFor='library-guide-query',className='atlas-small-label'),
                      dcc.Input(id='library-guide-query',type='search',value='',debounce=True,maxLength=120,
                                placeholder='Try mold seam, salt glaze or cut nail',className='atlas-search-input')]),
            html.Div([html.Label('Object material or type',htmlFor='library-guide-category',className='atlas-small-label'),
                      dcc.Dropdown(id='library-guide-category',value='all',clearable=False,options=[{'label':'All object guides','value':'all'}]+[{'label':label,'value':key} for key,label in CATEGORIES],className='atlas-filter-dropdown')]),
        ],className='clovis-library-filters'),
        html.P(id='library-guide-count',role='status',className='atlas-help'),
        html.Div([
            html.Div([html.Div(id='library-guide-cards',className='clovis-library-list'),
                      html.Div([html.Button('Previous',id='library-guide-previous',n_clicks=0,className='atlas-secondary-button'),
                                html.Span(id='library-guide-page-label'),html.Button('Next',id='library-guide-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
            html.Article(id='library-guide-detail',className='clovis-library-detail',children=html.P('Choose an object guide to read manufacturing clues, useful questions and recording prompts.')),
        ],className='clovis-library-split'),
        dcc.Store(id='library-guide-page',data=1),dcc.Store(id='library-guide-selected'),
    ],id='library-guides',style={'display':'none'})
