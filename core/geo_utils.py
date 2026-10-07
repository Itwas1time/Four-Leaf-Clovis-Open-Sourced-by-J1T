"""
Geographic utility functions for ARCHAEO-SCAN.

All internal coordinates are EPSG:4326 (WGS84). Source data arrives in
various CRS projections — these helpers normalize everything to a common
reference frame and provide distance/area calculations.
"""

from __future__ import annotations

import math

from pyproj import CRS, Transformer
from shapely.geometry import box, Point, Polygon
from shapely.ops import transform as shapely_transform

from core.schemas import BoundingBox

# Continental US bounding box — used to validate coordinates
US_BOUNDS = BoundingBox(
    min_lat=24.396308,
    min_lon=-125.0,
    max_lat=49.384358,
    max_lon=-66.93457,
)

# Include Alaska and Hawaii for completeness
US_BOUNDS_FULL = BoundingBox(
    min_lat=18.9,    # Hawaii
    min_lon=-179.15,  # Alaska (Aleutians cross antimeridian)
    max_lat=71.39,   # Alaska
    max_lon=-66.93,
)

# Earth radius in km
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Fast distance estimate in kilometers using the Haversine formula.

    Accurate to ~0.3% for distances under 1000km — more than sufficient
    for proximity scoring. Use geodesic_distance() when sub-meter precision matters.
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def geodesic_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Precise geodesic distance in kilometers using Vincenty's formula via pyproj.

    Use this when accuracy matters (e.g., converting historical travel-time
    references to distances: "three days' march" needs a reliable baseline).
    """
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    _, _, distance_m = geod.inv(lon1, lat1, lon2, lat2)
    return distance_m / 1000.0


def is_in_us(lat: float, lon: float, continental_only: bool = True) -> bool:
    """Check if a point falls within US boundaries."""
    bounds = US_BOUNDS if continental_only else US_BOUNDS_FULL
    return bounds.contains_point(lat, lon)


def bbox_to_polygon(bbox: BoundingBox) -> Polygon:
    """Convert a BoundingBox to a Shapely polygon."""
    return box(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat)


def polygon_to_bbox(polygon: Polygon) -> BoundingBox:
    """Extract bounding box from a Shapely polygon."""
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    return BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)


def get_transformer(from_crs: str, to_crs: str) -> Transformer:
    """
    Create a coordinate transformer between two CRS.

    Many source datasets arrive in projected CRS (UTM zones, state plane).
    This normalizes everything to WGS84 for internal storage, or projects
    to local CRS when metric area/distance calculations are needed.
    """
    return Transformer.from_crs(
        CRS(from_crs),
        CRS(to_crs),
        always_xy=True,
    )


def reproject_bbox(bbox: BoundingBox, from_crs: str, to_crs: str) -> BoundingBox:
    """Reproject a bounding box from one CRS to another."""
    transformer = get_transformer(from_crs, to_crs)
    min_x, min_y = transformer.transform(bbox.min_lon, bbox.min_lat)
    max_x, max_y = transformer.transform(bbox.max_lon, bbox.max_lat)
    return BoundingBox(
        min_lat=min_y, min_lon=min_x,
        max_lat=max_y, max_lon=max_x,
    )


def reproject_geometry(geom: Polygon, from_crs: str, to_crs: str) -> Polygon:
    """Reproject a Shapely geometry from one CRS to another."""
    transformer = get_transformer(from_crs, to_crs)
    return shapely_transform(transformer.transform, geom)


def bbox_area_km2(bbox: BoundingBox) -> float:
    """
    Approximate area of a bounding box in square kilometers.

    Uses a local equal-area projection for accuracy. Important for
    estimating data download sizes and processing time.
    """
    center_lat = bbox.center_lat
    center_lon = bbox.center_lon

    # Use a transverse Mercator centered on the bbox for local accuracy
    local_crs = f"+proj=tmerc +lat_0={center_lat} +lon_0={center_lon} +datum=WGS84 +units=m"
    transformer = get_transformer("EPSG:4326", local_crs)

    min_x, min_y = transformer.transform(bbox.min_lon, bbox.min_lat)
    max_x, max_y = transformer.transform(bbox.max_lon, bbox.max_lat)

    width_km = abs(max_x - min_x) / 1000.0
    height_km = abs(max_y - min_y) / 1000.0

    return width_km * height_km


def obfuscate_point(lat: float, lon: float, precision_km: float = 1.0) -> tuple[float, float]:
    """
    Round coordinates to protect site locations from looting.

    Archaeological sites are vulnerable to unauthorized excavation.
    Public-facing outputs should obfuscate precise locations while
    keeping enough precision for regional analysis.
    """
    if not all(math.isfinite(value) for value in (lat, lon, precision_km)) or not (-90 <= lat <= 90 and -180 <= lon <= 180) or not 0 < precision_km <= 100:
        raise ValueError("Use finite coordinates and a rounding precision between 0 and 100 km.")
    # Longitude spacing must depend on the public latitude bucket. Using the
    # raw latitude here lets a recipient infer it from the rounded longitude.
    lat_precision = precision_km * 0.009
    obf_lat = max(-90, min(90, round(lat / lat_precision) * lat_precision))
    if abs(obf_lat) >= 89.99:
        obf_lon = 0.0
    else:
        lon_precision = precision_km * 0.009 / math.cos(math.radians(obf_lat))
        obf_lon = max(-180, min(180, round(lon / lon_precision) * lon_precision))

    return (round(obf_lat, 4), round(obf_lon, 4))


def estimate_travel_distance_km(
    days: float,
    mode: str = "foot",
    terrain: str = "mixed",
) -> float:
    """
    Estimate travel distance from historical time references.

    Historical documents often describe locations as "N days' travel from X."
    These rough conversions help the NLP reference resolver geocode such
    references. Based on ethnographic and experimental archaeology data.

    These are CENTER estimates — actual distances have wide error bars
    that the confidence scorer accounts for.
    """
    # km per day estimates from ethnographic/experimental data
    daily_rates = {
        ("foot", "flat"): 35.0,       # Open terrain, unladen
        ("foot", "mixed"): 25.0,      # Varied terrain, typical load
        ("foot", "mountain"): 15.0,   # Steep terrain
        ("foot", "forest"): 20.0,     # Dense vegetation
        ("canoe", "downstream"): 50.0,
        ("canoe", "upstream"): 20.0,
        ("canoe", "lake"): 30.0,
        ("horse", "flat"): 50.0,      # Post-contact only
        ("horse", "mixed"): 35.0,
    }

    rate = daily_rates.get((mode, terrain), 25.0)
    return days * rate
