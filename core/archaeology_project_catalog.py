"""Read source-linked archaeology publications without exposing map locations."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from core.fieldbook import validate_book
from core.resident_context import _md

DATA = Path(__file__).resolve().parents[1] / "atlas/gui/data/archaeology_projects.sqlite"
PAGE_SIZE = 12
ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")


@contextmanager
def connect():
    connection = sqlite3.connect(DATA.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def catalog_stats():
    with connect() as connection:
        row = connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()
    if row is None:
        raise ValueError("The archaeology catalog has no coverage record.")
    return json.loads(row[0])


def _query(value):
    if not isinstance(value, str) or len(value) > 120 or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("Search with up to 120 characters.")
    return value.strip()


def search_projects(query="", country="all", page=1):
    query = _query(query)
    if not isinstance(country, str) or len(country) > 100 or any(ord(c) < 32 for c in country):
        raise ValueError("Choose a country in this catalog.")
    if type(page) is not int or page < 1 or page > 10000:
        raise ValueError("Choose a valid catalog page.")
    clauses, parameters = [], []
    if country != "all":
        clauses.append("country = ?")
        parameters.append("" if country == "unrecorded" else country)
    # Escape LIKE metacharacters: ordinary input never becomes a wildcard.
    for term in query.split()[:10]:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(title || ' ' || description || ' ' || creators || ' ' || subjects || ' ' || periods || ' ' || country) LIKE ? ESCAPE '\\'")
        parameters.append("%" + escaped + "%")
    where = " AND ".join(clauses) or "1 = 1"
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM projects WHERE " + where, parameters).fetchone()[0]  # nosec B608
        last_page = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, last_page)
        rows = connection.execute("SELECT * FROM projects WHERE " + where + " ORDER BY title COLLATE NOCASE, id LIMIT ? OFFSET ?",  # nosec B608
                                  [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
    return [_decode(row) for row in rows], total, page


def _decode(row):
    record = dict(row)
    for key in ("creators", "subjects", "periods"):
        record[key] = json.loads(record[key])
    return record


def get_project(identifier):
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        return None
    with connect() as connection:
        row = connection.execute("SELECT * FROM projects WHERE id = ?", (identifier,)).fetchone()
    return _decode(row) if row else None


def chronology(record):
    def label(value):
        if value is None:
            return "not recorded"
        if value == 0:
            return "0 (source convention)"
        return f"{abs(value):,} {'BCE' if value < 0 else 'CE'}"
    if record["early_year"] is None and record["late_year"] is None:
        return "Not recorded"
    return label(record["early_year"]) + " – " + label(record["late_year"])


def facts(record):
    return [("Publisher", "Open Context"), ("Country context", record["country"] or "Not recorded"),
            ("Region", record["region"] or "Not recorded"),
            ("Creators", "; ".join(record["creators"]) or "Not recorded"),
            ("Subjects", "; ".join(record["subjects"]) or "Not recorded"),
            ("Coverage labels", "; ".join(record["periods"]) or "Not recorded"),
            ("Source time span", chronology(record)),
            ("Published", record["published"] or "Not recorded"),
            ("Source modified", record["updated"] or "Not recorded")]


def project_entry(identifier):
    """Save authoritative bundled fields; never accept client-supplied metadata."""
    record = get_project(identifier)
    if not record:
        raise ValueError("Choose a publication from the archaeology catalog.")
    lines = ["# Archaeology publication — " + _md(record["title"]), "",
             "Published dataset reference. Its time span describes source coverage, not a current dig season or the age of a separate find.", ""]
    for label, value in facts(record):
        lines.append("- " + label + ": " + _md(value))
    if record["description"]:
        lines += ["", "## Source description", "", _md(record["description"])]
    lines += ["", "- Source record: " + record["source_url"],
              "- Metadata license: " + record["license_url"],
              "- Catalog retrieved: " + catalog_stats()["retrieved"]]
    if record["citation_url"]:
        lines.append("- Citation identifier: " + record["citation_url"])
    lines += ["", "Clovis selected bibliographic fields and rendered source text as plain text. These selected source fields retain the metadata license linked above. The full dataset, abstract, images and excavation coordinates are not included in these notes."]
    text = "\n".join(lines)
    entry = {"id": hashlib.sha256(("archaeology-publication:" + record["id"] + text).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Publication · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Archaeology publication", "source": record["source_url"],
                         "date": chronology(record), "outcome": "Published dataset reference"},
             "markdown": text}
    validate_book({"version": 1, "entries": [entry]})
    return entry
