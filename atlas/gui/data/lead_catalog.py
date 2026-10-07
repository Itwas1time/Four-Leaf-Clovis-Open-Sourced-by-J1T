"""Transparent filtering for the public fieldwork opportunity catalogue.

Evidence levels describe what a source reports about previous fieldwork. They
are not probabilities, scores of archaeological importance, or expected returns.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

from atlas.gui.data.fieldwork_leads import FIELDWORK_LEADS
from atlas.gui.data.jurisdiction_rules import JURISDICTION_RULES
from atlas.gui.data.lead_context import LEAD_CONTEXT

REGIONS = ("North America", "Central & South America", "Europe", "West Asia")
PERIODS = ("Prehistory", "Ancient world", "Multiple periods")
GOALS = {
    "evidence": "Strongest prior evidence",
    "exploratory": "More exploratory research",
    "support": "Published support route",
}
CHECKED_ON = date(2026, 10, 5)


def _validate_catalogue() -> None:
    required = {
        "id", "name", "region", "region_group", "season", "season_end", "period",
        "period_group", "evidence_level", "evidence_label", "novelty_level",
        "support_route", "support_note", "center", "zoom", "evidence", "planned",
        "finding", "why", "next_step", "open_question", "source_url", "listing_url",
    }
    seen: set[str] = set()
    for lead in FIELDWORK_LEADS:
        missing = required - lead.keys()
        if missing:
            raise ValueError(f"{lead.get('id', 'unnamed lead')} lacks {sorted(missing)}")
        if lead["id"] in seen:
            raise ValueError(f"duplicate lead id: {lead['id']}")
        seen.add(lead["id"])
        if lead["region_group"] not in REGIONS or lead["period_group"] not in PERIODS:
            raise ValueError(f"invalid filter category for {lead['id']}")
        if lead["evidence_level"] not in (1, 2, 3) or lead["novelty_level"] not in (1, 2, 3):
            raise ValueError(f"invalid evidence category for {lead['id']}")
        if lead["support_route"] not in ("published", "inquiry"):
            raise ValueError(f"invalid support route for {lead['id']}")
        if lead["support_route"] == "published" and not lead.get("support_url"):
            raise ValueError(f"missing support URL for {lead['id']}")
        if len(lead["center"]) != 2 or not -90 <= lead["center"][0] <= 90 or not -180 <= lead["center"][1] <= 180:
            raise ValueError(f"invalid regional center for {lead['id']}")
        date.fromisoformat(lead["season_end"])
        for key in ("source_url", "listing_url", "support_url"):
            if lead.get(key) and urlparse(lead[key]).scheme != "https":
                raise ValueError(f"invalid {key} for {lead['id']}")
        context = LEAD_CONTEXT.get(lead["id"])
        if not context:
            raise ValueError(f"missing site and partner context for {lead['id']}")
        if not all(context.get(key) for key in ("site_area", "site_note", "first_contact", "institutions")):
            raise ValueError(f"incomplete site and partner context for {lead['id']}")
        if context.get("jurisdiction_key") not in JURISDICTION_RULES:
            raise ValueError(f"missing jurisdiction rule for {lead['id']}")
        for institution in context["institutions"]:
            if not all(institution.get(key) for key in ("name", "relationship", "source_url")):
                raise ValueError(f"incomplete institution for {lead['id']}")
            if urlparse(institution["source_url"]).scheme != "https":
                raise ValueError(f"invalid institution URL for {lead['id']}")
            if institution.get("institution_url") and urlparse(institution["institution_url"]).scheme != "https":
                raise ValueError(f"invalid institution website URL for {lead['id']}")
    if seen != set(LEAD_CONTEXT):
        raise ValueError("site and partner context must match fieldwork leads")
    for key, rule in JURISDICTION_RULES.items():
        if not all(rule.get(field) for field in ("jurisdiction", "authority", "rule", "verify", "source_url")):
            raise ValueError(f"incomplete jurisdiction rule: {key}")
        for field in ("source_url", "additional_url"):
            if rule.get(field) and urlparse(rule[field]).scheme != "https":
                raise ValueError(f"invalid jurisdiction URL: {key}")


_validate_catalogue()


def matching_leads(
    goal: str = "evidence",
    region: str = "all",
    period: str = "all",
    support: str = "all",
    query: str = "",
    today: date | None = None,
) -> list[dict]:
    """Select current opportunities and order them by an explicit user goal."""
    today = today or date.today()
    needle = query.strip().casefold()
    rows = []
    for lead in FIELDWORK_LEADS:
        if date.fromisoformat(lead["season_end"]) < today:
            continue
        if region != "all" and lead["region_group"] != region:
            continue
        if period != "all" and lead["period_group"] != period:
            continue
        if support == "published" and lead["support_route"] != "published":
            continue
        haystack = " ".join(str(lead[key]) for key in (
            "name", "region", "period", "evidence", "planned", "finding"
        ))
        context = LEAD_CONTEXT[lead["id"]]
        haystack += " " + " ".join((context["site_area"], context["site_note"], context["first_contact"]))
        haystack += " " + " ".join(institution["name"] for institution in context["institutions"])
        haystack = haystack.casefold()
        if needle and needle not in haystack:
            continue
        rows.append(lead)

    if goal == "exploratory":
        rows.sort(key=lambda row: (-row["novelty_level"], -row["evidence_level"], row["name"]))
    elif goal == "support":
        rows.sort(key=lambda row: (row["support_route"] != "published", -row["evidence_level"], row["name"]))
    else:
        rows.sort(key=lambda row: (-row["evidence_level"], row["support_route"] != "published", row["name"]))
    return rows


def source_is_stale(today: date | None = None) -> bool:
    return ((today or date.today()) - CHECKED_ON).days > 90
