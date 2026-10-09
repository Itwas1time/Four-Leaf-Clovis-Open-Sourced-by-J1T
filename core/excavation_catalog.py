"""Read attributable excavation contexts, finds and survey observations locally."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import re
import sqlite3
import zlib

from core.data_packs import PackStore

PACK = "excavations-surveys"
PAGE_SIZE = 24
DATASETS = {"gabii": "Gabii", "petra": "Petra Great Temple", "ekas": "Eastern Korinthia survey"}
SURVEY_PROCEDURES = "aaf24420-bbf0-415a-b28b-3aa1353e15de"
SCOPES = ("record", "children", "targets", "incoming")
IDENTIFIER = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")


def database():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    return store.resolve_file(PACK, "contexts.sqlite")


def _connect(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _decode(value):
    return json.loads(zlib.decompress(value))


def field_label(predicate):
    """Readable source keys; the original predicate stays in the observation."""
    key = predicate.partition(":")[2] or predicate
    return re.sub(r"^(?:\d+-|oc-gen-)", "", key).replace("-", " ").capitalize()


class _SourceText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("p", "div", "li", "tr"):
            self.parts.append("\n")


def _source_text(value):
    # Publisher prose sometimes includes HTML. Display text without interpreting markup;
    # the unmodified source value remains in the original observation document.
    display = value.translate({0x91: "‘", 0x92: "’", 0x93: "“", 0x94: "”", 0x96: "–", 0x97: "—"})
    if re.search(r"</?(?:p|div|br|span|u|b|i|a|ul|li|table)\b", display, flags=re.I):
        parser = _SourceText()
        parser.feed(display)
        return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
    return display


def value_text(value):
    if isinstance(value, dict):
        if "@en" in value:
            return _source_text(value["@en"])
        if "label" in value:
            return value["label"]
        return value.get("id") or json.dumps(value, ensure_ascii=False)
    if value is None:
        return "Not recorded"
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def observation_fields(observation, definitions=None):
    return [((definitions or {}).get(key, {}).get("label") or field_label(key),
             "; ".join(value_text(value) for value in values))
            for key, values in observation.items() if key.startswith("oc-pred:")]


def stats():
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        row = connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()
    return json.loads(row[0])


def validate_parameters(query="", page=1, dataset="", category="", scope="", record_id="", predicate=""):
    values = (query, dataset, category, scope, record_id, predicate)
    if (any(not isinstance(value, str) or len(value) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value) for value in values)
            or type(page) is not int or not 1 <= page <= 100_000
            or dataset not in ("", *DATASETS) or scope not in ("", *SCOPES)
            or bool(scope) != bool(record_id) or record_id and not IDENTIFIER.fullmatch(record_id)
            or predicate and (scope not in ("targets", "incoming") or not predicate.startswith("oc-pred:"))):
        raise ValueError("Choose a published excavation or survey association.")


def search(query="", page=1, dataset="", category="", scope="", record_id="", predicate=""):
    validate_parameters(query, page, dataset, category, scope, record_id, predicate)
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    clauses, parameters = [], []
    terms = re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    source = "records r"
    candidate = query.strip().lower().removeprefix("https://opencontext.org/subjects/").removeprefix("http://opencontext.org/subjects/")
    exact_identifier = candidate if IDENTIFIER.fullmatch(candidate) else None
    if exact_identifier:
        clauses.append("r.id=?")
        parameters.append(exact_identifier)
    elif terms:
        source = "records_fts f JOIN records r ON r.rowid=f.rowid"
        clauses.append("records_fts MATCH ?")
        parameters.append(" AND ".join('"' + term + '"*' for term in terms))
    for column, value in (("dataset", dataset), ("category", category)):
        if value:
            clauses.append(f"r.{column}=?")  # nosec B608: fixed internal column names
            parameters.append(value)
    if scope in ("record", "children"):
        clauses.append("r.id=?" if scope == "record" else "r.parent_id=?")
        parameters.append(record_id)
    elif scope:
        edge = ("SELECT target_id FROM relationships WHERE source_id=?" if scope == "targets"
                else "SELECT source_id FROM relationships WHERE target_id=?")
        if predicate:
            edge += " AND predicate=?"
        clauses.append("r.id IN (" + edge + ")")  # nosec B608
        parameters.extend((record_id, predicate) if predicate else (record_id,))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(_connect(path)) as connection:
        # Avoid fetching every matching row just to count or alphabetize a broad search.
        if terms and not exact_identifier and not any((dataset, category, scope)):
            total = connection.execute("SELECT count(*) FROM records_fts WHERE records_fts MATCH ?", parameters).fetchone()[0]
        else:
            total = connection.execute("SELECT count(*) FROM " + source + where, parameters).fetchone()[0]  # nosec B608: fixed SQL clauses
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        order = "f.rowid" if terms and not exact_identifier else "r.rowid"
        rows = [dict(row) for row in connection.execute(
            "SELECT r.id,r.dataset,r.title,r.category,r.context_label,r.source_uri FROM " + source + where +  # nosec B608: fixed SQL clauses
            " ORDER BY " + order + " LIMIT ? OFFSET ?", [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


def get_record(identifier):
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        return None
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        row = connection.execute("SELECT * FROM records WHERE id=?", (identifier,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        project = connection.execute("SELECT title,uri,license,source_json FROM datasets WHERE id=?", (record["dataset"],)).fetchone()
        record["project"] = dict(project)
        record["project"]["source"] = _decode(record["project"].pop("source_json"))
        original = connection.execute("SELECT source_json,source_sha256 FROM item_sources WHERE record_id=?", (identifier,)).fetchone()
        record["source"] = _decode(original[0]) if original else {}
        record["source_sha256"] = original[1] if original else ""
        record["tables"] = []
        for entry in connection.execute(
                "SELECT t.id,t.title,t.uri,t.source_sha256,t.fields_json,c.ordinal,c.source_values "
                "FROM csv_rows c JOIN csv_tables t ON t.id=c.table_id WHERE c.record_id=? ORDER BY t.id,c.ordinal", (identifier,)):
            values = _decode(entry["source_values"])
            record["tables"].append({"id": entry["id"], "title": entry["title"], "uri": entry["uri"],
                                     "sha256": entry["source_sha256"], "row": entry["ordinal"],
                                     "fields": dict(zip(json.loads(entry["fields_json"]), values))})
        summary = connection.execute("SELECT source_json FROM query_summaries WHERE record_id=?", (identifier,)).fetchone()
        record["query_summary"] = _decode(summary[0]) if summary else {}
        record["definitions"] = {}
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name='definition_aliases'").fetchone():
            aliases = {key for observation in record["source"].get("oc-gen:has-obs", [])
                       for key in observation if key.startswith("oc-pred:")}
            aliases.update(match[1] for table in record["tables"] for key in table["fields"]
                           if (match := re.search(r"\[(https://opencontext\.org/predicates/[0-9a-f-]+)\]", key)))
            ordered = sorted(aliases)
            for start in range(0, len(ordered), 500):
                selected = ordered[start:start + 500]
                placeholders = ",".join("?" for _ in selected)
                for alias, blob in connection.execute(
                        "SELECT a.alias,d.source_json FROM definition_aliases a JOIN field_definitions d "
                        "ON d.id=a.definition_id WHERE a.alias IN (" + placeholders + ")", selected):  # nosec B608
                    record["definitions"][alias] = _decode(blob)
    record["observations"] = record["source"].get("oc-gen:has-obs", [])
    record.pop("search_text")
    record.pop("rowid")
    return record


def facts(record):
    rows = [("Published record", record["category"]), ("Project", record["project"]["title"])]
    if record["context_label"]:
        rows.append(("Recorded context", record["context_label"]))
    source = record["source"]
    authors = "; ".join(value["label"] for value in (source or record["project"]["source"]).get("dc-terms:creator", []) if value.get("label"))
    if authors:
        rows.append(("Source authors", authors))
    if source:
        rows.append(("Original observation groups", str(len(record["observations"]))))
        # A concise overview; all other fields remain available under the original groups.
        selected = ("definition", "description", "interpretation", "stage-description", "class", "sieving", "ceramics-count", "sample-count")
        for obs in record["observations"]:
            for key, values in obs.items():
                if key.startswith("oc-pred:") and re.sub(r"^\d+-", "", key.partition(":")[2]) in selected:
                    text = "; ".join(value_text(value) for value in values)
                    # The original group below retains long prose in full.
                    if key.endswith(("-description", "-interpretation")) and len(text) > 800:
                        text = text[:800].rsplit(" ", 1)[0] + "… (complete text in the original observation)"
                    label = record.get("definitions", {}).get(key, {}).get("label") or field_label(key)
                    rows.append((label + " · " + obs.get("label", obs["id"]), text))
    elif record["tables"]:
        rows.append(("Evidence available", "Original published table fields"))
    else:
        rows.append(("Evidence available", "Publisher query summary; no original observation document in this collection"))
    if record["dataset"] == "ekas" and record["category"] == "Survey Unit":
        for table in record["tables"]:
            if table["id"] != SURVEY_PROCEDURES:
                continue
            for key, value in table["fields"].items():
                label = key.split(" [", 1)[0]
                if label in ("Class", "Total Count", "Transect-Count", "Area"):
                    match = re.search(r"\[(https://opencontext\.org/predicates/[0-9a-f-]+)\]", key)
                    definition = record.get("definitions", {}).get(match[1], {}) if match else {}
                    units = [entry["label"] for entry in definition.get("rdfs:range", [])
                             if entry.get("slug", "").startswith("units-") and entry.get("label")]
                    if units:
                        label += " (" + "; ".join(units) + ")"
                    rows.append(("Survey procedure · " + label, value if value != "" else "Not recorded"))
    return rows


def location_time_fields(record):
    """Show publisher reference/precision metadata without inventing accuracy."""
    groups = []
    for feature in record["source"].get("features", []):
        properties, when = feature.get("properties") or {}, feature.get("when") or {}
        geometry = feature.get("geometry") or {}
        fields = []
        for key, label in (("reference_type", "Location reference"), ("location_precision_note", "Source location precision")):
            if properties.get(key):
                fields.append((label, properties[key]))
        if geometry.get("type"):
            fields.append(("Published geometry", geometry["type"]))
        for key, label in (("start", "Source start (ISO years)"), ("stop", "Source stop (ISO years)"),
                           ("reference_type", "Time reference")):
            if when.get(key) is not None:
                fields.append((label, str(when[key])))
        if fields:
            groups.append(fields)
    return groups


def definition_fields(record):
    """Return original field notes/ranges with attribution; each definition once."""
    groups, seen = [], set()
    for definition in record.get("definitions", {}).values():
        if definition["id"] in seen:
            continue
        seen.add(definition["id"])
        fields = [("Source definition", value_text(value)) for value in definition.get("skos:note", [])]
        fields.extend(("Source range or unit", value_text(value)) for value in definition.get("rdfs:range", []))
        if fields:
            groups.append({"label": definition["label"], "fields": fields, "source_uri": definition["id"]})
    return groups


def relationships(record):
    """Navigate exact source identities within their project, never matching labels."""
    path = database()
    if path is None:
        return []
    identifier, dataset = record["id"], record["dataset"]
    links = []

    def add(key, label, parameters):
        result = search(dataset=dataset, **parameters)
        if result["total"]:
            links.append({"key": key, "label": label, "total": result["total"],
                          "parameters": {"collection": "contexts", "dataset": dataset, **parameters}})

    if record["parent_id"]:
        add("parent", "Recorded parent context", {"scope": "record", "record_id": record["parent_id"]})
    add("children", "Records in this context", {"scope": "children", "record_id": identifier})
    with closing(_connect(path)) as connection:
        predicates = connection.execute("SELECT DISTINCT predicate FROM relationships WHERE source_id=? ORDER BY predicate", (identifier,)).fetchall()
        incoming = connection.execute("SELECT 1 FROM relationships WHERE target_id=? LIMIT 1", (identifier,)).fetchone()
    for (predicate,) in predicates:
        label = record.get("definitions", {}).get(predicate, {}).get("label") or field_label(predicate)
        add("target:" + predicate, "Source link: " + label,
            {"scope": "targets", "record_id": identifier, "predicate": predicate})
    if incoming:
        add("incoming", "Records linking to this context", {"scope": "incoming", "record_id": identifier})
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose a record from the installed excavation and survey collection.")
    lines = ["# Published excavation or survey reference — " + _md(record["title"]), ""]
    lines.extend("- " + label + ": " + _md(value) for label, value in facts(record))
    lines += ["", "Source record: " + record["source_uri"], "Project: " + record["project"]["uri"],
              "Data rights: " + record["project"]["license"],
              "Original item SHA256: " + record["source_sha256"] if record["source_sha256"] else "Original evidence: publisher table fields",
              "", "Original zero, false and blank values retain their separate meanings.",
              "Typed source links preserve the original predicate; free text is not a deposit ordering."]
    for fields in location_time_fields(record):
        lines.extend(["", "## Published location and time", ""])
        lines.extend("- " + label + ": " + _md(value) for label, value in fields)
        lines.append("Original publisher ISO years use 0000 for 1 BCE. Inferred locations do not become individual find GPS positions.")
    for table in record["tables"]:
        lines.extend(["", "Source table: " + _md(table["title"]), table["uri"],
                      "Table SHA256: " + table["sha256"], "Original row: " + str(table["row"])])
    entry = {"id": hashlib.sha256(("opencontext-subject:" + identifier + "\n" + "\n".join(lines)).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Published evidence · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published excavation or survey reference", "source": record["source_uri"],
                         "outcome": record["category"]}, "markdown": "\n".join(lines)}
    validate_book({"version": 1, "entries": [entry]})
    return entry
