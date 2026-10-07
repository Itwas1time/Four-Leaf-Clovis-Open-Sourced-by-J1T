"""Offline, evidence-led planning for archaeological research areas.

This module ranks *research follow-up*, not excavation locations or the
probability of a discovery. The bundled site records are useful context, but
their coordinates and sampling effort are too uncertain to calibrate a dig
probability. Independent observations must be supplied with provenance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import cached_property
import json
from math import isfinite
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StudyBounds:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in (self.min_lat, self.min_lon, self.max_lat, self.max_lon))
                or not (-90 <= self.min_lat < self.max_lat <= 90 and -180 <= self.min_lon < self.max_lon <= 180)):
            raise ValueError("bbox coordinates are out of range or reversed")

    def contains_point(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


class PlanDataStore:
    """Read the two bundled site files without optional map dependencies."""

    def __init__(self, project_root: Path | None = None):
        self.root = project_root or Path(__file__).resolve().parent.parent

    def _read(self, name: str) -> list[dict]:
        path = self.root / "tools" / "processed" / name
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        return data.get("records", []) if isinstance(data, dict) else data

    @cached_property
    def master_sites(self) -> list[dict]:
        return self._read("master_processed.json")

    @cached_property
    def nrhp_sites(self) -> list[dict]:
        return self._read("nrhp_geocoded.json")


INDEPENDENT_KINDS = {
    "archival_document",
    "hydrology",
    "lidar",
    "paleoenvironment",
    "prior_survey",
    "soil",
    "terrain",
}

ARCHAEOLOGY_TERMS = (
    "archaeolog", "archeolog", "prehistoric", "paleoindian", "archaic",
    "midden", "lithic", "pueblo", "rock shelter", "rockshelter",
    "petroglyph", "earthwork", "mound", "ancient village",
)
SENSITIVE_TERMS = (
    "burial", "cemetery", "grave", "mortuary", "sacred", "funerary",
)
FIND_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("midden", "shell"), "midden or shell deposits"),
    (("lithic", "flint", "chert", "quarry", "workshop"), "stone tools or production debris"),
    (("rock shelter", "rockshelter", "cave", "alcove"), "shelter deposits"),
    (("pueblo", "village", "habitation", "settlement"), "habitation features"),
    (("mound", "earthwork"), "earthworks"),
    (("petroglyph", "pictograph", "rock art"), "rock art"),
)


def _text(record: dict) -> str:
    return " ".join(str(record.get(key) or "") for key in ("name", "description", "site_type")).lower()


def _in_bbox(record: dict, bbox: StudyBounds) -> bool:
    try:
        lat, lon = float(record["lat"]), float(record["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return bbox.contains_point(lat, lon)


def _context_records(store: PlanDataStore, bbox: StudyBounds) -> tuple[list[dict], list[dict]]:
    open_context = [
        record for record in store.master_sites
        if record.get("source") == "open_context"
        and str(record.get("site_type", "")).lower() == "site"
        and _in_bbox(record, bbox)
    ]
    nrhp = [
        record for record in store.nrhp_sites
        if str(record.get("site_type", "")).upper() == "SITE"
        and _in_bbox(record, bbox)
    ]
    return open_context, nrhp


def _find_hints(records: list[dict]) -> list[dict]:
    counts: Counter[str] = Counter()
    for record in records:
        text = _text(record)
        if any(term in text for term in SENSITIVE_TERMS):
            continue
        for tokens, label in FIND_HINTS:
            if any(token in text for token in tokens):
                counts[label] += 1
    return [
        {"class": label, "supporting_records": count, "basis": "words in existing records"}
        for label, count in counts.most_common(4)
    ]


def _independent_signals(candidate: dict) -> list[dict]:
    accepted: list[dict] = []
    seen_kinds: set[str] = set()
    seen_sources: set[str] = set()
    raw_signals = candidate.get("signals")
    if raw_signals is None:
        raw_signals = []
    if not isinstance(raw_signals, list):
        raise ValueError("signals must be an array")
    if len(raw_signals) > 100:
        raise ValueError("Provide at most 100 signal observations per candidate")
    for raw in raw_signals:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "").strip().lower()
        if not isinstance(raw.get("source"), str) or not isinstance(raw.get("observation"), str):
            continue
        source = raw["source"].strip()
        observation = raw["observation"].strip()
        if isinstance(raw.get("strength"), bool):
            continue
        try:
            strength = float(raw.get("strength"))
        except (TypeError, ValueError, OverflowError):
            continue
        if (kind not in INDEPENDENT_KINDS or kind in seen_kinds or
                not source or source.lower() in seen_sources or not observation):
            continue
        if not isfinite(strength) or not 0 <= strength <= 1:
            continue
        accepted.append({
            "kind": kind,
            "source": source,
            "observation": observation,
            "strength": strength,
        })
        seen_kinds.add(kind)
        seen_sources.add(source.lower())
    return accepted


def assess_candidate(candidate: dict, store: PlanDataStore | None = None) -> dict[str, Any]:
    """Assess a named study area without exposing specific site coordinates."""
    store = store or PlanDataStore()
    bounds = candidate.get("bbox")
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
        raise ValueError("bbox must be [min_lat, min_lon, max_lat, max_lon]")
    if any(isinstance(value, bool) for value in bounds):
        raise ValueError("bbox coordinates must be numbers, not booleans")
    try:
        bbox = StudyBounds(*(float(value) for value in bounds))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("bbox coordinates must be finite numbers in longitude/latitude range and order") from exc
    name = str(candidate.get("name") or "").strip() or "Unnamed study area"
    signals = _independent_signals(candidate)
    open_context, nrhp = _context_records(store, bbox)
    explicit_archaeology = [r for r in nrhp if any(term in _text(r) for term in ARCHAEOLOGY_TERMS)]
    historical_context = open_context + explicit_archaeology
    permission = str(candidate.get("permission_status") or "unknown").strip().lower()
    permission = permission if permission in {"unknown", "pending", "confirmed"} else "unknown"

    # This is an ordinal planning index, deliberately unavailable when the
    # observations are not independent. It is never a discovery probability.
    priority_index = None
    signal_kinds = {item["kind"] for item in signals}
    if len(signals) >= 2 and "prior_survey" in signal_kinds:
        priority_index = round(
            100 * (sum(item["strength"] for item in signals) / len(signals))
            * min(len(signals) / 3, 1), 1,
        )

    if "prior_survey" not in signal_kinds:
        next_step = "Obtain documented prior survey coverage, including negative results, then add an independent landscape or archival observation."
    elif len(signals) < 2:
        next_step = "Add an independently sourced landscape or archival observation to the prior survey record."
    elif permission != "confirmed":
        next_step = (
            "Have a qualified archaeologist verify the supplied observations and their independence; "
            "then ask the relevant land manager and descendant communities to review a non-invasive survey proposal."
        )
    else:
        next_step = (
            "Have a qualified archaeologist verify the supplied observations, their independence, "
            "and the claimed permission scope; then design a non-invasive survey for review."
        )

    geocodes = Counter(str(r.get("geocode_method") or "unknown") for r in nrhp)
    hints = _find_hints(historical_context)
    return {
        "name": name,
        "bbox": list(bounds),
        "target_period": str(candidate.get("target_period") or "unspecified"),
        "period_evidence_status": "not filtered to target period; bundled period labels are largely absent",
        "priority_index": priority_index,
        "priority_meaning": (
            "uncalibrated index from user-supplied strengths; sources and independence "
            "are unverified; not a discovery probability"
        ),
        "signal_review_status": "user-supplied metadata; sources and independence have not been verified by Clovis",
        "fieldwork_status": "review only; no excavation recommendation",
        "next_step": next_step,
        "permission_status": permission,
        "independent_signals": signals,
        "documented_context": {
            "open_context_site_records": len(open_context),
            "nrhp_site_records_mixed": len(nrhp),
            "nrhp_explicit_archaeology_records": len(explicit_archaeology),
            "nrhp_geocode_methods": dict(geocodes),
            "note": "Existing records are not undiscovered sites. Geocode match quality does not establish site coordinate precision or survey coverage.",
        },
        "possible_find_classes": hints,
        "finds_note": (
            "Hints describe documented records without target-period matching, not a prediction of a new find."
            if hints else "No defensible find class can be inferred from these records; target-period matching is unavailable."
        ),
        "data_gaps": [
            "Bundled hydrology, geology, land status, LiDAR, and survey effort are not usable as spatial evidence here.",
            "Bundled archaeological period labels are largely absent.",
            "Land access, permits, and community consultation require project-specific verification.",
        ],
    }


def rank_candidates(candidates: list[dict], project_root: Path | None = None) -> list[dict]:
    """Rank only evidence-supported candidates; leave others explicitly unranked."""
    store = PlanDataStore(project_root)
    if not all(isinstance(candidate, dict) for candidate in candidates):
        raise ValueError("each candidate must be an object")
    assessed = [assess_candidate(candidate, store) for candidate in candidates]
    assessed.sort(key=lambda row: (row["priority_index"] is None, -(row["priority_index"] or 0), row["name"]))
    rank = 0
    previous_index = None
    for position, row in enumerate(assessed, start=1):
        if row["priority_index"] is not None:
            if row["priority_index"] != previous_index:
                rank = position
                previous_index = row["priority_index"]
            row["research_rank"] = rank
        else:
            row["research_rank"] = None
    return assessed
