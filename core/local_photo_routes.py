"""Local original-photo and complete fieldbook backup transport."""
from io import BytesIO
import sqlite3
from threading import BoundedSemaphore
from urllib.parse import unquote

from core.local_photos import PhotoStore,MAX_PHOTO_BYTES,photo_name
from core.fieldbook import MAX_BYTES
from core.fieldbook_backups import export_book,restore_book,parse_book,MAX_ZIP_BYTES

_READERS=BoundedSemaphore(2)


def register_routes(server):
    from flask import request,jsonify,Response,send_file
    from werkzeug.exceptions import RequestEntityTooLarge

    @server.post('/clovis/photos')
    def upload_local_photo():
        if request.headers.get('X-Clovis-Photo')!='1' or request.mimetype!='application/octet-stream':
            return jsonify(error='Choose a photo through Add a photo.'),415
        if not _READERS.acquire(blocking=False):
            return jsonify(error='Two photos are being checked. Try again when they finish.'),429
        try:
            request.max_content_length=MAX_PHOTO_BYTES
            name=photo_name(unquote(request.headers.get('X-Clovis-Photo-Name',''),errors='strict'))
            reference=PhotoStore().add(request.get_data(cache=False),name)
            return jsonify(reference)
        except RequestEntityTooLarge:
            return jsonify(error='Choose a photo under 5 MB.'),413
        except (ValueError,OSError,sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error,ValueError) else 'The photo could not be saved locally.'),400
        finally:
            _READERS.release()

    def photo_response(digest,download=False):
        try:
            facts,data=PhotoStore().get(digest)
            if download:
                name=photo_name(request.args.get('name','photo'))
                return send_file(BytesIO(data),mimetype=facts['media_type'],as_attachment=True,download_name=name)
            return Response(data,mimetype=facts['media_type'],headers={
                'Cache-Control':'private, max-age=3600','Cross-Origin-Resource-Policy':'same-origin'})
        except (ValueError,OSError,sqlite3.Error):
            return Response('The original photo is unavailable. Restore its photo-inclusive backup.',status=404,mimetype='text/plain')

    @server.get('/clovis/photos/<digest>')
    def view_local_photo(digest):
        return photo_response(digest)

    @server.get('/clovis/photos/<digest>/download')
    def download_local_photo(digest):
        return photo_response(digest,True)

    @server.post('/clovis/fieldbook/backup')
    def download_fieldbook_backup():
        if request.headers.get('X-Clovis-Fieldbook-Backup')!='1' or request.mimetype!='application/json':
            return jsonify(error='Use Download this fieldbook.'),415
        try:
            book=parse_book(request.get_data())
            data,media,name=export_book(book,PhotoStore())
            return send_file(BytesIO(data),mimetype=media,as_attachment=True,download_name=name)
        except (ValueError,OSError,sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error,ValueError) else 'The fieldbook backup could not be created.'),400

    @server.post('/clovis/fieldbook/restore')
    def restore_fieldbook_backup():
        if request.headers.get('X-Clovis-Fieldbook-Backup')!='1' or request.mimetype!='multipart/form-data':
            return jsonify(error='Use Restore a fieldbook.'),415
        try:
            request.max_content_length=MAX_ZIP_BYTES+MAX_BYTES+65536
            request.max_form_memory_size=MAX_BYTES+65536
            request.max_form_parts=4
            if (set(request.files)!={'backup'} or len(request.files.getlist('backup'))!=1
                    or set(request.form)!={'current'} or len(request.form.getlist('current'))!=1):
                raise ValueError('Choose one fieldbook backup.')
            current=parse_book(request.form['current'])
            data=request.files['backup'].stream.read(MAX_ZIP_BYTES+1)
            merged=restore_book(data,current,PhotoStore())
            return jsonify(book=merged)
        except RequestEntityTooLarge:
            return jsonify(error='The fieldbook exceeds its notes and 100 MB photo allowance.'),413
        except (ValueError,OSError,sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error,ValueError) else 'The fieldbook could not be restored. Existing work was preserved.'),400

    @server.post('/clovis/fieldbook/question-backup')
    def download_photo_question():
        if request.headers.get('X-Clovis-Fieldbook-Backup')!='1' or request.mimetype!='application/json':
            return jsonify(error='Use Download question packet.'),415
        try:
            from core.fieldbook import validate_book
            from core.expert_questions import prepare_question
            from core.fieldbook_backups import export_question
            value=request.get_json()
            if not isinstance(value,dict) or set(value)!={'book','selected','question','comparison','detail','draft'}:
                raise ValueError('Preview the current question before downloading it.')
            book=validate_book(value['book'])
            row=next((row for row in book['entries'] if row['id']==value['selected']),None)
            if row is None:raise ValueError('Choose saved notes for this question.')
            packet=prepare_question(row,value['question'],value['comparison'],value['detail'])
            if value['draft']!={'source_id':row['id'],'packet_id':packet['id']}:
                raise ValueError('Preview the current question before downloading it.')
            data,media,name=export_question(packet,PhotoStore())
            return send_file(BytesIO(data),mimetype=media,as_attachment=True,download_name=name)
        except (ValueError,OSError,sqlite3.Error) as error:
            return jsonify(error=str(error) if isinstance(error,ValueError) else 'The question packet could not be downloaded.'),400
