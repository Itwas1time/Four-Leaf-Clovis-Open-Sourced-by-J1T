"""Bounded browser-to-local-server ZIP transfer, followed by the normal verifier.

Only catalog collections are accepted. Client filenames and filesystem paths
are never used. Upload bodies stay below the ordinary local request limit.
"""
from threading import Lock, Thread
import time

from core import data_pack_jobs as jobs
from core.data_packs import PackStore, _inside

CHUNK_BYTES = 1024 * 1024
IDLE_SECONDS = 30 * 60
_lock = Lock()
_uploads = {}


def _discard(row):
    # Only this operation's unique file, resolved inside its original pack root.
    _inside(row['store'].root, row['path']).unlink(missing_ok=True)


def expire():
    """Reclaim this process's idle transfers, never arbitrary pre-existing files."""
    with _lock:
        for key, row in list(_uploads.items()):
            if time.monotonic() - row['touched'] > IDLE_SECONDS:
                _discard(row)
                del _uploads[key]
                jobs.update(key, state='failed', phase='ZIP transfer expired',
                    message='The local ZIP transfer was idle for 30 minutes. Choose the ZIP again.', finished=time.time_ns())


def begin(identifier, size):
    expire()
    store = PackStore()
    definition = store.definition(identifier)
    if type(size) is not int or size != definition['archive_bytes']:
        raise ValueError('This ZIP size does not match the selected collection snapshot. Choose its official ZIP.')
    key = jobs.reserve(identifier, 'Transferring local ZIP')
    try:
        directory = _inside(store.root, store.root / '.uploads')
        directory.mkdir(parents=True, exist_ok=True)
        path = _inside(store.root, directory / (key + '.zip'))
        with path.open('xb'):
            pass
        with _lock:
            _uploads[key] = {'store': store, 'path': path, 'pack': identifier,
                'size': size, 'received': 0, 'touched': time.monotonic()}
        jobs.update(key, total=size)
        return {'id': key, 'chunk_bytes': CHUNK_BYTES}
    except (OSError, ValueError):
        jobs.update(key, state='failed', phase='ZIP transfer stopped',
            message='Local storage is unavailable. Existing collections and notebook records were preserved.', finished=time.time_ns())
        raise


def append(key, offset, block):
    expire()
    if type(offset) is not int or not isinstance(block, bytes) or not 1 <= len(block) <= CHUNK_BYTES:
        raise ValueError('Send one bounded ZIP chunk at its recorded offset.')
    with _lock:
        row = _uploads.get(key)
        if row is None:
            raise ValueError('This ZIP transfer is no longer active. Choose the ZIP again.')
        if offset != row['received'] or offset + len(block) > row['size']:
            raise ValueError('The ZIP chunks are out of order or exceed the selected snapshot size.')
        with _inside(row['store'].root, row['path']).open('ab') as output:
            output.write(block)
        row.update(received=offset + len(block), touched=time.monotonic())
        jobs.update(key, received=row['received'])
        return row['received']


def cancel(key):
    with _lock:
        row = _uploads.get(key)
        if row is None:
            raise ValueError('This transfer has finished or is being checked. Collection verification continues in the progress panel.')
        _discard(row)
        del _uploads[key]
        jobs.update(key, state='failed', phase='ZIP transfer cancelled',
            message='ZIP transfer cancelled. Existing collections and notebook records were preserved.', finished=time.time_ns())


def finish(key):
    expire()
    with _lock:
        row = _uploads.get(key)
        if row is None or row['received'] != row['size']:
            raise ValueError('The complete ZIP has not arrived. Choose the ZIP again if the transfer was interrupted.')
        del _uploads[key]
    jobs.update(key, phase='Checking local ZIP', received=0, total=0)

    def progress(phase, received, total):
        jobs.update(key, phase=phase, received=received, total=total)

    def run():
        try:
            row['store'].install_archive(row['pack'], row['path'], progress=progress)
            jobs.update(key, state='complete', phase='Installed', finished=time.time_ns(),
                message='Collection installed and verified. Choose Explore in atlas to read its records.')
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else 'ZIP verification stopped. Existing collections and notebook records were preserved. Choose the official ZIP to try again.'
            jobs.update(key, state='failed', phase='ZIP verification stopped', message=message, finished=time.time_ns())
        finally:
            try:
                _discard(row)
            except (OSError, ValueError):
                # A changed/unavailable path must never cause cleanup elsewhere.
                pass

    Thread(target=run, name='clovis-local-collection-check', daemon=True).start()


def register_routes(server):
    from flask import abort, jsonify, request

    def guard():
        if (request.headers.get('Origin') != request.host_url.rstrip('/')
                or request.headers.get('X-Clovis-Local-Upload') != '1'):
            abort(403, description='Use the local Clovis collection picker.')

    def response(operation, status=200):
        guard()
        try:
            result = jsonify(operation())
            result.status_code = status
        except ValueError as error:
            result = jsonify(error=str(error))
            result.status_code = 400
        except OSError:
            result = jsonify(error='Local storage is unavailable. Existing collections and notebook records were preserved.')
            result.status_code = 503
        result.headers['Cache-Control'] = 'no-store'
        return result

    @server.post('/clovis/collections/local')
    def local_collection_begin():
        def start():
            document = request.get_json()
            if not isinstance(document, dict) or set(document) != {'collection', 'bytes'}:
                raise ValueError('Choose one listed collection ZIP.')
            return begin(document['collection'], document['bytes'])
        return response(start, 201)

    @server.put('/clovis/collections/local/<key>')
    def local_collection_chunk(key):
        def chunk():
            offset = request.headers.get('X-Clovis-Offset', '')
            if request.content_length is not None and request.content_length > CHUNK_BYTES:
                abort(413, description='The ZIP transfer chunk is too large.')
            if (request.mimetype != 'application/octet-stream' or not offset.isascii() or not offset.isdecimal()
                    or len(offset) > 10 or request.content_length is None
                    or not 1 <= request.content_length <= CHUNK_BYTES):
                raise ValueError('Send one bounded ZIP chunk at its recorded offset.')
            return {'received': append(key, int(offset), request.stream.read(CHUNK_BYTES + 1))}
        return response(chunk)

    @server.post('/clovis/collections/local/<key>/finish')
    def local_collection_finish(key):
        return response(lambda: (finish(key) or {'id': key}), 202)

    @server.delete('/clovis/collections/local/<key>')
    def local_collection_cancel(key):
        return response(lambda: (cancel(key) or {'cancelled': True}))
