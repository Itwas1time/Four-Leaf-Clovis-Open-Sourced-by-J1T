"""Read-only, paged access to the bundled public records catalogue."""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

DB_PATH = Path(__file__).with_name("public_catalog.sqlite")
PAGE_SIZE = 20
SOURCE_NAMES = {
    "wikidata": "Wikidata",
    "nrhp": "U.S. National Register extract",
    "curated_projects": "Researched project pages",
}


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def available() -> bool:
    return DB_PATH.is_file()


@lru_cache(maxsize=1)
def overview() -> dict:
    if not available():
        return {"built_on": "", "nrhp_scrape_date": "", "counts": [], "countries": []}
    with _connect() as connection:
        counts = [dict(row) for row in connection.execute(
            "SELECT kind, source_key, COUNT(*) AS count FROM records GROUP BY kind, source_key ORDER BY kind, source_key"
        )]
        countries = [row[0] for row in connection.execute(
            "SELECT DISTINCT country FROM records WHERE country <> '' ORDER BY country COLLATE NOCASE"
        )]
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    return {"built_on": metadata.get("built_on", ""),
            "nrhp_scrape_date": metadata.get("nrhp_scrape_date", ""),
            "counts": counts, "countries": countries}


def search_records(kind: str = "site", query: str = "", source: str = "all",
                   country: str = "all", page: int = 1) -> tuple[list[dict], int, int]:
    if kind not in ("site", "institution"):
        raise ValueError("kind must be site or institution")
    if not available():
        return [], 0, 1
    conditions = ["r.kind = ?"]
    params: list[str] = [kind]
    if source != "all":
        conditions.append("r.source_key = ?")
        params.append(source)
    if country != "all":
        conditions.append("r.country = ?")
        params.append(country)
    terms = re.findall(r"\w+", (query or "").strip(), flags=re.UNICODE)[:8]
    if terms:
        # Materialize matching row IDs once. SQLite otherwise may drive the
        # COUNT query from the kind index and re-run FTS for every record.
        conditions.append("r.id IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        params.append(" AND ".join(f'"{term}"*' for term in terms))
    where = " AND ".join(conditions)
    with _connect() as connection:
        # Clauses are static; all caller values use SQLite parameters.
        total = connection.execute(f"SELECT COUNT(*) FROM records r WHERE {where}", params).fetchone()[0]  # nosec B608
        last_page = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(int(page or 1), last_page))
        rows = [dict(row) for row in connection.execute(
            f"SELECT r.* FROM records r WHERE {where} "  # nosec B608
            "ORDER BY r.name COLLATE NOCASE, r.source_key, r.source_id LIMIT ? OFFSET ?",
            [*params, PAGE_SIZE, (page - 1) * PAGE_SIZE],
        )]
    return rows, total, page


def get_record(record_id: int | None) -> dict | None:
    if not available() or not record_id:
        return None
    with _connect() as connection:
        row = connection.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    return dict(row) if row else None
