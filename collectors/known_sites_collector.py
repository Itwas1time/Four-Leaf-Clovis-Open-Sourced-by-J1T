"""
Known archaeological sites collector (NRHP + SHPO).

Queries the National Register of Historic Places (NRHP) ArcGIS service
for listed archaeological sites. This is TRAINING DATA for the scoring
model — known sites establish ground truth for what environmental
convergence patterns actually correspond to real sites.

Archaeological rationale:
    The NRHP lists ~95,000 properties, of which roughly 25% are significant
    for archaeological value. These known sites are not the goal — they are
    the training signal. By overlaying known site locations with environmental
    layers (terrain, hydro, soils, geology), the scoring model learns what
    combinations of features predict site presence. This enables discovery
    of UNKNOWN sites with similar environmental signatures.

Data source:
    - National Register of Historic Places (NPS/NRHP)
    - API: https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services
    - Coverage: All US states and territories
    - License: Public Domain (US Government)
    - Format: GeoJSON via ArcGIS Feature Service, stored as GeoPackage
    - Update frequency: Weekly
    - Storage: ~2 MB per state
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

# NRHP ArcGIS Feature Service
NRHP_BASE_URL = "https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services"
NRHP_LAYER_URL = f"{NRHP_BASE_URL}/NRHP_Status/FeatureServer/0"

# Resource types that indicate archaeological significance
ARCHAEOLOGICAL_RESOURCE_TYPES = {"site", "district", "structure"}


class KnownSitesCollector(BaseCollector):
    """
    Collect known archaeological sites from NRHP for model training.

    Downloads all NRHP-listed properties in the bbox that have
    archaeological significance, storing them as point features in a
    GeoPackage. These serve as positive training examples for the
    convergence scoring model.
    """

    @property
    def name(self) -> str:
        return "known_sites"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Check how many NRHP sites exist in the bounding box.

        NRHP coverage spans all US states, but listed sites are
        concentrated in areas with active SHPO programs and development
        pressure (Section 106 compliance).
        """
        query_url = f"{NRHP_LAYER_URL}/query"
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
            logger.warning("NRHP availability check failed: %s", e)
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
            estimated_size_mb=max(0.1, count * 0.001),
            notes=f"NRHP reports {count} listed properties in bbox",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download NRHP sites for the bounding box.

        Pages through the ArcGIS Feature Service in batches of 1000,
        filters for archaeologically significant resource types, and
        writes to GeoPackage. Supports checkpoint/resume.
        """
        output_dir = self.data_dir / "known_sites"
        output_dir.mkdir(parents=True, exist_ok=True)
        bbox_slug = f"{bbox.min_lat:.2f}_{bbox.min_lon:.2f}_{bbox.max_lat:.2f}_{bbox.max_lon:.2f}"
        output_path = output_dir / f"nrhp_sites_{bbox_slug}.gpkg"

        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Known sites data already collected for this bbox")
        else:
            self._download_nrhp_sites(bbox, output_path)
            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="known_sites_nrhp",
            source="National Register of Historic Places (NPS)",
            source_url=NRHP_LAYER_URL,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="gpkg",
            crs="EPSG:4326",
            metadata={
                "use": "training_data",
                "resource_types_included": list(ARCHAEOLOGICAL_RESOURCE_TYPES),
            },
        )

    def _download_nrhp_sites(self, bbox: BoundingBox, output_path: Path) -> None:
        """Page through NRHP Feature Service and collect archaeological sites."""
        query_url = f"{NRHP_LAYER_URL}/query"
        envelope = f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}"
        page_size = 1000
        offset = 0
        all_frames: list[gpd.GeoDataFrame] = []

        checkpoint = self._load_checkpoint(bbox) or {}
        offset = checkpoint.get("last_offset", 0)

        with httpx.Client(timeout=120) as client:
            while True:
                params = {
                    "geometry": envelope,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "outSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "resultOffset": offset,
                    "resultRecordCount": page_size,
                    "f": "geojson",
                }

                logger.info("Fetching NRHP sites, offset %d", offset)
                response = client.get(query_url, params=params)
                response.raise_for_status()

                geojson = response.json()
                features = geojson.get("features", [])
                if not features:
                    break

                gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
                filtered = self._filter_archaeological(gdf)

                if not filtered.empty:
                    all_frames.append(filtered)

                offset += len(features)

                # Save progress checkpoint
                self._save_checkpoint(bbox, {
                    "last_offset": offset,
                    "complete": False,
                })

                if len(features) < page_size:
                    break

        if all_frames:
            result = gpd.pd.concat(all_frames, ignore_index=True)
            result.to_file(output_path, driver="GPKG")
            logger.info("Known sites saved: %d sites to %s", len(result), output_path)
        else:
            empty = gpd.GeoDataFrame(columns=["geometry", "resource_type"], crs="EPSG:4326")
            empty.to_file(output_path, driver="GPKG")
            logger.info("No NRHP archaeological sites found in bbox")

    @staticmethod
    def _filter_archaeological(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Filter for features with archaeological significance."""
        if gdf.empty:
            return gdf

        # Try standard NRHP columns for resource type
        type_col = None
        for candidate in ["ResourceType", "resource_type", "ResType", "RESTYPE"]:
            if candidate in gdf.columns:
                type_col = candidate
                break

        if type_col is not None:
            mask = gdf[type_col].fillna("").str.lower().isin(ARCHAEOLOGICAL_RESOURCE_TYPES)
            return gdf[mask].copy()

        # If no resource type column, check for significance criteria
        for candidate in ["AreaOfSignificance", "area_of_significance", "Significance"]:
            if candidate in gdf.columns:
                mask = gdf[candidate].fillna("").str.lower().str.contains(
                    "archeo|archaeo|prehist", regex=True
                )
                return gdf[mask].copy()

        # If we cannot filter, return all — better noisy than empty
        logger.warning("No resource type column found; returning all NRHP features")
        return gdf

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "National Register of Historic Places — Archaeological Sites",
            "source": "National Park Service / NRHP",
            "url": "https://www.nps.gov/subjects/nationalregister/database-research.htm",
            "api": NRHP_LAYER_URL,
            "license": "Public Domain (US Government work)",
            "coverage": "All US states and territories",
            "format": "GeoPackage (from ArcGIS REST GeoJSON)",
            "crs": "EPSG:4326",
            "update_frequency": "Weekly",
            "use": "Training data for convergence scoring model",
            "archaeological_rationale": (
                "Known sites establish the ground truth for predictive modeling. "
                "By analyzing the environmental characteristics of NRHP-listed "
                "archaeological sites, the model learns what convergence patterns "
                "correspond to real sites and can then identify areas with similar "
                "signatures that have never been surveyed."
            ),
        }
