"""Tribal/Indigenous territory scrapers.

Downloads:
  1. US Census TIGER/Line AIANNH shapefile (legal boundaries)
  2. Native Land Digital API (historical territories, languages, treaties)
  3. BIA ArcGIS trust/restricted-fee land
  4. EPA tribal ArcGIS layers (cession boundaries, reservations, etc.)
"""

import io
import json
import logging
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# --- TIGER/Line AIANNH ---
TIGER_AIANNH_URL = "https://www2.census.gov/geo/tiger/TIGER2023/AIANNH/tl_2023_us_aiannh.zip"

AIANNH_TYPES = {
    "G2100": "reservation",
    "G2101": "reservation",              # Federal AI reservation
    "G2102": "reservation",              # State AI reservation
    "G2103": "reservation",              # Federal AI reservation (joint area)
    "G2120": "off_reservation_trust",
    "G2130": "hawaiian_home_land",
    "G2140": "alaska_native_village",
    "G2150": "oklahoma_tribal",
    "G2160": "state_recognized",
    "G2170": "joint_use_area",
}

# --- Native Land Digital API ---
NATIVE_LAND_BASE = "https://native-land.ca/api/polygons/geojson"
NATIVE_LAND_LAYERS = ["territories", "languages", "treaties"]

# US bounding box for filtering (generous)
US_BBOX = (-180.0, 17.0, -60.0, 72.0)  # includes Alaska, Hawaii, territories

# --- BIA ArcGIS ---
BIA_TRUST_LAND_URL = (
    "https://biamaps.geoplatform.gov/server/rest/services/DivLTR/"
    "BIA_AIAN_National_LAR/MapServer/0/query"
)

# --- EPA Tribal ArcGIS ---
EPA_TRIBAL_BASE = "https://geopub.epa.gov/arcgis/rest/services/EMEF/Tribal/MapServer"
# Layer indices of interest
EPA_LAYERS = {
    0: "alaska_native_allotments",
    1: "alaska_native_villages",
    2: "reservations",
    3: "off_reservation_trust",
    4: "oklahoma_tribal_statistical",
    5: "virginia_federally_recognized",
    6: "alaska_native_regional_corps",
    7: "state_recognized_reservations",
    8: "hawaiian_home_lands",
    9: "tribal_cession_boundaries",
}


def _load_config() -> dict:
    """Load tools/config.json."""
    cfg_path = Path(__file__).resolve().parent.parent / "config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _bbox_intersects_us(geom) -> bool:
    """Check if a geometry's bounding box intersects the US bbox."""
    try:
        minx, miny, maxx, maxy = geom.bounds
        return not (maxx < US_BBOX[0] or minx > US_BBOX[2] or
                    maxy < US_BBOX[1] or miny > US_BBOX[3])
    except Exception:
        return False


class TIGERTribalScraper(BaseScraper):
    """Download and parse TIGER/Line AIANNH shapefile."""

    source_id = "tiger_aiannh"
    source_name = "US Census TIGER/Line AIANNH Boundaries"
    base_url = TIGER_AIANNH_URL
    timeout = 120

    def scrape(self) -> list[dict]:
        logger.info(f"[{self.source_id}] Downloading TIGER AIANNH shapefile...")
        resp = self._request_with_retry(TIGER_AIANNH_URL)
        logger.info(f"[{self.source_id}] Downloaded {len(resp.content) / 1024 / 1024:.1f} MB")

        # Extract ZIP to temp dir and read shapefile
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(tmpdir)

            # Find the .shp file
            shp_files = list(Path(tmpdir).glob("*.shp"))
            if not shp_files:
                raise FileNotFoundError("No .shp file found in TIGER ZIP")

            gdf = gpd.read_file(shp_files[0])
            logger.info(f"[{self.source_id}] Loaded {len(gdf)} AIANNH features")

        # Ensure WGS84
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        # Simplify geometries to reduce size (~0.01 degree ≈ 1km)
        gdf["geometry"] = gdf["geometry"].simplify(0.01)

        records = []
        for _, row in gdf.iterrows():
            geom = row["geometry"]
            if geom is None or geom.is_empty:
                continue

            mtfcc = str(row.get("MTFCC", ""))
            boundary_type = AIANNH_TYPES.get(mtfcc, "unknown")

            geo_interface = geom.__geo_interface__
            land_area = row.get("ALAND", 0) or 0
            water_area = row.get("AWATER", 0) or 0

            records.append({
                "source": "tiger_aiannh",
                "name": str(row.get("NAMELSAD", row.get("NAME", "Unknown"))),
                "code": str(row.get("AIANHHCE", "")),
                "boundary_type": boundary_type,
                "mtfcc": mtfcc,
                "funcstat": str(row.get("FUNCSTAT", "")),
                "land_area_sqm": int(land_area),
                "water_area_sqm": int(water_area),
                "geometry": geo_interface,
            })

        logger.info(f"[{self.source_id}] Extracted {len(records)} AIANNH records")
        return records


class NativeLandScraper(BaseScraper):
    """Download territories, languages, and treaties from Native Land Digital API."""

    source_id = "native_land"
    source_name = "Native Land Digital"
    base_url = "https://native-land.ca"
    timeout = 120
    rate_limit = 2.0  # Be respectful

    def scrape(self) -> list[dict]:
        config = _load_config()
        api_key = config.get("native_land_api_key", "")
        if not api_key:
            logger.warning(f"[{self.source_id}] No API key found, skipping")
            return []

        all_records = []

        for layer in NATIVE_LAND_LAYERS:
            logger.info(f"[{self.source_id}] Fetching {layer}...")
            url = f"{NATIVE_LAND_BASE}/{layer}"
            try:
                resp = self._request_with_retry(url, params={"key": api_key})
                data = resp.json()
            except Exception as e:
                logger.error(f"[{self.source_id}] Failed to fetch {layer}: {e}")
                continue

            features = data.get("features", [])
            logger.info(f"[{self.source_id}] Got {len(features)} {layer} features worldwide")

            # Filter to US bbox
            us_count = 0
            for feat in features:
                try:
                    from shapely.geometry import shape
                    geom = shape(feat["geometry"])
                    if not _bbox_intersects_us(geom):
                        continue

                    # Simplify large polygons
                    if geom.area > 0.1:
                        geom = geom.simplify(0.01)

                    props = feat.get("properties", {})
                    name = props.get("Name", props.get("name", "Unknown"))
                    # Native Land uses "Slug" for URL-safe names
                    slug = props.get("Slug", props.get("slug", ""))
                    description = props.get("description", props.get("Description", ""))
                    # Some features have FrenchName or other language variants
                    native_name = props.get("FrenchDescription", "")

                    all_records.append({
                        "source": "native_land",
                        "layer": layer,  # "territories", "languages", "treaties"
                        "name": name if isinstance(name, str) else str(name),
                        "native_name": native_name if isinstance(native_name, str) else "",
                        "slug": slug,
                        "description": description if isinstance(description, str) else "",
                        "geometry": geom.__geo_interface__,
                    })
                    us_count += 1
                except Exception as e:
                    logger.debug(f"[{self.source_id}] Skipping feature: {e}")
                    continue

            logger.info(f"[{self.source_id}] Kept {us_count} US-intersecting {layer}")

        logger.info(f"[{self.source_id}] Total: {len(all_records)} US records")
        return all_records


class BIATribalScraper(BaseScraper):
    """Download BIA trust/restricted-fee land boundaries from ArcGIS."""

    source_id = "bia_tribal"
    source_name = "BIA AIAN National Land Area Representations"
    base_url = BIA_TRUST_LAND_URL
    timeout = 120

    def _query_arcgis_all(self, url: str, layer_name: str) -> list[dict]:
        """Page through ArcGIS REST API results."""
        records = []
        offset = 0
        batch_size = 1000

        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "resultRecordCount": batch_size,
                "resultOffset": offset,
            }
            try:
                resp = self._request_with_retry(url, params=params)
                data = resp.json()
            except Exception as e:
                logger.error(f"[{self.source_id}] ArcGIS query failed at offset {offset}: {e}")
                break

            features = data.get("features", [])
            if not features:
                break

            for feat in features:
                props = feat.get("properties", {})
                geom_raw = feat.get("geometry")
                if not geom_raw:
                    continue

                try:
                    from shapely.geometry import shape
                    geom = shape(geom_raw)
                    if geom.is_empty:
                        continue
                    # Simplify
                    geom = geom.simplify(0.01)

                    name = (props.get("LANAME", "") or
                            props.get("NAME", "") or
                            props.get("NAMELSAD", "") or
                            "Unknown")
                    records.append({
                        "source": "bia_tribal",
                        "layer": layer_name,
                        "name": str(name),
                        "properties": {k: str(v) for k, v in props.items() if v is not None},
                        "geometry": geom.__geo_interface__,
                    })
                except Exception as e:
                    logger.debug(f"[{self.source_id}] Skipping feature: {e}")
                    continue

            offset += batch_size
            if len(features) < batch_size:
                break

        return records

    def scrape(self) -> list[dict]:
        logger.info(f"[{self.source_id}] Querying BIA trust land MapServer...")
        records = self._query_arcgis_all(BIA_TRUST_LAND_URL, "trust_land")
        logger.info(f"[{self.source_id}] Got {len(records)} BIA trust land features")
        return records


class EPATribalScraper(BaseScraper):
    """Download EPA tribal layers from ArcGIS, especially cession boundaries."""

    source_id = "epa_tribal"
    source_name = "EPA Tribal ArcGIS Services"
    base_url = EPA_TRIBAL_BASE
    timeout = 120

    def _query_layer(self, layer_idx: int, layer_name: str) -> list[dict]:
        """Query a single EPA tribal layer."""
        url = f"{EPA_TRIBAL_BASE}/{layer_idx}/query"
        records = []
        offset = 0
        batch_size = 1000

        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "resultRecordCount": batch_size,
                "resultOffset": offset,
            }
            try:
                resp = self._request_with_retry(url, params=params)
                data = resp.json()
            except Exception as e:
                logger.error(f"[{self.source_id}] Layer {layer_name} query failed: {e}")
                break

            features = data.get("features", [])
            if not features:
                break

            for feat in features:
                props = feat.get("properties", {})
                geom_raw = feat.get("geometry")
                if not geom_raw:
                    continue

                try:
                    from shapely.geometry import shape
                    geom = shape(geom_raw)
                    if geom.is_empty:
                        continue
                    geom = geom.simplify(0.01)

                    name = (props.get("NAME", "") or
                            props.get("NAMELSAD", "") or
                            props.get("BASENAME", "") or
                            "Unknown")
                    records.append({
                        "source": "epa_tribal",
                        "layer": layer_name,
                        "name": str(name),
                        "properties": {k: str(v) for k, v in props.items() if v is not None},
                        "geometry": geom.__geo_interface__,
                    })
                except Exception as e:
                    logger.debug(f"[{self.source_id}] Skipping feature: {e}")
                    continue

            offset += batch_size
            if len(features) < batch_size:
                break

        return records

    def scrape(self) -> list[dict]:
        all_records = []

        for layer_idx, layer_name in EPA_LAYERS.items():
            logger.info(f"[{self.source_id}] Querying layer {layer_idx}: {layer_name}...")
            recs = self._query_layer(layer_idx, layer_name)
            logger.info(f"[{self.source_id}] Layer {layer_name}: {len(recs)} features")
            all_records.extend(recs)

        logger.info(f"[{self.source_id}] Total EPA tribal: {len(all_records)} features")
        return all_records
