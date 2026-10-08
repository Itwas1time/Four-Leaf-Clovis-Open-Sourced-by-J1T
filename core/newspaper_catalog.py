"""Offline Library of Congress directory of U.S. newspaper titles.

This coordinate-free catalog contains descriptive title metadata, not newspaper
articles or images. Town matches use the exact city/state values supplied by
the Library of Congress; a missing town match may be shown as statewide only
when the caller supplied a state.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from core.us_places import STATE_NAMES as CENSUS_STATE_NAMES

DATA = Path(__file__).resolve().parents[1] / "atlas/gui/data/newspaper_catalog.sqlite"
PAGE_SIZE = 24
SOURCE_TITLE = "Library of Congress, Directory of U.S. Newspapers in American Libraries"
SOURCE_URL = "https://www.loc.gov/collections/directory-of-us-newspapers-in-american-libraries/"

# These codes extend the Census place file's 50 states, DC, and Puerto Rico to
# the other U.S. territories used by LOC. A state code is exposed only when it
# can be matched to a recognized LOC geographic value.
STATE_NAMES = {
    **CENSUS_STATE_NAMES,
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "VI": "U.S. Virgin Islands",
}
_STATE_CODES = {name.casefold(): code for code, name in STATE_NAMES.items()}
_STATE_CODES.update({
    "district of columbia": "DC",
    "american samoa": "AS",
    "commonwealth of the northern mariana islands": "MP",
    "northern mariana islands": "MP",
    "mariana islands": "MP",
    "u.s. virgin islands": "VI",
    "us virgin islands": "VI",
    "united states virgin islands": "VI",
    "virgin islands of the united states": "VI",
    "virgin islands": "VI",
})
_ID_RE = re.compile(r"(?:[a-z]{2,3}\d{8,10}|\d{8,10})\Z", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(?:16|17|18|19|20)\d{2}(?!\d)")
_COVERAGE_KEYS = (
    "snapshot_complete", "snapshot_mode", "source_records_observed",
    "source_records_expected", "source_pages_observed", "source_pages_expected",
    "coverage_note",
)


def normalize_town(value: str) -> str:
    """Normalize a town for exact lookup without expanding historical aliases."""
    if not isinstance(value, str) or len(value) > 240:
        return ""
    if any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        return ""
    folded = "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", folded)).strip()


def _state_code(value: str) -> str | None:
    if not isinstance(value, str):
        raise ValueError("Choose a valid U.S. state or territory.")
    key = value.strip().casefold()
    if not key:
        return None
    if len(key) == 2:
        if key.upper() in STATE_NAMES:
            return key.upper()
        raise ValueError("Choose a valid U.S. state or territory.")
    code = _STATE_CODES.get(key)
    if not code:
        raise ValueError("Choose a valid U.S. state or territory.")
    return code


@contextmanager
def _connect():
    connection = sqlite3.connect(DATA.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


@lru_cache(maxsize=1)
def _summary():
    with _connect() as connection:
        row = connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()
    if not row:
        raise RuntimeError("The newspaper catalog has no source summary.")
    return json.loads(row[0])


def _coverage():
    summary = _summary()
    return {key: summary.get(key) for key in _COVERAGE_KEYS}


def _validated_town(value):
    if value in (None, ""):
        return ""
    key = normalize_town(value)
    if not key:
        raise ValueError("Enter a valid town name.")
    return key


def catalog_stats(state="", town=""):
    """Return source counts or exact counts for a state/town selection.

    A town with no matching catalog records returns zero counts. This method
    never substitutes statewide figures for an exact town count.
    """
    code = _state_code(state)
    town_key = _validated_town(town)
    if not code and not town_key:
        result = json.loads(json.dumps(_summary()))
        result.update({
            "titles": result["included_titles"],
            "scope": "national",
            "state": "",
            "town": "",
            "exact_town": False,
        })
        return result

    clauses, params = [], []
    if code:
        clauses.append("p.state=?")
        params.append(code)
    if town_key:
        clauses.append("p.town_key=?")
        params.append(town_key)
    where = " AND ".join(clauses)
    with _connect() as connection:
        row = connection.execute(
            "SELECT count(DISTINCT t.id) AS titles, "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            "count(DISTINCT CASE WHEN t.digitized=1 THEN t.id END) AS digitized, "
            "min(t.start_year) AS earliest_year, max(t.end_year) AS latest_year "
            "FROM titles t JOIN places p ON p.id=t.id WHERE " + where,
            params,
        ).fetchone()
        states = [r[0] for r in connection.execute(
            "SELECT DISTINCT p.state FROM places p JOIN titles t ON t.id=p.id WHERE "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            + where + " ORDER BY p.state", params,
        )]
        state_counts = dict(connection.execute(
            "SELECT p.state,count(DISTINCT t.id) FROM places p JOIN titles t ON t.id=p.id WHERE "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            + where + " GROUP BY p.state ORDER BY p.state", params,
        ).fetchall())
        towns = connection.execute(
            "SELECT count(DISTINCT p.town_key) FROM places p JOIN titles t ON t.id=p.id "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            "WHERE p.town_key!='' AND " + where,
            params,
        ).fetchone()[0]
    titles = row["titles"]
    return {
        "titles": titles,
        "digitized": row["digitized"],
        "states": state_counts,
        "state_count": len(states),
        "towns": towns,
        "earliest_year": row["earliest_year"],
        "latest_year": row["latest_year"],
        "scope": "town" if town_key else "state",
        "state": code or "",
        "town": town if town_key else "",
        "exact_town": bool(town_key and titles),
        "snapshot": _summary()["snapshot"],
        "source_url": SOURCE_URL,
        "rights": _summary()["rights"],
        **_coverage(),
    }


def _safe_query(value):
    if not isinstance(value, str) or len(value) > 120:
        raise ValueError("Enter a search phrase of 120 characters or fewer.")
    if any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("Enter a valid search phrase.")
    if any(char in value for char in "%_\\"):
        raise ValueError("Search phrases cannot contain wildcard characters.")
    return value.strip()


def _decorate(rows, connection):
    if not rows:
        return []
    ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in ids)
    places = {}
    for place in connection.execute(
        "SELECT id,state,town FROM places WHERE id IN (" + placeholders + ") "  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        "ORDER BY state,town", ids,
    ):
        places.setdefault(place["id"], []).append({
            "state": place["state"],
            "state_name": STATE_NAMES.get(place["state"], place["state"]),
            "town": place["town"] or "",
        })
    result = []
    coverage = _coverage()
    for source_row in rows:
        row = dict(source_row)
        row["places"] = places.get(row["id"], [])
        row["source"] = SOURCE_TITLE
        row["catalog"] = True
        row["digitized"] = bool(row["digitized"])
        row.update(coverage)
        result.append(row)
    return result


def search_titles(state="", town="", query="", page=1):
    """Search a local page of up to 24 title records, without network access.

    Exact city/state matching uses only LOC's indexed city and state fields. If
    an exact town is absent and a state was supplied, the results fall back to
    that state's catalog and return ``scope='state'`` with ``exact_town=False``.
    """
    code = _state_code(state)
    town_key = _validated_town(town)
    phrase = _safe_query(query)
    if type(page) is not int or not 1 <= page <= 100_000:
        raise ValueError("Choose a valid newspaper catalog page.")

    params = []
    where = []
    exact_town = False
    scope = "national"
    if town_key:
        checks, check_params = ["town_key=?"], [town_key]
        if code:
            checks.append("state=?")
            check_params.append(code)
        with _connect() as connection:
            exact_town = connection.execute(
                "SELECT 1 FROM places WHERE " + " AND ".join(checks) + " LIMIT 1",  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
                check_params,
            ).fetchone() is not None
        if exact_town:
            where.extend(["p.town_key=?"])
            params.append(town_key)
            if code:
                where.append("p.state=?")
                params.append(code)
            scope = "town"
        elif code:
            where.append("p.state=?")
            params.append(code)
            scope = "state"
        else:
            return {
                "rows": [], "total": 0, "page": 1, "pages": 0,
                "scope": "national", "exact_town": False,
                "state": "", "town": town, "query": phrase,
                "snapshot": _summary()["snapshot"],
                **_coverage(),
            }
    elif code:
        where.append("p.state=?")
        params.append(code)
        scope = "state"

    if phrase:
        pattern = "%" + phrase + "%"
        search = (
            "(t.title LIKE ? COLLATE NOCASE OR "
            "t.summary LIKE ? COLLATE NOCASE OR "
            "t.languages LIKE ? COLLATE NOCASE OR "
            "t.id IN (SELECT px.id FROM places px WHERE "
            "(px.town LIKE ? COLLATE NOCASE OR px.state_name LIKE ? COLLATE NOCASE)))"
        )
        where.append(search)
        params.extend([pattern] * 5)

    join = " JOIN places p ON p.id=t.id" if scope in ("town", "state") else ""
    condition = " WHERE " + " AND ".join(where) if where else ""
    with _connect() as connection:
        total = connection.execute(
            "SELECT count(DISTINCT t.id) FROM titles t" + join + condition,  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            params,
        ).fetchone()[0]
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        page = min(page, pages) if pages else 1
        offset = (page - 1) * PAGE_SIZE
        order = "t.start_year IS NULL,t.start_year,t.title,t.id"
        rows = connection.execute(
            "SELECT DISTINCT t.* FROM titles t" + join + condition  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            + " ORDER BY " + order + " LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, offset],
        ).fetchall()
        result_rows = _decorate(rows, connection)
    return {
        "rows": result_rows,
        "total": total,
        "page": page,
        "pages": pages,
        "scope": scope,
        "exact_town": exact_town,
        "state": code or "",
        "town": town if town_key else "",
        "query": phrase,
        "snapshot": _summary()["snapshot"],
        **_coverage(),
    }


def get_title(identifier):
    """Return one title by a validated stable LOC item ID, or ``None``."""
    if not isinstance(identifier, str) or not _ID_RE.fullmatch(identifier):
        return None
    with _connect() as connection:
        row = connection.execute("SELECT * FROM titles WHERE id=?", (identifier,)).fetchone()
        return _decorate([row], connection)[0] if row else None
