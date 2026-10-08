"""Archaeological publication reader inside the reference library."""
from dash import dcc, html


def library():
    return html.Div([
        html.H3('Read archaeological projects.', className='clovis-library-heading'),
        html.P('Explore the evidence published by research teams: excavation projects, surveys, specialist analyses and comparative databases.', className='atlas-help'),
        html.Div([
            html.Div([html.Label('Search publications', htmlFor='library-project-query', className='atlas-small-label'),
                      dcc.Input(id='library-project-query', type='search', value='', debounce=True, maxLength=120,
                                placeholder='Try pottery, Gabii, survey or Louisiana', className='atlas-search-input')]),
            html.Div([html.Label('Source country context', htmlFor='library-project-country', className='atlas-small-label'),
                      dcc.Dropdown(id='library-project-country', value='all', clearable=False,
                                   options=[{'label':'All country contexts','value':'all'}], className='atlas-filter-dropdown')]),
        ], className='clovis-library-filters'),
        html.P(id='library-project-coverage', className='clovis-project-coverage', role='status'),
        html.P(id='library-project-count', className='atlas-help', role='status'),
        html.Div([
            html.Div([
                html.Div(id='library-project-cards', className='clovis-library-list'),
                html.Div([html.Button('Previous', id='library-project-previous', n_clicks=0, className='atlas-secondary-button'),
                          html.Span(id='library-project-page-label'),
                          html.Button('Next', id='library-project-next', n_clicks=0, className='atlas-secondary-button')], className='clovis-library-pagination'),
            ]),
            html.Article(id='library-project-detail', className='clovis-library-detail', children=html.P('Choose a publication to read its source metadata.')),
        ], className='clovis-library-split'),
        dcc.Store(id='library-project-page', data=1),
        dcc.Store(id='library-project-selected'),
    ], id='library-projects', style={'display':'none'})
