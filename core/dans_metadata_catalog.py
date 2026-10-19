"""DANS archaeology DOI metadata; datasets and subjects are not excavation IDs."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import quote, urlsplit
import zlib

from core.data_packs import PackStore
from core.ads_metadata_catalog import category, connect, fields, literal
from core.datacite_text import description_text

PACK = 'dans-archaeology-metadata'
PAGE_SIZE = 24
FIELDS = {'research': 'Research text', 'all': 'All DataCite text',
          'title': 'Titles only', 'places': 'Recorded place text only'}
POLICY = 'https://support.datacite.org/docs/datacite-data-file-use-policy'
NOTES = (
    'One DataCite DOI metadata resource, not a unique dataset, report, site, find or excavation event. Object-register entries, desk studies, boreholes and excavation reports can share the technical Dataset type.',
    'DataCite supplies this metadata under CC0. Original authors, DANS and DataCite attribution are retained. Linked reports and files have separate rights and are not included.',
    'Resource version, metadataVersion, publication year, source dates and retrieval dates have different meanings. No fieldwork or occupation date is inferred from them.',
    'This is the DataCite metadata representation. Native Dataverse archaeology fields and earlier native versions are not supplied by this traversal.',
    'Missing coordinates stay missing. Recorded place words and source coordinates do not establish countries, town boundaries, excavation footprints or find locations.',
)


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store = PackStore()
    return store.resolve_file(PACK, 'metadata.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def stats():
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def doi(value):
    if not isinstance(value, str):
        return ''
    value = value.strip()
    if value.lower().startswith(('https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/')):
        parsed = urlsplit(value)
        if parsed.query or parsed.fragment:
            return ''
        value = parsed.path[1:]
    return value if re.fullmatch(r'10\.\d{4,9}/[A-Za-z0-9][A-Za-z0-9._()/;:-]{0,250}', value, re.I) else ''


def _phrase(query, prefix=True):
    return ' AND '.join('"' + term + '"' + ('*' if prefix else '') for term in re.findall(r'\w+', query, re.UNICODE))


def _stored_doi(db, identifier):
    # Source IDs use a binary unique index. Resolve common exact/canonical cases
    # through it before the compatibility lookup for unusual native casing.
    for candidate in dict.fromkeys((identifier, identifier.casefold())):
        row = db.execute('SELECT doi FROM resources WHERE doi=?', (candidate,)).fetchone()
        if row is not None:
            return row[0]
    row = db.execute('SELECT doi FROM resources WHERE doi=? COLLATE NOCASE', (identifier,)).fetchone()
    return row[0] if row is not None else None


def validate_parameters(query='', page=1, subject='', field='research', shared_legacy=''):
    if (not isinstance(query, str) or len(query) > 120
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in query)
            or type(page) is not int or not 1 <= page <= 1_000_000
            or not isinstance(subject, str) or subject and not re.fullmatch(r'[a-f0-9]{64}', subject)
            or not isinstance(field, str) or field not in FIELDS
            or not isinstance(shared_legacy, str)
            or shared_legacy and not re.fullmatch(r'easy-dataset:[A-Za-z0-9._-]{1,80}', shared_legacy)):
        raise ValueError('Choose a listed original subject, metadata text field and recorded shared identifier.')


def _shared_group(summary, identifier):
    """Use the audited original-identifier index, never titles or proximity."""
    groups = summary.get('repeated_legacy_identifier_candidates', {})
    if not isinstance(groups, dict):
        raise ValueError('The recorded shared-identifier index needs source review.')
    if identifier not in groups:
        return []
    values = groups[identifier]
    if (not isinstance(values, list) or len(values) < 2
            or any(not isinstance(value, str) or doi(value) != value for value in values)
            or len({value.casefold() for value in values}) != len(values)):
        raise ValueError('The recorded shared-identifier index needs source review.')
    return values


def subjects(query='', selected=''):
    validate_parameters(query, subject=selected)
    path = database()
    if path is None:
        return []
    # Bound the picker, not the searchable catalog. Retain a selected source value.
    pattern = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    with closing(connect(path)) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT s.*,count(r.resource_id) AS records FROM subjects s JOIN resource_subjects r USING(subject_key) "
            "WHERE s.label LIKE ? ESCAPE '\\' COLLATE NOCASE GROUP BY s.subject_key ORDER BY records DESC,s.label,s.subject_key LIMIT 40", (pattern,))]
        if selected and not any(row['subject_key'] == selected for row in rows):
            row = db.execute('SELECT s.*,count(r.resource_id) AS records FROM subjects s JOIN resource_subjects r USING(subject_key) '
                'WHERE s.subject_key=? GROUP BY s.subject_key', (selected,)).fetchone()
            if row:
                rows.append(dict(row))
    for row in rows:
        native = json.loads(row['native_json'])
        scheme = native.get('subjectScheme') or native.get('schemeUri') or ''
        row.update(value=row['subject_key'], label=(row['label'] or 'Empty original subject') + (' · ' + scheme if scheme else ''))
    return rows


def search(query='', page=1, subject='', field='research', shared_legacy=''):
    validate_parameters(query, page, subject, field, shared_legacy)
    path = database()
    if path is None:
        return {'rows': [], 'total': 0, 'page': 1, 'pages': 1, 'installed': False}
    clauses, parameters = [], []
    if subject:
        clauses.append('rowid IN (SELECT resource_id FROM resource_subjects WHERE subject_key=?)')
        parameters.append(subject)
    identifier = doi(query)
    if not identifier:
        phrase = _phrase(query, field != 'places')
        if phrase:
            scope = {'research': '{title creators subjects description places identifiers}',
                     'all': 'all_text', 'title': 'title', 'places': 'places'}[field]
            clauses.append('rowid IN (SELECT rowid FROM resource_fts WHERE resource_fts MATCH ?)')
            parameters.append(scope + ' : (' + phrase + ')')
        elif query.strip():
            clauses.append('0')
    with closing(connect(path)) as db:
        if identifier:
            clauses.append('doi=?')
            parameters.append(_stored_doi(db, identifier))
        if shared_legacy:
            summary = json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
            identifiers = _shared_group(summary, shared_legacy)
            # Group IDs come verbatim from the source/index, so use their exact
            # binary keys instead of scanning the title index with NOCASE.
            clauses.append('doi IN (' + ','.join('?' for _ in identifiers) + ')' if identifiers else '0')
            parameters.extend(identifiers)
        statement = ' FROM resources WHERE ' + (' AND '.join(clauses) or '1')
        total = db.execute('SELECT count(*)' + statement, parameters).fetchone()[0]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = [dict(row) for row in db.execute('SELECT doi AS id,title,resource_type,general_type,publication_year' + statement
            + ' ORDER BY title COLLATE NOCASE,doi LIMIT ? OFFSET ?', [*parameters, PAGE_SIZE, (page - 1) * PAGE_SIZE])]
    for row in rows:
        row.update(title=row['title'] or row['id'], category=category(row['resource_type'], row['general_type']),
            subtitle=' · '.join(value for value in (row['general_type'] or 'General type not recorded',
                ('Publication year ' + row['publication_year']) if row['publication_year'] else '', row['id']) if value))
    return {'rows': rows, 'total': total, 'page': page, 'pages': pages, 'installed': True}


def get_record(identifier):
    if not doi(identifier) or identifier != doi(identifier):
        return None
    path = database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        row = db.execute('SELECT * FROM resources WHERE doi=?', (_stored_doi(db, identifier),)).fetchone()
        if row is None:
            return None
        result = dict(row)
        decoder = zlib.decompressobj()
        native = decoder.decompress(result.pop('source_json'), 2_000_001)
        if (len(native) > 2_000_000 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
                or len(native) != result['source_bytes'] or hashlib.sha256(native).hexdigest() != result['source_sha256']):
            raise ValueError('The retained original DOI metadata failed byte verification.')
        source = json.loads(native)
        if (source.get('id') != result['doi'] or not isinstance(source.get('attributes', {}).get('doi'), str)
                or source['attributes']['doi'].casefold() != result['doi'].casefold()
                or source.get('relationships', {}).get('client', {}).get('data', {}).get('id') != 'dans.archive'
                or urlsplit(source['attributes'].get('url', '')).hostname != 'archaeology.datastations.nl'):
            raise ValueError('The retained source differs from its indexed DOI or repository scope.')
        receipt = dict(db.execute('SELECT * FROM source_pages WHERE ordinal=?', (result['source_page'],)).fetchone())
        summary = json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
    result.update(id=result['doi'], source=source, native=native, receipt=receipt, summary=summary,
        title=result['title'] or result['doi'], source_url='https://doi.org/' + quote(result['doi'], safe='/'),
        category=category(result['resource_type'], result['general_type']),
        subtitle=' · '.join(value for value in (result['general_type'], result['publication_year'], result['doi']) if value))
    return result


def descriptions(record):
    return [{'type': row.get('descriptionType') or 'Type not recorded', 'text': description_text(row.get('description')),
             'original': row.get('description')}
            for row in record['source']['attributes'].get('descriptions') or [] if isinstance(row, dict)]


def relationships(record):
    """Recorded identifier overlap is review evidence, not an identity merge."""
    result, seen = [], set()
    for native in record['source']['attributes'].get('alternateIdentifiers') or []:
        value = native.get('alternateIdentifier') if isinstance(native, dict) else None
        if not isinstance(value, str) or value in seen or not re.fullmatch(r'easy-dataset:[A-Za-z0-9._-]{1,80}', value):
            continue
        seen.add(value)
        identifiers = _shared_group(record['summary'], value)
        if len(identifiers) > 1 and record['doi'] in identifiers:
            result.append({'key': 'shared-legacy:' + value,
                'label': 'Records sharing ' + value + ' · possible overlap; count before current limits',
                'total': len(identifiers), 'parameters': {'collection': 'dans', 'shared_legacy': value}})
    return result


def reference_entry(identifier):
    record = get_record(identifier)
    if record is None:
        raise ValueError('Choose an installed DANS metadata resource.')
    return _reference_entry(record)


def _reference_markdown(record):
    """Complete literal source capture; shared with private size/source audits."""
    from core.resident_context import _md
    lines = ['# DANS archaeology metadata reference · ' + _md(record['title']), '', record['source_url'], '',
        'Metadata supplied by DataCite. Original DANS, creator and contributor attribution follows.']
    lines.extend(label + ': ' + _md(value) for label, value in fields(record))
    lines.extend(['', *NOTES, '', 'Metadata license: CC0 1.0.', 'Metadata policy: ' + POLICY,
        'Original metadata object SHA-256: ' + record['source_sha256'],
        'Original response page SHA-256: ' + record['receipt']['sha256'],
        'Source page / object ordinal: ' + str(record['source_page']) + ' / ' + str(record['source_ordinal']),
        'Retrieved response URL: ' + record['receipt']['url'], '', '## Complete parsed DataCite source metadata',
        'Original JSON values follow as literal text. Reading format is separate from the exact original object download.',
        '\n'.join(_md(line) for line in json.dumps(record['source'], ensure_ascii=False,
            indent=2, allow_nan=False).split('\n'))])
    return '\n'.join(lines)


def _reference_entry(record):
    from core.fieldbook import validate_citation_entry
    markdown = _reference_markdown(record)
    entry = {'id': hashlib.sha256(markdown.encode()).hexdigest()[:24], 'kind': 'investigation',
        'title': ('DANS metadata · ' + record['title']).encode()[:120].decode('utf-8', 'ignore'),
        'created': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary': {'source': 'DANS via DataCite · ' + record['doi']}, 'markdown': markdown}
    validate_citation_entry(entry)
    return entry
