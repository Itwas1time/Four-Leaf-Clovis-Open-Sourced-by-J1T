"""Read-only access to the bundled USGS Cooperative National Geologic Map."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "atlas" / "gui" / "data" / "usgs_units.sqlite"
PAGE_SIZE = 24
_GEOID = re.compile(r"\d{7}\Z")
_UNIT_ID = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")
_STATE = re.compile(r"[A-Z]{2}\Z")


def _connect() -> sqlite3.Connection:
    """Open the bundled snapshot without creating or changing database files."""
    uri = DB_PATH.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def available() -> bool:
    return DB_PATH.is_file()


def _meta(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT key, value FROM metadata"))


def _json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _public_unit(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["source_citations"] = _json_list(result.pop("source_citations_json", None))
    result["mapped_places"] = int(result.get("mapped_places", 0) or 0)
    return result


def catalog_stats() -> dict[str, Any]:
    """Return snapshot counts, coverage, release details, and source checksums."""
    empty = {
        "available": False,
        "version": "",
        "map_scale": "",
        "source_hash": "",
        "source_snapshot_sha256": "",
        "gazetteer_hash": "",
        "unit_count": 0,
        "source_unit_count": 0,
        "mapped_places": 0,
        "place_count": 0,
        "unmapped_places": 0,
        "layers": [],
        "layer_coverage": [],
        "state_coverage": [],
        "state_layer_coverage": [],
        "sources": [],
    }
    if not available():
        return empty

    with _connect() as connection:
        metadata = _meta(connection)
        unit_count = int(connection.execute("SELECT COUNT(*) FROM units").fetchone()[0])
        source_unit_count = int(connection.execute("SELECT COUNT(*) FROM unit_source_units").fetchone()[0])
        mapped_places = int(connection.execute(
            "SELECT COUNT(DISTINCT geoid) FROM place_units"
        ).fetchone()[0])
        layer_counts = [dict(row) for row in connection.execute(
            "SELECT layer, layer_label, COUNT(*) AS unit_count "
            "FROM units GROUP BY layer, layer_label ORDER BY layer_order, layer"
        )]
        states = [dict(row) for row in connection.execute(
            "SELECT state, place_count, mapped_places, unit_count, gap_count "
            "FROM state_coverage ORDER BY state"
        )]
        layer_coverage = [dict(row) for row in connection.execute(
            "SELECT layer, layer_label, place_count, mapped_places, unit_count, gap_count "
            "FROM layer_coverage ORDER BY layer_order, layer"
        )]
        state_layer_coverage = [dict(row) for row in connection.execute(
            "SELECT state, layer, layer_label, place_count, mapped_places, unit_count, gap_count "
            "FROM state_layer_coverage ORDER BY state, layer_order, layer"
        )]

    try:
        place_count = int(metadata.get("census_place_count", "0"))
    except ValueError:
        place_count = 0
    return {
        "available": True,
        "version": metadata.get("product_version", ""),
        "map_scale": metadata.get("map_scale", ""),
        "source_hash": metadata.get(
            "source_snapshot_sha256", metadata.get("source_archive_sha256", "")
        ),
        "source_snapshot_sha256": metadata.get(
            "source_snapshot_sha256", metadata.get("source_archive_sha256", "")
        ),
        "gazetteer_hash": metadata.get("census_gazetteer_sha256", ""),
        "unit_count": unit_count,
        "source_unit_count": source_unit_count,
        "mapped_places": mapped_places,
        "place_count": place_count,
        "unmapped_places": max(0, place_count - mapped_places),
        "layers": layer_counts,
        "layer_coverage": layer_coverage,
        "state_coverage": states,
        "state_layer_coverage": state_layer_coverage,
        "sources": _json_list(metadata.get("primary_sources_json")),
    }


def _like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_units(state: str = "", query: str = "", page: int = 1) -> dict[str, Any]:
    """Search reviewed unit records, optionally limited to units mapped at towns."""
    if not available():
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    if not isinstance(state, str):
        state = ""
    state = state.strip().upper()
    if state and not _STATE.fullmatch(state):
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    if not isinstance(query, str) or len(query) > 120:
        query = ""
    query = query.strip()

    conditions: list[str] = []
    params: list[Any] = []
    if state:
        conditions.append(
            "EXISTS (SELECT 1 FROM place_units p WHERE p.unit_id = u.id AND p.state = ?)"
        )
        params.append(state)
    if query:
        pattern = f"%{_like(query)}%"
        conditions.append(
            "(u.name LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "u.full_name LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "u.age LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "u.description LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "u.geomaterial LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "u.source_citations_json LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "EXISTS (SELECT 1 FROM unit_source_units s WHERE s.unit_id = u.id AND "
            "(s.source_name LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "s.source_full_name LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "s.source_age LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "s.source_description LIKE ? ESCAPE '\\' COLLATE NOCASE OR "
            "s.geomaterial LIKE ? ESCAPE '\\' COLLATE NOCASE)))"
        )
        params.extend([pattern] * 11)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    try:
        requested_page = max(1, int(page or 1))
    except (TypeError, ValueError):
        requested_page = 1

    with _connect() as connection:
        total = int(connection.execute(
            f"SELECT COUNT(*) FROM units u{where}", params  # nosec B608: clauses are fixed
        ).fetchone()[0])
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        current_page = min(requested_page, pages)
        rows = [
            _public_unit(row) for row in connection.execute(
                f"SELECT u.*, (SELECT COUNT(DISTINCT p.geoid) FROM place_units p "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
                f"WHERE p.unit_id = u.id) AS mapped_places FROM units u{where} "
                "ORDER BY u.layer_order, u.name COLLATE NOCASE, u.map_unit "
                "LIMIT ? OFFSET ?",
                [*params, PAGE_SIZE, (current_page - 1) * PAGE_SIZE],
            )
        ]
    return {"rows": rows, "total": total, "page": current_page, "pages": pages}


def units_for_place(geoid: str) -> list[dict[str, Any]]:
    """Return only map units intersecting this Census place point; no extrapolation."""
    if not available() or not isinstance(geoid, str) or not _GEOID.fullmatch(geoid):
        return []
    with _connect() as connection:
        rows = connection.execute(
            "SELECT u.*, p.state, p.source_map_units_json, p.map_source_ids_json, "
            "p.data_source_ids_json, "
            "p.identity_confidence FROM place_units p JOIN units u ON u.id = p.unit_id "
            "WHERE p.geoid = ? ORDER BY u.layer_order, u.name COLLATE NOCASE, u.map_unit",
            (geoid,),
        )
        results = []
        for row in rows:
            item = _public_unit(row)
            item["unit_source_citations"] = item["source_citations"]
            place_citations = []
            citation_rows = connection.execute(
                "SELECT c.citation_json FROM place_unit_citations p "
                "JOIN citations c ON c.id = p.citation_id "
                "WHERE p.geoid = ? AND p.layer = ? AND p.unit_id = ? "
                "ORDER BY c.citation_json",
                (geoid, item["layer"], item["id"]),
            )
            for citation_row in citation_rows:
                try:
                    citation = json.loads(citation_row["citation_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(citation, dict):
                    place_citations.append(citation)
            item["source_citations"] = place_citations
            item["source_map_units"] = _json_list(item.pop("source_map_units_json", None))
            item["map_source_ids"] = _json_list(item.pop("map_source_ids_json", None))
            item["data_source_ids"] = _json_list(item.pop("data_source_ids_json", None))
            item["source_units"] = _source_units(
                connection, item["id"], item["source_map_units"], limit=30
            )
            results.append(item)
    return results


def get_unit(unit_id: str | int | None) -> dict[str, Any] | None:
    """Return one catalog record by its exact, bounded stable identifier."""
    if not available() or unit_id is None:
        return None
    value = str(unit_id).strip()
    if not _UNIT_ID.fullmatch(value):
        return None
    with _connect() as connection:
        row = connection.execute(
            "SELECT u.*, (SELECT COUNT(DISTINCT p.geoid) FROM place_units p "
            "WHERE p.unit_id = u.id) AS mapped_places FROM units u WHERE u.id = ?",
            (value,),
        ).fetchone()
        if not row:
            return None
        result = _public_unit(row)
        result["source_units"] = _source_units(connection, value, None, limit=100)
        result["source_units_truncated"] = len(result["source_units"]) == 100 and int(
            connection.execute("SELECT COUNT(*) FROM unit_source_units WHERE unit_id = ?", (value,)).fetchone()[0]
        ) > 100
    return result


def _source_units(
    connection: sqlite3.Connection,
    unit_id: str,
    source_map_units: list[str] | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM unit_source_units WHERE unit_id = ?"
    params: list[Any] = [unit_id]
    if source_map_units is not None:
        if not source_map_units:
            return []
        placeholders = ",".join("?" for _ in source_map_units)
        query += f" AND source_mapunit IN ({placeholders})"
        params.extend(source_map_units)
    query += " ORDER BY source_name COLLATE NOCASE, source_mapunit, id LIMIT ?"
    params.append(limit)
    result = []
    for row in connection.execute(query, params):
        item = dict(row)
        item["source_citations"] = _json_list(item.pop("source_citations_json", None))
        result.append(item)
    return result
