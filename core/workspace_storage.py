"""Transactional workspace snapshots for readings, projects and original photos.

The browser's legacy fieldbook remains unchanged until explicitly imported.
Workspace archives are independent of the existing project and fieldbook formats.
"""
import json
import re
import sqlite3

from core.dig_records import DigBook
from core.fieldbook import EMPTY_BOOK, validate_book
from core.large_readings import validate_readings, expand_book, compact_book, is_reference
from core.local_photos import (archive_bytes, check_archive_references, check_reference,
    insert_photos, read_archive, read_photo, referenced_photos)

READING_COLUMNS = ('id', 'snapshot')
MAX_WORKSPACE_BYTES = 64_000_000
MAX_PROJECTS = 100


def _strict_merge(current, incoming):
    validate_readings(current)
    incoming = expand_book(incoming, current)
    existing = {row['id']: row for row in current['entries']}
    for row in incoming['entries']:
        old = existing.get(row['id'])
        if old and {k: v for k, v in old.items() if k != 'created'} != {k: v for k, v in row.items() if k != 'created'}:
            raise ValueError('A saved reading has conflicting content under the same identifier. Restore was cancelled.')
    return validate_readings({'version': max(current['version'], incoming['version']),
        'entries': [*current['entries'], *[row for row in incoming['entries'] if row['id'] not in existing]]})


def _readings(connection):
    # Version 5 used one whole-book row; version 6 stores each immutable
    # reading separately. A migration reads the old row before replacing it.
    rows = list(connection.execute('SELECT id,snapshot FROM fieldbooks ORDER BY rowid'))
    if not rows:
        return dict(EMPTY_BOOK, entries=[])
    if len(rows) == 1 and rows[0]['id'] == 'main':
        return validate_readings(json.loads(rows[0]['snapshot']))
    if any(row['id'] == 'main' for row in rows):
        raise ValueError('The saved-reading notebook has an inconsistent layout.')
    meta = next((row for row in rows if row['id'] == '__version__'), None)
    if not meta:
        raise ValueError('The saved-reading notebook is missing its format version.')
    version = json.loads(meta['snapshot'])
    entries = []
    for row in rows:
        if row['id'] == '__version__':
            continue
        item = json.loads(row['snapshot'])
        if not isinstance(item, dict) or item.get('id') != row['id']:
            raise ValueError('A saved reading does not match its identifier.')
        entries.append(item)
    return validate_readings({'version': version, 'entries': entries})


def _save(connection, book):
    # Entries are append-only: merge validation has already rejected divergent
    # content. Keep the first capture time and preserve existing row order.
    for row in book['entries']:
        connection.execute('INSERT OR IGNORE INTO fieldbooks(id,snapshot) VALUES(?,?)',
                           (row['id'], json.dumps(row, ensure_ascii=False, allow_nan=False)))
    connection.execute("INSERT INTO fieldbooks(id,snapshot) VALUES('__version__',?) ON CONFLICT(id) DO UPDATE SET snapshot=excluded.snapshot", (json.dumps(book['version']),))
    connection.execute("DELETE FROM fieldbooks WHERE id='main'")


def _project_refs(project):
    return referenced_photos(row['data'] for name in ('records', 'revisions') for row in project[name])


def _all_refs(book, projects):
    rows = list(book['entries'])
    for project in projects:
        rows.extend(row['data'] for name in ('records', 'revisions') for row in project[name])
    return referenced_photos(rows)


class _SnapshotPhotos:
    def __init__(self, connection):
        self.connection = connection

    def get(self, digest):
        return read_photo(self.connection, digest)


class WorkspaceStorage:
    def __init__(self, path=None):
        self.book = DigBook(path)

    def readings(self):
        if not self.book.path.is_file():
            return dict(EMPTY_BOOK, entries=[])
        with self.book._connection() as connection:
            if connection.execute('PRAGMA user_version').fetchone()[0] < 5:
                return dict(EMPTY_BOOK, entries=[])
            return _readings(connection)

    def reading(self, identifier):
        """Read one full entry without sending the whole workspace to the browser."""
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-f0-9]{24}', identifier):
            raise ValueError('Choose a saved reading.')
        if not self.book.path.is_file():
            raise ValueError('The saved reading is unavailable. Restore its workspace backup.')
        with self.book._connection() as connection:
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version < 5:
                raise ValueError('The saved reading is unavailable. Restore its workspace backup.')
            if version == 5:
                row = next((item for item in _readings(connection)['entries'] if item['id'] == identifier), None)
            else:
                saved = connection.execute('SELECT snapshot FROM fieldbooks WHERE id=?', (identifier,)).fetchone()
                row = json.loads(saved[0]) if saved else None
            if row is None:
                raise ValueError('The saved reading is unavailable. Restore its workspace backup.')
            validate_readings({'version': 2 if 'photos' in row else 1, 'entries': [row]})
            if row['id'] != identifier:
                raise ValueError('The saved reading does not match its identifier.')
            return row

    def resolve_reading(self, row):
        if not is_reference(row):
            return row
        try:
            original = self.reading(row['id'])
        except (OSError, sqlite3.Error):
            raise ValueError('The saved reading is unavailable. Restore its complete workspace backup.') from None
        version = 2 if 'photos' in row else 1
        return expand_book({'version': version, 'entries': [row]},
                           {'version': version, 'entries': [original]})['entries'][0]

    def expand_browser_readings(self, book):
        """Resolve browser references without changing old copies."""
        return expand_book(book, self.readings())

    def import_readings(self, incoming, *, browser_limit=False):
        validate_book(incoming)
        if not incoming['entries']:
            result = self.readings()
            return validate_book(compact_book(result)) if browser_limit else result
        with self.book._connection(True, 6) as connection:
            merged = _strict_merge(_readings(connection), incoming)
            if browser_limit:
                validate_book(compact_book(merged))
            for digest, reference in referenced_photos(merged['entries']).items():
                facts, _ = read_photo(connection, digest)
                check_reference(reference, facts)
            _save(connection, merged)
            return merged

    def save_large_reading(self, current, entry):
        """Commit a large source before returning only its compact browser reference."""
        validate_book(current)
        validate_readings({'version': 1, 'entries': [entry]})
        with self.book._connection(True, 6) as connection:
            merged = _strict_merge(_readings(connection), current)
            merged = _strict_merge(merged, {'version': 1, 'entries': [entry]})
            compact = validate_book(compact_book(merged))
            for digest, reference in referenced_photos(merged['entries']).items():
                facts, _ = read_photo(connection, digest)
                check_reference(reference, facts)
            _save(connection, merged)
            return compact

    def backup_bytes(self, current=None):
        if not self.book.path.is_file():
            readings = expand_book(validate_book(current or dict(EMPTY_BOOK, entries=[])), dict(EMPTY_BOOK, entries=[]))
            refs = referenced_photos(readings['entries'])
            if refs:
                raise ValueError('An original photo is missing. Restore its photo-inclusive backup.')
            encoded = json.dumps({'format': 'clovis-workspace', 'version': 1, 'readings': readings, 'projects': []}, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
            return archive_bytes('workspace.json', encoded, refs, None)
        with self.book._connection() as connection:
            connection.execute('BEGIN')
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            readings = _readings(connection) if version >= 5 else dict(EMPTY_BOOK, entries=[])
            if current is not None:
                readings = _strict_merge(readings, current)
            ids = [row[0] for row in connection.execute('SELECT id FROM projects ORDER BY code_key')]
            if len(ids) > MAX_PROJECTS:
                raise ValueError('This workspace exceeds the 100-project backup allowance.')
            projects = [json.loads(self.book._export(connection, identifier)) for identifier in ids]
            refs = _all_refs(readings, projects)
            encoded = json.dumps({'format': 'clovis-workspace', 'version': 1,
                                  'readings': readings, 'projects': projects},
                                 ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
            if len(encoded) > MAX_WORKSPACE_BYTES:
                raise ValueError('This workspace exceeds the 64 MB notes and revision allowance.')
            return archive_bytes('workspace.json', encoded, refs, _SnapshotPhotos(connection))

    def restore_backup(self, data, current=None, *, browser_limit=False):
        encoded, assets = read_archive(data, 'workspace.json', MAX_WORKSPACE_BYTES)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('The workspace repeats a JSON field.')
                result[key] = value
            return result
        try:
            bundle = json.loads(encoded, object_pairs_hook=unique)
        except (ValueError, RecursionError):
            raise ValueError('Use a valid Clovis workspace backup.') from None
        if (not isinstance(bundle, dict) or set(bundle) != {'format', 'version', 'readings', 'projects'}
                or bundle['format'] != 'clovis-workspace' or type(bundle['version']) is not int
                or bundle['version'] != 1 or not isinstance(bundle['projects'], list)
                or len(bundle['projects']) > MAX_PROJECTS):
            raise ValueError('This is not a supported workspace backup.')
        # Portable archives contain originals, not machine-local references.
        incoming = expand_book(validate_readings(bundle['readings']), dict(EMPTY_BOOK, entries=[]))
        # Verify project envelopes before examining photo references. Full record and
        # revision validation is performed by DigBook.restore inside the transaction.
        projects = bundle['projects']
        try:
            ids = [p['project']['id'] for p in projects]
            if any(not isinstance(identifier, str) for identifier in ids) or len(set(ids)) != len(ids):
                raise ValueError('The workspace repeats a project identifier.')
            refs = _all_refs(incoming, projects)
        except (KeyError, TypeError, AttributeError):
            raise ValueError('The workspace contains an invalid project.') from None
        check_archive_references(refs, assets)
        with self.book._connection(True, 6) as connection:
            merged = _strict_merge(_readings(connection), incoming)
            if current is not None:
                merged = _strict_merge(merged, current)
            if browser_limit:
                validate_book(compact_book(merged))
            insert_photos(connection, assets)
            results = []
            for project in projects:
                project_refs = _project_refs(project)
                project_assets = {digest: assets[digest] for digest in project_refs}
                results.append(self.book.restore(json.dumps(project, ensure_ascii=False, allow_nan=False),
                                                 _photos=project_assets, _connection=connection))
            for digest, reference in referenced_photos(merged['entries']).items():
                facts, _ = read_photo(connection, digest)
                check_reference(reference, facts)
            _save(connection, merged)
            return {'projects': results, 'readings': len(merged['entries']), 'book': merged}
