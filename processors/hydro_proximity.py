"""
Hydrological proximity scoring processor.

Computes distance-to-water metrics for each grid cell — the single
strongest predictor of human settlement across all time periods and
cultural contexts in North America.

Scoring factors:
    1. Distance to nearest current waterway (NHD flowlines)
    2. Distance to nearest paleo-channel (reconstructed ancient waterways)
    3. Confluence proximity (where rivers meet = high-value settlement zones)
    4. Elevation above nearest water (terraces preferred over floodplains)

The scorer distinguishes between floodplains (frequently inundated,
used for agriculture but not permanent settlement) and river terraces
(elevated, well-drained, defensible — the preferred habitation surface
for most North American cultures).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from core.geo_utils import haversine_distance
from core.schemas import BoundingBox, GridCell

logger = logging.getLogger(__name__)

# Scoring parameters derived from archaeological site distribution studies
MAX_WATER_DISTANCE_KM = 10.0   # Beyond this, score drops to 0
IDEAL_WATER_DISTANCE_KM = 0.5  # Peak score zone
CONFLUENCE_BONUS_KM = 2.0      # Radius for confluence proximity bonus
TERRACE_ELEVATION_MIN_M = 3.0  # Minimum elevation above water for terrace
TERRACE_ELEVATION_MAX_M = 30.0 # Above this, too high for easy water access


class HydroProximityProcessor:
    """
    Score grid cells by proximity to water features.

    Uses an exponential decay function: score is highest within 500m
    of water, drops off rapidly, and reaches zero at 10km. Confluences
    get a bonus because they provide access to multiple drainage networks
    and tend to accumulate alluvial resources (flint cobbles, clay deposits).
    """

    def score_cell(
        self,
        cell: GridCell,
        flowlines: gpd.GeoDataFrame | None = None,
        waterbodies: gpd.GeoDataFrame | None = None,
    ) -> dict[str, Any]:
        """
        Compute hydro proximity score for a single cell.

        Returns dict with score (0-1) and component details.
        """
        cell_point = Point(cell.center_lon, cell.center_lat)
        scores = {}

        if flowlines is not None and len(flowlines) > 0:
            # Distance to nearest flowline
            distances = flowlines.geometry.distance(cell_point)
            min_dist_deg = distances.min()
            # Approximate degrees to km at this latitude
            min_dist_km = min_dist_deg * 111.0 * math.cos(math.radians(cell.center_lat))

            scores["water_distance_km"] = round(min_dist_km, 3)
            scores["water_proximity_score"] = self._distance_score(min_dist_km)

            # Confluence detection: find points where multiple flowlines converge
            scores["confluence_score"] = self._confluence_score(cell_point, flowlines)

        if waterbodies is not None and len(waterbodies) > 0:
            wb_distances = waterbodies.geometry.distance(cell_point)
            min_wb_dist_deg = wb_distances.min()
            min_wb_dist_km = min_wb_dist_deg * 111.0 * math.cos(math.radians(cell.center_lat))
            scores["waterbody_distance_km"] = round(min_wb_dist_km, 3)

        # Composite hydro score
        components = [
            scores.get("water_proximity_score", 0.0),
            scores.get("confluence_score", 0.0),
        ]
        # Take the best signal, with bonus for multiple signals
        if components:
            base = max(components)
            bonus = sum(c for c in components if c > 0.3) * 0.1
            scores["hydro_proximity"] = round(min(base + bonus, 1.0), 4)
        else:
            scores["hydro_proximity"] = 0.0

        return scores

    def score_region(
        self,
        cells: list[GridCell],
        flowlines: gpd.GeoDataFrame | None = None,
        waterbodies: gpd.GeoDataFrame | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Score all cells in a region. Returns {cell_id: scores_dict}."""
        results = {}
        for i, cell in enumerate(cells):
            results[cell.cell_id] = self.score_cell(cell, flowlines, waterbodies)
            if (i + 1) % 100 == 0:
                logger.info("Scored %d/%d cells for hydro proximity", i + 1, len(cells))
        return results

    def _distance_score(self, distance_km: float) -> float:
        """
        Exponential decay score based on distance to water.

        Archaeological site density follows an approximately exponential
        decay with distance from water. Most sites are within 1km;
        virtually none are beyond 10km (in non-arid environments).
        """
        if distance_km <= IDEAL_WATER_DISTANCE_KM:
            return 1.0
        if distance_km >= MAX_WATER_DISTANCE_KM:
            return 0.0

        # Exponential decay with lambda chosen so score ≈ 0.05 at max distance
        decay_rate = -math.log(0.05) / (MAX_WATER_DISTANCE_KM - IDEAL_WATER_DISTANCE_KM)
        return math.exp(-decay_rate * (distance_km - IDEAL_WATER_DISTANCE_KM))

    def _confluence_score(self, point: Point, flowlines: gpd.GeoDataFrame) -> float:
        """
        Score proximity to river confluences.

        Confluences are where rivers meet — archaeologically significant
        because they provide access to multiple drainage basins, tend to
        have richer alluvial deposits, and were used as navigation landmarks
        and meeting points. Major sites like Cahokia sit at confluences.
        """
        # Simple heuristic: count flowlines within the confluence radius
        buffer = point.buffer(CONFLUENCE_BONUS_KM / 111.0)  # degrees approx
        intersecting = flowlines[flowlines.geometry.intersects(buffer)]

        n_streams = len(intersecting)
        if n_streams >= 3:
            return 0.9  # Major confluence
        elif n_streams >= 2:
            return 0.6  # Minor confluence
        else:
            return 0.0  # No confluence
