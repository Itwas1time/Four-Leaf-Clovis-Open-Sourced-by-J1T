"""Read-only search over licensed, coordinate-free ceramic analysis samples."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data" / "artifact_analysis.sqlite"
PAGE_SIZE = 24
MAX_QUERY_LENGTH = 120
MAX_QUERY_TERMS = 8
SCHEMA_VERSION = "1"


def _connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the bundled catalog read-only, without creating SQLite sidecars."""
    path = path or DATA_PATH
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _meta(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"])
        for row in connection.execute("SELECT key, value FROM metadata")
    }


def _json(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _empty_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "source_rows": 0,
        "source_hash": "",
        "sources": [],
        "field_coverage": {},
        "excluded": {},
        "runtime_file_bytes": 0,
    }


def catalog_stats() -> dict[str, Any]:
    """Return record totals, exact source hashes, exclusions, and field coverage."""
    if not DATA_PATH.is_file():
        return _empty_stats()
    try:
        with _connect() as connection:
            meta = _meta(connection)
    except (OSError, sqlite3.Error):
        return _empty_stats()

    result = _empty_stats()
    result.update({
        "total": int(meta.get("record_count", "0") or 0),
        "source_rows": int(meta.get("source_row_count", "0") or 0),
        "source_hash": meta.get("source_hash", ""),
        "sources": _json(meta.get("sources"), []),
        "field_coverage": _json(meta.get("field_coverage"), {}),
        "excluded": _json(meta.get("excluded"), {}),
        "built_at_utc": meta.get("built_at_utc", ""),
        "schema_version": meta.get("schema_version", ""),
        "runtime_file_bytes": DATA_PATH.stat().st_size,
        "license_note": (
            "Source records carry their original public-domain or CC BY 4.0 notice; "
            "see docs/ARTIFACT_ANALYSIS_SOURCES.md for attribution."
        ),
    })
    return result


def _query_expression(query: str) -> str | None:
    terms = [
        term.casefold()
        for term in re.findall(r"\w+", (query or "")[:MAX_QUERY_LENGTH], flags=re.UNICODE)[:MAX_QUERY_TERMS]
    ]
    if not terms:
        return None
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms)


def _where(query_expression: str | None, category: str) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if query_expression:
        clauses.append("r.id IN (SELECT id FROM records_fts WHERE records_fts MATCH ?)")
        params.append(query_expression)
    requested_category = (category or "all").strip().casefold()
    if requested_category not in {"", "all", "ceramic", "ceramics", "pottery"}:
        clauses.append("r.category = ? COLLATE NOCASE")
        params.append(requested_category[:40])
    elif requested_category in {"ceramic", "ceramics", "pottery"}:
        clauses.append("r.category = 'ceramic'")
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["attributes"] = _json(result.pop("attributes_json", ""), [])
    result["measurements"] = _json(result.pop("measurements_json", ""), [])
    result["identifiers"] = _json(result.pop("identifiers_json", ""), [])
    result.pop("search_text", None)
    return result


def search_artifacts(query: str = "", category: str = "all", page: int = 1) -> dict[str, Any]:
    """Search the coordinate-free ceramic sample records with bounded pagination."""
    if not DATA_PATH.is_file():
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    expression = _query_expression(query)
    where, params = _where(expression, category)
    try:
        with _connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM records r" + where, params).fetchone()[0])  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            try:
                requested_page = max(1, int(page or 1))
            except (TypeError, ValueError, OverflowError):
                requested_page = 1
            current_page = min(requested_page, pages)
            rows = connection.execute(
                "SELECT r.* FROM records r" + where + " ORDER BY r.source_key, r.source_label COLLATE NOCASE, r.id "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
                "LIMIT ? OFFSET ?",
                [*params, PAGE_SIZE, (current_page - 1) * PAGE_SIZE],
            ).fetchall()
    except (OSError, sqlite3.Error):
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    return {
        "rows": [_public_row(row) for row in rows],
        "total": total,
        "page": current_page,
        "pages": pages,
    }


def get_artifact(artifact_id: str | int | None) -> dict[str, Any] | None:
    """Return one record by stable ``oc:<Open Context subject UUID>`` identifier."""
    if artifact_id is None or not DATA_PATH.is_file():
        return None
    value = str(artifact_id).strip()
    if value.casefold().startswith("oc:"):
        value = value[3:]
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        return None
    try:
        with _connect() as connection:
            row = connection.execute("SELECT * FROM records WHERE source_record_id = ?", (value.casefold(),)).fetchone()
    except (OSError, sqlite3.Error):
        return None
    return _public_row(row) if row is not None else None


@lru_cache(maxsize=1)
def _database_sha256() -> str:
    """Return a digest useful for private build reports without loading the DB in memory."""
    if not DATA_PATH.is_file():
        return ""
    digest = hashlib.sha256()
    with DATA_PATH.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
