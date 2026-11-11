"""Package the two large Smithsonian reference shelves as optional collections (11 Nov 2026).

The fossil-specimen shelf (NMNH Paleobiology, ~1.1 GB) and the museum-object shelf (NMNH
Anthropology, ~0.5 GB) used to ship inside every install. They are now optional collections
installed from Atlas > Manage offline collections, so the core download stays small.

For each shelf this writes, under release/data-packs/<id>/<version>/:
  clovis-<id>-<version>.zip   files at the archive root, exactly as core.data_packs installs them
  definition.json             the catalog entry (sizes, hashes, schemas, record counts)
Usage: python tools/build_smithsonian_shelf_packs.py [--version 2026.11.11] [--catalog]
  --catalog also writes the definitions into atlas/gui/data/data_pack_catalog.json.
"""
import argparse
import hashlib
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "atlas" / "gui" / "data"
OUT = ROOT / "release" / "data-packs"
CATALOG = DATA / "data_pack_catalog.json"
REPOSITORY = "https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T"
FTS_SHADOW = ("_data", "_idx", "_content", "_docsize", "_config")

SHELVES = {
    "smithsonian-fossil-specimens": {
        "patterns": ["fossil_references_index_paleo.sqlite", "fossil_references_paleo_*.sqlite",
                     "fossil_references_taxa_paleo_*.sqlite"],
        "title": "Smithsonian fossil specimens",
        "description": "Museum catalog records for fossil specimens in the Smithsonian National Museum of Natural "
                       "History Department of Paleobiology: taxonomy, ages, formations, specimen descriptions and "
                       "type citations where recorded, with links to individually CC0 images.",
        "record_type": "museum specimen records",
        "coverage": "Where specimens are curated, not where fossils occur locally. Worldwide collection with uneven "
                    "coverage; missing fields stay unknown.",
        "source_url": "https://www.si.edu/openaccess",
        "citation_url": "https://naturalhistory.si.edu/research/paleobiology",
        "index": "fossil_references_index_paleo.sqlite",
    },
    "smithsonian-museum-objects": {
        "patterns": ["smithsonian_reference_index.sqlite", "smithsonian_objects_*.sqlite"],
        "title": "Smithsonian museum objects",
        "description": "Smithsonian National Museum of Natural History Anthropology catalog records: recorded "
                       "materials, cultures, dates, measurements and catalog numbers beside their source, for "
                       "comparison with objects people find.",
        "record_type": "museum object records",
        "coverage": "Museum holdings, not finds in any town. Worldwide with uneven coverage; missing fields stay "
                    "unknown.",
        "source_url": "https://www.si.edu/openaccess",
        "citation_url": "https://naturalhistory.si.edu/research/anthropology",
        "index": "smithsonian_reference_index.sqlite",
    },
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def describe(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        fts = {name for name in tables if db.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0]
               .upper().startswith("CREATE VIRTUAL TABLE")}
        keep = [name for name in tables if not name.startswith("sqlite_")
                and not any(name == base + suffix for base in fts for suffix in FTS_SHADOW)]
        schema = {name: [column[1] for column in db.execute(f'PRAGMA table_info("{name}")')] for name in keep}  # nosec B608
        record_table = next((name for name in ("records", "routes", "shard_manifest") if name in schema), keep[0])
        records = db.execute(f'SELECT count(*) FROM "{record_table}"').fetchone()[0]  # nosec B608
        user_version = db.execute("PRAGMA user_version").fetchone()[0]
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path), "schema": schema,
            "record_table": record_table, "records": records, "user_version": user_version}


def build(pack_id, version):
    shelf = SHELVES[pack_id]
    files = sorted({path for pattern in shelf["patterns"] for path in DATA.glob(pattern)}, key=lambda p: p.name)
    if not any(path.name == shelf["index"] for path in files):
        raise SystemExit(f"{pack_id}: index {shelf['index']} not found in {DATA}")
    rows = [describe(path) for path in files]
    out = OUT / pack_id / version
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"clovis-{pack_id}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in files:
            zipped.write(path, arcname=path.name)
    with closing(sqlite3.connect((DATA / shelf["index"]).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        meta = dict(db.execute("SELECT key, value FROM metadata"))
    definition = {
        "id": pack_id, "version": version, "title": shelf["title"], "description": shelf["description"],
        "records": int(meta["record_count"]), "record_type": shelf["record_type"], "coverage": shelf["coverage"],
        "source_release": meta.get("built_at_utc", "")[:10] or version,
        "license": meta.get("metadata_license", "CC0 1.0"),
        "source_url": shelf["source_url"], "citation_url": shelf["citation_url"],
        "download_url": f"{REPOSITORY}/releases/download/data-{pack_id}-{version}/{archive.name}",
        "archive_bytes": archive.stat().st_size, "archive_sha256": sha256(archive),
        "installed_bytes": sum(row["bytes"] for row in rows), "files": rows, "countries": [],
    }
    (out / "definition.json").write_text(json.dumps(definition, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{pack_id}: {len(rows)} files, {definition['installed_bytes'] / 1e9:.2f} GB installed, "
          f"{definition['archive_bytes'] / 1e9:.2f} GB archive -> {archive}")
    return definition


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="2026.11.11")
    parser.add_argument("--catalog", action="store_true")
    args = parser.parse_args()
    definitions = [build(pack_id, args.version) for pack_id in SHELVES]
    if args.catalog:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        catalog["packs"] = [row for row in catalog["packs"] if row["id"] not in SHELVES] + definitions
        CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sys.path.insert(0, str(ROOT))
        from core.data_packs import catalog_definitions
        catalog_definitions(CATALOG)  # raises if the new entries break the strict catalog format
        print("catalog updated and validated:", CATALOG)


if __name__ == "__main__":
    main()
