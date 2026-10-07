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


def search_places(state, query, selected=None):
    """Return at most 30 choices; never send the whole national lookup to Dash."""
    if not isinstance(state, str) or state not in states():
        return []
    if not isinstance(query, str) or len(query) > 80:
        query = ""
    tokens = _fold(query.strip()).split()
    matches = [row for row in _places().values() if row["state"] == state
               and all(token in _fold(row["name"]) for token in tokens)]
    matches.sort(key=lambda row: (not _fold(row["name"]).startswith(_fold(query.strip())), row["name"]))
    choices = matches[:30]
    current = get_place(selected, state)
    if current and all(row["geoid"] != selected for row in choices):
        choices = [current, *choices[:29]]
    return [{"label": row["name"] + ", " + row["state"], "value": row["geoid"]} for row in choices]
