"""Read-only search for sourced museum object reference records."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data" / "object_references.sqlite"
PAGE_SIZE = 24
SOURCE_KEY = "met"


def _connect() -> sqlite3.Connection:
    """Open the bundled catalog without creating a database or journal."""
    uri = DB_PATH.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def available() -> bool:
    return DB_PATH.is_file()


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT key, value FROM metadata"))


def catalog_stats() -> dict[str, Any]:
    """Return compact coverage, source, license, and snapshot information."""
    if not available():
        return {
            "counts": [], "distinct_records": 0, "snapshot_date": "",
            "source_hash": "", "source_url": "", "license": "CC0 1.0",
        }
    with _connect() as connection:
        metadata = _metadata(connection)
        counts = [dict(row) for row in connection.execute(
            "SELECT category_key AS category, COUNT(*) AS count "
            "FROM records GROUP BY category_key ORDER BY category_key"
        )]
        distinct_records = connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    return {
        "counts": counts,
        "distinct_records": distinct_records,
        "snapshot_date": metadata.get("snapshot_date", ""),
        "built_at_utc": metadata.get("built_at_utc", ""),
        "source_hash": metadata.get("source_sha256", ""),
        "source_url": metadata.get("source_csv_url", ""),
        "license": metadata.get("metadata_license", "CC0 1.0"),
        "image_url_count": int(metadata.get("image_url_count", "0")),
        "categories": json.loads(metadata.get("category_labels", "{}")),
    }


def _safe_query_expression(query: str) -> str | None:
    terms = re.findall(r"\w+", (query or "").strip(), flags=re.UNICODE)[:8]
    if not terms:
        return None
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["id"] = f"{result.pop('source_key')}:{result['source_id']}"
    result["title"] = result.pop("title_source") or result.get("object_type", "")
    result["date"] = result.pop("object_date", "")
    result["material"] = result.pop("medium", "")
    result["institution"] = result.pop("institution_source", "")
    result["license"] = result.pop("metadata_license", "CC0 1.0")
    result["rights"] = result.pop("rights_statement", "")
    result["is_public_domain"] = bool(result.get("is_public_domain", 0))
    result["image_verified"] = bool(result.get("image_verified", 0))
    return result


def search_objects(
    query: str = "",
    material: str = "all",
    page: int = 1,
    *,
    object_type: str = "all",
    category: str = "all",
    date_from: int | None = None,
    date_to: int | None = None,
) -> dict[str, Any]:
    """Search the local catalog with optional source-field filters and paging.

    ``date_from`` and ``date_to`` match the source's numeric object-date bounds.
    They are catalog record dates, not a new estimate of when an object was
    found or used.
    """
    if not available():
        return {"rows": [], "total": 0, "page": 1, "pages": 1}

    conditions: list[str] = []
    params: list[Any] = []
    expression = _safe_query_expression(query)
    if expression:
        conditions.append("r.id IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        params.append(expression)
    if material and material.casefold() != "all":
        conditions.append("r.medium LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(material.strip())}%")
    if object_type and object_type.casefold() != "all":
        conditions.append("r.object_type = ?")
        params.append(object_type)
    if category and category.casefold() != "all":
        conditions.append("r.category_key = ?")
        params.append(category)
    if date_from is not None:
        conditions.append("r.object_end_date >= ?")
        params.append(int(date_from))
    if date_to is not None:
        conditions.append("r.object_begin_date <= ?")
        params.append(int(date_to))
    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    try:
        requested_page = max(1, int(page or 1))
    except (TypeError, ValueError):
        requested_page = 1
    with _connect() as connection:
        total = int(connection.execute(
            f"SELECT COUNT(*) FROM records r{where}", params  # nosec B608: clauses are static
        ).fetchone()[0])
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        current_page = min(requested_page, pages)
        rows = [
            _public_row(row) for row in connection.execute(
                f"SELECT r.* FROM records r{where} "  # nosec B608: clauses are static
                "ORDER BY CASE WHEN r.object_end_date IS NULL THEN 1 ELSE 0 END, "
                "r.object_end_date DESC, r.title_source COLLATE NOCASE, r.source_id "
                "LIMIT ? OFFSET ?",
                [*params, PAGE_SIZE, (current_page - 1) * PAGE_SIZE],
            )
        ]
    return {"rows": rows, "total": total, "page": current_page, "pages": pages}


def get_object(record_id: str | int | None) -> dict[str, Any] | None:
    """Return one object record by the stable ``met:<Object ID>`` identifier."""
    if not available() or record_id is None:
        return None
    value = str(record_id).strip()
    if value.startswith("met:"):
        value = value[4:]
    if not value or len(value) > 80:
        return None
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM records WHERE source_key = ? AND source_id = ?",
            (SOURCE_KEY, value),
        ).fetchone()
    return _public_row(row) if row else None
