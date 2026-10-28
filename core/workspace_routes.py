"""Bounded, local-only workspace archive transport."""
from io import BytesIO
import sqlite3
from threading import BoundedSemaphore

from core.fieldbook import MAX_BYTES
from core.fieldbook_backups import parse_book
from core.local_photos import MAX_ARCHIVE_PHOTO_BYTES, ZIP_OVERHEAD
from core.workspace_storage import MAX_WORKSPACE_BYTES, WorkspaceStorage
from core.large_readings import compact_book

MAX_UPLOAD = MAX_WORKSPACE_BYTES + MAX_ARCHIVE_PHOTO_BYTES + ZIP_OVERHEAD
_READERS = BoundedSemaphore(2)


def register_routes(server):
    from flask import jsonify, request, send_file
    from werkzeug.exceptions import RequestEntityTooLarge

    @server.post('/clovis/workspace/sync-readings')
    def sync_readings():
        if request.headers.get('X-Clovis-Workspace') != '1' or request.mimetype != 'application/json':
            return jsonify(error='Use Sync saved readings.'), 415
        try:
            current = parse_book(request.get_data())
            return jsonify(book=compact_book(WorkspaceStorage().import_readings(current, browser_limit=True)))
        except (ValueError, OSError, sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error, ValueError) else 'Readings could not be synced. Existing work was preserved.'), 400

    @server.post('/clovis/workspace/backup')
    def backup():
        if request.headers.get('X-Clovis-Workspace') != '1' or request.mimetype != 'application/json':
            return jsonify(error='Use Download complete workspace.'), 415
        try:
            current = parse_book(request.get_data())
            data = WorkspaceStorage().backup_bytes(current)
            return send_file(BytesIO(data), mimetype='application/zip', as_attachment=True, download_name='clovis-workspace.zip')
        except (ValueError, OSError, sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error, ValueError) else 'The workspace could not be backed up.'), 400

    @server.post('/clovis/workspace/restore')
    def restore():
        if request.headers.get('X-Clovis-Workspace') != '1' or request.mimetype != 'multipart/form-data':
            return jsonify(error='Use Restore complete workspace.'), 415
        if not _READERS.acquire(blocking=False):
            return jsonify(error='Two workspace backups are being checked. Try again shortly.'), 429
        try:
            request.max_content_length = MAX_UPLOAD + MAX_BYTES + 65536
            request.max_form_memory_size = MAX_BYTES + 65536
            request.max_form_parts = 4
            if (set(request.files) != {'backup'} or len(request.files.getlist('backup')) != 1
                    or set(request.form) != {'current'} or len(request.form.getlist('current')) != 1):
                raise ValueError('Choose one workspace backup.')
            current = parse_book(request.form['current'])
            data = request.files['backup'].stream.read(MAX_UPLOAD + 1)
            result = WorkspaceStorage().restore_backup(data, current, browser_limit=True)
            result['book'] = compact_book(result['book'])
            return jsonify(result)
        except RequestEntityTooLarge:
            return jsonify(error='The workspace backup exceeds its size allowance.'), 413
        except (ValueError, OSError, sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error, ValueError) else 'The workspace could not be restored. Existing work was preserved.'), 400
        finally:
            _READERS.release()
