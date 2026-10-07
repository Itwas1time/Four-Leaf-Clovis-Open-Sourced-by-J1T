"""
SRTM/DEM terrain elevation data collector.

Downloads 30-meter resolution digital elevation model (DEM) tiles from
USGS/OpenTopography. This is the simplest collector and establishes the
pattern for all others.

Archaeological rationale:
    Elevation and slope are fundamental to settlement prediction. Humans
    preferentially occupied terraces above floodplains, flat areas on slopes
    (artificial platforms), and locations with strategic viewsheds. The DEM
    is also the input for terrain anomaly detection (mounds, depressions,
    linear features) — the most direct remote indicator of human earthworks.

Data source:
    - SRTM 30m (Shuttle Radar Topography Mission)
    - Available via OpenTopography API or USGS EarthExplorer
    - Coverage: global between 60°N and 56°S
    - License: Public Domain (US Government)
    - Format: GeoTIFF, EPSG:4326
    - Update frequency: Static (collected February 2000)
    - Storage: ~25 MB per 1° x 1° tile
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from collectors.base import BaseCollector
from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)

# OpenTopography SRTM Global endpoint
OPENTOPO_API = "https://portal.opentopography.org/API/globaldem"


class TerrainCollector(BaseCollector):
    """
    Collect SRTM 30m DEM tiles for a bounding box.

    Downloads elevation data tile-by-tile, stores as GeoTIFF.
    Supports incremental collection — skips tiles already downloaded.
    """

    @property
    def name(self) -> str:
        return "terrain"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        SRTM has near-global coverage (60°N to 56°S).
        Check if the bbox falls within coverage and estimate download size.
        """
        # SRTM coverage check
        in_coverage = bbox.min_lat >= -56.0 and bbox.max_lat <= 60.0

        if not in_coverage:
            return CoverageReport(
                layer_name=self.name,
                bbox=bbox,
                available=False,
                coverage_fraction=0.0,
                notes="SRTM coverage is limited to 60°N - 56°S",
            )

        # Estimate tiles needed (1° x 1° tiles)
        lat_tiles = int(bbox.max_lat - bbox.min_lat) + 1
        lon_tiles = int(bbox.max_lon - bbox.min_lon) + 1
        tile_count = lat_tiles * lon_tiles

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=True,
            coverage_fraction=1.0,
            tile_count=tile_count,
            estimated_size_mb=tile_count * 25.0,
            notes="SRTM 30m full coverage available",
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download SRTM 30m DEM for the given bounding box.

        Uses the OpenTopography API for direct bbox-based downloads.
        Falls back to tile-by-tile if the area is too large.
        """
        output_dir = self.data_dir / "terrain"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"srtm_{bbox.min_lat:.2f}_{bbox.min_lon:.2f}_{bbox.max_lat:.2f}_{bbox.max_lon:.2f}.tif"

        # Check checkpoint
        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Terrain data already collected for this bbox")
        else:
            self._download_srtm(bbox, output_path)
            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="terrain_dem",
            source="SRTM 30m (Shuttle Radar Topography Mission)",
            source_url=OPENTOPO_API,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="tif",
            crs="EPSG:4326",
            metadata={
                "resolution_m": 30,
                "vertical_datum": "EGM96",
                "collection_date": "2000-02",
            },
        )

    def _download_srtm(self, bbox: BoundingBox, output_path: Path) -> None:
        """Download SRTM data from OpenTopography API."""
        params = {
            "demtype": "SRTMGL1",
            "south": bbox.min_lat,
            "north": bbox.max_lat,
            "west": bbox.min_lon,
            "east": bbox.max_lon,
            "outputFormat": "GTiff",
        }

        logger.info("Downloading SRTM DEM for bbox: %s", bbox)

        with httpx.Client(timeout=300) as client:
            response = client.get(OPENTOPO_API, params=params)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info("SRTM DEM saved to %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "SRTM 30m Digital Elevation Model",
            "source": "NASA / USGS",
            "url": "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1",
            "license": "Public Domain",
            "resolution": "30 meters (1 arc-second)",
            "coverage": "Global, 60°N to 56°S",
            "format": "GeoTIFF",
            "crs": "EPSG:4326",
            "update_frequency": "Static (February 2000 collection)",
            "storage_per_tile": "~25 MB per 1° x 1° tile",
            "archaeological_rationale": (
                "Elevation and slope are fundamental to settlement prediction. "
                "The DEM is the input for terrain anomaly detection — mounds, "
                "depressions, platforms, and linear features that indicate "
                "human earthworks."
            ),
        }
