"""Read-only search for the bundled Smithsonian NMNH Anthropology catalog."""

from __future__ import annotations

from functools import lru_cache
import heapq
import hashlib
import json
import re
import sqlite3
from itertools import islice
from pathlib import Path
from typing import Any, Iterator


DATA_DIR = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data"
LOOKUP_PATH = DATA_DIR / "smithsonian_reference_index.sqlite"
SHARD_GLOB = "smithsonian_objects_*.sqlite"
PAGE_SIZE = 24
MAX_QUERY_LENGTH = 120
MAX_QUERY_TERMS = 8
SOURCE_KEY = "si"


@lru_cache(maxsize=8)
def _inventory(directory: str) -> tuple[tuple[str, dict[str, str]], ...]:
    """Cache shard paths and metadata; bundled data does not change at runtime."""
    found: list[tuple[str, dict[str, str]]] = []
    for path in sorted(Path(directory).glob(SHARD_GLOB), key=lambda item: item.name.casefold()):
        try:
            with _connect(path) as connection:
                found.append((path.name, _metadata(connection)))
        except (OSError, sqlite3.Error):
            continue
    return tuple(found)


def _shard_paths() -> list[Path]:
    directory = DATA_DIR.resolve()
    return [directory / name for name, _ in _inventory(str(directory))]


def available() -> bool:
    return bool(_shard_paths())


def _connect(path: Path) -> sqlite3.Connection:
    """Open one bundled shard read-only without creating journals or files."""
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"])
        for row in connection.execute("SELECT key, value FROM metadata")
    }


def catalog_stats() -> dict[str, Any]:
    """Return source coverage, license, snapshot, and per-file hash details."""
    shard_summaries: list[dict[str, Any]] = []
    for filename, meta in _inventory(str(DATA_DIR.resolve())):
        shard_summaries.append({
            "shard": meta.get("source_shard", Path(filename).stem.rsplit("_", 1)[-1]),
            "source_url": meta.get("source_url", ""),
            "source_sha256": meta.get("source_sha256", ""),
            "source_etag": meta.get("source_etag", ""),
            "source_bytes": int(meta.get("source_bytes", "0") or 0),
            "snapshot_date": meta.get("snapshot_date", ""),
            "built_at_utc": meta.get("built_at_utc", ""),
            "source_records": int(meta.get("source_records", "0") or 0),
            "distinct_records": int(meta.get("record_count", "0") or 0),
            "excluded_restricted": int(meta.get("excluded_restricted", "0") or 0),
            "excluded_non_cc0": int(meta.get("excluded_non_cc0", "0") or 0),
            "excluded_missing_id": int(meta.get("excluded_missing_id", "0") or 0),
            "excluded_missing_description": int(meta.get("excluded_missing_description", "0") or 0),
            "excluded_duplicate": int(meta.get("excluded_duplicate", "0") or 0),
            "image_url_count": int(meta.get("image_url_count", "0") or 0),
        })

    if not shard_summaries:
        return {
            "counts": [], "distinct_records": 0, "snapshot_date": "",
            "source_hash": "", "source_url": "",
            "license": "CC0 1.0 (Smithsonian metadata)", "shards": [],
        }

    distinct_records = sum(row["distinct_records"] for row in shard_summaries)
    source_records = sum(row["source_records"] for row in shard_summaries)
    restricted = sum(row["excluded_restricted"] for row in shard_summaries)
    non_cc0 = sum(row["excluded_non_cc0"] for row in shard_summaries)
    image_count = sum(row["image_url_count"] for row in shard_summaries)
    source_hash = hashlib.sha256("".join(
        f"{row['shard']}:{row['source_sha256']}\n" for row in shard_summaries
    ).encode("utf-8")).hexdigest()
    snapshot_date = max((row["snapshot_date"] for row in shard_summaries), default="")
    return {
        "counts": [{"collection": "NMNH Anthropology", "count": distinct_records}],
        "distinct_records": distinct_records,
        "source_records": source_records,
        "snapshot_date": snapshot_date,
        "built_at_utc": max((row["built_at_utc"] for row in shard_summaries), default=""),
        "source_hash": source_hash,
        "source_url": "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhanthro/",
        "license": "CC0 1.0 (Smithsonian metadata marked CC0 in EDAN)",
        "image_url_count": image_count,
        "excluded_restricted": restricted,
        "excluded_non_cc0": non_cc0,
        "shard_count": len(shard_summaries),
        "shards": shard_summaries,
    }


def _safe_query_expression(query: str) -> str | None:
    terms = [
        term.casefold()
        for term in re.findall(r"\w+", (query or "")[:MAX_QUERY_LENGTH], flags=re.UNICODE)[:MAX_QUERY_TERMS]
    ]
    if not terms:
        return None
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _where_clause(query_expression: str | None, material: str) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query_expression:
        clauses.append("r.rowid IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        params.append(query_expression)
    if material and material.casefold() != "all":
        clauses.append("r.material LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(material.strip())}%")
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


@lru_cache(maxsize=256)
def _matching_counts(directory: str, query_expression: str, material: str) -> tuple[tuple[str, int], ...]:
    """Cache per-shard filtered counts for repeated searches in the UI."""
    where, params = _where_clause(query_expression or None, material)
    counts: list[tuple[str, int]] = []
    for filename, _ in _inventory(directory):
        try:
            with _connect(Path(directory) / filename) as connection:
                count = int(connection.execute(
                    "SELECT COUNT(*) FROM records r" + where, params  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
                ).fetchone()[0])
            counts.append((filename, count))
        except (OSError, sqlite3.Error):
            continue
    return tuple(counts)


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result.pop("title_sort", None)
    result.pop("source_shard", None)
    for field in ("material_tags", "dimensions"):
        try:
            result[field] = json.loads(result[field] or "[]")
        except (TypeError, json.JSONDecodeError):
            result[field] = []
    result["id"] = f"{SOURCE_KEY}:{result.pop('source_id')}"
    result["license"] = result.pop("metadata_license")
    result["material_basis"] = "Title/object-type keyword tags" if result["material_tags"] else ""
    result["image_verified"] = bool(result.get("image_url"))
    return result


def _stream_rows(
    path: Path,
    where: str,
    params: list[Any],
) -> Iterator[sqlite3.Row]:
    connection = _connect(path)
    cursor: sqlite3.Cursor | None = None
    try:
        cursor = connection.execute(
            "SELECT r.* FROM records r" + where + " ORDER BY r.title_sort, r.id",  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            params,
        )
        yield from cursor
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def search_objects(
    query: str = "",
    material: str = "all",
    page: int = 1,
) -> dict[str, Any]:
    """Search across all installed shards with a global, stable title order."""
    paths = _shard_paths()
    if not paths:
        return {"rows": [], "total": 0, "page": 1, "pages": 1}

    expression = _safe_query_expression(query)
    safe_material = (material or "all").strip()[:80]
    where, params = _where_clause(expression, safe_material)
    total = 0
    directory = str(DATA_DIR.resolve())
    inventory = dict(_inventory(directory))
    if not expression and safe_material.casefold() == "all":
        total = sum(int(meta.get("record_count", "0") or 0) for meta in inventory.values())
    else:
        matches = _matching_counts(
            directory, expression or "", safe_material.casefold()
        )
        total = sum(count for _, count in matches)
        paths = [Path(directory) / filename for filename, count in matches if count > 0]

    try:
        requested_page = max(1, int(page or 1))
    except (TypeError, ValueError, OverflowError):
        requested_page = 1
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    current_page = min(requested_page, pages)
    offset = (current_page - 1) * PAGE_SIZE

    streams = [_stream_rows(path, where, params) for path in paths]
    try:
        merged = heapq.merge(
            *streams,
            key=lambda row: (row["title_sort"], row["id"]),
        )
        selected = list(islice(merged, offset, offset + PAGE_SIZE))
    except sqlite3.Error:
        selected = []
    finally:
        for stream in streams:
            stream.close()

    return {
        "rows": [_public_row(row) for row in selected],
        "total": total,
        "page": current_page,
        "pages": pages,
    }


def get_object(record_id: str | int | None) -> dict[str, Any] | None:
    """Return one record by stable ``si:<Smithsonian record_ID>`` identifier."""
    if record_id is None:
        return None
    value = str(record_id).strip()
    if value.casefold().startswith("si:"):
        value = value[3:]
    if not value or len(value) > 120:
        return None
    lookup_path = DATA_DIR.resolve() / LOOKUP_PATH.name
    shard: str | None = None
    if lookup_path.is_file():
        try:
            with sqlite3.connect(lookup_path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
                found = connection.execute("SELECT shard FROM routes WHERE source_id = ?", (value,)).fetchone()
            if found is not None and re.fullmatch(r"[0-9a-f]{2}", str(found[0])):
                shard = str(found[0])
        except (OSError, sqlite3.Error):
            shard = None
    if shard is not None:
        paths = [DATA_DIR.resolve() / f"smithsonian_objects_{shard}.sqlite"]
    else:
        # The route index is built beside the catalog. This fallback keeps the
        # reader useful for small temporary catalogs and interrupted builds.
        paths = _shard_paths()
    for path in paths:
        try:
            with _connect(path) as connection:
                row = connection.execute("SELECT * FROM records WHERE source_id = ?", (value,)).fetchone()
        except (OSError, sqlite3.Error):
            continue
        if row is not None:
            return _public_row(row)
    return None
