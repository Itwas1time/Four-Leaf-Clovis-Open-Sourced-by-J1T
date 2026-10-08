from dash import dcc, html
from core.investigations import MISSIONS, OUTCOMES


def action(label, target, key, class_name='atlas-secondary-button'):
    return html.Button(label, id={'type': 'workbench-action', 'target': target, 'key': key}, n_clicks=0, className=class_name)


def example_panel():
    return html.Div([
        html.Div(id='resident-example-summary', role='status'),
        html.Button('×', id='resident-example-dismiss', n_clicks=0,
                    title='Close example guidance', **{'aria-label':'Close example guidance'}),
    ], id='resident-example-panel', className='clovis-example-strip', style={'display':'none'})


def workspace():
    return html.Section([
        html.Div('FOLLOW A QUESTION', className='atlas-lead-eyebrow'),
        html.H2('Make an observation. Keep the evidence.', className='clovis-hero-title'),
        html.Div([
            html.Button([html.Span(f'0{index+1}', className='clovis-mission-number'),
                         html.H3(guide['title']), html.P(guide['subtitle']), html.Span('Start investigation →')],
                        id={'type': 'mission-start', 'mission': key}, n_clicks=0, className='clovis-mission-card')
            for index, (key, guide) in enumerate(MISSIONS.items())
        ], className='clovis-mission-grid'),
        html.Div([
            html.Div([
                html.Label('Current investigation', htmlFor='mission-type', className='atlas-small-label'),
                dcc.Dropdown(id='mission-type', options=[{'label': m['title'], 'value': k} for k, m in MISSIONS.items()], value='rocks', clearable=False, className='atlas-filter-dropdown'),
                html.Div(id='mission-evidence', className='clovis-mission-evidence'),
                html.H3('Work with the source'),
                action('Read geological evidence', 'map', 'mission-map'),
                action('Open the map viewer', 'archive', 'mission-archive'),
                action('Inspect an exposed object', 'inspect', 'mission-inspect'),
                dcc.Checklist(id='mission-steps', options=[], value=[], className='clovis-mission-steps'),
            ], className='clovis-mission-guide'),
            html.Div([
                html.Label('Source or map title', htmlFor='mission-source', className='atlas-small-label'),
                dcc.Input(id='mission-source', type='text', maxLength=1000, value='', placeholder='Select a map/evidence card, or record your source', className='atlas-search-input'),
                html.Label('Map date or geological interval', htmlFor='mission-date', className='atlas-small-label'),
                dcc.Input(id='mission-date', type='text', maxLength=120, value='', placeholder='Unknown is fine', className='atlas-search-input'),
                html.Label('What did you observe?', htmlFor='mission-notes', className='atlas-small-label'),
                dcc.Textarea(id='mission-notes', value='', maxLength=1500, className='atlas-find-notes'),
                html.Label('Your comparison', htmlFor='mission-outcome', className='atlas-small-label'),
                dcc.Dropdown(id='mission-outcome', options=[{'label': value, 'value': key} for key, value in OUTCOMES.items()], value='open', clearable=False, className='atlas-filter-dropdown'),
                html.Button('Save investigation to fieldbook', id='mission-save', n_clicks=0, disabled=True, className='atlas-primary-button'),
                html.Div(id='mission-save-status', role='status', className='atlas-help'),
                html.P('Written notes save in this browser. Export your fieldbook to keep a backup. Photos and map image files stay outside the saved record.', className='atlas-help'),
            ], className='clovis-mission-form'),
        ], className='clovis-mission-detail'),
    ], id='mission-workspace', className='clovis-mission-workspace', style={'display': 'none'})
