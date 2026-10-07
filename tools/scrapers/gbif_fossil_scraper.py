"""GBIF (Global Biodiversity Information Facility) fossil specimen scraper.

Scrapes US fossil occurrences using the GBIF Occurrence API.
Uses taxonKey-based queries for accurate taxonomic filtering.

API: https://api.gbif.org/v1/occurrence/search
Auth: None required
Rate limit: 1-2 sec between requests
Max per request: 300 records
"""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

BATCH_SIZE = 300

# Verified GBIF taxon keys (backbone taxonomy)
# Each entry: (label, taxonKey, max_records)
TAXON_QUERIES = [
    # --- Dinosaur families ---
    ("tyrannosauridae", 4822619, 5000),
    ("ceratopsidae", 3238858, 5000),
    ("hadrosauridae", 4823263, 5000),
    ("stegosauridae", 3238864, 5000),
    ("diplodocidae", 3239001, 5000),
    ("allosauridae", 4822582, 5000),
    ("camarasauridae", 4822793, 5000),
    ("dromaeosauridae", 3238979, 5000),
    ("ornithomimidae", 4822888, 5000),
    ("pachycephalosauridae", 4823072, 5000),
    ("titanosauridae", 4822754, 5000),
    ("ankylosauridae", 9359, 5000),
    ("brachiosauridae", 4822671, 5000),
    # --- Marine reptiles ---
    ("mosasauridae", 3238752, 5000),
    # --- Megafauna genera ---
    ("mammuthus", 8411230, 5000),
    ("mammut", 3240497, 5000),
    ("smilodon", 3240061, 5000),
    ("arctodus", 4833639, 5000),
    ("megalonyx", 8474690, 5000),
    ("paramylodon", 4834511, 5000),
    ("castoroides", 4574461, 5000),
    ("camelops", 4835773, 5000),
    ("bison", 2441175, 5000),
    ("equus", 8652950, 20000),
    ("glyptotherium", 4834281, 5000),
    # --- Broad taxonomic groups (sampled) ---
    ("mammalia", 359, 50000),
    ("reptilia_phylum", 44, 30000),  # GBIF has Reptilia under phylum 44
    ("plantae", 6, 30000),
]


class GBIFFossilScraper(BaseScraper):
    source_id = "gbif_fossils"
    source_name = "GBIF Fossil Specimens"
    base_url = "https://api.gbif.org/v1/occurrence/search"
    rate_limit = 1.5
    timeout = 60

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        completed = set()
        if checkpoint:
            records = checkpoint.get("records", [])
            completed = set(checkpoint.get("completed", []))

        seen_ids = {r.get("source_id") for r in records if r.get("source_id")}

        for label, taxon_key, max_records in TAXON_QUERIES:
            if label in completed:
                logger.info(f"[gbif_fossils] Skipping {label} (already done)")
                continue

            logger.info(f"[gbif_fossils] Querying: {label} (taxonKey={taxon_key}, max={max_records})")
            query_count = 0
            offset = 0

            while query_count < max_records:
                params = {
                    "taxonKey": str(taxon_key),
                    "country": "US",
                    "hasCoordinate": "true",
                    "basisOfRecord": "FOSSIL_SPECIMEN",
                    "limit": BATCH_SIZE,
                    "offset": offset,
                }

                try:
                    resp = self._request_with_retry(self.base_url, params=params)
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"[gbif_fossils] {label} failed at offset {offset}: {e}")
                    break

                results = data.get("results", [])
                if not results:
                    break

                batch_new = 0
                for occ in results:
                    rec = self._parse_occurrence(occ)
                    if rec and rec["source_id"] not in seen_ids:
                        seen_ids.add(rec["source_id"])
                        records.append(rec)
                        query_count += 1
                        batch_new += 1

                offset += BATCH_SIZE
                total_available = data.get("count", 0)

                if offset >= total_available or len(results) < BATCH_SIZE:
                    break

                # Checkpoint every 5000 records
                if query_count % 5000 == 0 and query_count > 0:
                    self._save_checkpoint({
                        "completed": list(completed),
                        "records": records,
                    })

            logger.info(f"[gbif_fossils] {label}: {query_count} new records (total {len(records)})")
            completed.add(label)
            self._save_checkpoint({
                "completed": list(completed),
                "records": records,
            })

        logger.info(f"[gbif_fossils] Total raw records: {len(records)}")
        return records

    def _parse_occurrence(self, occ: dict) -> dict | None:
        """Parse a GBIF occurrence record into our format."""
        lat = occ.get("decimalLatitude")
        lon = occ.get("decimalLongitude")
        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        # Must be in US
        if not (24.0 <= lat <= 72.0 and -180.0 <= lon <= -66.0):
            return None

        scientific_name = occ.get("scientificName") or occ.get("species") or ""
        genus = occ.get("genus") or ""
        species = occ.get("species") or ""

        return {
            "name": scientific_name,
            "lat": lat,
            "lon": lon,
            "state": occ.get("stateProvince", ""),
            "kingdom": occ.get("kingdom", ""),
            "phylum": occ.get("phylum", ""),
            "class": occ.get("class", ""),
            "order": occ.get("order", ""),
            "family": occ.get("family", ""),
            "genus": genus,
            "species": species,
            "institution": occ.get("institutionCode", ""),
            "dataset": occ.get("datasetName", ""),
            "source_id": str(occ.get("gbifID", "")),
            "year": occ.get("year"),
        }
