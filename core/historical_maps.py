"""Bounded public-place map research using the documented Library of Congress API.

https://www.loc.gov/apis/json-and-yaml/requests/endpoints/
No user URL is fetched. Redirects are refused; image URLs are only rendered by browsers.
"""
import json
import re
import time
import secrets
from threading import Lock, BoundedSemaphore
from urllib.parse import urlsplit

import requests
from core.us_places import get_place, STATE_NAMES

MAX_BYTES = 2_000_000
MAX_RESULTS = 12
_CACHE = {}
_LOCK = Lock()
_PROVIDER_GATE = BoundedSemaphore(2)


def remember_archive(value, state, geoid):
    token=secrets.token_urlsafe(24)
    with _LOCK:
        now=time.monotonic()
        for old in list(_CACHE):
            if now-_CACHE[old][0]>1800: _CACHE.pop(old,None)
        while len(_CACHE)>=128: _CACHE.pop(next(iter(_CACHE)))
        _CACHE[token]=(now,state,geoid,value)
    return token


def current_archive(token,state,geoid):
    if not isinstance(token,str) or len(token)>100: return None
    with _LOCK:
        row=_CACHE.get(token)
    return row[3] if row and row[1:3]==(state,geoid) and time.monotonic()-row[0]<1800 else None


def validated_note_context(context,state,geoid):
    """Resolve server-owned note metadata, tied to the current Census place."""
    if not get_place(geoid,state) or not isinstance(context,dict): return None
    value=current_archive(context.get('token'),state,geoid)
    return dict(value) if isinstance(value,dict) and set(value)=={'title','date','source','notes'} else None


def public_url(value, image=False):
    if not isinstance(value, str) or len(value) > 2000:
        return ''
    try:
        p = urlsplit(value)
        hosts = {'www.loc.gov', 'loc.gov', 'tile.loc.gov'} if image else {'www.loc.gov', 'loc.gov'}
        return value if p.scheme == 'https' and p.hostname in hosts and not p.username and not p.password and p.port in (None, 443) else ''
    except ValueError:
        return ''


def _fetch(path, params):
    if not _PROVIDER_GATE.acquire(blocking=False):
        raise ValueError('The map provider is already serving two requests. Wait a moment, then try again.')
    try:
        return _fetch_impl(path,params)
    finally:
        _PROVIDER_GATE.release()


def _fetch_impl(path, params):
    """Read at most 2 MB, with connection/read and total streaming bounds."""
    deadline = time.monotonic() + 14
    with requests.Session() as session:
        session.trust_env=False
        return _read_response(session,path,params,deadline)


def _read_response(session,path,params,deadline):
    with session.get('https://www.loc.gov' + path, params=params, timeout=(3, 5),
                      allow_redirects=False, stream=True,
                      headers={'Accept': 'application/json', 'User-Agent': 'Clovis-public-map-workspace/1.0'}) as response:
        if response.status_code in (403, 429):
            raise ValueError(f'Library of Congress refused the API request (HTTP {response.status_code}). Try later; local map viewing is available below.')
        if response.status_code != 200:
            raise ValueError(f'Library of Congress returned HTTP {response.status_code}. Local map viewing is available below.')
        if 'json' not in response.headers.get('Content-Type', '').lower():
            raise ValueError('Library of Congress returned a non-JSON response, possibly an access challenge. Local map viewing is available below.')
        parts, size = [], 0
        for block in response.iter_content(32768):
            size += len(block)
            if size > MAX_BYTES or time.monotonic() > deadline:
                raise ValueError('Library of Congress response exceeded the workspace limits. Try later.')
            parts.append(block)
        data = json.loads(b''.join(parts))
        if not isinstance(data, dict):
            raise ValueError('Library of Congress returned an unsupported response.')
        return data


def _text(value, limit=400):
    return str(value)[:limit] if isinstance(value, (str, int)) else ''


def _image(value):
    values = value if isinstance(value, list) else [value]
    safe = [public_url(v, image=True) for v in values]
    return next((v for v in reversed(safe) if v), '')


def search_maps(state, geoid):
    place = get_place(geoid, state)
    if not place:
        raise ValueError('Choose a public Census town before searching maps.')
    town = re.sub(r' (?:city and borough|city|town|village|borough|municipio|CDP|zona urbana)(?: \(balance\))?$', '', place['name'], flags=re.I)
    query = town + ' ' + STATE_NAMES[state]
    try:
        data = _fetch('/maps/', {'q': query, 'fo': 'json', 'c': MAX_RESULTS, 'at': 'results,pagination'})
    except (requests.RequestException, json.JSONDecodeError):
        return {'status': 'unavailable', 'message': 'The Library of Congress API could not be reached from this server. This does not mean there are no maps. Open a local map image below.', 'results': [], 'query': query}
    except ValueError as exc:
        return {'status': 'unavailable', 'message': str(exc), 'results': [], 'query': query}
    rows = []
    results=data.get('results')
    if not isinstance(results,list):
        return {'status':'unavailable','results':[], 'query':query,'message':'Library of Congress returned an unsupported results structure. Try later or use a local image.'}
    for row in results[:MAX_RESULTS]:
        if not isinstance(row, dict):
            continue
        url = public_url(row.get('url')) or public_url(row.get('id'))
        p = urlsplit(url)
        if not re.fullmatch(r'/item/[A-Za-z0-9_-]+/?', p.path):
            continue
        rows.append({'id': p.path.strip('/').split('/')[-1], 'title': _text(row.get('title')) or 'Untitled map',
                     'date': _text(row.get('date'), 80) or 'Date not supplied', 'url': url,
                     'image': _image(row.get('image_url', [])), 'source': 'Library of Congress'})
    return {'status': 'ready' if rows else 'no_matches', 'results': rows, 'query': query,
            'message': f'{len(rows)} map records for {query}. Search relevance is not proof of local coverage; check the title, date and map extent.' if rows else f'No usable digitized map records returned for {query}. Collection coverage is incomplete; try a local image.'}


def map_sheets(item_id):
    if not isinstance(item_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', item_id):
        raise ValueError('Select a map record from the search results.')
    try:
        data = _fetch('/item/' + item_id + '/', {'fo': 'json', 'at': 'resources,item'})
    except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
        return [], 'Map sheets could not be loaded from Library of Congress. The record preview may still be available.'
    sheets = []
    resources=data.get('resources')
    resources=resources if isinstance(resources,list) else []
    for resource in resources[:24]:
        if not isinstance(resource, dict):
            continue
        groups = resource.get('files')
        groups = groups if isinstance(groups, list) else []
        for group in groups[:60]:
            files = group if isinstance(group, list) else [group]
            images = [f for f in files if isinstance(f, dict) and f.get('mimetype') in ('image/jpeg', 'image/png') and public_url(f.get('url'), True)]
            if images:
                # Prefer an inspectable image without selecting the largest archival master.
                candidate = min(images, key=lambda f: abs((f.get('width') if isinstance(f.get('width'), (int,float)) else 1200) - 1600))
                sheets.append({'label': f'Sheet {len(sheets)+1}', 'image': public_url(candidate['url'], True)})
            if len(sheets) >= 60:
                break
        if len(sheets) >= 60:
            break
        fallback = _image(resource.get('image'))
        if fallback and not sheets:
            sheets.append({'label': 'Resource preview', 'image': fallback})
    return sheets, f'{len(sheets)} viewable sheets loaded (up to 60).' if sheets else 'No JPEG/PNG sheet previews were supplied. Use the record preview or a local image.'
