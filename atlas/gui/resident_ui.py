"""Controls and report for the resident town-context workflow."""
from dash import dcc, html

from core.resident_context import CONTEXTS
from core.us_places import STATE_NAMES, states


def controls():
    return html.Section([
        html.Div("01 / YOUR PLACE", className="atlas-lead-eyebrow"),
        html.H2("Start somewhere.", className="atlas-brief-heading"),
        html.P("Pick a town you know. No address needed.", className="atlas-resident-intro"),
        html.Button('Try an example ↗', id='resident-demo', n_clicks=0,
                    title='Randomly choose one of 100 public-town questions. Uses your current online geology setting.',
                    className='clovis-example-button clovis-example-invitation'),
        html.Label("State or territory", htmlFor="resident-state", className="atlas-small-label"),
        dcc.Dropdown(id="resident-state", options=[{"label": f"{STATE_NAMES[value]} ({value})", "value": value} for value in sorted(states(), key=STATE_NAMES.get)],
                     placeholder="Choose state", className="atlas-filter-dropdown", clearable=False),
        html.Label("Town or Census place", htmlFor="resident-place", className="atlas-small-label"),
        dcc.Dropdown(id="resident-place", options=[], placeholder="Type a town name after choosing state",
                     className="atlas-filter-dropdown", disabled=True),
        html.P("Type to search. For rural places, choose a nearby town.", className="atlas-help"),
        html.Button(["Explore this town", html.Span(" →", **{"aria-hidden": "true"})], id="resident-build", n_clicks=0,
                    disabled=True, className="atlas-primary-button"),
        html.P("Includes online rock maps at the public town point.", id="resident-lookup-note", className="atlas-help"),
        dcc.Loading(html.Div(id="resident-status", children="Choose a state, then a town.",
                            role="status", className="atlas-place-status"), type="dot", color="#2d6a4f"),
        html.Div("Reading the rock maps…", id="resident-loading", role="status", className="atlas-status-card", style={"display": "none"}),
        html.Details([
        html.Summary("Options & land-use context"),
        html.Label("What do you know about past land use?", htmlFor="resident-history", className="atlas-small-label"),
        dcc.Dropdown(id="resident-history", options=[{"label": label, "value": key} for key, label in CONTEXTS.items()],
                     value="unknown", clearable=False, className="atlas-filter-dropdown"),
        html.Div([
            dcc.Checklist(id="resident-online", options=[{"label": " Include local rock maps (online)", "value": "geology"}],
                          value=["geology"], className="atlas-lead-support-filter"),
            html.P("Macrostrat runs when you select Explore. Uncheck for an offline report.", className="atlas-help"),
            html.Details([html.Summary("What is shared?"), html.P("Only the public town point and standard network metadata go to Macrostrat. Its maps are regional context, not an assessment of your yard.")], className="atlas-privacy-note"),
        ], className="atlas-geology-option"),
        ], className="clovis-place-options"),
        html.P("Public town context. Your yard may differ.", className="atlas-evidence-note"),
        html.Details([
            html.Summary("Statewide background and sources"),
            dcc.Markdown(id="resident-state-guide", className="atlas-state-guide", link_target="_blank", dangerously_allow_html=False),
        ], id="resident-state-background", className="atlas-resident-evidence", open=False),
    ], id="resident-controls", className="atlas-resident-controls")


def report_panel():
    return html.Section([
        html.Div([
            html.Div("03 / KEEP A RECORD", className="atlas-lead-eyebrow"),
            html.H2("A place has a story.", id="resident-report-heading", className="atlas-brief-heading"),
            html.Button("Choose a town ↗", id="resident-choose-place", n_clicks=0,
                        className="atlas-secondary-button atlas-place-action"),
        ], className="atlas-resident-actions"),
        html.Div([
            html.P("Explore a town to start a source-linked record. Saved notes stay in your browser."),
        ], id="resident-empty-state", className="atlas-empty-state"),
        html.Div(id='resident-evidence-overview', className='clovis-evidence-overview'),
        html.Div([
            html.Button('Record an observation →', id={'type':'workbench-action','target':'missions','key':'inspector-mission'}, n_clicks=0, className='atlas-primary-button'),
        ], className='clovis-inspector-tools'),
        html.Div([
        html.Button('Save town context',id='resident-save',n_clicks=0,className='atlas-secondary-button'),
        html.Button("Download notes ↓", id="resident-download-button", n_clicks=0,
                    disabled=True, className="atlas-secondary-button atlas-brief-download"),
        ], className='clovis-note-actions'),
        html.Div(id='resident-save-status',role='status',className='atlas-help'),
        html.Button('Open fieldbook →', id={'type':'workbench-action','target':'notebook','key':'after-town-save'}, n_clicks=0,
                    className='atlas-secondary-button clovis-saved-next'),
        html.Details([
            html.Summary('Read the text summary'),
            dcc.Markdown(id="resident-summary", className="atlas-resident-summary", link_target="_blank", dangerously_allow_html=False),
        ], className='atlas-resident-evidence'),
        html.Details([
            html.Summary("Read map evidence and full field notes"),
            dcc.Markdown(id="resident-preview", className="atlas-brief-preview", link_target="_blank", dangerously_allow_html=False),
        ], id="resident-evidence", className="atlas-resident-evidence"),
    ], id="resident-inspector", className="atlas-brief-panel")
