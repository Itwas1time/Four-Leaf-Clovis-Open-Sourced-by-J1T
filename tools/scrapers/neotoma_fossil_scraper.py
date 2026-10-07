"""Neotoma Paleoecology Database fossil scraper.

Scrapes FAUNMAP vertebrate fauna, pollen, plant macrofossil, charcoal,
and geochronologic datasets for paleontological overlay.

API: https://api.neotomadb.org/v2.0/data/datasets
Auth: None required
Rate limit: 1 sec between requests
"""

import json as _json
import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# Dataset types relevant to paleontology
PALEO_DATASET_TYPES = [
    "vertebrate fauna",
    "pollen",
    "plant macrofossil",
    "charcoal",
    "geochronologic",
]

BATCH_SIZE = 500


class NeotomaFossilScraper(BaseScraper):
    source_id = "neotoma_fossils"
    source_name = "Neotoma Paleoecology Database (Fossils)"
    base_url = "https://api.neotomadb.org/v2.0/data/datasets"
    rate_limit = 1.0
    timeout = 60

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        completed_types = set()
        if checkpoint:
            records = checkpoint.get("records", [])
            completed_types = set(checkpoint.get("completed_types", []))

        for dstype in PALEO_DATASET_TYPES:
            if dstype in completed_types:
                logger.info(f"[neotoma_fossils] Skipping {dstype} (already done)")
                continue

            logger.info(f"[neotoma_fossils] Scraping dataset type: {dstype}")
            offset = 0

            while True:
                params = {
                    "datasettype": dstype,
                    "limit": BATCH_SIZE,
                    "offset": offset,
                }

                try:
                    resp = self._request_with_retry(self.base_url, params=params)
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"[neotoma_fossils] {dstype} failed at offset {offset}: {e}")
                    self._save_checkpoint({
                        "records": records,
                        "completed_types": list(completed_types),
                    })
                    break

                sites = self._extract_data(data)
                if not sites:
                    break

                batch_count = 0
                for item in sites:
                    rec = self._parse_dataset(item, dstype)
                    if rec:
                        records.append(rec)
                        batch_count += 1

                offset += BATCH_SIZE
                logger.info(f"[neotoma_fossils] {dstype} offset {offset}: +{batch_count} (total {len(records)})")

                if len(sites) < BATCH_SIZE:
                    break

                if offset % 5000 == 0:
                    self._save_checkpoint({
                        "records": records,
                        "completed_types": list(completed_types),
                    })

            completed_types.add(dstype)
            self._save_checkpoint({
                "records": records,
                "completed_types": list(completed_types),
            })

        logger.info(f"[neotoma_fossils] Total records: {len(records)}")
        return records

    def _extract_data(self, data: dict) -> list:
        """Extract dataset list from Neotoma API response."""
        if isinstance(data, dict):
            if data.get("status") == "success" and "data" in data:
                d = data["data"]
                if isinstance(d, list):
                    return d
                if isinstance(d, dict):
                    return d.get("result", d.get("results", d.get("datasets", [])))
            if "data" in data:
                d = data["data"]
                if isinstance(d, list):
                    return d
            for key in ("datasets", "results", "result"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        if isinstance(data, list):
            return data
        return []

    def _parse_dataset(self, item: dict, dstype: str) -> dict | None:
        """Parse a Neotoma dataset record."""
        lat = None
        lon = None

        # Try site-level geography
        site = item.get("site") or item
        geography = site.get("geography")
        if isinstance(geography, str):
            try:
                geom = _json.loads(geography)
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        lon, lat = float(coords[0]), float(coords[1])
            except (ValueError, _json.JSONDecodeError):
                pass
        elif isinstance(geography, dict):
            if geography.get("type") == "Point":
                coords = geography.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = float(coords[0]), float(coords[1])

        # Fallback: direct lat/lon fields
        if lat is None:
            lat = site.get("lat") or site.get("latitude")
            lon = site.get("lon") or site.get("longitude") or site.get("lng")

        # Fallback: location object
        if lat is None:
            loc = site.get("location") or item.get("location") or {}
            if isinstance(loc, dict):
                lat = loc.get("latitude") or loc.get("lat")
                lon = loc.get("longitude") or loc.get("lon") or loc.get("lng")

        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        # Filter to US bounding box
        if not (24.0 <= lat <= 72.0 and -180.0 <= lon <= -66.0):
            return None

        name = (site.get("sitename") or site.get("site_name") or
                site.get("name") or item.get("datasetname") or "")

        # Age info
        age_old = item.get("ageold") or item.get("maxage") or site.get("maxage")
        age_young = item.get("ageyoung") or item.get("minage") or site.get("minage")

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": site.get("stateprovince") or site.get("state") or "",
            "dataset_type": dstype,
            "age_old": age_old,
            "age_young": age_young,
            "source_id": str(item.get("datasetid") or item.get("siteid") or
                            site.get("siteid") or ""),
            "database": item.get("database") or "",
        }
