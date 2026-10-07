"""Step 4: Deduplicate records by name similarity + coordinate proximity."""

import logging
import math
from difflib import SequenceMatcher

logger = logging.getLogger("scraper")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers between two WGS84 points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _name_similarity(name1: str, name2: str) -> float:
    """Similarity ratio between two names (0-1)."""
    if not name1 or not name2:
        return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def _record_completeness(record: dict) -> int:
    """Score how complete a record is (more fields = higher score)."""
    score = 0
    for field in ("name", "period", "site_type", "description", "source_id", "state"):
        val = record.get(field, "")
        if val:
            score += 1
            score += min(len(str(val)), 100)  # Bonus for longer values
    return score


def _merge_records(primary: dict, secondary: dict) -> dict:
    """Merge two duplicate records, keeping the best data from each."""
    merged = dict(primary)

    # Merge sources
    sources_p = set(merged.get("source", "").split("+"))
    sources_s = set(secondary.get("source", "").split("+"))
    merged["source"] = "+".join(sorted(sources_p | sources_s))

    # Keep highest confidence
    merged["confidence"] = max(
        merged.get("confidence", 0.5),
        secondary.get("confidence", 0.5)
    )

    # Fill in missing fields from secondary
    for field in ("name", "period", "site_type", "description", "state"):
        if not merged.get(field) and secondary.get(field):
            merged[field] = secondary[field]
        elif field == "description":
            # Keep longer description
            if len(str(secondary.get(field, ""))) > len(str(merged.get(field, ""))):
                merged[field] = secondary[field]

    # Merge layers
    layers_p = merged.get("layers", {})
    layers_s = secondary.get("layers", {})
    for layer, val in layers_s.items():
        if layer not in layers_p:
            layers_p[layer] = val
    merged["layers"] = layers_p

    return merged


def deduplicate_records(records: list[dict], existing_sites: list[tuple] | None = None) -> list[dict]:
    """Deduplicate records against each other and against existing embedded sites.

    Args:
        records: List of classified records with 'layers' field.
        existing_sites: Optional list of (name, lon, lat, ...) tuples from
            the current known_sites_expanded.py data.

    Returns:
        Deduplicated list of records.
    """
    if not records:
        return []

    # Build spatial index using grid cells (~10km resolution)
    GRID_SIZE = 0.1  # ~10km at mid-latitudes

    def _grid_key(lat: float, lon: float) -> tuple[int, int]:
        return (int(lat / GRID_SIZE), int(lon / GRID_SIZE))

    def _neighbor_keys(key: tuple[int, int]) -> list[tuple[int, int]]:
        r, c = key
        return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]

    # First, deduplicate against existing embedded sites
    existing_grid: dict[tuple[int, int], list[tuple[str, float, float]]] = {}
    if existing_sites:
        for site in existing_sites:
            name, lon, lat = site[0], site[1], site[2]
            key = _grid_key(lat, lon)
            existing_grid.setdefault(key, []).append((name, lon, lat))

    # Filter out records that duplicate existing sites
    new_records = []
    duped_existing = 0
    for rec in records:
        lat, lon = rec["lat"], rec["lon"]
        key = _grid_key(lat, lon)
        is_dup = False

        for nkey in _neighbor_keys(key):
            for ename, elon, elat in existing_grid.get(nkey, []):
                dist = _haversine_km(lat, lon, elat, elon)
                if dist < 0.1:  # 100m
                    is_dup = True
                    break
                if dist < 1.0 and _name_similarity(rec.get("name", ""), ename) > 0.8:
                    is_dup = True
                    break
            if is_dup:
                break

        if is_dup:
            duped_existing += 1
        else:
            new_records.append(rec)

    if existing_sites:
        logger.info(f"[dedup] {duped_existing} records matched existing sites")

    # Now deduplicate among new records
    # Sort by completeness (best records first)
    new_records.sort(key=_record_completeness, reverse=True)

    grid: dict[tuple[int, int], list[int]] = {}  # grid cell -> list of indices
    kept = []
    merged_count = 0

    for rec in new_records:
        lat, lon = rec["lat"], rec["lon"]
        key = _grid_key(lat, lon)
        found_dup = False

        for nkey in _neighbor_keys(key):
            for idx in grid.get(nkey, []):
                existing_rec = kept[idx]
                dist = _haversine_km(lat, lon, existing_rec["lat"], existing_rec["lon"])

                if dist < 0.1:  # 100m = same site regardless of name
                    kept[idx] = _merge_records(existing_rec, rec)
                    found_dup = True
                    merged_count += 1
                    break

                if dist < 1.0:  # 1km + name similarity check
                    sim = _name_similarity(rec.get("name", ""), existing_rec.get("name", ""))
                    if sim > 0.8:
                        kept[idx] = _merge_records(existing_rec, rec)
                        found_dup = True
                        merged_count += 1
                        break

            if found_dup:
                break

        if not found_dup:
            idx = len(kept)
            kept.append(rec)
            grid.setdefault(key, []).append(idx)

    logger.info(
        f"[dedup] {len(records)} input -> {len(kept)} unique "
        f"({merged_count} merged, {duped_existing} matched existing)"
    )
    return kept
