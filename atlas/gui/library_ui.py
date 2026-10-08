"""Searchable public reference records and short statewide readings."""
from dash import dcc, html
from core.us_places import STATE_NAMES
from atlas.gui.fossil_library_ui import library as fossil_library
from atlas.gui.newspaper_library_ui import library as newspaper_library
from atlas.gui.unit_library_ui import library as unit_library
from atlas.gui.object_guide_ui import library as object_guides
from atlas.gui.archaeology_library_ui import library as archaeology_library
from atlas.gui.mineral_library_ui import library as mineral_library
from atlas.gui.radiocarbon_library_ui import library as radiocarbon_library
from atlas.gui.data_pack_ui import library as data_pack_library
from atlas.gui.dinosaur_library_ui import library as dinosaur_library
from atlas.gui.atlas_ui import library as atlas_library


def reading_nav(query):
    return html.Button('Change search ↑',type='button',className='clovis-library-back',**{'data-library-back':query})


def workspace():
    return html.Section([
        html.P('Explore published places, objects, assemblages and fossils. Search once, read the evidence and follow its source.', className='atlas-help'),
        html.Div([html.Button('Atlas search', id='atlas-return', n_clicks=0, className='atlas-secondary-button'),
                  html.Button('Manage offline collections', id='atlas-manage-packs', n_clicks=0, className='atlas-secondary-button')],
                 className='clovis-atlas-toolbar'),
        html.Details([html.Summary('Specialist searches'),
            dcc.Dropdown(id='library-section', value='atlas', clearable=False,
                      options=[{'label':'Atlas search','value':'atlas'}, {'label':'Object guides','value':'guides'},{'label':'Museum objects','value':'objects'}, {'label':'Fossil specimens','value':'fossils'},
                               {'label':'Newspaper history','value':'newspapers'}, {'label':'Mapped geology','value':'units'},
                               {'label':'State fossil stories','value':'states'}, {'label':'Archaeological projects','value':'projects'},
                               {'label':'Mineral properties','value':'minerals'},
                               {'label':'Radiocarbon dates','value':'radiocarbon'},
                               {'label':'Dinosaur taxa & sites','value':'dinosaurs'},
                               {'label':'Data collections','value':'packs'}],
                      className='atlas-filter-dropdown'),
        ], className='clovis-atlas-specialist'),
        atlas_library(),
        html.Div([
            html.Div([html.Label('Collection',htmlFor='library-object-collection',className='atlas-small-label'),
                      dcc.Dropdown(id='library-object-collection',value='met',clearable=False,
                                   options=[{'label':'Met · dated object references','value':'met'},
                                            {'label':'Smithsonian · anthropology','value':'si'}],className='atlas-filter-dropdown')],className='clovis-library-collection'),
            html.Div([
                html.Div([html.Label('Search the collection', htmlFor='library-object-query', className='atlas-small-label'),
                          dcc.Input(id='library-object-query', type='search', value='', debounce=True, maxLength=120,
                                    placeholder='Try bottle, earthenware, button or flint', className='atlas-search-input')]),
                html.Div([html.Label('Object group', id='library-object-group-label', htmlFor='library-object-material', className='atlas-small-label'),
                          dcc.Dropdown(id='library-object-material', value='all', clearable=False,
                                       options=[{'label':'All groups','value':'all'}, {'label':'Glass','value':'glass_containers'},
                                                {'label':'Ceramics','value':'ceramic_vessels'}, {'label':'Metal tools & hardware','value':'metal_implements_hardware'},
                                                {'label':'Coins, medals & tokens','value':'coins_medals_tokens'}, {'label':'Buttons','value':'buttons'},
                                                {'label':'Stone implements','value':'stone_implements'}], className='atlas-filter-dropdown')]),
                html.Div([html.Label('Catalog date',htmlFor='library-object-era',className='atlas-small-label'),
                          dcc.Dropdown(id='library-object-era',value='historic',clearable=False,
                                       options=[{'label':'Before 1951','value':'historic'},{'label':'Before 1800','value':'early'},
                                                {'label':'1800–1950','value':'industrial'},{'label':'All recorded dates','value':'all'}],className='atlas-filter-dropdown')]),
            ], className='clovis-library-filters'),
            html.P(id='library-object-count', role='status', className='atlas-help'),
            html.Div([
                html.Div([
                    html.Div(id='library-object-cards', className='clovis-library-list'),
                    html.Div([html.Button('Previous',id='library-object-previous',n_clicks=0,className='atlas-secondary-button'),
                              html.Span(id='library-object-page-label'),
                              html.Button('Next',id='library-object-next',n_clicks=0,className='atlas-secondary-button')], className='clovis-library-pagination'),
                ]),
                html.Article(id='library-object-detail', className='clovis-library-detail', children=html.P('Choose a record to read its details.')),
            ], className='clovis-library-split'),
            html.P(id='library-object-source', className='atlas-help'),
            dcc.Store(id='library-object-page', data=1),
            dcc.Store(id='library-object-selected'),
        ], id='library-objects', style={'display':'none'}),
        fossil_library(),
        newspaper_library(),
        unit_library(),
        object_guides(),
        archaeology_library(),
        mineral_library(),
        radiocarbon_library(),
        dinosaur_library(),
        data_pack_library(),
        html.Div([
            html.Label('Read a state or territory', htmlFor='library-state', className='atlas-small-label'),
            dcc.Dropdown(id='library-state', value=None, clearable=False, placeholder='Choose a state to read',
                         options=[{'label':name,'value':state} for state,name in sorted(STATE_NAMES.items(),key=lambda item:item[1])],
                         className='atlas-filter-dropdown'),
            html.Div(id='library-state-reading', className='clovis-library-reading'),
        ], id='library-states', style={'display':'none'}),
    ], id='library-workspace', className='clovis-library-workspace', style={'display':'none'})
