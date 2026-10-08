"""Historical title chronology, read inside the reference shelf."""
from dash import dcc,html


def library():
    return html.Div([
        html.Label('Search newspaper titles, languages or places',htmlFor='library-newspaper-query',className='atlas-small-label'),
        dcc.Input(id='library-newspaper-query',type='search',value='',debounce=True,maxLength=120,
                  placeholder='Try gazette, German or a town name',className='atlas-search-input'),
        dcc.RadioItems(id='library-newspaper-scope',value='national',inline=True,
                      options=[{'label':'All indexed titles','value':'national'},{'label':'Selected state','value':'state'},
                               {'label':'Selected town','value':'town'}],className='clovis-library-tabs'),
        html.P(id='library-newspaper-count',role='status',className='atlas-help'),
        html.Div([
            html.Div([html.Div(id='library-newspaper-cards',className='clovis-library-list'),
                      html.Div([html.Button('Previous',id='library-newspaper-previous',n_clicks=0,className='atlas-secondary-button'),
                                html.Span(id='library-newspaper-page-label'),html.Button('Next',id='library-newspaper-next',n_clicks=0,className='atlas-secondary-button')],className='clovis-library-pagination')]),
            html.Article(id='library-newspaper-detail',className='clovis-library-detail',children=html.P('Choose a title to read its publication years, language and indexed places.')),
        ],className='clovis-library-split'),
        html.P('Title records help establish a historical timeline and find contemporary accounts. Article pages and OCR are separate from this bibliographic catalog.',className='atlas-help'),
        dcc.Store(id='library-newspaper-page',data=1),dcc.Store(id='library-newspaper-selected'),
    ],id='library-newspapers',style={'display':'none'})
