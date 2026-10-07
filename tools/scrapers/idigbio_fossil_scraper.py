"""iDigBio (Integrated Digitized Biocollections) fossil scraper.

Scrapes US fossil specimens via the iDigBio search API.

API: https://search.idigbio.org/v2/search/records/ (POST)
Auth: None required
Rate limit: 1 sec between requests
"""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

BATCH_SIZE = 100  # iDigBio recommends smaller batches

# Single broad query — iDigBio doesn't support taxonomic filters via POST rq well.
# We scrape all US fossil specimens and let the classifier sort them.
TARGET_QUERIES = [
    {"label": "all_fossils", "rq": {"basisofrecord": "fossilspecimen",
                                     "country": "united states"}, "max": 50000},
]

FIELDS = [
    "scientificname", "geopoint", "stateprovince", "locality",
    "class", "order", "family", "genus", "kingdom", "phylum",
    "institutioncode",
]


class IDigBioFossilScraper(BaseScraper):
    source_id = "idigbio_fossils"
    source_name = "iDigBio Fossil Specimens"
    base_url = "https://search.idigbio.org/v2/search/records/"
    rate_limit = 1.0
    timeout = 60

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        completed_queries = set()
        if checkpoint:
            records = checkpoint.get("records", [])
            completed_queries = set(checkpoint.get("completed_queries", []))

        for query_def in TARGET_QUERIES:
            label = query_def["label"]
            if label in completed_queries:
                logger.info(f"[idigbio_fossils] Skipping {label} (already done)")
                continue

            max_records = query_def.get("max", 50000)
            logger.info(f"[idigbio_fossils] Querying: {label} (max {max_records})")

            offset = 0
            query_count = 0

            while query_count < max_records:
                body = {
                    "rq": query_def["rq"],
                    "limit": BATCH_SIZE,
                    "offset": offset,
                    "fields": FIELDS,
                }

                try:
                    resp = self._request_with_retry(
                        self.base_url, method="POST", json_body=body,
                    )
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"[idigbio_fossils] {label} failed at offset {offset}: {e}")
                    break

                items = data.get("items", [])
                if not items:
                    break

                if offset % 1000 == 0:
                    logger.info(f"[idigbio_fossils] {label} offset {offset}: {query_count} parsed so far")

                for item in items:
                    rec = self._parse_record(item)
                    if rec:
                        records.append(rec)
                        query_count += 1

                offset += BATCH_SIZE

                if len(items) < BATCH_SIZE:
                    break

                total_available = data.get("itemCount", 0)
                if offset >= total_available:
                    break

                if query_count % 5000 == 0 and query_count > 0:
                    self._save_checkpoint({
                        "records": records,
                        "completed_queries": list(completed_queries),
                    })

            logger.info(f"[idigbio_fossils] {label}: {query_count} records")
            completed_queries.add(label)
            self._save_checkpoint({
                "records": records,
                "completed_queries": list(completed_queries),
            })

        logger.info(f"[idigbio_fossils] Total records: {len(records)}")
        return records

    def _parse_record(self, item: dict) -> dict | None:
        """Parse an iDigBio search result item."""
        # iDigBio wraps fields in "indexTerms" and/or "data"
        idx = item.get("indexTerms") or {}
        data = item.get("data") or {}

        # Coordinates: prefer indexTerms.geopoint, then data fields
        lat = None
        lon = None
        geopoint = idx.get("geopoint")
        if isinstance(geopoint, dict):
            lat = geopoint.get("lat")
            lon = geopoint.get("lon")

        if lat is None:
            lat = idx.get("lat") or data.get("dwc:decimalLatitude")
            lon = idx.get("lon") or data.get("dwc:decimalLongitude")

        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        # US bounding box
        if not (24.0 <= lat <= 72.0 and -180.0 <= lon <= -66.0):
            return None

        # Merge indexed + raw data fields
        def _get(key_idx, key_dwc=""):
            return idx.get(key_idx) or data.get(key_dwc) or ""

        return {
            "name": _get("scientificname", "dwc:scientificName"),
            "lat": lat,
            "lon": lon,
            "state": _get("stateprovince", "dwc:stateProvince"),
            "kingdom": _get("kingdom", "dwc:kingdom"),
            "phylum": _get("phylum", "dwc:phylum"),
            "class": _get("class", "dwc:class"),
            "order": _get("order", "dwc:order"),
            "family": _get("family", "dwc:family"),
            "genus": _get("genus", "dwc:genus"),
            "species": _get("scientificname", "dwc:scientificName"),
            "institution": _get("institutioncode", "dwc:institutionCode"),
            "source_id": item.get("uuid") or "",
            "locality": _get("locality", "dwc:locality"),
        }
