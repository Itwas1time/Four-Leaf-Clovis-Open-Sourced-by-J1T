"""Merge browser entries while resolving compact workspace references."""
from core.fieldbook import merge_entries as merge_plain, validate_book
from core.workspace_storage import WorkspaceStorage


def merge_entries(book, entries):
    validate_book(book)
    existing = {row['id']: row for row in book['entries']}
    store = WorkspaceStorage()
    normalized = []
    for row in entries:
        full = store.resolve_reading(row)
        previous = existing.get(row['id'])
        if previous:
            old = store.resolve_reading(previous)
            if {key: value for key, value in old.items() if key != 'created'} != {key: value for key, value in full.items() if key != 'created'}:
                raise ValueError('A saved investigation has conflicting notes or photos under the same identifier.')
            normalized.append(previous)
        else:
            normalized.append(row)
    return merge_plain(book, normalized)
