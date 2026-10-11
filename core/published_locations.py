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
    if record.get("source") == "environments":
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


def frame(rows):
    """Frame nearby sites across the dateline without replacing an area by a pin."""
    if not rows:
        return [], None
    anchor = rows[0]["coordinates"][0][1]
    displayed = []
    for row in rows:
        west = row["coordinates"][0][1]
        offset = 360 * round((anchor - west) / 360)
        displayed.append({**row, "coordinates": [[lat, lon + offset] for lat, lon in row["coordinates"]]})
    points = [point for row in displayed for point in row["coordinates"]]
    return displayed, [[min(point[0] for point in points), min(point[1] for point in points)],
                       [max(point[0] for point in points), max(point[1] for point in points)]]
