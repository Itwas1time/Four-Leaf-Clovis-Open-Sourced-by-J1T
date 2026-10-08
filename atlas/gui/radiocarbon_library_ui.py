from dash import dcc, html


def library():
    return html.Div([
        html.P("Read published laboratory determinations with their sample materials, methods, uncertainties and sources.", className="atlas-help"),
        html.Div([
            html.Div([html.Label("Search material, laboratory ID, site name or reference", htmlFor="radiocarbon-query", className="atlas-small-label"),
                      dcc.Input(id="radiocarbon-query", type="search", value="", debounce=True, maxLength=160,
                                placeholder="Try charcoal, shell or a laboratory identifier", className="atlas-search-input")]),
            html.Div([html.Label("Recorded country", htmlFor="radiocarbon-country", className="atlas-small-label"),
                      dcc.Dropdown(id="radiocarbon-country", value="all", clearable=False,
                                   options=[{"label": "All recorded countries", "value": "all"}], className="atlas-filter-dropdown")]),
        ], className="clovis-library-filters"),
        html.Details([html.Summary("Filter laboratory ages (uncalibrated BP)"),
                      html.P("These are laboratory radiocarbon years. They are not calendar years BCE or CE.", className="atlas-help"),
                      html.Div([html.Div([html.Label("Minimum laboratory age", htmlFor="radiocarbon-min-age"),
                                          dcc.Input(id="radiocarbon-min-age", type="number", value=None, step=1, debounce=True)]),
                                html.Div([html.Label("Maximum laboratory age", htmlFor="radiocarbon-max-age"),
                                          dcc.Input(id="radiocarbon-max-age", type="number", value=None, step=1, debounce=True)])], className="clovis-library-filters")]),
        html.P(id="radiocarbon-coverage", className="clovis-library-coverage", role="status"),
        html.P(id="radiocarbon-count", className="atlas-help", role="status"),
        html.Div([
            html.Div([html.Div(id="radiocarbon-cards", className="clovis-library-list"),
                      html.Div([html.Button("Previous", id="radiocarbon-previous", n_clicks=0, className="atlas-secondary-button"),
                                html.Span(id="radiocarbon-page-label"),
                                html.Button("Next", id="radiocarbon-next", n_clicks=0, className="atlas-secondary-button")], className="clovis-library-pagination")]),
            html.Article(id="radiocarbon-detail", className="clovis-library-detail"),
        ], className="clovis-library-split"),
        dcc.Store(id="radiocarbon-page", data=1),
        dcc.Store(id="radiocarbon-selected"),
    ], id="library-radiocarbon", style={"display": "none"})
