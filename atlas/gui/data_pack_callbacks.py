from atlas.gui.library_activation import require_section
from dash import ALL, Input, Output, State, callback, callback_context, html, no_update
from core.data_packs import PackStore
from core import data_pack_jobs, data_pack_uploads

LIBRARIES = {'radiocarbon-world': ('atlas', 'Explore in atlas'),
             'dinosaur-sites': ('atlas', 'Explore in atlas'),
             'neolithic-assemblages': ('atlas', 'Explore in atlas'),
             'excavations-surveys': ('atlas', 'Explore in atlas'),
             'dated-environments': ('atlas', 'Explore in atlas'),
             'anatolian-zooarchaeology': ('atlas', 'Explore in atlas'),
             'excavation-assemblages': ('atlas', 'Explore in atlas'),
             'north-american-sites': ('atlas', 'Explore in atlas'),
             'ancient-places': ('atlas', 'Explore in atlas'),
             'ads-research-metadata': ('atlas', 'Explore in atlas'),
             'amcr-native-metadata': ('atlas', 'Explore in atlas'),
             'dans-archaeology-metadata': ('atlas', 'Explore in atlas')}


@callback(Output('library-workspace', 'className'), Input('library-section', 'value'))
def collection_scroll_context(section):
    return 'clovis-library-workspace' + (' clovis-collection-workspace' if section == 'packs' else '')


@callback(Output("data-pack-cards", "children"), Input("data-pack-refresh", "data"), Input("library-section", "value"))
def cards(_refresh, section="packs"):
    require_section(section, "packs")
    try:
        store = PackStore()
        identifiers = sorted({row["id"] for row in store.definitions})
        children = []
        for identifier in identifiers:
            pack = store.definition(identifier)
            state = store.status(identifier)
            local_only = not pack['download_url']
            action = "Installed" if state["state"] == "installed" else "Update collection" if state["state"] == "update" else "Repair collection" if state["state"] == "damaged" else "Download collection"
            actions = []
            if not local_only:
                actions.append(html.Button(action, id={"type": "data-pack-install", "index": identifier}, n_clicks=0,
                    disabled=state['state'] == 'installed', className='atlas-primary-button'))
            actions.append(html.Button('Install from ZIP', type='button', className='atlas-secondary-button',
                **{'data-clovis-pack': identifier, 'data-clovis-bytes': str(pack['archive_bytes'])}))
            if identifier in LIBRARIES:
                actions.append(html.Button(LIBRARIES[identifier][1], id={"type": "data-pack-open", "index": identifier}, n_clicks=0,
                    disabled=state['state'] not in ('installed', 'update'), className='atlas-secondary-button'))
            children.append(html.Article([
                html.H3(pack["title"]), html.P(pack["description"]),
                html.P(f'{pack["records"]:,} {pack["record_type"]}', className="clovis-library-coverage"),
                html.P(pack["coverage"], className="atlas-help"),
                html.P(f'{pack["archive_bytes"] / 1_000_000:.1f} MB {"ZIP" if local_only else "download"} · {pack["installed_bytes"] / 1_000_000:.1f} MB installed · {pack["license"]}', className="atlas-help"),
                html.P("Snapshot " + pack["source_release"] + " · " + state["message"], className="atlas-help"),
                html.A("Original collection & reuse rights", href=pack["source_url"], target="_blank", rel="noopener noreferrer"),
                html.Span(" · "), html.A("Research citation", href=pack["citation_url"], target="_blank", rel="noopener noreferrer"),
                *([html.Span(' · '), html.A('Download ZIP for offline transfer', href=pack['download_url'], target='_blank', rel='noopener noreferrer')]
                  if not local_only else [html.P('Local ZIP collection · no online download in this catalog.', className='atlas-help')]),
                html.Div(actions, className="clovis-pack-actions"),
            ], className="clovis-pack-card"))
        return children
    except (ValueError, OSError, KeyError, TypeError):
        return html.P("The local collection catalog could not be read.")


@callback(Output("data-pack-job", "data"), Output("data-pack-start-status", "children"),
          Output("data-pack-poll", "disabled", allow_duplicate=True),
          Input({"type": "data-pack-install", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def install(clicks):
    trigger = callback_context.triggered_id
    if not isinstance(trigger, dict) or not any(type(value) is int and value > 0 for value in clicks or []):
        return no_update, no_update, no_update
    try:
        return data_pack_jobs.start(trigger["index"]), "", False
    except ValueError as error:
        return no_update, str(error), no_update
    except (OSError, KeyError):
        return no_update, "A collection is already downloading, or the collection catalog is unavailable.", no_update


@callback(Output("data-pack-progress", "children"), Output("data-pack-poll", "disabled"),
          Output("data-pack-refresh", "data"), Input("data-pack-poll", "n_intervals"),
          Input("data-pack-job", "data"))
def progress(_ticks, identifier):
    data_pack_uploads.expire()
    job = data_pack_jobs.status(identifier)
    if job is None:
        return "", True, no_update
    working = job["state"] == "working"
    fraction = job["received"] / job["total"] if job["total"] else 0
    title = job.get('title', job['pack'])
    children = [html.Strong(title), html.P(job["phase"]),
                html.Progress(value=min(100, round(fraction * 100)) if job['total'] else None, max=100,
                              hidden=not working, **{'aria-label': title + ' installation progress'}),
                html.P(f'{job["received"] / 1_000_000:.1f} of {job["total"] / 1_000_000:.1f} MB' if working and job["total"] else job["message"])]
    return children, not working, no_update if working else job["finished"]


@callback(Output("library-section", "value", allow_duplicate=True),
          Input({"type": "data-pack-open", "index": ALL}, "n_clicks"), prevent_initial_call=True)
def open_collection(clicks):
    trigger = callback_context.triggered_id
    return LIBRARIES[trigger['index']][0] if isinstance(trigger, dict) and trigger.get("index") in LIBRARIES and any(
        type(value) is int and value > 0 for value in clicks or []) else no_update
