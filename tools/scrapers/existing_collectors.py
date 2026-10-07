"""Sources 11-13: Wrappers around existing collector classes (Hydro, Geology, BLM)."""

import logging
import sys
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# Add project root to path so we can import collectors
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class HydroScraper(BaseScraper):
    source_id = "hydro"
    source_name = "USGS National Hydrography Dataset"
    base_url = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
    rate_limit = 1.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        """Use HydroCollector to fetch NHD data for major river regions."""
        records = []
        try:
            from collectors.hydro_collector import HydroCollector
            from core.schemas import BoundingBox
        except ImportError as e:
            logger.warning(f"[hydro] Cannot import HydroCollector: {e}")
            return records

        # Regional bboxes for major river systems
        regions = [
            ("Mississippi", -92.0, 29.0, -88.0, 48.0),
            ("Ohio River", -89.0, 36.0, -79.0, 42.0),
            ("Missouri", -115.0, 38.0, -90.0, 49.0),
            ("Columbia", -125.0, 42.0, -115.0, 49.0),
            ("Colorado", -117.0, 31.0, -107.0, 42.0),
            ("Rio Grande", -107.0, 26.0, -97.0, 37.0),
        ]

        collector = HydroCollector()
        for name, min_lon, min_lat, max_lon, max_lat in regions:
            try:
                bbox = BoundingBox(
                    min_lat=min_lat, min_lon=min_lon,
                    max_lat=max_lat, max_lon=max_lon
                )
                avail = collector.check_availability(bbox)
                if not avail.available:
                    logger.info(f"[hydro] No data for {name}")
                    continue

                layer = collector.collect(bbox)
                logger.info(f"[hydro] Got data for {name}: {layer.local_path}")
                records.append({
                    "name": f"{name} NHD data",
                    "region": name,
                    "local_path": str(layer.local_path),
                    "format": layer.format,
                })
            except Exception as e:
                logger.warning(f"[hydro] Failed for {name}: {e}")

        return records


class GeologyScraper(BaseScraper):
    source_id = "geology"
    source_name = "USGS State Geologic Map Compilation"
    base_url = "https://mrdata.usgs.gov/services/sgmc"
    rate_limit = 1.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        """Use GeologyCollector to fetch geological formation data."""
        records = []
        try:
            from collectors.geology_collector import GeologyCollector
            from core.schemas import BoundingBox
        except ImportError as e:
            logger.warning(f"[geology] Cannot import GeologyCollector: {e}")
            return records

        # Karst/sandstone/volcanic regions
        regions = [
            ("Mammoth Cave", -87.0, 36.5, -85.0, 38.0, "karst"),
            ("Ozark Plateau", -94.0, 35.5, -91.0, 37.5, "karst"),
            ("Edwards Plateau", -101.0, 29.0, -97.0, 32.0, "karst"),
            ("Appalachian sandstone", -82.0, 35.0, -78.0, 40.0, "sandstone"),
            ("Colorado Plateau", -112.0, 35.0, -107.0, 39.0, "sandstone"),
            ("Cascades volcanic", -123.0, 42.0, -120.0, 49.0, "volcanic"),
        ]

        collector = GeologyCollector()
        for name, min_lon, min_lat, max_lon, max_lat, zone_type in regions:
            try:
                bbox = BoundingBox(
                    min_lat=min_lat, min_lon=min_lon,
                    max_lat=max_lat, max_lon=max_lon
                )
                avail = collector.check_availability(bbox)
                if not avail.available:
                    continue
                layer = collector.collect(bbox)
                records.append({
                    "name": name,
                    "zone_type": zone_type,
                    "local_path": str(layer.local_path),
                    "format": layer.format,
                })
                logger.info(f"[geology] Got data for {name}")
            except Exception as e:
                logger.warning(f"[geology] Failed for {name}: {e}")

        return records


class LandStatusScraper(BaseScraper):
    source_id = "land_status"
    source_name = "BLM Land Status / Surface Management Agency"
    base_url = "https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_SMA_Cached_without_Wilderness/MapServer"
    rate_limit = 1.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        """Use LandStatusCollector to fetch BLM ownership data."""
        records = []
        try:
            from collectors.land_status_collector import LandStatusCollector
            from core.schemas import BoundingBox
        except ImportError as e:
            logger.warning(f"[land_status] Cannot import LandStatusCollector: {e}")
            return records

        # Western US regions where most federal land is
        regions = [
            ("Pacific NW", -125.0, 42.0, -116.0, 49.0),
            ("California", -125.0, 32.0, -114.0, 42.0),
            ("Great Basin", -120.0, 35.0, -111.0, 42.0),
            ("Southwest", -114.0, 31.0, -103.0, 37.0),
            ("Rocky Mountain", -115.0, 37.0, -104.0, 49.0),
        ]

        collector = LandStatusCollector()
        for name, min_lon, min_lat, max_lon, max_lat in regions:
            try:
                bbox = BoundingBox(
                    min_lat=min_lat, min_lon=min_lon,
                    max_lat=max_lat, max_lon=max_lon
                )
                avail = collector.check_availability(bbox)
                if not avail.available:
                    continue
                layer = collector.collect(bbox)
                records.append({
                    "name": name,
                    "local_path": str(layer.local_path),
                    "format": layer.format,
                })
                logger.info(f"[land_status] Got data for {name}")
            except Exception as e:
                logger.warning(f"[land_status] Failed for {name}: {e}")

        return records
