"""Draw only coordinates and areas published with the selected source record."""
from math import isfinite


def _coordinate(value, limit):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) and -limit <= number <= limit else None


def locations(record):
    """Keep independent original sites separate; never geocode names or infer GPS."""
    original = record.get("original") or {}
    result = []
    if record.get('source')=='raa':
        from core.raa_fieldwork_catalog import published_geometries
        return published_geometries(original)
    if record.get('source')=='finland':
        from core.finland_register_catalog import published_geometries
        return published_geometries(original)
    if record.get('source') in ('ads', 'dans'):
        attributes = original.get('source', {}).get('attributes', {})
        for index, location in enumerate(attributes.get('geoLocations') or [], 1):
            if not isinstance(location, dict):
                continue
            point = location.get('geoLocationPoint') or {}
            box = location.get('geoLocationBox') or {}
            label = location.get('geoLocationPlace') or 'Published resource coverage'
            if not isinstance(label, str):
                label = 'Published resource coverage'
            note = ('Published DOI resource location metadata; its spatial meaning and precision are unestablished. '
                    'This does not establish an excavation footprint or an individual find location. '
                    'Original place, point and box fields remain separate in the metadata reader.')
            if isinstance(point, dict):
                latitude = _coordinate(point.get('pointLatitude'), 90)
                longitude = _coordinate(point.get('pointLongitude'), 180)
                if latitude is not None and longitude is not None:
                    result.append({'id': original['doi'] + '/location/' + str(index) + '/point', 'label': label,
                        'shape': 'point', 'coordinates': [[latitude, longitude]], 'note': note})
            if isinstance(box, dict):
                south = _coordinate(box.get('southBoundLatitude'), 90)
                north = _coordinate(box.get('northBoundLatitude'), 90)
                west = _coordinate(box.get('westBoundLongitude'), 180)
                east = _coordinate(box.get('eastBoundLongitude'), 180)
                if None not in (south, north, west, east) and south <= north:
                    east_display = east + 360 if west > east else east
                    shape, points = ('point', [[south, west]]) if west == east_display and south == north else (
                        ('line', [[south, west], [north, east_display]]) if west == east_display or south == north else
                        ('area', [[south, west], [south, east_display], [north, east_display], [north, west]]))
                    result.append({'id': original['doi'] + '/location/' + str(index) + '/box', 'label': label,
                        'shape': shape, 'coordinates': points, 'note': 'Original bounding box. ' + note})
    elif record.get("source") == "places":
        source = original.get("source") or {}
        native_locations = {item.get("uri"): item for item in source.get("locations", [])}
        for feature in source.get("features", []):
            geometry = feature.get("geometry")
            points = geometry_points(geometry)
            if not points:
                continue
            properties = feature.get("properties") or {}
            location = native_locations.get(properties.get("link"), {})
            result.append({"id": properties.get("link") or str(feature.get("id", "")),
                "label": properties.get("title") or location.get("title") or "Published location",
                "shape": "geojson", "geometry": geometry, "coordinates": points,
                "note": "Original published location geometry. Source precision: "
                    + str(properties.get("location_precision") or "Not recorded")
                    + ". Source association certainty: " + str(location.get("associationCertainty") or "Not recorded")
                    + ". Native accuracy value: " + str(location.get("accuracy_value") if location.get("accuracy_value") is not None else "Not recorded")
                    + ". These are gazetteer locations, not a record of where a find was excavated."})
        if not result:
            point = source.get("reprPoint")
            if isinstance(point, list) and len(point) == 2:
                longitude, latitude = _coordinate(point[0], 180), _coordinate(point[1], 90)
                if longitude is not None and latitude is not None:
                    result.append({"id": source.get("uri", ""), "label": "Publisher's representative point",
                        "shape": "point", "coordinates": [[latitude, longitude]],
                        "note": "Pleiades calculated this representative point from location centroids or connected places. "
                                "No usable original location geometry is present here. This is not an exact site or find location."})
    elif record.get("source") == "environments":
        for site in original.get("associated", {}).get("sites", []):
            if not site:
                continue
            west, east = (_coordinate(site.get(key), 180) for key in ("longitudewest", "longitudeeast"))
            south, north = (_coordinate(site.get(key), 90) for key in ("latitudesouth", "latitudenorth"))
            if None in (west, east, south, north) or south > north:
                continue
            # An east bound below the west bound crosses the antimeridian.
            # Unwrap for display only; the reader keeps every original value.
            east_display = east + 360 if west > east else east
            if west == east_display and south == north:
                shape, coordinates = "point", [[south, west]]
            elif west == east_display or south == north:
                shape, coordinates = "line", [[south, west], [north, east_display]]
            else:
                shape, coordinates = "area", [[south, west], [south, east_display],
                                               [north, east_display], [north, west]]
            result.append({"id": "Neotoma site " + str(site.get("siteid", "")),
                           "label": site.get("sitename") or "Published site", "shape": shape,
                           "coordinates": coordinates,
                           "note": "Published point or bounding area. An area may describe extent, uncertainty or an obscured location; its centre is not an exact site position."})
    elif record.get("source") == "site_registers":
        from core.site_register_catalog import cell
        for edition in original.get("editions", []):
            latitude = _coordinate(cell(edition, "Latitude (WGS-84)"), 90)
            longitude = _coordinate(cell(edition, "Longitude (WGS-84)"), 180)
            if latitude is None or longitude is None:
                continue
            result.append({"id": edition["id"], "label": edition["metadata"]["label"],
                "shape": "point", "coordinates": [[latitude, longitude]],
                "note": "Original published WGS-84 reference point, CSV record " + str(edition["ordinal"]) + ". "
                    + "Location note (source): " + (cell(edition, "Geospatial note") or "Not recorded")
                    + ". Obscured grid references and county centroids do not establish an exact site position. "
                    + "Underlying source accuracy or local coordinate systems do not determine the published point's precision."})
    elif record.get("source") == "dinosaurs" and original.get("kind") == "occ":
        source = original.get("source") or {}
        latitude, longitude = _coordinate(source.get("lat"), 90), _coordinate(source.get("lng"), 180)
        if latitude is not None and longitude is not None:
            qualifiers = [f"{label}: {source[key]}" for key, label in (
                ("latlng_basis", "Coordinate basis"), ("latlng_precision", "Coordinate precision"),
                ("geogscale", "Geographic scale"), ("geogcomments", "Location notes"),
                ("protected", "Source protection code")) if source.get(key) not in (None, "")]
            result.append({"id": "PBDB collection " + str(source.get("collection_no", "")),
                           "label": source.get("collection_name") or "Published fossil collection",
                           "shape": "point", "coordinates": [[latitude, longitude]],
                           "note": "Published modern collection coordinates. Precision is defined by the source. " + " · ".join(qualifiers)})
    elif record.get("source") == "field_assemblages" and original.get("dataset") in (
            "chengdu", "el-progreso", "giza-botany", "cixwicen-birds", "cixwicen-bird-sorting",
            "cixwicen-fish", "cixwicen-charcoal"):
        headers, values = original.get("headers", []), original.get("values", [])
        def cell(name):
            return values[headers.index(name)] if name in headers and headers.index(name) < len(values) else ""
        latitude, longitude = _coordinate(cell("Latitude (WGS-84)"), 90), _coordinate(cell("Longitude (WGS-84)"), 180)
        if latitude is not None and longitude is not None:
            inference = cell("Geospatial Inference")
            context = cell("Item Context URI") or cell("Context URI")
            note = "Original table's WGS-84 reference point. The table does not establish an individual artifact's measured position or coordinate precision."
            if original["dataset"].startswith("cixwicen-"):
                note += " The publisher's project location is deliberately coarsened. Repeated table points describe inherited site/context references, not surveyed find positions."
            if inference: note += " Geospatial inference (source): " + inference + "."
            if cell("Geospatial note"): note += " Geospatial note (source): " + cell("Geospatial note") + "."
            if context: note += " Original context: " + context
            result.append({"id": cell("Item URI") or cell("URI") or original.get("id", ""),
                           "label": cell("Item Label") or cell("Label") or original.get("site", "Published reference point"),
                           "shape": "point", "coordinates": [[latitude, longitude]], "note": note})
    return result


def geometry_points(geometry):
    """Validate complete source geometry; keep rings and multipart topology intact."""
    if not isinstance(geometry, dict):
        return []
    kind = geometry.get("type")
    depths = {"Point": 0, "MultiPoint": 1, "LineString": 1, "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}
    if kind == "GeometryCollection":
        children = geometry.get("geometries")
        if not isinstance(children, list) or not children:
            return []
        groups = [geometry_points(child) for child in children]
        return [point for group in groups for point in group] if all(groups) else []
    if kind not in depths:
        return []

    def walk(value, depth):
        if not isinstance(value, list) or not value:
            return None
        if depth:
            groups = [walk(item, depth - 1) for item in value]
            return [point for group in groups for point in group] if all(groups) else None
        if len(value) < 2:
            return None
        longitude, latitude = _coordinate(value[0], 180), _coordinate(value[1], 90)
        return [[latitude, longitude]] if longitude is not None and latitude is not None else None

    return walk(geometry.get("coordinates"), depths[kind]) or []


def display_geometry(geometry, offset):
    """Shift a display copy by whole world widths without changing native geometry."""
    kind = geometry["type"]
    if kind == "GeometryCollection":
        return {"type": kind, "geometries": [display_geometry(child, offset) for child in geometry["geometries"]]}

    def shift(value):
        if isinstance(value[0], list):
            return [shift(item) for item in value]
        return [float(value[0]) + offset, *[float(item) if item is not None else None for item in value[1:]]]

    return {"type": kind, "coordinates": shift(geometry["coordinates"])}


def frame(rows):
    """Frame nearby sites across the dateline without replacing an area by a pin."""
    if not rows:
        return [], None
    anchor = rows[0]["coordinates"][0][1]
    displayed = []
    for row in rows:
        west = row["coordinates"][0][1]
        offset = 360 * round((anchor - west) / 360)
        displayed.append({**row, "coordinates": [[lat, lon + offset] for lat, lon in row["coordinates"]],
                          **({"geometry": display_geometry(row["geometry"], offset)} if row["shape"] == "geojson" else {})})
    points = [point for row in displayed for point in row["coordinates"]]
    return displayed, [[min(point[0] for point in points), min(point[1] for point in points)],
                       [max(point[0] for point in points), max(point[1] for point in points)]]
