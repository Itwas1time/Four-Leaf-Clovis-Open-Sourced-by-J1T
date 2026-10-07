"""Source 10: Crow Canyon Archaeological Center research reports."""

import logging
import re
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")


class CrowCanyonScraper(BaseScraper):
    source_id = "crow_canyon"
    source_name = "Crow Canyon Archaeological Center"
    base_url = "https://www.crowcanyon.org/researchreports/"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []

        # Try data endpoints
        data_endpoints = [
            "https://www.crowcanyon.org/ResearchReports/api/sites",
            "https://www.crowcanyon.org/ArchaeologicalDatabase/",
            "https://www.crowcanyon.org/data/sites.json",
            "https://www.crowcanyon.org/data/sites.geojson",
        ]

        for url in data_endpoints:
            try:
                resp = self._request_with_retry(url)
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                        for feat in data.get("features", []):
                            rec = self._parse_geojson(feat)
                            if rec:
                                records.append(rec)
                    else:
                        records.extend(self._parse_json(data))
                    if records:
                        logger.info(f"[crow_canyon] Got {len(records)} from {url}")
                        break
            except Exception as e:
                logger.debug(f"[crow_canyon] {url} failed: {e}")

        # Try the research reports page for links
        if not records:
            try:
                resp = self._request_with_retry(self.base_url)
                records = self._scrape_reports_page(resp.text)
            except Exception as e:
                logger.warning(f"[crow_canyon] Reports page failed: {e}")

        return records

    def _parse_json(self, data) -> list[dict]:
        """Parse JSON response."""
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
                    "state": item.get("state") or "CO",
                    "period": item.get("period") or "",
                    "site_type": item.get("site_type") or item.get("type") or "Ancestral Puebloan",
                    "source_id": str(item.get("id", "")),
                    "description": item.get("description") or "",
                })
            except (ValueError, TypeError):
                continue
        return records

    def _parse_geojson(self, feat: dict) -> dict | None:
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
            "state": props.get("state") or "CO",
            "period": props.get("period") or "",
            "site_type": props.get("site_type") or "Ancestral Puebloan",
            "source_id": str(props.get("id", "")),
            "description": props.get("description") or "",
        }

    def _scrape_reports_page(self, html: str) -> list[dict]:
        """Try to extract data links from the reports page."""
        records = []
        pattern = re.compile(
            r'href=["\']([^"\']*(?:\.json|\.csv|\.geojson|\.shp|data|database)[^"\']*)["\']',
            re.IGNORECASE
        )
        for match in pattern.finditer(html):
            url = match.group(1)
            if not url.startswith("http"):
                url = f"https://www.crowcanyon.org/{url.lstrip('/')}"
            try:
                resp = self._request_with_retry(url)
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                    records.extend(self._parse_json(data))
            except Exception:
                continue
        return records
