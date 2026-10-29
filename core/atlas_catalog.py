"""One paged search and record reader over attributable local collections."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import re
import sqlite3
from threading import Lock
import unicodedata
from weakref import WeakValueDictionary

from core import archaeology_project_catalog as projects
from core import neolithic_catalog as assemblages
from core import radiocarbon_catalog as dates
from core import reference_catalog as objects
from core import fossil_reference_catalog as fossils
from core import dinosaur_catalog as dinosaurs
from core import mineral_property_catalog as minerals
from core import newspaper_catalog as newspapers
from core import usgs_unit_library as geology
from core import object_material_guides as guides
from core import excavation_catalog as contexts
from core import environment_catalog as environments
from core import zooarchaeology_catalog as specimens
from core import assemblage_catalog as field_assemblages
from core import site_register_catalog as site_registers
from core import pleiades_catalog as places
from core import ads_metadata_catalog as ads
from core import amcr_catalog as amcr
from core import dans_metadata_catalog as dans
from core import raa_fieldwork_catalog as raa
from core import france_fieldwork_catalog as france
from core import finland_register_catalog as finland
from core import publication_catalog as publications
from core import data_packs

PAGE_SIZE = 24
SOURCES = {
    "assemblages": "UCL · Neolithic assemblages", "projects": "Open Context · publications",
    "dates": "p3k14c · radiocarbon dates", "met": "Met · objects",
    "si": "Smithsonian · anthropology", "fossils": "Smithsonian · fossil specimens",
    "dinosaurs": "Paleobiology Database · fossil occurrences", "geology": "USGS · mapped geology",
    "minerals": "Wikidata · mineral properties", "newspapers": "Library of Congress · newspaper titles",
    "guides": "Material reference guides", "contexts": "Open Context · excavations & surveys",
    "environments": "Neotoma · sites, samples & environments",
    "specimens": "Open Context · Anatolian animal-bone records",
    "field_assemblages": "Excavation & survey assemblages",
    "site_registers": "DINAA · archaeological site registers",
    "places": "Pleiades · ancient places",
    "ads": "ADS · reports & archives",
    "amcr": "AMCR · native fieldwork & sites",
    "dans": "DANS · archaeology DOI metadata",
    "raa": "Sweden · RAÄ fieldwork assignments",
    "france": "France · regional archaeological operations",
    "finland": "Finland · Antiquities Record sites",
    "publications": "Full research papers & original tables",
}
KINDS = {"all": "All evidence", "archaeology": "Archaeology & objects", "fossils": "Fossils",
         "history": "Historical documents", "earth": "Geology & minerals"}
GROUPS = {"all": tuple(SOURCES), "archaeology": ("assemblages", "contexts", "environments", "specimens", "field_assemblages", "site_registers", "places", "projects", "dates", "met", "si", "guides", "ads", "amcr", "dans", "raa", "france", "finland", "publications"),
          "fossils": ("fossils", "dinosaurs"), "history": ("newspapers",), "earth": ("geology", "minerals")}
OPTIONAL = {"assemblages": assemblages, "dates": dates, "dinosaurs": dinosaurs, "contexts": contexts, "environments": environments, "specimens": specimens, "field_assemblages": field_assemblages, "site_registers": site_registers, "places": places}
OPTIONAL['ads'] = ads
OPTIONAL['amcr'] = amcr
OPTIONAL['dans'] = dans
OPTIONAL['raa'] = raa
OPTIONAL['france'] = france
OPTIONAL['finland'] = finland
_READERS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="clovis-atlas")
_VERIFIERS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="clovis-atlas-verification")
_FIRST_PAGE_LOCKS = WeakValueDictionary()
_FIRST_PAGE_LOCKS_GUARD = Lock()


def available_sources():
    # A private candidate is offered only when its trusted catalog is supplied.
    # Do not leave an unpublished source with no installation route in the UI.
    offered = {}
    for key, module in (('places', places), ('ads', ads), ('amcr', amcr), ('dans', dans), ('raa', raa), ('france', france), ('finland', finland)):
        try:
            offered[key] = module.advertised()
        except (ValueError, OSError):
            offered[key] = False
    return {key: label for key, label in SOURCES.items() if key not in offered or offered[key]}


def _signature(sources=None):
    """Verify optional data before using cached results, including after repair."""
    selected=[(name,module) for name,module in OPTIONAL.items() if sources is None or name in sources]
    def verify(item):
        name,module=item
        try:
            path = module.database()
            stat = path.stat() if path else None
            return (name, str(path) if path else "", stat.st_mtime_ns if stat else 0,
                    stat.st_ctime_ns if stat else 0, stat.st_size if stat else 0)
        except (ValueError, OSError, sqlite3.Error):
            return (name, "unavailable")
    # Full checksum verification remains mandatory. Independent collections can
    # wait on the bounded pack-file verifiers together, preserving source order.
    # A separate pool avoids nesting verification inside the catalog query pool.
    return tuple(_VERIFIERS.map(data_packs.in_request(verify),selected))


def _native(source, query, page, context=()):
    if source == 'publications':
        return publications.search(query=query,page=page,summary=True),publications.PAGE_SIZE
    if source == 'finland':
        parameters=dict(context)
        parameters.pop('collection',None)
        return finland.search(query=query,page=page,**parameters),finland.PAGE_SIZE
    if source == 'france':
        parameters=dict(context)
        parameters.pop('collection',None)
        return france.search(query=query,page=page,**parameters),france.PAGE_SIZE
    if source == 'raa':
        parameters=dict(context)
        parameters.pop('collection',None)
        return raa.search(query=query,page=page,**parameters),raa.PAGE_SIZE
    if source == 'dans':
        parameters = dict(context)
        parameters.pop('collection', None)
        return dans.search(query=query, page=page, **parameters), dans.PAGE_SIZE
    if source == 'amcr':
        parameters = dict(context)
        parameters.pop('collection', None)
        return amcr.search(query=query, page=page, **parameters), amcr.PAGE_SIZE
    if source == 'ads':
        parameters = dict(context)
        parameters.pop('collection', None)
        return ads.search(query=query, page=page, **parameters), ads.PAGE_SIZE
    if source == "places":
        parameters = dict(context)
        parameters.pop("collection", None)
        return places.search(query=query, page=page, **parameters), places.PAGE_SIZE
    if source == "site_registers":
        parameters = dict(context)
        parameters.pop("collection", None)
        return site_registers.search(query=query, page=page, **parameters), site_registers.PAGE_SIZE
    if source == "field_assemblages":
        parameters = dict(context)
        parameters.pop("collection", None)
        return field_assemblages.search(query=query, page=page, **parameters), field_assemblages.PAGE_SIZE
    if source == "specimens":
        parameters = dict(context)
        parameters.pop("collection", None)
        return specimens.search(query=query, page=page, **parameters), specimens.PAGE_SIZE
    if source == "environments":
        parameters = dict(context)
        parameters.pop("collection", None)
        return environments.search(query=query, page=page, **parameters), environments.PAGE_SIZE
    if source == "contexts":
        parameters = dict(context)
        parameters.pop("collection", None)
        return contexts.search(query=query, page=page, **parameters), contexts.PAGE_SIZE
    if source == "assemblages":
        return assemblages.search(query=query, page=page, **dict(context)), assemblages.PAGE_SIZE
    if source == "projects":
        rows, total, page = projects.search_projects(query=query, page=page)
        return {"rows": rows, "total": total, "page": page}, projects.PAGE_SIZE
    if source == "dates":
        return dates.search(query=query, page=page), dates.PAGE_SIZE
    if source in ("met", "si"):
        return objects.search_objects(collection=source, query=query, era="all", page=page), 24
    if source == "fossils":
        return fossils.search_fossils(query=query, page=page), fossils.PAGE_SIZE
    if source == "dinosaurs":
        parameters=dict(context)
        parameters.pop("collection",None)
        return dinosaurs.search(query=query, lineage="fossils", page=page, **parameters), dinosaurs.PAGE_SIZE
    if source == "geology":
        return geology.search_units(query=query, page=page), geology.PAGE_SIZE
    if source == "minerals":
        return minerals.search_minerals(query=query, page=page), minerals.PAGE_SIZE
    if source == "newspapers":
        return newspapers.search_titles(query=query, page=page), newspapers.PAGE_SIZE
    if source == "guides":
        return guides.search_guides(query=query, page=page), guides.PAGE_SIZE
    raise ValueError("Choose a source from the atlas.")


@lru_cache(maxsize=256)
def _cached_first_pages(query, sources, context, signature):
    def read(source):
        try:
            result, size = _page(source, query, 1, context, signature)
            if result.get("installed") is False:
                return None, (source, "Collection not installed")
            warnings=result.get('missing_editions',[])
            warning=(source,' '.join(warnings)) if warnings else None
            return (source, result, size), warning
        except (ValueError, OSError, sqlite3.Error):
            return None, (source, "Collection could not be read")
    available, missing = [], []
    for result, unavailable in _READERS.map(data_packs.in_request(read), sources):
        if result is not None:
            available.append(result)
        if unavailable is not None:
            missing.append(unavailable)
    return available, missing


def _first_pages(query, sources, context, signature):
    # Early preparation and a foreground query can arrive together. Reuse the
    # same verified result instead of computing every collection page twice.
    key=(query,sources,context,signature)
    with _FIRST_PAGE_LOCKS_GUARD:
        lock=_FIRST_PAGE_LOCKS.get(key)
        if lock is None:
            lock=Lock()
            _FIRST_PAGE_LOCKS[key]=lock
    with lock:
        return _cached_first_pages(query,sources,context,signature)


_first_pages.cache_clear = _cached_first_pages.cache_clear
_first_pages.cache_info = _cached_first_pages.cache_info


@lru_cache(maxsize=128)
def _page(source, query, page, context, signature):
    return _native(source, query, page, context)


def _positions(counts, offset, limit):
    """Seek a fair interleaving without dropping records at native page boundaries."""
    low, high = 0, max(counts, default=0)
    while low < high:
        middle = (low + high + 1) // 2
        if sum(min(count, middle) for count in counts) <= offset:
            low = middle
        else:
            high = middle - 1
    round_number = low
    skip = offset - sum(min(count, round_number) for count in counts)
    positions = []
    while len(positions) < limit and round_number < max(counts, default=0):
        for source, count in enumerate(counts):
            if count <= round_number:
                continue
            if skip:
                skip -= 1
            else:
                positions.append((source, round_number))
                if len(positions) == limit:
                    break
        round_number += 1
    return positions


def _card(source, row):
    title = row.get("title") or row.get("name") or row.get("accepted_name") or row.get("lab_id") or row["id"]
    if source=="dinosaurs" and "occurrence_no" in row:
        title=row.get("accepted_name") or row.get("identified_name") or "Occurrence "+row["occurrence_no"]
    evidence = {"projects": "Dataset publication", "met": "Museum object", "si": "Museum object",
                "fossils": "Fossil specimen", "dinosaurs": "Published fossil occurrence",
                "dates": "Radiocarbon determination", "geology": "Mapped geological unit",
                "minerals": "Mineral reference", "newspapers": "Newspaper title", "guides": "Material guide"}.get(source)
    if source in ("environments", "specimens", "field_assemblages", "site_registers", "places", "ads", "amcr", "dans", "raa", "france", "finland", "publications"):
        evidence, subtitle = row["category"], row["subtitle"]
    elif source == "contexts":
        evidence = row["category"]
        subtitle = " · ".join(value for value in (contexts.DATASETS[row["dataset"]], row.get("context_label")) if value)
    elif source == "assemblages":
        evidence = assemblages.VIEWS[row["view"]]
        subtitle = " · ".join(value for value in (row["subtitle"], row["country"]) if value)
    elif source == "dates":
        subtitle = f'{row["age_bp"]:,} ± {row["error_bp"]:,} uncalibrated BP'
        subtitle += " · " + " · ".join(value for value in (row["site_name"], row["country"], row["material"]) if value)
    elif source == "projects":
        subtitle = " · ".join(value for value in (row["country"], row["region"], "; ".join(row["periods"])) if value)
    else:
        subtitle = " · ".join(str(row[key]) for key in ("date", "material", "country", "state", "formation", "age", "formula", "publication_dates", "summary") if row.get(key))
    return {"id": source + "|" + str(row["id"]), "title": title, "subtitle": subtitle,
            "evidence": evidence, "source": source, "source_label": SOURCES[source]}


def _parameters(query, kind, source, context):
    if (not isinstance(query, str) or len(query) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in query)
            or kind not in KINDS or source not in ("all", *SOURCES)):
        raise ValueError("Search the atlas with up to 120 characters and a listed evidence type.")
    if context is None:
        context = {}
    if (not isinstance(context, dict)
            or any(not isinstance(value, str) or not value or len(value) > 120
                   or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value) for value in context.values())):
        raise ValueError("Choose a published evidence association.")
    collection = context.get("collection", "assemblages")
    if collection == 'finland':
        if set(context)-{'collection','site_class','dating','field'}:
            raise ValueError('Choose Finnish native register classes, dating and text fields.')
        finland.validate_parameters(**{key:value for key,value in context.items() if key!='collection'})
    elif collection == 'france':
        if set(context)-{'collection','method','field'}:
            raise ValueError('Choose French native operation categories and text fields.')
        france.validate_parameters(**{key:value for key,value in context.items() if key!='collection'})
    elif collection == 'raa':
        if set(context)-{'collection','method','status','ground','field'}:
            raise ValueError('Choose original Swedish assignment types, status and geometry coverage.')
        raa.validate_parameters(**{key:value for key,value in context.items() if key!='collection'})
    elif collection == 'dans':
        if set(context) - {'collection', 'subject', 'field', 'shared_legacy'}:
            raise ValueError('Choose an original DANS subject and metadata text field.')
        dans.validate_parameters(**{key: value for key, value in context.items() if key != 'collection'})
    elif collection == 'amcr':
        if set(context) - {'collection', 'scope', 'method', 'field'}:
            raise ValueError('Choose native AMCR record kind, method and text filters.')
        amcr.validate_parameters(**{key: value for key, value in context.items() if key != 'collection'})
    elif collection == 'ads':
        if set(context) - {'collection', 'resource_type', 'field'}:
            raise ValueError('Choose original ADS metadata type and text filters.')
        ads.validate_parameters(**{key: value for key, value in context.items() if key != 'collection'})
    elif collection == "dinosaurs":
        if set(context)-{"collection","country","state","collection_no"}:
            raise ValueError("Choose a published fossil location or collection.")
        dinosaurs.validate_location_filters(**{key:value for key,value in context.items() if key!="collection"})
    elif collection == "places":
        if set(context) - {"collection", "place_id", "scope", "record_id"}:
            raise ValueError("Choose an original ancient-place association.")
        places.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif collection == "site_registers":
        if set(context) - {"collection", "context_id", "edition", "state"}:
            raise ValueError("Choose an original site-register association.")
        site_registers.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif collection == "field_assemblages":
        if set(context) - {"collection", "view", "scope", "table_id", "dataset", "record_id"}:
            raise ValueError("Choose an original excavation assemblage association.")
        field_assemblages.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif collection == "specimens":
        if set(context) - {"collection", "view", "subject_id", "context_id", "table_sha", "project_id", "record_id"}:
            raise ValueError("Choose an original zooarchaeological subject or context association.")
        specimens.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif collection == "environments":
        if set(context) - {"collection", "view", "record_id", *environments.SCOPES}:
            raise ValueError("Choose an original Neotoma scientific association.")
        environments.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif collection == "contexts":
        if set(context) - {"collection", "dataset", "category", "scope", "record_id", "predicate"}:
            raise ValueError("Choose a published excavation or survey association.")
        contexts.validate_parameters(**{key: value for key, value in context.items() if key != "collection"})
    elif (collection != "assemblages" or set(context) - {"view", "phase_id", "site_id", "bone_id"}
          or context.get("view", "all") not in (*assemblages.VIEWS, "all")):
        raise ValueError("Choose a published evidence association.")
    # Association links are confined to their original source, never matched across datasets.
    offered = available_sources() if not context else {}
    sources = ((collection,) if context else
               tuple(name for name in GROUPS[kind] if name in offered and (source == "all" or name == source)))
    return query.strip(), sources, tuple(sorted(context.items()))


def _words(text):
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(char for char in folded if not unicodedata.combining(char)).casefold()
    return re.findall(r"[^\W_]+", folded)


def _relevance(words, phrase, card):
    """Whole-word matches in what a reader sees first; substrings such as 'daytonense' do not count."""
    title = _words(card["title"])
    subtitle = _words(card["subtitle"])
    if not words:
        return 0
    title_set, subtitle_set = set(title), set(subtitle)
    in_title = sum(word in title_set for word in words) / len(words)
    in_subtitle = sum(word in subtitle_set for word in words) / len(words)
    score = 60 * in_title + 15 * in_subtitle
    if len(words) > 1 and phrase in " ".join(title):
        score += 40
    if title[:len(words)] == words:
        score += 10
    return score


def _ranked_first_pages(available, counts, query):
    """Order every source's first-page records by visible relevance; later records keep fair interleaving."""
    first = [min(count, len(result["rows"])) for count, (_, result, _) in zip(counts, available)]
    baseline = _positions(first, 0, sum(first))
    words = _words(query)
    phrase = " ".join(words)
    order = {key: rank for rank, key in enumerate(baseline)}
    scores = {}
    queues = {}
    for index, position in baseline:
        source = available[index][0]
        # Newspaper titles often contain a query word as a name (e.g. "Arrowhead Leader").
        try:
            score = _relevance(words, phrase, _card(source, available[index][1]["rows"][position]))
        except (KeyError, TypeError, ValueError):
            score = 0  # Ranking never removes or breaks a record that cannot be scored.
        scores[(index, position)] = score - (12 if source == "newspapers" else 0)
        queues.setdefault(index, []).append((index, position))
    for keys in queues.values():
        keys.sort(key=lambda key: (-scores[key], order[key]))
    # Diminishing returns per source keep the strongest matches from several
    # collections on the first page instead of one collection's near-duplicates.
    picked = dict.fromkeys(queues, 0)
    ranked = []
    while queues:
        index = max(queues, key=lambda item: (scores[queues[item][0]] - 8 * picked[item], -order[queues[item][0]]))
        ranked.append(queues[index].pop(0))
        picked[index] += 1
        if not queues[index]:
            del queues[index]
    return ranked, first


def search(query="", kind="all", source="all", page=1, context=None):
    if type(page) is not int or not 1 <= page <= 1_000_000:
        raise ValueError("Choose a valid atlas page.")
    query, sources, context = _parameters(query, kind, source, context)
    signature = _signature(sources)
    available, missing = _first_pages(query, sources, context, signature)
    counts = [result["total"] for _, result, _ in available]
    total = sum(counts)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    offset = (page - 1) * PAGE_SIZE
    if _words(query) and len(available) > 1:
        # Best whole-word matches from all first pages lead; every later record
        # still appears exactly once in fair interleaving, so paging never drops one.
        ranked, first = _ranked_first_pages(available, counts, query)
        wanted = ranked[offset:offset + PAGE_SIZE]
        remaining = [count - shown for count, shown in zip(counts, first)]
        wanted += [(index, first[index] + position) for index, position in
                   _positions(remaining, max(0, offset - len(ranked)), PAGE_SIZE - len(wanted))]
    else:
        wanted = _positions(counts, offset, PAGE_SIZE)
    native_pages = {(index, 1): result for index, (_, result, _) in enumerate(available)}
    rows = []
    for index, position in wanted:
        source, _, size = available[index]
        native_page, within_page = divmod(position, size)
        key = (index, native_page + 1)
        if key not in native_pages:
            native_pages[key] = _page(source, query, native_page + 1, context, signature)[0]
        rows.append(_card(source, native_pages[key]["rows"][within_page]))
    return {"rows": rows, "total": total, "page": page, "pages": pages,
            "coverage": [{"source": source, "label": SOURCES[source], "records": result["total"]}
                         for source, result, _ in available],
            "missing": [{"source": source, "label": SOURCES[source], "reason": reason} for source, reason in missing]}


def _identifier(identifier):
    if not isinstance(identifier, str) or len(identifier) > 350 or any(ord(char) < 32 for char in identifier):
        return None, None
    source, separator, key = identifier.partition("|")
    return (source, key) if separator and source in SOURCES and key else (None, None)


def get_record(identifier):
    """Resolve facts and attribution from local source records, not browser text."""
    source, key = _identifier(identifier)
    if source is None:
        return None
    if source == 'publications':
        row=publications.get_summary(key)
        if row is None:
            return None
        facts,url=publications.fields(row),'https://doi.org/'+row['native_id']
        notes,description,license_text=publications.notes_for(row),row['description'],row['rights']['label']
    elif source == 'finland':
        row=finland.get_record(key)
        if row is None:
            return None
        facts,url=finland.fields(row),row['source_url']
        notes,description,license_text=list(finland.NOTES),'',finland.LICENSE
    elif source == 'france':
        row=france.get_record(key)
        if row is None:
            return None
        facts,url=france.fields(row),row['source_url']
        notes,description,license_text=list(france.NOTES),'',france.LICENSE
    elif source == 'raa':
        row=raa.get_record(key)
        if row is None:
            return None
        facts,url=raa.fields(row),row['source_url']
        notes,description,license_text=list(raa.NOTES),'',raa.LICENSE
    elif source == 'dans':
        row = dans.get_record(key)
        if row is None:
            return None
        facts, url = dans.fields(row), row['source_url']
        notes = list(dans.NOTES)
        description = '\n\n'.join(item['text'] for item in dans.descriptions(row))
        license_text = 'CC0 1.0 DataCite metadata; linked resource rights retained separately'
    elif source == 'amcr':
        row = amcr.get_record(key)
        if row is None:
            return None
        facts, url = amcr.fields(row), row['source_url']
        notes, description, license_text = list(amcr.NOTES), '', amcr.LICENSE
    elif source == 'ads':
        row = ads.get_record(key)
        if row is None:
            return None
        facts, url = ads.fields(row), row['source_url']
        notes = list(ads.NOTES)
        description = '\n\n'.join(item.get('description', '') for item in row['source']['attributes'].get('descriptions', []) or [])
        license_text = 'CC0 1.0 metadata; linked resource rights retained separately'
    elif source == "places":
        row = places.get_record(key)
        if row is None:
            return None
        facts, url = places.facts(row), row["source_url"]
        notes = ["One published gazetteer place resource; associated names, locations and connections are not additional places or excavations.",
                 "Native place types include settlements, monuments, regions and other concepts; this is not a census of excavations.",
                 "Representative points are publisher-calculated centroids or connected-place estimates, not exact excavation or find coordinates.",
                 "Name and location attestations keep their separate periods and confidence; they are not merged into an occupation date range."]
        description, license_text = row["description"], row["license"]
    elif source == "site_registers":
        row = site_registers.get_record(key)
        if row is None:
            return None
        facts, url = site_registers.facts(row), row["source_url"]
        notes = [row["summary"][name] for name in ("scope_note", "count_note", "location_note", "source_condition_note", "period_note")]
        description, license_text = "", "Original table and project rights retained separately for each edition"
    elif source == "field_assemblages":
        row = field_assemblages.get_record(key)
        if row is None:
            return None
        facts, url = field_assemblages.facts(row), row["source_url"]
        notes = [*field_assemblages.source_notes(row), *row["edition"]["notes"],
                 row["summary"]["quantity_note"], row["summary"]["source_row_identifiers_note"]]
        description, license_text = "", row["edition"]["license"]
    elif source == "specimens":
        row = specimens.get_record(key)
        if row is None:
            return None
        facts, url = specimens.facts(row), row["source_url"]
        notes = [row["summary"][name] for name in ("quantity_note", "context_note", "sampling_note", "location_note", "encoding_note")]
        description, license_text = "", specimens.LICENSE
    elif source == "environments":
        row = environments.get_record(key)
        if row is None:
            return None
        summary = environments.stats()
        facts, url = environments.facts(row), row["source_url"]
        notes = [summary[name] for name in ("hierarchy_note", "quantity_note", "age_note", "location_note", "area_note")]
        description, license_text = "", summary["license"] + " · original dataset and publication attribution retained"
    elif source == "contexts":
        row = contexts.get_record(key)
        if row is None:
            return None
        facts, url = contexts.facts(row), row["source_uri"]
        notes = ["Records retain their original project and context identities; similar labels do not establish an association.",
                 "Original observation groups and published table versions remain separate. Zero, false and unrecorded values have different meanings.",
                 "Source links retain their predicates. Free-text relationships do not establish a deposit sequence."]
        description, license_text = "", row["project"]["license"]
    elif source == "assemblages":
        row = assemblages.get_record(key)
        if row is None:
            return None
        summary = assemblages.stats()
        facts, url = assemblages.facts(row), summary["citation_url"]
        notes = [summary[name] for name in ("context_note", "quantity_note", "age_note", "units_note")]
        description, license_text = summary["citation"], summary["license"]
    elif source in ("met", "si"):
        row = objects.get_object(key)
        if row is None or not row["id"].startswith(source + ":"):
            return None
        facts, url = objects.facts(row), row["source_url"]
        notes = ["Museum catalog descriptions retain their source wording and attribution."]
        description, license_text = "", row["license"]
    elif source == "projects":
        row = projects.get_project(key)
        if row is None:
            return None
        facts, url = projects.facts(row), row["source_url"]
        notes = ["This is a dataset publication. Its time span describes the publication's coverage."]
        description, license_text = row["description"], row["license_url"]
    elif source == "dates":
        row = dates.get_date(key)
        if row is None:
            return None
        summary = dates.stats()
        facts, url = dates.facts(row), summary["citation_url"]
        notes = ["Ages are original, uncalibrated radiocarbon years BP with one-sigma standard errors.", summary["source_field_note"]]
        description, license_text = summary["citation"], "CC0 1.0"
    elif source == "dinosaurs":
        row = dinosaurs.get_record(key)
        if row is None:
            return None
        facts, url = dinosaurs.facts(row), dinosaurs.source_url(row)
        notes = ["Published occurrence and collection context in a frozen PBDB snapshot. Collection coordinates retain their reported basis and precision."]
        description, license_text = "", "CC BY 4.0 archive; original attribution retained"
    elif source == "fossils":
        from core.fossil_notes import facts as fossil_facts
        row = fossils.get_fossil(key)
        if row is None:
            return None
        facts, url = fossil_facts(row), row["source_url"]
        notes, description, license_text = ["Source specimen taxonomy, geological ages and measurements."], "", row["license"]
    elif source == "minerals":
        from core.mineral_notes import value_text, property_notes
        row = minerals.get_mineral(key)
        if row is None:
            return None
        facts = [("Formula", row["formula"]), ("Classification", row["kind"])]
        for fact in row["properties"]:
            facts.append((fact["name"], value_text(fact)))
            facts.extend(property_notes(fact))
            facts.append(("Property source", fact["source_url"]))
        url, notes, description, license_text = row["source_url"], ["Properties preserve recorded units, bounds and qualifiers."], "", row["license"]
    elif source == "newspapers":
        from core.newspaper_notes import facts as title_facts
        row = newspapers.get_title(key)
        if row is None:
            return None
        facts, url = title_facts(row), row["url"]
        notes = ["Title metadata and publication dates. The partial catalog contains no article text."]
        description, license_text = "", "Library of Congress directory metadata"
    elif source == "geology":
        from core.usgs_notes import facts as unit_facts
        row = geology.get_unit(key)
        if row is None:
            return None
        facts = unit_facts(row)
        for citation in row.get("source_citations", []):
            facts.append(("Source-map citation", citation.get("text", "") + " " + citation.get("url", "")))
        url = "https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm"
        notes, description, license_text = ["USGS regional map context at 1:500,000 scale."], "", "CC0 1.0"
    else:
        row = guides.get_guide(key)
        if row is None:
            return None
        facts = []
        for fact in row["facts"]:
            facts.append(("Reference guidance", fact["text"]))
            facts.extend(("Source", citation["name"] + " " + citation["url"]) for citation in fact["sources"])
        url = row["facts"][0]["sources"][0]["url"]
        notes, description, license_text = row["questions"], row["summary"], "Source attribution retained for each guide fact"
    result = _card(source, row)
    result.update(facts=facts, source_url=url, notes=notes, description=description, license=license_text,
                  original=deepcopy(row))
    return result


def reference_entry(identifier):
    source, key = _identifier(identifier)
    row = get_record(identifier)
    if row is None:
        raise ValueError("Choose a current atlas record to save.")
    if source == 'publications':
        return publications.reference_entry(key)
    if source == 'finland':
        return finland.reference_entry(key)
    if source == 'france':
        return france.reference_entry(key)
    if source == 'raa':
        return raa.reference_entry(key)
    if source == 'dans':
        return dans.reference_entry(key)
    if source == 'amcr':
        return amcr.reference_entry(key)
    if source == 'ads':
        return ads.reference_entry(key)
    if source == "places":
        return places.reference_entry(key)
    if source == "site_registers":
        return site_registers.reference_entry(key)
    if source == "field_assemblages":
        return field_assemblages.reference_entry(key)
    if source == "specimens":
        return specimens.reference_entry(key)
    if source == "environments":
        return environments.reference_entry(key)
    if source == "contexts":
        return contexts.reference_entry(key)
    if source == "assemblages":
        return assemblages.reference_entry(key)
    if source == "projects":
        return projects.project_entry(key)
    if source == "dates":
        return dates.reference_entry(key)
    if source == "dinosaurs":
        return dinosaurs.reference_entry(key)
    if source == "minerals":
        from core.mineral_notes import reference_entry as save
        return save(key)
    if source in ("met", "si"):
        from core.reference_notes import reference_entry as save
    elif source == "fossils":
        from core.fossil_notes import reference_entry as save
    elif source == "newspapers":
        from core.newspaper_notes import reference_entry as save
    elif source == "geology":
        from core.usgs_notes import reference_entry as save
    else:
        from core.object_guide_notes import reference_entry as save
        return save(row["original"])
    return save(row["original"])


def relationships(record):
    """Source-specific associations for the shared reader and navigation."""
    if record['source'] == 'dans':
        return dans.relationships(record['original'])
    if record["source"] == "dinosaurs":
        return dinosaurs.relationships(record["original"])
    if record["source"] == "places":
        return places.relationships(record["original"])
    if record["source"] == "site_registers":
        return site_registers.relationships(record["original"])
    if record["source"] == "field_assemblages":
        return field_assemblages.relationships(record["original"])
    if record["source"] == "specimens":
        return specimens.relationships(record["original"])
    if record["source"] == "environments":
        return environments.relationships(record["original"])
    if record["source"] == "contexts":
        return contexts.relationships(record["original"])
    if record["source"] == "assemblages":
        return [{**link, "key": link["parameters"]["view"]}
                for link in assemblages.relationships(record["original"])]
    return []
