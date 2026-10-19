"""An optional offline location map within the shared source reader."""
from functools import lru_cache
import json
from pathlib import Path

import dash_leaflet as dl
from dash import html

from core.published_locations import frame, locations


def control(identifier, label='Show published location map'):
    return html.Div([
        html.Button(label, id={"type": "atlas-location-open", "index": identifier}, n_clicks=0,
                    className="atlas-secondary-button"),
        html.Div(id={"type": "atlas-location-view", "index": identifier}, role="region", **{"aria-label": "Published location map"}),
    ])


@lru_cache(maxsize=1)
def _land():
    data = json.loads((Path(__file__).parent / "assets/natural-earth-land-110m.json").read_text(encoding="utf-8"))

    def shift(coordinates, offset):
        if coordinates and isinstance(coordinates[0], (int, float)):
            return [coordinates[0] + offset, *coordinates[1:]]
        return [shift(part, offset) for part in coordinates]

    # Adjacent world copies make the offline outline work across the dateline.
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {
            "type": feature["geometry"]["type"],
            "coordinates": shift(feature["geometry"]["coordinates"], offset)}}
        for offset in (-360, 0, 360) for feature in data["features"]]}


def render(record,*,map_id='atlas-published-map'):
    rows, bounds = frame(locations(record))
    if not rows:
        if record.get('source') in ('ads', 'dans'):
            return html.P('No usable numeric point or bounding box is available for this plot. All original location fields remain in the source reader.', className='atlas-help')
        return html.P("This record has no usable published coordinates. Its original location fields remain in the source reader.", className="atlas-help")
    layers = [dl.GeoJSON(data=_land(), interactive=False,
                        options={"style": {"color": "#8f9f82", "weight": 1,
                                           "fillColor": "#d8e0c7", "fillOpacity": 1}})]
    shapes = []
    max_zoom=18 if record.get('source')=='raa' and any(row['shape']=='geojson' for row in rows) else 12
    for row in rows:
        color=row.get('color','#275840')
        popup = dl.Popup(html.Div([html.Strong(row["label"]), html.P(row["id"]), html.P(row["note"])]))
        if row["shape"] == "geojson":
            layer = dl.GeoJSON(data={"type": "Feature", "properties": {}, "geometry": row["geometry"]},
                options={"style": {"color": color, "weight": 2, "fillColor": color, "fillOpacity": 0.15}},
                children=popup)
        elif row["shape"] == "point":
            layer = dl.CircleMarker(center=row["coordinates"][0], radius=7, color="#275840",
                                    fillColor="#275840", fillOpacity=0.9, children=popup)
        elif row["shape"] == "line":
            layer = dl.Polyline(positions=row["coordinates"], color="#275840", weight=3, children=popup)
        else:
            layer = dl.Polygon(positions=row["coordinates"], color="#275840", weight=2,
                               fillColor="#275840", fillOpacity=0.2, children=popup)
        shapes.append(layer)
    layers.append(dl.Pane(shapes, name="published-source-locations", style={"zIndex": 450}))
    layers.append(dl.ScaleControl(position="bottomleft"))
    if bounds[0] == bounds[1]:
        view = {"center": bounds[0], "zoom": 3}
    else:
        # Camera centre only. The published area is drawn without a centre pin.
        # Dash Leaflet's move handler also requires a defined initial centre.
        view = {"center": [(bounds[0][0] + bounds[1][0]) / 2,
                           (bounds[0][1] + bounds[1][1]) / 2],
                "bounds": bounds, "boundsOptions": {"padding": [24, 24], "maxZoom": max_zoom}}
    notice = [html.P("This plot uses the source's declared latitude and longitude. Check the coordinate fields against the place text and original report; numeric validity does not verify the geographic interpretation.", className='atlas-help')] if record.get('source') in ('ads', 'dans') else []
    return [*notice, dl.Map(layers, id=map_id, **view, crs="EPSG4326", maxZoom=max_zoom,
                   scrollWheelZoom=False, attributionControl=False, trackResize=True,
                   className="clovis-published-map", style={"height": "300px", "width": "100%"}),
            html.Ul([html.Li([html.Strong(row["label"] + " · " + row["id"]),
                              html.P(row["note"])],style={'borderLeft':'4px solid '+row['color'],'paddingLeft':'8px'} if row.get('color') else {}) for row in rows], className="clovis-location-key"),
            html.P(["Offline modern land outline: ",
                    html.A("Natural Earth", href="https://www.naturalearthdata.com/", target="_blank", rel="noopener noreferrer"),
                    ". General orientation at 1:110 million scale; the outline does not show ancient shores or site boundaries."], className="atlas-help")]
