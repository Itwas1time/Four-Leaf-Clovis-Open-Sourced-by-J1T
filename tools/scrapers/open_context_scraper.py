"""Sources 5 & 6: Open Context JSON-LD API scraper."""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

PAGE_SIZE = 100


class OpenContextScraper(BaseScraper):
    source_id = "open_context"
    source_name = "Open Context"
    base_url = "https://opencontext.org/subjects-search/"
    rate_limit = 1.5

    # Subclasses can override to filter by project
    project_filter: str = ""

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        start = checkpoint["start"] if checkpoint else 0
        if checkpoint:
            records = checkpoint.get("records", [])

        # Try JSON API first, then GeoJSON endpoint
        api_urls = [
            self.base_url + ".json",
            self.base_url,
            "https://opencontext.org/search/.json",
        ]

        working_url = None
        for url in api_urls:
            try:
                test_params = {
                    "cat": "oc-gen-cat-site",
                    "disc-bbox": "-90,35,-85,40",
                    "rows": 5,
                }
                if self.project_filter:
                    test_params["proj"] = self.project_filter
                resp = self._request_with_retry(url, params=test_params)
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    working_url = url
                    logger.info(f"[{self.source_id}] Found working JSON endpoint: {url}")
                    break
            except Exception:
                continue

        if not working_url:
            logger.warning(f"[{self.source_id}] No working JSON endpoint found")
            return records

        while True:
            params = {
                "cat": "oc-gen-cat-site",
                "disc-bbox": "-125,24,-66,50",
                "start": start,
                "rows": PAGE_SIZE,
            }
            if self.project_filter:
                params["proj"] = self.project_filter

            try:
                resp = self._request_with_retry(working_url, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[{self.source_id}] Failed at offset {start}: {e}")
                self._save_checkpoint({"start": start, "records": records})
                break

            features = self._extract_features(data)
            if not features:
                break

            for feat in features:
                rec = self._parse_feature(feat)
                if rec:
                    records.append(rec)

            start += PAGE_SIZE
            logger.info(f"[{self.source_id}] {start} fetched, {len(records)} with coords")

            if len(features) < PAGE_SIZE:
                break

            if start % 500 == 0:
                self._save_checkpoint({"start": start, "records": records})

        return records

    def _extract_features(self, data: dict) -> list:
        """Extract features from Open Context geo-facet response."""
        # Open Context returns GeoJSON in the response
        if isinstance(data, dict):
            # Try geo-facet format
            if "type" in data and data["type"] == "FeatureCollection":
                return data.get("features", [])
            # Try nested features
            for key in ("features", "results", "oc-api:has-results"):
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        return val
            # Some responses nest under geo-facet
            if "oc-api:has-facets" in data:
                for facet in data["oc-api:has-facets"]:
                    if facet.get("type") == "oc-api:geo-facet":
                        return facet.get("oc-api:has-id-options", [])
        return []

    def _parse_feature(self, feat: dict) -> dict | None:
        """Parse an Open Context feature."""
        # GeoJSON Feature format
        if "geometry" in feat:
            geom = feat["geometry"]
            props = feat.get("properties", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    return {
                        "name": props.get("label") or props.get("title") or "",
                        "lat": coords[1],
                        "lon": coords[0],
                        "state": "",
                        "period": props.get("early date") or "",
                        "site_type": props.get("item category") or props.get("context") or "site",
                        "source_id": props.get("uri") or props.get("id") or "",
                        "description": props.get("project name") or "",
                    }

        # Flat dict with lat/lon
        lat = feat.get("lat") or feat.get("latitude")
        lon = feat.get("lon") or feat.get("longitude") or feat.get("lng")
        if lat is not None and lon is not None:
            try:
                return {
                    "name": feat.get("label") or feat.get("title") or "",
                    "lat": float(lat),
                    "lon": float(lon),
                    "state": "",
                    "period": str(feat.get("early date") or ""),
                    "site_type": feat.get("category") or "site",
                    "source_id": feat.get("uri") or feat.get("id") or "",
                    "description": feat.get("project name") or "",
                }
            except (ValueError, TypeError):
                pass

        return None


class OpenContextDigitalAntiquityScraper(OpenContextScraper):
    source_id = "open_context_da"
    source_name = "Open Context - Digital Antiquity Project"
    project_filter = "cdd78c10-e6da-42ef-9829-e792ce55bdd6"
