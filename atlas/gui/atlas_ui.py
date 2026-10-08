"""The shared atlas search; collections add evidence without adding tabs."""
from dash import dcc, html
from core.atlas_catalog import KINDS, SOURCES


def library():
    return html.Div([
        html.Div([
            html.Div([html.Label("Search the atlas", htmlFor="atlas-query", className="atlas-small-label"),
                      dcc.Input(id="atlas-query", type="search", value="", debounce=True, maxLength=120,
                                placeholder="Try Arbon, barley, flint or Tyrannosaurus", className="atlas-search-input")]),
            html.Div([html.Label("Evidence", htmlFor="atlas-kind", className="atlas-small-label"),
                      dcc.Dropdown(id="atlas-kind", value="all", clearable=False,
                                   options=[{"label": label, "value": key} for key, label in KINDS.items()],
                                   className="atlas-filter-dropdown")]),
        ], className="clovis-library-filters clovis-atlas-filters"),
        html.Details([
            html.Summary("Limit to a source"),
            dcc.Dropdown(id="atlas-source", value="all", clearable=False,
                         options=[{"label": "All sources for this evidence", "value": "all"},
                                  *[{"label": label, "value": key} for key, label in SOURCES.items()]],
                         className="atlas-filter-dropdown"),
        ], className="clovis-atlas-source-filter"),
        html.Div([html.Span(id="atlas-context-label"),
                  html.Button("Search the whole atlas", id="atlas-clear-context", n_clicks=0,
                              className="clovis-library-back")], id="atlas-context-banner", style={"display": "none"}),
        html.P(id="atlas-count", role="status", className="clovis-atlas-count"),
        html.Div([
            html.Div([
                dcc.Loading(html.Div(id="atlas-cards", className="clovis-library-list"), type="dot", delay_show=350),
                html.Div([html.Button("Previous", id="atlas-previous", n_clicks=0, className="atlas-secondary-button"),
                          html.Span(id="atlas-page-label"),
                          html.Button("Next", id="atlas-next", n_clicks=0, className="atlas-secondary-button")],
                         className="clovis-library-pagination"),
            ]),
            html.Article(id="atlas-detail", className="clovis-library-detail",
                         children=html.P("Choose a result to read its evidence, context and source.")),
        ], className="clovis-library-split"),
        html.Details([html.Summary("Search coverage"), html.Div(id="atlas-coverage")], className="clovis-atlas-coverage"),
        dcc.Store(id="atlas-page", data=1), dcc.Store(id="atlas-selected"), dcc.Store(id="atlas-context"),
    ], id="library-atlas")
