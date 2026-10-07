#!/usr/bin/env python3
"""
FOURLEAFCLOVIS Archaeological Database Harvester

Scrapes 18 archaeological databases, processes/deduplicates results,
and embeds them into the atlas data files.

Usage:
    python tools/scrape_databases.py --all                    # Scrape all sources
    python tools/scrape_databases.py --source nrhp            # Scrape one source
    python tools/scrape_databases.py --source dinaa --source tdar  # Scrape multiple
    python tools/scrape_databases.py --process                # Process raw scrapes only
    python tools/scrape_databases.py --embed                  # Embed processed data only
    python tools/scrape_databases.py --dry-run --all          # Report what would happen
    python tools/scrape_databases.py --status                 # Show scrape status
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root and tools dir are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

TOOLS_DIR = Path(__file__).resolve().parent
RAW_DIR = TOOLS_DIR / "raw_scrapes"
PROCESSED_DIR = TOOLS_DIR / "processed"
LOG_FILE = TOOLS_DIR / "scrape.log"

RAW_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Logging setup
logger = logging.getLogger("scraper")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def get_scraper_classes() -> dict:
    """Import and return all scraper classes."""
    from tools.scrapers import SCRAPER_MAP
    return SCRAPER_MAP


def scrape_sources(source_ids: list[str], dry_run: bool = False) -> dict[str, list[dict]]:
    """Run scrapers for specified sources. Returns {source_id: [records]}."""
    scraper_map = get_scraper_classes()
    results = {}

    for sid in source_ids:
        if sid not in scraper_map:
            logger.warning(f"Unknown source: {sid}. Available: {list(scraper_map.keys())}")
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would scrape: {sid}")
            results[sid] = []
            continue

        scraper_cls = scraper_map[sid]
        scraper = scraper_cls(RAW_DIR)
        start = time.time()

        try:
            records = scraper.run()
            elapsed = time.time() - start
            logger.info(f"[{sid}] Scraped {len(records)} records in {elapsed:.1f}s")
            results[sid] = records
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[{sid}] FAILED after {elapsed:.1f}s: {e}")
            results[sid] = []

    return results


def process_raw_scrapes(dry_run: bool = False) -> list[dict]:
    """Load raw scrapes, normalize, classify, and deduplicate."""
    from tools.processors.normalizer import normalize_records
    from tools.processors.classifier import classify_records
    from tools.processors.deduplicator import deduplicate_records

    all_normalized = []

    # Load all raw scrape files
    for raw_file in sorted(RAW_DIR.glob("*.json")):
        try:
            with open(raw_file) as f:
                data = json.load(f)
            source = data.get("source", raw_file.stem)
            records = data.get("records", [])
            if not records:
                logger.info(f"[process] {raw_file.name}: no records, skipping")
                continue

            normalized = normalize_records(records, source)
            all_normalized.extend(normalized)
            logger.info(f"[process] {raw_file.name}: {len(normalized)} normalized from {len(records)} raw")
        except Exception as e:
            logger.error(f"[process] Failed to load {raw_file.name}: {e}")

    if not all_normalized:
        logger.warning("[process] No normalized records to process")
        return []

    logger.info(f"[process] Total normalized: {len(all_normalized)}")

    # Classify
    classified = classify_records(all_normalized)

    # Load existing sites for deduplication
    existing_sites = []
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from atlas.gui.data.known_sites_expanded import get_known_sites_geojson
        geojson = get_known_sites_geojson()
        for feat in geojson["features"]:
            props = feat["properties"]
            coords = feat["geometry"]["coordinates"]
            existing_sites.append((props["name"], coords[0], coords[1]))
    except Exception as e:
        logger.warning(f"[process] Could not load existing sites for dedup: {e}")

    # Deduplicate
    deduped = deduplicate_records(classified, existing_sites if existing_sites else None)

    # Save processed data
    processed_file = PROCESSED_DIR / "master_processed.json"
    if not dry_run:
        with open(processed_file, "w") as f:
            json.dump({
                "process_date": str(datetime.now()),
                "record_count": len(deduped),
                "records": deduped,
            }, f, indent=2, default=str)
        logger.info(f"[process] Saved {len(deduped)} processed records to {processed_file}")
    else:
        logger.info(f"[DRY RUN] Would save {len(deduped)} processed records")

    return deduped


def process_fossil_scrapes(dry_run: bool = False) -> list[dict]:
    """Load fossil raw scrapes, normalize, classify, and deduplicate."""
    from tools.processors.fossil_normalizer import normalize_fossil_records
    from tools.processors.fossil_classifier import classify_fossil_records
    from tools.processors.fossil_deduplicator import deduplicate_fossils

    fossil_sources = ["gbif_fossils", "neotoma_fossils", "idigbio_fossils", "pbdb_fossils"]
    all_normalized = []

    for source_id in fossil_sources:
        raw_file = RAW_DIR / f"{source_id}.json"
        if not raw_file.exists():
            logger.info(f"[process-fossils] {source_id}: no raw file, skipping")
            continue
        try:
            with open(raw_file) as f:
                data = json.load(f)
            records = data.get("records", [])
            if not records:
                logger.info(f"[process-fossils] {source_id}: no records")
                continue

            normalized = normalize_fossil_records(records, source_id)
            all_normalized.extend(normalized)
            logger.info(f"[process-fossils] {source_id}: {len(normalized)} normalized from {len(records)} raw")
        except Exception as e:
            logger.error(f"[process-fossils] Failed to load {source_id}: {e}")

    if not all_normalized:
        logger.warning("[process-fossils] No fossil records to process")
        return []

    logger.info(f"[process-fossils] Total normalized: {len(all_normalized)}")

    classified = classify_fossil_records(all_normalized)
    deduped = deduplicate_fossils(classified)

    processed_file = PROCESSED_DIR / "fossil_processed.json"
    if not dry_run:
        with open(processed_file, "w") as f:
            json.dump({
                "process_date": str(datetime.now()),
                "record_count": len(deduped),
                "records": deduped,
            }, f, indent=2, default=str)
        logger.info(f"[process-fossils] Saved {len(deduped)} records to {processed_file}")
    else:
        logger.info(f"[DRY RUN] Would save {len(deduped)} fossil records")

    return deduped


def embed_fossil_processed(dry_run: bool = False) -> dict[str, int]:
    """Load processed fossil records and embed into data files."""
    from tools.processors.fossil_embedder import embed_fossil_records

    processed_file = PROCESSED_DIR / "fossil_processed.json"
    if not processed_file.exists():
        logger.error(f"[embed-fossils] No processed fossil data at {processed_file}. Run --process-fossils first.")
        return {}

    with open(processed_file) as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        logger.warning("[embed-fossils] No fossil records to embed")
        return {}

    logger.info(f"[embed-fossils] Embedding {len(records)} fossil records...")
    return embed_fossil_records(records, dry_run)


def embed_processed(dry_run: bool = False) -> dict[str, int]:
    """Load processed records and embed into data files."""
    from tools.processors.embedder import embed_records

    processed_file = PROCESSED_DIR / "master_processed.json"
    if not processed_file.exists():
        logger.error(f"[embed] No processed data at {processed_file}. Run --process first.")
        return {}

    with open(processed_file) as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        logger.warning("[embed] No records to embed")
        return {}

    logger.info(f"[embed] Embedding {len(records)} processed records...")
    return embed_records(records, dry_run)


def show_status():
    """Show the status of all sources."""
    scraper_map = get_scraper_classes()
    print(f"\n{'Source':<25} {'Status':<12} {'Records':>10} {'File'}")
    print("-" * 70)

    total_records = 0
    for sid in sorted(scraper_map.keys()):
        raw_file = RAW_DIR / f"{sid}.json"
        if raw_file.exists():
            try:
                with open(raw_file) as f:
                    data = json.load(f)
                count = data.get("record_count", 0)
                date = data.get("scrape_date", "?")
                total_records += count
                print(f"{sid:<25} {'DONE':<12} {count:>10} {raw_file.name} ({date})")
            except Exception:
                print(f"{sid:<25} {'ERROR':<12} {'?':>10} {raw_file.name}")
        else:
            print(f"{sid:<25} {'PENDING':<12} {'-':>10}")

    print("-" * 70)
    print(f"{'TOTAL':<25} {'':12} {total_records:>10}")

    # Check processed data
    processed_file = PROCESSED_DIR / "master_processed.json"
    if processed_file.exists():
        try:
            with open(processed_file) as f:
                data = json.load(f)
            print(f"\nProcessed master: {data.get('record_count', 0)} records ({data.get('process_date', '?')})")
        except Exception:
            print("\nProcessed master: ERROR reading file")
    else:
        print("\nProcessed master: not yet generated")

    # Check embedded data sizes
    try:
        from atlas.gui.data.known_sites_expanded import get_known_sites_geojson
        from atlas.gui.data.search_index import get_search_index
        from atlas.gui.data.terrain_anomalies import get_terrain_anomalies_geojson
        from atlas.gui.data.cave_shelters import get_cave_shelters_geojson

        print(f"\nEmbedded data:")
        print(f"  known_sites: {len(get_known_sites_geojson()['features'])} features")
        print(f"  search_index: {len(get_search_index())} entries")
        print(f"  terrain_anomalies: {len(get_terrain_anomalies_geojson()['features'])} features")
        print(f"  cave_shelters: {len(get_cave_shelters_geojson()['features'])} features")
    except Exception as e:
        print(f"\nCould not check embedded data: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="FOURLEAFCLOVIS Archaeological Database Harvester"
    )
    parser.add_argument("--all", action="store_true", help="Scrape all 18 sources")
    parser.add_argument("--source", action="append", default=[], help="Scrape specific source(s)")
    parser.add_argument("--process", action="store_true", help="Process raw scrapes (normalize/classify/dedup)")
    parser.add_argument("--embed", action="store_true", help="Embed processed data into atlas files")
    parser.add_argument("--process-fossils", action="store_true", help="Process fossil raw scrapes (normalize/classify/dedup)")
    parser.add_argument("--embed-fossils", action="store_true", help="Embed fossil data into dinosaur/megafauna/plant files")
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen without modifying files")
    parser.add_argument("--status", action="store_true", help="Show scrape status")

    args = parser.parse_args()

    if not any([args.all, args.source, args.process, args.embed,
                args.process_fossils, args.embed_fossils, args.status]):
        parser.print_help()
        return

    start_time = time.time()

    if args.status:
        show_status()
        return

    # Phase 1: Scrape
    if args.all or args.source:
        if args.all:
            scraper_map = get_scraper_classes()
            source_ids = list(scraper_map.keys())
        else:
            source_ids = args.source

        logger.info(f"Scraping {len(source_ids)} sources: {source_ids}")
        results = scrape_sources(source_ids, dry_run=args.dry_run)

        for sid, recs in results.items():
            logger.info(f"  {sid}: {len(recs)} records")

    # Phase 2: Process
    if args.all or args.process:
        logger.info("Processing raw scrapes...")
        processed = process_raw_scrapes(dry_run=args.dry_run)
        logger.info(f"Processed: {len(processed)} unique records")

    # Phase 3: Embed
    if args.all or args.embed:
        logger.info("Embedding into data files...")
        embed_results = embed_processed(dry_run=args.dry_run)
        for layer, count in embed_results.items():
            if count:
                logger.info(f"  {layer}: +{count}")

    # Phase 4: Process fossils
    if args.process_fossils:
        logger.info("Processing fossil raw scrapes...")
        processed = process_fossil_scrapes(dry_run=args.dry_run)
        logger.info(f"Processed fossils: {len(processed)} unique records")

    # Phase 5: Embed fossils
    if args.embed_fossils:
        logger.info("Embedding fossil data into data files...")
        fossil_results = embed_fossil_processed(dry_run=args.dry_run)
        for layer, count in fossil_results.items():
            if count:
                logger.info(f"  {layer}: +{count}")

    elapsed = time.time() - start_time
    logger.info(f"Pipeline complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
