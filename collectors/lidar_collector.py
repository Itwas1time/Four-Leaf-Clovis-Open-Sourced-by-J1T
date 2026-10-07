"""
USGS 3DEP LiDAR data collector via The National Map API.

Queries the USGS 3D Elevation Program (3DEP) product index for available
LiDAR point cloud and DEM tiles, supports querying without downloading,
individual tile downloads by bbox, and incremental/resume for large areas.

Archaeological rationale:
    LiDAR penetrates forest canopy to reveal bare-earth surface features
    invisible from the ground or in optical imagery. It has revolutionized
    archaeology by exposing mounds, earthworks, house platforms, field
    systems, and roads in forested regions. The Cahokia discovery expansion,
    Maya LiDAR surveys, and countless Southeastern US mound discoveries
    all owe to LiDAR. This is the most direct remote sensing indicator
    of human modification of the landscape.

Data source:
    - USGS 3D Elevation Program (3DEP)
    - API: https://tnmaccess.nationalmap.gov/api/v1/products
    - Coverage: ~80% of contiguous US (growing; priority areas first)
    - License: Public Domain (US Government)
    - Format: LAZ (compressed LAS) point clouds and GeoTIFF DEMs
    - Update frequency: Ongoing (multi-year national acquisition)
    - Storage: 50-500 MB per tile depending on point density
    - WARNING: Full US coverage is multi-terabyte. Process tile-by-tile.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from collectors.base import BaseCollector
from core.schemas import BoundingBox, CoverageReport, DataLayer

logger = logging.getLogger(__name__)

TNM_PRODUCTS_API = "https://tnmaccess.nationalmap.gov/api/v1/products"

# 3DEP dataset codes
LIDAR_DATASETS = [
    "Digital Elevation Model (DEM) 1 meter",
    "Lidar Point Cloud (LPC)",
    "Original Product Resolution (OPR)",
]


class LidarCollector(BaseCollector):
    """
    Collect USGS 3DEP LiDAR data tile-by-tile.

    Supports three modes:
    1. Query-only (check_availability): enumerate available tiles without downloading
    2. Individual tile download: download specific tiles by bbox
    3. Incremental collection: resume interrupted downloads

    Memory-conscious: processes one tile at a time, never loads entire datasets.
    This is the largest single dataset — multi-terabyte for full US.
    """

    def __init__(
        self,
        data_dir: str | Path = "./data",
        cache_dir: str | Path = "./cache",
        dataset: str = "Digital Elevation Model (DEM) 1 meter",
    ):
        super().__init__(data_dir=data_dir, cache_dir=cache_dir)
        self.dataset = dataset

    @property
    def name(self) -> str:
        return "lidar"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Query the National Map for available 3DEP tiles WITHOUT downloading.

        Returns tile count, total estimated size, and coverage notes.
        This is the recommended first step before committing to a download.
        """
        tiles = self._query_tile_index(bbox, max_results=500)

        if not tiles:
            return CoverageReport(
                layer_name=self.name,
                bbox=bbox,
                available=False,
                coverage_fraction=0.0,
                notes="No 3DEP LiDAR tiles found for this area",
            )

        total_size_mb = sum(t.get("sizeInBytes", 0) for t in tiles) / 1e6
        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=True,
            coverage_fraction=min(1.0, len(tiles) * 0.01),  # rough estimate
            tile_count=len(tiles),
            estimated_size_mb=total_size_mb,
            notes=(
                f"{len(tiles)} 3DEP tiles available, dataset='{self.dataset}'. "
                f"Estimated {total_size_mb:.0f} MB total."
            ),
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download 3DEP tiles for the bounding box, one tile at a time.

        Supports incremental/resume: tracks which tiles have been downloaded
        in the checkpoint and skips them on re-run. Each tile is streamed
        to disk to avoid loading large files into memory.

        Keyword arguments:
            max_tiles: int — cap the number of tiles to download (default: all)
            dataset: str — override the dataset type for this collection
        """
        max_tiles: int = kwargs.get("max_tiles", 0)
        dataset_override: str | None = kwargs.get("dataset")
        if dataset_override:
            self.dataset = dataset_override

        output_dir = self.data_dir / "lidar"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Query available tiles
        tiles = self._query_tile_index(bbox, max_results=5000)
        if not tiles:
            logger.info("No 3DEP tiles available for bbox")
            return self._make_data_layer(bbox, output_dir, downloaded=[])

        if max_tiles > 0:
            tiles = tiles[:max_tiles]

        # Load checkpoint to resume
        checkpoint = self._load_checkpoint(bbox) or {}
        downloaded: list[str] = checkpoint.get("downloaded_files", [])
        downloaded_urls: set[str] = set(checkpoint.get("downloaded_urls", []))

        with httpx.Client(timeout=600, follow_redirects=True) as client:
            for i, tile in enumerate(tiles):
                download_url = tile.get("downloadURL", "")
                if not download_url or download_url in downloaded_urls:
                    continue

                tile_path = self._download_tile(client, tile, output_dir)
                if tile_path:
                    downloaded.append(str(tile_path))
                    downloaded_urls.add(download_url)

                # Checkpoint every 5 tiles
                if (i + 1) % 5 == 0:
                    self._save_checkpoint(bbox, {
                        "downloaded_files": downloaded,
                        "downloaded_urls": list(downloaded_urls),
                        "complete": False,
                    })

        self._save_checkpoint(bbox, {
            "downloaded_files": downloaded,
            "downloaded_urls": list(downloaded_urls),
            "complete": True,
        })

        return self._make_data_layer(bbox, output_dir, downloaded)

    def _query_tile_index(
        self, bbox: BoundingBox, max_results: int = 500
    ) -> list[dict[str, Any]]:
        """
        Query The National Map product API for available tiles.

        Returns a list of tile metadata dicts (title, downloadURL, sizeInBytes, etc.)
        without downloading any actual data.
        """
        params = {
            "datasets": self.dataset,
            "bbox": f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}",
            "max": max_results,
            "outputFormat": "JSON",
        }

        all_items: list[dict[str, Any]] = []
        offset = 0

        with httpx.Client(timeout=120) as client:
            while True:
                params["offset"] = offset
                try:
                    response = client.get(TNM_PRODUCTS_API, params=params)
                    response.raise_for_status()
                    data = response.json()
                except (httpx.HTTPError, Exception) as e:
                    logger.warning("TNM product query failed at offset %d: %s", offset, e)
                    break

                items = data.get("items", [])
                if not items:
                    break

                all_items.extend(items)

                total = data.get("total", 0)
                if len(all_items) >= total or len(all_items) >= max_results:
                    break
                offset += len(items)

        logger.info("Found %d 3DEP tiles for bbox", len(all_items))
        return all_items

    def _download_tile(
        self, client: httpx.Client, tile: dict[str, Any], output_dir: Path
    ) -> Path | None:
        """
        Download a single tile, streaming to disk. Returns path or None on failure.
        """
        download_url = tile.get("downloadURL", "")
        title = tile.get("title", "unknown_tile")
        # Sanitize filename from title
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)
        # Determine extension from URL
        ext = ".tif"
        if download_url.lower().endswith(".laz"):
            ext = ".laz"
        elif download_url.lower().endswith(".las"):
            ext = ".las"
        elif download_url.lower().endswith(".zip"):
            ext = ".zip"

        tile_path = output_dir / f"{safe_name}{ext}"

        if tile_path.exists():
            logger.debug("Tile already on disk: %s", tile_path)
            return tile_path

        try:
            logger.info("Downloading tile: %s (%.1f MB)", title, tile.get("sizeInBytes", 0) / 1e6)
            with client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(tile_path, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
            logger.info("Tile saved: %s (%.1f MB)", tile_path, tile_path.stat().st_size / 1e6)
            return tile_path
        except (httpx.HTTPError, Exception) as e:
            logger.warning("Failed to download tile %s: %s", title, e)
            if tile_path.exists():
                tile_path.unlink()
            return None

    def _make_data_layer(
        self, bbox: BoundingBox, output_dir: Path, downloaded: list[str]
    ) -> DataLayer:
        """Build a DataLayer pointing to the collection directory."""
        return DataLayer(
            name="lidar_3dep",
            source="USGS 3D Elevation Program (3DEP)",
            source_url=TNM_PRODUCTS_API,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_dir,
            format="tif",
            crs="EPSG:4326",
            metadata={
                "dataset": self.dataset,
                "tiles_downloaded": len(downloaded),
                "tile_files": downloaded[:50],  # cap metadata size
            },
        )

    def get_metadata(self) -> dict[str, Any]:
        return {
            "name": "USGS 3DEP LiDAR",
            "source": "USGS 3D Elevation Program",
            "url": "https://www.usgs.gov/3d-elevation-program",
            "api": TNM_PRODUCTS_API,
            "license": "Public Domain (US Government work)",
            "coverage": "~80% of contiguous US (growing)",
            "datasets": LIDAR_DATASETS,
            "format": "GeoTIFF (DEM) and LAZ (point clouds)",
            "crs": "EPSG:4326 (varies by tile, reprojected on ingest)",
            "update_frequency": "Ongoing multi-year national acquisition",
            "storage_warning": (
                "Full US coverage is multi-terabyte. Always use check_availability() "
                "first and download tile-by-tile with max_tiles parameter."
            ),
            "archaeological_rationale": (
                "LiDAR penetrates forest canopy to reveal bare-earth surface features "
                "invisible from the ground or in optical imagery — mounds, earthworks, "
                "platforms, field systems, and roads. It is the most direct remote "
                "sensing indicator of human landscape modification."
            ),
        }
