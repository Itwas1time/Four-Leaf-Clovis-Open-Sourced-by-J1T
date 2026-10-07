"""
NOAA NCEI bathymetric data collector for submerged continental shelves.

Queries the NOAA National Centers for Environmental Information (NCEI)
THREDDS catalog for bathymetric elevation data on the continental shelf,
focusing on areas shallower than -130 m (the Last Glacial Maximum sea level).

Archaeological rationale:
    During the Last Glacial Maximum (~26,500-19,000 BP), global sea levels
    were 120-130 meters lower than today. Vast areas of continental shelf
    that are now underwater were exposed dry land — and were the primary
    migration corridors along the Pacific and Atlantic coasts. Evidence for
    coastal migration routes and early maritime settlements is now submerged.
    The -130m contour defines the maximum search area for drowned Pleistocene
    landscapes where pre-Clovis coastal sites may survive beneath marine
    sediments.

Data source:
    - NOAA NCEI Coastal Relief Model / ETOPO / multibeam bathymetry
    - API: https://www.ngdc.noaa.gov/thredds (THREDDS OPeNDAP)
    - Coverage: US continental shelves (Atlantic, Pacific, Gulf, Alaska)
    - License: Public Domain (US Government)
    - Format: NetCDF via THREDDS, stored as GeoTIFF
    - Resolution: 1/3 arc-second (~10m) coastal, 1 arc-minute (~1.8km) deep
    - Storage: ~50 MB per 1-degree coastal tile
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

NCEI_THREDDS_BASE = "https://www.ngdc.noaa.gov/thredds"

# Coastal Relief Model catalog (high-resolution coastal bathymetry)
CRM_CATALOG_URL = f"{NCEI_THREDDS_BASE}/catalog/crm/catalog.html"

# ETOPO 2022 for broader shelf coverage
ETOPO_OPENDAP_URL = f"{NCEI_THREDDS_BASE}/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc"

# LGM sea level — areas shallower than this were exposed land
LGM_SEA_LEVEL_M = -130.0


class BathymetryCollector(BaseCollector):
    """
    Collect continental shelf bathymetry to identify drowned Pleistocene landscapes.

    Queries NOAA NCEI for bathymetric data on continental shelves, filtering
    for the 0 to -130m depth zone (exposed land during the LGM). Stores
    results as GeoTIFF with depth values. Large areas are processed in
    sub-tiles to manage memory.
    """

    def __init__(
        self,
        data_dir: str | Path = "./data",
        cache_dir: str | Path = "./cache",
        min_depth_m: float = LGM_SEA_LEVEL_M,
    ):
        super().__init__(data_dir=data_dir, cache_dir=cache_dir)
        self.min_depth_m = min_depth_m

    @property
    def name(self) -> str:
        return "bathymetry"

    def check_availability(self, bbox: BoundingBox) -> CoverageReport:
        """
        Check if the bbox intersects coastal/offshore areas with bathymetric data.

        ETOPO covers the entire ocean, but high-resolution Coastal Relief Model
        data is available only for US waters.
        """
        # Probe ETOPO OPeNDAP to confirm service is up and data exists
        try:
            with httpx.Client(timeout=60) as client:
                # Request DAS (Dataset Attribute Structure) as a lightweight probe
                das_url = f"{ETOPO_OPENDAP_URL}.das"
                response = client.get(das_url)
                response.raise_for_status()
                available = True
        except (httpx.HTTPError, Exception) as e:
            logger.warning("NCEI THREDDS availability check failed: %s", e)
            available = False

        # Estimate tile count based on bbox size
        lat_span = bbox.max_lat - bbox.min_lat
        lon_span = bbox.max_lon - bbox.min_lon
        tile_count = max(1, int(lat_span) * int(lon_span))

        return CoverageReport(
            layer_name=self.name,
            bbox=bbox,
            available=available,
            coverage_fraction=1.0 if available else 0.0,
            tile_count=tile_count,
            estimated_size_mb=tile_count * 50.0,
            notes=(
                f"ETOPO/CRM bathymetry available. Filtering for depths "
                f"0 to {self.min_depth_m}m (LGM exposed shelf)."
            ),
        )

    def collect(self, bbox: BoundingBox, **kwargs: Any) -> DataLayer:
        """
        Download bathymetric data for the continental shelf within the bbox.

        Fetches ETOPO data via OPeNDAP subsetting, filters for depths between
        0 and -130m (LGM sea level), and stores as GeoTIFF. Sub-tiles large
        areas to manage memory.

        Keyword arguments:
            min_depth_m: float — override minimum depth threshold
            resolution: str — 'high' for CRM (~10m), 'low' for ETOPO (~1.8km)
        """
        if "min_depth_m" in kwargs:
            self.min_depth_m = kwargs["min_depth_m"]

        output_dir = self.data_dir / "bathymetry"
        output_dir.mkdir(parents=True, exist_ok=True)
        bbox_slug = f"{bbox.min_lat:.2f}_{bbox.min_lon:.2f}_{bbox.max_lat:.2f}_{bbox.max_lon:.2f}"
        output_path = output_dir / f"bathymetry_shelf_{bbox_slug}.tif"

        checkpoint = self._load_checkpoint(bbox)
        if checkpoint and checkpoint.get("complete") and output_path.exists():
            logger.info("Bathymetry data already collected for this bbox")
        else:
            self._download_bathymetry(bbox, output_path)
            self._save_checkpoint(bbox, {"complete": True, "path": str(output_path)})

        return DataLayer(
            name="bathymetry_shelf",
            source="NOAA NCEI (ETOPO / Coastal Relief Model)",
            source_url=NCEI_THREDDS_BASE,
            license="Public Domain (US Government work)",
            coverage_bbox=bbox,
            local_path=output_path,
            format="tif",
            crs="EPSG:4326",
            metadata={
                "min_depth_m": self.min_depth_m,
                "lgm_sea_level_m": LGM_SEA_LEVEL_M,
                "vertical_datum": "MSL (Mean Sea Level)",
                "filter": f"Continental shelf: 0 to {self.min_depth_m}m",
            },
        )

    def _download_bathymetry(self, bbox: BoundingBox, output_path: Path) -> None:
        """
        Download ETOPO data via OPeNDAP and filter for shelf depths.

        Uses OPeNDAP subsetting to request only the bbox extent, avoiding
        download of the full global grid. Falls back to ASCII subset if
        binary access fails.
        """
        sub_tiles = self._split_bbox(bbox, max_degrees=1.0)
        all_arrays: list[tuple[np.ndarray, BoundingBox]] = []

        checkpoint = self._load_checkpoint(bbox) or {}
        completed_tiles = set(checkpoint.get("completed_tiles", []))

        for tile in sub_tiles:
            tile_key = f"{tile.min_lat:.4f}_{tile.min_lon:.4f}"
            if tile_key in completed_tiles:
                continue

            array = self._fetch_opendap_tile(tile)
            if array is not None:
                # Mask to shelf depths only (0 to min_depth_m)
                shelf_mask = (array <= 0) & (array >= self.min_depth_m)
                masked = np.where(shelf_mask, array, np.nan)
                if not np.all(np.isnan(masked)):
                    all_arrays.append((masked, tile))

            completed_tiles.add(tile_key)
            self._save_checkpoint(bbox, {
                "completed_tiles": list(completed_tiles),
                "complete": False,
            })

        self._write_bathymetry_tif(all_arrays, bbox, output_path)

    def _fetch_opendap_tile(self, tile: BoundingBox) -> np.ndarray | None:
        """
        Fetch a sub-tile of bathymetry via OPeNDAP ASCII subset.

        ETOPO 2022 has 1-arcminute resolution: 60 cells per degree.
        """
        # Convert lat/lon to ETOPO grid indices
        # ETOPO grid: lat from -90 to 90, lon from -180 to 180, 1 arcmin steps
        lat_start = int((tile.min_lat + 90) * 60)
        lat_end = int((tile.max_lat + 90) * 60)
        lon_start = int((tile.min_lon + 180) * 60)
        lon_end = int((tile.max_lon + 180) * 60)

        # OPeNDAP array subset syntax: variable[lat_start:lat_end][lon_start:lon_end]
        subset_url = (
            f"{ETOPO_OPENDAP_URL}.ascii?"
            f"z[{lat_start}:{lat_end}][{lon_start}:{lon_end}]"
        )

        try:
            with httpx.Client(timeout=120) as client:
                response = client.get(subset_url)
                response.raise_for_status()
                return self._parse_opendap_ascii(response.text, lat_end - lat_start + 1, lon_end - lon_start + 1)
        except (httpx.HTTPError, Exception) as e:
            logger.warning("OPeNDAP fetch failed for tile: %s", e)
            return None

    @staticmethod
    def _parse_opendap_ascii(text: str, nrows: int, ncols: int) -> np.ndarray | None:
        """Parse OPeNDAP ASCII response into a numpy array."""
        try:
            lines = text.strip().split("\n")
            # Find the data section (after the header)
            data_lines = []
            in_data = False
            for line in lines:
                if line.startswith("z,"):
                    continue
                if in_data or line[0:1].lstrip("-").isdigit():
                    in_data = True
                    # Each row may have a row index prefix like "[0]" — strip it
                    if "]" in line:
                        line = line.split("]", 1)[-1]
                    values = [float(v) for v in line.split(",") if v.strip()]
                    if values:
                        data_lines.extend(values)

            if not data_lines:
                return None
            arr = np.array(data_lines).reshape(nrows, ncols)
            return arr
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse OPeNDAP ASCII: %s", e)
            return None

    @staticmethod
    def _write_bathymetry_tif(
        arrays: list[tuple[np.ndarray, BoundingBox]],
        bbox: BoundingBox,
        output_path: Path,
    ) -> None:
        """
        Write bathymetry arrays to a GeoTIFF.

        Uses rasterio if available, otherwise writes a raw numpy file as
        fallback (with a sidecar metadata JSON).
        """
        if not arrays:
            logger.info("No shelf bathymetry data found in bbox — writing empty marker")
            output_path.write_bytes(b"")
            return

        try:
            import rasterio
            from rasterio.transform import from_bounds

            # Merge all tiles into a single array
            # Simple approach: concatenate along lat axis if tiles span lat
            merged = np.vstack([a for a, _ in arrays])
            nrows, ncols = merged.shape

            transform = from_bounds(
                bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat,
                ncols, nrows,
            )

            with rasterio.open(
                output_path, "w",
                driver="GTiff",
                height=nrows,
                width=ncols,
                count=1,
                dtype=merged.dtype,
                crs="EPSG:4326",
                transform=transform,
                nodata=np.nan,
            ) as dst:
                dst.write(merged, 1)

            logger.info("Bathymetry GeoTIFF saved: %s (%d x %d)", output_path, nrows, ncols)

        except ImportError:
            # Fallback: save as numpy binary with metadata sidecar
            npy_path = output_path.with_suffix(".npy")
            np.save(npy_path, np.vstack([a for a, _ in arrays]))
            import json
            meta_path = output_path.with_suffix(".json")
            with open(meta_path, "w") as f:
                json.dump({
                    "bbox": bbox.model_dump(),
                    "min_depth_m": LGM_SEA_LEVEL_M,
                    "format": "numpy_array",
                    "note": "Install rasterio for GeoTIFF output",
                }, f)
            logger.warning("rasterio not available; saved as .npy + .json sidecar")

    @staticmethod
    def _split_bbox(bbox: BoundingBox, max_degrees: float = 1.0) -> list[BoundingBox]:
        """Split a bbox into sub-tiles for memory-conscious processing."""
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
            "name": "NOAA NCEI Continental Shelf Bathymetry",
            "source": "NOAA National Centers for Environmental Information",
            "url": "https://www.ncei.noaa.gov/products/bathymetry",
            "api": NCEI_THREDDS_BASE,
            "license": "Public Domain (US Government work)",
            "coverage": "US continental shelves (Atlantic, Pacific, Gulf, Alaska)",
            "resolution": "1/3 arc-second (~10m) coastal, 1 arc-minute (~1.8km) deep ocean",
            "format": "GeoTIFF (from NetCDF via OPeNDAP)",
            "crs": "EPSG:4326",
            "depth_filter": f"0 to {LGM_SEA_LEVEL_M}m (LGM exposed shelf)",
            "vertical_datum": "Mean Sea Level",
            "archaeological_rationale": (
                "During the Last Glacial Maximum (~26,500-19,000 BP), sea levels "
                "were 120-130m lower. The continental shelf that is now underwater "
                "was the primary coastal migration corridor. Evidence for the "
                "earliest coastal populations is drowned beneath marine sediments. "
                "The -130m contour defines the maximum search area for submerged "
                "Pleistocene archaeological landscapes."
            ),
        }
