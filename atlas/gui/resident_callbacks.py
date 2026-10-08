"""Resident callbacks keep browser values bounded and exports server-owned."""
from dash import Input, Output, State, callback, callback_context, clientside_callback, html, no_update
import dash_leaflet as dl

from atlas.gui.data.fieldwork_leads import LEADS_BY_ID
from core.resident_context import build_context, current_report, input_key, remember_report
from core.us_places import get_place, search_places, states
from core.state_context import state_context


@callback(Output("resident-place", "options"), Output("resident-place", "disabled"),
          Input("resident-state", "value"), Input("resident-place", "search_value"),
          State("resident-place", "value"))
def place_choices(state, query, selected):
    return search_places(state, query or "", selected), state not in states() if isinstance(state, str) else True


@callback(Output("resident-build", "disabled"), Input("resident-state", "value"), Input("resident-place", "value"))
def ready_to_explore(state, geoid):
    return get_place(geoid, state) is None


@callback(Output("resident-report-heading", "children"), Output("resident-choose-place", "children"),
          Output("header-place-button", "children"), Output("resident-lookup-note", "children"),
          Output("resident-state-background", "open"), Output('resident-workbench-title', 'children'), Output('resident-workbench-title','title'),
          Input("resident-state", "value"), Input("resident-place", "value"), Input("resident-online", "value"),Input('resident-tool','value'))
def place_actions(state, geoid, online, tool='map'):
    place = get_place(geoid, state)
    chosen = place is not None
    heading = f"{place['name']}, {place['state']}" if chosen else "Your field notes"
    note = ("Includes online rock maps at the public town point." if isinstance(online, list) and "geology" in online
            else "Offline report. Online rock maps are off.")
    workbench='Atlas' if tool=='library' else heading if chosen else 'Explore a place.'
    return heading, "Change town ↗" if chosen else "Choose a town ↗", "Change town ↗" if chosen else "Choose town ↗", note, False, workbench, heading


@callback(Output('clovis-app','className'),
          Output('resident-build','children'), Output('clovis-reading-path','children'),
          Input('resident-report-store','data'), Input('resident-state','value'), Input('resident-place','value'),
          Input('resident-history','value'), Input('resident-online','value'), Input('workflow-mode','value'), Input('resident-tool','value'))
def workspace_progress(token, state, geoid, history, online, mode, tool='map'):
    place = get_place(geoid, state)
    report = current_report(token, state, geoid, history, online)
    mode = mode if mode in ('resident','inspect','notebook','research') else 'resident'
    stage = 'clovis-has-report' if report else 'clovis-has-place' if place else 'clovis-start'
    labels = ('Place selected' if place else 'Choose a place',
              'Evidence ready' if report else 'Explore its evidence', 'Keep a field note')
    path = [html.Span([html.Small(f'0{index+1}'), label],
                      className='is-done' if (index==0 and place) or (index==1 and report) else
                      'is-current' if index==(2 if report else 1 if place else 0) else '')
            for index,label in enumerate(labels)]
    tool = tool if tool in ('map','archive','missions','library') else 'map'
    return f'atlas-app-shell clovis-mode-{mode} clovis-tool-{tool} {stage}', \
        ('Refresh town evidence ↻' if report else 'Explore this town →'), path


clientside_callback(
    """function(header, panel) {
        if (!window.dash_clientside.callback_context.triggered_id) return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        return ['resident', Date.now()];
    }""",
    Output('workflow-mode','value'), Output('place-focus-request','data'),
    Input('header-place-button','n_clicks'), Input('resident-choose-place','n_clicks'), prevent_initial_call=True)


clientside_callback(
    """function(request, state) {
        if (!request) return window.dash_clientside.no_update;
        return new Promise(resolve => {
            let attempts = 0;
            const focusPlace = () => {
                const controls = document.getElementById('resident-controls');
                const target = document.getElementById(state ? 'resident-place' : 'resident-state');
                if (controls && controls.getBoundingClientRect().height && target && !target.disabled) {
                    target.scrollIntoView({block:'center', behavior:'auto'});
                    target.focus();
                    target.click();
                    resolve(request);
                } else if (++attempts < 120) requestAnimationFrame(focusPlace);
                else resolve(window.dash_clientside.no_update);
            };
            requestAnimationFrame(focusPlace);
        });
    }""",
    Output('place-focus-complete','data'), Input('place-focus-request','data'), State('resident-state','value'))


clientside_callback(
    """function(token, place, state, mode) {
        const changed = window.dash_clientside.callback_context.triggered || [];
        if (window.innerWidth <= 980 && changed.some(item => item.prop_id === 'workflow-mode.value')) {
            return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => {
                window.scrollTo({top:0,behavior:'auto'}); resolve(Date.now());
            })));
        }
        if (mode !== 'resident') return window.dash_clientside.no_update;
        const panel = document.getElementById('inspector-panel');
        if (panel) panel.scrollTop = 0;
        if (typeof token === 'string' && token &&
            changed.some(item => item.prop_id === 'resident-report-store.data')) {
            return new Promise(resolve => {
                let attempts = 0;
                const reveal = () => {
                    const shell = document.getElementById('clovis-app');
                    const workbench = document.getElementById('resident-workbench');
                    if (shell?.classList.contains('clovis-has-report') && workbench?.getBoundingClientRect().height) {
                        const controls = document.getElementById('layer-panel');
                        if (controls) controls.scrollTop = 0;
                        if (window.innerWidth <= 980) window.scrollTo({top:Math.max(0, workbench.getBoundingClientRect().top + window.scrollY - 12),behavior:'auto'});
                        resolve(Date.now());
                    } else if (++attempts < 120) requestAnimationFrame(reveal);
                    else resolve(window.dash_clientside.no_update);
                };
                requestAnimationFrame(reveal);
            });
        }
        return Date.now();
    }""",
    Output('resident-panel-position','data'), Input('resident-report-store','data'),
    Input('resident-place','value'), Input('resident-state','value'), Input('workflow-mode','value'))


def clear_mismatched_place(state, geoid):
    return geoid if get_place(geoid, state) else None


@callback(Output("resident-controls", "style"), Output("resident-inspector", "style"),
          Output("research-controls", "style"), Output("research-inspector", "style"),
          Output("inspection-controls", "style"), Output("inspection-inspector", "style"),
          Output("inspection-workspace", "style"), Output("map-workspace", "style"),
          Output('fieldbook-controls','style'), Output('fieldbook-inspector','style'), Output('fieldbook-workspace','style'),
          Output('archive-workspace','style'), Output('mission-workspace','style'),
          Output('resident-workbench','style'), Output('resident-workbench-bar','style'),
          Output('library-workspace','style'),
          Input("workflow-mode", "value"), Input('resident-tool','value'))
def workflow_sections(mode, tool='map'):
    show, hide = {"display": "block"}, {"display": "none"}
    map_show={'display':'flex','flexDirection':'column','height':'100%','width':'100%','position':'relative','flex':'1','minHeight':'0'}
    workbench_show={'display':'flex','flexDirection':'column','height':'100%','minHeight':'0'}
    if mode == 'inspect': return hide, hide, hide, hide, show, show, show, hide, hide, hide, hide, hide, hide, hide, hide, hide
    if mode == 'notebook': return hide, hide, hide, hide, hide, hide, hide, hide, show, show, show, hide, hide, hide, hide, hide
    if mode == 'research': return hide, hide, show, show, hide, hide, hide, map_show, hide, hide, hide, hide, hide, workbench_show, hide, hide
    return show, hide if tool=='library' else show, hide, hide, hide, hide, hide, map_show if tool not in ('archive','missions','library') else hide, hide, hide, hide, show if tool=='archive' else hide, show if tool=='missions' else hide, workbench_show, {}, show if tool=='library' else hide


clientside_callback(
    """function(style) {
        if (style && style.display === 'none') return window.dash_clientside.no_update;
        return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => {
            const element = document.getElementById('main-map');
            if (element && window.ResizeObserver && window.dash_clientside.set_props) {
                const previous = window.clovisMapResize;
                if (!previous || previous.element !== element) {
                    if (previous) { previous.observer.disconnect(); cancelAnimationFrame(previous.frame); }
                    const state = {element, frame:0, observer:null};
                    state.observer = new ResizeObserver(entries => {
                        if (!entries.some(entry => entry.contentRect.width > 0 && entry.contentRect.height > 0)) return;
                        cancelAnimationFrame(state.frame);
                        state.frame = requestAnimationFrame(() => {
                            window.dash_clientside.set_props('main-map', {invalidateSize:Date.now()});
                        });
                    });
                    state.observer.observe(element);
                    window.clovisMapResize = state;
                }
            }
            resolve(Date.now());
        })));
    }""",
    Output('main-map','invalidateSize'),Input('map-workspace','style'))


@callback(Output("resident-empty-state", "style"), Output("map-workspace", "className"),
          Input("resident-report-store", "data"), Input("workflow-mode", "value"), Input("resident-state", "value"))
def display_context_state(token, mode, state):
    return ({"display": "none"} if (isinstance(token, str) and token) or state_context(state) else {"display": "block"},
            "atlas-map-frame atlas-map-research clovis-map-workspace" if mode == "research" else "atlas-map-frame atlas-map-resident clovis-map-workspace")


@callback(Output("resident-state-guide", "children"), Input("resident-state", "value"), Input("resident-report-store", "data"))
def show_state_context(state, token):
    return state_context(state)


@callback(Output("main-map", "viewport", allow_duplicate=True),
          Input("workflow-mode", "value"), Input("resident-place", "value"),
          Input("resident-state", "value"), State("selected-lead-store", "data"),
          prevent_initial_call=True)
def navigate_workflow(mode, geoid, state, lead_id):
    if mode in ('inspect','notebook'): return no_update
    if mode == "research":
        lead = LEADS_BY_ID.get(lead_id) if isinstance(lead_id, str) else None
        return {"center": lead["center"], "zoom": lead["zoom"], "transition": "setView"} if lead else no_update
    place = get_place(geoid, state)
    return {"center": [place["latitude"], place["longitude"]], "zoom": 9, "transition": "setView"} if place else no_update


@callback(Output("resident-town-point", "children"),
          Input("workflow-mode", "value"), Input("resident-place", "value"), Input("resident-state", "value"))
def show_town_point(mode, geoid, state):
    place = get_place(geoid, state)
    if mode != "resident" or place is None:
        return []
    return [dl.CircleMarker(
        center=[place['latitude'], place['longitude']], radius=8,
        color="#ffffff", weight=3, fillColor="#285d45", fillOpacity=1,
        children=dl.Tooltip(f"{place['name']}, {state} · Public Census town point",
                            permanent=True, direction="top", className="atlas-town-tooltip"))]


@callback(Output("resident-preview", "children"), Output("resident-status", "children"),
          Output("resident-report-store", "data"), Output("resident-download-button", "disabled"),
          Output("resident-summary", "children"),
          Output('resident-save','disabled'),
          Input("resident-build", "n_clicks"), Input("resident-state", "value"),
          Input("resident-place", "value"), Input("resident-history", "value"),
          Input("resident-online", "value"),
          running=[(Output("resident-loading", "style"), {"display": "block"}, {"display": "none"})])
def render_resident_context(clicks, state, geoid, history, online):
    if not any(item['prop_id']=='resident-build.n_clicks' for item in callback_context.triggered) or not clicks:
        status = "Select Explore this town to build your field notes." if get_place(geoid, state) else "Choose a town to begin your field notes."
        return "", status, None, True, "", True
    try:
        input_key(state, geoid, history, online)
        report = build_context(state, geoid, history, online)
    except ValueError as exc:
        return "", str(exc), None, True, "", True
    token = remember_report(report)
    geology_status = {'available':'Rock-map evidence is ready.', 'not_requested':'Rock maps are off.',
                      'no_coverage':'No rock-map coverage returned.', 'unavailable':'Rock maps could not load.'}
    status = 'Town context ready. ' + geology_status.get(report['geology_status'], 'Rock-map status is unknown.')
    return report["markdown"], status, token, False, report["summary"], False


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
