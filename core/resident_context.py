"""Town-scale find context with provenance and explicit unknown likelihood.

No site-density score, geological age or map overlap is converted into odds.
Reports contain public town names and fixed context choices, never addresses.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from time import monotonic
import secrets
import re
from urllib.parse import urlencode

from core.regional_geology import API, geology_for_place
from core.fossil_guides import GUIDES, matching_guides
from core.us_places import SOURCE, STATE_NAMES, get_place
from core.state_context import state_context

CONTEXTS = {
    "unknown": "I do not know the land-use history",
    "home": "An older home or building stood here",
    "farm": "It was used as a farm or garden",
    "fill": "Soil was imported or the ground was reworked",
}
ARTIFACT_SOURCE = "https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm"
FOSSIL_SOURCE = "https://www.nps.gov/subjects/fossils/what-is-a-fossil.htm"
GEOLOGY_SOURCE = "https://dev.macrostrat.org/docs/data-services"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ROCK_WORDS_SOURCE = "https://water.usgs.gov/water-basics_glossary.html"
_REPORTS = OrderedDict()
_REPORT_LOCK = Lock()


def _md(value):
    """Escape provider text as prose; HTML and provider-controlled links disabled."""
    text = str(value).replace("\n", " ").replace("\r", " ")
    for char in "\\`*_{}[]<>()!#|":
        text = text.replace(char, "\\" + char)
    return text


def input_key(state, geoid, context, online):
    if not isinstance(state, str) or not get_place(geoid, state):
        raise ValueError("Choose a state and a matching town from the list.")
    if not isinstance(context, str) or context not in CONTEXTS:
        raise ValueError("Choose a supported land-use history.")
    if not isinstance(online, list) or online not in ([], ["geology"]):
        raise ValueError("Choose whether to request regional geology.")
    return state, geoid, context, bool(online)


def _history(context):
    if context == "home":
        return ("Conditional possibilities: fragments of bottle or window glass, ceramics, nails and other building hardware. "
                "These examples fit occupation or building debris if the reported building history is correct. "
                "No object, date or archaeological site has been documented here by Clovis.")
    if context == "farm":
        return ("Conditional possibilities: discarded household glass or ceramics, nails and metal hardware associated with "
                "buildings or land use. Farming alone does not establish an artifact deposit. "
                "Clovis has not verified this history or documented objects here.")
    if context == "fill":
        return ("Imported fill may contain transported glass, ceramics, brick or rock fragments. "
                "Their original location and age cannot be inferred from the present yard. "
                "An object in fill would not by itself establish an undisturbed local site.")
    return ("Recognition examples to investigate include glass, ceramics and metal hardware. "
            "No historical find type is documented for this property; these examples are not evidence that objects occur here. "
            "Start with dated maps, building records or a local archive to establish past use.")


def _map_words(units):
    """Explain selected map wording; do not infer specimens or occurrences."""
    text = ' '.join(unit['name'] + ' ' + unit['lithology'] for unit in units).casefold()
    definitions = []
    if 'alluv' in text:
        definitions.append("**Alluvium:** loose sand, gravel, silt or clay deposited by flowing water.")
    if 'sedimentary' in text:
        definitions.append("**Sedimentary rock:** material accumulated in layers and hardened into rock.")
    if 'limestone' in text:
        definitions.append("**Limestone:** sedimentary rock made mostly of calcium carbonate.")
    if 'shale' in text:
        definitions.append("**Shale:** fine-grained rock formed from hardened clay, silt or mud.")
    if 'unconsolidated' in text:
        definitions.append("**Unconsolidated:** loose material that has not hardened into solid rock.")
    for word,definition,source in (
        ('granite','a coarse-grained rock formed as molten rock cooled below the surface.','https://www.usgs.gov/faqs/what-are-igneous-rocks'),
        ('basalt','a volcanic rock formed from cooled lava.','https://www.usgs.gov/faqs/what-are-igneous-rocks'),
        ('arkose','sandstone rich in the mineral feldspar.','https://apps.usgs.gov/thesaurus/term-simple.php?code=2.1.3.2&thcode=4'),
        ('gneiss','a metamorphic rock with alternating mineral bands.','https://apps.usgs.gov/thesaurus/term-simple.php?code=5.7&thcode=4'),
        ('dolostone','rock made mostly of the mineral dolomite; some maps call the rock dolomite.','https://pubs.usgs.gov/sir/2017/5118/elements/Dolomite/Dlmt_txt.html'),
    ):
        if word in text or (word=='dolostone' and 'dolomite' in text):
            definitions.append(f"**{word.capitalize()}:** {definition} [USGS explanation]({source})")
    if not definitions:
        return []
    return ["### Map words in plain English", "", *['- ' + item for item in definitions], "",
            f"[USGS glossary]({ROCK_WORDS_SOURCE}). These definitions explain map wording; "
            "they do not identify a specimen or establish what is present in a yard.", ""]


def _next_steps(place, context):
    """Fixed official destinations built only from the validated public catalogue."""
    town = re.sub(r" (?:city|town|village|borough|municipio|CDP)(?: \(balance\))?$", "", place['name'])
    historical = "https://www.loc.gov/collections/sanborn-maps/?" + urlencode({
        'q': town + ' ' + STATE_NAMES[place['state']]})
    geology = "https://ngmdb.usgs.gov/mapview/?" + urlencode({
        'center': f"{place['longitude']:.6f},{place['latitude']:.6f}", 'zoom': 9})
    history_action = {
        'home': 'Look for the reported building on a dated sheet; record the year and sheet number.',
        'farm': 'Check whether a dated map covers the farm area; rural coverage may be missing. Ask a local archive about land-use records.',
        'fill': 'Ask when soil or gravel was brought in and where it came from. A local map cannot establish the origin of fill.',
        'unknown': 'Use the index to find familiar streets and buildings; record the year and sheet number.',
    }[context]
    return [
        "## Try one small investigation", "",
        f"1. **Past buildings:** [Search Sanborn maps for {_md(town)}]({historical}). {history_action} "
        "Matching coverage has not been checked; try a local archive if missing or unavailable.", "",
        f"2. **Rocks and fossils:** [Open USGS geological maps around this town]({geology}). "
        "Compare its legend, date and scale with these unit names. "
        "Coverage varies; mapped rock does not confirm an exposure or a fossil.", "",
        "3. **Something already exposed?** Photograph it with a ruler; note its material and whether it was in fill or attached to rock. "
        "Ask a survey or museum about identification; survey links are in the full notes. "
        "Clovis cannot identify a specimen. No digging is needed to start.", "",
    ]


def build_context(state, geoid, context="unknown", online=None):
    key = input_key(state, geoid, context, [] if online is None else online)
    place = get_place(geoid, state)
    geology = geology_for_place(place) if key[3] else {
        "status": "not_requested", "units": [], "checked_at": "",
        "message": "Online geology was not requested. Historical context still works offline."}
    units = geology["units"]
    guides = matching_guides(state, units)
    lines = [f"# What might be here? — {_md(place['name'])}, {state}", "",
             "**Scale: town context, not a property assessment.** The map lookup uses the Census representative point "
             "for this place. It may describe a different deposit from your yard. No street address is collected.", "",
             "## At a glance", "",
             ("**Town-point rock maps:** " + "; ".join(_md(unit['name']) for unit in units[:4]) + ". "
              "Read the mapped materials and original references below." if units else geology['message']), "",
             "**Historical clues:** " + {
                 'unknown': "past land use is unknown; dated records are the next step.",
                 'home': "your reported older building suggests glass, ceramics and hardware as recognition examples.",
                 'farm': "your reported farm or garden history gives a starting point for land-use research.",
                 'fill': "imported fill can contain transported objects; their original place and age remain unknown.",
             }[context] + " "
             "**Discovery odds:** not currently estimable.", ""]
    if guides:
        lines += ["**Fossil learning examples:** " + "; ".join(
            f"{guide['name']} — {guide['examples']}" for guide in guides) + ". "
            "These published records are a comparison starting point if the mapped unit is actually present and exposed; "
            "they do not establish a find here. Sources are in the full field notes.", ""]
    if units:
        lines += ["## What the maps describe", "",
                  "These are overlapping map descriptions at the public town point. Compare the material with an actual exposure or object.", ""]
        for unit in units[:3]:
            lines += [f"**{_md(unit['name'])}**", "",
                      f"- Material: {_md(unit['lithology']) or 'Not specified'}.",
                      f"- Map interval: {_md(unit['interval']) or 'Not specified'}."]
            if unit['description']:
                excerpt = unit['description']
                if len(excerpt) > 400:
                    excerpt = excerpt[:400].rsplit(' ', 1)[0] + '…'
                lines += [f"- Original description excerpt: {_md(excerpt)}"]
            lines += [f"- Map unit {unit['map_id']}, source {unit['source_id']}; original reference in full notes.", ""]
        if len(units) > 3:
            lines += [f"Showing 3 of {len(units)} returned map units. All units and references are in the full field notes.", ""]
        lines += _map_words(units)
    lines += _next_steps(place, context)
    summary = f"**{_md(place['name'])}, {state} · Town context.** Maps use the public Census town point, not a yard assessment.\n\n" + "\n".join(lines[4:])
    lines += ["## Historical objects", "",
             f"Your land-use selection: **{_md(CONTEXTS[context])}**. This is user-reported and unverified.", "",
             _history(context), "",
             f"[NPS artifact recognition examples]({ARTIFACT_SOURCE}) are drawn from a park guide. "
             "Its park collection rules do not determine the rules for your property.", "",
             "## Rocks and geological materials", ""]
    if units:
        lines += [f"Macrostrat returned **{len(units)} overlapping map units** at the public town point. "
                  "These are maps at different scales, not a vertical sequence, separate discoveries or independent "
                  "confirmations. Their mapped materials are regional possibilities, not a yard soil profile.", ""]
        lines += ["Map labels are reproduced as returned by the provider. If a label seems inconsistent with this town, "
                  "check the original map and its legend before using it. A successful lookup does not verify a map's local accuracy.", ""]
        lines += _map_words(units)
        for unit in units:
            lines += [f"### {_md(unit['name'])}", "",
                      f"- Mapped material: {_md(unit['lithology']) or 'Not specified'}.",
                      f"- Geologic interval: {_md(unit['interval']) or 'Not specified'}.",
                      f"- Map unit ID {unit['map_id']}; source ID {unit['source_id']}."]
            if unit["description"]:
                lines += [f"- Source description excerpt: {_md(unit['description'])}"]
            if unit.get("comments"):
                lines += [f"- Original map notes excerpt: {_md(unit['comments'])}"]
            lines += [""]
    else:
        lines += [geology["message"], "", "No mapped material is inferred when the provider is disabled, unavailable "
                  "or has no coverage. Soil, gravel, landscaping stone and imported fill require local observations.", ""]
    lines += ["## Fossils", ""]
    for guide in guides:
        lines += [f"**Formation-specific examples — {guide['name']}:** Published formation records include "
                  f"{guide['examples']}. These are conditional possibilities if that formation is actually present "
                  "and exposed on a property; they are not confirmed yard finds or a forecast of frequency. "
                  f"[{guide['source_name']}]({guide['source']})", ""]
        if guide.get('scope_source'):
            lines += [f"[USGS stratigraphic scope and bed variation]({guide['scope_source']})", ""]
    if not guides:
        lines += ["No reviewed formation-specific fossil guide matched the returned map names. "
                  f"The current guide covers {len(GUIDES)} reviewed named units in selected states; "
                  "an unmatched formation is a coverage gap, not evidence that it has no fossils.", ""]
    mentions = [unit for unit in units if "fossil" in unit["description"].casefold()]
    if mentions:
        lines += ["A returned map description mentions fossils. Read its exact wording and original reference above; "
                  "it may describe fossil-bearing rock, an absence, or a regional observation. "
                  "Clovis has not confirmed a fossil occurrence at the town point or on your property.", ""]
    elif units:
        lines += ["The returned descriptions provide no explicit fossil occurrence for this town point. "
                  "That does not establish that fossils are absent.", ""]
    else:
        lines += ["There is no local geological evidence here to narrow fossil types.", ""]
    lines += ["General recognition examples include preserved shells, bones, wood, impressions and traces in rock "
              "or sediment. Their presence depends on the formation and preservation conditions; rock age alone "
              "does not predict a taxon or a find. A patterned rock or mineral coating may resemble a fossil.", "",
              f"[NPS fossil identification background]({FOSSIL_SOURCE})", "",
              "## Statewide learning context", "", state_context(state), "",
              "## How likely is a find?", "",
              "**Likelihood cannot be estimated from the available evidence.** No validated, comparable survey with "
              "both finds and no-find outcomes, sampling method, searched area and depth is connected to this town. "
              "A record nearby or a suitable rock type does not give the chance of finding an object in a backyard. "
              "Unknown does not mean zero.", "",
              "## What would improve this answer?", "",
              "- A dated property or neighborhood land-use record, checked with a local archive.",
              "  [Library of Congress Sanborn maps](https://www.loc.gov/collections/sanborn-maps/about-this-collection/) "
              "can help investigate older buildings where coverage exists; Clovis has not checked a property against them.",
              "- A local geological map and a qualified description of the actual soil, bedrock or imported fill.",
              "- A representative survey recording searched area, depth and methods, with all positive and negative "
              "outcomes. Even an observed survey frequency needs validation before predicting a new property.",
              "- Permission and applicable local/state rules; this report does not verify collection rights.", "",
              "## If you encounter something", "",
              "Before ground disturbance, use [811 utility marking](https://www.transportation.gov/content/call-811-you-dig-1). "
              "Photograph an exposed find with its context and ask a local museum, archaeologist or geological survey "
              "for identification. Avoid publishing precise sensitive locations. If you suspect human remains, "
              "stop disturbing the area and contact local authorities.", "",
              "## Sources and privacy", "",
              f"- U.S. Census Bureau, 2026 Places Gazetteer: [place names and representative points]({SOURCE}). "
              "The lookup is a public place catalogue, not archaeology or household data.",
              f"- [Macrostrat data services]({GEOLOGY_SOURCE}); [CC BY 4.0]({LICENSE}). "
              f"Provider status: **{geology['status']}**. Checked: {geology['checked_at'] or 'not requested'}."]
    if units:
        lines += [f"- [Geology query for this public town point]({API}?lat={place['latitude']:.6f}&lng={place['longitude']:.6f}). "
                  "Descriptions are excerpts; Clovis's interpretations are separate from the original map data."]
        references = {unit["source_id"]: unit["reference"] for unit in units}
        lines += [f"- Original map source {source_id}: {_md(reference)}" for source_id, reference in references.items()]
    lines += ["", "The online option sends only the bundled public town point to Macrostrat, which receives standard "
              "network metadata. Reports can be downloaded for up to an hour. Reports and provider responses are "
              "held in bounded server memory caches; restarting clears them. Clovis writes neither to disk. Downloads remain on your computer. "
              "Map tiles and styles use their own external providers. No personal address or private site record is "
              "required for this workflow.", ""]
    return {"key": key, "markdown": "\n".join(lines), "summary": summary, "geology_status": geology["status"],
            "unit_count": len(units), "mapped_units": [unit['name'] for unit in units], "place": place}


def remember_report(report):
    token = secrets.token_urlsafe(24)
    with _REPORT_LOCK:
        _REPORTS[token] = (monotonic(), report)
        while len(_REPORTS) > 128:
            _REPORTS.popitem(last=False)
    return token


def current_report(token, state, geoid, context, online):
    if not isinstance(token, str) or len(token) > 64:
        return None
    try:
        key = input_key(state, geoid, context, online)
    except ValueError:
        return None
    with _REPORT_LOCK:
        cached = _REPORTS.get(token)
        if cached is None:
            return None
        if monotonic() - cached[0] > 3_600:
            del _REPORTS[token]
            return None
        return cached[1] if cached[1]["key"] == key else None
