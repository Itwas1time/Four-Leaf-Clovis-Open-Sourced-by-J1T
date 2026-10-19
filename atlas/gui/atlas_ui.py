"""The shared atlas search; collections add evidence without adding tabs."""
from dash import dcc, html
from core.atlas_catalog import KINDS, available_sources
from core.atlas_search_ideas import ideas
from atlas.gui.offline_reference_ui import control as local_source_control


def search_help(query):
    result=ideas(query or '')
    note=('Search terms match source text, including descriptions and references. Check the evidence type and original wording.'
          if isinstance(query,str) and query.strip() else '')
    if not result['choices']:
        return [],note
    return html.Section([
        html.Strong('Search ideas'),
        html.Div([html.Button('Search: '+row['query'], id={'type':'atlas-search-idea','index':row['id']},
            n_clicks=0, className='atlas-secondary-button', **{'data-atlas-search-idea':'true'}) for row in result['choices']],
            className='clovis-search-idea-buttons'),
        html.Small('Choose a separate text search within your current evidence, source and association limits.'),
        html.Details([html.Summary('What these words mean'),
            *[html.Div([html.Strong(topic['title']),html.P(topic['meaning']),
                *local_source_control(topic['source_url'],'search-'+topic['id']),
                html.A(topic['source_title']+' (online)',href=topic['source_url'],target='_blank',rel='noopener noreferrer')]) for topic in result['topics']]]),
    ],className='clovis-search-ideas'),note


def library():
    initial_help,initial_note=search_help('')
    return html.Div([
        html.Div([
            html.Div([html.Label("Search the atlas", htmlFor="atlas-query", className="atlas-small-label"),
                      dcc.Input(id="atlas-query", type="search", value="", debounce=True, maxLength=120,
                                placeholder="Try pottery, glass bottle, a site name or a lab code", className="atlas-search-input")]),
            html.Div([html.Label("Evidence", htmlFor="atlas-kind", className="atlas-small-label"),
                      dcc.Dropdown(id="atlas-kind", value="all", clearable=False,
                                   options=[{"label": label, "value": key} for key, label in KINDS.items()],
                                   className="atlas-filter-dropdown")]),
        ], className="clovis-library-filters clovis-atlas-filters"),
        html.P('Press Enter to search. Choose a result to read its evidence and source.', className='atlas-help'),
        html.P(initial_note, id='atlas-search-note', className='atlas-help'),
        html.Div(initial_help, id='atlas-search-ideas', **{'aria-live':'polite'}),
        html.Details([
            html.Summary("Limit to a source"),
            dcc.Dropdown(id="atlas-source", value="all", clearable=False,
                         options=[{"label": "All sources for this evidence", "value": "all"},
                                  *[{"label": label, "value": key} for key, label in available_sources().items()]],
                         className="atlas-filter-dropdown"),
        ], className="clovis-atlas-source-filter"),
        html.Div([
            html.Div([
                html.Label('Declared resource type', htmlFor='atlas-ads-type', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-ads-type', value='', clearable=False,
                    options=[{'label': 'All source types', 'value': ''}], className='atlas-filter-dropdown'),
            ]),
            html.Div([
                html.Label('Search text in', htmlFor='atlas-ads-field', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-ads-field', value='all', clearable=False,
                    options=[{'label': label, 'value': key} for key, label in
                        (('all', 'All metadata'), ('title', 'Titles only'), ('places', 'Recorded place text only'))],
                    className='atlas-filter-dropdown'),
            ]),
            html.P('Reports, articles and archives are metadata resources, not excavation counts. Recorded place text matches whole words; it does not define a country, town boundary or distance.', className='atlas-help'),
            html.P(id='atlas-ads-status', role='status', className='atlas-help'),
        ], id='atlas-ads-filters', style={'display': 'none'}, className='clovis-library-filters'),
        html.Div([
            html.Div([html.Label('Original subject', htmlFor='atlas-dans-subject', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-dans-subject', value='', clearable=False,
                    options=[{'label': 'All original subjects', 'value': ''}], className='atlas-filter-dropdown'),
                html.Small('Type to find a source subject. Original wording and subject schemes stay separate. Missing subject labels can hide relevant records; clear this limit to search descriptions.')]),
            html.Div([html.Label('Search text in', htmlFor='atlas-dans-field', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-dans-field', value='research', clearable=False,
                    options=[{'label': label, 'value': key} for key, label in (
                        ('research', 'Research text'), ('all', 'All DataCite text'),
                        ('title', 'Titles only'), ('places', 'Recorded place text only'))],
                    className='atlas-filter-dropdown')]),
            html.P('Dataset is a technical resource type. Subjects and descriptions may distinguish object-register entries, desk studies, boreholes and excavation reports; these records are not unique excavation events. Research text searches titles, creators, subjects, descriptions, recorded places and identifiers.', className='atlas-help'),
            html.P(id='atlas-dans-status', role='status', className='atlas-help'),
        ], id='atlas-dans-filters', style={'display': 'none'}, className='clovis-library-filters'),
        html.Div([
            html.Div([html.Label('Native record kind', htmlFor='atlas-amcr-scope', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-amcr-scope', value='all', clearable=False,
                    options=[{'label': label, 'value': key} for key, label in
                        (('all', 'Fieldwork and sites'), ('fieldwork', 'Fieldwork metadata'), ('sites', 'Site metadata'))], className='atlas-filter-dropdown')]),
            html.Div([html.Label('Native fieldwork type', htmlFor='atlas-amcr-method', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-amcr-method', value='', clearable=False,
                    options=[{'label': 'All methods', 'value': ''}], className='atlas-filter-dropdown')]),
            html.Div([html.Label('Search text in', htmlFor='atlas-amcr-field', className='atlas-small-label'),
                dcc.Dropdown(id='atlas-amcr-field', value='evidence', clearable=False,
                    options=[{'label': label, 'value': key} for key, label in
                        (('evidence', 'Archaeology text'), ('all', 'All native metadata'), ('places', 'Recorded district / cadastral text'))], className='atlas-filter-dropdown')]),
            html.P('Fieldwork coverage is incomplete and includes survey and chance finds. Site records stay separate. District/cadastral words do not define a town boundary or find location.', className='atlas-help'),
            html.P(id='atlas-amcr-status', role='status', className='atlas-help'),
        ], id='atlas-amcr-filters', style={'display': 'none'}, className='clovis-library-filters'),
        html.Div([
            html.Div([html.Label('Original assignment type',htmlFor='atlas-raa-method',className='atlas-small-label'),
                dcc.Dropdown(id='atlas-raa-method',value='',clearable=False,
                    options=[{'label':'All original types','value':''}],className='atlas-filter-dropdown')]),
            html.Div([html.Label('Recorded status',htmlFor='atlas-raa-state',className='atlas-small-label'),
                dcc.Dropdown(id='atlas-raa-state',value='',clearable=False,
                    options=[{'label':'All recorded statuses','value':''}],className='atlas-filter-dropdown')]),
            html.Div([html.Label('Recorded ground-disturbance data',htmlFor='atlas-raa-ground',className='atlas-small-label'),
                dcc.Dropdown(id='atlas-raa-ground',value='all',clearable=False,options=[
                    {'label':'All coverage','value':'all'},
                    {'label':'Disturbed-ground geometry recorded','value':'recorded'},
                    {'label':'No disturbed-ground geometry recorded (unknown)','value':'unrecorded'}],className='atlas-filter-dropdown')]),
            html.Div([html.Label('Search text in',htmlFor='atlas-raa-field',className='atlas-small-label'),
                dcc.Dropdown(id='atlas-raa-field',value='all',clearable=False,options=[
                    {'label':'Original assignment metadata','value':'all'},
                    {'label':'Recorded place text only','value':'places'},
                    {'label':'Original identifiers only','value':'identifiers'}],className='atlas-filter-dropdown')]),
            html.P('Counts describe assignment UUIDs, not geometry rows or unique excavations. Native type/status values must co-occur in one source variant. Place text is not a town boundary. Missing disturbed-ground data does not mean no excavation occurred.',className='atlas-help'),
            html.P(id='atlas-raa-status',role='status',className='atlas-help'),
        ],id='atlas-raa-filters',style={'display':'none'},className='clovis-library-filters'),
        html.Div([html.Span(id="atlas-context-label"),
                  html.Button("Clear these limits", id="atlas-clear-context", n_clicks=0,
                              className="clovis-library-back")], id="atlas-context-banner", style={"display": "none"}),
        html.P('Preparing local collections…', id='atlas-search-status', role='status', className='atlas-help'),
        html.P(id="atlas-count", role="status", className="clovis-atlas-count"),
        html.Div([
            html.Div([
                dcc.Loading(html.Div(id="atlas-cards", className="clovis-library-list"), type="dot", delay_show=350),
                html.Div([html.Button("Previous", id="atlas-previous", n_clicks=0, className="atlas-secondary-button"),
                          html.Span(id="atlas-page-label"),
                          html.Button("Next", id="atlas-next", n_clicks=0, className="atlas-secondary-button")],
                         className="clovis-library-pagination"),
            ]),
            html.Article([
                html.Div(id="atlas-detail", children=html.P("Choose a result to read its evidence, context and source.")),
                html.Details([
                    html.Summary("Use in a dig project"),
                    html.P("Keep a cited snapshot with a local project. Its published source and qualifications remain readable.", className="atlas-help"),
                    html.Label("Local dig project", htmlFor="atlas-dig-project", className="atlas-small-label"),
                    dcc.Dropdown(id="atlas-dig-project", options=[], placeholder="Choose a saved project", className="atlas-filter-dropdown"),
                    html.P("Create a project in Fieldbook → Dig records if none is listed.", className="atlas-help"),
                    html.Label("Project source code", htmlFor="atlas-dig-code", className="atlas-small-label"),
                    dcc.Input(id="atlas-dig-code", type="text", value="", maxLength=80, placeholder="For example, REF-01", className="atlas-search-input"),
                    html.Button("Save and open project source", id="atlas-dig-capture", n_clicks=0, className="atlas-primary-button"),
                    html.P(id="atlas-dig-status", role="status", className="atlas-help"),
                ], id="atlas-dig-tools", style={"display": "none"}),
            ], className="clovis-library-detail"),
        ], className="clovis-library-split"),
        html.Details([html.Summary("Search coverage"), html.Div(id="atlas-coverage")], className="clovis-atlas-coverage"),
        dcc.Store(id="atlas-page", data=1), dcc.Store(id="atlas-selected"), dcc.Store(id="atlas-context"),
        dcc.Download(id='atlas-ads-download'),
        dcc.Download(id='atlas-amcr-download'),
        dcc.Download(id='atlas-dans-download'),
        dcc.Download(id='atlas-raa-download'),
    ], id="library-atlas")
