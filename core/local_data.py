"""
Local data loader for ARCHAEO-SCAN.

Reads the pre-collected JSON data from tools/processed/ and tools/raw_scrapes/
and provides spatial query methods. Everything stays offline — no network calls.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.schemas import BoundingBox

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "tools" / "processed"
RAW_DIR = PROJECT_ROOT / "tools" / "raw_scrapes"


def _load_json(path: Path) -> dict | list:
    """Load a JSON file, return empty dict on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return {}


def _records_from(data: dict | list) -> list[dict]:
    """Extract records list from a JSON file (handles both dict-wrapped and bare list)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("records", [])
    return []


class LocalDataStore:
    """
    Provides access to all pre-collected local data.

    Loads lazily on first access, caches in memory.
    """

    def __init__(self, project_root: Path | None = None):
        self._root = project_root or PROJECT_ROOT
        self._processed = self._root / "tools" / "processed"
        self._raw = self._root / "tools" / "raw_scrapes"
        self._cache: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Core datasets (processed, with coordinates)
    # ------------------------------------------------------------------

    @property
    def nrhp_sites(self) -> list[dict]:
        """25,658 National Register sites with geocoded lat/lon."""
        return self._get("nrhp", self._processed / "nrhp_geocoded.json")

    @property
    def master_sites(self) -> list[dict]:
        """5,695 merged archaeological sites from multiple sources."""
        return self._get("master", self._processed / "master_processed.json")

    @property
    def fossils(self) -> list[dict]:
        """16,990 fossil records with coordinates."""
        return self._get("fossils", self._processed / "fossil_processed.json")

    # ------------------------------------------------------------------
    # Raw datasets
    # ------------------------------------------------------------------

    @property
    def native_territories(self) -> list[dict]:
        """2,250 native territory polygons with geometry."""
        return self._get("native_land", self._raw / "native_land.json")

    @property
    def bia_tribal(self) -> list[dict]:
        """335 BIA tribal boundary records."""
        return self._get("bia_tribal", self._raw / "bia_tribal.json")

    @property
    def epa_tribal(self) -> list[dict]:
        """14,448 EPA tribal records."""
        return self._get("epa_tribal", self._raw / "epa_tribal.json")

    @property
    def tiger_aiannh(self) -> list[dict]:
        """862 Census AIANNH boundary records."""
        return self._get("tiger_aiannh", self._raw / "tiger_aiannh.json")

    @property
    def open_context(self) -> list[dict]:
        """330,191 Open Context archaeological records."""
        return self._get("open_context", self._raw / "open_context.json")

    @property
    def gbif_fossils(self) -> list[dict]:
        """142,550 GBIF fossil records."""
        return self._get("gbif_fossils", self._raw / "gbif_fossils.json")

    @property
    def idigbio_fossils(self) -> list[dict]:
        """18,883 iDigBio fossil records."""
        return self._get("idigbio", self._raw / "idigbio_fossils.json")

    @property
    def neotoma_fossils(self) -> list[dict]:
        """2,873 Neotoma paleoecology records."""
        return self._get("neotoma", self._raw / "neotoma_fossils.json")

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def sites_in_bbox(self, bbox: BoundingBox) -> list[dict]:
        """All known archaeological sites (NRHP + master) within bbox."""
        return self._filter_bbox(self.nrhp_sites, bbox) + self._filter_bbox(self.master_sites, bbox)

    def fossils_in_bbox(self, bbox: BoundingBox) -> list[dict]:
        """All fossil records within bbox."""
        return self._filter_bbox(self.fossils, bbox)

    def all_sites_in_bbox(self, bbox: BoundingBox) -> dict[str, list[dict]]:
        """All datasets filtered to bbox, keyed by source name."""
        return {
            "nrhp": self._filter_bbox(self.nrhp_sites, bbox),
            "master": self._filter_bbox(self.master_sites, bbox),
            "fossils": self._filter_bbox(self.fossils, bbox),
        }

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def inventory(self) -> list[dict]:
        """Return file inventory with record counts and sizes."""
        result = []
        for label, path in self._all_files():
            if not path.exists():
                continue
            size_mb = path.stat().st_size / (1024 * 1024)
            try:
                data = _load_json(path)
                records = _records_from(data)
                count = len(records)
            except Exception:
                count = 0
            result.append({
                "label": label,
                "path": str(path),
                "size_mb": round(size_mb, 2),
                "record_count": count,
            })
        return result

    def inventory_summary(self) -> dict[str, Any]:
        """Aggregate stats across all data files."""
        inv = self.inventory()
        total_records = sum(i["record_count"] for i in inv)
        total_size = sum(i["size_mb"] for i in inv)
        non_empty = [i for i in inv if i["record_count"] > 0]
        return {
            "total_files": len(inv),
            "files_with_data": len(non_empty),
            "total_records": total_records,
            "total_size_mb": round(total_size, 2),
            "datasets": inv,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, key: str, path: Path) -> list[dict]:
        if key not in self._cache:
            if path.exists():
                data = _load_json(path)
                self._cache[key] = _records_from(data)
            else:
                self._cache[key] = []
        return self._cache[key]

    @staticmethod
    def _filter_bbox(records: list[dict], bbox: BoundingBox) -> list[dict]:
        """Filter records with lat/lon to those within bbox."""
        results = []
        for r in records:
            lat = r.get("lat")
            lon = r.get("lon")
            if lat is None or lon is None:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue
            if bbox.min_lat <= lat <= bbox.max_lat and bbox.min_lon <= lon <= bbox.max_lon:
                results.append(r)
        return results

    def _all_files(self) -> list[tuple[str, Path]]:
        files = []
        # Processed
        for p in sorted(self._processed.glob("*.json")):
            files.append((f"processed/{p.name}", p))
        # Raw
        for p in sorted(self._raw.glob("*.json")):
            files.append((f"raw/{p.name}", p))
        return files
