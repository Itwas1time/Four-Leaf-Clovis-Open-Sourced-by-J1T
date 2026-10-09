"""Read original zooarchaeological subjects, context references and table rows."""
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
import zlib

from core.data_packs import PackStore

PACK = "anatolian-zooarchaeology"
PAGE_SIZE = 24
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
UUID_RE = re.compile(UUID + r"\Z")
TOKEN = r"[A-Za-z0-9][A-Za-z0-9_.~-]{0,79}"
TOKEN_RE = re.compile(TOKEN + r"\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
RECORD_RE = re.compile(r"(?:(?:subject|context):" + TOKEN + r"|row:[0-9a-f]{64}:[1-9][0-9]{0,11})\Z")
VIEWS = {"subject": "Zooarchaeological subject", "context": "Published context reference", "row": "Original scientific table row"}
SOURCE = "https://github.com/ekansa/opencontext-eol-zooarch"
LICENSE = "CC BY 3.0 source repository edition; original contributor attribution retained"


def published_identifier(uri, kind="subjects"):
    """Keep legacy publisher IDs literally; canonicalize only hexadecimal UUIDs."""
    parsed = urlsplit(uri)
    prefix = "/" + kind + "/"
    if (parsed.scheme not in ("http", "https") or parsed.hostname != "opencontext.org"
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.path.startswith(prefix)):
        return None
    identifier = parsed.path[len(prefix):].removesuffix("/")
    if not TOKEN_RE.fullmatch(identifier):
        return None
    return identifier.lower() if UUID_RE.fullmatch(identifier.lower()) else identifier


def databases():
    store = PackStore()
    if PACK not in {row["id"] for row in store.definitions}:
        return None
    paths = tuple(store.resolve_file(PACK, name) for name in ("reader.sqlite", "specimens.sqlite"))
    return paths if all(paths) else None


def database():
    paths = databases()
    return paths[0] if paths else None


def _connect(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA temp_store=MEMORY")
    return connection


def value_text(value):
    """Show unknown encoding bytes explicitly without guessing their characters."""
    if value == "":
        return "Not recorded (blank)"
    return re.sub(r"[\udc80-\udcff]", lambda match: "\\x" + format(ord(match[0]) - 0xDC00, "02X"), str(value))


def original_fields(headers, values):
    """Retain ordered, repeated column names and extra/missing source cells."""
    result = []
    for position in range(max(len(headers), len(values))):
        name = headers[position] if position < len(headers) else "Additional source cell " + str(position + 1)
        if position < len(headers) and headers.count(name) > 1:
            name += " [column " + str(position + 1) + "]"
        result.append((value_text(name), value_text(values[position]) if position < len(values) else "Cell absent in this source row"))
    return result


def row_label(headers, values):
    fields = dict(zip(headers, values))
    title = fields.get("Item label") or fields.get("Open Context URI") or "Original source row"
    context = " / ".join(fields.get("Context (" + str(index) + ")", "") for index in range(1, 7)
                         if fields.get("Context (" + str(index) + ")"))
    project = fields.get("Project name", "")
    return value_text(title), value_text(" · ".join(part for part in (project, context) if part)), value_text(context)


def validate_parameters(query="", page=1, view="all", subject_id="", context_id="", table_sha="", project_id="", record_id=""):
    values = (query, view, subject_id, context_id, table_sha, project_id, record_id)
    if (any(not isinstance(value, str) or len(value) > 120 or
            any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value) for value in values)
            or type(page) is not int or not 1 <= page <= 100_000
            or view not in ("all", "rows", *VIEWS)
            or any(value and not TOKEN_RE.fullmatch(value) for value in (subject_id, context_id, project_id))
            or table_sha and not SHA_RE.fullmatch(table_sha)
            or record_id and not RECORD_RE.fullmatch(record_id)):
        raise ValueError("Choose original zooarchaeological identifiers or a published table association.")


def stats():
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def _conditions(query, subject_id, context_id, table_sha, project_id):
    conditions, parameters = [], []
    candidate = published_identifier(query.strip()) or published_identifier(query.strip(), "projects")
    exact = candidate or (query.strip().lower() if UUID_RE.fullmatch(query.strip().lower()) else None)
    if not exact and re.fullmatch(r"TEST(?:SPA|SCA|PRJ)[0-9]+", query.strip()):
        exact = query.strip()
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if exact:
        conditions.append("(i.subject_id=? OR i.context_id=? OR i.project_id=?)")
        parameters.extend([exact, exact, exact])
    elif terms:
        conditions.append("i.rowid IN (SELECT rowid FROM source_fts WHERE source_fts MATCH ?)")
        parameters.append(" AND ".join('"' + term + '"*' for term in terms))
    for condition, value in (("i.subject_id=?", subject_id), ("i.context_id=?", context_id),
                             ("i.table_id=(SELECT id FROM source_tables WHERE sha256=?)", table_sha), ("i.project_id=?", project_id)):
        if value:
            conditions.append(condition)
            parameters.append(value)
    return " AND ".join(conditions) or "1", parameters


def search(query="", page=1, view="all", subject_id="", context_id="", table_sha="", project_id="", record_id=""):
    validate_parameters(query, page, view, subject_id, context_id, table_sha, project_id, record_id)
    path = database()
    if path is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1, "installed": False}
    where, parameters = _conditions(query, subject_id, context_id, table_sha, project_id)
    clauses, tail = [], []
    if view == "rows":
        source = "source_index r"
    else:
        source = "records r"
        if view in VIEWS:
            clauses.append("r.kind=?")
            tail.append(view)
    if record_id:
        if view == "rows" and record_id.startswith("row:"):
            _, sha, ordinal = record_id.split(":")
            clauses.extend(("r.table_id=(SELECT id FROM source_tables WHERE sha256=?)", "r.ordinal=?"))
            tail.extend([sha, int(ordinal)])
        elif view == "rows":
            clauses.append("0")
        else:
            clauses.append("r.id=?")
            tail.append(record_id)
    condition = " AND ".join(clauses) or "1"
    # Fixed internal SQL fragments above; all caller values are bound parameters.
    sql = "SELECT {columns} FROM " + source + " WHERE " + condition  # nosec B608
    if query.strip() or any((subject_id, context_id, table_sha, project_id)):
        paths = databases()
        signature = tuple((str(file), file.stat().st_mtime_ns, file.stat().st_ctime_ns, file.stat().st_size) for file in paths)
        matched = _matched_rows(str(path), where, tuple(parameters), signature, view, record_id)
        total = len(matched)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        selected = matched[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        table = "source_index" if view == "rows" else "records"
        with closing(_connect(path)) as connection:
            # A page has at most 24 source ordinals; no query or record cap.
            statement = "SELECT * FROM " + table + " WHERE rowid IN (" + ",".join("?" for _ in selected) + ") ORDER BY rowid"  # nosec B608: fixed tables/bound ordinals
            rows = [dict(row) for row in connection.execute(statement, selected)] if selected else []
    else:
        with closing(_connect(path)) as connection:
            total = connection.execute(sql.format(columns="count(*)"), tail).fetchone()[0]
            pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            page = min(page, pages)
            rows = [dict(row) for row in connection.execute(sql.format(columns="r.*") + " ORDER BY r.rowid LIMIT ? OFFSET ?",
                        tail + [PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    if view == "rows":
        with closing(_connect(databases()[1])) as native:
            for row in rows:
                edition = _edition(native, row["table_id"], row["ordinal"])
                row["id"] = "row:" + edition["table"]["sha256"] + ":" + str(row["ordinal"])
                row["title"], row["subtitle"], _ = row_label(edition["headers"], edition["values"])
    for row in rows:
        row["category"] = VIEWS["row" if view == "rows" else row["kind"]]
    return {"rows": rows, "total": total, "page": page, "pages": pages, "installed": True}


@lru_cache(maxsize=8)
def _matched_rows(path, where, parameters, signature, view, record_id):
    """Keep complete integer ordinals for paging, invalidated by both files."""
    with closing(_connect(Path(path))) as connection:
        target = None
        if record_id:
            if view == "rows":
                if not record_id.startswith("row:"):
                    return ()
                _, sha, ordinal = record_id.split(":")
                row = connection.execute("SELECT rowid FROM source_index WHERE table_id=(SELECT id FROM source_tables WHERE sha256=?) AND ordinal=?", (sha, int(ordinal))).fetchone()
            else:
                row = connection.execute("SELECT rowid,kind FROM records WHERE id=?", (record_id,)).fetchone()
                if row and view in VIEWS and row["kind"] != view:
                    return ()
            if row is None:
                return ()
            target = row[0]
        if view == "rows":
            columns, source = "i.rowid", "source_index i"
        else:
            columns = {"subject": "l.subject_rowid", "context": "l.context_rowid", "row": "l.aggregate_rowid"}.get(
                view, "l.subject_rowid,l.context_rowid,l.aggregate_rowid")
            source = "source_links l"
            # Text-only searches already identify exact original row ordinals.
            # Read their compact numeric links without reopening the URI index.
            if where == "i.rowid IN (SELECT rowid FROM source_fts WHERE source_fts MATCH ?)":
                where = "l.rowid IN (SELECT rowid FROM source_fts WHERE source_fts MATCH ?)"
            elif where != "1":
                where = "l.rowid IN (SELECT i.rowid FROM source_index i WHERE " + where + ")"  # nosec B608
        # Columns/tables/clauses are internal constants; all source values are bound.
        statement = "SELECT " + columns + " FROM " + source + " WHERE " + where  # nosec B608
        matched = set()
        for row in connection.execute(statement, parameters):
            if target is not None:
                if target in row:
                    return (target,)
            else:
                matched.update(value for value in row if value is not None)
        return tuple(sorted(matched))


def _edition(native, table_id, ordinal):
    table = dict(native.execute("SELECT * FROM table_editions WHERE id=?", (table_id,)).fetchone())
    row = native.execute("SELECT * FROM row_editions WHERE table_id=? AND ordinal=?", (table_id, ordinal)).fetchone()
    values = json.loads(zlib.decompress(row["source_values"]))
    headers = json.loads(table["headers_json"])
    def field(name):
        return values[headers.index(name)] if name in headers and headers.index(name) < len(values) else ""
    return {"table": table, "ordinal": ordinal, "headers": headers, "values": values,
            "fields": original_fields(headers, values), "subject_id": row["subject_id"], "context_id": row["context_id"],
            "original_item_uri": field("Open Context URI"), "original_context_uri": field("Context URI"),
            "original_project_uri": field("Project URI"), "project_id": row["project_id"]}


def get_record(identifier):
    if not isinstance(identifier, str) or not RECORD_RE.fullmatch(identifier):
        return None
    paths = databases()
    if paths is None:
        return None
    with closing(_connect(paths[0])) as reader, closing(_connect(paths[1])) as native:
        is_row = identifier.startswith("row:")
        if is_row:
            _, sha, ordinal = identifier.split(":")
            record = reader.execute("SELECT * FROM source_index WHERE table_id=(SELECT id FROM source_tables WHERE sha256=?) AND ordinal=?", (sha, int(ordinal))).fetchone()
        else:
            record = reader.execute("SELECT * FROM records WHERE id=?", (identifier,)).fetchone()
        if record is None:
            return None
        result = dict(record)
        result["kind"] = "row" if is_row else record["kind"]
        result["category"] = VIEWS[result["kind"]]
        result["summary"] = json.loads(reader.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
        result["representative"] = _edition(native, record["table_id"], record["ordinal"])
        if is_row:
            result["id"] = identifier
            result["title"], result["subtitle"], _ = row_label(result["representative"]["headers"], result["representative"]["values"])
        if result["kind"] == "subject":
            originals = native.execute("SELECT table_id,ordinal FROM row_editions WHERE subject_id=? ORDER BY table_id,ordinal", (record["source_id"],)).fetchall()
            result["editions"] = [_edition(native, row[0], row[1]) for row in originals]
        elif is_row:
            result["editions"] = [result["representative"]]
        else:
            # Contexts are references inside the CSVs, not independent unit documents.
            result["editions"] = []
        result["source_url"] = ("https://opencontext.org/subjects/" + record["source_id"]
                                if not is_row else result["representative"]["table"]["source_url"])
    return result


def facts(record):
    rows = [(("Published identifier", record["source_id"]) if record["kind"] != "row" else
             ("Original table row", record["representative"]["table"]["path"] + " · row " + str(record["representative"]["ordinal"]))),
            ("Published context", record["subtitle"])]
    if record["kind"] == "context":
        rows.append(("Evidence available", "Context references in original specimen tables; no independent excavation-unit document is supplied by this collection."))
    else:
        rows.append(("Original source rows", str(len(record["editions"]))))
    edition = record["representative"]
    rows.extend((value_text(header), value_text(value)) for header, value in zip(edition["headers"], edition["values"])
                if value and header in ("Related person(s)", "Project name"))
    if record["kind"] != "context":
        seen = set()
        # Source study/recovery flags may be absent from a measurement table.
        # Read their actual editions and keep disagreement explicitly attributed.
        for original in record["editions"]:
            for header, value in zip(original["headers"], original["values"]):
                if (value and any(word in header.lower() for word in ("recovery", "recording", "nisp", "study"))
                        and (header, value) not in seen):
                    seen.add((header, value))
                    rows.append((value_text(header) + " · " + original["table"]["path"], value_text(value)))
        selected = [(header, value) for header, value in zip(edition["headers"], edition["values"])
                    if value and any(word in header.lower() for word in ("taxon", "anatom"))]
        rows.extend((value_text(key), value_text(value)) for key, value in selected[:6])
    rows.append(("Source edition", record["summary"]["source_release"]))
    return rows


def relationships(record):
    links = []
    def add(key, label, **scope):
        result = search(**scope)
        if result["total"]:
            links.append({"key": key, "label": label, "total": result["total"],
                          "parameters": {"collection": "specimens", **scope}})
    if record["kind"] == "context":
        add("children", "Subjects referenced in this context", view="subject", context_id=record["source_id"])
        add("source-rows", "Original table rows for this context", view="rows", context_id=record["source_id"])
    elif record["kind"] == "subject":
        add("parent", "Recorded context references", view="context", subject_id=record["source_id"])
        add("source-rows", "Original table rows and measurements", view="rows", subject_id=record["source_id"])
    else:
        edition = record["representative"]
        if edition["subject_id"]:
            add("subject", "Published subject", record_id="subject:" + edition["subject_id"])
        if edition["context_id"]:
            add("parent", "Recorded context reference", record_id="context:" + edition["context_id"])
        add("source-rows", "This original table edition", view="rows", table_sha=edition["table"]["sha256"])
    return links


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError("Choose an installed zooarchaeological source record.")
    lines = ["# Zooarchaeological source reference — " + _md(record["title"]), ""]
    lines.extend("- " + _md(label) + ": " + _md(value) for label, value in facts(record))
    lines += ["", record["source_url"], "Data rights: " + LICENSE]
    for edition in record["editions"] or [record["representative"]]:
        lines += ["", "Source table: " + _md(edition["table"]["path"]), edition["table"]["source_url"],
                  "SHA-256: " + edition["table"]["sha256"], "Original row: " + str(edition["ordinal"])]
    for name in ("quantity_note", "context_note", "sampling_note", "location_note", "encoding_note"):
        lines += ["", record["summary"][name]]
    markdown = "\n".join(lines)
    entry = {"id": hashlib.sha256(("zooarch:" + identifier + markdown).encode()).hexdigest()[:24],
             "kind": "investigation", "title": ("Zooarchaeology · " + record["title"]).encode()[:120].decode("utf-8", "ignore"),
             "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
             "summary": {"mission": "Published zooarchaeological reference", "source": record["source_url"], "outcome": record["category"]},
             "markdown": markdown}
    validate_book({"version": 1, "entries": [entry]})
    return entry
