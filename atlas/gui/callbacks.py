from __future__ import annotations

import json
import hashlib
import math
import re

from dash import ALL, Input, Output, State, callback, callback_context, html, no_update

from atlas.gui.data.fieldwork_leads import LEADS_BY_ID
from atlas.gui.data.institution_locations import CURATED_INSTITUTION_LOCATIONS
from atlas.gui.data.jurisdiction_rules import JURISDICTION_RULES
from atlas.gui.data.lead_catalog import CHECKED_ON, matching_leads, source_is_stale
from atlas.gui.data.lead_context import LEAD_CONTEXT
from atlas.gui.data.public_catalog import SOURCE_NAMES, get_record, overview, search_records
from atlas.gui.data.search_index import get_search_index
from core.aoi_analysis import AOIAnalysisEngine, EMPTY_FC, geometry_from_geojson
from core.discovery_planner import rank_candidates
from core.research_brief import area_brief, project_brief

ENGINE = AOIAnalysisEngine()


def _string_list(value):
    return isinstance(value, list) and len(value) <= 100 and all(isinstance(item, str) for item in value)


def _render_summary(analysis, *, counts=(), strings=(), lists=()):
    """Browser stores are user input; validate only fields this renderer uses."""
    if not isinstance(analysis, dict) or not isinstance(analysis.get("summary"), dict):
        return None
    summary = analysis["summary"]
    if any(isinstance(summary.get(key), bool) or not isinstance(summary.get(key), int)
           or not 0 <= summary[key] <= 10_000_000 for key in counts):
        return None
    if any(not isinstance(summary.get(key), str) for key in strings):
        return None
    if any(not _string_list(summary.get(key)) for key in lists):
        return None
    return summary


def _feature_data(value):
    return (isinstance(value, dict) and value.get("type") == "Feature"
            and isinstance(value.get("geometry"), dict)
            and value["geometry"].get("type") in {"Point", "Polygon", "MultiPolygon"}
            and isinstance(value["geometry"].get("coordinates"), (list, tuple))
            and isinstance(value.get("properties"), dict))


def _collection_data(value):
    return (isinstance(value, dict) and value.get("type") == "FeatureCollection"
            and isinstance(value.get("features"), list) and len(value["features"]) <= 1_000
            and all(_feature_data(feature) for feature in value["features"]))


def _finite_render_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _candidate_renderable(row):
    if not isinstance(row, dict):
        return False
    if any(not isinstance(row.get(key), str) for key in ("name", "permission_status", "next_step")):
        return False
    rank = row.get("research_rank")
    score = row.get("priority_index")
    if rank is not None and (isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 25):
        return False
    if score is not None and (not _finite_render_number(score) or not 0 <= score <= 100):
        return False
    hints, signals = row.get("possible_find_classes"), row.get("independent_signals")
    if not isinstance(hints, list) or len(hints) > 100 or any(
        not isinstance(item, dict) or not isinstance(item.get("class"), str) for item in hints
    ):
        return False
    if not isinstance(signals, list) or len(signals) > 100 or any(
        not isinstance(item, dict) or not isinstance(item.get("kind"), str) or not isinstance(item.get("source"), str)
        for item in signals
    ):
        return False
    return True


def _aoi_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _brief_area_is_current(analysis, aoi_data):
    return (isinstance(analysis, dict) and isinstance(aoi_data, dict)
            and isinstance(aoi_data.get("features"), list)
            and aoi_data.get("type") == "FeatureCollection"
            and analysis.get("reviewed_aoi_hash") == _aoi_hash(aoi_data))


NATIONAL_RULE_STARTERS = {
    "Portugal": ("portugal", "Archaeological work requires authorization and landowner consent; confirm the competent regional service."),
    "Greece": ("greece", "Confirm the proposed archaeological work with the competent Ephorate and Ministry of Culture."),
    "Belize": ("belize", "Field research needs an Institute of Archaeology permit covering the site or study area."),
    "Austria": ("austria", "Excavation and systematic prospection require Federal Monuments Office authorization."),
    "Peru": ("peru", "Survey and excavation research require prior Ministry of Culture authorization."),
    "Oman": ("oman", "Confirm archaeological fieldwork authorization with the competent Omani office; Royal Decree 62/2026 assigns authority by remit across the heritage and culture ministries."),
}


@callback(
    Output("brief-step-guide", "children"),
    Output("brief-status", "children"),
    Output("brief-preview", "children"),
    Output("brief-area-label-wrap", "style"),
    Output("brief-download-button", "disabled"),
    Input("brief-mode", "value"),
    Input("selected-lead-store", "data"),
    Input("analysis-store", "data"),
    Input("aoi-store", "data"),
    Input("brief-area-label", "value"),
    Input("brief-question", "value"),
)
def render_research_brief(mode, lead_id, analysis, aoi_data, area_label, question):
    if mode == "area":
        steps = [html.Div(step) for step in (
            "1. Draw a local U.S. area on the map.",
            "2. Run Review Research Area in the left panel.",
            "3. Inspect gaps, then export a brief for a qualified team.",
        )]
        if not _brief_area_is_current(analysis, aoi_data):
            return steps, "Review a drawn area before downloading.", "No local area has been reviewed yet.", {}, True
        try:
            title, markdown = area_brief(analysis, area_label, question)
        except ValueError as exc:
            return steps, str(exc), "The brief is unavailable until the inputs are corrected.", {}, True
        status = f"Ready: {title}. Coordinates are omitted; source dates and permission gaps are explicit."
        return steps, status, markdown, {}, False
    steps = [html.Div(step) for step in (
        "1. Select a published project in the left panel.",
        "2. Review its source, role, and jurisdiction links.",
        "3. Export a brief and confirm open questions with the project team.",
    )]
    if mode != "project" or not isinstance(lead_id, str) or lead_id not in LEADS_BY_ID:
        return steps, "Choose a current project before downloading.", "No project selected.", {"display": "none"}, True
    try:
        title, markdown = project_brief(lead_id, question)
    except ValueError as exc:
        return steps, str(exc), "The brief is unavailable until the inputs are corrected.", {"display": "none"}, True
    status = f"Ready: {title}. This is a research handoff, not a permit or discovery forecast."
    return steps, status, markdown, {"display": "none"}, False


@callback(
    Output("brief-download", "data"),
    Input("brief-download-button", "n_clicks"),
    State("brief-mode", "value"), State("selected-lead-store", "data"),
    State("analysis-store", "data"), State("aoi-store", "data"),
    State("brief-area-label", "value"), State("brief-question", "value"),
    prevent_initial_call=True,
)
def download_research_brief(_clicks, mode, lead_id, analysis, aoi_data, area_label, question):
    try:
        if mode == "area":
            if not _brief_area_is_current(analysis, aoi_data):
                return no_update
            title, markdown = area_brief(analysis, area_label, question)
        elif mode == "project" and isinstance(lead_id, str) and lead_id in LEADS_BY_ID:
            title, markdown = project_brief(lead_id, question)
        else:
            return no_update
    except ValueError:
        return no_update
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:70] or "study-area"
    return {"content": markdown, "filename": f"clovis-research-brief-{slug}.md", "type": "text/markdown"}


@callback(Output("aoi-controls-section", "open"), Input("brief-mode", "value"))
def reveal_area_controls(mode):
    return mode == "area"


@callback(Output("catalog-detail-section", "open"), Input("catalog-selected-store", "data"))
def reveal_selected_record(record_id):
    return bool(record_id)


@callback(Output("local-review-section", "open"), Input("analysis-store", "data"))
def reveal_local_review(analysis):
    return bool(analysis)


@callback(Output("candidate-review-section", "open"), Input("candidate-results-store", "data"))
def reveal_candidate_comparison(results):
    return bool(results)


@callback(Output("map-inspector-section", "open"),
          Input("selected-map-feature-store", "data"), Input("analysis-store", "data"))
def reveal_map_inspector(selection, analysis):
    return bool(selection and analysis)


@callback(
    Output("catalog-page-store", "data"),
    Input("catalog-kind", "value"),
    Input("catalog-search", "value"),
    Input("catalog-source", "value"),
    Input("catalog-country", "value"),
    Input("catalog-prev", "n_clicks"),
    Input("catalog-next", "n_clicks"),
    State("catalog-page-store", "data"),
)
def change_catalog_page(_kind, _query, _source, _country, _prev, _next, page):
    trigger = callback_context.triggered_id
    if trigger == "catalog-prev":
        return max(1, int(page or 1) - 1)
    if trigger == "catalog-next":
        return int(page or 1) + 1
    return 1


@callback(
    Output("catalog-results", "children"),
    Output("catalog-status", "children"),
    Output("catalog-page-label", "children"),
    Output("catalog-prev", "disabled"),
    Output("catalog-next", "disabled"),
    Input("catalog-kind", "value"),
    Input("catalog-search", "value"),
    Input("catalog-source", "value"),
    Input("catalog-country", "value"),
    Input("catalog-page-store", "data"),
)
def render_catalog(kind, query, source, country, requested_page):
    if not overview()["built_on"]:
        return [html.Div("Run python3 tools/build_public_catalog.py to build the directory.", className="atlas-empty")], "No catalogue snapshot", "", True, True
    rows, total, page = search_records(kind or "site", query or "", source or "all", country or "all", requested_page or 1)
    cards = [
        html.Button([
            html.Span(row["name"], className="atlas-lead-name"),
            html.Span(" · ".join(part for part in (row["country"], row["region"]) if part) or "Location not recorded", className="atlas-lead-region"),
            html.Span(f"{SOURCE_NAMES.get(row['source_key'], row['source_key'])} · {row['record_type']}", className="atlas-lead-signal"),
        ], id={"type": "catalog-record", "index": row["id"]}, n_clicks=0, className="atlas-lead-button")
        for row in rows
    ]
    if not cards:
        cards = [html.Div("No records match these filters.", className="atlas-empty")]
    last_page = max(1, (total + 19) // 20)
    return cards, f"{total:,} matching {kind or 'site'} record(s) · snapshot {overview()['built_on']}", f"{page:,} / {last_page:,}", page <= 1, page >= last_page


@callback(
    Output("catalog-selected-store", "data"),
    Output("selected-lead-store", "data", allow_duplicate=True),
    Output("main-map", "viewport", allow_duplicate=True),
    Input({"type": "catalog-record", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_catalog_record(_clicks):
    trigger = callback_context.triggered_id
    if not any(_clicks or []) or not isinstance(trigger, dict):
        return no_update, no_update, no_update
    row = get_record(trigger.get("index"))
    if not row:
        return no_update, no_update, no_update
    lead = LEADS_BY_ID.get(row["source_id"]) if row["source_key"] == "curated_projects" and row["kind"] == "site" else None
    if row["source_key"] == "curated_projects" and row["kind"] == "institution":
        related_ids = [
            lead_id for lead_id, context in LEAD_CONTEXT.items()
            for institution in context["institutions"]
            if institution["name"].casefold() == row["name"].casefold()
        ]
        if len(related_ids) == 1:
            lead = LEADS_BY_ID[related_ids[0]]
    if lead:
        return row["id"], lead["id"], {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"}
    return row["id"], None, no_update


@callback(
    Output("selected-lead-store", "data", allow_duplicate=True),
    Output("main-map", "viewport", allow_duplicate=True),
    Input({"type": "related-lead", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_related_lead(_clicks):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(_clicks or []):
        return no_update, no_update
    lead = LEADS_BY_ID.get(trigger.get("index"))
    if not lead:
        return no_update, no_update
    return lead["id"], {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"}


@callback(
    Output("catalog-selected-store", "data", allow_duplicate=True),
    Input("catalog-kind", "value"),
    Input("catalog-search", "value"),
    Input("catalog-source", "value"),
    Input("catalog-country", "value"),
    prevent_initial_call=True,
)
def clear_catalog_selection(_kind, _query, _source, _country):
    return None


@callback(
    Output({"type": "catalog-record", "index": ALL}, "className"),
    Input("catalog-selected-store", "data"),
    Input({"type": "catalog-record", "index": ALL}, "id"),
)
def highlight_catalog_record(selected_id, button_ids):
    return [
        "atlas-lead-button atlas-lead-button-selected" if row_id["index"] == selected_id else "atlas-lead-button"
        for row_id in button_ids
    ]


@callback(Output("catalog-detail", "children"), Input("catalog-selected-store", "data"))
def render_catalog_record(record_id):
    row = get_record(record_id)
    if not row:
        return html.Div("Select a site or institution in the public directory.", className="atlas-empty")
    location = " · ".join(part for part in (row["country"], row["region"]) if part) or "Not stated in this record"
    status = (
        "This source lists an archaeological place. It does not establish an available dig area, discovery odds, a partner, or excavation permission."
        if row["kind"] == "site" else
        "This is a possible institutional contact. The listing alone does not establish capacity, interest, or a partnership."
    )
    if row["source_key"] == "curated_projects" and row["kind"] == "site":
        status = "This published fieldwork area is linked to the project below. Exact excavation units and current permission still need confirmation."
    elif row["source_key"] == "curated_projects":
        status = "Named role on a researched project page. Confirm the organization's present role and interest before outreach."
    starter = NATIONAL_RULE_STARTERS.get(row["country"]) if row["kind"] == "site" else None
    legal = JURISDICTION_RULES[starter[0]] if starter else None
    office_location = (
        CURATED_INSTITUTION_LOCATIONS.get(row["name"])
        if row["kind"] == "institution" and row["source_key"] == "curated_projects"
        else None
    )
    related = [
        (LEADS_BY_ID[lead_id], institution["relationship"])
        for lead_id, context in LEAD_CONTEXT.items()
        for institution in context["institutions"]
        if row["kind"] == "institution" and row["source_key"] == "curated_projects"
        and institution["name"].casefold() == row["name"].casefold()
    ]
    return [
        html.Div("PUBLIC SOURCE RECORD", className="atlas-lead-eyebrow"),
        html.H2(row["name"], className="atlas-lead-heading"),
        html.Div(row["record_type"], className="atlas-lead-meta"),
        html.Div([html.Div("Broad location", className="atlas-lead-label"), html.Div(location, className="atlas-lead-value")], className="atlas-lead-detail-row"),
        html.Div([html.Div("Source and identifier", className="atlas-lead-label"), html.Div(f"{SOURCE_NAMES.get(row['source_key'], row['source_key'])} · {row['source_id']}", className="atlas-lead-value")], className="atlas-lead-detail-row"),
        html.Div([html.Div("Source note", className="atlas-lead-label"), html.Div(row["source_note"], className="atlas-lead-value")], className="atlas-lead-detail-row"),
        html.Div([
            html.Div("Researched project connections", className="atlas-lead-label"),
            html.Ul([
                html.Li([
                    html.Button("Open " + lead["name"] + " in Clovis", id={"type": "related-lead", "index": lead["id"]},
                                n_clicks=0, className="atlas-text-button"),
                    html.Span(" · " + relationship + " · "),
                    html.A("Project source ↗", href=lead["source_url"], target="_blank", rel="noopener noreferrer"),
                ])
                for lead, relationship in related
            ], className="atlas-institution-list"),
        ], className="atlas-lead-detail-row") if related else None,
        html.P(status, className="atlas-lead-unknown"),
        html.P(
            "Read the linked project's jurisdiction check below, then confirm land access and current permission with its team."
            if row["source_key"] == "curated_projects" and row["kind"] == "site" else
            "Check the competent local heritage authority, landowner, and relevant communities before planning fieldwork. No site-specific permission review is attached to this bulk record."
            if row["kind"] == "site" else
            "Confirm the organization's current role directly before proposing support.",
            className="atlas-help",
        ),
        html.Div([
            html.Div("NATIONAL RULE STARTING POINT · SITE STATUS UNCHECKED", className="atlas-regulatory-heading"),
            html.P(starter[1]),
            html.A("Official national rule or guidance ↗", href=legal["source_url"], target="_blank", rel="noopener noreferrer"),
        ], className="atlas-regulatory-card") if legal else None,
        html.A("Open source dataset ↗" if row["source_key"] == "nrhp" else "Open source page ↗",
               href=row["source_url"], target="_blank", rel="noopener noreferrer", className="atlas-catalog-source-link"),
        html.Span(" · ") if office_location else None,
        html.A("Office location source ↗", href=office_location[1], target="_blank", rel="noopener noreferrer",
               className="atlas-catalog-source-link") if office_location else None,
    ]


def _lookup_search_matches(query: str) -> list[tuple[str, dict]]:
    from core.us_places import search_towns
    if not isinstance(query, str) or len(query) > 80:
        return []
    q = (query or "").strip().lower()
    if not q:
        return []
    index = get_search_index()
    if q in index:
        return [(q, index[q])]
    towns = search_towns(query)
    matches = [(row['key'], {key: value for key, value in row.items() if key != 'key'}) for row in towns]
    matches += [(name, info) for name, info in index.items() if q in name]
    if not towns:
        matches.sort(key=lambda row: (abs(len(row[0]) - len(q)), row[0]))
    return matches[:8]


def _feature_card(title: str, items: list[str], tone: str = "normal") -> html.Div:
    class_name = "atlas-summary-block atlas-summary-block-warning" if tone == "warning" else "atlas-summary-block"
    return html.Div(
        [html.Div(title, className="atlas-summary-title")] + [html.Div(item, className="atlas-summary-line") for item in items],
        className=class_name,
    )


@callback(
    Output("field-lead-list", "children"),
    Output("lead-results-status", "children"),
    Output("filtered-lead-store", "data"),
    Input("lead-goal", "value"),
    Input("lead-region-filter", "value"),
    Input("lead-period-filter", "value"),
    Input("lead-support-filter", "value"),
    Input("lead-search", "value"),
)
def render_lead_list(goal, region, period, support_values, query):
    rows = matching_leads(
        goal=goal or "evidence",
        region=region or "all",
        period=period or "all",
        support="published" if "published" in (support_values or []) else "all",
        query=query or "",
    )
    cards = [
        html.Button(
            [
                html.Span(f"{index:02d}  {lead['name']}", className="atlas-lead-name"),
                html.Span(LEAD_CONTEXT[lead["id"]]["site_area"], className="atlas-lead-site"),
                html.Span(f"{lead['evidence_label']} · {'Support page' if lead['support_route'] == 'published' else 'Director inquiry'}", className="atlas-lead-signal"),
                html.Span(lead["region"], className="atlas-lead-region"),
                html.Span(lead["season"], className="atlas-lead-season"),
            ],
            id={"type": "field-lead-button", "index": lead["id"]},
            className="atlas-lead-button",
            n_clicks=0,
        )
        for index, lead in enumerate(rows, 1)
    ]
    if not cards:
        cards = [html.Div("No current leads match these filters. Widen the filters or check the source pages for new seasons.", className="atlas-empty")]
    status = f"{len(rows)} current lead(s) · public sources checked {CHECKED_ON.day} {CHECKED_ON:%B %Y}"
    if source_is_stale():
        status += " · Source check is over 90 days old; verify before acting"
    return cards, status, [lead["id"] for lead in rows]


@callback(
    Output("selected-lead-store", "data"),
    Output("main-map", "viewport", allow_duplicate=True),
    Output("catalog-selected-store", "data", allow_duplicate=True),
    Input({"type": "field-lead-button", "index": ALL}, "n_clicks"),
    State({"type": "field-lead-button", "index": ALL}, "id"),
    prevent_initial_call=True,
)
def select_field_lead(clicks, button_ids):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict):
        return no_update, no_update, no_update
    clicked = next((count for count, button_id in zip(clicks, button_ids) if button_id["index"] == trigger.get("index")), 0)
    if not clicked:
        return no_update, no_update, no_update
    lead = LEADS_BY_ID.get(trigger.get("index"))
    if not lead:
        return no_update, no_update, no_update
    return lead["id"], {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"}, None


@callback(
    Output({"type": "field-lead-button", "index": ALL}, "className"),
    Input("selected-lead-store", "data"),
    Input({"type": "field-lead-button", "index": ALL}, "id"),
)
def highlight_field_lead(selected_id, button_ids):
    return [
        "atlas-lead-button atlas-lead-button-selected" if button_id["index"] == selected_id else "atlas-lead-button"
        for button_id in button_ids
    ]


@callback(
    Output("selected-lead-store", "data", allow_duplicate=True),
    Output("main-map", "viewport", allow_duplicate=True),
    Output("catalog-selected-store", "data", allow_duplicate=True),
    Input("filtered-lead-store", "data"),
    State("selected-lead-store", "data"),
    prevent_initial_call=True,
)
def select_first_visible_lead(visible_ids, selected_id):
    if not visible_ids:
        return (None, no_update, None) if selected_id is not None else (no_update, no_update, no_update)
    if selected_id in visible_ids:
        return no_update, no_update, no_update
    lead = LEADS_BY_ID[visible_ids[0]]
    return lead["id"], {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"}, None


@callback(
    Output("field-lead-detail", "children"),
    Input("selected-lead-store", "data"),
)
def render_field_lead(selected_id):
    lead = LEADS_BY_ID.get(selected_id)
    if not lead:
        return html.Div("No current fieldwork lead is selected.", className="atlas-empty")
    context = LEAD_CONTEXT[lead["id"]]
    legal = JURISDICTION_RULES[context["jurisdiction_key"]]

    def row(label, value):
        return html.Div(
            [html.Div(label, className="atlas-lead-label"), html.Div(value, className="atlas-lead-value")],
            className="atlas-lead-detail-row",
        )

    return [
        html.Div("SOURCED RESEARCH PROSPECT", className="atlas-lead-eyebrow"),
        html.H2(lead["name"], className="atlas-lead-heading"),
        html.Div(f"{lead['region']}  ·  {lead['season']}", className="atlas-lead-meta"),
        html.P(lead["why"], className="atlas-lead-thesis"),
        row("Public site or study area", context["site_area"]),
        row("Site plan status", context["site_note"]),
        row("Prior evidence", lead["evidence_label"]),
        row("Already documented", lead["evidence"]),
        row("Planned fieldwork", lead["planned"]),
        row("What further work might document", lead["finding"]),
        row("Route to support", lead["support_note"]),
        html.Div(
            [
                html.Div("Institutional entry points", className="atlas-lead-label"),
                html.Ul(
                    [
                        html.Li(
                            [
                                html.Span(institution["name"] + " · " + institution["relationship"] + " · "),
                                html.A("Role source ↗", href=institution["source_url"], target="_blank", rel="noopener noreferrer"),
                                *([html.Span(" · "), html.A("Institution website ↗", href=institution["institution_url"], target="_blank", rel="noopener noreferrer")]
                                  if institution.get("institution_url") else []),
                            ]
                        )
                        for institution in context["institutions"]
                    ],
                    className="atlas-institution-list",
                ),
            ],
            className="atlas-lead-detail-row",
        ),
        row("First partner conversation", context["first_contact"]),
        html.Div(
            [
                html.Div("LOCAL HERITAGE RULES · PERMIT STATUS UNVERIFIED", className="atlas-regulatory-heading"),
                html.Div(legal["jurisdiction"], className="atlas-regulatory-jurisdiction"),
                html.P([html.Strong("Authority: "), legal["authority"]]),
                html.P(legal["rule"]),
                html.P([html.Strong("Before funding fieldwork: "), legal["verify"]]),
                html.Div(
                    [
                        html.A("Official rule or guidance ↗", href=legal["source_url"], target="_blank", rel="noopener noreferrer"),
                        html.A("Additional authority source ↗", href=legal["additional_url"], target="_blank", rel="noopener noreferrer"),
                    ] if legal.get("additional_url") else [
                        html.A("Official rule or guidance ↗", href=legal["source_url"], target="_blank", rel="noopener noreferrer")
                    ],
                    className="atlas-regulatory-links",
                ),
            ],
            className="atlas-regulatory-card",
        ),
        row("First funding conversation", lead["next_step"]),
        html.Div(lead["open_question"], className="atlas-lead-unknown"),
        html.Div(
            [html.A("Project source ↗", href=lead["source_url"], target="_blank", rel="noopener noreferrer")]
            + ([html.A("Fieldwork listing ↗", href=lead["listing_url"], target="_blank", rel="noopener noreferrer")]
               if lead["listing_url"] != lead["source_url"] else [])
            + ([html.A("Support route ↗", href=lead["support_url"], target="_blank", rel="noopener noreferrer")]
               if lead.get("support_url") else []),
            className="atlas-lead-links",
        ),
        html.P(
                f"Sources checked {CHECKED_ON.day} {CHECKED_ON:%B %Y}. "
            + ("Source check is over 90 days old; recheck before acting. " if source_is_stale() else "")
            + "These are partnership leads, not ranked dig sites or estimated discovery probabilities. The map shows broad regional context only.",
            className="atlas-lead-disclaimer",
        ),
    ]


@callback(
    Output("main-map", "viewport", allow_duplicate=True),
    Output("search-results", "children"),
    Output("search-result-store", "data"),
    Input("search-btn", "n_clicks"),
    Input("search-input", "n_submit"),
    State("search-input", "value"),
    prevent_initial_call=True,
)
def submit_search(_clicks, _submit, query):
    if not isinstance(query, str) or len(query) > 80:
        return no_update, "Enter a town and state, a region, or coordinates (up to 80 characters).", []
    query = query.strip()
    if not query:
        return no_update, "Enter a place name or coordinates.", []
    parts = query.replace(",", " ").split()
    if len(parts) == 2:
        try:
            lat = float(parts[0])
            lon = float(parts[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {"center": [lat, lon], "zoom": 13, "transition": "setView"}, "Coordinate match loaded.", []
        except ValueError:
            pass
    matches = _lookup_search_matches(query)
    if not matches:
        return no_update, f'No local search match for "{query}".', []
    if len(matches) == 1:
        key, info = matches[0]
        return {"center": info["center"], "zoom": info["zoom"], "transition": "setView"}, f"Loaded {info['label']}.", [{"key": key, **info}]
    buttons = [
        html.Button(info["label"], id={"type": "search-result", "index": idx}, className="atlas-result-button")
        for idx, (_, info) in enumerate(matches)
    ]
    return no_update, buttons, [{"key": key, **info} for key, info in matches]


@callback(
    Output("main-map", "viewport", allow_duplicate=True),
    Output("search-results", "children", allow_duplicate=True),
    Input({"type": "search-result", "index": ALL}, "n_clicks"),
    State("search-result-store", "data"),
    prevent_initial_call=True,
)
def click_search_result(_clicks, results):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not results or not any(_clicks or []):
        return no_update, no_update
    info = results[trigger["index"]]
    return {"center": info["center"], "zoom": info["zoom"], "transition": "setView"}, f"Loaded {info['label']}."


@callback(Output("header-region", "children"), Input("selected-lead-store", "data"),
          Input("workflow-mode", "value"), Input("resident-place", "value"), Input("resident-state", "value"))
def show_selected_region(selected_id, mode="research", geoid=None, state=None):
    if mode == 'inspect': return 'Inspect a find · your observations'
    if mode == 'notebook': return 'Your saved investigations'
    if mode != "research":
        from core.us_places import get_place
        place = get_place(geoid, state)
        return f"{place['name']}, {place['state']} · town context" if place else "No town selected"
    lead = LEADS_BY_ID.get(selected_id) if isinstance(selected_id, str) else None
    return f"{lead['name']} · fieldwork lead" if lead else "No current fieldwork lead"


@callback(
    Output("aoi-store", "data"),
    Output("analysis-status", "children"),
    Input("draw-control", "geojson"),
)
def sync_aoi_store(geojson):
    try:
        geometry = geometry_from_geojson(geojson)
    except (TypeError, ValueError, OverflowError) as exc:
        return None, f"Could not capture this study area: {exc}"
    if geometry is None:
        return None, "No study area drawn yet."
    features = geojson["features"]
    return geojson, f"{len(features)} study-area shape(s) captured. Review to query only that area."


@callback(
    Output("analysis-store", "data", allow_duplicate=True),
    Input("aoi-store", "data"),
    prevent_initial_call=True,
)
def invalidate_analysis_for_new_area(_aoi):
    return None


@callback(
    Output("draw-control", "geojson", allow_duplicate=True),
    Output("aoi-store", "data", allow_duplicate=True),
    Output("analysis-store", "data", allow_duplicate=True),
    Output("analysis-status", "children", allow_duplicate=True),
    Input("clear-aoi-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_aoi(_clicks):
    return {"type": "FeatureCollection", "features": []}, None, None, "Study area cleared. Draw a new area to review records."


@callback(
    Output("analysis-store", "data"),
    Output("analysis-status", "children", allow_duplicate=True),
    Input("refresh-analysis-btn", "n_clicks"),
    State("aoi-store", "data"),
    State("buffer-km-slider", "value"),
    prevent_initial_call=True,
)
def run_local_analysis(_clicks, aoi_data, buffer_km):
    try:
        buffer_distance = float(buffer_km if buffer_km is not None else 1.0)
        if not math.isfinite(buffer_distance) or not 0 <= buffer_distance <= 5:
            raise ValueError("Use a review buffer between 0 and 5 km.")
        aoi_geom = geometry_from_geojson(aoi_data)
    except (TypeError, ValueError, OverflowError) as exc:
        return None, f"Could not review this area: {exc}"
    if aoi_geom is None:
        return no_update, "Draw a circle, rectangle, or polygon before reviewing local records."
    min_lon, min_lat, max_lon, max_lat = aoi_geom.bounds
    if max_lat - min_lat > 2 or max_lon - min_lon > 3:
        return no_update, "Study area is too large for local review. Zoom in and draw a smaller area."
    center = aoi_geom.centroid
    if not (-170 <= center.x <= -66 and 18 <= center.y <= 72):
        return no_update, "The bundled spatial records are U.S.-focused. Use the project sources for this region; no local map review is available here."
    analysis = ENGINE.analyze(
        aoi_geojson=aoi_data,
        viewport_bounds=None,
        buffer_km=buffer_distance,
    )
    analysis["reviewed_aoi_hash"] = _aoi_hash(aoi_data)
    summary = analysis["summary"]
    status = (
        f"Bundled index: {summary['aoi_site_count']} record(s) in the study area, "
        f"{summary['buffer_site_count']} nearby. Coverage is incomplete; zero records does not mean no archaeology."
    )
    return analysis, status


@callback(
    Output("analysis-metrics", "children"),
    Input("analysis-store", "data"),
)
def render_metrics(analysis):
    if not analysis:
        return "No local analysis loaded yet."
    summary = _render_summary(analysis, counts=("aoi_site_count", "buffer_site_count", "independent_signal_count",
                                                "paleo_count", "tribal_count", "native_count"))
    if summary is None:
        return "Invalid area review. Run Review Research Area again."
    return (
        f"Indexed area records: {summary['aoi_site_count']} | Nearby records: {summary['buffer_site_count']} | "
        f"Independent discovery signals: {summary['independent_signal_count']} | "
        f"Paleo context: {summary['paleo_count']} | Tribal: {summary['tribal_count']} | Native: {summary['native_count']}"
    )


@callback(
    Output("base-tile-layer", "url"),
    Output("base-tile-layer", "attribution"),
    Output("base-tile-layer", "maxNativeZoom"),
    Input("basemap-selector", "value"),
)
def switch_basemap(value):
    from atlas.gui.styles import TILE_ATTRIBUTIONS, TILE_URLS

    key = value or "terrain"
    key = key if isinstance(key, str) and key in TILE_URLS else "terrain"
    return TILE_URLS[key], TILE_ATTRIBUTIONS[key], 17 if key == "topographic" else 19


@callback(
    Output("aoi-layer", "data"),
    Output("buffer-layer", "data"),
    Output("scored-cells-layer", "data"),
    Output("hotspot-markers-layer", "data"),
    Output("known-sites-layer", "data"),
    Output("nearby-sites-layer", "data"),
    Output("paleo-context-layer", "data"),
    Output("tribal-boundaries-layer", "data"),
    Output("native-territories-layer", "data"),
    Input("analysis-store", "data"),
    Input("visible-layers", "value"),
)
def render_layers(analysis, visible_layers):
    if not analysis:
        return (EMPTY_FC,) * 9
    if not isinstance(visible_layers, list) or not all(isinstance(item, str) for item in visible_layers):
        return (EMPTY_FC,) * 9
    if not isinstance(analysis, dict) or not isinstance(analysis.get("layers"), dict):
        return (EMPTY_FC,) * 9
    layers = analysis["layers"]
    if not _feature_data(analysis.get("aoi")) or not _feature_data(analysis.get("buffer")) or any(
        not _collection_data(layers.get(key)) for key in ("scored_cells", "hotspots", "known_sites", "nearby_sites",
                                                        "paleo_context", "tribal_boundaries", "native_territories")
    ):
        return (EMPTY_FC,) * 9
    visible = set(visible_layers)
    aoi = {"type": "FeatureCollection", "features": [analysis["aoi"]]} if "aoi" in visible else EMPTY_FC
    buffer = {"type": "FeatureCollection", "features": [analysis["buffer"]]} if "aoi" in visible else EMPTY_FC
    return (
        aoi,
        buffer,
        layers["scored_cells"] if "scored_cells" in visible else EMPTY_FC,
        layers["hotspots"] if "hotspots" in visible else EMPTY_FC,
        layers["known_sites"] if "known_sites" in visible else EMPTY_FC,
        layers["nearby_sites"] if "nearby_sites" in visible else EMPTY_FC,
        layers["paleo_context"] if "paleo_context" in visible else EMPTY_FC,
        layers["tribal_boundaries"] if "tribal_boundaries" in visible else EMPTY_FC,
        layers["native_territories"] if "native_territories" in visible else EMPTY_FC,
    )


@callback(
    Output("summary-panel", "children"),
    Input("analysis-store", "data"),
)
def render_summary_panel(analysis):
    if not analysis:
        return html.Div("Draw a study area and review its documented context and research gaps.", className="atlas-empty")
    summary = _render_summary(analysis, counts=("independent_signal_count",),
                              strings=("finds_note", "next_step", "depth_context", "legal_caution"),
                              lists=("period_mix", "possible_find_classes", "evidence", "data_gaps"))
    if summary is None:
        return html.Div("Invalid area review. Run Review Research Area again.", className="atlas-empty")
    return html.Div(
        [
            _feature_card(
                "Coverage warning",
                ["This index is incomplete. A blank map or zero count is not a negative survey result."],
                tone="warning",
            ),
            _feature_card(
                "Research readiness",
                [
                    "No ranked dig target from current local data.",
                    f"Independent signals: {summary['independent_signal_count']}",
                    f"Period mix: {', '.join(summary['period_mix'])}",
                ],
            ),
            _feature_card(
                "Possible context in documented records",
                [item.title() for item in summary["possible_find_classes"]] or ["Unknown"],
            ),
            _feature_card("Interpretation", [summary["finds_note"]]),
            _feature_card("Evidence", summary["evidence"]),
            _feature_card("Next step", [summary["next_step"]]),
            _feature_card("Missing evidence", summary["data_gaps"]),
            _feature_card("Depth / Context", [summary["depth_context"]]),
            _feature_card("Legal Caution", [summary["legal_caution"]], tone="warning"),
        ]
    )


@callback(
    Output("candidate-results-store", "data"),
    Output("candidate-upload-status", "children"),
    Input("candidate-file-store", "data"),
    prevent_initial_call=True,
)
def load_candidate_areas(file_data):
    if not file_data:
        return None, "Choose a candidate JSON file."
    if not isinstance(file_data, dict):
        return None, "Candidate upload must contain a JSON file."
    filename = file_data.get("filename") or "candidate file"
    if file_data.get("error"):
        return None, f"Could not load {filename}: {file_data['error']}"
    contents = file_data.get("text") or ""
    if not isinstance(contents, str):
        return None, "Candidate file must contain JSON text."
    if len(contents.encode("utf-8")) > 1_000_000:
        return None, "Candidate file is too large; use at most 1 MB of JSON."
    try:
        document = json.loads(contents)
        candidates = document.get("candidates") if isinstance(document, dict) else document
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= 25:
            raise ValueError("Provide 1 to 25 candidate areas")
        results = rank_candidates(candidates)
    except (json.JSONDecodeError, TypeError, ValueError, RecursionError, OverflowError) as exc:
        return None, f"Could not load {filename or 'candidate file'}: {exc}"
    ranked = sum(row["research_rank"] is not None for row in results)
    noun = "area" if len(results) == 1 else "areas"
    verb = "has" if ranked == 1 else "have"
    return results, f"Loaded {len(results)} {noun} from {filename}; {ranked} {verb} enough user-supplied evidence for research ranking."


@callback(
    Output("candidate-panel", "children"),
    Input("candidate-results-store", "data"),
)
def render_candidate_areas(results):
    if not results:
        return html.Div("Load candidate areas to compare research follow-up priorities.", className="atlas-empty")
    if not isinstance(results, list) or len(results) > 25 or not all(_candidate_renderable(row) for row in results):
        return html.Div("Invalid candidate comparison. Load the candidate JSON file again.", className="atlas-empty")
    cards = []
    for row in results:
        rank = f"#{row['research_rank']}" if row["research_rank"] else "Unranked"
        score = (f"Research index {row['priority_index']:.1f}/100 · user-supplied and unverified; not a discovery probability"
                 if row["priority_index"] is not None else "Insufficient independent evidence")
        hints = ", ".join(item["class"] for item in row["possible_find_classes"]) or "Find class unknown"
        signals = ", ".join(f"{item['kind'].replace('_', ' ')} ({item['source']})" for item in row["independent_signals"]) or "None supplied"
        cards.append(_feature_card(
            f"{rank} · {row['name']}",
            [score, f"User-supplied inputs: {signals}",
             f"User-reported permission: {row['permission_status']} (unverified)",
             f"Record-text context hint: {hints}", row["next_step"]],
        ))
    return html.Div([html.Div("Research area comparison", className="atlas-panel-title")] + cards)


@callback(
    Output("inspector-content", "children"),
    Input("selected-map-feature-store", "data"),
    Input("analysis-store", "data"),
)
def inspect_feature(selection, analysis):
    if not analysis or callback_context.triggered_id == "analysis-store":
        return "Review an area, then click a map feature for record details."
    if _render_summary(analysis) is None:
        return "Invalid area review. Run Review Research Area again."
    if selection is None:
        return "Click a site or context feature to inspect it."
    if not isinstance(selection, dict):
        return "Invalid map selection. Click a map marker again."
    if selection.get("cluster_count") is not None:
        count = selection["cluster_count"]
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1_000_000:
            return "Invalid map selection. Click a map marker again."
        return f"{selection['cluster_count']} records are grouped here. Zoom in and click an individual marker to inspect it."
    feature = selection.get("feature")
    if not feature:
        return "Click a site or context feature to inspect it."
    if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
        return "Invalid map selection. Click a map marker again."
    props = feature["properties"]
    text_keys = ("name", "zone_name", "site_type", "period", "source", "record_id", "geocode_method", "state", "description")
    if any(props.get(key) is not None and not isinstance(props[key], str) for key in text_keys):
        return "Invalid map selection. Click a map marker again."
    if props.get("geocode_confidence") is not None and not _finite_render_number(props["geocode_confidence"]):
        return "Invalid map selection. Click a map marker again."
    if any(props.get(key) is not None and not _string_list(props[key]) for key in ("likely_remains", "evidence_names")):
        return "Invalid map selection. Click a map marker again."
    if props.get("period_mix") is not None and not (isinstance(props["period_mix"], str) or _string_list(props["period_mix"])):
        return "Invalid map selection. Click a map marker again."
    lines = []
    for key in ["site_type", "period", "source", "record_id", "geocode_method", "geocode_confidence", "state", "description", "period_mix"]:
        value = props.get(key)
        if value is not None and value != "":
            if isinstance(value, list):
                value = ", ".join(value)
            lines.append(html.Div(f"{key.replace('_', ' ').title()}: {value}", className="atlas-summary-line"))
    likely = props.get("likely_remains")
    if likely:
        lines.append(html.Div(f"Likely remains: {', '.join(likely)}", className="atlas-summary-line"))
    evidence_names = props.get("evidence_names")
    if evidence_names:
        lines.append(html.Div(f"Driving records: {', '.join(evidence_names)}", className="atlas-summary-line"))
    return html.Div(
        [html.Div(props.get("name") or props.get("zone_name") or "Feature", className="atlas-summary-title")] + lines,
        className="atlas-summary-block",
    )
