"""Indexed source dating results from a verified optional local collection."""
from contextlib import closing
import hashlib
import json
import re
import sqlite3
from core.data_packs import PackStore

PACK = "radiocarbon-world"
PAGE_SIZE = 24


def definition():
    return PackStore().definition(PACK)


def database():
    return PackStore().resolve_file(PACK, "radiocarbon.sqlite")


def stats():
    path = database()
    if path is None:
        return None
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        value = connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()
    return json.loads(value[0])


def _query(value):
    if (not isinstance(value, str) or len(value) > 160
            or any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in value)):
        raise ValueError("Search with up to 160 characters.")
    return value.strip()


def search(query="", country="all", min_age=None, max_age=None, page=1):
    query = _query(query)
    if not isinstance(country, str) or len(country) > 80 or any(ord(character) < 32 for character in country):
        raise ValueError("Choose a recorded country.")
    if type(page) is not int or not 1 <= page <= 100_000:
        raise ValueError("Choose a valid collection page.")
    for value in (min_age, max_age):
        if value is not None and (type(value) is not int or not -10**7 <= value <= 10**7):
            raise ValueError("Use integer laboratory ages in uncalibrated BP.")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise ValueError("The minimum laboratory age must not exceed the maximum.")
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    clauses, parameters = [], []
    terms = re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    if terms:
        clauses.append("r.rowid IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        parameters.append(" AND ".join('"' + term + '"*' for term in terms))
    if country != "all":
        clauses.append("r.country=?")
        parameters.append("" if country == "__unknown__" else country)
    if min_age is not None:
        clauses.append("r.age_bp>=?")
        parameters.append(min_age)
    if max_age is not None:
        clauses.append("r.age_bp<=?")
        parameters.append(max_age)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        total = connection.execute("SELECT count(*) FROM records r" + where, parameters).fetchone()[0]  # nosec B608: fixed clauses, parameterized values
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in connection.execute(
            "SELECT r.* FROM records r" + where + " ORDER BY r.age_bp,r.lab_id LIMIT ? OFFSET ?",  # nosec B608: fixed clauses, parameterized values
            [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row.pop("rowid", None)
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


def get_date(identifier):
    if not isinstance(identifier, str) or not identifier.startswith("p3k:") or len(identifier) > 110:
        return None
    path = database()
    if path is None:
        return None
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM records WHERE id=?", (identifier,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result.pop("rowid", None)
    return result


def facts(row):
    return [("Laboratory identifier", row["lab_id"]),
            ("Uncalibrated radiocarbon age", f'{row["age_bp"]:,} years BP'),
            ("One-sigma standard error", f'{row["error_bp"]:,} radiocarbon years'),
            ("Sample material", row["material"] or "Not recorded"),
            ("Source taxonomic label", row["taxa"] or "Not recorded"),
            ("Laboratory method", row["method"] or "Not recorded"),
            ("Source δ13C value", row["delta13c_source"] or "Not recorded"),
            ("Source period label", row["period"] or "Not recorded"),
            ("Recorded site identifier", row["site_id"] or "Not recorded"),
            ("Recorded site name", row["site_name"] or "Not recorded"),
            ("Country", row["country"] or "Not recorded"),
            ("Province / administrative label", row["province"] or "Not recorded"),
            ("Source continent label", row["continent"] or "Not recorded"),
            ("Contributing dataset labels", row["source_datasets"]),
            ("Original source reference", row["reference"] or "Not recorded")]


def reference_entry(identifier):
    from datetime import datetime, timezone
    from core.fieldbook import validate_book
    from core.resident_context import _md
    row = get_date(identifier)
    if row is None:
        raise ValueError("Choose a dating result from the installed collection.")
    summary = stats()
    lines = ["# Published radiocarbon result — " + _md(row["lab_id"]), "",
             "A published source determination. This does not date or identify a separate find.", ""]
    lines.extend("- " + label + ": " + _md(value) for label, value in facts(row))
    lines.extend(["", "## Source and conventions", summary["citation"],
                  summary["citation_url"], "Source release: " + summary["source_release"],
                  "Data rights: CC0 1.0.", "",
                  "Age and uncertainty retain their original laboratory units. No calendar calibration is applied.",
                  summary["source_field_note"],
                  "No selected town or observation is assigned to this reference. Coordinates are omitted."])
    text = "\n".join(lines)
    entry = {"id": hashlib.sha256(("radiocarbon:" + text).encode()).hexdigest()[:24],
             "kind": "investigation", "title": "Radiocarbon reference · " + row["lab_id"],
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published radiocarbon reference", "source": summary["citation_url"],
                         "material": row["material"] or "Not recorded",
                         "outcome": f'{row["age_bp"]} ± {row["error_bp"]} uncalibrated radiocarbon years BP'},
             "markdown": text}
    validate_book({"version": 1, "entries": [entry]})
    return entry
