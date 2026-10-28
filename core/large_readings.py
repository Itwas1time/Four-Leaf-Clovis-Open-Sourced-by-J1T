"""Bounded, integrity-checked browser references to full workspace readings."""
import hashlib
import json
import re

from core.fieldbook import MAX_ENTRY_BYTES, _validate_book

MAX_READING_BYTES = 20_000_000
REFERENCE_THRESHOLD = 40_000
_REFERENCE = re.compile(r'Clovis workspace reading SHA256: ([a-f0-9]{64})\Z')


def validate_readings(book):
    return _validate_book(book, MAX_READING_BYTES, MAX_ENTRY_BYTES)


def _digest(row):
    # The capture time may differ when the same source is saved twice.
    payload = {key: value for key, value in row.items() if key != 'created'}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def is_reference(row):
    return bool(_REFERENCE.fullmatch(row['markdown']))


def compact_reading(row):
    if len(row['markdown'].encode('utf-8')) <= REFERENCE_THRESHOLD:
        return row
    return {**row, 'markdown': 'Clovis workspace reading SHA256: ' + _digest(row)}


def compact_book(book):
    validate_readings(book)
    return {**book, 'entries': [compact_reading(row) for row in book['entries']]}


def expand_book(book, stored):
    """Resolve every reference, checking all fields against its saved original."""
    validate_readings(book)
    validate_readings(stored)
    originals = {row['id']: row for row in stored['entries']}
    entries = []
    for row in book['entries']:
        match = _REFERENCE.fullmatch(row['markdown'])
        if not match:
            entries.append(row)
            continue
        original = originals.get(row['id'])
        if not original or _digest(original) != match.group(1):
            raise ValueError('A saved reading is missing or differs from its local original. Restore a complete workspace backup.')
        expected = compact_reading(original)
        if {k: v for k, v in expected.items() if k != 'created'} != {k: v for k, v in row.items() if k != 'created'}:
            raise ValueError('A saved reading reference conflicts with its local original.')
        entries.append(original)
    return validate_readings({**book, 'entries': entries})
