"""Read original archaeological site-register editions without merging evidence."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
import zlib

from core.data_packs import PackStore

PACK = "north-american-sites"
PAGE_SIZE = 24
UUID = r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}"
SUBJECT = re.compile(r"https?://opencontext\.org/subjects/(" + UUID + r")", re.I)
EDITIONS = {"georgia-sites", "florida-sites", "florida-artifact-categories",
            "florida-diagnostic-artifacts", "coastal-model-sites"}
STATES = {"Alabama", "Florida", "Georgia", "Louisiana", "Maryland", "North Carolina",
          "South Carolina", "Virginia"}


def subject_id(value):
    match = SUBJECT.fullmatch(value) if isinstance(value, str) else None
    return match[1].lower() if match else ""


def encode(value):
    return zlib.compress(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode(), 6)


def decode(value):
    return json.loads(zlib.decompress(value))


def database():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    return store.resolve_file(PACK, "sites.sqlite")


def connect(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def stats():
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def validate_parameters(query="", page=1, context_id="", edition="", state=""):
    if (not isinstance(query, str) or len(query) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in query)
            or type(page) is not int or not 1 <= page <= 1_000_000
            or not isinstance(context_id, str) or context_id and not re.fullmatch(UUID, context_id)
            or edition not in ("", *EDITIONS) or state not in ("", *STATES)):
        raise ValueError("Choose an original site-register search or association.")


def search(query="", page=1, context_id="", edition="", state=""):
    validate_parameters(query, page, context_id, edition, state)
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    clauses, parameters = [], []
    identifier = subject_id(query.strip())
    if not identifier and re.fullmatch(UUID, query.strip(), re.I):
        identifier = query.strip().lower()
    if identifier:
        clauses.append("s.id=?")
        parameters.append(identifier)
    else:
        terms = re.findall(r"\w+", query, flags=re.UNICODE)
        if terms:
            clauses.append("s.rowid IN (SELECT r.site_key FROM source_fts f JOIN records r ON r.rowid=f.rowid WHERE source_fts MATCH ?)")
            parameters.append(" AND ".join('"' + term + '"*' for term in terms))
    if state:
        clauses.append("s.state=?")
        parameters.append(state)
    if context_id:
        clauses.append("s.rowid IN (SELECT site_key FROM records WHERE context_id=?)")
        parameters.append(context_id)
    if edition:
        clauses.append("s.rowid IN (SELECT site_key FROM records WHERE edition=?)")
        parameters.append(edition)
    statement = " FROM sites s WHERE " + (" AND ".join(clauses) or "1")  # nosec B608: fixed clauses, bound values
    with closing(connect(path)) as connection:
        total = connection.execute("SELECT count(*)" + statement, parameters).fetchone()[0]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in connection.execute(
            "SELECT s.id,s.title,s.subtitle" + statement + " ORDER BY s.rowid LIMIT ? OFFSET ?",
            [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row.update(id="site:" + row["id"], category="Archaeological site register")
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


def value_text(value):
    if value == "":
        return "Blank in source"
    return str(value).encode("utf-8", errors="backslashreplace").decode("utf-8")


def cell(edition, name):
    headers, values = edition["headers"], edition["values"]
    if name in headers:
        index = headers.index(name)
        if index < len(values):
            return values[index]
    return ""


def original_fields(edition):
    headers, values = edition["headers"], edition["values"]
    return [(str(index + 1) + " · " + header,
             value_text(values[index]) if index < len(values) else "Cell absent from this CSV row")
            for index, header in enumerate(headers)] + [
                ("Extra native column " + str(index + 1), value_text(value))
                for index, value in enumerate(values[len(headers):], len(headers))]


def period_values(edition):
    values = [cell(edition, name) for name in ("Period", "Culture", "Has period [Label]")]
    for index, header in enumerate(edition["headers"]):
        if (header.startswith("Has period :: ") and header.endswith(" [Has]")
                and index < len(edition["values"]) and edition["values"][index] == "True"):
            values.append(header.removeprefix("Has period :: ").removesuffix(" [Has]") + " (source flag: True)")
    return list(dict.fromkeys(value for value in values if value))


def rights_text(document):
    return "; ".join((row.get("label") or "Source license") + " · " + row.get("id", "")
                     for row in document.get("dc-terms:license", []))


def get_record(identifier):
    if not isinstance(identifier, str) or not re.fullmatch("site:" + UUID, identifier):
        return None
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        site = connection.execute("SELECT rowid,* FROM sites WHERE id=?", (identifier[5:],)).fetchone()
        if site is None:
            return None
        result = dict(site)
        editions = []
        for source in connection.execute("SELECT r.*,e.document,e.headers,e.source_file,e.sha256,e.source_url,e.priority "
                "FROM records r JOIN editions e ON e.id=r.edition WHERE r.site_key=? ORDER BY e.priority,r.ordinal", (site["rowid"],)):
            row = dict(source)
            row["metadata"] = decode(row.pop("document"))
            row["headers"] = decode(row["headers"])
            row["values"] = decode(row.pop("source_values"))
            row["rights"] = rights_text(row["metadata"])
            project_uri = cell(row, "Project URI")
            project_id = re.fullmatch(r"https?://opencontext\.org/projects/(" + UUID + r")", project_uri, re.I)
            project = connection.execute("SELECT document FROM projects WHERE id=?", (project_id[1].lower(),)).fetchone() if project_id else None
            row["project"] = decode(project[0]) if project else None
            # Adjacency is evidence about the malformed export, not a repaired field.
            row["adjacent_fragments"] = []
            if len(row["values"]) != len(row["headers"]):
                fragment = connection.execute("SELECT ordinal,line_start,line_end,source_values FROM records "
                    "WHERE edition=? AND ordinal=? AND site_key IS NULL", (row["edition"], row["ordinal"] + 1)).fetchone()
                if fragment:
                    row["adjacent_fragments"].append({**dict(fragment), "values": decode(fragment["source_values"])})
                    row["adjacent_fragments"][0].pop("source_values")
            editions.append(row)
        result["summary"] = json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
    result.update(id=identifier, category="Archaeological site register", editions=editions)
    return result


def edition_facts(edition):
    fields = [("Site name", ("Site name", "Site Name")), ("Original authorship", ("Authorship",)),
              ("Source project", ("Project",)), ("Site type", ("Site Type",)),
              ("Investigation date", ("Investigation Date",)), ("Collections held at", ("Location of Collections",)),
              ("Documentation held at", ("Location of Documentation",)), ("Report title", ("Report Title",)),
              ("Other reports", ("Other Reports",)), ("Collected artifacts (source)", ("Artifacts Collected",)),
              ("Preservation state", ("Preservation State",)), ("Deleted flag (source)", ("Deleted",)),
              ("Public status (source)", ("Public Status",)), ("Register status (source)", ("Register Status",))]
    facts = [(label, value_text(value)) for label, names in fields
             if (value := next((cell(edition, name) for name in names if cell(edition, name)), ""))]
    periods = period_values(edition)
    if periods:
        facts.append(("Periods (source)", "; ".join(periods)))
    for name in ("Early Date (BCE/CE)", "Late Date (BCE/CE)"):
        if cell(edition, name):
            facts.append((name + " (source)", cell(edition, name)))
    facts.extend([("Source table", edition["metadata"]["label"]),
                  ("Table rights (source)", edition["rights"]),
                  ("Original CSV record", str(edition["ordinal"])),
                  ("Original file SHA-256", edition["sha256"])])
    if len(edition["values"]) != len(edition["headers"]):
        facts.append(("Source row condition", f'{len(edition["values"])} of {len(edition["headers"])} columns present in this parsed CSV row. Adjacent fragments remain separate; no fields are repaired.'))
    return facts


def facts(record):
    return [("Published site identifier", record["id"][5:]), ("State", record["state"]),
            ("County context", record["county"]), ("Source table editions", str(len(record["editions"]))),
            *edition_facts(record["editions"][0])]


def relationships(record):
    links = []
    if record["context_id"]:
        total = search(context_id=record["context_id"])["total"]
        if total > 1:
            links.append({"key": "county", "label": "Sites in the same publisher county context",
                "total": total, "parameters": {"collection": "site_registers", "context_id": record["context_id"]}})
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose an installed archaeological site-register record.")
    lines = ["# Archaeological site reference · " + _md(record["title"]), "", record["source_url"], ""]
    lines.extend(record["summary"][key] for key in ("scope_note", "count_note", "location_note", "source_condition_note"))
    for edition in record["editions"]:
        document = edition["metadata"]
        lines.extend(["", "## " + _md(document["label"]), edition["source_url"],
            "CSV file in this collection: " + edition["source_file"],
            "CSV record: " + str(edition["ordinal"]),
            "Original file lines: " + str(edition["line_start"]) + "–" + str(edition["line_end"]),
            "Original SHA-256: " + edition["sha256"],
            "Table rights: " + _md(edition["rights"])])
        lines.extend(label + ": " + _md(document.get(key) or "Not recorded") for key, label in
                     (("dc-terms:issued", "Table issued"), ("dc-terms:modified", "Table modified")))
        for key, label in (("dc-terms:creator", "Table creators"), ("dc-terms:contributor", "Table contributors")):
            lines.append(label + ": " + _md("; ".join(row.get("label", row.get("id", "")) for row in document.get(key, []))))
        if edition["project"]:
            lines.append("Source project rights: " + _md(rights_text(edition["project"])))
        lines.extend("- " + _md(label) + ": " + _md(value) for label, value in original_fields(edition)
                     if value != "Blank in source")
        for fragment in edition["adjacent_fragments"]:
            lines.append("Adjacent unbound native CSV fragment, record " + str(fragment["ordinal"]) + "; original values: " + _md(json.dumps(fragment["values"], ensure_ascii=True)))
    lines.append("Original blank cells remain in the collection; absence is not a zero or a negative observation.")
    text = "\n".join(lines)
    entry = {"id": hashlib.sha256(("site-register:" + identifier + ":" + text).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Site reference · " + record["title"]).encode("utf-8")[:120].decode("utf-8", errors="ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published archaeological site reference", "source": record["source_url"], "outcome": identifier},
             "markdown": text}
    validate_book({"version": 1, "entries": [entry]})
    return entry
