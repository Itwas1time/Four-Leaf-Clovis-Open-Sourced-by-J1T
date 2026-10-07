"""
USGS state geologic map data collector.

Queries the USGS State Geologic Map Compilation (SGMC) service for
lithology data, filtering for formations that create natural shelters:
limestone/dolomite (karst dissolution caves), sandstone (rockshelters
from differential erosion), and volcanic rock (lava tubes).

Archaeological rationale:
    Sheltered sites have the oldest dates in North America. Meadowcroft
    Rockshelter (sandstone, ~19,000 BP) and Paisley Caves (volcanic tuff,
    ~14,500 BP) demonstrate that geology determines where deep stratigraphy
    is preserved. Caves and rockshelters protect deposits from erosion,
    bioturbation, and plowing — they are time capsules. This layer identifies
    the geologic formations most likely to contain such shelters.

Data source:
    - USGS State Geologic Map Compilation (SGMC)
    - API: https://mrdata.usgs.gov/services/sgmc (WFS/WMS)
    - Coverage: Contiguous US, Alaska, Hawaii (variable detail by state)
    - License: Public Domain (US Government)
    - Format: GeoJSON via WFS, stored as GeoPackage
    - Update frequency: Irregular (state-by-state revisions)
    - Storage: ~10 MB per 1-degree tile (filtered)
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

SGMC_WFS_URL = "https://mrdata.usgs.gov/services/sgmc"

# Lithology keywords that indicate shelter-forming geology
KARST_KEYWORDS = ["limestone", "dolomite", "carbonate", "marble"]
SANDSTONE_KEYWORDS = ["sandstone", "quartzite", "arkose"]
VOLCANIC_KEYWORDS = ["basalt", "volcanic", "lava", "tuff", "rhyolite", "andesite"]

SHELTER_CATEGORIES = {
    "karst": KARST_KEYWORDS,
    "sandstone": SANDSTONE_KEYWORDS,
    "volcanic": VOLCANIC_KEYWORDS,
}


class GeologyCollector(BaseCollector):
    """
    Collect geologic map polygons filtered for shelter-forming lithologies.

    Queries the USGS SGMC WFS service, filters for limestone/dolomite
    (karst caves), sandstone (rockshelters), and volcanic rock (lava tubes).
    Stores results as a GeoPackage with a 'shelter_type' classification column.
    """

    @property
    def name(self) -> str:
        return "geology"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Check SGMC coverage for the bounding box.

        SGMC covers all US states, though detail and vintage vary by state.
        Probes the WFS to confirm the service is reachable and returns a
        feature count estimate.
        """
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "sgmc:SGMCGeologyPolys",
            "bbox": f"{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon},EPSG:4326",
            "resultType": "hits",
            "outputFormat": "application/json",
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(SGMC_WFS_URL, params=params)
                response.raise_for_status()
                data = response.json()
                total = data.get("numberMatched", data.get("totalFeatures", 0))
        except (httpx.HTTPError, Exception) as e:
            logger.warning("SGMC availability check failed: %s", e)
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
            available=total > 0,
            coverage_fraction=1.0 if total > 0 else 0.0,
            tile_count=1,
            estimated_size_mb=max(1.0, total * 0.002),
            notes=f"SGMC reports {total} geologic polygons in bbox",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download geologic polygons and filter for shelter-forming lithologies.

        Fetches features in pages of 1000 to stay memory-conscious, filters
        each page for target lithologies, and writes the filtered result as
        a GeoPackage. Supports checkpoint/resume.
        """
        output_dir = self.data_dir / "geology"
        output_dir.mkdir(parents=True, exist_ok=True)
        bbox_slug = f"{bbox.min_lat:.2f}_{bbox.min_lon:.2f}_{bbox.max_lat:.2f}_{bbox.max_lon:.2f}"
        output_path = output_dir / f"geology_shelters_{bbox_slug}.gpkg"

        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Geology data already collected for this bbox")
        else:
            self._download_and_filter(bbox, output_path)
            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="geology_shelters",
            source="USGS State Geologic Map Compilation (SGMC)",
            source_url=SGMC_WFS_URL,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="gpkg",
            crs="EPSG:4326",
            metadata={
                "filter": "shelter-forming lithologies only",
                "categories": list(SHELTER_CATEGORIES.keys()),
            },
        )

    def _download_and_filter(self, bbox: BoundingBox, output_path: Path) -> None:
        """Page through WFS results, filter for shelter lithologies, write GeoPackage."""
        page_size = 1000
        start_index = 0
        all_frames: list[gpd.GeoDataFrame] = []

        with httpx.Client(timeout=120) as client:
            while True:
                params = {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": "sgmc:SGMCGeologyPolys",
                    "bbox": f"{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon},EPSG:4326",
                    "outputFormat": "application/json",
                    "count": page_size,
                    "startIndex": start_index,
                }

                logger.info("Fetching geology features, offset %d", start_index)
                response = client.get(SGMC_WFS_URL, params=params)
                response.raise_for_status()

                geojson = response.json()
                features = geojson.get("features", [])
                if not features:
                    break

                gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
                filtered = self._filter_shelter_lithologies(gdf)

                if not filtered.empty:
                    all_frames.append(filtered)

                if len(features) < page_size:
                    break
                start_index += page_size

        if all_frames:
            result = gpd.pd.concat(all_frames, ignore_index=True)
            result.to_file(output_path, driver="GPKG")
            logger.info(
                "Geology shelters saved: %d features to %s",
                len(result),
                output_path,
            )
        else:
            # Write empty GeoPackage so downstream knows collection ran
            empty = gpd.GeoDataFrame(columns=["geometry", "shelter_type"], crs="EPSG:4326")
            empty.to_file(output_path, driver="GPKG")
            logger.info("No shelter-forming geology found in bbox")

    def _filter_shelter_lithologies(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Classify and filter features by shelter-forming lithology keywords."""
        if gdf.empty:
            return gdf

        # Find the lithology description column (varies by schema version)
        lith_col = None
        for candidate in ["lith_type", "lithology", "rocktype", "generalized_lith", "unit_name", "description"]:
            if candidate in gdf.columns:
                lith_col = candidate
                break

        if lith_col is None:
            # Fall back: search all string columns
            for col in gdf.select_dtypes(include=["object"]).columns:
                if col != "geometry":
                    lith_col = col
                    break

        if lith_col is None:
            logger.warning("No lithology column found in geology response")
            return gpd.GeoDataFrame(columns=gdf.columns.tolist() + ["shelter_type"], crs="EPSG:4326")

        shelter_types = []
        for value in gdf[lith_col].fillna("").str.lower():
            category = self._classify_lithology(value)
            shelter_types.append(category)

        gdf = gdf.copy()
        gdf["shelter_type"] = shelter_types
        return gdf[gdf["shelter_type"] != ""].copy()

    @staticmethod
    def _classify_lithology(text: str) -> str:
        """Return shelter category if text matches any keyword, else empty string."""
        for category, keywords in SHELTER_CATEGORIES.items():
            if any(kw in text for kw in keywords):
                return category
        return ""

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "USGS State Geologic Map Compilation — Shelter Lithologies",
            "source": "USGS Mineral Resources Data System",
            "url": "https://mrdata.usgs.gov/geology/state/",
            "api": SGMC_WFS_URL,
            "license": "Public Domain (US Government work)",
            "coverage": "Contiguous US, Alaska, Hawaii",
            "format": "GeoPackage (filtered from WFS GeoJSON)",
            "crs": "EPSG:4326",
            "filter_categories": {
                "karst": "Limestone, dolomite, carbonate — dissolution caves",
                "sandstone": "Sandstone, quartzite — differential erosion rockshelters",
                "volcanic": "Basalt, tuff, rhyolite — lava tubes and volcanic shelters",
            },
            "archaeological_rationale": (
                "Caves and rockshelters preserve the oldest stratified deposits "
                "in North America. Meadowcroft Rockshelter (sandstone) and Paisley "
                "Caves (volcanic tuff) demonstrate that geology determines where "
                "deep time is accessible. This layer maps shelter-forming bedrock."
            ),
        }
