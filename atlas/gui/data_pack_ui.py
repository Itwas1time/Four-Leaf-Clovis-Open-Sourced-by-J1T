from dash import dcc, html


def library():
    return html.Div([
        html.H3("Choose your local collections"),
        html.P("Download a collection once, then search its records locally. Each collection includes sources, coverage notes and its original measurement conventions.", className="atlas-help"),
        html.Div(id="data-pack-cards", className="clovis-pack-cards"),
        html.Div(id="data-pack-start-status", role="status", className="atlas-help"),
        html.Div(id="data-pack-progress", role="status", className="clovis-pack-progress"),
        dcc.Store(id="data-pack-job", storage_type="local"),
        dcc.Store(id="data-pack-refresh"),
        dcc.Interval(id="data-pack-poll", interval=1000, disabled=True),
    ], id="library-data-packs", style={"display": "none"})
