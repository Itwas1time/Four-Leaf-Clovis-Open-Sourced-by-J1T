"""Source 4: DINAA (Digital Index of North American Archaeology) scraper.

DINAA aggregates state SHPO databases -- the single most valuable source.
"""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

# Regional bboxes for fallback bbox-based queries
REGION_BBOXES = [
    # (name, min_lon, min_lat, max_lon, max_lat)
    ("northeast", -80.0, 38.0, -66.0, 48.0),
    ("southeast", -92.0, 24.0, -75.0, 38.0),
    ("midwest", -104.0, 36.0, -80.0, 50.0),
    ("southwest", -120.0, 24.0, -104.0, 38.0),
    ("west", -125.0, 38.0, -104.0, 50.0),
]


class DInaaScraper(BaseScraper):
    source_id = "dinaa"
    source_name = "Digital Index of North American Archaeology"
    base_url = "https://alexandriaarchive.org/dinaa/api"
    rate_limit = 2.0  # Be respectful to academic servers

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        completed_states = set()
        if checkpoint:
            records = checkpoint.get("records", [])
            completed_states = set(checkpoint.get("completed_states", []))

        # Try state-by-state first
        for state in US_STATES:
            if state in completed_states:
                continue

            try:
                state_records = self._scrape_state(state)
                records.extend(state_records)
                completed_states.add(state)
                logger.info(f"[dinaa] {state}: {len(state_records)} sites")
            except Exception as e:
                logger.warning(f"[dinaa] State {state} failed: {e}")
                # Try bbox fallback for this state's region
                completed_states.add(state)  # Don't retry failed states

            if len(completed_states) % 5 == 0:
                self._save_checkpoint({
                    "records": records,
                    "completed_states": list(completed_states),
                })

        # Try bbox-based queries as supplemental
        if not records:
            logger.info("[dinaa] State queries yielded no results, trying bbox queries...")
            for name, min_lon, min_lat, max_lon, max_lat in REGION_BBOXES:
                try:
                    bbox_records = self._scrape_bbox(min_lon, min_lat, max_lon, max_lat)
                    records.extend(bbox_records)
                    logger.info(f"[dinaa] Region {name}: {len(bbox_records)} sites")
                except Exception as e:
                    logger.warning(f"[dinaa] Region {name} bbox query failed: {e}")

        return records

    def _scrape_state(self, state: str) -> list[dict]:
        """Scrape all sites for a given state abbreviation."""
        url = f"{self.base_url}/sites"
        params = {"state": state}

        try:
            resp = self._request_with_retry(url, params=params)
        except Exception:
            # Try alternate endpoint patterns
            for alt_url in [
                f"{self.base_url}/sites/{state}",
                f"{self.base_url}/v1/sites?state={state}",
            ]:
                try:
                    resp = self._request_with_retry(alt_url)
                    break
                except Exception:
                    continue
            else:
                raise

        data = resp.json()
        return self._parse_response(data, state)

    def _scrape_bbox(self, min_lon: float, min_lat: float,
                     max_lon: float, max_lat: float) -> list[dict]:
        """Scrape sites within a bounding box."""
        url = f"{self.base_url}/sites"
        params = {"bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}"}

        try:
            resp = self._request_with_retry(url, params=params)
        except Exception:
            # Try GeoJSON endpoint
            try:
                resp = self._request_with_retry(
                    f"{self.base_url}/geojson",
                    params={"bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}"}
                )
            except Exception:
                return []

        data = resp.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict | list, state: str = "") -> list[dict]:
        """Parse DINAA response into normalized records."""
        records = []

        # Handle GeoJSON FeatureCollection
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            for feat in data.get("features", []):
                rec = self._parse_feature(feat, state)
                if rec:
                    records.append(rec)
            return records

        # Handle list of features
        if isinstance(data, list):
            for item in data:
                rec = self._parse_item(item, state)
                if rec:
                    records.append(rec)
            return records

        # Handle dict with results key
        if isinstance(data, dict):
            for key in ("results", "sites", "data", "records", "features"):
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        for item in items:
                            rec = self._parse_item(item, state)
                            if rec:
                                records.append(rec)
                    return records

        return records

    def _parse_feature(self, feat: dict, state: str = "") -> dict | None:
        """Parse a GeoJSON Feature."""
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})

        if not geom or geom.get("type") != "Point":
            return None

        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            return None

        lon, lat = coords[0], coords[1]
        name = (props.get("site_name") or props.get("name") or
                props.get("label") or props.get("trinomial") or "")

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": props.get("state") or state,
            "period": props.get("period") or props.get("temporal") or "",
            "site_type": props.get("site_type") or props.get("type") or "",
            "source_id": props.get("trinomial") or props.get("id") or "",
            "description": props.get("description") or "",
        }

    def _parse_item(self, item: dict, state: str = "") -> dict | None:
        """Parse a flat dict record."""
        if isinstance(item, dict) and "geometry" in item:
            return self._parse_feature(item, state)

        lat = item.get("lat") or item.get("latitude") or item.get("y")
        lon = item.get("lon") or item.get("longitude") or item.get("lng") or item.get("x")

        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        name = (item.get("site_name") or item.get("name") or
                item.get("label") or item.get("trinomial") or "")

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": item.get("state") or state,
            "period": item.get("period") or item.get("temporal") or "",
            "site_type": item.get("site_type") or item.get("type") or "",
            "source_id": item.get("trinomial") or item.get("id") or "",
            "description": item.get("description") or "",
        }
