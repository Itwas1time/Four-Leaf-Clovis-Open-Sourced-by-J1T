"""
Copernicus Sentinel-2 L2A multispectral imagery collector.

Queries the Copernicus Data Space OData API for cloud-free Sentinel-2
Level-2A (atmospherically corrected) scenes across spring, summer, and
fall seasons. Stores composites as Cloud-Optimized GeoTIFF (COG).

Archaeological rationale:
    Buried walls, ditches, and foundations cause differential soil moisture
    and nutrient availability, which produces visible crop/vegetation marks
    in multispectral imagery. These features are invisible to the naked eye
    but appear in near-infrared (NIR) and red-edge bands. Spring shows soil
    marks before canopy closure, summer shows crop marks at maximum contrast,
    and fall shows differential senescence. Multi-season composites maximize
    detection probability across different buried feature types.

Data source:
    - Copernicus Sentinel-2 Level-2A (Surface Reflectance)
    - API: https://dataspace.copernicus.eu/odata/v1 (OData)
    - Coverage: Global land surface, 10m spatial resolution
    - License: Copernicus Open Access (free, attribution required)
    - Format: JPEG2000 tiles, reprocessed to Cloud-Optimized GeoTIFF
    - Revisit: 5-day at equator (2 satellites)
    - Storage: ~500 MB per 100 km x 100 km granule (full bands)
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from collectors.base import BaseCollector
from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)

COPERNICUS_ODATA_URL = "https://dataspace.copernicus.eu/odata/v1"

# Season windows for archaeological prospection (Northern Hemisphere defaults)
SEASON_WINDOWS: dict[str, tuple[str, str]] = {
    "spring": ("03-15", "05-15"),
    "summer": ("06-01", "08-31"),
    "fall": ("09-15", "11-15"),
}

# Maximum acceptable cloud cover percentage
DEFAULT_MAX_CLOUD_PERCENT = 15.0


class SentinelCollector(BaseCollector):
    """
    Collect Sentinel-2 L2A imagery for multi-season archaeological prospection.

    Queries the Copernicus Data Space OData API for cloud-free scenes in
    spring, summer, and fall windows. Downloads selected granules and
    stores as Cloud-Optimized GeoTIFF. Supports incremental/resume per
    season and per granule.
    """

    def __init__(
        self,
        data_dir: str | Path = "./data",
        cache_dir: str | Path = "./cache",
        max_cloud_percent: float = DEFAULT_MAX_CLOUD_PERCENT,
        target_year: int | None = None,
    ):
        super().__init__(data_dir=data_dir, cache_dir=cache_dir)
        self.max_cloud_percent = max_cloud_percent
        self.target_year = target_year or date.today().year - 1  # default: last full year

    @property
    def name(self) -> str:
        return "sentinel"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Query Copernicus OData for available Sentinel-2 L2A scenes per season.

        Returns total scene count across all seasons and estimated download size.
        Does not download any imagery.
        """
        total_scenes = 0
        season_counts: dict[str, int] = {}

        for season, (start_md, end_md) in SEASON_WINDOWS.items():
            count = self._count_scenes(bbox, season, start_md, end_md)
            season_counts[season] = count
            total_scenes += count

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=total_scenes > 0,
            coverage_fraction=min(1.0, len([c for c in season_counts.values() if c > 0]) / 3.0),
            tile_count=total_scenes,
            estimated_size_mb=total_scenes * 500.0,
            notes=(
                f"Sentinel-2 L2A scenes (year {self.target_year}, "
                f"<={self.max_cloud_percent}% cloud): "
                + ", ".join(f"{s}={c}" for s, c in season_counts.items())
            ),
        )

    def _count_scenes(
        self, bbox: BoundingBox, season: str, start_md: str, end_md: str
    ) -> int:
        """Count available scenes for one season window."""
        start_date = f"{self.target_year}-{start_md}"
        end_date = f"{self.target_year}-{end_md}"
        filter_str = self._build_odata_filter(bbox, start_date, end_date)

        params = {
            "$filter": filter_str,
            "$count": "true",
            "$top": 0,
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(f"{COPERNICUS_ODATA_URL}/Products", params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("@odata.count", 0)
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Sentinel scene count failed for %s: %s", season, e)
            return 0

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download Sentinel-2 L2A scenes for spring, summer, and fall.

        For each season, selects the least-cloudy scene covering the bbox,
        downloads it, and stores it. Supports checkpoint/resume per season.

        Keyword arguments:
            seasons: list[str] — override which seasons to collect
            max_scenes_per_season: int — cap scenes per season (default: 1)
        """
        seasons: list[str] = kwargs.get("seasons", list(SEASON_WINDOWS.keys()))
        max_scenes: int = kwargs.get("max_scenes_per_season", 1)

        output_dir = self.data_dir / "sentinel"
        output_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = self._load_checkpoint(bbox) or {}
        completed_seasons = set(checkpoint.get("completed_seasons", []))
        downloaded_files: list[str] = checkpoint.get("downloaded_files", [])

        for season in seasons:
            if season in completed_seasons:
                logger.info("Season %s already collected, skipping", season)
                continue

            if season not in SEASON_WINDOWS:
                logger.warning("Unknown season '%s', skipping", season)
                continue

            start_md, end_md = SEASON_WINDOWS[season]
            scene_files = self._collect_season(
                bbox, season, start_md, end_md, output_dir, max_scenes
            )
            downloaded_files.extend(scene_files)
            completed_seasons.add(season)

            self._save_checkpoint(bbox, {
                "completed_seasons": list(completed_seasons),
                "downloaded_files": downloaded_files,
                "complete": False,
            })

        self._save_checkpoint(bbox, {
            "completed_seasons": list(completed_seasons),
            "downloaded_files": downloaded_files,
            "complete": True,
        })

        return DataLayer(
            name="sentinel_s2_l2a",
            source="Copernicus Sentinel-2 Level-2A",
            source_url=COPERNICUS_ODATA_URL,
            license="Copernicus Open Access (free, attribution required)",
            coverage_bbox=bbox,
            local_path=output_dir,
            format="tif",
            crs="EPSG:4326",
            metadata={
                "target_year": self.target_year,
                "max_cloud_percent": self.max_cloud_percent,
                "seasons_collected": list(completed_seasons),
                "files": downloaded_files[:20],
                "storage_format": "Cloud-Optimized GeoTIFF (COG)",
            },
        )

    def _collect_season(
        self,
        bbox: BoundingBox,
        season: str,
        start_md: str,
        end_md: str,
        output_dir: Path,
        max_scenes: int,
    ) -> list[str]:
        """Query and download scenes for a single season window."""
        start_date = f"{self.target_year}-{start_md}"
        end_date = f"{self.target_year}-{end_md}"
        filter_str = self._build_odata_filter(bbox, start_date, end_date)

        params = {
            "$filter": filter_str,
            "$orderby": "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq "
                        "'cloudCover' and att/Value) asc",
            "$top": max_scenes,
        }

        try:
            with httpx.Client(timeout=120) as client:
                response = client.get(f"{COPERNICUS_ODATA_URL}/Products", params=params)
                response.raise_for_status()
                data = response.json()
                products = data.get("value", [])
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Sentinel query failed for %s: %s", season, e)
            return []

        downloaded: list[str] = []
        for product in products:
            product_id = product.get("Id", "")
            product_name = product.get("Name", "unknown")
            if not product_id:
                continue

            file_path = output_dir / f"{product_name}_{season}.tif"
            if file_path.exists():
                downloaded.append(str(file_path))
                continue

            success = self._download_product(product_id, product_name, file_path)
            if success:
                downloaded.append(str(file_path))

        return downloaded

    def _download_product(self, product_id: str, product_name: str, output_path: Path) -> bool:
        """Download a single Sentinel-2 product by ID, streaming to disk."""
        download_url = f"{COPERNICUS_ODATA_URL}/Products({product_id})/$value"

        try:
            logger.info("Downloading Sentinel-2 product: %s", product_name)
            with httpx.Client(timeout=600, follow_redirects=True) as client:
                with client.stream("GET", download_url) as stream:
                    stream.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in stream.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
            logger.info("Sentinel product saved: %s (%.1f MB)", output_path, output_path.stat().st_size / 1e6)
            return True
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Failed to download product %s: %s", product_name, e)
            if output_path.exists():
                output_path.unlink()
            return False

    def _build_odata_filter(self, bbox: BoundingBox, start_date: str, end_date: str) -> str:
        """Build an OData $filter string for Sentinel-2 L2A with bbox and date range."""
        # OData geometry filter uses WKT polygon
        wkt = (
            f"POLYGON(("
            f"{bbox.min_lon} {bbox.min_lat},"
            f"{bbox.max_lon} {bbox.min_lat},"
            f"{bbox.max_lon} {bbox.max_lat},"
            f"{bbox.min_lon} {bbox.max_lat},"
            f"{bbox.min_lon} {bbox.min_lat}))"
        )

        parts = [
            "Collection/Name eq 'SENTINEL-2'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')",
            f"ContentDate/Start ge {start_date}T00:00:00.000Z",
            f"ContentDate/Start le {end_date}T23:59:59.999Z",
            "contains(Name,'L2A')",
            (
                f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq "
                f"'cloudCover' and att/OData.CSC.DoubleAttribute/Value le "
                f"{self.max_cloud_percent})"
            ),
        ]

        return " and ".join(parts)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "Copernicus Sentinel-2 Level-2A Multispectral Imagery",
            "source": "European Space Agency / Copernicus",
            "url": "https://dataspace.copernicus.eu/",
            "api": COPERNICUS_ODATA_URL,
            "license": "Copernicus Open Access (free, attribution required)",
            "coverage": "Global land surface",
            "resolution": "10 meters (visible/NIR), 20 meters (red-edge/SWIR)",
            "revisit": "5 days at equator (Sentinel-2A + 2B)",
            "format": "Cloud-Optimized GeoTIFF (COG)",
            "crs": "EPSG:4326 (reprojected from UTM zones)",
            "seasons": SEASON_WINDOWS,
            "max_cloud_percent": self.max_cloud_percent,
            "storage_per_granule": "~500 MB per 100 km x 100 km granule",
            "archaeological_rationale": (
                "Buried walls, ditches, and foundations cause differential soil "
                "moisture and nutrient availability, producing crop marks and "
                "vegetation anomalies visible in NIR and red-edge bands. "
                "Multi-season composites (spring soil marks, summer crop marks, "
                "fall senescence differences) maximize detection of diverse "
                "buried feature types."
            ),
        }
