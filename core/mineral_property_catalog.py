"""Read-only search for sourced mineral chemistry and physical properties."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data" / "mineral_properties.sqlite"
PAGE_SIZE = 24
MAX_QUERY_LENGTH = 160
MAX_QUERY_TERMS = 10
SOURCE_URL = "https://www.wikidata.org/"
LICENSE = "CC0 1.0 (Wikidata structured data)"


def _connect() -> sqlite3.Connection:
    """Open the bundled catalog read-only and without creating sidecar files."""
    uri = DB_PATH.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def available() -> bool:
    return DB_PATH.is_file()


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {str(row["key"]): str(row["value"]) for row in connection.execute("SELECT key,value FROM metadata")}


def catalog_stats() -> dict[str, Any]:
    """Return snapshot provenance, item/fact coverage, and useful omissions."""
    if not available():
        return {
            "distinct_records": 0, "fact_count": 0, "snapshot_date": "",
            "source_hash": "", "source_url": SOURCE_URL, "license": LICENSE,
            "property_coverage": [], "class_coverage": [],
        }
    with _connect() as connection:
        metadata = _metadata(connection)
        property_coverage = [dict(row) for row in connection.execute(
            "SELECT name, COUNT(*) AS fact_count, COUNT(DISTINCT record_id) AS record_count "
            "FROM facts GROUP BY property_id,name ORDER BY fact_count DESC,name COLLATE NOCASE"
        )]
        class_coverage = json.loads(metadata.get("class_coverage_json", "[]"))
    return {
        "distinct_records": int(metadata.get("record_count", "0") or 0),
        "source_items": int(metadata.get("source_item_count", "0") or 0),
        "fact_count": int(metadata.get("fact_count", "0") or 0),
        "snapshot_date": metadata.get("snapshot_date", ""),
        "retrieved_at_utc": metadata.get("retrieved_at_utc", ""),
        "built_at_utc": metadata.get("built_at_utc", ""),
        "source_hash": metadata.get("source_sha256", ""),
        "query_hash": metadata.get("query_sha256", ""),
        "source_url": metadata.get("source_url", SOURCE_URL),
        "license": metadata.get("metadata_license", LICENSE),
        "class_coverage": class_coverage,
        "property_coverage": property_coverage,
        "omitted_no_useful_properties": int(metadata.get("omitted_no_useful_properties", "0") or 0),
        "omitted_missing_label": int(metadata.get("omitted_missing_label", "0") or 0),
        "missing_source_entities": int(metadata.get("missing_source_entities", "0") or 0),
        "runtime_file_bytes": DB_PATH.stat().st_size,
        "runtime_file": DB_PATH.name,
    }


def _safe_query_expression(query: str) -> str | None:
    terms = [
        term.casefold()
        for term in re.findall(r"\w+", (query or "")[:MAX_QUERY_LENGTH], flags=re.UNICODE)[:MAX_QUERY_TERMS]
    ]
    if not terms:
        return None
    return " AND ".join(f'"{term.replace(chr(34), chr(34) * 2)}"*' for term in terms)


def _json_value(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _facts(connection: sqlite3.Connection, record_id: str) -> list[dict[str, Any]]:
    return [
        {
            "name": str(row["name"]),
            "value": str(row["value"]),
            "unit": str(row["unit"]),
            "unit_id": str(row["unit_id"]),
            "qualifier": _json_value(row["qualifier_json"], []),
            "source_url": str(row["source_url"]),
            "sources": _json_value(row["sources_json"], []),
            "property_id": str(row["property_id"]),
            "statement_id": str(row["statement_id"]),
            "rank": str(row["rank"]),
            "value_entity_id": str(row["value_entity_id"]),
            "quantity_bounds": _json_value(row["quantity_bounds_json"], {}),
        }
        for row in connection.execute(
            "SELECT * FROM facts WHERE record_id=? "
            "ORDER BY CASE property_id WHEN 'P274' THEN 0 WHEN 'P1088' THEN 1 "
            "WHEN 'P556' THEN 2 WHEN 'P2054' THEN 3 ELSE 4 END,name COLLATE NOCASE,statement_id",
            (record_id,),
        )
    ]


def _record(connection: sqlite3.Connection, row: sqlite3.Row, *, include_properties: bool = True) -> dict[str, Any]:
    record = {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "formula": str(row["formula"]),
        "formula_values": _json_value(row["formula_values_json"], []),
        "kind": str(row["kind"]),
        "classes": _json_value(row["classes_json"], []),
        "source_url": str(row["source_url"]),
        "license": str(row["license"]),
        "property_count": int(row["property_count"]),
    }
    if include_properties:
        record["properties"] = _facts(connection, record["id"])
    return record


def search_minerals(query: str = "", page: int = 1) -> dict[str, Any]:
    """Search names, formulas, classifications, and source-reported property values."""
    if not available():
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    expression = _safe_query_expression(query)
    where = " WHERE r.rowid IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)" if expression else ""
    params: list[Any] = [expression] if expression else []
    try:
        requested_page = max(1, int(page or 1))
    except (TypeError, ValueError):
        requested_page = 1
    with _connect() as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM records r" + where, params).fetchone()[0])  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        current_page = min(requested_page, pages)
        selected = connection.execute(
            "SELECT r.* FROM records r" + where +  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            " ORDER BY r.name_sort,r.id LIMIT ? OFFSET ?",
            [*params, PAGE_SIZE, (current_page - 1) * PAGE_SIZE],
        ).fetchall()
        rows = [_record(connection, row) for row in selected]
    return {"rows": rows, "total": total, "page": current_page, "pages": pages}


def get_mineral(record_id: str | None) -> dict[str, Any] | None:
    """Return one full record by ``wikidata:Q...`` or a bare Wikidata QID."""
    if not available() or record_id is None:
        return None
    value = str(record_id).strip()
    if value.startswith("wikidata:"):
        value = value[len("wikidata:"):]
    if not re.fullmatch(r"Q[1-9][0-9]{0,11}", value):
        return None
    with _connect() as connection:
        row = connection.execute("SELECT * FROM records WHERE qid=?", (value,)).fetchone()
        return _record(connection, row) if row else None
