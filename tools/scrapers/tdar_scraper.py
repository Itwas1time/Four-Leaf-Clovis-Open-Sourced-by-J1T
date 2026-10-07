"""Sources 2 & 3: tDAR (The Digital Archaeological Record) + NADB collection."""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

PAGE_SIZE = 100


class TDARScraper(BaseScraper):
    source_id = "tdar"
    source_name = "The Digital Archaeological Record"
    base_url = "https://core.tdar.org/api/search"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        start = checkpoint["start"] if checkpoint else 0
        if checkpoint:
            records = checkpoint.get("records", [])

        while True:
            params = {
                "resourceType": "DATASET,PROJECT,DOCUMENT",
                "latLong.minLat": 24,
                "latLong.maxLat": 50,
                "latLong.minLon": -125,
                "latLong.maxLon": -66,
                "startRecord": start,
                "recordsPerPage": PAGE_SIZE,
            }

            try:
                resp = self._request_with_retry(self.base_url, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[tdar] Failed at offset {start}: {e}")
                # Try alternate API patterns
                try:
                    resp = self._request_with_retry(
                        "https://core.tdar.org/api/search/resources",
                        params=params
                    )
                    data = resp.json()
                except Exception:
                    self._save_checkpoint({"start": start, "records": records})
                    break

            items = self._extract_items(data)
            if not items:
                break

            for item in items:
                rec = self._parse_record(item)
                if rec:
                    records.append(rec)

            start += PAGE_SIZE
            logger.info(f"[tdar] Page {start // PAGE_SIZE}: {len(records)} records total")

            if len(items) < PAGE_SIZE:
                break

            if start % 500 == 0:
                self._save_checkpoint({"start": start, "records": records})

        return records

    def _extract_items(self, data: dict | list) -> list:
        """Extract resource items from tDAR API response."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("resources", "results", "records", "data", "items"):
                if key in data:
                    val = data[key]
                    return val if isinstance(val, list) else []
            # Might be a single-level response with totalRecords
            if "totalRecords" in data:
                return data.get("resources", data.get("results", []))
        return []

    def _parse_record(self, item: dict) -> dict | None:
        """Parse a tDAR resource record."""
        lat = item.get("lat") or item.get("latitude")
        lon = item.get("lon") or item.get("longitude") or item.get("lng")

        # Try nested spatial info
        if lat is None and "latLong" in item:
            ll = item["latLong"]
            lat = ll.get("lat") or ll.get("centerLat")
            lon = ll.get("lon") or ll.get("lng") or ll.get("centerLon")

        if lat is None and "spatialInformation" in item:
            si = item["spatialInformation"]
            lat = si.get("centerLat") or si.get("lat")
            lon = si.get("centerLon") or si.get("lon") or si.get("lng")

        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        name = (item.get("title") or item.get("name") or
                item.get("resourceTitle") or "")

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": item.get("state") or "",
            "period": _extract_period(item),
            "site_type": item.get("resourceType") or item.get("type") or "",
            "source_id": str(item.get("id") or item.get("resourceId") or ""),
            "description": (item.get("description") or "")[:500],
        }


def _extract_period(item: dict) -> str:
    """Try to extract temporal keywords from a tDAR record."""
    temporal = item.get("temporalKeywords") or item.get("temporal") or []
    if isinstance(temporal, list):
        return "; ".join(str(t) for t in temporal[:3])
    return str(temporal)


class NADBScraper(BaseScraper):
    source_id = "nadb"
    source_name = "National Archeological Database (via tDAR)"
    base_url = "https://core.tdar.org/api/search"
    rate_limit = 2.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        start = checkpoint["start"] if checkpoint else 0
        if checkpoint:
            records = checkpoint.get("records", [])

        while True:
            params = {
                "collectionId": 31020,
                "startRecord": start,
                "recordsPerPage": PAGE_SIZE,
            }

            try:
                resp = self._request_with_retry(self.base_url, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[nadb] Failed at offset {start}: {e}")
                self._save_checkpoint({"start": start, "records": records})
                break

            items = data if isinstance(data, list) else data.get("resources", data.get("results", []))
            if not items or not isinstance(items, list):
                break

            tdar = TDARScraper(self.output_dir)
            for item in items:
                rec = tdar._parse_record(item)
                if rec:
                    rec["source_id"] = f"nadb_{rec.get('source_id', '')}"
                    records.append(rec)

            start += PAGE_SIZE
            logger.info(f"[nadb] Page {start // PAGE_SIZE}: {len(records)} records")

            if len(items) < PAGE_SIZE:
                break

            if start % 500 == 0:
                self._save_checkpoint({"start": start, "records": records})

        return records
