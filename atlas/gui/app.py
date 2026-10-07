from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from threading import Timer

import dash
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import html

from atlas.gui.data.lead_catalog import matching_leads
from core.web_security import configure_local_flask

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from atlas.gui.components import build_header, build_inspector_panel, build_layer_panel, build_stores
from atlas.gui.map_layers import (
    make_aoi_layer,
    make_buffer_layer,
    make_hotspot_markers_layer,
    make_known_sites_layer,
    make_nearby_sites_layer,
    make_native_territories_layer,
    make_paleo_context_layer,
    make_scored_cells_layer,
    make_tile_layer,
    make_tribal_boundaries_layer,
)
from atlas.gui.styles import BG_PRIMARY, MAP_CONTAINER_STYLE

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        "https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css",
    ],
    suppress_callback_exceptions=True,
    title="Clovis Discovery Planner",
    update_title=None,
    assets_folder=str(Path(__file__).resolve().parent / "assets"),
)
server = app.server
configure_local_flask(server)
_initial_leads = matching_leads()
_initial_center = [39.8283, -98.5795]
_initial_zoom = 4


def _build_map() -> html.Div:
    return html.Div(
        style={"flex": "1", "position": "relative", "minHeight": "0"},
        children=[
            dl.Map(
                id="main-map",
                center=_initial_center,
                zoom=_initial_zoom,
                maxZoom=18,
                minZoom=3,
                trackViewport=True,
                style={"width": "100%", "height": "100%", "background": BG_PRIMARY},
                children=[
                    make_tile_layer("terrain"),
                    dl.ScaleControl(position="bottomleft"),
                    dl.FeatureGroup(
                        [
                            dl.EditControl(
                                id="draw-control",
                                position="topright",
                                draw={
                                    "polyline": False,
                                    "marker": False,
                                    "circlemarker": False,
                                    "rectangle": True,
                                    "polygon": True,
                                    "circle": True,
                                },
                                edit={"edit": True, "remove": True},
                                geojson={"type": "FeatureCollection", "features": []},
                            )
                        ]
                    ),
                    make_buffer_layer(),
                    make_aoi_layer(),
                    make_scored_cells_layer(),
                    make_native_territories_layer(),
                    make_tribal_boundaries_layer(),
                    make_nearby_sites_layer(),
                    make_known_sites_layer(),
                    make_paleo_context_layer(),
                    make_hotspot_markers_layer(),
                ],
            )
        ],
    )


app.layout = html.Div(
    [
        build_header(),
        html.Div(
            [
                build_layer_panel(),
                html.Div([_build_map()], style=MAP_CONTAINER_STYLE, className="atlas-map-shell"),
                build_inspector_panel(),
            ],
            style={"display": "flex", "flex": "1", "minHeight": "0", "overflow": "hidden"},
            className="atlas-main-row",
        ),
        build_stores(),
    ],
    style={
        "display": "flex",
        "flexDirection": "column",
        "height": "100vh",
        "width": "100vw",
        "overflow": "hidden",
    },
    className="atlas-app-shell",
)


import atlas.gui.callbacks  # noqa: E402,F401
import atlas.gui.resident_callbacks  # noqa: E402,F401


def _open_browser(url: str) -> None:
    try:
        webbrowser.get()
        webbrowser.open(url)
    except webbrowser.Error:
        pass


def main() -> None:
    port = 8050
    url = f"http://localhost:{port}"
    print(f"Clovis Local Atlas starting on {url}")
    Timer(1.5, _open_browser, args=[url]).start()
    app.run(debug=False, port=port, host="127.0.0.1")


if __name__ == "__main__":
    main()
