from __future__ import annotations

from dash import dcc, html

from atlas.gui.data.lead_catalog import GOALS, PERIODS, REGIONS, matching_leads
from atlas.gui.data.public_catalog import SOURCE_NAMES, overview
from atlas.gui.resident_ui import controls as resident_controls, report_panel as resident_report_panel
from atlas.gui.inspection_ui import controls as inspection_controls, report_panel as inspection_report_panel
from atlas.gui.fieldbook_ui import controls as fieldbook_controls, inspector as fieldbook_inspector
from atlas.gui.theme_ui import theme_toggle
from atlas.gui.styles import BG_PANEL, BORDER, PANEL_STYLE, SECTION_HEADER_STYLE, TEXT_DIM, TEXT_PRIMARY, TEXT_SECONDARY

_CURRENT_LEADS = matching_leads()
_INITIAL_LEAD = _CURRENT_LEADS[0] if _CURRENT_LEADS else None
_CATALOG = overview()
_SITE_COUNT = sum(row["count"] for row in _CATALOG["counts"] if row["kind"] == "site")
_INSTITUTION_COUNT = sum(row["count"] for row in _CATALOG["counts"] if row["kind"] == "institution")


def build_header() -> html.Header:
    return html.Header(
        [
            html.Div(
                [
                    html.Img(
                        src="/assets/clovis-bone-clover.svg",
                        className="atlas-logo-mark",
                        alt="Clovis four-leaf clover formed from bones",
                        style={"width": "40px", "height": "40px", "display": "block", "transform": "none", "flex": "0 0 auto"},
                    ),
                    html.Div([html.Span("clovis", className="atlas-brand-title"),
                              html.Span("A little curiosity, Dig deeper.", className="atlas-brand-tagline")]),
                ], className="atlas-brand"
            ),
            dcc.RadioItems(id="workflow-mode", options=[
                {"label": "Explore", "value": "resident"},
                {"label": "Inspect a find", "value": "inspect"},
                {"label": "Fieldbook", "value": "notebook"},
                {"label": "Research", "value": "research"},
            ], value="resident", className="atlas-workflow-mode atlas-primary-nav"),
            html.Div([
                html.Span(id="header-region", children="No town selected"),
                html.Button("Choose town ↗", id="header-place-button", n_clicks=0,
                            className="atlas-secondary-button atlas-header-place-button",
                            **{"aria-label": "Choose or change a town"}),
            ], className="atlas-header-location"),
            theme_toggle(),
        ],
        className="atlas-header",
    )


def _section(title: str, children: list, *, open: bool = False, section_id: str | None = None) -> html.Details:
    return html.Details(
        [html.Summary(title, style=SECTION_HEADER_STYLE), html.Div(children, style={"padding": "0 14px 14px"})],
        open=open,
        className="atlas-panel-disclosure",
        **({"id": section_id} if section_id else {}),
    )


def build_layer_panel() -> html.Aside:
    panel = html.Aside(
        id="layer-panel",
        style={**PANEL_STYLE, "width": "320px", "flexShrink": "0", "borderRight": f"1px solid {BORDER}"},
        children=[
            html.Div("Public directory", className="atlas-panel-title"),
            _section(
                "Documented records",
                [
                    html.Div(
                        f"{_SITE_COUNT:,} site records · {_INSTITUTION_COUNT:,} institution records"
                        if _CATALOG["built_on"] else "Public catalogue not built yet",
                        className="atlas-catalog-totals",
                    ),
                    html.Div(
                        " · ".join(
                            f"{SOURCE_NAMES.get(row['source_key'], row['source_key'])}: {row['count']:,} {row['kind']}"
                            for row in _CATALOG["counts"]
                        ) + (f" · NPS extract dated {_CATALOG['nrhp_scrape_date']}" if _CATALOG["nrhp_scrape_date"] else ""),
                        className="atlas-catalog-breakdown",
                    ),
                    html.Div(
                        "Records may overlap across sources. They are not ranked excavation targets or confirmed partners.",
                        className="atlas-help",
                    ),
                    dcc.RadioItems(
                        id="catalog-kind", options=[
                            {"label": " Sites", "value": "site"},
                            {"label": " Institutions", "value": "institution"},
                        ], value="site", className="atlas-catalog-kinds", inline=True,
                    ),
                    dcc.Input(
                        id="catalog-search", type="search", debounce=True,
                        placeholder="Search name, country, or source ID",
                        className="atlas-search-input atlas-catalog-search",
                    ),
                    dcc.Dropdown(
                        id="catalog-source", value="all", clearable=False,
                        options=[{"label": "Every source", "value": "all"}]
                        + [{"label": label, "value": key} for key, label in SOURCE_NAMES.items()],
                        className="atlas-filter-dropdown",
                    ),
                    dcc.Dropdown(
                        id="catalog-country", value="all", clearable=False,
                        options=[{"label": "Every country", "value": "all"}]
                        + [{"label": country, "value": country} for country in _CATALOG["countries"]],
                        className="atlas-filter-dropdown",
                    ),
                    html.Div(
                        "For institutions, country means a documented organization office, not a fieldwork site. "
                        "Unknown locations remain under Every country.",
                        className="atlas-help atlas-lead-footnote",
                    ),
                    html.Div(id="catalog-status", className="atlas-lead-count"),
                    html.Div(id="catalog-results", className="atlas-catalog-results"),
                    html.Div([
                        html.Button("Previous", id="catalog-prev", n_clicks=0, className="atlas-secondary-button"),
                        html.Span(id="catalog-page-label", className="atlas-catalog-page-label"),
                        html.Button("Next", id="catalog-next", n_clicks=0, className="atlas-secondary-button"),
                    ], className="atlas-catalog-pagination"),
                    html.Div(
                        "Source scope: direct Wikidata site and archaeology museum or society types; "
                        "U.S. National Register archaeology or prehistory entries; named institutions from researched projects. "
                        "No restricted locations or dig coordinates are shown.",
                        className="atlas-help atlas-lead-footnote",
                    ),
                ],
            ),
            html.Div("Research leads", className="atlas-panel-title atlas-subtitle"),
            _section(
                "Where to begin",
                [
                    html.Div("Compare active field projects by what is already known, how exploratory the next work is, and whether a support route is published.", className="atlas-help"),
                    html.Label("Your priority", className="atlas-small-label"),
                    dcc.RadioItems(
                        id="lead-goal",
                        options=[{"label": label, "value": key} for key, label in GOALS.items()],
                        value="evidence",
                        className="atlas-lead-goals",
                    ),
                    html.Label("Region", className="atlas-small-label"),
                    dcc.Dropdown(
                        id="lead-region-filter",
                        options=[{"label": "Every region", "value": "all"}] + [{"label": item, "value": item} for item in REGIONS],
                        value="all",
                        clearable=False,
                        className="atlas-filter-dropdown",
                    ),
                    html.Label("Period", className="atlas-small-label"),
                    dcc.Dropdown(
                        id="lead-period-filter",
                        options=[{"label": "Every period", "value": "all"}] + [{"label": item, "value": item} for item in PERIODS],
                        value="all",
                        clearable=False,
                        className="atlas-filter-dropdown",
                    ),
                    dcc.Checklist(
                        id="lead-support-filter",
                        options=[{"label": " Show only published support routes", "value": "published"}],
                        value=[],
                        className="atlas-lead-support-filter",
                    ),
                    dcc.Input(
                        id="lead-search",
                        type="search",
                        placeholder="Search sites, institutions, evidence",
                        debounce=True,
                        className="atlas-search-input atlas-lead-search",
                    ),
                    html.Div(id="lead-results-status", className="atlas-lead-count"),
                    html.Div(id="field-lead-list", className="atlas-lead-list"),
                    html.Div(
                        "The order describes evidence readiness or access, not discovery odds or investment returns. Recheck the linked source before outreach.",
                        className="atlas-help atlas-lead-footnote",
                    ),
                ],
                open=True,
            ),
            html.Div("Explore the map", className="atlas-panel-title atlas-subtitle"),
            _section(
                "Base Map",
                [
                    dcc.RadioItems(
                        id="basemap-selector",
                        options=[
                            {"label": " Terrain", "value": "terrain"},
                            {"label": " Topographic", "value": "topographic"},
                            {"label": " Satellite", "value": "satellite"},
                            {"label": " Dark", "value": "dark"},
                        ],
                        value="terrain",
                        className="layer-checklist",
                        inputStyle={"marginRight": "6px"},
                        labelStyle={"display": "block", "padding": "4px 0", "fontSize": "12px", "color": TEXT_PRIMARY},
                    )
                ],
            ),
            _section(
                "Move the research map",
                [
                    html.Div(
                        [
                            dcc.Input(
                                id="search-input",
                                type="text",
                                placeholder="Town, state; region; or coordinates",
                                debounce=False,
                                className="atlas-search-input",
                            ),
                            html.Button("Find", id="search-btn", n_clicks=0, className="atlas-search-button"),
                        ],
                        className="atlas-search-row",
                    ),
                    html.Div(id="search-results", className="atlas-search-results"),
                    html.P("This search moves the map. Use Explore a town for a town's rocks, fossils and historical context.", className="atlas-help"),
                ],
            ),
            _section(
                "Draw a study area",
                [
                    html.Div(
                        "Draw a circle, rectangle, or polygon to review U.S. records in that study area.",
                        className="atlas-help",
                    ),
                    html.Div(
                        "Draw tools are in the map’s top-right corner: circle, rectangle, polygon, edit, and delete.",
                        className="atlas-help",
                    ),
                    html.Label("Buffer around AOI", className="atlas-small-label"),
                    dcc.Slider(
                        id="buffer-km-slider",
                        min=0.25,
                        max=5.0,
                        step=0.25,
                        value=1.0,
                        marks={0.25: "0.25 km", 1: "1 km", 3: "3 km", 5: "5 km"},
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(
                        [
                            html.Button("Review Research Area", id="refresh-analysis-btn", n_clicks=0, className="atlas-primary-button"),
                            html.Button("Clear AOI", id="clear-aoi-btn", n_clicks=0, className="atlas-secondary-button"),
                        ],
                        className="atlas-button-row",
                    ),
                    html.Div(id="analysis-status", className="atlas-status-card"),
                    html.Div(id="analysis-metrics", className="atlas-status-card"),
                ],
                open=True,
                section_id="aoi-controls-section",
            ),
            _section(
                "Compare areas",
                [
                    html.Div("Load a local candidate JSON file with prior-survey and independent observations. Areas without enough evidence remain unranked.", className="atlas-help"),
                    dcc.Upload(
                        id="candidate-upload",
                        children=html.Button("Load Candidate JSON", className="atlas-secondary-button"),
                        accept=".json,application/json",
                        multiple=False,
                    ),
                    html.A("Download candidate template", href="/assets/candidate_template.json",
                           download="candidate_template.json", className="atlas-candidate-template-link"),
                    html.Div(id="candidate-upload-status", className="atlas-status-card"),
                ],
            ),
            _section(
                "Layers",
                [
                    dcc.Checklist(
                        id="visible-layers",
                        options=[
                            {"label": " AOI boundary", "value": "aoi"},
                            {"label": " Sites in AOI", "value": "known_sites"},
                            {"label": " Nearby documented sites", "value": "nearby_sites"},
                            {"label": " Paleo / fossil context", "value": "paleo_context"},
                            {"label": " Tribal boundaries", "value": "tribal_boundaries"},
                            {"label": " Native territories", "value": "native_territories"},
                        ],
                        value=["aoi", "known_sites"],
                        className="layer-checklist",
                        inputStyle={"marginRight": "6px"},
                        labelStyle={"display": "block", "padding": "4px 0", "fontSize": "12px", "color": TEXT_PRIMARY},
                    )
                ],
            ),
            _section(
                "Notes",
                [
                    html.Div(
                        "This app now queries only the selected local area. It does not preload national synthetic demo state.",
                        className="atlas-help",
                    ),
                    html.Div("The bundled records cannot estimate discovery probability or choose a dig location. Add independent evidence and permission review before fieldwork.", className="atlas-help atlas-help-warning"),
                ],
            ),
        ],
    )
    directory_title, directory_section, lead_title, lead_section, *map_sections = panel.children
    panel.children = [
        html.Div("Start with a published project or draw a local U.S. study area.", className="atlas-workflow-hint"),
        lead_title, lead_section, map_sections[2], directory_title, directory_section,
        *map_sections[3:],
    ]
    panel.children = [
        resident_controls(),
        inspection_controls(),
        fieldbook_controls(),
        html.Div(panel.children, id="research-controls", style={"display": "none"}),
    ]
    return panel


def _disclosure(title: str, child, *, section_id: str | None = None) -> html.Details:
    return html.Details(
        [html.Summary(title, className="atlas-panel-title"), child],
        className="atlas-panel-disclosure atlas-inspector-disclosure",
        **({"id": section_id} if section_id else {}),
    )


def build_brief_panel() -> html.Section:
    return html.Section(
        [
            html.Div("RESEARCH WORKFLOW", className="atlas-lead-eyebrow"),
            html.H2("Build a research brief", className="atlas-brief-heading"),
            html.P("Choose a published project or review a drawn study area. The brief keeps sources and unanswered questions together for a qualified team.", className="atlas-help"),
            dcc.RadioItems(
                id="brief-mode",
                options=[{"label": " Published project", "value": "project"}, {"label": " Drawn area", "value": "area"}],
                value="project",
                inline=True,
                className="atlas-brief-mode",
            ),
            html.Div(id="brief-step-guide", className="atlas-brief-steps"),
            html.Div(
                [
                    html.Label("Public area label", htmlFor="brief-area-label", className="atlas-small-label"),
                    dcc.Input(id="brief-area-label", type="text", maxLength=120,
                              placeholder="e.g. Santa Fe study envelope", className="atlas-search-input"),
                    html.Div("Avoid confidential site names or coordinates in an exported brief.", className="atlas-help"),
                ],
                id="brief-area-label-wrap",
            ),
            html.Label("Research question (optional)", htmlFor="brief-question", className="atlas-small-label"),
            dcc.Textarea(id="brief-question", maxLength=500,
                         placeholder="What would the next observation test?",
                         className="atlas-brief-question"),
            html.Div(id="brief-status", className="atlas-lead-count"),
            html.Button("Download source-linked brief", id="brief-download-button", n_clicks=0,
                        className="atlas-primary-button atlas-brief-download"),
            html.Details(
                [html.Summary("Preview brief and source links"), dcc.Markdown(id="brief-preview", className="atlas-brief-preview", link_target="_blank")],
                className="atlas-brief-preview-disclosure",
            ),
        ],
        className="atlas-brief-panel",
    )


def build_inspector_panel() -> html.Aside:
    panel = html.Aside(
        id="inspector-panel",
        style={**PANEL_STYLE, "width": "430px", "flexShrink": "0", "borderLeft": f"1px solid {BORDER}"},
        children=[
            build_brief_panel(),
            _disclosure("Selected fieldwork lead", html.Div(id="field-lead-detail", className="atlas-lead-detail")),
            _disclosure("Selected public record", html.Div(id="catalog-detail", className="atlas-lead-detail"), section_id="catalog-detail-section"),
            _disclosure("Local map review", html.Div(id="summary-panel", className="atlas-summary-panel"), section_id="local-review-section"),
            _disclosure("Compare your areas", html.Div(id="candidate-panel", className="atlas-summary-panel"), section_id="candidate-review-section"),
            _disclosure("Inspector", html.Div(id="inspector-content", className="atlas-inspector",
                                               children="Review an area, then click a map feature for record details."), section_id="map-inspector-section"),
            _disclosure("Ways to support research", html.Div(
                [
                    html.P("A contribution can fund discoveries and public knowledge. These project pages do not offer ownership of artifacts, equity, or a forecast financial return.", className="atlas-help"),
                    html.Div("Direct project contribution", className="atlas-funding-title"),
                    html.P("Argilos and Maya Research Program publish contribution routes. Ask for a defined research budget, reporting, curation, and open results.", className="atlas-help"),
                    html.Div("Restricted grant or sponsorship", className="atlas-funding-title"),
                    html.P("For field schools without a support page, ask the project director about a separately agreed grant. Participant fees buy training or fieldwork access.", className="atlas-help"),
                    html.Div("Crowdfunded project", className="atlas-funding-title"),
                    html.P(["A team can seek public backing through ", html.A("DigVentures ↗", href="https://digventures.com/crowdfunding/apply/", target="_blank", rel="noopener noreferrer"), ". Project availability and terms vary."], className="atlas-help"),
                    html.Div("Founder route", className="atlas-funding-title"),
                    html.P("Build a paid service for research teams, such as survey planning, records integration, or publication tools. Validate the need with archaeologists before claiming an investable return.", className="atlas-help"),
                ],
                className="atlas-funding-panel",
            )),
        ],
    )
    panel.children = [resident_report_panel(), inspection_report_panel(), fieldbook_inspector(), html.Div(panel.children, id="research-inspector", style={"display": "none"})]
    return panel


def build_stores() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="aoi-store", data=None),
            dcc.Store(id="analysis-store", data=None),
            dcc.Store(id="candidate-results-store", data=None),
            dcc.Store(id="candidate-file-store", data=None),
            dcc.Store(id="selected-map-feature-store", data=None),
            dcc.Store(id="selected-lead-store", data=_INITIAL_LEAD["id"] if _INITIAL_LEAD else None),
            dcc.Store(id="filtered-lead-store", data=[lead["id"] for lead in _CURRENT_LEADS]),
            dcc.Store(id="search-result-store", data=[]),
            dcc.Store(id="catalog-page-store", data=1),
            dcc.Store(id="catalog-selected-store", data=None),
            dcc.Download(id="brief-download"),
            dcc.Store(id="resident-report-store", data=None),
            dcc.Store(id="place-focus-request", data=None),
            dcc.Store(id="place-focus-complete", data=None),
            dcc.Store(id="resident-panel-position", data=None),
            dcc.Store(id='fieldbook-store',storage_type='local',data={'version':1,'entries':[]}),
            dcc.Download(id="resident-download"),
        ],
        style={"display": "none"},
    )
