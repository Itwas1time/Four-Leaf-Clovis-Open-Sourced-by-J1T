"""Deduplicate fossil records by ~1km grid cells.

Groups records by grid cell, keeps the most notable specimen per cell,
and merges metadata from duplicates.
"""

import logging
import math

logger = logging.getLogger("scraper")

GRID_SIZE_DEG = 0.01  # ~1km at mid-latitudes


def _grid_key(lat: float, lon: float) -> tuple[int, int]:
    """Map coordinates to a grid cell key."""
    return (int(lat / GRID_SIZE_DEG), int(lon / GRID_SIZE_DEG))


def _specimen_score(rec: dict) -> int:
    """Score a specimen by how notable/complete it is. Higher = better."""
    score = 0
    if rec.get("common_name"):
        score += 50
    if rec.get("name"):
        score += 10
        # Bonus for species-level identification
        if " " in rec["name"] and not rec["name"].endswith(" sp."):
            score += 20
    if rec.get("time_period"):
        score += 10
    if rec.get("institution"):
        score += 5
    if rec.get("genus"):
        score += 5
    if rec.get("family"):
        score += 3
    if rec.get("order"):
        score += 3
    # Prefer records with age data
    if rec.get("age_mya") is not None:
        score += 15
    return score


def deduplicate_fossils(records: list[dict]) -> list[dict]:
    """Deduplicate fossil records by ~1km grid cells.

    For each grid cell, keep the highest-scoring specimen and merge
    metadata (sources, specimen count) from duplicates.
    """
    if not records:
        return []

    # Group by (taxon_group, genus_or_family, grid_cell)
    # This preserves different species at the same location
    grid: dict[tuple, list[dict]] = {}
    for rec in records:
        group = rec.get("taxon_group", "other")
        # Use genus for fine-grained dedup, fall back to family
        taxon_id = rec.get("genus") or rec.get("family") or rec.get("name", "")[:20]
        key = (group, taxon_id) + _grid_key(rec["lat"], rec["lon"])
        grid.setdefault(key, []).append(rec)

    deduped = []
    total_merged = 0

    for cell_key, cell_records in grid.items():
        if len(cell_records) == 1:
            cell_records[0]["specimen_count"] = 1
            deduped.append(cell_records[0])
            continue

        # Sort by score, keep best
        cell_records.sort(key=_specimen_score, reverse=True)
        best = dict(cell_records[0])
        best["specimen_count"] = len(cell_records)

        # Merge sources
        sources = set()
        institutions = set()
        for rec in cell_records:
            if rec.get("source"):
                sources.add(rec["source"])
            if rec.get("institution"):
                institutions.add(rec["institution"])

        best["source"] = "+".join(sorted(sources)) if sources else best.get("source", "")
        if institutions:
            best["institution"] = ", ".join(sorted(institutions)[:3])

        # Fill missing fields from other records
        for field in ("common_name", "time_period", "genus", "family", "order", "class"):
            if not best.get(field):
                for rec in cell_records[1:]:
                    if rec.get(field):
                        best[field] = rec[field]
                        break

        deduped.append(best)
        total_merged += len(cell_records) - 1

    logger.info(
        f"[fossil_dedup] {len(records)} input -> {len(deduped)} unique "
        f"({total_merged} merged across grid cells)"
    )

    # Log per-group stats
    group_counts = {}
    for rec in deduped:
        g = rec.get("taxon_group", "other")
        group_counts[g] = group_counts.get(g, 0) + 1
    for g, c in sorted(group_counts.items()):
        logger.info(f"[fossil_dedup]   {g}: {c}")

    return deduped
