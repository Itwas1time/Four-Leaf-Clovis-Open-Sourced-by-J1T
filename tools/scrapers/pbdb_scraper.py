"""PaleoBioDB (Paleobiology Database) scraper.

Scrapes US fossil occurrences from the Paleobiology Database.
May be slow/intermittent — use 60-second timeout.
If unreachable, skip — GBIF already indexes most PaleoBioDB data.

API: https://paleobiodb.org/data1.2/
Auth: None required
"""

import logging
from pathlib import Path

from .base_scraper import BaseScraper

logger = logging.getLogger("scraper")

# Queries to run against PaleoBioDB
QUERIES = [
    {"label": "dinosauria", "base_name": "Dinosauria", "max": 50000},
    {"label": "proboscidea", "base_name": "Proboscidea", "max": 10000},
    {"label": "carnivora", "base_name": "Carnivora", "max": 20000},
    {"label": "mammalia_pleist", "base_name": "Mammalia", "interval": "Pleistocene", "max": 30000},
    {"label": "reptilia_mesozoic", "base_name": "Reptilia", "interval": "Mesozoic", "max": 20000},
    {"label": "plantae", "base_name": "Plantae", "max": 15000},
]

BATCH_SIZE = 1000  # PaleoBioDB supports larger batches


class PBDBScraper(BaseScraper):
    source_id = "pbdb_fossils"
    source_name = "Paleobiology Database"
    base_url = "https://paleobiodb.org/data1.2/occs/list.json"
    rate_limit = 2.0
    timeout = 60
    max_retries = 2  # Fewer retries since it can be flaky

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)

    def scrape(self) -> list[dict]:
        records = []
        checkpoint = self._load_checkpoint()
        completed = set()
        if checkpoint:
            records = checkpoint.get("records", [])
            completed = set(checkpoint.get("completed", []))

        for query_def in QUERIES:
            label = query_def["label"]
            if label in completed:
                logger.info(f"[pbdb_fossils] Skipping {label} (already done)")
                continue

            logger.info(f"[pbdb_fossils] Querying: {label}")
            params = {
                "base_name": query_def["base_name"],
                "cc": "US",
                "show": "coords,loc,class",
                "limit": "all",
            }
            if "interval" in query_def:
                params["interval"] = query_def["interval"]

            try:
                resp = self._request_with_retry(self.base_url, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[pbdb_fossils] {label} FAILED: {e}")
                logger.warning("[pbdb_fossils] PaleoBioDB may be down — continuing with other sources")
                completed.add(label)
                self._save_checkpoint({"records": records, "completed": list(completed)})
                continue

            results = data.get("records", [])
            count = 0
            max_records = query_def.get("max", 50000)

            for occ in results:
                if count >= max_records:
                    break
                rec = self._parse_occurrence(occ)
                if rec:
                    records.append(rec)
                    count += 1

            logger.info(f"[pbdb_fossils] {label}: {count} records from {len(results)} results")
            completed.add(label)
            self._save_checkpoint({"records": records, "completed": list(completed)})

        logger.info(f"[pbdb_fossils] Total records: {len(records)}")
        return records

    def _parse_occurrence(self, occ: dict) -> dict | None:
        """Parse a PaleoBioDB occurrence record."""
        lat = occ.get("lat")
        lon = occ.get("lng")
        if lat is None or lon is None:
            return None

        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            return None

        if not (24.0 <= lat <= 72.0 and -180.0 <= lon <= -66.0):
            return None

        # PaleoBioDB uses different field names
        name = occ.get("tna") or occ.get("idn") or ""  # accepted name or identified name
        genus = occ.get("gnl") or ""  # genus name
        family = occ.get("fml") or ""  # family name
        order = occ.get("odl") or ""  # order name
        cls = occ.get("cll") or ""  # class name
        phylum = occ.get("phl") or ""  # phylum name

        # Time period
        early_interval = occ.get("oei") or ""  # early interval
        late_interval = occ.get("oli") or ""  # late interval
        time_period = early_interval
        if late_interval and late_interval != early_interval:
            time_period = f"{early_interval}-{late_interval}"

        # Age in Ma
        max_ma = occ.get("eag")  # max age in Ma
        min_ma = occ.get("lag")  # min age in Ma

        return {
            "name": name,
            "lat": lat,
            "lon": lon,
            "state": occ.get("stp") or "",  # state/province
            "kingdom": "",
            "phylum": phylum,
            "class": cls,
            "order": order,
            "family": family,
            "genus": genus,
            "species": name,
            "time_period": time_period,
            "age_max_ma": max_ma,
            "age_min_ma": min_ma,
            "source_id": str(occ.get("oid") or ""),  # occurrence ID
            "collection_id": str(occ.get("cid") or ""),  # collection ID
        }
