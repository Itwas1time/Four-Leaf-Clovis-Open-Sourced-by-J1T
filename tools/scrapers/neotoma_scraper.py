"""Source 8: Neotoma Paleoecology Database REST API v2."""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# Dataset types that indicate human activity
HUMAN_ACTIVITY_TYPES = {
    "vertebrate fauna", "charcoal", "geochronologic",
    "pollen", "plant macrofossil", "diatom",
    "loss-on-ignition", "geochemistry",
}

BATCH_SIZE = 500


class NeotomaScraper(BaseScraper):
    source_id = "neotoma"
    source_name = "Neotoma Paleoecology Database"
    base_url = "https://api.neotomadb.org/v2.0/data/sites"
    rate_limit = 1.0

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        offset = checkpoint["offset"] if checkpoint else 0
        if checkpoint:
            records = checkpoint.get("records", [])

        while True:
            params = {
                "bbox": "-125,24,-66,50",
                "limit": BATCH_SIZE,
                "offset": offset,
            }

            try:
                resp = self._request_with_retry(self.base_url, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[neotoma] Failed at offset {offset}: {e}")
                self._save_checkpoint({"offset": offset, "records": records})
                break

            sites = self._extract_sites(data)
            if not sites:
                break

            for site in sites:
                rec = self._parse_site(site)
                if rec:
                    records.append(rec)

            offset += BATCH_SIZE
            logger.info(f"[neotoma] Offset {offset}: {len(records)} relevant sites")

            if len(sites) < BATCH_SIZE:
                break

            if offset % 2000 == 0:
                self._save_checkpoint({"offset": offset, "records": records})

        return records

    def _extract_sites(self, data: dict) -> list:
        """Extract site list from Neotoma API response."""
        if isinstance(data, dict):
            if data.get("status") == "success" and "data" in data:
                d = data["data"]
                if isinstance(d, list):
                    return d
            if "data" in data:
                d = data["data"]
                if isinstance(d, list):
                    return d
                if isinstance(d, dict):
                    return d.get("sites", d.get("results", []))
            for key in ("sites", "results"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        if isinstance(data, list):
            return data
        return []

    def _parse_site(self, site: dict) -> dict | None:
        """Parse a Neotoma site record."""
        import json as _json

        lat = None
        lon = None

        # Neotoma v2 stores coordinates in a JSON string under "geography"
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

        # Fallback to direct lat/lon fields
        if lat is None:
            lat = site.get("lat") or site.get("latitude")
            lon = site.get("lon") or site.get("longitude") or site.get("lng")

        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        # Extract dataset types from nested collectionunits structure
        dataset_types = set()
        for cu in (site.get("collectionunits") or []):
            if isinstance(cu, dict):
                for ds in (cu.get("datasets") or []):
                    if isinstance(ds, dict):
                        dt = ds.get("datasettype") or ""
                        if dt:
                            dataset_types.add(dt.lower())

        # Also check flat dataset fields
        for dt in (site.get("datasetTypes") or site.get("datasettypes") or
                   site.get("datasets") or []):
            if isinstance(dt, str):
                dataset_types.add(dt.lower())
            elif isinstance(dt, dict):
                t = dt.get("datasettype") or dt.get("type") or ""
                if t:
                    dataset_types.add(t.lower())

        # Keep sites with relevant dataset types, or keep all if no type info
        if dataset_types and not dataset_types.intersection(HUMAN_ACTIVITY_TYPES):
            return None

        name = site.get("sitename") or site.get("site_name") or site.get("name") or ""
        site_type = site.get("sitetype") or site.get("site_type") or ""

        # Age info
        max_age = site.get("maxage") or site.get("max_age") or ""
        min_age = site.get("minage") or site.get("min_age") or ""
        period = ""
        if max_age:
            period = f"{max_age}-{min_age} BP" if min_age else f"{max_age} BP"

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": "",
            "period": period,
            "site_type": site_type or "paleoecological",
            "source_id": str(site.get("siteid") or site.get("site_id") or site.get("id") or ""),
            "description": f"Dataset types: {', '.join(dataset_types)}" if dataset_types else "",
        }
