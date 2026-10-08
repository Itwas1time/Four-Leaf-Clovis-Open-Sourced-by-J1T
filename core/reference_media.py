"""Fetch a public-domain museum image only for a selected bundled record."""
from collections import OrderedDict
from collections import deque
from io import BytesIO
import json
import re
from threading import BoundedSemaphore, Lock
from time import monotonic
from urllib.parse import urlsplit
import requests
from PIL import Image
import warnings

API='https://collectionapi.metmuseum.org/public/collection/v1/objects/'
_CACHE=OrderedDict()
_LOCK=Lock()
_GATE=BoundedSemaphore(2)
_FOSSIL_CACHE=OrderedDict()
_FOSSIL_REQUESTS=deque()


def smithsonian_image(record):
    """Use the same individually CC0 asset at a useful, bounded display size.

    Smithsonian documents IDS deliveryService's id and max parameters at
    https://sirismm.si.edu/siris/ImageDisplay.htm. No arbitrary image ID is read
    from an input; this helper receives a verified bundled source record.
    """
    if not isinstance(record,dict) or record.get('image_verified') is not True:
        return ''
    value=record.get('image_url')
    if not isinstance(value,str) or len(value)>2000:
        return ''
    try:
        p=urlsplit(value)
        if p.scheme!='https' or p.hostname!='ids.si.edu' or p.username or p.password or p.port not in (None,443) or p.query or p.fragment:
            return ''
        match=re.fullmatch(r'/ids/deliveryService/id/(ark:/65665/m3[a-f0-9]{32})/90',p.path)
        if not match:
            return ''
        # Keep the source's canonical asset-path form; use its supported
        # bounded size slot rather than a query-based variant.
        return 'https://ids.si.edu/ids/deliveryService/id/'+match[1]+'/1600'
    except ValueError:
        return ''


def fossil_image_bytes(record):
    """Fetch only the catalog's individually CC0 asset; bounded, memory-only.

    This supports browsers that reject the museum's cross-origin delivery
    response. No uploaded image, note, location or arbitrary URL is accepted.
    """
    url=smithsonian_image(record)
    if not url:
        return None,'','This specimen has no verified CC0 image in the catalog.'
    with _LOCK:
        now=monotonic()
        cached=_FOSSIL_CACHE.get(url)
        if cached and now-cached[0]<600:
            _FOSSIL_CACHE.move_to_end(url)
            return cached[1],cached[2],''
        while _FOSSIL_REQUESTS and now-_FOSSIL_REQUESTS[0]>=60:
            _FOSSIL_REQUESTS.popleft()
        if len(_FOSSIL_REQUESTS)>=10:
            return None,'','Museum photograph request limit reached. Try again in a minute.'
        _FOSSIL_REQUESTS.append(now)
    if not _GATE.acquire(blocking=False):
        return None,'','Two museum photographs are loading. Try again in a moment.'
    try:
        started=monotonic()
        with requests.Session() as session:
            session.trust_env=False
            with session.get(url,timeout=(3,5),allow_redirects=False,stream=True,
                             headers={'User-Agent':'Clovis-public-reference-library/1.0','Accept':'image/jpeg,image/png,image/webp'}) as response:
                if response.status_code!=200 or response.headers.get('Content-Type','').split(';',1)[0].lower() not in ('image/jpeg','image/png','image/webp'):
                    return None,'','The museum photograph service could not provide this image.'
                chunks=[]
                size=0
                for chunk in response.iter_content(16384):
                    size+=len(chunk)
                    if size>8_000_000 or monotonic()-started>12:
                        return None,'','The museum photograph exceeded its display limits.'
                    chunks.append(chunk)
                data=b''.join(chunks)
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>4_000_000:
                    return None,'','The museum photograph exceeded its display limits.'
                media_type={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[image.format]
                image.verify()
        with _LOCK:
            _FOSSIL_CACHE[url]=(monotonic(),data,media_type)
            while sum(len(item[1]) for item in _FOSSIL_CACHE.values())>24_000_000 or len(_FOSSIL_CACHE)>8:
                _FOSSIL_CACHE.popitem(last=False)
        return data,media_type,''
    except (requests.RequestException,OSError,ValueError,Image.DecompressionBombWarning,Image.DecompressionBombError):
        return None,'','The museum photograph could not load. Its catalog facts remain readable.'
    finally:
        _GATE.release()


def register_image_routes(server):
    """Local, catalog-ID-only image display endpoint; never a general proxy."""
    from flask import Response
    from core.fossil_reference_catalog import get_fossil

    @server.get('/api/reference/fossil-image/<record_id>')
    def clovis_fossil_image(record_id):
        if not re.fullmatch(r'paleo:[A-Za-z0-9_-]{1,160}',record_id):
            return Response('Choose a catalog specimen.',status=404,mimetype='text/plain')
        record=get_fossil(record_id)
        if not record:
            return Response('Choose a catalog specimen.',status=404,mimetype='text/plain')
        data,media_type,status=fossil_image_bytes(record)
        if data is None:
            return Response(status,status=502,mimetype='text/plain',headers={'Cache-Control':'no-store'})
        return Response(data,mimetype=media_type,headers={'Cache-Control':'private, max-age=60','Cross-Origin-Resource-Policy':'same-origin'})


def image_url(value):
    if not isinstance(value,str) or len(value)>2000 or any(ord(c)<32 for c in value):
        return ''
    try:
        parsed=urlsplit(value)
        return value if parsed.scheme=='https' and parsed.hostname=='images.metmuseum.org' and not parsed.username and not parsed.password and parsed.port in (None,443) else ''
    except ValueError:
        return ''


def parse_image(payload,object_id):
    if not isinstance(payload,dict) or payload.get('isPublicDomain') is not True or type(payload.get('objectID')) is not int or str(payload['objectID'])!=object_id:
        return ''
    return image_url(payload.get('primaryImageSmall')) or image_url(payload.get('primaryImage'))


def museum_image(record):
    """Record must come from the local catalog; no user URL is accepted."""
    if not isinstance(record,dict) or record.get('is_public_domain') is not True:
        return '', 'This catalog record does not offer a public-domain photograph.'
    object_id=record.get('source_id')
    if not isinstance(object_id,str) or not re.fullmatch(r'[1-9][0-9]{0,9}',object_id) or record.get('id')!='met:'+object_id:
        return '', 'Choose a museum record from this library.'
    seeded=image_url(record.get('image_url')) if record.get('image_verified') is True else ''
    if seeded:
        return seeded, 'Public-domain photograph · The Metropolitan Museum of Art'
    with _LOCK:
        cached=_CACHE.get(object_id)
        if cached and monotonic()-cached[0]<86400:
            _CACHE.move_to_end(object_id)
            return cached[1:]
    if not _GATE.acquire(blocking=False):
        return '', 'Two photographs are loading. Try again in a moment.'
    try:
        with requests.Session() as session:
            session.trust_env=False
            started=monotonic()
            with session.get(API+object_id,timeout=(3,5),allow_redirects=False,stream=True,
                             headers={'Accept':'application/json','User-Agent':'Clovis-public-reference-library/1.0'}) as response:
                if response.status_code!=200 or 'json' not in response.headers.get('Content-Type','').lower():
                    return '', 'The museum image service is unavailable. The local record remains readable.'
                blocks=[]
                size=0
                for block in response.iter_content(16384):
                    size+=len(block)
                    if size>250000 or monotonic()-started>12:
                        return '', 'The museum image response exceeded its limits. The local record remains readable.'
                    blocks.append(block)
                image=parse_image(json.loads(b''.join(blocks)),object_id)
        status='Public-domain photograph · The Metropolitan Museum of Art' if image else 'The museum did not provide a public-domain photograph for this record.'
        with _LOCK:
            _CACHE[object_id]=(monotonic(),image,status)
            while len(_CACHE)>256:
                _CACHE.popitem(last=False)
        return image,status
    except (requests.RequestException,ValueError,UnicodeError):
        return '', 'The museum photograph could not load. The local record remains readable.'
    finally:
        _GATE.release()
