"""Offline, coordinate-free Library of Congress Sanborn atlas metadata.

Town matches use original catalog City_text and State_text only. They describe
catalog indexing, not map extent, complete coverage or present-day features.
"""
from functools import lru_cache
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

from core.us_places import STATE_NAMES

DATA = Path(__file__).resolve().parents[1] / 'atlas/gui/data/sanborn_catalog.sqlite'
PAGE_SIZE = 12


def normalize_town(value):
    if not isinstance(value, str) or len(value) > 240 or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        return ''
    value = unicodedata.normalize('NFKC', value).casefold()
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', value)).strip()


def census_town(value):
    if not isinstance(value, str):
        return ''
    return re.sub(r' (?:city and borough|city|town|village|borough|municipio|CDP|zona urbana)(?: \(balance\))?$', '', value, flags=re.I)


@contextmanager
def _connect():
    connection = sqlite3.connect(DATA.as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


@lru_cache(maxsize=1)
def _summary():
    with _connect() as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def catalog_stats(state=None, town=None):
    """Source summary or exact bounded regional aggregates (never a fallback)."""
    summary = json.loads(json.dumps(_summary()))
    if state is None:
        summary.update(maps=summary['records'], towns=summary['town_state_pairs'])
        return summary
    if not isinstance(state, str) or state not in STATE_NAMES:
        raise ValueError('Choose a valid US state or territory.')
    key = normalize_town(town) if town is not None else None
    where, params = 'p.state=?', [state]
    if key is not None:
        where += ' AND p.town_key=?'
        params.append(key)
    with _connect() as connection:
        maps = connection.execute('SELECT count(DISTINCT r.id) FROM records r JOIN places p ON p.id=r.id WHERE '+where, params).fetchone()[0]  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        towns = connection.execute("SELECT count(DISTINCT p.town_key) FROM places p WHERE p.town_key!='' AND "+where, params).fetchone()[0]  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        dates = []
        for direction in ('ASC', 'DESC'):
            row = connection.execute('SELECT r.date FROM records r JOIN places p ON p.id=r.id WHERE '+where+' AND r.sort_year IS NOT NULL ORDER BY r.sort_year '+direction+',r.date '+direction+' LIMIT 1',params).fetchone()  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
            dates.append(row[0] if row else None)
    return {'state': state, 'town': town if key else None, 'maps': maps, 'records': maps,
            'towns': towns, 'states': 1 if maps else 0, 'earliest': dates[0], 'latest': dates[1],
            'snapshot': summary['snapshot'], 'rights': summary['rights'], 'source_url': summary['source_url']}


def search_catalog(state, town='', page=0, scope='town', order='oldest'):
    """Return a bounded page; no network, fuzzy matches or coordinate fields.

    An absent exact town index falls back to explicitly labeled state records.
    Non-digitized records remain useful source citations, without image claims.
    """
    if not isinstance(state, str) or state not in STATE_NAMES:
        raise ValueError('Choose a valid US state or territory.')
    if type(page) is not int or not 0 <= page <= 10000:
        raise ValueError('Choose a valid catalog page.')
    if scope not in ('town', 'state') or order not in ('oldest', 'newest'):
        raise ValueError('Choose a catalog scope and date order.')
    town_key = normalize_town(town)
    exact = scope == 'town' and bool(town_key)
    with _connect() as connection:
        where = 'p.state=?'
        params = [state]
        if exact:
            count = connection.execute('SELECT count(DISTINCT id) FROM places WHERE state=? AND town_key=?', [state, town_key]).fetchone()[0]
            if count:
                where += ' AND p.town_key=?'
                params.append(town_key)
            else:
                exact = False
        total = connection.execute('SELECT count(DISTINCT r.id) FROM records r JOIN places p ON p.id=r.id WHERE ' + where, params).fetchone()[0]  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        direction = 'ASC' if order == 'oldest' else 'DESC'
        rows = connection.execute('SELECT DISTINCT r.* FROM records r JOIN places p ON p.id=r.id WHERE ' + where + ' ORDER BY r.sort_year IS NULL, r.sort_year ' + direction + ',r.date ' + direction + ',r.id LIMIT ? OFFSET ?', params + [PAGE_SIZE, page * PAGE_SIZE]).fetchall()  # nosec B608 # Fixed SQL clauses and placeholders; values use bound parameters.
    results = [{**dict(row), 'source': 'Library of Congress · Sanborn', 'catalog': True, 'digitized': bool(row['digitized'])} for row in rows]
    for row in results:
        row.pop('sort_year', None)
    return {'results': results, 'total': total, 'page': page, 'pages': pages,
            'scope': 'town' if exact else 'state', 'exact_town': exact,
            'requested_town': town if town_key else '',
            'state': state, 'snapshot': catalog_stats()['snapshot']}
