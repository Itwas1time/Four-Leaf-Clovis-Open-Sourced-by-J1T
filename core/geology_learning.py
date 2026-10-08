"""Small, sourced vocabulary for reading geological map descriptions.

Matches mean that a word appears in provider wording. They do not identify a
specimen, affirm a material's presence, interpret a negation, or date a find.
This module makes no requests and has no dependence on map coverage.
"""
from __future__ import annotations

from copy import deepcopy
import re

MAX_TEXT_LENGTH = 4096
MAX_QUERY_LENGTH = 120
MAX_SEARCH_RESULTS = 20

_WATER = "https://water.usgs.gov/water-basics_glossary.html"
_LITH = "https://apps.usgs.gov/thesaurus/thesaurus-full.php?thcode=4"
_SEDIMENT = "https://www.nps.gov/subjects/geology/sedimentary.htm"
_IGNEOUS = "https://www.nps.gov/subjects/geology/igneous.htm"
_METAMORPHIC = "https://www.nps.gov/subjects/geology/metamorphic.htm"
_METAMORPHIC_GUIDE = "https://www.nps.gov/romo/learn/education/upload/Geology-Teacher-Guide-for-web.pdf"
_PYROCLASTS = "https://www.nps.gov/subjects/volcanoes/pyroclasts.htm"
_TIME = "https://www.nps.gov/subjects/geology/time-scale.htm"
_USGS_TIME = "https://apps.usgs.gov/thesaurus/thesaurus-full.php"
_ICS = "https://stratigraphy.org/chart/"
_MAP = "https://www.usgs.gov/news/national-news-release/usgs-unveils-new-national-geologic-map"

PROVENANCE_CAVEAT = (
    "A map describes a geological unit across an area. It does not identify a "
    "loose specimen or establish where that specimen came from."
)
VOCABULARY_NOTICE = (
    "These are definitions of words appearing in the supplied text. Read the "
    "original wording for qualifiers such as 'no', 'possible', or 'minor'; "
    "a word match does not establish that a material occurs here."
)
AGE_CAVEAT = (
    "The age label belongs to the mapped unit. It does not date a loose "
    "specimen, an archaeological object, or a human activity."
)


def _material(identifier, name, aliases, meaning, question, sources, caveat=""):
    return {"id": identifier, "name": name, "kind": "material",
            "aliases": list(aliases), "what_it_means": meaning,
            "observation_question": question,
            "provenance_caveat": PROVENANCE_CAVEAT + (" " + caveat if caveat else ""),
            "source_urls": list(sources), "provenance_source_urls": [_MAP]}


_MATERIALS = (
    _material("sand", "Sand", ("sand", "sands", "sandy"),
              "Loose grains larger than silt and smaller than gravel; this is a size description, not a mineral name.",
              "Can you see separate grains in an existing loose deposit?", (_SEDIMENT,)),
    _material("gravel", "Gravel", ("gravel", "gravels", "gravelly"),
              "Loose rock fragments larger than sand, including pebbles and cobbles.",
              "Are the loose fragments rounded, angular, or a mixture?", (_USGS_TIME,)),
    _material("silt", "Silt", ("silt", "silts", "silty"),
              "Sediment with grains smaller than sand but larger than clay.",
              "Do you see fine sediment whose individual grains are hard to distinguish?", (_SEDIMENT,)),
    _material("clay", "Clay", ("clay", "clays", "clayey"),
              "Very fine sediment; clay also names a family of minerals, so the source's context matters.",
              "Are the grains in an existing exposure too small to distinguish by eye?", (_LITH,)),
    _material("alluvium", "Alluvium", ("alluvium", "alluvial"),
              "Loose sediment laid down by flowing water, which can include clay, silt, sand, and gravel.",
              "Can you see sediment layers or different grain sizes in an already exposed bank?", (_WATER,
                  "https://www.usgs.gov/publications/jasperoid-float-and-stream-cobbles-tools-geochemical-exploration-hydrothermal-ore"),
              "Water can move fragments away from the rock they originally came from."),
    _material("glacial_till", "Glacial till", ("glacial till", "till"),
              "A mixture of sediment sizes deposited directly by glacier ice, commonly with little sorting.",
              "Are large fragments mixed into much finer sediment in an existing exposure?", (_WATER,
                  "https://pubs.usgs.gov/of/2004/1216/text.html"),
              "Glacier transport can bring fragments from outside the local bedrock unit."),
    _material("loess", "Loess", ("loess",),
              "A wind deposited blanket of fine sediment, mainly silt.",
              "Is the exposed deposit mostly fine material rather than distinct pebbles?", (_WATER,
                  "https://www.usgs.gov/publications/eolian-sediments-0"),
              "Wind deposited sediment need not have the same origin as the bedrock underneath."),
    _material("shale", "Shale", ("shale", "shales"),
              "A sedimentary rock made of very fine particles, typically arranged in thin layers.",
              "Do existing broken surfaces show thin sheets or layers?", (_LITH,)),
    _material("siltstone", "Siltstone", ("siltstone", "siltstones"),
              "Sedimentary rock made mainly of silt sized particles; it lacks shale's characteristic thin splitting.",
              "Is the surface fine textured without visible sand grains or thin sheets?", (_LITH,)),
    _material("sandstone", "Sandstone", ("sandstone", "sandstones"),
              "Sedimentary rock in which sand sized grains have become joined into solid rock.",
              "Can you see grains held together on an existing surface?", (
                  "https://apps.usgs.gov/thesaurus/term-simple.php?code=2.1.3&thcode=4", _SEDIMENT)),
    _material("mudstone", "Mudstone", ("mudstone", "mudstones"),
              "A broad name for rock made from fine sediment when clay and silt proportions are not specified.",
              "Are the existing surfaces very fine textured, without visible sand grains?", (_LITH,)),
    _material("limestone", "Limestone", ("limestone", "limestones"),
              "Sedimentary rock made mainly of calcium carbonate, usually the mineral calcite. Some limestone forms from shells or other organisms.",
              "Are layers or shell shaped outlines visible on an existing surface?", (_LITH, _SEDIMENT),
              "The word 'limestone' alone does not show that a specimen contains fossils."),
    _material("dolostone", "Dolostone / dolomite", ("dolostone", "dolostones", "dolomite", "dolomites"),
              "Dolostone is sedimentary rock rich in the mineral dolomite. 'Dolomite' may mean that mineral or the rock in map wording.",
              "Are bedding or small crystals visible on an existing surface?", (
                  "https://apps.usgs.gov/thesaurus/term-simple.php?code=2.2.2&thcode=4",
                  "https://pubs.usgs.gov/sir/2017/5118/elements/Dolomite/Dlmt_txt.html"),
              "Appearance alone may not distinguish dolostone from limestone."),
    _material("conglomerate", "Conglomerate", ("conglomerate", "conglomerates"),
              "Sedimentary rock containing rounded to partly rounded gravel sized fragments joined in a finer material.",
              "Are larger rounded fragments embedded in a solid rock rather than lying loose?", (
                  "https://apps.usgs.gov/thesaurus/term-simple.php?code=2.1.5&thcode=4",)),
    _material("basalt", "Basalt", ("basalt", "basalts"),
              "A volcanic rock, typically dark with small crystals. Some basalt has holes left by gas bubbles.",
              "Is the surface fine textured, and are any rounded cavities visible?", (_IGNEOUS,)),
    _material("granite", "Granite", ("granite", "granites"),
              "Rock formed as magma cooled underground, mainly containing quartz and feldspar with crystals commonly visible.",
              "Can you see interlocking crystals of different colors?", (_IGNEOUS,)),
    _material("schist", "Schist", ("schist", "schists"),
              "Metamorphic rock with aligned minerals; visible flakes of mica are common.",
              "Do visible mineral flakes line up along surfaces?", (_METAMORPHIC, _METAMORPHIC_GUIDE)),
    _material("gneiss", "Gneiss", ("gneiss", "gneisses"),
              "Metamorphic rock with mineral bands, often showing alternating lighter and darker parts.",
              "Do different mineral colors form bands within the rock?", (_METAMORPHIC_GUIDE,)),
    _material("volcanic_ash", "Volcanic ash", ("volcanic ash",),
              "Tiny fragments of rock, mineral, or volcanic glass ejected in an eruption; volcanic ash is not burned wood ash.",
              "Is an existing exposure loose fine material or solid rock?", (_PYROCLASTS,)),
    _material("tuff", "Tuff", ("tuff", "tuffs", "ash-flow tuff", "ash flow tuff"),
              "Rock formed when volcanic fragments, mainly ash, become consolidated.",
              "Can you see fragments held together in a solid rock on an existing surface?", (_PYROCLASTS,)),
    _material("chert", "Chert", ("chert", "cherts"),
              "A silica rich rock containing quartz crystals too small to see individually.",
              "Are individual grains invisible on the existing surface?", (
                  "https://pubs.usgs.gov/of/2004/1098/",),
              "This term does not establish that a stone was shaped or used by people."),
    _material("quartzite", "Quartzite", ("quartzite", "quartzites"),
              "Metamorphic rock made mainly of quartz, often formed by recrystallizing sandstone.",
              "Do the visible grains form a joined crystalline mass on an existing surface?", (_LITH, _METAMORPHIC),
              "This term does not establish that a stone was shaped or used by people."),
    _material("sedimentary", "Sedimentary rocks", ("sedimentary rocks", "sedimentary rock", "sedimentary"),
              "A broad rock family formed from deposited sediment, accumulated organisms, or minerals precipitated from water; it is not one specific rock type.",
              "Are layers or joined sediment grains visible on an existing surface?", (_SEDIMENT,),
              "This broad label alone does not establish a particular rock type or fossil content."),
    _material("unconsolidated", "Unconsolidated", ("unconsolidated",),
              "Sediment that remains loose or loosely bound rather than joined into solid rock.",
              "Does an existing exposure show separate loose grains or fragments?", (_WATER,)),
    _material("mud", "Mud", ("mud", "muds"),
              "In geological sediment descriptions, a broad term for fine material containing silt and clay.",
              "Are the exposed grains too small to distinguish individually?", (
                  "https://pubs.usgs.gov/ds/2005/118/htmldocs/faqs.htm",),
              "The word does not specify the separate proportions of silt and clay."),
    _material("chalk", "Chalk", ("chalk",),
              "A soft, porous, very fine textured kind of limestone, often light colored.",
              "Is an existing surface fine textured, and are weathered crumbs already visible?", (
                  "https://www.kgs.ku.edu/Publications/Bulletins/ED2/03_rocks.html",),
              "The map word does not identify an individual white object or establish fossil content."),
    _material("igneous", "Igneous rocks", ("igneous rocks", "igneous rock", "igneous"),
              "A broad rock family formed when melted rock cools and becomes solid, underground or at the surface.",
              "Are crystals, a glassy surface, or rounded gas cavities visible?", (_IGNEOUS,),
              "This broad label does not specify granite, basalt, or another particular rock."),
    _material("metamorphic", "Metamorphic rocks", ("metamorphic rocks", "metamorphic rock", "metamorphic"),
              "A broad rock family changed from earlier rock by heat and pressure; visible mineral alignment occurs in some types.",
              "Are aligned mineral flakes or bands visible on an existing surface?", (_METAMORPHIC,),
              "This broad label alone does not establish a particular rock type."),
)


def _age(name, rank, parent, meaning, order=None, aliases=(), sources=(_TIME,)):
    return {"id": name.lower(), "name": name, "kind": "age",
            "aliases": [name.lower(), *aliases], "rank": rank, "parent": parent,
            "relative_order": order, "what_it_means": meaning,
            "observation_question": "Which age label and any qualifiers does the original map legend give?",
            "provenance_caveat": AGE_CAVEAT, "source_urls": list(sources),
            "provenance_source_urls": [_MAP]}


# relative_order is oldest-to-youngest ONLY within the same rank and parent.
# It is not a duration, date, confidence value, or cross-rank comparison.
_AGES = (
    _age("Precambrian", "broad interval", "", "A broad interval before the Cambrian; not a single period."),
    _age("Paleozoic", "era", "Phanerozoic", "The era before the Mesozoic.", 1),
    _age("Mesozoic", "era", "Phanerozoic", "The era between the Paleozoic and Cenozoic.", 2),
    _age("Cenozoic", "era", "Phanerozoic", "The era after the Mesozoic, including today.", 3),
    *(_age(name, "period", "Paleozoic", "A period within Paleozoic geologic time.", order)
      for order, name in enumerate(("Cambrian", "Ordovician", "Silurian", "Devonian", "Carboniferous", "Permian"), 1)),
    _age("Mississippian", "subperiod", "Carboniferous", "The older part of the Carboniferous.", 1,
         sources=(_USGS_TIME, _TIME)),
    _age("Pennsylvanian", "subperiod", "Carboniferous", "The younger part of the Carboniferous.", 2,
         sources=(_USGS_TIME, _TIME)),
    *(_age(name, "period", "Mesozoic", "A period within Mesozoic geologic time.", order)
      for order, name in enumerate(("Triassic", "Jurassic", "Cretaceous"), 1)),
    *(_age(name, "period", "Cenozoic", "A period within Cenozoic geologic time.", order)
      for order, name in enumerate(("Paleogene", "Neogene", "Quaternary"), 1)),
    _age("Tertiary", "older map label", "Cenozoic", "An older label spanning Paleogene and Neogene time."),
    *(_age(name, "epoch", "Paleogene", "An epoch within the Paleogene Period.", order)
      for order, name in enumerate(("Paleocene", "Eocene", "Oligocene"), 1)),
    *(_age(name, "epoch", "Neogene", "An epoch within the Neogene Period.", order)
      for order, name in enumerate(("Miocene", "Pliocene"), 1)),
    _age("Pleistocene", "epoch", "Quaternary", "The Quaternary epoch before the Holocene.", 1),
    _age("Holocene", "epoch", "Quaternary", "The current epoch, after the Pleistocene.", 2),
    _age("Burdigalian", "stage", "Miocene", "A named stage within the Miocene Epoch; a smaller subdivision than an epoch.",
         sources=(_ICS,)),
    _age("Lutetian", "stage", "Eocene", "A named stage within the Eocene Epoch; a smaller subdivision than an epoch.",
         sources=(_ICS,)),
)
_TERMS = _MATERIALS + _AGES


def _compile(terms):
    aliases = {alias: term for term in terms for alias in term["aliases"]}
    # Long phrases come first, preventing 'till' from also matching in 'glacial till'.
    phrases = sorted(aliases, key=lambda alias: (-len(alias), alias))
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(
        re.escape(alias).replace(r"\ ", r"\s+") for alias in phrases) + r")(?!\w)", re.IGNORECASE)
    return aliases, pattern


_MATERIAL_ALIASES, _MATERIAL_PATTERN = _compile(_MATERIALS)
_AGE_ALIASES, _AGE_PATTERN = _compile(_AGES)
_ALIASES = {alias: term for term in _TERMS for alias in term["aliases"]}
_ALIASES.update({term["id"]: term for term in _TERMS})


def _bounded_text(value, label, notices, limit=MAX_TEXT_LENGTH):
    if value is None:
        return ""
    if not isinstance(value, str):
        notices.append(f"{label} was not plain text and was not interpreted.")
        return ""
    if len(value) > limit:
        notices.append(f"{label} exceeded {limit} characters and was not interpreted.")
        # Reject, rather than cutting a word or silently omitting a later negation.
        return ""
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        notices.append(f"{label} contained invalid Unicode surrogates and was not interpreted.")
        return ""
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        notices.append(f"{label} contained control characters and was not interpreted.")
        return ""
    return value


def lookup_term(term):
    """Return a fresh term dictionary for an exact id/name/alias, or None."""
    text = _bounded_text(term, "Term", [], MAX_QUERY_LENGTH)
    key = " ".join(text.lower().split())
    found = _ALIASES.get(key)
    return deepcopy(found) if found is not None else None


def search_terms(query="", limit=8):
    """Search reviewed names/aliases; blank query browses the vocabulary.

    A query must be a literal name fragment, not regex or a natural-language
    claim. Bad limits and oversized/malformed queries return no results.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_SEARCH_RESULTS:
        return []
    notices = []
    text = _bounded_text(query, "Search query", notices, MAX_QUERY_LENGTH)
    if notices:
        return []
    key = " ".join(text.lower().split())
    results = [term for term in _TERMS if any(key in alias for alias in term["aliases"])]
    # Exact matches are most useful, then retain the stable vocabulary ordering.
    results.sort(key=lambda term: key not in term["aliases"])
    return deepcopy(results[:limit])


def _explain(text, aliases, pattern):
    terms, spans, seen = [], [], set()
    for match in pattern.finditer(text):
        term = aliases[" ".join(match.group().lower().split())]
        spans.append((match.start(), match.end()))
        if term["id"] not in seen:
            seen.add(term["id"])
            terms.append(deepcopy(term))
    # Keep every nonmatching span, including negations and qualifiers. No
    # sentence, formation name, quantity, age qualifier, or abbreviation inferred.
    unrecognized, start = [], 0
    for left, right in [*spans, (len(text), len(text))]:
        fragment = text[start:left].strip(" \t\r\n,;/")
        if fragment:
            unrecognized.append(fragment)
        start = right
    return terms, unrecognized


def explain_unit(material_text="", age_text=""):
    """Explain material and age vocabulary separately, retaining source wording.

    Pass a Macrostrat card's lithology/description as material_text and interval
    as age_text. Unknown wording is explicitly retained. Terms are in order of
    first mention, deduplicated. HTML is plain text, never rendered here: callers
    must use their normal text escaping when displaying all returned strings.
    """
    notices = [VOCABULARY_NOTICE, PROVENANCE_CAVEAT, AGE_CAVEAT]
    material = _bounded_text(material_text, "Material text", notices)
    age = _bounded_text(age_text, "Age text", notices)
    material_terms, unknown_material = _explain(material, _MATERIAL_ALIASES, _MATERIAL_PATTERN)
    age_terms, unknown_age = _explain(age, _AGE_ALIASES, _AGE_PATTERN)
    return {"raw_material": material, "raw_age": age,
            "material_terms": material_terms, "age_terms": age_terms,
            "unrecognized_material": unknown_material, "unrecognized_age": unknown_age,
            "notices": notices}
