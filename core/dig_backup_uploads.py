"""Restore bounded project ZIPs directly, without a whole-file Dash payload."""
import sqlite3

from core.dig_records import DigBook,MAX_BACKUP_ZIP_BYTES


def register_routes(server):
    from flask import jsonify,request
    from werkzeug.exceptions import RequestEntityTooLarge

    @server.post('/clovis/dig-records/restore-backup')
    def restore_project_backup():
        if request.headers.get('X-Clovis-Project-Backup')!='1' or request.mimetype!='application/zip':
            return jsonify(error='Choose a project ZIP through Restore project backup.'),415
        # The ordinary JSON request limit remains unchanged. This route accepts
        # only a bounded ZIP; DigBook also bounds its single expanded JSON file.
        request.max_content_length=MAX_BACKUP_ZIP_BYTES
        try:
            result=DigBook().restore_backup(request.get_data(cache=False))
            return jsonify(result)
        except RequestEntityTooLarge:
            return jsonify(error='The backup exceeds its 32 MB notes and 100 MB photo allowance.'),413
        except ValueError as error:
            return jsonify(error=str(error)),400
        except (OSError,sqlite3.Error):
            return jsonify(error='The local project backup could not be restored. Existing records were preserved.'),400
