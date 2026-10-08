"""Controls and report for the resident town-context workflow."""
from dash import dcc, html

from core.resident_context import CONTEXTS
from core.us_places import STATE_NAMES, states


def controls():
    return html.Section([
        html.Div("LOOK A LITTLE CLOSER", className="atlas-lead-eyebrow"),
        html.H2("What might be here?", className="atlas-brief-heading"),
        html.P("Choose a state, search for your town, then select Explore. Get local rock maps, historical clues and sources to investigate next.", className="atlas-resident-intro"),
        html.Div("01  /  CHOOSE YOUR PLACE", className="atlas-step-label"),
        html.Label("State or territory", htmlFor="resident-state", className="atlas-small-label"),
        dcc.Dropdown(id="resident-state", options=[{"label": f"{STATE_NAMES[value]} ({value})", "value": value} for value in sorted(states(), key=STATE_NAMES.get)],
                     placeholder="Choose state", className="atlas-filter-dropdown", clearable=False),
        html.Label("Town or Census place", htmlFor="resident-place", className="atlas-small-label"),
        dcc.Dropdown(id="resident-place", options=[], placeholder="Type a town name after choosing state",
                     className="atlas-filter-dropdown", disabled=True),
        html.P("Click the town box, then type in its search field. A town name or ‘Santa Rosa, CA’ works. For rural areas, choose a nearby town.", className="atlas-help"),
        html.Div("02  /  ADD SOME CONTEXT", className="atlas-step-label"),
        html.Label("What do you know about past land use?", htmlFor="resident-history", className="atlas-small-label"),
        dcc.Dropdown(id="resident-history", options=[{"label": label, "value": key} for key, label in CONTEXTS.items()],
                     value="unknown", clearable=False, className="atlas-filter-dropdown"),
        html.Div([
            dcc.Checklist(id="resident-online", options=[{"label": " Include local rock maps (online)", "value": "geology"}],
                          value=["geology"], className="atlas-lead-support-filter"),
            html.P("Macrostrat runs when you select Explore. Uncheck for an offline report.", className="atlas-help"),
            html.Details([html.Summary("What is shared?"), html.P("Only the public town point and standard network metadata go to Macrostrat. Its maps are regional context, not an assessment of your yard.")], className="atlas-privacy-note"),
        ], className="atlas-geology-option"),
        html.Button(["Explore this town", html.Span(" →", **{"aria-hidden": "true"})], id="resident-build", n_clicks=0, disabled=True, className="atlas-primary-button"),
        html.Div([html.Strong("Context, not a prediction."), html.P("Clovis keeps sources and unknowns visible. Discovery odds need survey evidence we don't yet have.")], className="atlas-evidence-note"),
    ], id="resident-controls", className="atlas-resident-controls")


def report_panel():
    return html.Section([
        html.Div("YOUR FIELD NOTES", className="atlas-lead-eyebrow"),
        html.H2("A place has a story.", className="atlas-brief-heading"),
        dcc.Loading(html.Div(id="resident-status", children="Choose a town and select Explore this town.",
                             className="atlas-status-card"), type="dot", color="#2d6a4f"),
        html.Div("Reading public town context and rock maps…", id="resident-loading", role="status", className="atlas-status-card", style={"display": "none"}),
        dcc.Markdown(id="resident-state-guide", className="atlas-state-guide", link_target="_blank", dangerously_allow_html=False),
        html.Div([
            html.Div([html.Span(className="atlas-landline"), html.Span(className="atlas-landline"), html.Span(className="atlas-landline")], className="atlas-empty-art", **{"aria-hidden": "true"}),
            html.H3("Start with the place you know."),
            html.P("Choose a town and explore. Your notes will connect local possibilities to their sources."),
            html.Div([html.Span("01"), html.Div([html.Strong("Historical objects"), html.P("Clues from how land was used")])], className="atlas-empty-topic"),
            html.Div([html.Span("02"), html.Div([html.Strong("Rocks & fossils"), html.P("Regional maps and formation guides")])], className="atlas-empty-topic"),
            html.Div([html.Span("03"), html.Div([html.Strong("Evidence & unknowns"), html.P("Sources, limits, and what to check next")])], className="atlas-empty-topic"),
        ], id="resident-empty-state", className="atlas-empty-state"),
        html.Button("↓  Download field notes", id="resident-download-button", n_clicks=0,
                    disabled=True, className="atlas-primary-button atlas-brief-download"),
        html.Button('Save to fieldbook',id='resident-save',n_clicks=0,className='atlas-secondary-button'),
        html.Div(id='resident-save-status',role='status',className='atlas-help'),
        dcc.Markdown(id="resident-summary", className="atlas-resident-summary", link_target="_blank", dangerously_allow_html=False),
        html.Details([
            html.Summary("Read map evidence and full field notes"),
            dcc.Markdown(id="resident-preview", className="atlas-brief-preview", link_target="_blank", dangerously_allow_html=False),
        ], id="resident-evidence", className="atlas-resident-evidence"),
    ], id="resident-inspector", className="atlas-brief-panel")
