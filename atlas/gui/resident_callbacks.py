"""Resident callbacks keep browser values bounded and exports server-owned."""
from dash import Input, Output, State, callback, callback_context, no_update

from atlas.gui.data.fieldwork_leads import LEADS_BY_ID
from core.resident_context import build_context, current_report, input_key, remember_report
from core.us_places import get_place, search_places, states


@callback(Output("resident-place", "options"), Output("resident-place", "disabled"),
          Input("resident-state", "value"), Input("resident-place", "search_value"),
          State("resident-place", "value"))
def place_choices(state, query, selected):
    return search_places(state, query or "", selected), state not in states() if isinstance(state, str) else True


@callback(Output("resident-build", "disabled"), Input("resident-state", "value"), Input("resident-place", "value"))
def ready_to_explore(state, geoid):
    return get_place(geoid, state) is None


@callback(Output("resident-place", "value"), Input("resident-state", "value"),
          State("resident-place", "value"), prevent_initial_call=True)
def clear_mismatched_place(state, geoid):
    return geoid if get_place(geoid, state) else None


@callback(Output("resident-controls", "style"), Output("resident-inspector", "style"),
          Output("research-controls", "style"), Output("research-inspector", "style"),
          Input("workflow-mode", "value"))
def workflow_sections(mode):
    show, hide = {"display": "block"}, {"display": "none"}
    return (hide, hide, show, show) if mode == "research" else (show, show, hide, hide)


@callback(Output("resident-empty-state", "style"), Output("map-workspace", "className"),
          Input("resident-report-store", "data"), Input("workflow-mode", "value"))
def display_context_state(token, mode):
    return ({"display": "none"} if isinstance(token, str) and token else {"display": "block"},
            "atlas-map-frame atlas-map-research" if mode == "research" else "atlas-map-frame atlas-map-resident")


@callback(Output("main-map", "viewport", allow_duplicate=True),
          Input("workflow-mode", "value"), Input("resident-place", "value"),
          Input("resident-state", "value"), State("selected-lead-store", "data"),
          prevent_initial_call=True)
def navigate_workflow(mode, geoid, state, lead_id):
    if mode == "research":
        lead = LEADS_BY_ID.get(lead_id) if isinstance(lead_id, str) else None
        return {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"} if lead else no_update
    place = get_place(geoid, state)
    return {"center": [place["latitude"], place["longitude"]], "zoom": 9, "transition": "setView"} if place else no_update


@callback(Output("resident-preview", "children"), Output("resident-status", "children"),
          Output("resident-report-store", "data"), Output("resident-download-button", "disabled"),
          Input("resident-build", "n_clicks"), Input("resident-state", "value"),
          Input("resident-place", "value"), Input("resident-history", "value"),
          Input("resident-online", "value"))
def render_resident_context(clicks, state, geoid, history, online):
    if callback_context.triggered_id != "resident-build" or not clicks:
        return "", "Choose a town to begin your field notes.", None, True
    try:
        input_key(state, geoid, history, online)
        report = build_context(state, geoid, history, online)
    except ValueError as exc:
        return "", str(exc), None, True
    token = remember_report(report)
    status = f"Town context ready · geology {report['geology_status'].replace('_', ' ')} · likelihood not estimable."
    return report["markdown"], status, token, False


@callback(Output("resident-download", "data"), Output("resident-status", "children", allow_duplicate=True),
          Input("resident-download-button", "n_clicks"),
          State("resident-report-store", "data"), State("resident-state", "value"),
          State("resident-place", "value"), State("resident-history", "value"),
          State("resident-online", "value"), prevent_initial_call=True)
def download_resident_context(clicks, token, state, geoid, history, online):
    report = current_report(token, state, geoid, history, online) if clicks else None
    if report is None:
        return no_update, "This report expired or the inputs changed. Select Explore this town to build a current report."
    return {"content": report["markdown"], "filename": f"clovis-town-context-{geoid}.md", "type": "text/markdown"}, no_update
