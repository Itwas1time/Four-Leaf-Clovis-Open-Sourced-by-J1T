"""
BLM Surface Management Agency land status collector.

Queries BLM's ArcGIS REST service for surface land ownership/management
and classifies parcels into federal, state, tribal, and private categories.

Archaeological rationale:
    Approximately 95% of US federal land has never been systematically
    surveyed for archaeological sites. Federal and tribal lands — managed by
    BLM, USFS, NPS, USFWS, and tribal nations — represent the largest pool
    of unsurveyed terrain. Conversely, private land is essentially invisible
    to systematic survey. Knowing land status tells us both where to look
    (unsurveyed federal land) and what permissions are needed.

Data source:
    - BLM Surface Management Agency (SMA) GIS layer
    - API: https://gis.blm.gov/arcgis/rest/services/lands (ArcGIS REST)
    - Coverage: All US states (best coverage in western states)
    - License: Public Domain (US Government)
    - Format: GeoJSON via ArcGIS Feature Service, stored as GeoPackage
    - Update frequency: Quarterly
    - Storage: ~5 MB per 1-degree tile
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx

from collectors.base import BaseCollector
from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)

BLM_SMA_URL = "https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_SMA_Cached_without_Wilderness/MapServer"

# Feature layer index for surface management agency polygons
SMA_LAYER_ID = 1

# Map agency codes to ownership categories
OWNERSHIP_CATEGORIES = {
    "federal": ["BLM", "USFS", "NPS", "USFWS", "DOD", "DOE", "BOR", "TVA", "USACE"],
    "tribal": ["BIA", "TRIBAL", "IR"],
    "state": ["STATE", "ST"],
}


def classify_ownership(admin_agency: str) -> str:
    """Classify a management agency string into a broad ownership category."""
    upper = (admin_agency or "").upper().strip()
    for category, codes in OWNERSHIP_CATEGORIES.items():
        if any(code in upper for code in codes):
            return category
    if upper in ("PVT", "PRIVATE", ""):
        return "private"
    return "other"


class LandStatusCollector(BaseCollector):
    """
    Collect surface land ownership/management polygons from BLM SMA.

    Queries the ArcGIS REST service in spatial pages, classifies each parcel
    by ownership category, and stores as GeoPackage. Large bboxes are split
    into sub-tiles to respect the service's 1000-feature query limit.
    """

    @property
    def name(self) -> str:
        return "land_status"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Probe the BLM SMA service for feature count in the bbox.

        The SMA layer covers all US states but has the most detailed
        parcel-level data in the western states where BLM manages large areas.
        """
        query_url = f"{BLM_SMA_URL}/{SMA_LAYER_ID}/query"
        envelope = f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}"
        params = {
            "geometry": envelope,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "returnCountOnly": "true",
            "f": "json",
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(query_url, params=params)
                response.raise_for_status()
                data = response.json()
                count = data.get("count", 0)
        except (httpx.HTTPError, Exception) as e:
            logger.warning("BLM SMA availability check failed: %s", e)
            return CoverageReport(
                layer_name=self.name,
                bbox=bbox,
                available=False,
                coverage_fraction=0.0,
                notes=f"Service unreachable: {e}",
            )

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=count > 0,
            coverage_fraction=1.0 if count > 0 else 0.0,
            tile_count=1,
            estimated_size_mb=max(1.0, count * 0.005),
            notes=f"BLM SMA reports {count} parcels in bbox",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download land ownership polygons for the bounding box.

        Queries in sub-tiles to stay under the 1000-feature limit per request.
        Classifies each parcel into federal/state/tribal/private. Supports
        checkpoint/resume at the sub-tile level.
        """
        output_dir = self.data_dir / "land_status"
        output_dir.mkdir(parents=True, exist_ok=True)
        bbox_slug = f"{bbox.min_lat:.2f}_{bbox.min_lon:.2f}_{bbox.max_lat:.2f}_{bbox.max_lon:.2f}"
        output_path = output_dir / f"land_status_{bbox_slug}.gpkg"

        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Land status data already collected for this bbox")
        else:
            self._download_land_status(bbox, output_path)
            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="land_status",
            source="BLM Surface Management Agency (SMA)",
            source_url=BLM_SMA_URL,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="gpkg",
            crs="EPSG:4326",
            metadata={
                "ownership_categories": ["federal", "state", "tribal", "private", "other"],
            },
        )

    def _download_land_status(self, bbox: BoundingBox, output_path: Path) -> None:
        """Query BLM SMA in sub-tiles and assemble classified GeoPackage."""
        sub_tiles = self._split_bbox(bbox, max_degrees=0.5)
        all_frames: list[gpd.GeoDataFrame] = []

        checkpoint = self._load_checkpoint(bbox) or {}
        completed_tiles = set(checkpoint.get("completed_tiles", []))

        with httpx.Client(timeout=120) as client:
            for i, tile in enumerate(sub_tiles):
                tile_key = f"{tile.min_lat:.4f}_{tile.min_lon:.4f}"
                if tile_key in completed_tiles:
                    logger.debug("Skipping already-collected tile %s", tile_key)
                    continue

                gdf = self._query_tile(client, tile)
                if gdf is not None and not gdf.empty:
                    gdf["ownership_category"] = gdf.get(
                        "ADMIN_AGENCY_CODE", gdf.get("admin_agency_code", "")
                    ).apply(classify_ownership)
                    all_frames.append(gdf)

                completed_tiles.add(tile_key)
                if (i + 1) % 10 == 0:
                    self._save_checkpoint(bbox, {
                        "completed_tiles": list(completed_tiles),
                        "complete": False,
                    })

        if all_frames:
            result = gpd.pd.concat(all_frames, ignore_index=True)
            result.to_file(output_path, driver="GPKG")
            logger.info("Land status saved: %d parcels to %s", len(result), output_path)
        else:
            empty = gpd.GeoDataFrame(
                columns=["geometry", "ownership_category"], crs="EPSG:4326"
            )
            empty.to_file(output_path, driver="GPKG")
            logger.info("No land status features found in bbox")

    def _query_tile(self, client: httpx.Client, tile: BoundingBox) -> gpd.GeoDataFrame | None:
        """Query a single sub-tile from the ArcGIS REST service."""
        query_url = f"{BLM_SMA_URL}/{SMA_LAYER_ID}/query"
        envelope = f"{tile.min_lon},{tile.min_lat},{tile.max_lon},{tile.max_lat}"
        params = {
            "geometry": envelope,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
        }

        try:
            response = client.get(query_url, params=params)
            response.raise_for_status()
            geojson = response.json()
            features = geojson.get("features", [])
            if not features:
                return None
            return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Failed to query tile %s: %s", tile, e)
            return None

    @staticmethod
    def _split_bbox(bbox: BoundingBox, max_degrees: float = 0.5) -> list[BoundingBox]:
        """Split a large bbox into sub-tiles to stay under feature query limits."""
        tiles: list[BoundingBox] = []
        lat = bbox.min_lat
        while lat < bbox.max_lat:
            lon = bbox.min_lon
            while lon < bbox.max_lon:
                tiles.append(BoundingBox(
                    min_lat=lat,
                    min_lon=lon,
                    max_lat=min(lat + max_degrees, bbox.max_lat),
                    max_lon=min(lon + max_degrees, bbox.max_lon),
                ))
                lon += max_degrees
            lat += max_degrees
        return tiles

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "BLM Surface Management Agency — Land Status",
            "source": "Bureau of Land Management",
            "url": "https://www.blm.gov/about/data",
            "api": BLM_SMA_URL,
            "license": "Public Domain (US Government work)",
            "coverage": "All US states (detailed parcel data in western states)",
            "format": "GeoPackage (from ArcGIS REST GeoJSON)",
            "crs": "EPSG:4326",
            "update_frequency": "Quarterly",
            "ownership_categories": {
                "federal": "BLM, USFS, NPS, USFWS, DOD, DOE, BOR, TVA, USACE",
                "tribal": "BIA-managed and tribal trust lands",
                "state": "State-managed public lands",
                "private": "Private ownership (minimal survey data available)",
            },
            "archaeological_rationale": (
                "Approximately 95% of US federal land has never been systematically "
                "surveyed for archaeological sites. Land status determines both where "
                "unknown sites are most likely to survive and what permissions are "
                "required for field investigation."
            ),
        }
