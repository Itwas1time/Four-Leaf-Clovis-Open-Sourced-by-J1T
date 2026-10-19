"""Read ADS DOI metadata without turning publications into excavation events."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from urllib.parse import quote, urlsplit
import zlib

from core.data_packs import PackStore

PACK = 'ads-research-metadata'
PAGE_SIZE = 24
FIELDS = {'all': 'All metadata', 'title': 'Titles only', 'places': 'Recorded place text only'}
NOTES = (
    'One DOI metadata resource, not a unique site, excavation, specimen or find. Reports and archives can overlap or describe many investigations.',
    'CC0 applies to this metadata. Linked reports, archives, images and datasets retain their separately recorded rights; their full content is not included here.',
    'Publication years and metadata dates do not establish dates of fieldwork or occupation. Resource versions and metadata versions remain distinct.',
    'Place text and coordinates describe a resource with unestablished spatial meaning and precision. They do not establish an excavation footprint or an individual find location.',
)


def advertised():
    """Do not offer an unpublished collection absent from the trusted catalog."""
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store = PackStore()
    return store.resolve_file(PACK, 'metadata.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def connect(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def stats():
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def type_id(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _types(connection):
    return [(row[0], row[1]) for row in connection.execute(
        'SELECT resource_type,count(*) FROM resources GROUP BY resource_type ORDER BY resource_type')]


def resource_types():
    path = database()
    if path is None:
        return []
    with closing(connect(path)) as connection:
        values = _types(connection)
    return [{'value': type_id(value), 'label': (value.strip() or 'Not recorded')
             + (' (source whitespace retained)' if value != value.strip() else ''), 'records': count}
            for value, count in values]


def doi(value):
    """Accept an original ADS DOI or its DOI resolver URL, never a title URL."""
    if not isinstance(value, str):
        return ''
    value = value.strip()
    if value.lower().startswith(('https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/')):
        parsed = urlsplit(value)
        if parsed.query or parsed.fragment:
            return ''
        value = parsed.path[1:]
    return value if re.fullmatch(r'10\.5284/[A-Za-z0-9][A-Za-z0-9._()/;-]{0,250}', value, re.I) else ''


def validate_parameters(query='', page=1, resource_type='', field='all'):
    if (not isinstance(query, str) or len(query) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in query)
            or type(page) is not int or not 1 <= page <= 1_000_000
            or not isinstance(resource_type, str) or resource_type and not re.fullmatch(r'[a-f0-9]{64}', resource_type)
            or field not in FIELDS):
        raise ValueError('Choose an ADS metadata search and listed source type or text field.')


def category(resource_type, general_type=''):
    value = resource_type.strip()
    labels = {'Report': 'Report metadata', 'Archive': 'Archive metadata', 'Article': 'Article metadata',
              'Monograph': 'Monograph metadata', 'Blog': 'Blog metadata', 'Files': 'File resource metadata',
              'Online Book': 'Book metadata', 'Webpage': 'Webpage metadata', 'Workflow': 'Workflow metadata'}
    return labels.get(value, (general_type + ' metadata') if general_type else 'Unclassified resource metadata')


def search(query='', page=1, resource_type='', field='all'):
    validate_parameters(query, page, resource_type, field)
    path = database()
    if path is None:
        return {'rows': [], 'total': 0, 'page': 1, 'pages': 1, 'installed': False}
    clauses, parameters = [], []
    with closing(connect(path)) as connection:
        if resource_type:
            native = next((value for value, _ in _types(connection) if type_id(value) == resource_type), None)
            if native is None:
                clauses.append('0')
            else:
                clauses.append('resource_type=?')
                parameters.append(native)
        identifier = doi(query)
        if identifier:
            clauses.append('doi=? COLLATE NOCASE')
            parameters.append(identifier)
        else:
            terms = re.findall(r'\w+', query, flags=re.UNICODE)
            if terms:
                # Place words must not turn York into Yorkshire or Oman into Omani.
                # Other metadata searches retain the catalog's word-beginning search.
                phrase = ' AND '.join('"' + term + '"' + ('' if field == 'places' else '*') for term in terms)
                if field != 'all':
                    phrase = ('title' if field == 'title' else 'places') + ' : (' + phrase + ')'
                clauses.append('rowid IN (SELECT rowid FROM resource_fts WHERE resource_fts MATCH ?)')
                parameters.append(phrase)
            elif query.strip():
                clauses.append('0')
        # Only fixed clauses are assembled; every source/query value is bound.
        statement = ' FROM resources WHERE ' + (' AND '.join(clauses) or '1')
        total = connection.execute('SELECT count(*)' + statement, parameters).fetchone()[0]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in connection.execute(
            'SELECT doi AS id,title,resource_type,general_type,publication_year' + statement
            + ' ORDER BY title COLLATE NOCASE,doi LIMIT ? OFFSET ?', [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row.update(title=row['title'] or row['id'], category=category(row['resource_type'], row['general_type']),
                   subtitle=' · '.join(value for value in (row['resource_type'].strip() or 'Type not recorded',
                       ('Published ' + row['publication_year']) if row['publication_year'] else '', row['id']) if value))
    return {'rows': rows, 'total': total, 'page': page, 'pages': pages, 'installed': True}


def get_record(identifier):
    if not doi(identifier) or identifier != doi(identifier):
        return None
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as connection:
        record = connection.execute('SELECT * FROM resources WHERE doi=? COLLATE NOCASE', (identifier,)).fetchone()
        if record is None:
            return None
        result = dict(record)
        compressed = result.pop('source_json')
        decoder = zlib.decompressobj()
        native = decoder.decompress(compressed, 1_000_001)
        if (len(native) > 1_000_000 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
                or len(native) != result['source_bytes'] or hashlib.sha256(native).hexdigest() != result['source_sha256']):
            raise ValueError('The original DOI metadata failed its stored byte verification.')
        source = json.loads(native)
        if (source.get('id') != result['doi'] or not isinstance(source.get('attributes', {}).get('doi'), str)
                or source['attributes']['doi'].casefold() != result['doi'].casefold()):
            raise ValueError('The original DOI identifier differs from its indexed record.')
        receipt = dict(connection.execute('SELECT * FROM source_pages WHERE ordinal=?', (result['source_page'],)).fetchone())
        summary = json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
    result.update(id=result['doi'], title=result['title'] or result['doi'], source=source, native=native,
                  receipt=receipt, summary=summary, source_url='https://doi.org/' + quote(result['doi'], safe='/'),
                  category=category(result['resource_type'], result['general_type']),
                  subtitle=' · '.join(value for value in (result['resource_type'].strip(), result['publication_year'], result['doi']) if value))
    return result


def literal(value):
    if value is None:
        return 'Not recorded'
    if isinstance(value, str) and value and value == value.strip():
        return value
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def fields(record):
    a = record['source']['attributes']
    declared_types = a.get('types') or {}
    creators = '; '.join(str(item.get('name', '')) for item in a.get('creators') or [])
    places = '; '.join(str(item.get('geoLocationPlace', '')) for item in a.get('geoLocations') or [] if item.get('geoLocationPlace'))
    return [('DOI', record['doi']), ('Declared resource type', literal(declared_types.get('resourceType'))),
            ('General resource type', literal(declared_types.get('resourceTypeGeneral'))), ('Creators', creators or 'Not recorded'),
            ('Publisher', literal(a.get('publisher'))), ('Publication year', literal(a.get('publicationYear'))),
            ('Resource version', literal(a.get('version'))), ('Metadata version', literal(a.get('metadataVersion'))),
            ('Metadata updated (source)', literal(a.get('updated'))),
            ('Metadata retrieved', record['receipt']['retrieved_utc']), ('Recorded place text', places or 'Not recorded')]


def reference_entry(identifier):
    record = get_record(identifier)
    if record is None:
        raise ValueError('Choose an installed ADS metadata resource.')
    return _reference_entry(record)


def _reference_entry(record):
    """Create the same complete citation for reading, export and source audits."""
    from core.fieldbook import validate_book
    from core.resident_context import _md
    lines = ['# ADS metadata reference · ' + _md(record['title']), '', record['source_url'], '']
    lines.extend(label + ': ' + _md(value) for label, value in fields(record))
    lines.extend(['', *NOTES, '', 'Metadata license: CC0 1.0.',
        'Metadata policy: https://archaeologydataservice.ac.uk/about/policies/metadata/',
        'Original metadata object SHA-256: ' + record['source_sha256'],
        'Original response page SHA-256: ' + record['receipt']['sha256'],
        'Source page / object ordinal: ' + str(record['source_page']) + ' / ' + str(record['source_ordinal']),
        'Retrieved response URL: ' + record['receipt']['url'], '',
        '## Complete parsed source metadata',
        'Original JSON values follow as literal text. Formatting is for reading; Download original metadata retains the exact source object bytes.',
        _md(json.dumps(record['source'], ensure_ascii=False, indent=2, allow_nan=False))])
    markdown = '\n'.join(lines)
    entry = {'id': hashlib.sha256(markdown.encode()).hexdigest()[:24], 'kind': 'investigation',
        'title': ('ADS metadata · ' + record['title']).encode('utf-8')[:120].decode('utf-8', 'ignore'),
        'created': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary': {'source': 'ADS via DataCite · ' + record['doi']}, 'markdown': markdown}
    validate_book({'version': 1, 'entries': [entry]})
    return entry
