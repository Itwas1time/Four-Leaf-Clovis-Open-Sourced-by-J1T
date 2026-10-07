"""
Helpers for normalizing archaeological period labels into approximate BP ranges.
"""

from __future__ import annotations

import re


def normalize_period_text(value) -> str:
    return " ".join(str(value or "").lower().replace("/", " ").replace("-", " ").split())


def _contains_keyword(text: str, keyword: str) -> bool:
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


_PERIOD_RULES: list[tuple[tuple[str, ...], tuple[int, int], str]] = [
    (("disputed pre clovis", "pre clovis"), (16000, 25000), "Pre-Clovis"),
    (("clovis",), (12800, 13500), "Clovis"),
    (("folsom",), (10000, 12900), "Folsom"),
    (("paleoindian",), (10000, 16000), "Paleoindian"),
    (("pleistocene",), (12000, 25000), "Pleistocene"),
    (("early archaic",), (8000, 10000), "Early Archaic"),
    (("middle archaic",), (5000, 8000), "Middle Archaic"),
    (("late archaic", "maritime archaic"), (3000, 5000), "Late Archaic"),
    (("archaic",), (3000, 10000), "Archaic"),
    (("adena",), (2000, 3000), "Adena"),
    (("hopewell", "laurel"), (1000, 2200), "Hopewell"),
    (("early woodland",), (2000, 3000), "Early Woodland"),
    (("middle woodland",), (1000, 2000), "Middle Woodland"),
    (("late woodland",), (500, 1400), "Late Woodland"),
    (("woodland",), (500, 3000), "Woodland"),
    (("basketmaker",), (1300, 2200), "Basketmaker"),
    (("ancestral puebloan",), (700, 2200), "Ancestral Puebloan"),
    (("pueblo ii iii",), (650, 1150), "Pueblo II-III"),
    (("pueblo iii",), (650, 900), "Pueblo III"),
    (("pueblo ii",), (800, 1150), "Pueblo II"),
    (("puebloan", "pueblo"), (650, 1300), "Puebloan"),
    (("sinagua",), (700, 1200), "Sinagua"),
    (("hohokam",), (700, 2000), "Hohokam"),
    (("mogollon",), (700, 2000), "Mogollon"),
    (("salado",), (600, 1300), "Salado"),
    (("fremont",), (700, 1700), "Fremont"),
    (("mississippian", "caddo"), (500, 1300), "Mississippian"),
    (("fort ancient",), (400, 1000), "Fort Ancient"),
    (("plains village", "oneota"), (300, 1300), "Plains Village"),
    (("late prehistoric", "prehistoric"), (300, 1500), "Late Prehistoric"),
    (("contact", "colonial", "historic", "protohistoric"), (0, 500), "Historic/Contact"),
    (("modern", "present"), (0, 100), "Modern"),
]


def infer_period_range_bp(value) -> tuple[int | None, int | None, str | None]:
    text = normalize_period_text(value)
    if not text:
        return None, None, None

    skip_generic_archaic = any(_contains_keyword(text, token) for token in ("early archaic", "middle archaic", "late archaic", "maritime archaic"))
    skip_generic_woodland = any(_contains_keyword(text, token) for token in ("early woodland", "middle woodland", "late woodland"))
    skip_generic_pueblo = any(_contains_keyword(text, token) for token in ("ancestral puebloan", "basketmaker", "pueblo ii", "pueblo iii", "puebloan"))
    skip_generic_paleo = any(_contains_keyword(text, token) for token in ("clovis", "folsom", "pre clovis"))

    starts: list[int] = []
    ends: list[int] = []
    labels: list[str] = []
    for keywords, (end_bp, start_bp), label in _PERIOD_RULES:
        if label == "Archaic" and skip_generic_archaic:
            continue
        if label == "Woodland" and skip_generic_woodland:
            continue
        if label == "Puebloan" and skip_generic_pueblo:
            continue
        if label == "Paleoindian" and skip_generic_paleo:
            continue
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            starts.append(start_bp)
            ends.append(end_bp)
            labels.append(label)

    if not starts:
        return None, None, None
    return max(starts), min(ends), " / ".join(dict.fromkeys(labels))


def period_matches_year(years_bp: int | None, value, *, start_key=None, end_key=None, props=None) -> bool:
    years_bp = 0 if years_bp is None else years_bp
    if props and start_key and end_key:
        start_bp = props.get(start_key)
        end_bp = props.get(end_key)
    else:
        start_bp = end_bp = None
    if start_bp is None or end_bp is None:
        start_bp, end_bp, _ = infer_period_range_bp(value)
    if start_bp is None or end_bp is None:
        return False
    return end_bp <= years_bp <= start_bp
