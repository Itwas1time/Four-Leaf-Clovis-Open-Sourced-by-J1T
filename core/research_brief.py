"""Reviewable, locally generated briefs for research follow-up.

These briefs organize public and user-drawn context. They do not identify dig
targets, validate permissions, or turn editorial ordering into probabilities.
"""

from __future__ import annotations

from datetime import date

from atlas.gui.data.fieldwork_leads import LEADS_BY_ID
from atlas.gui.data.jurisdiction_rules import JURISDICTION_RULES
from atlas.gui.data.lead_catalog import CHECKED_ON, source_is_stale
from atlas.gui.data.lead_context import LEAD_CONTEXT


def _plain(value: object, fallback: str = "Not recorded") -> str:
    """Keep user-entered labels and questions as plain Markdown text."""
    text = " ".join(str(value or "").split()).strip()
    for mark in ("\\", "`", "*", "_", "[", "]", "<", ">", "#", "|", "!"):
        text = text.replace(mark, "\\" + mark)
    return text[:500] or fallback


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _user_text(value: object, name: str, limit: int) -> str:
    """Enforce the form's input limits again at the export boundary."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text.")
    if len(value) > limit:
        raise ValueError(f"{name} must contain at most {limit} characters.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must contain valid Unicode text.") from exc
    return value


def _area_summary(analysis: object) -> dict:
    """Reject malformed client store data before producing a local brief."""
    if not isinstance(analysis, dict) or not isinstance(analysis.get("summary"), dict):
        raise ValueError("Draw an area and run Review Research Area before exporting a brief.")
    summary = analysis["summary"]
    counts = ("aoi_site_count", "buffer_site_count", "paleo_count", "tribal_count",
              "native_count", "independent_signal_count")
    def valid_count(value):
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1_000_000

    if any(not valid_count(summary.get(key)) for key in counts):
        raise ValueError("The area review contains invalid record counts; review the area again.")
    source_counts = summary.get("site_source_counts") or {}
    if (not isinstance(source_counts, dict) or len(source_counts) > 100
            or any(not isinstance(key, str) or len(key) > 100 or not valid_count(value)
                   for key, value in source_counts.items())):
        raise ValueError("The area review contains invalid source counts; review the area again.")
    geocode_missing = summary.get("geocode_method_missing_count")
    if (geocode_missing is not None and
            (not valid_count(geocode_missing) or geocode_missing > summary["aoi_site_count"] + summary["buffer_site_count"])):
        raise ValueError("The area review contains invalid location metadata; review the area again.")
    for key in ("data_gaps", "period_mix", "possible_find_classes"):
        items = summary.get(key)
        if items is not None and (not isinstance(items, list) or len(items) > 100
                or any(not isinstance(item, str) or len(item) > 2000 for item in items)):
            raise ValueError("The area review contains invalid context; review the area again.")
    for key in ("next_step", "legal_caution"):
        value = summary.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 2000):
            raise ValueError("The area review contains invalid guidance; review the area again.")
    return summary


def project_brief(lead_id: str, question: str = "", today: date | None = None) -> tuple[str, str]:
    """Return a title and Markdown brief for a published fieldwork lead."""
    lead = LEADS_BY_ID.get(lead_id) if isinstance(lead_id, str) else None
    if lead is None:
        raise ValueError("Choose a current fieldwork lead before exporting a brief.")
    question = _user_text(question, "Research question", 500)
    context = LEAD_CONTEXT[lead_id]
    rule = JURISDICTION_RULES[context["jurisdiction_key"]]
    prepared = today or date.today()
    title = lead["name"]
    checked = f"{CHECKED_ON.day} {CHECKED_ON:%B %Y}"
    season_ended = date.fromisoformat(lead["season_end"]) < prepared
    question_text = _plain(question, "Define a testable research question with the project team and relevant communities.")
    contacts = [
        f"{_plain(item['name'])} — {_plain(item['relationship'])}. "
        f"[Published role source]({item['source_url']})"
        for item in context["institutions"]
    ]
    support = (
        f"A [published contribution route]({lead['support_url']}) exists. "
        "Its terms, eligible costs, reporting, and any restrictions need a written agreement."
        if lead["support_route"] == "published"
        else "No project contribution route is documented here. A grant or sponsorship requires direct agreement with the directors. Participant fees are not an investment."
    )
    source_lines = [
        f"[Project page]({lead['source_url']}) — checked by Clovis {checked}; the page's publication date is not recorded here.",
        f"[Fieldwork listing]({lead['listing_url']}) — season and scope should be reconfirmed.",
        f"[Official heritage rule or guidance]({rule['source_url']}) — general jurisdiction source, not a project permit.",
    ]
    if rule.get("additional_url"):
        source_lines.append(f"[Additional authority source]({rule['additional_url']}) — confirm its current application to this work.")
    if source_is_stale(prepared):
        source_lines.append("Clovis's source check is over 90 days old. Recheck every linked project and authority page before acting.")
    lines = [
        f"# Clovis research brief: {_plain(title)}",
        "",
        f"Prepared {prepared.isoformat()} · Research follow-up only · Permission status unverified",
        "",
        "## Research question",
        question_text,
        "",
        "## Scope and location precision",
        f"Publicly named site or study area: {_plain(context['site_area'])}. Region: {_plain(lead['region'])}. Season advertised: {_plain(lead['season'])}.",
        "The advertised season has ended; current fieldwork and support availability are unknown." if season_ended else "The advertised season has not ended; its current plan still needs confirmation.",
        f"{_plain(context['site_note'])} The map center is regional context, not an excavation coordinate. No unit boundary or pinpoint location is exported.",
        "",
        "## What the sources say",
        _bullets([
            f"Prior evidence ({_plain(lead['evidence_label'])}): {_plain(lead['evidence'])}",
            f"Published plan: {_plain(lead['planned'])}",
            f"Research possibility, not a promised find: {_plain(lead['finding'])}",
        ]),
        "",
        "## Evidence gaps and decisions",
        _bullets([
            _plain(lead["open_question"]),
            "Obtain the 2027 research design, exact work area, earlier positive and negative survey coverage, and a defined budget.",
            "Ask the qualified team what observation would change the research case; record alternative explanations and negative results.",
        ]),
        "",
        "## People and support route",
        f"First conversation: {_plain(context['first_contact'])}",
        _bullets(contacts),
        support,
        "",
        "## Authority and access check",
        f"Jurisdiction: {_plain(rule['jurisdiction'])}. Competent authority starting point: {_plain(rule['authority'])}",
        f"General rule summary: {_plain(rule['rule'])}",
        f"Before fieldwork or funding: {_plain(rule['verify'])}",
        "Confirm the current project-specific permit, land access, required consultation, finds custody, curation, and publication terms with the competent people. The cited law or guidance does not verify a dig permission.",
        "",
        "## Source register and freshness",
        _bullets(source_lines),
        "",
        "## Interpretation limit",
        "This brief organizes public claims for human review. Public records and editorial lead ordering are not calibrated discovery probabilities, investable returns, or verified field permissions.",
        "",
    ]
    return title, "\n".join(lines)


def area_brief(analysis: dict, label: str = "", question: str = "", today: date | None = None) -> tuple[str, str]:
    """Return a broad, non-coordinate brief for the locally reviewed AOI."""
    summary = _area_summary(analysis)
    label = _user_text(label, "Public area label", 120)
    question = _user_text(question, "Research question", 500)
    prepared = today or date.today()
    title = _plain(label, "Drawn U.S. study area")
    question_text = _plain(question, "Define a testable question with a qualified archaeologist and relevant communities.")
    counts = [
        f"{summary['aoi_site_count']} indexed archaeological record(s) intersect the drawn area; {summary['buffer_site_count']} fall in the review buffer.",
        f"{summary['paleo_count']} fossil or paleo-context record(s), {summary['tribal_count']} tribal-boundary record(s), and {summary['native_count']} Native territory record(s) intersect the area or buffer. These layers have different meanings and may overlap.",
        f"Independent discovery signals available to this analysis: {summary['independent_signal_count']}. Existing sites, fossils, and territory polygons do not count as independent signals.",
    ]
    gaps = [_plain(item) for item in summary.get("data_gaps") or []]
    if not gaps:
        gaps = ["Prior survey effort, including negative coverage, is not established by this index."]
    source_counts = summary.get("site_source_counts") or {}
    source_lines = []
    if source_counts.get("open_context"):
        source_lines.append(
            f"{source_counts['open_context']} bundled Open Context site record(s) — "
            "[Open Context](https://opencontext.org/). Record-level extraction date is not established here."
        )
    if source_counts.get("nrhp"):
        source_lines.append(
            f"{source_counts['nrhp']} bundled U.S. National Register extract record(s) — "
            "[NPS data downloads](https://www.nps.gov/subjects/nationalregister/data-downloads.htm). "
            "Local geocodes and coverage are incomplete; extraction date is not established here."
        )
    for key, count in source_counts.items():
        if key not in {"open_context", "nrhp"}:
            source_lines.append(f"{count} local {_plain(key)} record(s); source date and record-level link not established here.")
    if not source_lines:
        source_lines.append("No indexed archaeological site record source was returned for this review. This is not a negative survey.")
    if summary.get("paleo_count"):
        source_lines.append("Paleo context comes from a bundled local fossil file; source dates and record-level links are not established here.")
    if summary.get("tribal_count") or summary.get("native_count"):
        source_lines.append("Tribal-boundary and Native territory context comes from bundled local files. These overlays do not establish current jurisdiction or consultation contacts; source dates are not established here.")
    source_lines.append("All bundled source dates require verification before a field decision.")
    site_total = summary["aoi_site_count"] + summary["buffer_site_count"]
    geocode_missing = summary.get("geocode_method_missing_count")
    if geocode_missing is None:
        precision_note = "Geocode methods have not been audited for these records. "
    elif site_total == 0:
        precision_note = "No indexed site locations were returned for this area. "
    else:
        precision_note = (
            f"Geocode method metadata is present for {site_total - geocode_missing} of {site_total} indexed site record(s); "
            "the physical accuracy of those locations is unverified. "
        )
    lines = [
        f"# Clovis research brief: {title}",
        "",
        f"Prepared {prepared.isoformat()} · Local U.S. area review · Permission status unverified",
        "",
        "## Research question",
        question_text,
        "",
        "## Scope and location precision",
        "This is a user-drawn study area reviewed against bundled local records. Its boundary and site coordinates are omitted from this export. "
        + precision_note + "A match confidence score does not establish physical location accuracy; this brief cannot define an excavation location.",
        "",
        "## Documented context",
        _bullets(counts),
        f"Periods stated in nearby records: {_plain(', '.join(summary.get('period_mix') or []), 'Not established')}.",
        f"Record-text find-class context: {_plain(', '.join(summary.get('possible_find_classes') or []), 'Unknown')}. This describes existing records, not an unexamined area.",
        "",
        "## Evidence gaps and next review",
        _bullets(gaps),
        f"Suggested research follow-up: {_plain(summary.get('next_step'))}",
        "Obtain prior positive and negative survey reports, source metadata, and independent observations before comparing this area with alternatives.",
        "",
        "## People, authority, and access",
        "A qualified archaeologist and relevant descendant or host communities must frame the question. Identify the landowner or land manager, current heritage authority, consultation requirements, and a capable institutional partner for this specific area.",
        f"Local caution: {_plain(summary.get('legal_caution'))}",
        "No land status, consultation outcome, or field permission is verified by the local map review.",
        "",
        "## Source register and freshness",
        _bullets(source_lines),
        "",
        "## Interpretation limit",
        "A blank map is not a negative survey. Counts and user-entered observations are not calibrated discovery probabilities or authorization to survey or excavate. Do not circulate sensitive site coordinates.",
        "",
    ]
    return title, "\n".join(lines)
