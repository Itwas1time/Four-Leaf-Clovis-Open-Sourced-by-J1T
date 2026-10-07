"""
H3 hexagonal grid system for spatial analysis.

H3 hexagons are used because they tessellate uniformly — unlike square grids,
every cell has the same number of neighbors at the same distance. This eliminates
directional bias in spatial analysis (a critical property when detecting
isotropic features like settlement catchment areas).

Resolution reference:
  Res 7 ≈ 5.16 km² — regional survey planning
  Res 8 ≈ 0.74 km² — field survey unit (default)
  Res 9 ≈ 0.10 km² — high-resolution analysis where LiDAR is available
"""

from __future__ import annotations

import h3

from core.schemas import BoundingBox, GridCell


# Average H3 cell areas in km² by resolution
H3_AREAS_KM2: dict[int, float] = {
    0: 4_357_449.416,
    1: 609_788.441,
    2: 86_801.780,
    3: 12_393.434,
    4: 1_770.348,
    5: 252.903,
    6: 36.129,
    7: 5.161,
    8: 0.737,
    9: 0.105,
    10: 0.015,
    11: 0.002,
    12: 0.0003,
    13: 0.00004,
    14: 0.000006,
    15: 0.0000009,
}


def cells_in_bbox(bbox: BoundingBox, resolution: int = 8) -> list[GridCell]:
    """
    Generate all H3 cells that intersect a bounding box.

    This is the primary method for dividing a study area into analyzable
    units. Each returned cell becomes a row in the scoring matrix.

    Args:
        bbox: Area of interest.
        resolution: H3 resolution level (7=regional, 8=survey, 9=detailed).

    Returns:
        List of GridCell objects covering the bounding box.
    """
    if resolution < 0 or resolution > 15:
        raise ValueError(f"H3 resolution must be 0-15, got {resolution}")

    # Define the bounding polygon as a GeoJSON-style ring
    # H3 expects vertices as (lat, lng) tuples in counter-clockwise order
    polygon_vertices = [
        (bbox.min_lat, bbox.min_lon),
        (bbox.min_lat, bbox.max_lon),
        (bbox.max_lat, bbox.max_lon),
        (bbox.max_lat, bbox.min_lon),
    ]

    # Get all H3 cells whose centers fall within the polygon
    cell_ids = h3.polygon_to_cells(
        h3.LatLngPoly(polygon_vertices),
        resolution,
    )

    area_km2 = H3_AREAS_KM2.get(resolution, 1.0)

    cells = []
    for cell_id in cell_ids:
        lat, lon = h3.cell_to_latlng(cell_id)
        cells.append(GridCell(
            cell_id=cell_id,
            resolution=resolution,
            center_lat=lat,
            center_lon=lon,
            area_km2=area_km2,
        ))

    return cells


def cell_neighbors(cell_id: str) -> list[str]:
    """
    Get the immediate neighbors of an H3 cell (k-ring with k=1).

    Neighbor analysis is critical for the convergence scorer: an isolated
    high-scoring cell is less significant than a cluster of high-scoring
    neighbors (spatial autocorrelation of archaeological potential).
    """
    # grid_disk returns the cell itself plus its neighbors
    ring = h3.grid_disk(cell_id, 1)
    return [c for c in ring if c != cell_id]


def cell_to_geojson(cell_id: str) -> dict:
    """
    Convert an H3 cell to a GeoJSON Feature.

    Used for visualization in the atlas map and for spatial joins
    with other vector data layers.
    """
    boundary = h3.cell_to_boundary(cell_id)
    lat, lon = h3.cell_to_latlng(cell_id)
    resolution = h3.get_resolution(cell_id)

    # H3 returns boundary as list of (lat, lng) — GeoJSON needs (lng, lat)
    coordinates = [[lng, lat] for lat, lng in boundary]
    # Close the ring
    coordinates.append(coordinates[0])

    return {
        "type": "Feature",
        "properties": {
            "cell_id": cell_id,
            "resolution": resolution,
            "center_lat": lat,
            "center_lon": lon,
            "area_km2": H3_AREAS_KM2.get(resolution, 0),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coordinates],
        },
    }


def cells_to_geojson(cells: list[GridCell]) -> dict:
    """Convert a list of GridCells to a GeoJSON FeatureCollection."""
    features = [cell_to_geojson(cell.cell_id) for cell in cells]
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def cell_contains_point(cell_id: str, lat: float, lon: float) -> bool:
    """Check if a point falls within an H3 cell."""
    point_cell = h3.latlng_to_cell(lat, lon, h3.get_resolution(cell_id))
    return point_cell == cell_id


def point_to_cell(lat: float, lon: float, resolution: int = 8) -> str:
    """Get the H3 cell containing a point."""
    return h3.latlng_to_cell(lat, lon, resolution)


def compact_cells(cell_ids: list[str]) -> list[str]:
    """
    Compact a set of H3 cells to the most efficient representation.

    When a full set of child cells is present, replace with the parent cell.
    Useful for efficient storage and faster spatial queries on large regions.
    """
    return list(h3.compact_cells(cell_ids))


def estimate_cell_count(bbox: BoundingBox, resolution: int = 8) -> int:
    """
    Estimate how many cells a bounding box will produce at a given resolution.

    Useful for progress bars and memory budgeting before committing to
    a full grid generation.
    """
    from core.geo_utils import bbox_area_km2
    area = bbox_area_km2(bbox)
    cell_area = H3_AREAS_KM2.get(resolution, 1.0)
    return max(1, int(area / cell_area))
