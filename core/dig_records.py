"""Local excavation records with stable IDs, checked links and dated revisions.

User records live outside the installed package. Nothing here contacts a
publisher or turns a museum/reference record into an observed find.
"""
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import io
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

KINDS = {'unit': 'Unit / trench', 'context': 'Context', 'find': 'Find',
         'sample': 'Sample', 'source': 'Source document'}
CONTEXT_TYPES = ('unknown', 'deposit', 'cut', 'structure', 'interface')
UNITS = ('mm', 'cm', 'm', 'in', 'ft')
MAX_RECORDS = 20_000
MAX_BACKUP_BYTES = 32_000_000
MAX_BACKUP_ZIP_BYTES = 1_200_000
PAGE_SIZE = 24
COMMON = {'description': '', 'interpretation': '', 'recorder': '',
          'observed_date': '', 'source_ids': []}
EXTRA = {
    'unit': {},
    'context': {'unit_id': None, 'context_type': 'unknown', 'depth': '', 'depth_unit': '', 'datum': ''},
    'find': {'context_id': None, 'material': '', 'count': None, 'bag': '', 'depth': '', 'depth_unit': '', 'datum': ''},
    'sample': {'context_id': None, 'sample_type': '', 'method': '', 'bag': '', 'depth': '', 'depth_unit': '', 'datum': ''},
    'source': {'citation': '', 'url': ''},
}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{32}', value):
        raise ValueError('Choose a valid saved record.')
    return value


def _text(value, label, limit=4000, required=False):
    try:
        valid = isinstance(value, str) and len(value.encode('utf-8')) <= limit and '\x00' not in value
    except UnicodeError:
        valid = False
    if not valid:
        raise ValueError(f'{label} must be text of up to {limit} bytes.')
    value = value.strip()
    if required and not value:
        raise ValueError(f'Record {label.lower()}.')
    return value


def _stamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00', value):
        raise ValueError('A saved revision has an invalid date.')
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('A saved revision has an invalid date.') from None
    return value


def _data(value):
    if not isinstance(value, dict) or not isinstance(value.get('kind'), str) or value['kind'] not in KINDS:
        raise ValueError('Choose unit, context, find, sample or source.')
    kind = value['kind']
    defaults = {**COMMON, **EXTRA[kind]}
    if set(value) - {'kind', 'code', *defaults}:
        raise ValueError('This record contains unsupported fields.')
    data = {'kind': kind, 'code': _text(value.get('code'), 'Record code', 80, True)}
    for key, default in defaults.items():
        data[key] = value.get(key, default)
    for key in ('description', 'interpretation', 'recorder', 'observed_date'):
        data[key] = _text(data[key], key.replace('_', ' ').title(), 4000 if key in ('description', 'interpretation') else 120)
    if data['observed_date']:
        try:
            if date.fromisoformat(data['observed_date']).isoformat() != data['observed_date']:
                raise ValueError()
        except ValueError:
            raise ValueError('Use YYYY-MM-DD for the observation date, or leave it unknown.') from None
    source_ids = data['source_ids']
    if not isinstance(source_ids, list) or len(source_ids) > 20:
        raise ValueError('Choose up to 20 distinct source documents.')
    data['source_ids'] = [_id(identifier) for identifier in source_ids]
    if len(set(data['source_ids'])) != len(source_ids):
        raise ValueError('Choose distinct source documents.')
    for key in ('unit_id', 'context_id'):
        if key in data and data[key] is not None:
            _id(data[key])
    if kind == 'context' and data['context_type'] not in CONTEXT_TYPES:
        raise ValueError('Choose a recorded context type, or unknown.')
    if kind in ('context', 'find', 'sample'):
        data['depth'] = _text(data['depth'], 'Depth', 40)
        data['depth_unit'] = _text(data['depth_unit'], 'Depth unit', 10)
        data['datum'] = _text(data['datum'], 'Depth datum', 200)
        if data['depth']:
            try:
                number = Decimal(data['depth'])
                if not number.is_finite() or number < 0 or number > 10_000_000:
                    raise InvalidOperation()
            except InvalidOperation:
                raise ValueError('Depth below the datum must be a finite, nonnegative number.') from None
            if data['depth_unit'] not in UNITS or not data['datum']:
                raise ValueError('A measured depth needs its unit and named datum.')
        elif data['depth_unit'] or data['datum']:
            raise ValueError('Record the measured depth with its unit and datum, or leave all three unknown.')
    for key in ('material', 'bag', 'sample_type', 'method', 'citation', 'url'):
        if key in data:
            data[key] = _text(data[key], key.replace('_', ' ').title(), 4000 if key == 'citation' else 2000 if key == 'url' else 200)
    if kind == 'find' and data['count'] is not None and (type(data['count']) is not int or not 1 <= data['count'] <= 1_000_000):
        raise ValueError('Find count must be a positive whole number, or unknown.')
    if kind == 'source' and data['url']:
        try:
            parsed = urlsplit(data['url'])
            safe = (parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
                    and not parsed.password and parsed.port in (None, 443)
                    and not any(c.isspace() or ord(c) < 32 for c in data['url']))
        except ValueError:
            safe = False
        if not safe:
            raise ValueError('Use a complete HTTPS source link without credentials.')
    return data


def _links(data, records, own_id):
    for field, kind in (('unit_id', 'unit'), ('context_id', 'context')):
        identifier = data.get(field)
        if identifier and (identifier == own_id or identifier not in records or records[identifier]['data']['kind'] != kind):
            raise ValueError(f'Choose a saved {kind} in this project, or leave it unknown.')
    if any(identifier == own_id or identifier not in records or records[identifier]['data']['kind'] != 'source' for identifier in data['source_ids']):
        raise ValueError('Source links must refer to saved source documents in this project.')


def _sequence(relations):
    """Check directed sequence after grouping explicit same-as correlations."""
    parent = {}
    def root(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    for row in relations:
        if row['kind'] == 'same_as':
            parent[root(row['subject'])] = root(row['object'])
    graph = {}
    for row in relations:
        if row['kind'] == 'same_as':
            continue
        a, b = root(row['subject']), root(row['object'])
        if row['kind'] == 'below':
            a, b = b, a
        graph.setdefault(a, set()).add(b)
    indegree = {node: 0 for node in parent}
    for targets in graph.values():
        for node in targets:
            indegree[node] = indegree.get(node, 0) + 1
    queue = [node for node, count in indegree.items() if not count]
    checked = 0
    while queue:
        node = queue.pop()
        checked += 1
        for target in graph.get(node, ()):
            indegree[target] -= 1
            if not indegree[target]:
                queue.append(target)
    if checked != len(indegree):
        raise ValueError('These relationships form a circular sequence. Recheck the contexts before saving.')


class DigBook:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('CLOVIS_DIGBOOK_PATH') or Path.home() / 'Clovis Local' / 'dig-records.sqlite').resolve()

    @contextmanager
    def _connection(self, write=False):
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path if write else self.path.as_uri() + '?mode=ro', uri=not write, timeout=10)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if write and version == 0:
                if connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise ValueError('This file is not a Clovis dig record database.')
                connection.executescript('''
                    CREATE TABLE projects(id TEXT PRIMARY KEY, code TEXT NOT NULL, code_key TEXT UNIQUE NOT NULL, title TEXT NOT NULL, created TEXT NOT NULL);
                    CREATE TABLE records(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), kind TEXT NOT NULL, code_key TEXT NOT NULL, revision INTEGER NOT NULL, snapshot TEXT NOT NULL, UNIQUE(project_id,kind,code_key));
                    CREATE TABLE revisions(record_id TEXT NOT NULL REFERENCES records(id), revision INTEGER NOT NULL, snapshot TEXT NOT NULL, PRIMARY KEY(record_id,revision));
                    CREATE TABLE relations(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), snapshot TEXT NOT NULL);
                    CREATE TABLE relation_voids(relation_id TEXT PRIMARY KEY REFERENCES relations(id), reason TEXT NOT NULL, created TEXT NOT NULL);
                    PRAGMA user_version=1;
                ''')
                version = 1
            if version != 1:
                raise ValueError('This dig record database uses an unsupported version.')
            if write:
                connection.execute('BEGIN IMMEDIATE')
            try:
                yield connection
                if write:
                    connection.commit()
            except BaseException:
                if write:
                    connection.rollback()
                raise

    def projects(self):
        if not self.path.is_file():
            return []
        with self._connection() as connection:
            return [dict(row) for row in connection.execute('SELECT id,code,title,created FROM projects ORDER BY code_key')]

    def create_project(self, code, title):
        row = {'id': uuid4().hex, 'code': _text(code, 'Project code', 80, True),
               'title': _text(title, 'Project title', 200, True), 'created': _now()}
        with self._connection(True) as connection:
            try:
                connection.execute('INSERT INTO projects VALUES (?,?,?,?,?)', (row['id'], row['code'], row['code'].casefold(), row['title'], row['created']))
            except sqlite3.IntegrityError:
                raise ValueError('A project already uses that code.') from None
        return row

    @staticmethod
    def _records(connection, project):
        return {row['id']: json.loads(row['snapshot']) for row in connection.execute('SELECT id,snapshot FROM records WHERE project_id=?', (project,))}

    @staticmethod
    def _project(connection, identifier):
        row = connection.execute('SELECT id,code,title,created FROM projects WHERE id=?', (_id(identifier),)).fetchone()
        if not row:
            raise ValueError('Choose a saved project.')
        return dict(row)

    def records(self, project, kind='all', query='', page=1):
        if not self.path.is_file():
            return {'rows': [], 'total': 0, 'page': 1, 'pages': 1}
        if not isinstance(query, str) or len(query) > 120 or not isinstance(kind, str) or (kind != 'all' and kind not in KINDS):
            raise ValueError('Use a search of up to 120 characters and a valid record type.')
        with self._connection() as connection:
            self._project(connection, project)
            # Fixed clauses; every user value is a bound parameter.
            where = 'project_id=? AND (?=\'all\' OR kind=?) AND (?=\'\' OR instr(lower(snapshot),lower(?))>0)'
            params = (project, kind, kind, query, query)
            total = connection.execute('SELECT count(*) FROM records WHERE ' + where, params).fetchone()[0]  # nosec B608 # Fixed clause; all values are bound.
            pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
            page = min(pages, max(1, page if type(page) is int else 1))
            rows = connection.execute('SELECT snapshot FROM records WHERE ' + where + ' ORDER BY kind,code_key,id LIMIT ? OFFSET ?', (*params, PAGE_SIZE, (page - 1) * PAGE_SIZE)).fetchall()  # nosec B608 # Fixed clause and ordering; all values are bound.
            return {'rows': [json.loads(row[0]) for row in rows], 'total': total, 'page': page, 'pages': pages}

    def get(self, project, identifier):
        if not self.path.is_file():
            return None
        with self._connection() as connection:
            row = connection.execute('SELECT snapshot FROM records WHERE project_id=? AND id=?', (_id(project), _id(identifier))).fetchone()
            return json.loads(row[0]) if row else None

    def options(self, project, kind, query='', selected=None):
        if not project or not self.path.is_file():
            return []
        if not isinstance(kind, str) or kind not in KINDS or not isinstance(query, str) or len(query) > 120:
            raise ValueError('Use a valid record search.')
        with self._connection() as connection:
            rows = connection.execute('SELECT id,snapshot FROM records WHERE project_id=? AND kind=? AND (?=\'\' OR instr(code_key,lower(?))>0 OR id=?) ORDER BY code_key LIMIT 100', (_id(project), kind, query, query, selected or '')).fetchall()
            result = {row['id']: json.loads(row['snapshot'])['data']['code'] for row in rows}
            if selected and selected not in result:
                row = connection.execute('SELECT id,snapshot FROM records WHERE project_id=? AND kind=? AND id=?', (project, kind, selected)).fetchone()
                if row:
                    result[row['id']] = json.loads(row['snapshot'])['data']['code']
            return [{'value': identifier, 'label': code} for identifier, code in result.items()]

    def save(self, project, value, identifier=None, expected_revision=None):
        data = _data(value)
        with self._connection(True) as connection:
            self._project(connection, project)
            records = self._records(connection, project)
            old = records.get(_id(identifier)) if identifier else None
            if identifier and not old:
                raise ValueError('The selected record does not belong to this project.')
            if old and (type(expected_revision) is not int or old['revision'] != expected_revision):
                raise ValueError('This record changed since it was opened. Reopen it before saving your correction.')
            if old and old['data']['kind'] != data['kind']:
                raise ValueError('A saved record keeps its record type. Create a separate record for another type.')
            identifier = identifier or uuid4().hex
            _links(data, records, identifier)
            if not old and len(records) >= MAX_RECORDS:
                raise ValueError('This project reached its 20,000-record limit. Export a backup.')
            if old and data == old['data']:
                return old
            now = _now()
            row = {'id': identifier, 'project_id': project, 'revision': old['revision'] + 1 if old else 1,
                   'created': old['created'] if old else now, 'updated': now, 'data': data}
            snapshot = json.dumps(row, ensure_ascii=False, allow_nan=False)
            try:
                if old:
                    connection.execute('UPDATE records SET code_key=?,revision=?,snapshot=? WHERE id=?', (data['code'].casefold(), row['revision'], snapshot, identifier))
                else:
                    connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', (identifier, project, data['kind'], data['code'].casefold(), row['revision'], snapshot))
                connection.execute('INSERT INTO revisions VALUES (?,?,?)', (identifier, row['revision'], snapshot))
            except sqlite3.IntegrityError:
                raise ValueError('This project already uses that code for this record type.') from None
            return row

    def history(self, project, identifier):
        if not self.path.is_file():
            return []
        with self._connection() as connection:
            return [json.loads(row[0]) for row in connection.execute('SELECT v.snapshot FROM revisions v JOIN records r ON r.id=v.record_id WHERE r.project_id=? AND r.id=? ORDER BY v.revision', (_id(project), _id(identifier)))]

    @staticmethod
    def _relations(connection, project, active=True):
        result = []
        for row in connection.execute('SELECT r.snapshot,v.reason,v.created AS voided FROM relations r LEFT JOIN relation_voids v ON r.id=v.relation_id WHERE r.project_id=? ORDER BY r.id', (project,)):
            value = json.loads(row['snapshot'])
            if row['voided']:
                value['void'] = {'reason': row['reason'], 'created': row['voided']}
            if not active or 'void' not in value:
                result.append(value)
        return result

    def relations(self, project, query=''):
        if not self.path.is_file():
            return []
        query = _text(query, 'Relationship search', 120).casefold()
        with self._connection() as connection:
            self._project(connection, project)
            rows = self._relations(connection, project, False)
            if not query:
                return rows
            records = self._records(connection, project)
            return [row for row in rows if query in ' '.join((records[row['subject']]['data']['code'],
                    records[row['object']]['data']['code'], row['note'], row.get('void', {}).get('reason', ''))).casefold()]

    def relate(self, project, subject, kind, object_id, note=''):
        if kind not in ('above', 'below', 'same_as') or subject == object_id:
            raise ValueError('Choose two distinct contexts and above, below or same as.')
        row = {'id': uuid4().hex, 'project_id': _id(project), 'subject': _id(subject),
               'kind': kind, 'object': _id(object_id), 'note': _text(note, 'Relationship note', 2000), 'created': _now()}
        with self._connection(True) as connection:
            records = self._records(connection, project)
            if any(identifier not in records or records[identifier]['data']['kind'] != 'context' for identifier in (subject, object_id)):
                raise ValueError('Both contexts must belong to this project.')
            current = self._relations(connection, project)
            if any((r['subject'], r['kind'], r['object']) == (subject, kind, object_id) for r in current):
                raise ValueError('That relationship is already recorded.')
            _sequence([*current, row])
            connection.execute('INSERT INTO relations VALUES (?,?,?)', (row['id'], project, json.dumps(row, ensure_ascii=False)))
        return row

    def void_relation(self, project, identifier, reason):
        reason = _text(reason, 'Reason for correction', 2000, True)
        with self._connection(True) as connection:
            row = connection.execute('SELECT id FROM relations WHERE id=? AND project_id=?', (_id(identifier), _id(project))).fetchone()
            if not row:
                raise ValueError('Choose a relationship in this project.')
            try:
                connection.execute('INSERT INTO relation_voids VALUES (?,?,?)', (identifier, reason, _now()))
            except sqlite3.IntegrityError:
                raise ValueError('This relationship was already voided.') from None

    def export(self, project):
        with self._connection() as connection:
            connection.execute('BEGIN')
            bundle = {'format': 'clovis-dig-records', 'version': 1, 'project': self._project(connection, project),
                      'records': list(self._records(connection, project).values()),
                      'revisions': [json.loads(row[0]) for row in connection.execute('SELECT v.snapshot FROM revisions v JOIN records r ON r.id=v.record_id WHERE r.project_id=? ORDER BY v.record_id,v.revision', (project,))],
                      'relations': self._relations(connection, project, False)}
            encoded = json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2)
            if len(encoded.encode('utf-8')) > MAX_BACKUP_BYTES:
                raise ValueError('This full revision backup exceeds 32 MB. Preserve the local database and start a separate project for further records.')
            return encoded

    def backup_bytes(self, project):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr('dig-records.json', self.export(project).encode('utf-8'))
        data = stream.getvalue()
        if len(data) > MAX_BACKUP_ZIP_BYTES:
            raise ValueError('This portable backup exceeds 1.2 MB compressed. Preserve the local database; no saved records were removed.')
        return data

    def restore_backup(self, data):
        if not isinstance(data, bytes) or len(data) > MAX_BACKUP_ZIP_BYTES:
            raise ValueError('Use a dig-record ZIP backup of up to 1.2 MB.')
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if len(archive.infolist()) != 1 or archive.namelist() != ['dig-records.json']:
                    raise ValueError('The ZIP must contain only dig-records.json.')
                info = archive.infolist()[0]
                if info.file_size > MAX_BACKUP_BYTES or info.flag_bits & 1:
                    raise ValueError('The backup is oversized or encrypted.')
                with archive.open(info) as member:
                    encoded = member.read(MAX_BACKUP_BYTES + 1)
                if len(encoded) > MAX_BACKUP_BYTES:
                    raise ValueError('The expanded backup is oversized.')
                text = encoded.decode('utf-8')
        except (zipfile.BadZipFile, UnicodeError, RuntimeError, NotImplementedError):
            raise ValueError('Use a valid, unencrypted Clovis dig-record ZIP backup.') from None
        return self.restore(text)

    def restore(self, encoded):
        """Merge a checked shared revision prefix atomically; reject divergence."""
        if not isinstance(encoded, str) or len(encoded.encode('utf-8')) > MAX_BACKUP_BYTES:
            raise ValueError('Use a dig-record backup of up to 32 MB.')
        try:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('The backup repeats a JSON field.')
                    result[key] = value
                return result
            bundle = json.loads(encoded, object_pairs_hook=unique)
        except (ValueError, RecursionError):
            raise ValueError('Use a valid Clovis dig-record JSON backup.') from None
        if (not isinstance(bundle, dict) or set(bundle) != {'format', 'version', 'project', 'records', 'revisions', 'relations'}
                or bundle['format'] != 'clovis-dig-records' or type(bundle['version']) is not int or bundle['version'] != 1):
            raise ValueError('This is not a supported dig-record backup.')
        project = bundle['project']
        if not isinstance(project, dict) or set(project) != {'id', 'code', 'title', 'created'}:
            raise ValueError('The backup has an invalid project.')
        project = {'id': _id(project['id']), 'code': _text(project['code'], 'Project code', 80, True),
                   'title': _text(project['title'], 'Project title', 200, True), 'created': _stamp(project['created'])}
        for key, limit in (('records', MAX_RECORDS), ('revisions', MAX_RECORDS * 20), ('relations', MAX_RECORDS * 10)):
            if not isinstance(bundle[key], list) or len(bundle[key]) > limit:
                raise ValueError('The backup has too many or invalid records.')
        records, histories, codes = {}, {}, set()
        def checked(row):
            if not isinstance(row, dict) or set(row) != {'id', 'project_id', 'revision', 'created', 'updated', 'data'}:
                raise ValueError('The backup has an unsupported record.')
            if row['project_id'] != project['id'] or type(row['revision']) is not int or not 1 <= row['revision'] <= 100_000:
                raise ValueError('The backup has an invalid record revision or project link.')
            return {**row, 'id': _id(row['id']), 'created': _stamp(row['created']), 'updated': _stamp(row['updated']), 'data': _data(row['data'])}
        for raw in bundle['records']:
            row = checked(raw)
            code = (row['data']['kind'], row['data']['code'].casefold())
            if row['id'] in records or code in codes:
                raise ValueError('The backup repeats a record identifier or code.')
            records[row['id']] = row
            codes.add(code)
        for raw in bundle['revisions']:
            row = checked(raw)
            if row['id'] not in records:
                raise ValueError('A revision refers to a missing record.')
            history = histories.setdefault(row['id'], {})
            if row['revision'] in history:
                raise ValueError('The backup repeats a revision.')
            history[row['revision']] = row
        for identifier, row in records.items():
            history = histories.get(identifier, {})
            if set(history) != set(range(1, row['revision'] + 1)) or history.get(row['revision']) != row:
                raise ValueError('The backup must retain every revision and its current record.')
            for snapshot in history.values():
                if snapshot['created'] != row['created'] or snapshot['data']['kind'] != row['data']['kind']:
                    raise ValueError('A revision changed a stable record identity.')
                _links(snapshot['data'], records, identifier)
        relations, relation_ids = [], set()
        for raw in bundle['relations']:
            required = {'id', 'project_id', 'subject', 'kind', 'object', 'note', 'created'}
            if not isinstance(raw, dict) or not required <= set(raw) or set(raw) - required - {'void'}:
                raise ValueError('The backup has an invalid relationship.')
            row = {**raw, 'id': _id(raw['id']), 'subject': _id(raw['subject']), 'object': _id(raw['object']),
                   'note': _text(raw['note'], 'Relationship note', 2000), 'created': _stamp(raw['created'])}
            if row['id'] in relation_ids or row['project_id'] != project['id'] or row['kind'] not in ('above', 'below', 'same_as') or row['subject'] == row['object']:
                raise ValueError('The backup has an invalid relationship identity.')
            if any(identifier not in records or records[identifier]['data']['kind'] != 'context' for identifier in (row['subject'], row['object'])):
                raise ValueError('A relationship refers to a missing context.')
            if 'void' in row:
                void = row['void']
                if not isinstance(void, dict) or set(void) != {'reason', 'created'}:
                    raise ValueError('The backup has an invalid relationship correction.')
                row['void'] = {'reason': _text(void['reason'], 'Reason for correction', 2000, True), 'created': _stamp(void['created'])}
            relation_ids.add(row['id'])
            relations.append(row)
        _sequence([row for row in relations if 'void' not in row])
        added = advanced = 0
        with self._connection(True) as connection:
            existing = connection.execute('SELECT id,code,title,created FROM projects WHERE id=?', (project['id'],)).fetchone()
            if existing and dict(existing) != project:
                raise ValueError('This project identifier has different metadata. Restore was cancelled.')
            try:
                if not existing:
                    connection.execute('INSERT INTO projects VALUES (?,?,?,?,?)', (project['id'], project['code'], project['code'].casefold(), project['title'], project['created']))
                local = self._records(connection, project['id'])
                final = {**local, **records}
                for identifier, row in records.items():
                    old = local.get(identifier)
                    if old:
                        previous = {r['revision']: r for r in [json.loads(r[0]) for r in connection.execute('SELECT snapshot FROM revisions WHERE record_id=?', (identifier,))]}
                        if any(previous[rev] != histories[identifier][rev] for rev in set(previous) & set(histories[identifier])):
                            raise ValueError('This backup diverges from a saved revision. Restore was cancelled; neither version was overwritten.')
                        if row['revision'] <= old['revision']:
                            final[identifier] = old
                            continue
                        advanced += 1
                        connection.execute('UPDATE records SET code_key=?,revision=?,snapshot=? WHERE id=?', (row['data']['code'].casefold(), row['revision'], json.dumps(row, ensure_ascii=False), identifier))
                    else:
                        added += 1
                        connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', (identifier, project['id'], row['data']['kind'], row['data']['code'].casefold(), row['revision'], json.dumps(row, ensure_ascii=False)))
                    for revision, snapshot in histories[identifier].items():
                        if not old or revision > old['revision']:
                            connection.execute('INSERT INTO revisions VALUES (?,?,?)', (identifier, revision, json.dumps(snapshot, ensure_ascii=False)))
                if len(final) > MAX_RECORDS:
                    raise ValueError('Restoring would exceed the project record limit.')
                for identifier, row in final.items():
                    _links(row['data'], final, identifier)
                local_relations = {row['id']: row for row in self._relations(connection, project['id'], False)}
                for row in relations:
                    old = local_relations.get(row['id'])
                    if old and {k: v for k, v in old.items() if k != 'void'} != {k: v for k, v in row.items() if k != 'void'}:
                        raise ValueError('A relationship identifier has conflicting observations.')
                    if old and 'void' in old and 'void' in row and old['void'] != row['void']:
                        raise ValueError('A relationship correction has conflicting versions.')
                    if not old:
                        raw = {k: v for k, v in row.items() if k != 'void'}
                        connection.execute('INSERT INTO relations VALUES (?,?,?)', (row['id'], project['id'], json.dumps(raw, ensure_ascii=False)))
                    if 'void' in row and (not old or 'void' not in old):
                        connection.execute('INSERT INTO relation_voids VALUES (?,?,?)', (row['id'], row['void']['reason'], row['void']['created']))
                _sequence(self._relations(connection, project['id']))
            except sqlite3.IntegrityError:
                raise ValueError('A saved code or identifier conflicts with this backup. Restore was cancelled.') from None
        return {'project_id': project['id'], 'added': added, 'advanced': advanced}
