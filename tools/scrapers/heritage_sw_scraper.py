"""Source 9: Heritage Southwest Database."""

import logging
import re
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")


class HeritageSWScraper(BaseScraper):
    source_id = "heritage_sw"
    source_name = "Heritage Southwest Database"
    base_url = "https://www.archaeologysouthwest.org/projects/the-heritage-southwest-database/"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []

        # Try to find API or data download endpoints
        try:
            resp = self._request_with_retry(self.base_url)
            html = resp.text

            # Look for data/API links
            data_urls = self._find_data_links(html)
            for url in data_urls:
                try:
                    data_resp = self._request_with_retry(url)
                    ct = data_resp.headers.get("content-type", "")
                    if "json" in ct:
                        records.extend(self._parse_json(data_resp.json()))
                    elif "csv" in ct or url.endswith(".csv"):
                        records.extend(self._parse_csv(data_resp.text))
                except Exception as e:
                    logger.debug(f"[heritage_sw] Data URL {url} failed: {e}")
        except Exception as e:
            logger.warning(f"[heritage_sw] Main page failed: {e}")

        # Try alternate known endpoints
        alt_endpoints = [
            "https://www.archaeologysouthwest.org/api/sites",
            "https://www.archaeologysouthwest.org/data/heritage-southwest.json",
            "https://www.archaeologysouthwest.org/data/sites.geojson",
        ]
        for url in alt_endpoints:
            if records:
                break
            try:
                resp = self._request_with_retry(url)
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                        for feat in data.get("features", []):
                            rec = self._parse_geojson_feature(feat)
                            if rec:
                                records.append(rec)
                    else:
                        records.extend(self._parse_json(data))
            except Exception:
                continue

        return records

    def _find_data_links(self, html: str) -> list[str]:
        """Extract potential data download URLs from HTML."""
        links = []
        pattern = re.compile(
            r'href=["\']([^"\']*(?:\.json|\.csv|\.geojson|api|data|download)[^"\']*)["\']',
            re.IGNORECASE
        )
        for match in pattern.finditer(html):
            url = match.group(1)
            if not url.startswith("http"):
                url = f"https://www.archaeologysouthwest.org/{url.lstrip('/')}"
            links.append(url)
        return links[:10]

    def _parse_json(self, data) -> list[dict]:
        """Parse JSON data."""
        records = []
        items = data if isinstance(data, list) else data.get("sites", data.get("data", data.get("results", [])))
        for item in items:
            if not isinstance(item, dict):
                continue
            lat = item.get("lat") or item.get("latitude")
            lon = item.get("lon") or item.get("longitude") or item.get("lng")
            if lat is None or lon is None:
                continue
            try:
                records.append({
                    "name": item.get("name") or item.get("site_name") or "",
                    "lat": float(lat),
                    "lon": float(lon),
                    "state": item.get("state") or "",
                    "period": item.get("period") or item.get("culture") or "",
                    "site_type": item.get("site_type") or item.get("type") or "",
                    "source_id": str(item.get("id", "")),
                    "description": item.get("description") or item.get("culture") or "",
                })
            except (ValueError, TypeError):
                continue
        return records

    def _parse_csv(self, text: str) -> list[dict]:
        """Parse CSV text."""
        import csv
        import io
        records = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            lat = row.get("lat") or row.get("latitude") or row.get("Latitude")
            lon = row.get("lon") or row.get("longitude") or row.get("Longitude")
            if not lat or not lon:
                continue
            try:
                records.append({
                    "name": row.get("name") or row.get("site_name") or row.get("Site") or "",
                    "lat": float(lat),
                    "lon": float(lon),
                    "state": row.get("state") or row.get("State") or "",
                    "period": row.get("period") or row.get("culture") or row.get("Culture") or "",
                    "site_type": row.get("site_type") or row.get("type") or row.get("Type") or "",
                    "source_id": row.get("id") or "",
                    "description": row.get("description") or "",
                })
            except (ValueError, TypeError):
                continue
        return records

    def _parse_geojson_feature(self, feat: dict) -> dict | None:
        """Parse a GeoJSON feature."""
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})
        if not geom or geom.get("type") != "Point":
            return None
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            return None
        return {
            "name": props.get("name") or props.get("site_name") or "",
            "lat": coords[1],
            "lon": coords[0],
            "state": props.get("state") or "",
            "period": props.get("period") or props.get("culture") or "",
            "site_type": props.get("site_type") or props.get("type") or "",
            "source_id": str(props.get("id", "")),
            "description": props.get("description") or "",
        }
