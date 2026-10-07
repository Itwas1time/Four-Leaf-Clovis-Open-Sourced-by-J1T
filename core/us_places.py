"""Public Census place lookup. These points represent towns, never properties."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
import re
import unicodedata

DATA = Path(__file__).resolve().parents[1] / "atlas/gui/data/us_places_2026.csv"
SOURCE = "https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html"
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def _fold(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(char))


@lru_cache(maxsize=1)
def _places():
    with DATA.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    return {row["geoid"]: {**row, "latitude": float(row["latitude"]),
                           "longitude": float(row["longitude"])} for row in rows}


def states() -> list[str]:
    return sorted({row["state"] for row in _places().values()})


def get_place(geoid, state):
    if not isinstance(geoid, str) or not re.fullmatch(r"\d{7}", geoid):
        return None
    if not isinstance(state, str) or not re.fullmatch(r"[A-Z]{2}", state):
        return None
    row = _places().get(geoid)
    return dict(row) if row and state == row["state"] else None


def _query_parts(query, state=None):
    """Accept a town with a trailing state name/code and ordinary punctuation."""
    if not isinstance(query, str) or len(query) > 80:
        return "", state
    separated = bool(re.search(r"[,.;]", query))
    query = re.sub(r"[,.;]+", " ", _fold(query)).strip()
    query = re.sub(r"\s+", " ", query)
    for code, name in sorted(STATE_NAMES.items(), key=lambda item: len(item[1]), reverse=True):
        for suffix in (_fold(name), code.lower()):
            if query.endswith(" " + suffix):
                # Names such as West New York (NJ) and New Washington (OH)
                # contain a state name. Prefer a literal town when no separator
                # explicitly marks the suffix as a state.
                if not separated and any((not state or row['state'] == state)
                                         and _fold(row['name']).startswith(query)
                                         for row in _places().values()):
                    return query, state
                if state and code != state:
                    return "", "invalid"
                return query[:-(len(suffix) + 1)].strip(), code
    return query, state


def search_places(state, query, selected=None):
    """Return at most 30 choices; never send the whole national lookup to Dash."""
    if not isinstance(state, str) or state not in states():
        return []
    search, query_state = _query_parts(query, state)
    if query_state != state:
        return []
    tokens = search.split()
    matches = [row for row in _places().values() if row["state"] == state
               and all(token in _fold(row["name"]) for token in tokens)]
    matches.sort(key=lambda row: (not _fold(row["name"]).startswith(search), row["name"]))
    choices = matches[:30]
    current = get_place(selected, state)
    if current and all(row["geoid"] != selected for row in choices):
        choices = [current, *choices[:29]]
    return [{"label": row["name"] + ", " + row["state"], "value": row["geoid"],
             "search": f"{row['name']} {STATE_NAMES[state]} {query if isinstance(query, str) and len(query) <= 80 else ''}"}
            for row in choices]


def search_towns(query, limit=8):
    """National public-place search for map navigation; no site catalogue needed."""
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 80:
        return []
    search, state = _query_parts(query)
    tokens = search.split()
    if not tokens:
        return []
    matches = [row for row in _places().values() if (not state or row['state'] == state)
               and all(token in _fold(row['name']) for token in tokens)]
    matches.sort(key=lambda row: (not _fold(row['name']).startswith(search), row['name'], row['state'], row['geoid']))
    return [{"key": 'town:' + row['geoid'], "label": row['name'] + ', ' + row['state'],
             "center": [row['latitude'], row['longitude']], "zoom": 9}
            for row in matches[:min(max(limit, 1), 30)]]
