"""Read original Neotoma sites, samples, observations and age models locally.

Text is indexed at its own scientific level. Observation searches follow
indexed source IDs to sample context and variable meanings; inherited site
prose is never copied into millions of observation documents.
"""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import re
import sqlite3

from core.data_packs import PackStore

PACK = "dated-environments"
PAGE_SIZE = 24
KINDS = {
    "site": ("sites", "siteid", "Published site"),
    "unit": ("collectionunits", "collectionunitid", "Collection unit"),
    "dataset": ("datasets", "datasetid", "Scientific dataset"),
    "analysis": ("analysisunits", "analysisunitid", "Analysis unit"),
    "sample": ("samples", "sampleid", "Scientific sample"),
    "chronology": ("chronologies", "chronologyid", "Age model"),
    "control": ("chroncontrols", "chroncontrolid", "Chronology control"),
    "date": ("geochronology", "geochronid", "Dating measurement"),
    "observation": ("data", "dataid", "Scientific observation"),
    "age": ("sampleages", "sampleageid", "Sample age assignment"),
}
IDENTIFIER = re.compile(r"(site|unit|dataset|analysis|sample|chronology|control|date|observation|age):(0|[1-9][0-9]{0,11})\Z")
NUMBER = re.compile(r"0|[1-9][0-9]{0,11}\Z")
SCOPES = {"site_id": "site", "unit_id": "unit", "dataset_id": "dataset", "analysis_id": "analysis",
          "sample_id": "sample", "chronology_id": "chronology", "variable_id": "variable"}
# A sample has both a dataset and an analysis-unit link. Preserve both original
# paths, including disagreement; do not reconcile them by similar names.
PARENTS = {
    "unit": (("siteid", "site"),),
    "dataset": (("collectionunitid", "unit"),),
    "analysis": (("collectionunitid", "unit"),),
    "sample": (("datasetid", "dataset"), ("analysisunitid", "analysis")),
    "chronology": (("collectionunitid", "unit"),),
    "control": (("chronologyid", "chronology"), ("analysisunitid", "analysis")),
    "date": (("sampleid", "sample"),),
    "observation": (("sampleid", "sample"), ("variableid", "variable")),
    "age": (("sampleid", "sample"), ("chronologyid", "chronology")),
}


def databases():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    paths = tuple(store.resolve_file(PACK, name) for name in
                  ("reader.sqlite", "environment.sqlite", "observations.sqlite"))
    return paths if all(paths) else None


def database():
    paths = databases()
    return paths[0] if paths else None


def _connect(paths):
    connection = sqlite3.connect(paths[0].resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    for alias, path in zip(("n", "o"), paths[1:]):
        connection.execute("ATTACH DATABASE ? AS " + alias,
                           (path.resolve().as_uri() + "?mode=ro&immutable=1",))  # nosec B608: fixed aliases
    return connection


def stats():
    paths = databases()
    if not paths:
        return None
    with closing(_connect(paths)) as connection:
        return _summary(connection)


def _summary(connection):
    return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def _table(kind):
    table, _, _ = KINDS[kind]
    return ("o" if kind == "observation" else "n") + ".ndb__" + table


def _one(connection, table, column, value):
    if value is None:
        return {}
    # Table/column identifiers are fixed call sites or the KINDS mapping.
    row = connection.execute('SELECT * FROM n.ndb__' + table + ' WHERE "' + column + '"=?', (value,)).fetchone()  # nosec B608
    return {key: row[key] for key in row.keys() if key != "source_row"} if row else {}


def _native(connection, kind, source_id):
    _, column, _ = KINDS[kind]
    row = connection.execute('SELECT * FROM ' + _table(kind) + ' WHERE "' + column + '"=?', (source_id,)).fetchone()  # nosec B608
    return {key: row[key] for key in row.keys() if key != "source_row"} if row else None


def _documents(kind, match):
    return ("SELECT d.source_id FROM search_fts JOIN search_documents d ON d.rowid=search_fts.rowid "
            "WHERE search_fts MATCH ? AND d.kind=?", [match, kind])


def _text_condition(kind, hits, match, alias="r"):
    clauses, values = [], []
    if kind in hits:
        query, parameters = _documents(kind, match)
        column = "variableid" if kind == "variable" else KINDS[kind][1]
        clauses.append(alias + '.' + column + ' IN (' + query + ')')
        values.extend(parameters)
    for column, parent in PARENTS.get(kind, ()):
        child, parameters = _text_condition(parent, hits, match)
        if child:
            table = "n.ndb__variables" if parent == "variable" else _table(parent)
            key = "variableid" if parent == "variable" else KINDS[parent][1]
            clauses.append(alias + '.' + column + ' IN (SELECT r.' + key + ' FROM ' + table + ' r WHERE ' + child + ')')  # nosec B608: fixed scientific mappings; values are bound separately
            values.extend(parameters)
    return ('(' + ' OR '.join(clauses) + ')' if clauses else ""), values


def _scope_condition(kind, scope, value, alias="r"):
    if kind == scope:
        key = "variableid" if kind == "variable" else KINDS[kind][1]
        return alias + '.' + key + '=?', [value]
    clauses, values = [], []
    for column, parent in PARENTS.get(kind, ()):
        child, parameters = _scope_condition(parent, scope, value)
        if child:
            table = "n.ndb__variables" if parent == "variable" else _table(parent)
            key = "variableid" if parent == "variable" else KINDS[parent][1]
            clauses.append(alias + '.' + column + ' IN (SELECT r.' + key + ' FROM ' + table + ' r WHERE ' + child + ')')  # nosec B608: fixed scientific mappings; values are bound separately
            values.extend(parameters)
    return ('(' + ' OR '.join(clauses) + ')' if clauses else ""), values


def _bulk_condition(hits, match):
    clauses, parameters = [], []
    dataset, values = _text_condition("dataset", hits, match)
    if dataset:
        clauses.append("c.datasetid IN (SELECT r.datasetid FROM n.ndb__datasets r WHERE " + dataset + ")")  # nosec B608: fixed compiler clauses
        parameters.extend(values)
    unit, values = _text_condition("unit", hits, match)
    if unit:
        clauses.append("c.analysis_collectionunitid IN (SELECT r.collectionunitid FROM n.ndb__collectionunits r WHERE " + unit + ")")  # nosec B608: fixed compiler clauses
        parameters.extend(values)
    if "variable" in hits:
        query, values = _documents("variable", match)
        clauses.append("c.variableid IN (" + query + ")")
        parameters.extend(values)
    return ('(' + ' OR '.join(clauses) + ')' if clauses else "0"), parameters


def _observation_count(connection, matches):
    """Use exact repeated-context counts, then add individual text exceptions.

    Rows matched through both a variable and a site are counted once. A sample
    or analysis-unit note can match independently; its native observations are
    added only when the grouped context has not already counted them.
    """
    bulk, bulk_values, full, full_values, uniform, uniform_values, extras, extra_values = [], [], [], [], [], [], [], []
    for match, hits in matches:
        clause, values = _bulk_condition(hits, match)
        bulk.append(clause)
        bulk_values.extend(values)
        clause, values = _text_condition("observation", hits, match)
        full.append(clause or "0")
        full_values.extend(values)
        clause, values = _text_condition("observation", hits - {"sample", "analysis"}, match)
        uniform.append(clause or "0")
        uniform_values.extend(values)
        clause, values = _text_condition("observation", hits & {"sample", "analysis"}, match)
        if clause:
            extras.append(clause)
            extra_values.extend(values)
    total = connection.execute("SELECT coalesce(sum(c.observations),0) FROM observation_counts c WHERE " +
                               " AND ".join(bulk), bulk_values).fetchone()[0]  # nosec B608
    if extras:
        where = ('(' + ' OR '.join(extras) + ') AND ' + ' AND '.join(full) +
                 ' AND NOT coalesce((' + ' AND '.join(uniform) + '),0)')
        total += connection.execute("SELECT count(*) FROM o.ndb__data r WHERE " + where,  # nosec B608: fixed compiler clauses; all query terms are bound
                                    [*extra_values, *full_values, *uniform_values]).fetchone()[0]  # nosec B608
    return total


def validate_parameters(query="", page=1, view="", record_id="", **scopes):
    values = (query, view, record_id, *scopes.values())
    if (any(not isinstance(value, str) or len(value) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value) for value in values)
            or type(page) is not int or not 1 <= page <= 1_000_000 or view not in ("", *KINDS)
            or record_id and not IDENTIFIER.fullmatch(record_id)
            or set(scopes) - set(SCOPES) or any(not NUMBER.fullmatch(value) for value in scopes.values())):
        raise ValueError("Choose an original Neotoma record or scientific association.")


def _positions(counts, offset, limit):
    low, high = 0, max(counts, default=0)
    while low < high:
        middle = (low + high + 1) // 2
        if sum(min(count, middle) for count in counts) <= offset:
            low = middle
        else:
            high = middle - 1
    skip, round_number, positions = offset - sum(min(count, low) for count in counts), low, []
    while len(positions) < limit and round_number < max(counts, default=0):
        for index, count in enumerate(counts):
            if count <= round_number:
                continue
            if skip:
                skip -= 1
            else:
                positions.append((index, round_number))
                if len(positions) == limit:
                    break
        round_number += 1
    return positions


def search(query="", page=1, view="", record_id="", **scopes):
    validate_parameters(query, page, view, record_id, **scopes)
    paths = databases()
    if not paths:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    signature = tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns, path.stat().st_ctime_ns) for path in paths)
    return deepcopy(_search(query.strip(), page, view, record_id, tuple(sorted(scopes.items())), paths, signature))


@lru_cache(maxsize=256)
def _plans(query, view, record_id, scopes, paths, signature):
    kinds = (view,) if view else tuple(KINDS)
    exact = IDENTIFIER.fullmatch(query.removeprefix("neotoma:"))
    exact_id = exact[0] if exact else record_id
    terms = [] if exact else re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    with closing(_connect(paths)) as connection:
        summary = _summary(connection)
        matches = []
        for term in terms:
            match = '"' + term + '"*'
            hits = {row[0] for row in connection.execute(
                "SELECT DISTINCT d.kind FROM search_fts JOIN search_documents d ON d.rowid=search_fts.rowid WHERE search_fts MATCH ?", (match,))}
            matches.append((match, hits))
        counts, statements = [], []
        for kind in kinds:
            clauses, parameters = [], []
            for match, hits in matches:
                clause, values = _text_condition(kind, hits, match)
                clauses.append(clause or "0")
                parameters.extend(values)
            if exact_id:
                target, _, key = exact_id.partition(":")
                clauses.append("r." + KINDS[kind][1] + "=?" if kind == target else "0")
                if kind == target:
                    parameters.append(key)
            if record_id and exact and exact_id != record_id:
                clauses.append("0")
            for name, value in scopes:
                clause, values = _scope_condition(kind, SCOPES[name], value)
                clauses.append(clause or "0")
                parameters.extend(values)
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            statement = " FROM " + _table(kind) + " r" + where
            if kind == "observation" and matches and not (exact_id or scopes):
                count = _observation_count(connection, matches)
            else:
                count = (connection.execute("SELECT count(*)" + statement, parameters).fetchone()[0] if clauses
                         else summary["record_counts"][kind])  # nosec B608: fixed source mapping and bound values
            counts.append(count)
            statements.append((statement, parameters))
        return kinds, counts, statements, summary["record_counts"]


@lru_cache(maxsize=256)
def _search(query, page, view, record_id, scopes, paths, signature):
    kinds, counts, statements, record_counts = _plans(query, view, record_id, scopes, paths, signature)
    with closing(_connect(paths)) as connection:
        total = sum(counts)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        wanted = _positions(counts, (page - 1) * PAGE_SIZE, PAGE_SIZE)
        offsets = {}
        for index, offset in wanted:
            offsets.setdefault(index, []).append(offset)
        fetched = {}
        for index, positions in offsets.items():
            kind = kinds[index]
            statement, parameters = statements[index]
            if counts[index] > max(10_000, record_counts[kind] // 20):
                # An indexed OR can collect and sort millions of broad matches
                # before LIMIT. Read their existing source order instead.
                statement = statement.replace(" r WHERE ", " r NOT INDEXED WHERE ", 1)
            # Fetch a small contiguous page per evidence type, not all matches.
            rows = connection.execute("SELECT r.*" + statement + " ORDER BY r.source_row LIMIT ? OFFSET ?",
                                      [*parameters, len(positions), positions[0]]).fetchall()  # nosec B608
            for offset, row in zip(positions, rows):
                source = {key: row[key] for key in row.keys() if key != "source_row"}
                fetched[index, offset] = _record(connection, kind, source, details=False)
        return {"rows": [fetched[position] for position in wanted], "total": total, "page": page, "pages": pages,
                "installed": True, "counts": dict(zip(kinds, counts))}


def _context(connection, kind, source):
    associated = {}
    if kind in ("observation", "age", "date"):
        associated["sample"] = _one(connection, "samples", "sampleid", source.get("sampleid"))
    sample = source if kind == "sample" else associated.get("sample", {})
    if sample:
        associated["dataset"] = _one(connection, "datasets", "datasetid", sample.get("datasetid"))
        associated["analysis"] = _one(connection, "analysisunits", "analysisunitid", sample.get("analysisunitid"))
    if kind in ("age", "control"):
        associated["chronology"] = _one(connection, "chronologies", "chronologyid", source.get("chronologyid"))
    if kind == "control" and source.get("analysisunitid") is not None:
        associated["analysis"] = _one(connection, "analysisunits", "analysisunitid", source["analysisunitid"])
    dataset = source if kind == "dataset" else associated.get("dataset", {})
    analysis = source if kind == "analysis" else associated.get("analysis", {})
    chronology = source if kind == "chronology" else associated.get("chronology", {})
    unit_ids = list(dict.fromkeys(row["collectionunitid"] for row in (dataset, analysis, chronology)
                                if row.get("collectionunitid") is not None))
    associated["units"] = [_one(connection, "collectionunits", "collectionunitid", key) for key in unit_ids]
    if kind == "unit":
        associated["units"] = [source]
    site_ids = list(dict.fromkeys(row["siteid"] for row in associated["units"] if row.get("siteid") is not None))
    associated["sites"] = [_one(connection, "sites", "siteid", key) for key in site_ids]
    if kind == "site":
        associated["sites"] = [source]
    associated["collection_types"] = [_one(connection, "collectiontypes", "colltypeid", row.get("colltypeid"))
                                       for row in associated["units"]]
    if dataset:
        associated["dataset_type"] = _one(connection, "datasettypes", "datasettypeid", dataset.get("datasettypeid"))
    if kind == "observation":
        variable = _one(connection, "variables", "variableid", source.get("variableid"))
        associated["variable"] = variable
        associated["taxon"] = _one(connection, "taxa", "taxonid", variable.get("taxonid"))
        associated["variable_units"] = _one(connection, "variableunits", "variableunitsid", variable.get("variableunitsid"))
        associated["element"] = _one(connection, "variableelements", "variableelementid", variable.get("variableelementid"))
        associated["variable_context"] = _one(connection, "variablecontexts", "variablecontextid", variable.get("variablecontextid"))
    age_source = source if kind in ("chronology", "date", "control") else chronology
    if age_source:
        associated["age_type"] = _one(connection, "agetypes", "agetypeid", age_source.get("agetypeid"))
    if kind == "control":
        associated["control_type"] = _one(connection, "chroncontroltypes", "chroncontroltypeid", source.get("chroncontroltypeid"))
    if kind == "date":
        associated["date_type"] = _one(connection, "geochrontypes", "geochrontypeid", source.get("geochrontypeid"))
    return associated


def value_text(value):
    if value is None:
        return "Not recorded (source NULL)"
    if value == "":
        return "Blank source field"
    return str(value)


def _linked_text(row, key):
    # An unresolved relationship is different from a recorded SQL NULL value.
    return value_text(row[key]) if key in row else "Not available in this source"


def _flag(value):
    return {"t": "True", "f": "False"}.get(value, value_text(value))


def _record(connection, kind, source, details=True):
    associated = _context(connection, kind, source)
    identifier = source[KINDS[kind][1]]
    title = {"site": source.get("sitename"), "unit": source.get("collunitname") or source.get("handle"),
             "dataset": source.get("datasetname") or associated.get("dataset_type", {}).get("datasettype"),
             "analysis": source.get("analysisunitname"), "sample": source.get("samplename") or source.get("labnumber"),
             "chronology": source.get("chronologyname")}.get(kind)
    if kind == "observation":
        title = " · ".join((associated["taxon"].get("taxonname") or "Variable " + value_text(source.get("variableid")),
                            value_text(source.get("value")), _linked_text(associated["variable_units"], "variableunits")))
    elif kind in ("age", "control", "date"):
        label = (source.get("labnumber") or associated.get("date_type", {}).get("geochrontype") if kind == "date" else
                 associated.get("control_type", {}).get("chroncontroltype") if kind == "control" else "Sample " + str(source.get("sampleid")))
        age_text = value_text(source.get("age"))
        if kind == "date" and source.get("infinite") == "t":
            age_text = "Greater than " + age_text if source.get("age") is not None else "Infinite / greater-than date"
        if kind == "age" and source.get("age") is None and all(source.get(key) is not None for key in ("ageyounger", "ageolder")):
            age_text = "Model bounds " + source["ageyounger"] + "–" + source["ageolder"]
        title = " · ".join((label or KINDS[kind][2], age_text,
                            associated.get("age_type", {}).get("agetype") or "Age type not recorded"))
    title = title or KINDS[kind][2] + " " + identifier
    subtitle = " · ".join(dict.fromkeys(str(value) for value in (
        *[row.get("sitename") for row in associated["sites"]],
        *[row.get("colltype") for row in associated["collection_types"]],
        associated.get("dataset_type", {}).get("datasettype"),
        associated.get("analysis", {}).get("analysisunitname"),
        associated.get("chronology", {}).get("chronologyname")) if value))
    record = {"id": kind + ":" + identifier, "source_id": identifier, "kind": kind, "title": title,
              "subtitle": subtitle, "category": KINDS[kind][2], "source": source, "associated": associated,
              "source_url": "https://data.neotomadb.org/"}
    if details:
        _details(connection, record)
    return record


def get_record(identifier):
    if not isinstance(identifier, str) or not (match := IDENTIFIER.fullmatch(identifier)):
        return None
    paths = databases()
    if not paths:
        return None
    with closing(_connect(paths)) as connection:
        source = _native(connection, match[1], match[2])
        return _record(connection, match[1], source) if source is not None else None


def _rows(connection, statement, parameters):
    return [{key: row[key] for key in row.keys() if key != "source_row"}
            for row in connection.execute(statement, parameters)]


def _details(connection, record):
    source, associated, kind = record["source"], record["associated"], record["kind"]
    record["regions"] = [{"site_id": site["siteid"], "source": _rows(connection,
        "SELECT g.* FROM n.ndb__sitegeopolitical sg JOIN n.ndb__geopoliticalunits g ON g.geopoliticalid=sg.geopoliticalid WHERE sg.siteid=? ORDER BY sg.source_row",
        (site["siteid"],))} for site in associated["sites"] if site]
    sample = source if kind == "sample" else associated.get("sample", {})
    record["age_assignments"], record["age_assignments_total"] = [], 0
    if sample:
        key = sample["sampleid"]
        record["age_assignments_total"] = connection.execute(
            "SELECT count(*) FROM n.ndb__sampleages WHERE sampleid=?", (key,)).fetchone()[0]
        for row in _rows(connection, "SELECT * FROM n.ndb__sampleages WHERE sampleid=? ORDER BY source_row LIMIT 24", (key,)):
            chronology = _one(connection, "chronologies", "chronologyid", row["chronologyid"])
            age_type = _one(connection, "agetypes", "agetypeid", chronology.get("agetypeid"))
            record["age_assignments"].append({"source": row, "chronology": chronology, "age_type": age_type})
    record["uncertainties"] = (_rows(connection, "SELECT * FROM n.ndb__datauncertainties WHERE dataid=? ORDER BY source_row", (source["dataid"],))
                               if kind == "observation" else [])
    record["uncertainty_meanings"] = [{"unit": _one(connection, "variableunits", "variableunitsid", row["uncertaintyunitid"]),
        "basis": _one(connection, "uncertaintybases", "uncertaintybasisid", row["uncertaintybasisid"])} for row in record["uncertainties"]]
    if kind == "date":
        record["radiocarbon"] = _one(connection, "radiocarbon", "geochronid", source["geochronid"])
    record["publications"], record["dataset_dois"], record["constituent_databases"], record["investigators"] = [], [], [], []
    dataset = source if kind == "dataset" else associated.get("dataset", {})
    if dataset:
        key = dataset["datasetid"]
        record["publications"] = _rows(connection,
            "SELECT p.*,d.primarypub FROM n.ndb__datasetpublications d JOIN n.ndb__publications p ON p.publicationid=d.publicationid WHERE d.datasetid=? ORDER BY d.source_row", (key,))
        record["dataset_dois"] = _rows(connection, "SELECT * FROM n.ndb__datasetdoi WHERE datasetid=? ORDER BY source_row", (key,))
        record["constituent_databases"] = _rows(connection,
            "SELECT c.* FROM n.ndb__datasetdatabases d JOIN n.ndb__constituentdatabases c ON c.databaseid=d.databaseid WHERE d.datasetid=? ORDER BY d.source_row", (key,))
        record["investigators"] = _rows(connection,
            "SELECT c.*,p.piorder FROM n.ndb__datasetpis p JOIN n.ndb__contacts c ON c.contactid=p.contactid WHERE p.datasetid=? ORDER BY CAST(p.piorder AS INTEGER),p.source_row", (key,))
    if kind == "date":
        dating_publications = _rows(connection,
            "SELECT p.* FROM n.ndb__geochronpublications g JOIN n.ndb__publications p ON p.publicationid=g.publicationid WHERE g.geochronid=? ORDER BY g.source_row", (source["geochronid"],))
        seen = {row["publicationid"] for row in record["publications"]}
        record["publications"].extend(row for row in dating_publications if row["publicationid"] not in seen)


def facts(record):
    source, associated, kind = record["source"], record["associated"], record["kind"]
    rows = [("Evidence", record["category"]), ("Source record ID", record["id"])]
    rows.extend(("Published site", row.get("sitename") or "Site " + row["siteid"]) for row in associated["sites"] if row)
    rows.extend(("Collection method", row["colltype"]) for row in associated["collection_types"] if row.get("colltype"))
    for region in record.get("regions", []):
        labels = "; ".join(row["geopoliticalname"] for row in region["source"] if row.get("geopoliticalname"))
        if labels:
            rows.append(("Published region labels · site " + region["site_id"], labels))
    if associated.get("dataset_type", {}).get("datasettype"):
        rows.append(("Dataset type", associated["dataset_type"]["datasettype"]))
    if len(associated["units"]) > 1:
        rows.append(("Source context", "Dataset, analysis unit or chronology refer to different collection units; original links retained."))
    if kind == "observation":
        rows.append(("Original value", value_text(source.get("value"))))
        rows.extend((label, _linked_text(associated[group], key)) for label, group, key in (
            ("Original unit", "variable_units", "variableunits"), ("Taxon or measured parameter", "taxon", "taxonname"),
            ("Variable element", "element", "variableelement"), ("Variable context", "variable_context", "variablecontext")))
        if (associated["variable_units"].get("variableunits") or "").casefold() == "present/absent":
            rows.append(("Quantity convention", "Presence/absence observation; this value is not a specimen count."))
    if kind in ("age", "date", "control", "chronology"):
        rows.append(("Original age type", _linked_text(associated.get("age_type", {}), "agetype")))
        for key, label in (("age", "Original age"), ("ageyounger", "Younger age bound"), ("ageolder", "Older age bound"),
                           ("errorolder", "Older error"), ("erroryounger", "Younger error"),
                           ("agelimityounger", "Younger control limit"), ("agelimitolder", "Older control limit"),
                           ("ageboundyounger", "Younger model bound"), ("ageboundolder", "Older model bound")):
            if key in source:
                rows.append((label, value_text(source[key])))
        chronology = source if kind == "chronology" else associated.get("chronology", {})
        if chronology:
            rows.append(("Model default for its age type", _flag(chronology.get("isdefault"))))
            rows.append(("Age model", value_text(chronology.get("agemodel"))))
        if kind == "date":
            rows.append(("Infinite / greater-than measurement", _flag(source.get("infinite"))))
    sample = source if kind == "sample" else associated.get("sample", {})
    if sample and sample.get("preparationmethod") is not None:
        rows.append(("Original preparation method", value_text(sample["preparationmethod"])))
    if record.get("age_assignments_total"):
        rows.append(("Associated sample age assignments", str(record["age_assignments_total"])))
    if record.get("investigators"):
        rows.append(("Dataset investigators", "; ".join(row["contactname"] for row in record["investigators"] if row.get("contactname"))))
    if record.get("constituent_databases"):
        rows.append(("Constituent databases", "; ".join(row["databasename"] for row in record["constituent_databases"] if row.get("databasename"))))
    return rows


def location_fields(record):
    groups = []
    for site in record["associated"]["sites"]:
        if not site:
            continue
        fields = [("Source site", site.get("sitename") or site["siteid"])]
        fields.extend((label, value_text(site[key])) for key, label in (
            ("longitudewest", "West longitude"), ("longitudeeast", "East longitude"),
            ("latitudesouth", "South latitude"), ("latitudenorth", "North latitude"),
            ("altitude", "Altitude (metres)"), ("area", "Original site area (unit documentation differs)")) if key in site)
        fields.append(("Location convention", "Original published point or bounding area. Areas may describe extent, uncertainty or a deliberately obscured location. A rectangle's centre is not an exact site location."))
        groups.append(fields)
    for unit in record["associated"]["units"]:
        if not unit:
            continue
        fields = [("Source collection unit", unit.get("collunitname") or unit["collectionunitid"])]
        fields.extend((label, value_text(unit[key])) for key, label in (
            ("gpslatitude", "Recorded GPS latitude"), ("gpslongitude", "Recorded GPS longitude"),
            ("gpsaltitude", "Recorded GPS altitude (metres)"), ("gpserror", "Recorded GPS error (metres)"),
            ("waterdepth", "Recorded water depth (metres)"), ("location", "Source location description")) if key in unit)
        groups.append(fields)
    return groups


def relationships(record):
    """Page through original scientific associations in the shared Atlas."""
    kind, source, associated = record["kind"], record["source"], record["associated"]
    links, candidates = [], []
    children = {
        "site": ("unit", "dataset", "observation", "date"),
        "unit": ("dataset", "analysis", "chronology", "observation", "date"),
        "dataset": ("sample", "observation", "date"),
        "analysis": ("sample", "observation", "date"),
        "sample": ("observation", "age", "date"),
        "chronology": ("control", "age"),
    }
    for view in children.get(kind, ()):
        candidates.append((view, {kind + "_id": record["source_id"]}))
    if kind == "observation":
        candidates.append(("age", {"sample_id": source["sampleid"]}))
    for parent, row in (("sample", associated.get("sample")), ("dataset", associated.get("dataset")),
                        ("analysis", associated.get("analysis")), ("chronology", associated.get("chronology"))):
        if row:
            candidates.append((parent, {"record_id": parent + ":" + row[KINDS[parent][1]]}))
    if kind != "site":
        candidates.extend(("site", {"record_id": "site:" + row["siteid"]}) for row in associated["sites"] if row)
    if kind != "unit":
        candidates.extend(("unit", {"record_id": "unit:" + row["collectionunitid"]}) for row in associated["units"] if row)
    seen = set()
    for view, scope in candidates:
        identity = (view, tuple(scope.items()))
        if identity in seen:
            continue
        seen.add(identity)
        result = search(view=view, **scope)
        if result["total"]:
            links.append({"key": view + ":" + str(len(links)), "label": KINDS[view][2] + ("s" if result["total"] > 1 else ""), "total": result["total"],
                          "rows": result["rows"][:4], "parameters": {"collection": "environments", "view": view, **scope}})
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose an installed Neotoma record to save.")
    summary = stats()
    lines = ["# Neotoma scientific reference — " + _md(record["title"]), ""]
    lines.extend("- " + label + ": " + _md(value) for label, value in facts(record))
    lines += ["", "## Original source fields", ""]
    lines.extend("- " + _md(key) + ": " + _md(value_text(value)) for key, value in record["source"].items())
    for assignment in record["age_assignments"]:
        lines += ["", "## Sample age assignment · " + assignment["source"]["sampleageid"], ""]
        for label, row in (("Source", assignment["source"]), ("Chronology", assignment["chronology"]), ("Age type", assignment["age_type"])):
            lines.extend("- " + label + " · " + _md(key) + ": " + _md(value_text(value)) for key, value in row.items())
    if record["age_assignments_total"] > len(record["age_assignments"]):
        lines.append("First 24 of " + str(record["age_assignments_total"]) + " assignments; all are available through the sample association.")
    for uncertainty, meanings in zip(record["uncertainties"], record["uncertainty_meanings"]):
        lines += ["", "## Original measurement uncertainty", ""]
        for label, row in (("Source", uncertainty), ("Unit", meanings["unit"]), ("Basis", meanings["basis"])):
            lines.extend("- " + label + " · " + _md(key) + ": " + _md(value_text(value)) for key, value in row.items())
    for publication in record["publications"]:
        lines += ["", "## Source publication", ""]
        lines.extend("- " + _md(key) + ": " + _md(value_text(publication[key])) for key in
                     ("publicationid", "citation", "articletitle", "booktitle", "year", "journal", "volume", "issue", "pages", "publisher", "doi", "url") if key in publication)
    for row in record["dataset_dois"]:
        lines.append("Dataset DOI (original): " + _md(value_text(row.get("doi"))))
    for key in ("quantity_note", "age_note", "location_note", "area_note", "hierarchy_note"):
        lines += ["", summary[key]]
    lines += ["", summary["source"], summary["source_release"], summary["source_url"], summary["citation_url"],
              "Source archive SHA-256: " + summary["source_sha256"], "Data rights: " + summary["license"]]
    markdown = "\n".join(lines)
    entry = {"id": hashlib.sha256(("neotoma:" + markdown).encode()).hexdigest()[:24], "kind": "investigation",
             "title": ("Neotoma · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published scientific reference", "source": summary["source_url"], "outcome": record["category"]},
             "markdown": markdown}
    validate_book({"version": 1, "entries": [entry]})
    return entry
