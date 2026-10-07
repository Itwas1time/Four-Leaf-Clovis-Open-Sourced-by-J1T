from __future__ import annotations

import dash_leaflet as dl
from dash_extensions.javascript import variable

from atlas.gui.styles import TILE_ATTRIBUTIONS, TILE_URLS

EMPTY_FC = {"type": "FeatureCollection", "features": []}


def _client_function(name: str) -> dict:
    return variable("dash_clientside", "atlas", name)


def make_tile_layer(layer_key: str = "terrain") -> dl.TileLayer:
    return dl.TileLayer(
        id="base-tile-layer",
        url=TILE_URLS.get(layer_key, TILE_URLS["terrain"]),
        attribution=TILE_ATTRIBUTIONS.get(layer_key, ""),
        maxZoom=19,
    )


def make_buffer_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="buffer-layer",
        data=EMPTY_FC,
        options={"style": {"color": "#7dd3fc", "weight": 2, "opacity": 0.65, "fillOpacity": 0.04, "dashArray": "6 6"}},
        zoomToBounds=False,
    )


def make_aoi_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="aoi-layer",
        data=EMPTY_FC,
        options={"style": {"color": "#fbbf24", "weight": 3, "opacity": 0.95, "fillOpacity": 0.06}},
        zoomToBounds=False,
    )


def make_scored_cells_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="scored-cells-layer",
        data=EMPTY_FC,
        style=_client_function("hexStyle"),
        hoverStyle=dict(weight=2.5, fillOpacity=0.88),
        zoomToBounds=False,
    )


def make_hotspot_markers_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="hotspot-markers-layer",
        data=EMPTY_FC,
        pointToLayer=_client_function("hotspotMarkerPointToLayer"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )


def make_known_sites_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="known-sites-layer",
        data=EMPTY_FC,
        cluster=True,
        superClusterOptions={"radius": 38, "maxZoom": 12},
        pointToLayer=_client_function("knownSitePointToLayer"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )


def make_nearby_sites_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="nearby-sites-layer",
        data=EMPTY_FC,
        cluster=True,
        superClusterOptions={"radius": 38, "maxZoom": 11},
        pointToLayer=_client_function("nearbySitePointToLayer"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )


def make_paleo_context_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="paleo-context-layer",
        data=EMPTY_FC,
        cluster=True,
        superClusterOptions={"radius": 36, "maxZoom": 11},
        pointToLayer=_client_function("paleoContextPointToLayer"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )


def make_tribal_boundaries_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="tribal-boundaries-layer",
        data=EMPTY_FC,
        style=_client_function("tribalBoundaryStyle"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )


def make_native_territories_layer() -> dl.GeoJSON:
    return dl.GeoJSON(
        id="native-territories-layer",
        data=EMPTY_FC,
        style=_client_function("nativeTerritoryStyle"),
        onEachFeature=_client_function("bindFeatureLabel"),
        zoomToBounds=False,
    )
