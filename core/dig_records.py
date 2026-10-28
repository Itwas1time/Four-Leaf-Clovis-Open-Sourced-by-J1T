"""Local excavation records with stable IDs, checked links and dated revisions.

User records live outside the installed package. Nothing here contacts a
publisher or turns a museum/reference record into an observed find.
"""
from contextlib import closing, contextmanager, nullcontext
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
from uuid import uuid4

KINDS = {'unit': 'Unit / trench', 'context': 'Context', 'find': 'Find',
         'sample': 'Sample', 'measurement': 'Sample measurement / processing', 'source': 'Source document'}
CONTEXT_TYPES = ('unknown', 'deposit', 'cut', 'structure', 'interface')
UNITS = ('mm', 'cm', 'm', 'in', 'ft')
MEASUREMENT_ROLES = {'unknown': 'Not specified', 'collected': 'Collected sample',
    'processed': 'Material processed', 'analyzed': 'Portion analyzed',
    'retained': 'Material retained unprocessed', 'result': 'Recovered material / result'}
ANALYSIS_STATUS = {'unknown': 'Unknown / not recorded', 'not_analyzed': 'Not analyzed',
    'partial': 'Partly analyzed', 'analyzed': 'Analyzed', 'unavailable': 'Material unavailable'}
QUANTITY_KINDS = {'unknown': 'Not specified', 'volume': 'Volume', 'mass': 'Mass', 'count': 'Count', 'other': 'Other'}
QUANTITY_QUALIFIERS = {'recorded': 'As recorded', 'approximate': 'Approximately',
    'less_than': 'Less than', 'greater_than': 'Greater than'}
MAX_RECORDS = 20_000
MAX_BACKUP_BYTES = 32_000_000
MAX_BACKUP_ZIP_BYTES = MAX_BACKUP_BYTES + 100_000_000 + 1_000_000
PAGE_SIZE = 24
SCHEMA_COLUMNS = {
    'projects': ('id','code','code_key','title','created'),
    'records': ('id','project_id','kind','code_key','revision','snapshot'),
    'revisions': ('record_id','revision','snapshot'),
    'relations': ('id','project_id','snapshot'),
    'relation_voids': ('relation_id','reason','created'),
}
COMMON = {'description': '', 'interpretation': '', 'recorder': '',
          'observed_date': '', 'source_ids': []}
EXTRA = {
    'unit': {},
    'context': {'unit_id': None, 'context_type': 'unknown', 'depth': '', 'depth_unit': '', 'datum': ''},
    'find': {'context_id': None, 'material': '', 'count': None, 'bag': '', 'depth': '', 'depth_unit': '', 'datum': ''},
    'sample': {'context_id': None, 'sample_type': '', 'method': '', 'bag': '', 'depth': '', 'depth_unit': '', 'datum': ''},
    'measurement': {'sample_id': None, 'role': 'unknown', 'analysis_status': 'unknown',
        'portion': '', 'quantity_kind': 'unknown', 'quantity': '', 'quantity_unit': '',
        'qualifier': 'recorded', 'material': '', 'method': '', 'bag': '', 'mesh_size': '', 'mesh_unit': ''},
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


def _quantity(value, label, *, positive=False):
    value=_text(value,label,40)
    if value:
        try:
            number=Decimal(value)
            if not number.is_finite() or number<0 or number>1_000_000_000_000 or positive and number==0:
                raise InvalidOperation()
        except InvalidOperation:
            raise ValueError(f'{label} must be a finite {"positive" if positive else "nonnegative"} number up to 10^12, or blank.') from None
    return value


def _atlas_reference(value):
    from core.fieldbook import validate_citation_entry
    if not isinstance(value,dict) or set(value)!={'atlas_id','entry'}:
        raise ValueError('Use a complete captured Atlas citation.')
    identifier=value['atlas_id']
    if (not isinstance(identifier,str) or len(identifier)>350
            or not re.fullmatch(r'[a-z_]+\|[^\x00-\x1f]+',identifier)
            or any(0xD800<=ord(char)<=0xDFFF for char in identifier)):
        raise ValueError('The captured Atlas record identifier is invalid.')
    validate_citation_entry(value['entry'])
    return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))


def _reference_content(value):
    # Capture time and the fieldbook's derived ID are retained, but do not
    # create another project source when the cited content is identical.
    return {**value,'entry':{key:item for key,item in value['entry'].items() if key not in ('created','id')}}


def _data(value):
    if not isinstance(value, dict) or not isinstance(value.get('kind'), str) or value['kind'] not in KINDS:
        raise ValueError('Choose a listed dig record type.')
    kind = value['kind']
    defaults = {**COMMON, **EXTRA[kind]}
    if set(value) - {'kind', 'code', 'photos', *defaults, *({'atlas_reference'} if kind=='source' else set())}:
        raise ValueError('This record contains unsupported fields.')
    data = {'kind': kind, 'code': _text(value.get('code'), 'Record code', 80, True)}
    if 'photos' in value:
        from core.local_photos import validate_refs
        data['photos']=json.loads(json.dumps(validate_refs(value['photos']),ensure_ascii=False,allow_nan=False))
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
    for key in ('unit_id', 'context_id', 'sample_id'):
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
    if kind=='measurement':
        if data['sample_id'] is None:
            raise ValueError('Choose a recorded sample for this measurement.')
        for key,choices in (('role',MEASUREMENT_ROLES),('analysis_status',ANALYSIS_STATUS),
                            ('quantity_kind',QUANTITY_KINDS),('qualifier',QUANTITY_QUALIFIERS)):
            if not isinstance(data[key],str) or data[key] not in choices:
                raise ValueError('Choose a listed measurement role, status, quantity type and qualifier.')
        for key,limit in (('portion',200),('quantity_unit',80),('mesh_unit',80)):
            data[key]=_text(data[key],key.replace('_',' ').title(),limit)
        data['quantity']=_quantity(data['quantity'],'Quantity')
        data['mesh_size']=_quantity(data['mesh_size'],'Mesh size',positive=True)
        if data['quantity'] and not data['quantity_unit']:
            raise ValueError('A recorded quantity needs its original unit, including counts.')
        if not data['quantity'] and data['qualifier']!='recorded':
            raise ValueError('A quantity qualifier needs a recorded quantity.')
        if data['mesh_size'] and not data['mesh_unit']:
            raise ValueError('A mesh size needs its original unit.')
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
    if kind=='source' and 'atlas_reference' in value:
        data['atlas_reference']=_atlas_reference(value['atlas_reference'])
    return data


def _links(data, records, own_id):
    for field, kind in (('unit_id', 'unit'), ('context_id', 'context'), ('sample_id', 'sample')):
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
    def _connection(self, write=False, minimum_version=1):
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
            if version not in (1,2,3,4,5,6):
                raise ValueError('This dig record database uses an unsupported version.')
            if version>=4:
                from core.local_photos import PHOTO_COLUMNS
                if tuple(row[1] for row in connection.execute('PRAGMA table_info(photos)'))!=PHOTO_COLUMNS:
                    raise ValueError('This photo notebook has an unsupported database layout.')
            if version>=5:
                from core.workspace_storage import READING_COLUMNS
                if tuple(row[1] for row in connection.execute('PRAGMA table_info(fieldbooks)')) != READING_COLUMNS:
                    raise ValueError('This saved-reading notebook has an unsupported database layout.')
            if write:
                # A user_version number is shared by unrelated SQLite formats.
                # Confirm the existing notebook layout before any migration or
                # record write, including when an override points at a wrong file.
                for table,columns in SCHEMA_COLUMNS.items():
                    actual=tuple(row[1] for row in connection.execute('PRAGMA table_info("'+table+'")'))  # nosec B608
                    if actual!=columns:
                        raise ValueError('This file is not a supported Clovis dig record database.')
                connection.execute('BEGIN IMMEDIATE')
                if minimum_version>version:
                    # Keep existing snapshots
                    # byte-for-byte while preventing an older app from editing
                    # records whose fields or captured citations it cannot understand.
                    if minimum_version>=4:
                        from core.local_photos import PHOTO_COLUMNS
                        connection.execute('CREATE TABLE IF NOT EXISTS photos(sha256 TEXT PRIMARY KEY,media_type TEXT NOT NULL,bytes INTEGER NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,original BLOB NOT NULL)')
                        if tuple(row[1] for row in connection.execute('PRAGMA table_info(photos)'))!=PHOTO_COLUMNS:
                            connection.rollback()
                            raise ValueError('This photo notebook has an unsupported database layout.')
                    if minimum_version>=5:
                        from core.workspace_storage import READING_COLUMNS
                        connection.execute('CREATE TABLE IF NOT EXISTS fieldbooks(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL)')
                        if tuple(row[1] for row in connection.execute('PRAGMA table_info(fieldbooks)')) != READING_COLUMNS:
                            raise ValueError('This saved-reading notebook has an unsupported database layout.')
                    connection.execute({2:'PRAGMA user_version=2',3:'PRAGMA user_version=3',4:'PRAGMA user_version=4',5:'PRAGMA user_version=5',6:'PRAGMA user_version=6'}[minimum_version])
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

    def measurements(self, project, sample, page=1):
        parent=self.get(project,sample)
        if parent is None or parent['data']['kind']!='sample':
            raise ValueError('Choose a saved sample in this project.')
        with self._connection() as connection:
            where="project_id=? AND kind='measurement' AND json_extract(snapshot,'$.data.sample_id')=?"
            values=(project,sample)
            total=connection.execute('SELECT count(*) FROM records WHERE '+where,values).fetchone()[0]  # nosec B608
            pages=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
            page=min(pages,max(1,page if type(page) is int else 1))
            rows=connection.execute('SELECT snapshot FROM records WHERE '+where+' ORDER BY code_key,id LIMIT ? OFFSET ?',  # nosec B608
                                    (*values,PAGE_SIZE,(page-1)*PAGE_SIZE)).fetchall()
        return {'rows':[json.loads(row[0]) for row in rows],'total':total,'page':page,'pages':pages}

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
        required=4 if 'photos' in data else 3 if 'atlas_reference' in data else 2 if data['kind']=='measurement' else 1
        with self._connection(True,required) as connection:
            return self._save(connection,project,data,identifier,expected_revision)

    def _save(self, connection, project, data, identifier=None, expected_revision=None):
        self._project(connection, project)
        records = self._records(connection, project)
        old = records.get(_id(identifier)) if identifier else None
        if identifier and not old:
            raise ValueError('The selected record does not belong to this project.')
        if old and (type(expected_revision) is not int or old['revision'] != expected_revision):
            raise ValueError('This record changed since it was opened. Reopen it before saving your correction.')
        if old and old['data']['kind'] != data['kind']:
            raise ValueError('A saved record keeps its record type. Create a separate record for another type.')
        if old:
            if 'photos' not in data and 'photos' in old['data']:
                data['photos']=old['data']['photos']
            captured=old['data'].get('atlas_reference')
            if 'atlas_reference' in data and data['atlas_reference']!=captured:
                raise ValueError('Keep the captured citation unchanged. Add another source document for different cited content.')
            if captured is not None:
                data['atlas_reference']=captured
        if data.get('photos'):
            from core.local_photos import read_photo,check_reference
            for reference in data['photos']:
                facts,_=read_photo(connection,reference['sha256'])
                check_reference(reference,facts)
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

    def capture_source(self, project, code, reference, url=''):
        reference=_atlas_reference(reference)
        with self._connection(True,3) as connection:
            self._project(connection,project)
            rows=connection.execute("SELECT snapshot FROM records WHERE project_id=? AND kind='source' "
                "AND json_extract(snapshot,'$.data.atlas_reference.atlas_id')=?",(project,reference['atlas_id']))
            for stored, in rows:
                row=json.loads(stored)
                if _reference_content(row['data']['atlas_reference'])==_reference_content(reference):
                    return {'record':row,'created':False}
            data=_data({'kind':'source','code':code,'citation':reference['entry']['title'],
                        'url':url,'atlas_reference':reference})
            return {'record':self._save(connection,project,data),'created':True}

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
            return self._export(connection, project)

    def _export(self, connection, project):
        """Export from an existing consistent database snapshot."""
        bundle = {'format': 'clovis-dig-records', 'version': 1, 'project': self._project(connection, project),
                  'records': list(self._records(connection, project).values()),
                  'revisions': [json.loads(row[0]) for row in connection.execute('SELECT v.snapshot FROM revisions v JOIN records r ON r.id=v.record_id WHERE r.project_id=? ORDER BY v.record_id,v.revision', (project,))],
                  'relations': self._relations(connection, project, False)}
        if any(row['data']['kind']=='measurement' for row in bundle['records']):
            bundle['version']=2
        if any('atlas_reference' in row['data'] for rows in (bundle['records'],bundle['revisions']) for row in rows):
            bundle['version']=3
        if any('photos' in row['data'] for rows in (bundle['records'],bundle['revisions']) for row in rows):
            bundle['version']=4
        encoded = json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2)
        if len(encoded.encode('utf-8')) > MAX_BACKUP_BYTES:
            raise ValueError('This full revision backup exceeds 32 MB. Preserve the local database and start a separate project for further records.')
        return encoded

    def backup_bytes(self, project):
        from core.local_photos import referenced_photos,archive_bytes,PhotoStore
        encoded=self.export(project).encode('utf-8')
        bundle=json.loads(encoded)
        references=referenced_photos(row['data'] for rows in (bundle['records'],bundle['revisions']) for row in rows)
        data=archive_bytes('dig-records.json',encoded,references,PhotoStore(self.path))
        if len(data) > MAX_BACKUP_ZIP_BYTES:
            raise ValueError('This portable backup exceeds its 32 MB notes and 100 MB photo allowance. Preserve the local database; no saved records were removed.')
        return data

    def restore_backup(self, data):
        from core.local_photos import read_archive
        text,photos=read_archive(data,'dig-records.json',MAX_BACKUP_BYTES)
        return self.restore(text,_photos=photos)

    def restore(self, encoded,*,_photos=None,_connection=None):
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
                or bundle['format'] != 'clovis-dig-records' or type(bundle['version']) is not int or bundle['version'] not in (1,2,3,4)):
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
            if bundle['version']==1 and isinstance(row['data'],dict) and row['data'].get('kind')=='measurement':
                raise ValueError('Sample measurements require a version 2 project backup.')
            if bundle['version']<3 and isinstance(row['data'],dict) and 'atlas_reference' in row['data']:
                raise ValueError('Captured Atlas citations require a version 3 project backup.')
            if bundle['version']<4 and isinstance(row['data'],dict) and 'photos' in row['data']:
                raise ValueError('Saved photos require a version 4 project backup.')
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
                if snapshot['data'].get('atlas_reference')!=row['data'].get('atlas_reference'):
                    raise ValueError('A revision changed a captured Atlas citation.')
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
        from core.local_photos import referenced_photos,check_archive_references,insert_photos
        references=referenced_photos(row['data'] for rows in (bundle['records'],bundle['revisions']) for row in rows)
        if references and _photos is None:
            raise ValueError('Restore a photo-inclusive project ZIP containing every original photo.')
        check_archive_references(references,_photos or {})
        added = advanced = 0
        manager = nullcontext(_connection) if _connection is not None else self._connection(True, bundle['version'])
        with manager as connection:
            if _photos:
                insert_photos(connection,_photos)
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
