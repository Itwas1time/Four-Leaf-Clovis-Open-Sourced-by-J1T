from dash import dcc, html


def library():
    return html.Div([
        html.H3("Choose your local collections"),
        html.P("Download a collection once, or choose its ZIP from this computer, then search its records locally. Each collection includes sources, coverage notes and its original measurement conventions.", className="atlas-help"),
        html.P("Install from ZIP checks the complete file against the selected collection snapshot before using it. Keep this page open during the transfer; checking continues in the background afterward.", className="atlas-help"),
        html.Div([
            html.Div(id="data-pack-start-status", role="status", className="atlas-help"),
            html.Button('Cancel ZIP transfer', id='data-pack-cancel-local', type='button', disabled=True, style={'display': 'none'}, className='atlas-secondary-button'),
            html.Div(id="data-pack-progress", role="status", className="clovis-pack-progress"),
        ], className='clovis-pack-status', role='region', **{'aria-label': 'Collection installation status'}),
        html.Div(id="data-pack-cards", className="clovis-pack-cards"),
        dcc.Store(id="data-pack-job", storage_type="local"),
        dcc.Store(id="data-pack-refresh"),
        dcc.Interval(id="data-pack-poll", interval=1000, disabled=True),
    ], id="library-data-packs", style={"display": "none"})
