"""Read source rows and qualified excavation associations from local data packs."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import zlib

from core.data_packs import PackStore

PACK = "excavation-assemblages"
PAGE_SIZE = 24
KINDS = {
    "field": "Field recording", "lithic": "Lithic analysis", "fauna": "Faunal analysis",
    "ochre": "Ochre analysis", "recovery": "Bulk recovery", "code": "Original recording codes",
    "layer": "Source stratigraphic order", "pottery": "Grouped pottery observation",
    "chronology": "Locus chronology", "annotation": "Source annotation or blank template",
    "fragment": "Refitting fragment", "blank": "Reconstructed refitting blank",
    "connection": "Published refit connection", "model": "3D specimen metadata",
    "deposit": "Recorded deposit", "survey": "Survey observation", "aggregate": "Published summary",
    "date": "Dating or calibration record", "laboratory": "Laboratory result", "document": "Publisher context record",
    "plant": "Plant remains", "sample": "Published sample or context column",
}
SHA = re.compile(r"[a-f0-9]{64}\Z")
ROW = re.compile(r"(?:row|column):[a-f0-9]{64}:[0-9]{1,3}:[1-9][0-9]{0,11}\Z")
TABLE = re.compile(r"[a-f0-9]{64}:[0-9]{1,3}\Z")
DATASETS = {"hoedjiespunt", "berenike-sikait", "fumane-refits", "fumane-models",
            "chengdu", "el-progreso", "khao-toh-chong", "madjedbebe",
            "giza-botany", "elephantine-botany", "mezber-plants", "indus-plants", "monte-castelo-plants",
            "cixwicen-birds", "cixwicen-bird-sorting", "cixwicen-fish", "cixwicen-charcoal",
            "locumba-recovery", "soro-wilamaya-evidence", "huaca-grande-deposits"}


def database():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    return store.resolve_file(PACK, "assemblages.sqlite")


def connect(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def value_text(value):
    if value == "":
        return "Not recorded (blank)"
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\udc80-\udcff]",
                  lambda match: "\\x" + format(ord(match[0]) - 0xDC00 if ord(match[0]) >= 0xDC80 else ord(match[0]), "02X"), str(value))


def original_fields(headers, values):
    result = []
    for index in range(max(len(headers), len(values))):
        name = headers[index] if index < len(headers) else "Additional source cell"
        if not name or headers.count(name) > 1:
            name = (name or "Unnamed source column") + " [column " + str(index + 1) + "]"
        result.append((value_text(name), value_text(values[index]) if index < len(values)
                       else "Cell absent in this source row"))
    return result


def decode(blob):
    return json.loads(zlib.decompress(blob))


def validate_parameters(query="", page=1, view="all", scope="", table_id="", dataset="", record_id=""):
    for value in (query, view, scope, table_id, dataset, record_id):
        if (not isinstance(value, str) or len(value) > 120 or
                any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
            raise ValueError("Choose an original assemblage record or source association.")
    if (type(page) is not int or not 1 <= page <= 1_000_000 or view not in ("all", *KINDS)
            or scope and not SHA.fullmatch(scope) or table_id and not TABLE.fullmatch(table_id)
            or dataset and dataset not in DATASETS or record_id and not ROW.fullmatch(record_id)):
        raise ValueError("Choose an original assemblage record or source association.")


def stats():
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def search(query="", page=1, view="all", scope="", table_id="", dataset="", record_id=""):
    validate_parameters(query, page, view, scope, table_id, dataset, record_id)
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    conditions, parameters = [], []
    for expression, value in (("r.kind=?", "" if view == "all" else view), ("r.table_id=?", table_id),
                               ("r.dataset=?", dataset), ("r.id=?", record_id)):
        if value:
            conditions.append(expression)
            parameters.append(value)
    if scope:
        conditions.append("r.rowid IN (SELECT record FROM record_scopes WHERE scope=?)")
        parameters.append(scope)
    literal = query.strip()
    if re.fullmatch(r"RF\.[bc]_[0-9]+", literal):
        key = hashlib.sha256(("fumane:full-artifact-id\0" + literal).encode()).hexdigest()
        conditions.append("r.rowid IN (SELECT record FROM record_scopes WHERE scope=?)")
        parameters.append(key)
    elif re.fullmatch(r"[A-Z]{1,3}[0-9]{1,3}-[0-9]+-[0-9]+", literal):
        key = hashlib.sha256(("hdp:recorded-id\0" + literal).encode()).hexdigest()
        conditions.append("r.rowid IN (SELECT record FROM record_scopes WHERE scope=? AND basis=?)")
        parameters.extend([key, "Exact source UNIQUE_ID."])
    elif re.findall(r"\w+", query, flags=re.UNICODE):
        terms = re.findall(r"\w+", query, flags=re.UNICODE)
        conditions.append("r.rowid IN (SELECT rowid FROM source_fts WHERE source_fts MATCH ?)")
        parameters.append(" AND ".join('"' + term + '"' + ("" if term.isdecimal() else "*") for term in terms))
    # All fragments are fixed internally; caller values are SQLite parameters.
    statement = " FROM records r WHERE " + (" AND ".join(conditions) or "1")  # nosec B608
    # Wide matrices match every taxon in their headings. Let a searched
    # observation or context reading appear before those summary rows, while
    # retaining all matches and their stable ordering across later pages.
    order = ("CASE WHEN r.kind IN ('aggregate','annotation') THEN 1 ELSE 0 END,r.rowid"
             if literal else "r.rowid")
    with closing(connect(path)) as connection:
        total = connection.execute("SELECT count(*)" + statement, parameters).fetchone()[0]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in connection.execute(
            "SELECT r.rowid,r.id,r.kind,r.title,r.subtitle" + statement + " ORDER BY " + order + " LIMIT ? OFFSET ?",
            parameters + [PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row["category"] = KINDS[row["kind"]]
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


def get_record(identifier):
    if not isinstance(identifier, str) or not ROW.fullmatch(identifier):
        return None
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        source = connection.execute("SELECT * FROM records WHERE id=?", (identifier,)).fetchone()
        if source is None:
            return None
        row = dict(source)
        row["table"] = dict(connection.execute("SELECT * FROM source_tables WHERE id=?", (row["table_id"],)).fetchone())
        row["file"] = dict(connection.execute("SELECT * FROM source_files WHERE id=?", (row["table"]["file_id"],)).fetchone())
        row["edition"] = json.loads(connection.execute("SELECT document FROM editions WHERE id=?", (row["dataset"],)).fetchone()[0])
        row["headers"] = json.loads(row["table"].pop("headers_json"))
        row["merges"] = json.loads(row["table"].pop("merges_json"))
        row["header_rows"] = decode(row["table"].pop("header_rows"))
        row["values"] = decode(row.pop("source_values"))
        row["cells"] = decode(row.pop("source_cells"))
        row["reading_facts"] = decode(row.pop("reading_facts"))
        attributes = row["cells"]["attributes"]
        display = attributes.get("display_headers")
        row["fields"] = original_fields(display if display is not None else row["headers"], row["values"])
        row["merged_anchors"] = []
        for merged in (() if attributes.get("orientation") == "column" or attributes.get("source_cell_format", "").startswith("word") else row["merges"]):
            match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)", merged)
            if match and int(match[2]) <= row["ordinal"] <= int(match[4]):
                reference = match[1] + match[2]
                anchor = connection.execute("SELECT source_cells FROM records WHERE table_id=? AND ordinal=? AND id LIKE 'row:%'",
                                            (row["table_id"], int(match[2]))).fetchone()
                if anchor:
                    for cell in decode(anchor[0])["cells"]:
                        if cell["ref"] == reference:
                            row["merged_anchors"].append({"range": merged, **cell})
        if row["cells"]["cells"] or attributes.get("orientation") == "column":
            present = set()
            for cell in row["cells"]["cells"]:
                if "field_index" in cell:
                    present.add(cell["field_index"])
                    continue
                letters = re.match(r"[A-Z]+", cell["ref"])[0]
                number = 0
                for letter in letters:
                    number = number * 26 + ord(letter) - 64
                present.add(number - 1)
            absent = "Cell absent in this source column" if attributes.get("orientation") == "column" else "Cell absent in this source row"
            row["fields"] = [(name, value if index in present else absent)
                             for index, (name, value) in enumerate(row["fields"])]
        row["associations"] = [dict(item) for item in connection.execute(
            "SELECT s.id,s.kind,s.label,m.basis FROM record_scopes m JOIN scopes s ON s.id=m.scope "
            "WHERE m.record=? ORDER BY s.kind,s.id,m.basis", (row["rowid"],))]
        row["summary"] = json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
    row["category"] = KINDS[row["kind"]]
    row["source_url"] = row["file"]["source_url"]
    publisher_uri = row["cells"]["attributes"].get("publisher_uri")
    if publisher_uri is None and row["dataset"] in ("chengdu", "el-progreso"):
        for name in ("Item URI", "URI"):
            if name in row["headers"] and row["headers"].index(name) < len(row["values"]):
                publisher_uri = row["values"][row["headers"].index(name)]
                break
    if isinstance(publisher_uri, str) and re.fullmatch(r"https?://opencontext\.org/subjects/[a-f0-9-]{36}", publisher_uri):
        row["source_url"] = "https://" + publisher_uri.split("://", 1)[1]
    return row


def source_locator(record):
    locator = record["file"]["path"]
    if record["table"]["sheet"]:
        locator += " · " + record["table"]["sheet"]
    attributes = record["cells"]["attributes"]
    axis = "column" if attributes.get("orientation") == "column" else "row"
    if axis == "column" and attributes.get("source_column_end_number"):
        return locator + " · columns " + str(record["ordinal"]) + "–" + str(attributes["source_column_end_number"])
    return locator + " · " + axis + " " + str(record["ordinal"])


def facts(record):
    label = "Original source column" if record["cells"]["attributes"].get("orientation") == "column" else "Original source row"
    if label == "Original source column" and record["cells"]["attributes"].get("source_column_end_number"):
        label = "Original source columns"
    return [("Study or site", record["site"]), *record["reading_facts"],
            (label, source_locator(record)),
            ("Contributors", "; ".join(record["edition"]["contributors"])),
            ("Source edition", record["edition"]["edition"])]


def relationships(record):
    links, seen = [], set()
    for item in record["associations"]:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        result = search(scope=item["id"])
        if result["total"] > 1:
            links.append({"key": item["kind"] + ":" + item["id"], "label": item["label"],
                          "total": result["total"], "parameters": {"collection": "field_assemblages", "scope": item["id"]}})
    result = search(table_id=record["table_id"])
    links.append({"key": "source-rows", "label": "All records in this source table", "total": result["total"],
                  "parameters": {"collection": "field_assemblages", "table_id": record["table_id"]}})
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose an installed assemblage source record.")
    lines = ["# Excavation source reference — " + _md(record["title"]), ""]
    lines.extend("- " + _md(label) + ": " + _md(value) for label, value in facts(record))
    lines += ["", record["source_url"], "SHA-256: " + record["file"]["sha256"],
              "Citation: " + record["edition"]["citation_url"], "Data rights: " + record["edition"]["license"]]
    lines.extend("\n" + note for note in record["edition"]["notes"])
    lines.extend("\nAssociation: " + _md(item["label"]) + " — " + _md(item["basis"]) for item in record["associations"])
    lines.append("\n" + record["summary"]["quantity_note"])
    markdown = "\n".join(lines)
    entry = {"id": hashlib.sha256(("assemblage:" + identifier + markdown).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Excavation · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published excavation reference", "source": record["source_url"], "outcome": record["category"]},
             "markdown": markdown}
    validate_book({"version": 1, "entries": [entry]})
    return entry
