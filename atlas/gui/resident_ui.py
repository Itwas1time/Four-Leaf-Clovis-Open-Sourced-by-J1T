"""Controls and report for the resident town-context workflow."""
from dash import dcc, html

from core.resident_context import CONTEXTS
from core.us_places import states


def controls():
    return html.Section([
        html.Div("LOCAL CURIOSITY", className="atlas-lead-eyebrow"),
        html.H2("What might be here?", className="atlas-brief-heading"),
        html.P("Explore historical objects, fossils and geology around a U.S. town. Start with public town context; no address needed.", className="atlas-help"),
        html.Label("State or territory", htmlFor="resident-state", className="atlas-small-label"),
        dcc.Dropdown(id="resident-state", options=[{"label": value, "value": value} for value in states()],
                     placeholder="Choose state", className="atlas-filter-dropdown"),
        html.Label("Town or Census place", htmlFor="resident-place", className="atlas-small-label"),
        dcc.Dropdown(id="resident-place", options=[], placeholder="Type a town name after choosing state",
                     className="atlas-filter-dropdown"),
        html.P("Search returns up to 30 matches. Not every rural location is a Census place; a nearby town remains broad context.", className="atlas-help"),
        html.Label("What do you know about past land use?", htmlFor="resident-history", className="atlas-small-label"),
        dcc.Dropdown(id="resident-history", options=[{"label": label, "value": key} for key, label in CONTEXTS.items()],
                     value="unknown", clearable=False, className="atlas-filter-dropdown"),
        dcc.Checklist(id="resident-online", options=[{"label": " Request regional geology from Macrostrat", "value": "geology"}],
                      value=[], className="atlas-lead-support-filter"),
        html.P("Optional online lookup sends only the public town point to Macrostrat. It receives network metadata. Its maps do not describe an individual yard.", className="atlas-help"),
        html.Button("Explore this town", id="resident-build", n_clicks=0, className="atlas-primary-button"),
        html.P("Discovery odds need representative survey outcomes. Clovis will show when a likelihood cannot be estimated.", className="atlas-help"),
    ], id="resident-controls", className="atlas-resident-controls")


def report_panel():
    return html.Section([
        html.Div("YOUR LOCAL CONTEXT", className="atlas-lead-eyebrow"),
        html.H2("A starting point for your curiosity", className="atlas-brief-heading"),
        dcc.Loading(html.Div(id="resident-status", children="Choose a town and select Explore this town.",
                             className="atlas-status-card"), type="dot", color="#fbbf24"),
        html.Button("Download this context report", id="resident-download-button", n_clicks=0,
                    disabled=True, className="atlas-primary-button atlas-brief-download"),
        dcc.Markdown(id="resident-preview", children="The report will explain plausible find types, source evidence and missing information.",
                     className="atlas-brief-preview", link_target="_blank", dangerously_allow_html=False),
    ], id="resident-inspector", className="atlas-brief-panel")
