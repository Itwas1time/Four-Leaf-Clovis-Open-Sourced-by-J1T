"""Read native AMCR fieldwork and site metadata as qualified source editions."""
from contextlib import closing
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import re
import sqlite3
from urllib.parse import urlencode

from defusedxml import ElementTree as ET
from core.data_packs import PackStore

PACK = 'amcr-native-metadata'
PAGE_SIZE = 24
NS = {'o': 'http://www.openarchives.org/OAI/2.0/', 'a': 'https://api.aiscr.cz/schema/amcr/2.2/'}
FIELDS = {'evidence': 'Archaeology text', 'all': 'All native metadata', 'places': 'Recorded district / cadastral text'}
SCOPES = {'all': 'Fieldwork and sites', 'fieldwork': 'Fieldwork metadata', 'sites': 'Site metadata'}
ACCESS = {'available': 'Readable metadata retained', 'partial': 'Partial metadata retained',
          'denied': 'Metadata denied by provider', 'deleted': 'Deleted source header'}
LICENSE = 'CC BY-NC 4.0 by default; original source exceptions and linked-document rights remain separate'
POLICY = 'https://arup-cas.github.io/aiscr-api-home/'
NOTES = (
    'Native fieldwork and site metadata editions are different evidence. A fieldwork record can describe survey, a chance find or an unknown context, not just excavation.',
    'Fieldwork coverage is incomplete. Denied and deleted headers are retained separately and are not searchable readable records. Partial records retain their protected-field markers.',
    'A metadata datestamp is an edition date, not a date of fieldwork. Read activity dates with the provider\'s precision declaration; range endpoints alone do not establish daily work or duration.',
    'Negative declarations describe individual documentation units; different declarations can coexist in one activity. They do not establish absence across a town.',
    'Recorded district/cadastral text is not a boundary or distance filter. Spatial-unit references are not resolved here; no point, footprint or find position is inferred.',
    'Source IDs are namespaced to AMCR. Cross-catalog duplicates, aliases and real-world event identities have not been reconciled.',
)


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store = PackStore()
    return store.resolve_file(PACK, 'amcr.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def connect(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    return db


def tree_value(node):
    return [node.tag, sorted(node.attrib.items()), node.text, node.tail, [tree_value(child) for child in node]]


def edition_hash(node):
    return hashlib.sha256(json.dumps(tree_value(node), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def values(node, path):
    return [{'text': item.text, 'attributes': dict(item.attrib)} for item in node.findall(path, NS)] if node is not None else []


def details(record, scope):
    native = record.find('o:metadata/a:amcr/a:archeologicky_zaznam', NS)
    content = native.find('a:akce' if scope == 'fieldwork' else 'a:lokalita', NS)
    units = native.findall('a:dokumentacni_jednotka', NS)
    return {'recording_codes': values(content, 'a:typ') if scope == 'fieldwork' else [],
        'types': values(content, 'a:hlavni_typ' if scope == 'fieldwork' else 'a:typ_lokality'),
        'site_kinds': values(content, 'a:druh') if scope == 'sites' else [],
        'start_dates': values(content, 'a:datum_zahajeni') if scope == 'fieldwork' else [],
        'end_dates': values(content, 'a:datum_ukonceni') if scope == 'fieldwork' else [],
        'date_precision': values(content, 'a:specifikace_data') if scope == 'fieldwork' else [],
        'districts': values(native, 'a:okres'),
        'cadastral_areas': values(native, 'a:chranene_udaje/a:hlavni_katastr'),
        'units': [{'identifiers': values(unit, 'a:ident_cely'), 'negative': values(unit, 'a:negativni_jednotka'),
            'spatial_references': values(unit, 'a:pian')} for unit in units]}


def native_identifier(value):
    if not isinstance(value, str):
        return ''
    value = value.strip().removeprefix('https://api.aiscr.cz/id/')
    return value if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}', value) else ''


def validate_parameters(query='', page=1, scope='all', method='', field='evidence'):
    if (not isinstance(query, str) or len(query) > 120 or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in query)
            or type(page) is not int or not 1 <= page <= 1_000_000 or scope not in SCOPES or field not in FIELDS
            or not isinstance(method, str) or method and not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', method)):
        raise ValueError('Choose a native AMCR record kind, fieldwork type and listed text field.')


def stats():
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def methods():
    path = database()
    if path is None:
        return []
    with closing(connect(path)) as db:
        rows = db.execute('SELECT method_id,min(label),count(DISTINCT record_key) FROM methods GROUP BY method_id ORDER BY min(label),method_id').fetchall()
    return [{'value': row[0], 'label': row[1] or row[0], 'records': row[2]} for row in rows]


def header_status(query):
    """Explain a known identifier's access states without inventing a resource."""
    identifier = native_identifier(query)
    path = database() if identifier else None
    if path is None:
        return []
    with closing(connect(path)) as db:
        rows = db.execute('SELECT DISTINCT datestamp,access FROM observations WHERE identifier=? ORDER BY datestamp,access',
            ('https://api.aiscr.cz/id/' + identifier,)).fetchall()
    return [{'datestamp': row[0], 'access': row[1], 'label': ACCESS[row[1]]} for row in rows]


def search(query='', page=1, scope='all', method='', field='evidence'):
    validate_parameters(query, page, scope, method, field)
    path = database()
    if path is None:
        return {'rows': [], 'total': 0, 'page': 1, 'pages': 1, 'installed': False}
    clauses, params = [], []
    if scope != 'all':
        clauses.append('scope=?')
        params.append(scope)
    if method:
        clauses.append('record_key IN (SELECT record_key FROM methods WHERE method_id=?)')
        params.append(method)
    identifier = native_identifier(query)
    if identifier and (query.strip().startswith('https://api.aiscr.cz/id/') or re.match(r'^[CM]-\d', identifier)):
        clauses.append('native_id=?')
        params.append(identifier)
    else:
        terms = re.findall(r'[^\W_]+', query, re.UNICODE)
        if terms:
            column = {'evidence': 'evidence', 'places': 'places', 'all': 'all_text'}[field]
            phrase = column + ' : (' + ' AND '.join('"' + term + '"' + ('' if field == 'places' else '*') for term in terms) + ')'
            clauses.append('rowid IN (SELECT rowid FROM resource_fts WHERE resource_fts MATCH ?)')
            params.append(phrase)
        elif query.strip():
            clauses.append('0')
    statement = ' FROM resources WHERE ' + (' AND '.join(clauses) or '1')
    with closing(connect(path)) as db:
        total = db.execute('SELECT count(*)' + statement, params).fetchone()[0]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in db.execute('SELECT record_key AS id,title,scope,datestamp,access,native_id' + statement
            + ' ORDER BY native_id,datestamp,record_key LIMIT ? OFFSET ?', [*params, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row.update(category=SCOPES[row['scope']] + ' edition',
            subtitle=row['native_id'] + ' · Metadata edition ' + row['datestamp'] + (' · Partial access' if row['access'] == 'partial' else ''))
    return {'rows': rows, 'total': total, 'page': page, 'pages': pages, 'installed': True}


def _native(db, page_id, ordinal, expected):
    page = dict(db.execute('SELECT * FROM source_pages WHERE id=?', (page_id,)).fetchone())
    compressed = page.pop('source_gzip')
    receipt = json.loads(page['receipt_json'])
    if hashlib.sha256(compressed).hexdigest() != receipt['compressed_sha256']:
        raise ValueError('The stored original XML page failed its compressed-byte check.')
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        raw = stream.read(32_000_001)
    if len(raw) > 32_000_000 or len(raw) != receipt['bytes'] or hashlib.sha256(raw).hexdigest() != receipt['sha256']:
        raise ValueError('The stored original XML page failed its byte check.')
    records = ET.fromstring(raw, forbid_dtd=True).findall('o:ListRecords/o:record', NS)
    if not 1 <= ordinal <= len(records) or edition_hash(records[ordinal - 1]) != expected:
        raise ValueError('The original XML edition differs from its indexed record.')
    return records[ordinal - 1], receipt, raw


def get_record(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}~[a-f0-9]{64}', key):
        return None
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        row = db.execute('SELECT * FROM resources WHERE record_key=?', (key,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        native, receipt, raw = _native(db, result['source_page'], result['source_ordinal'], result['edition_sha256'])
        data = details(native, result['scope'])
        terms = []
        term_ids = {item['attributes'].get('id') for field in ('types', 'date_precision') for item in data[field]}
        for term_id in sorted(term_ids - {None}):
            for term in db.execute('SELECT * FROM vocabulary WHERE native_id=? ORDER BY datestamp,edition_sha256', (term_id,)):
                term_xml, term_receipt, _ = _native(db, term['source_page'], term['source_ordinal'], term['edition_sha256'])
                terms.append({'id': term_id, 'scope': term['scope'], 'datestamp': term['datestamp'], 'receipt': term_receipt,
                    'edition_sha256': term['edition_sha256'], 'xml': ET.tostring(term_xml, encoding='unicode')})
    result.update(id=key, category=SCOPES[result['scope']] + ' edition', subtitle=result['native_id'],
        source_url='https://api.aiscr.cz/2.2/oai?' + urlencode({'verb': 'GetRecord', 'metadataPrefix': 'oai_amcr', 'identifier': result['identifier']}),
        details=data, parsed_xml=ET.tostring(native, encoding='unicode'),
        vocabulary=terms, receipt=receipt, native_page=raw)
    return result


def literal(items):
    return json.dumps(items, ensure_ascii=False) if items else 'Not recorded'


def display(items):
    return '; '.join((item['text'] if item['text'] is not None else '(empty value)')
        + (' [' + item['attributes']['id'] + ']' if item['attributes'].get('id') else '') for item in items) if items else 'Not recorded'


def fields(row):
    data = row['details']
    def vocabulary_fields(scope, label):
        terms = [term for term in row['vocabulary'] if term.get('scope', 'fieldwork-types') == scope]
        result = []
        for term in terms:
            native = ET.fromstring(term['xml']).find('o:metadata/a:amcr/a:heslo', NS)
            name = label + ' [' + term['id'] + ']'
            if sum(other['id'] == term['id'] for other in terms) > 1:
                name += ' · Vocabulary edition ' + term['datestamp'] + ' · ' + term['edition_sha256']
            result.append((name, native.findtext('a:heslo_en', namespaces=NS) or 'Not recorded'))
        return result

    result = [('Original AMCR identifier', row['identifier']), ('Native record kind', SCOPES[row['scope']]),
        ('Metadata edition (not fieldwork date)', row['datestamp']), ('Metadata access', row['access']),
        ('Original type declarations', display(data['types'])), ('Recorded district', display(data['districts'])),
        ('Recorded cadastral area', display(data['cadastral_areas']))]
    result.extend(vocabulary_fields('fieldwork-types', 'Provider English type label'))
    if row['scope'] == 'fieldwork':
        result.extend([('Original recording code', display(data['recording_codes'])),
            ('Activity start dates', display(data['start_dates'])), ('Activity end dates', display(data['end_dates'])),
            ('Activity date precision', display(data['date_precision']))])
        result.extend(vocabulary_fields('date-precision', 'Provider English date precision label'))
    else:
        result.append(('Original site kinds', display(data['site_kinds'])))
    result.extend(('Documentation unit ' + display(unit['identifiers']), 'Source negative flag: '
        + display(unit['negative']) + '; spatial reference: ' + display(unit['spatial_references'])) for unit in data['units'])
    return result


def reference_entry(key):
    row = get_record(key)
    if row is None:
        raise ValueError('Choose an installed native AMCR metadata edition.')
    return _reference_entry(row)


def _reference_entry(row):
    from core.fieldbook import validate_citation_entry
    from core.resident_context import _md
    def escaped_xml(value):
        for char in "\\`*_{}[]<>()!#|":
            value = value.replace(char, '\\' + char)
        return value
    lines = ['# AMCR source edition · ' + _md(row['title']), row['source_url'], '',
        'Attribution: AIS CR / Archaeological Map of the Czech Republic. Native authorship and attribution are retained in the complete parsed source record.',
        'Metadata reuse: ' + LICENSE, POLICY, '', *NOTES, '']
    lines.extend(label + ': ' + _md(value) for label, value in fields(row))
    lines.extend(['', 'Source page SHA-256: ' + row['receipt']['sha256'],
        'Parsed XML edition SHA-256: ' + row['edition_sha256'], 'Record ordinal: ' + str(row['source_ordinal']),
        'Retrieved: ' + row['receipt']['retrieved_utc'], 'Response URL: ' + row['receipt']['url'],
        '', '## Complete parsed source record',
        'XML namespace prefixes/formatting are regenerated; exact original response bytes remain available as the source-page download.',
        escaped_xml(row['parsed_xml'])])
    for term in row['vocabulary']:
        lines.extend(['', '## Supporting native vocabulary · ' + term['id'],
            'Metadata edition: ' + term['datestamp'], 'Source page SHA-256: ' + term['receipt']['sha256'],
            'Parsed XML edition SHA-256: ' + term['edition_sha256'],
            'Response URL: ' + term['receipt']['url'], 'Retrieved: ' + term['receipt']['retrieved_utc'], escaped_xml(term['xml'])])
    markdown = '\n'.join(lines)
    entry = {'id': hashlib.sha256(markdown.encode()).hexdigest()[:24], 'kind': 'investigation',
        'title': ('AMCR · ' + row['native_id'])[:120], 'created': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary': {'source': 'AIS CR / AMCR · ' + row['native_id']}, 'markdown': markdown}
    validate_citation_entry(entry)
    return entry
