"""One paged search and record reader over attributable local collections."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import sqlite3

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

PAGE_SIZE = 24
SOURCES = {
    "assemblages": "UCL · Neolithic assemblages", "projects": "Open Context · publications",
    "dates": "p3k14c · radiocarbon dates", "met": "Met · objects",
    "si": "Smithsonian · anthropology", "fossils": "Smithsonian · fossil specimens",
    "dinosaurs": "Paleobiology Database · Dinosauria", "geology": "USGS · mapped geology",
    "minerals": "Wikidata · mineral properties", "newspapers": "Library of Congress · newspaper titles",
    "guides": "Material reference guides", "contexts": "Open Context · excavations & surveys",
    "environments": "Neotoma · sites, samples & environments",
}
KINDS = {"all": "All evidence", "archaeology": "Archaeology & objects", "fossils": "Fossils",
         "history": "Historical documents", "earth": "Geology & minerals"}
GROUPS = {"all": tuple(SOURCES), "archaeology": ("assemblages", "contexts", "environments", "projects", "dates", "met", "si", "guides"),
          "fossils": ("fossils", "dinosaurs"), "history": ("newspapers",), "earth": ("geology", "minerals")}
OPTIONAL = {"assemblages": assemblages, "dates": dates, "dinosaurs": dinosaurs, "contexts": contexts, "environments": environments}
_READERS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="clovis-atlas")


def _signature(sources=None):
    """Verify optional data before using cached results, including after repair."""
    signature = []
    for name, module in OPTIONAL.items():
        if sources is not None and name not in sources:
            continue
        try:
            path = module.database()
            stat = path.stat() if path else None
            signature.append((name, str(path) if path else "", stat.st_mtime_ns if stat else 0,
                              stat.st_ctime_ns if stat else 0, stat.st_size if stat else 0))
        except (ValueError, OSError, sqlite3.Error):
            signature.append((name, "unavailable"))
    return tuple(signature)


def _native(source, query, page, context=()):
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
        return dinosaurs.search(query=query, lineage="all", page=page), dinosaurs.PAGE_SIZE
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
def _first_pages(query, sources, context, signature):
    def read(source):
        try:
            result, size = _page(source, query, 1, context, signature)
            if result.get("installed") is False:
                return None, (source, "Collection not installed")
            return (source, result, size), None
        except (ValueError, OSError, sqlite3.Error):
            return None, (source, "Collection could not be read")
    available, missing = [], []
    for result, unavailable in _READERS.map(read, sources):
        if result is not None:
            available.append(result)
        if unavailable is not None:
            missing.append(unavailable)
    return available, missing


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
    evidence = {"projects": "Dataset publication", "met": "Museum object", "si": "Museum object",
                "fossils": "Fossil specimen", "dinosaurs": "Published fossil occurrence",
                "dates": "Radiocarbon determination", "geology": "Mapped geological unit",
                "minerals": "Mineral reference", "newspapers": "Newspaper title", "guides": "Material guide"}.get(source)
    if source == "environments":
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
    if collection == "environments":
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
    sources = ((collection,) if context else
               tuple(name for name in GROUPS[kind] if source == "all" or name == source))
    return query.strip(), sources, tuple(sorted(context.items()))


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
    wanted = _positions(counts, (page - 1) * PAGE_SIZE, PAGE_SIZE)
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
    if source == "environments":
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
    if record["source"] == "environments":
        return environments.relationships(record["original"])
    if record["source"] == "contexts":
        return contexts.relationships(record["original"])
    if record["source"] == "assemblages":
        return [{**link, "key": link["parameters"]["view"]}
                for link in assemblages.relationships(record["original"])]
    return []
