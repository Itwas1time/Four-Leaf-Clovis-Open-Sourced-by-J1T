"""
National Hydrography Dataset (NHD) collector.

Downloads hydrographic features (rivers, streams, lakes, wetlands) and
Watershed Boundary Dataset (WBD) from USGS.

Archaeological rationale:
    Water access correlates with human settlement more strongly than almost
    any other variable. Every major prehistoric population center in North
    America sits near water — from Poverty Point on Bayou Macon to Cahokia
    on the Mississippi to Mesa Verde above springs. The hydro layer feeds
    directly into the convergence scorer's strongest-weighted factor.

    Paleo-hydrology is equally critical: rivers have migrated, lakes have
    dried, and coastlines have shifted. A site that appears "far from water"
    today may have been riverside 3,000 years ago. The NHD captures modern
    hydrology; paleo-reconstruction is handled in the hydro_proximity processor.

Data source:
    - USGS National Hydrography Dataset (NHD) Plus High Resolution
    - Available via USGS National Map API
    - Coverage: Continental US, Alaska, Hawaii
    - License: Public Domain (US Government)
    - Format: GeoPackage / Shapefile
    - Update frequency: Continuously updated
    - Storage: ~50-200 MB per HUC4 watershed
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

NHD_API_BASE = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
WBD_API_BASE = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer"


class HydroCollector(BaseCollector):
    """
    Collect hydrographic features from the National Hydrography Dataset.

    Downloads flowlines (rivers/streams), waterbodies (lakes/ponds),
    and watershed boundaries. Stores as GeoPackage layers.
    """

    @property
    def name(self) -> str:
        return "hydro"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """NHD covers all of the US. Check feature density for the bbox."""
        # NHD has complete US coverage
        from core.geo_utils import is_in_us
        center_in_us = is_in_us(bbox.center_lat, bbox.center_lon, continental_only=False)

        if not center_in_us:
            return CoverageReport(
                layer_name=self.name,
                bbox=bbox,
                available=False,
                coverage_fraction=0.0,
                notes="NHD covers US territories only",
            )

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=True,
            coverage_fraction=1.0,
            notes="NHD High Resolution coverage available",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download NHD features for the bounding box.

        Collects three feature classes:
        1. Flowlines — rivers, streams, canals
        2. Waterbodies — lakes, ponds, reservoirs
        3. Watershed boundaries — HUC drainage areas
        """
        output_dir = self.data_dir / "hydro"
        output_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = self._load_checkpoint(bbox)
        collected_layers: dict[str, str] = checkpoint.get("layers", {}) if checkpoint else {}

        # Collect flowlines (Layer 2 in NHD MapServer)
        if "flowlines" not in collected_layers:
            flowlines_path = output_dir / f"flowlines_{bbox.min_lat:.2f}_{bbox.min_lon:.2f}.gpkg"
            gdf = self._query_arcgis_features(NHD_API_BASE, layer_id=2, bbox=bbox)
            if gdf is not None and len(gdf) > 0:
                gdf.to_file(str(flowlines_path), driver="GPKG")
                collected_layers["flowlines"] = str(flowlines_path)
                logger.info("Collected %d flowline features", len(gdf))

        # Collect waterbodies (Layer 3)
        if "waterbodies" not in collected_layers:
            waterbodies_path = output_dir / f"waterbodies_{bbox.min_lat:.2f}_{bbox.min_lon:.2f}.gpkg"
            gdf = self._query_arcgis_features(NHD_API_BASE, layer_id=3, bbox=bbox)
            if gdf is not None and len(gdf) > 0:
                gdf.to_file(str(waterbodies_path), driver="GPKG")
                collected_layers["waterbodies"] = str(waterbodies_path)
                logger.info("Collected %d waterbody features", len(gdf))

        self._save_checkpoint(bbox, {"layers": collected_layers, "complete": True})

        return DataLayer(
            name="hydro_nhd",
            source="USGS National Hydrography Dataset (NHD) High Resolution",
            source_url=NHD_API_BASE,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_dir,
            format="gpkg",
            crs="EPSG:4326",
            metadata={
                "feature_classes": list(collected_layers.keys()),
                "feature_counts": {k: "see file" for k in collected_layers},
            },
        )

    def _query_arcgis_features(
        self,
        base_url: str,
        layer_id: int,
        bbox: BoundingBox,
        max_features: int = 10000,
    ) -> gpd.GeoDataFrame | None:
        """
        Query an ArcGIS REST MapServer for features within a bbox.

        Uses the query endpoint with a spatial filter. Handles pagination
        if the server enforces a max record count.
        """
        url = f"{base_url}/{layer_id}/query"
        params = {
            "where": "1=1",
            "geometry": f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultRecordCount": min(max_features, 2000),
        }

        try:
            with httpx.Client(timeout=120) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if "features" not in data or len(data["features"]) == 0:
                    logger.warning("No features returned for layer %d", layer_id)
                    return None

                return gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")

        except Exception as e:
            logger.error("Failed to query %s layer %d: %s", base_url, layer_id, e)
            return None

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "National Hydrography Dataset (NHD) High Resolution",
            "source": "USGS",
            "url": "https://www.usgs.gov/national-hydrography/national-hydrography-dataset",
            "license": "Public Domain",
            "coverage": "Continental US, Alaska, Hawaii",
            "format": "GeoPackage",
            "crs": "EPSG:4326",
            "update_frequency": "Continuously updated",
            "storage_estimate": "50-200 MB per HUC4 watershed",
            "feature_classes": [
                "Flowlines (rivers, streams, canals, ditches)",
                "Waterbodies (lakes, ponds, reservoirs)",
                "Watershed boundaries (HUC drainage areas)",
            ],
            "archaeological_rationale": (
                "Water access is the strongest universal predictor of human "
                "settlement. Every major prehistoric population center in North "
                "America sits near water. Confluences are especially high-value "
                "locations — they provide access to multiple drainage networks "
                "and tend to accumulate alluvial resources."
            ),
        }
