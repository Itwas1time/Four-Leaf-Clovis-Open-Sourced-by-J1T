"""Read published EUROEVOL observations and their original phase associations."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3

from core.data_packs import PackStore

PACK = "neolithic-assemblages"
PAGE_SIZE = 24
VIEWS = {
    "phases": "Occupation phase", "sites": "Published site",
    "animals": "Animal assemblage observation", "plants": "Plant assemblage observation",
    "bones": "Recorded animal bone", "measurements": "Bone measurement",
    "dates": "Dating sample", "animal-recovery": "Animal recovery methods",
    "plant-recovery": "Plant recovery methods", "plant-phases": "Plant sampling phase",
    "animal-taxa": "Animal taxonomic label", "plant-taxa": "Plant taxonomic label",
}


def database():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    return store.resolve_file(PACK, "assemblages.sqlite")


def _connect(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def stats():
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        row = connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()
    return json.loads(row[0])


def search(query="", view="all", page=1, phase_id="", site_id="", bone_id=""):
    if (view not in (*VIEWS, "all") or type(page) is not int or not 1 <= page <= 100_000
            or any(not isinstance(value, str) or len(value) > 120
                   or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
                   for value in (query, phase_id, site_id, bone_id))):
        raise ValueError("Choose a valid assemblage search with up to 120 characters.")
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    clauses, parameters = [], []
    terms = re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    if terms:
        clauses.append("r.rowid IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?)")
        parameters.append(" AND ".join('"' + term + '"*' for term in terms))
    for column, value in (("view", view if view != "all" else ""),
                          ("phase_id", phase_id), ("site_id", site_id), ("bone_id", bone_id)):
        if value:
            clauses.append(f"r.{column}=?")  # nosec B608: fixed internal column names
            parameters.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(_connect(path)) as connection:
        total = connection.execute("SELECT count(*) FROM records r" + where, parameters).fetchone()[0]  # nosec B608
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        # List pages omit the large original fields and associated recovery descriptions.
        rows = [dict(row) for row in connection.execute(
            "SELECT id,view,source_id,title,site_id,site_name,country,phase_id,bone_id,taxon_label,subtitle,"
            "animal_count,plant_count,date_count FROM records r" + where +  # nosec B608
            " ORDER BY CASE view WHEN 'phases' THEN 0 WHEN 'sites' THEN 1 ELSE 2 END,view,source_id LIMIT ? OFFSET ?",
            [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


def get_record(identifier):
    if not isinstance(identifier, str) or len(identifier) > 160 or identifier.partition(":")[0] not in VIEWS:
        return None
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        row = connection.execute(
            "SELECT r.*,s.source_json FROM records r JOIN source_records s "
            "ON s.kind=r.source_kind AND s.source_id=r.source_id WHERE r.id=?", (identifier,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        source = json.loads(record["source_json"])
        associated = json.loads(record["extra_json"])
        joins = {"phase": ("CommonPhases", record["phase_id"]), "site": ("CommonSites", record["site_id"]),
                 "bone": ("FaunalBones", record["bone_id"]), "animal_recovery": ("FaunalPhases", record["phase_id"]),
                 "plant_sampling": ("ABotPhases", record["phase_id"]), "plant_recovery": ("ABotSites", record["site_id"])}
        for label, (kind, key) in joins.items():
            found = connection.execute("SELECT source_json FROM source_records WHERE kind=? AND source_id=?", (kind, key)).fetchone() if key else None
            associated[label] = json.loads(found[0]) if found else {}
        taxon_code = source.get("TaxonCode", associated["bone"].get("TaxonCode", ""))
        taxon_kind = "ABotTaxaList" if record["view"] in ("plants", "plant-taxa") else "FaunalTaxaList"
        taxon = connection.execute("SELECT source_json FROM source_records WHERE kind=? AND source_id=?", (taxon_kind, taxon_code)).fetchone()
        associated["taxonomy"] = json.loads(taxon[0]) if taxon else {}
    if row is None:
        return None
    record["source"] = json.loads(record.pop("source_json"))
    record.pop("extra_json")
    record["associated"] = associated
    record.pop("search_text")
    record.pop("rowid")
    return record


def facts(record):
    rows = [("Evidence", VIEWS[record["view"]]), ("Source identifier", record["source_id"])]
    rows.extend((label, record[key]) for label, key in (
        ("Published site", "site_name"), ("Country label", "country"),
        ("Recorded occupation phase", "phase_id"), ("Bone identifier", "bone_id"),
        ("Source taxonomic label", "taxon_label")) if record[key])
    if record["view"] in ("phases", "sites"):
        rows.extend((label, f'{record[key]:,}') for label, key in (
            ("Associated animal observation rows", "animal_count"),
            ("Associated plant observation rows", "plant_count"),
            ("Associated dating sample rows", "date_count")))
    source = record["source"]
    phase = record["associated"].get("phase", {})
    for key, label in (("Culture", "Culture label"), ("Subculture", "Subculture label"), ("Period", "Period label")):
        value = source.get(key, phase.get(key))
        if value not in (None, "", "NULL"):
            rows.append((label, value))
    if source.get("PresenceOnly") == "1":
        rows.append(("Quantity convention", "Presence-only observation; excluded from quantitative sums"))
    for key, label in (("NISP", "Source NISP count"), ("NumberPerPhase", "Source plant count"),
                       ("C14Age", "Original age (uncalibrated BP)"),
                       ("C14SD", "Original standard deviation"), ("Measurement", "Measurement code")):
        if source.get(key) not in (None, "", "NULL"):
            rows.append((label, source[key]))
    if record["view"] == "measurements":
        rows.append(("Source measurement", source["Value"] + " mm"))
    for key, label in (("animal_nisp", "Quantitative animal NISP sum"),
                       ("plant_count", "Quantitative plant count sum")):
        quantity = record["associated"].get(key)
        if quantity and quantity["value"] is not None:
            rows.append((label, quantity["value"] + f' ({quantity["numeric_rows"]:,} quantitative rows)'))
    return rows


def relationships(record):
    """Return original identity joins for the common reader's evidence links."""
    if record["view"] == "sites":
        scope = {"site_id": record["site_id"]}
        views = ("phases", "animals", "plants", "dates", "bones", "measurements", "plant-recovery")
    elif record["view"] in ("bones", "measurements") and record["bone_id"]:
        scope = {"bone_id": record["bone_id"]}
        views = ("bones", "measurements")
    elif record["phase_id"]:
        scope = {"phase_id": record["phase_id"]}
        views = ("animals", "plants", "dates", "bones", "measurements", "animal-recovery", "plant-phases")
    else:
        return []
    links = []
    for view in views:
        result = search(view=view, **scope)
        if result["total"]:
            links.append({"label": VIEWS[view], "total": result["total"], "rows": result["rows"][:4],
                          "parameters": {"view": view, **scope}})
    for view, key in (("phases", "phase_id"), ("sites", "site_id")):
        if record["view"] != view and record[key] and view not in views:
            result = search(view=view, **{key: record[key]})
            if result["total"]:
                links.append({"label": VIEWS[view], "total": result["total"], "rows": result["rows"][:4],
                              "parameters": {"view": view, key: record[key]}})
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose a record from the installed assemblage collection.")
    summary = stats()
    lines = ["# Published assemblage reference — " + _md(record["title"]), ""]
    lines.extend("- " + label + ": " + _md(value) for label, value in facts(record))
    lines += ["", "## Original source fields", ""]
    lines.extend("- " + _md(key) + ": " + _md(value) for key, value in record["source"].items())
    for key, label in (("animal_recovery", "Animal recovery methods"),
                       ("plant_sampling", "Plant sampling phase"), ("plant_recovery", "Plant recovery methods")):
        original = record["associated"].get(key)
        if original:
            lines.extend(["", "## " + label, ""])
            lines.extend("- " + _md(name) + ": " + _md(value) for name, value in original.items())
    lines += ["", summary["context_note"], summary["quantity_note"], summary["age_note"],
              summary["units_note"], "", summary["citation"], summary["citation_url"],
              "Source table: " + record["source_kind"], "Source snapshot: " + summary["source_release"],
              "Data rights: CC0 1.0. Original NULL strings mean unknown; zeros remain source zeros."]
    markdown = "\n".join(lines)
    entry = {"id": hashlib.sha256(("euroevol:" + markdown).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Assemblage · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published assemblage reference", "source": summary["citation_url"],
                         "outcome": VIEWS[record["view"]]}, "markdown": markdown}
    validate_book({"version": 1, "entries": [entry]})
    return entry
