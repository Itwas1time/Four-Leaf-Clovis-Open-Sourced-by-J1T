"""Read-only search for the bundled NMNH Paleobiology specimen catalog."""

from __future__ import annotations

from functools import lru_cache
from email.utils import parsedate_to_datetime
import hashlib
import heapq
import json
import re
import sqlite3
from itertools import islice
from pathlib import Path
from typing import Any, Iterator


DATA_DIR = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data"
RUNTIME_TAG = "paleo"
LOOKUP_PATH = DATA_DIR / f"fossil_references_index_{RUNTIME_TAG}.sqlite"
PAGE_SIZE = 24
MAX_QUERY_LENGTH = 120
MAX_QUERY_TERMS = 8
SOURCE_KEY = "paleo"


def _connect(path: Path) -> sqlite3.Connection:
    """Open one bundled shard read-only without creating journals or files."""
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {str(row["key"]): str(row["value"]) for row in connection.execute("SELECT key,value FROM metadata")}


@lru_cache(maxsize=8)
def _inventory(directory: str) -> tuple[tuple[str, dict[str, str]], ...]:
    """Use the build index to ignore obsolete runtime shards left by older builds."""
    root = Path(directory)
    index = root / LOOKUP_PATH.name
    if not index.is_file():
        return ()
    try:
        with _connect(index) as connection:
            names = [str(row[0]) for row in connection.execute(
                "SELECT filename FROM shard_manifest WHERE record_count > 0 AND database_bytes > 0 ORDER BY shard"
            )]
    except (OSError, sqlite3.Error):
        return ()
    found: list[tuple[str, dict[str, str]]] = []
    for filename in names:
        if not re.fullmatch(rf"fossil_references_{RUNTIME_TAG}_[0-9a-f]{{2}}\.sqlite", filename):
            continue
        path = root / filename
        if not path.is_file():
            continue
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


def _index_metadata() -> dict[str, str]:
    path = DATA_DIR.resolve() / LOOKUP_PATH.name
    if not path.is_file():
        return {}
    try:
        with _connect(path) as connection:
            return _metadata(connection)
    except (OSError, sqlite3.Error):
        return {}


def catalog_stats() -> dict[str, Any]:
    """Return record coverage, source snapshot hashes, and field coverage."""
    index_path = DATA_DIR.resolve() / LOOKUP_PATH.name
    if not index_path.is_file():
        return {
            "distinct_records": 0, "distinct_taxon_names": 0, "taxonomy_groups": 0,
            "source_records": 0, "snapshot_date": "", "source_hash": "", "source_index_hash": "",
            "source_url": "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhpaleo/",
            "license": "CC0 1.0 (Smithsonian record metadata marked CC0)", "shards": [],
            "field_coverage": {}, "excluded": {},
        }
    try:
        with _connect(index_path) as connection:
            meta = _metadata(connection)
            rows = [dict(row) for row in connection.execute("SELECT * FROM shard_manifest ORDER BY shard")]
            taxon_rows = [dict(row) for row in connection.execute("SELECT * FROM taxa_shards ORDER BY bucket")]
    except (OSError, sqlite3.Error):
        return {
            "distinct_records": 0, "distinct_taxon_names": 0, "taxonomy_groups": 0,
            "source_records": 0, "snapshot_date": "", "source_hash": "", "source_index_hash": "",
            "source_url": "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhpaleo/",
            "license": "CC0 1.0 (Smithsonian record metadata marked CC0)", "shards": [],
            "field_coverage": {}, "excluded": {},
        }

    record_count = sum(int(row["record_count"]) for row in rows)
    source_records = sum(int(row["source_records"]) for row in rows)
    source_hash = hashlib.sha256("".join(
        f"{row['shard']}:{row['source_sha256']}\n" for row in rows
    ).encode("utf-8")).hexdigest()
    source_modified = max((str(row["source_last_modified"]) for row in rows), default="")
    try:
        snapshot_date = parsedate_to_datetime(source_modified).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        snapshot_date = ""
    coverage_columns = {
        "taxonomy_hierarchy": "taxonomy_count",
        "geological_age": "geological_age_count",
        "stratigraphy": "stratigraphy_count",
        "without_geologic_context": "without_geologic_context_count",
        "specimen_number": "specimen_number_count",
        "measurements": "measurement_count",
        "physical_description": "physical_description_count",
        "materials": "materials_count",
        "type_status": "type_status_count",
        "cc0_images": "image_url_count",
    }
    exclusion_columns = {
        "restricted": "excluded_restricted",
        "non_cc0": "excluded_non_cc0",
        "wrong_unit": "excluded_wrong_unit",
        "missing_id": "excluded_missing_id",
        "missing_taxon": "excluded_missing_taxon",
        "missing_taxonomy_hierarchy": "excluded_missing_taxonomy_hierarchy",
        "duplicate": "excluded_duplicate",
    }
    return {
        "distinct_records": record_count,
        "counts": [{"collection": "NMNH Paleobiology", "count": record_count}],
        "distinct_taxon_names": int(meta.get("taxon_name_count", "0") or 0),
        "taxonomy_groups": int(meta.get("taxon_group_count", "0") or 0),
        "source_records": source_records,
        "snapshot_date": snapshot_date,
        "built_at_utc": meta.get("built_at_utc", ""),
        "source_hash": source_hash,
        "source_index_hash": meta.get("index_sha256", ""),
        "source_index_etag": meta.get("source_index_etag", ""),
        "source_index_last_modified": meta.get("source_index_last_modified", ""),
        "source_index_bytes": int(meta.get("source_index_bytes", "0") or 0),
        "source_url": meta.get("source_index_url", ""),
        "license": meta.get("metadata_license", ""),
        "field_coverage": {
            label: sum(int(row[column]) for row in rows) for label, column in coverage_columns.items()
        },
        "excluded": {
            label: sum(int(row[column]) for row in rows) for label, column in exclusion_columns.items()
        },
        "shard_count": int(meta.get("shard_count", "0") or 0),
        "runtime_shards": sum(int(row["record_count"]) > 0 for row in rows),
        "taxon_shards": taxon_rows,
        "runtime_file_count": sum(int(row["record_count"]) > 0 for row in rows) + len(taxon_rows) + 1,
        "runtime_max_file_bytes": max(
            [int(row["database_bytes"]) for row in rows]
            + [int(row["database_bytes"]) for row in taxon_rows]
            + [index_path.stat().st_size]
        ),
        "shards": [
            {
                "shard": row["shard"], "source_url": row["source_url"], "source_sha256": row["source_sha256"],
                "runtime_filename": row["filename"],
                "source_etag": row["source_etag"], "source_last_modified": row["source_last_modified"],
                "source_bytes": int(row["source_bytes"]), "source_records": int(row["source_records"]),
                "distinct_records": int(row["record_count"]), "database_bytes": int(row["database_bytes"]),
            }
            for row in rows
        ],
    }


def _safe_query_expression(query: str) -> str | None:
    terms = [
        term.casefold()
        for term in re.findall(r"\w+", (query or "")[:MAX_QUERY_LENGTH], flags=re.UNICODE)[:MAX_QUERY_TERMS]
    ]
    if not terms:
        return None
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms)


def _where_clause(query_expression: str | None, group: str) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query_expression:
        clauses.append("r.rowid IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        params.append(query_expression)
    if group and group.casefold() != "all":
        clauses.append("r.taxon_group = ? COLLATE NOCASE")
        params.append(group.strip()[:100])
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


@lru_cache(maxsize=512)
def _matching_counts(directory: str, query_expression: str, group: str) -> tuple[tuple[str, int], ...]:
    where, params = _where_clause(query_expression or None, group)
    counts: list[tuple[str, int]] = []
    for filename, _ in _inventory(directory):
        try:
            with _connect(Path(directory) / filename) as connection:
                count = int(connection.execute("SELECT COUNT(*) FROM records r" + where, params).fetchone()[0])  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            counts.append((filename, count))
        except (OSError, sqlite3.Error):
            continue
    return tuple(counts)


def _decode_json(value: Any, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result.pop("title_sort", None)
    result.pop("taxon_name_sort", None)
    result.pop("source_shard", None)
    for field, default in (
        ("taxonomic_hierarchy", {}), ("geological_age", {}), ("stratigraphy", {}),
        ("measurements", []), ("physical_description", []), ("materials", []), ("categories", []),
    ):
        result[field] = _decode_json(result.get(field), default)
    result["id"] = f"{SOURCE_KEY}:{result.pop('source_id')}"
    result["license"] = result.pop("metadata_license")
    result["image_verified"] = bool(result.get("image_url"))
    return result


def _stream_rows(path: Path, where: str, params: list[Any]) -> Iterator[sqlite3.Row]:
    connection = _connect(path)
    cursor: sqlite3.Cursor | None = None
    try:
        cursor = connection.execute(
            "SELECT r.* FROM records r" + where + " ORDER BY r.title_sort,r.id", params  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        )
        yield from cursor
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def search_fossils(query: str = "", group: str = "all", page: int = 1) -> dict[str, Any]:
    """Search records with stable global title ordering and bounded pagination.

    ``group`` filters the record-reported taxonomic kingdom (for example
    ``Animalia`` or ``Plantae``). The default ``all`` searches all included
    records.
    """
    paths = _shard_paths()
    if not paths:
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    expression = _safe_query_expression(query)
    safe_group = (group or "all").strip()[:100]
    where, params = _where_clause(expression, safe_group)
    directory = str(DATA_DIR.resolve())
    inventory = dict(_inventory(directory))
    if not expression and safe_group.casefold() == "all":
        total = sum(int(meta.get("record_count", "0") or 0) for meta in inventory.values())
    else:
        matches = _matching_counts(directory, expression or "", safe_group.casefold())
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
        merged = heapq.merge(*streams, key=lambda row: (row["title_sort"], row["id"]))
        selected = list(islice(merged, offset, offset + PAGE_SIZE))
    except sqlite3.Error:
        selected = []
    finally:
        for stream in streams:
            stream.close()
    return {"rows": [_public_row(row) for row in selected], "total": total, "page": current_page, "pages": pages}


def get_fossil(record_id: str | int | None) -> dict[str, Any] | None:
    """Return one record by its stable ``paleo:<EDAN record_ID>`` identifier."""
    index_path = DATA_DIR.resolve() / LOOKUP_PATH.name
    if record_id is None or not index_path.is_file():
        return None
    value = str(record_id).strip()
    if value.casefold().startswith(f"{SOURCE_KEY}:"):
        value = value[len(SOURCE_KEY) + 1:]
    if not value or len(value) > 160:
        return None
    try:
        with _connect(index_path) as connection:
            route = connection.execute(
                "SELECT m.shard,m.filename FROM routes r JOIN shard_manifest m ON m.shard=r.shard "
                "WHERE r.source_id=?", (value,)
            ).fetchone()
    except (OSError, sqlite3.Error):
        return None
    if route is None or not re.fullmatch(r"[0-9a-f]{2}", str(route["shard"])):
        return None
    filename = str(route["filename"])
    if not re.fullmatch(rf"fossil_references_{RUNTIME_TAG}_[0-9a-f]{{2}}\.sqlite", filename):
        return None
    path = DATA_DIR.resolve() / filename
    try:
        with _connect(path) as connection:
            row = connection.execute("SELECT * FROM records WHERE source_id=?", (value,)).fetchone()
            meta = _metadata(connection)
    except (OSError, sqlite3.Error):
        return None
    if row is None:
        return None
    result = _public_row(row)
    result["source_sha256"] = meta.get("source_sha256", "")
    result["source_etag"] = meta.get("source_etag", "")
    result["source_last_modified"] = meta.get("source_last_modified", "")
    result["source_shard"] = meta.get("source_shard", "")
    return result


def _taxon_paths(index_path: Path) -> list[Path]:
    try:
        with _connect(index_path) as connection:
            names = [str(row[0]) for row in connection.execute("SELECT filename FROM taxa_shards ORDER BY bucket")]
    except (OSError, sqlite3.Error):
        return []
    paths: list[Path] = []
    for name in names:
        if not re.fullmatch(rf"fossil_references_taxa_{RUNTIME_TAG}_[0-9]{{2}}\.sqlite", name):
            continue
        path = DATA_DIR.resolve() / name
        if path.is_file():
            paths.append(path)
    return paths


def _stream_taxa(path: Path, where: str, params: list[Any]) -> Iterator[sqlite3.Row]:
    connection = _connect(path)
    cursor: sqlite3.Cursor | None = None
    try:
        cursor = connection.execute(
            "SELECT t.* FROM taxa t" + where + " ORDER BY t.taxon_name_sort,t.taxon_key", params  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        )
        yield from cursor
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def search_taxa(query: str = "", group: str = "all", page: int = 1) -> dict[str, Any]:
    """Return distinct source-name/hierarchy groups with specimen counts.

    Sample record IDs route directly to ``get_fossil`` for actual specimen
    details. A name with different source hierarchies remains separate.
    """
    index_path = DATA_DIR.resolve() / LOOKUP_PATH.name
    if not index_path.is_file():
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    paths = _taxon_paths(index_path)
    if not paths:
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    expression = _safe_query_expression(query)
    clauses: list[str] = []
    params: list[Any] = []
    if expression:
        clauses.append("t.rowid IN (SELECT rowid FROM taxa_fts WHERE taxa_fts MATCH ?)")
        params.append(expression)
    if group and group.casefold() != "all":
        clauses.append("t.taxon_group = ? COLLATE NOCASE")
        params.append(group.strip()[:100])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    try:
        total = 0
        for path in paths:
            with _connect(path) as connection:
                total += int(connection.execute("SELECT COUNT(*) FROM taxa t" + where, params).fetchone()[0])  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        requested_page = max(1, int(page or 1))
    except (TypeError, ValueError, OverflowError, OSError, sqlite3.Error):
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    current_page = min(requested_page, pages)
    streams = [_stream_taxa(path, where, params) for path in paths]
    try:
        merged = heapq.merge(*streams, key=lambda row: (row["taxon_name_sort"], row["taxon_key"]))
        rows = list(islice(merged, (current_page - 1) * PAGE_SIZE, current_page * PAGE_SIZE))
    except sqlite3.Error:
        rows = []
    finally:
        for stream in streams:
            stream.close()
    return {
        "rows": [
            {
                "id": row["taxon_key"], "taxon_name": row["taxon_name"],
                "taxonomic_hierarchy": _decode_json(row["hierarchy"], {}),
                "taxon_group": row["taxon_group"], "specimen_count": int(row["specimen_count"]),
                "sample_record_ids": _decode_json(row["sample_record_ids"], []),
            }
            for row in rows
        ],
        "total": total,
        "page": current_page,
        "pages": pages,
    }
