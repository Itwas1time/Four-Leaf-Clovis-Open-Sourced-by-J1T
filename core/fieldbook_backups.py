"""Fieldbook JSON compatibility and complete original-photo ZIP portability."""
import json

from core.fieldbook import MAX_BYTES,validate_book,merge_entries
from core.local_photos import (PhotoStore,MAX_ARCHIVE_PHOTO_BYTES,ZIP_OVERHEAD,
    referenced_photos,archive_bytes,read_archive,check_archive_references,check_reference)
from core.web_security import validate_json

MAX_ZIP_BYTES=MAX_BYTES+MAX_ARCHIVE_PHOTO_BYTES+ZIP_OVERHEAD


def parse_book(encoded):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('The fieldbook repeats a JSON field.')
            result[key]=value
        return result
    validate_json(encoded)
    return validate_book(json.loads(encoded,object_pairs_hook=unique))


def export_book(book,store=None):
    validate_book(book)
    references=referenced_photos(book['entries'])
    encoded=json.dumps(book,ensure_ascii=False,indent=2).encode('utf-8')
    if len(encoded)>MAX_BYTES:
        encoded=json.dumps(book,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if not references:return encoded,'application/json','clovis-fieldbook.json'
    data=archive_bytes('fieldbook.json',encoded,references,store or PhotoStore())
    return data,'application/zip','clovis-fieldbook.zip'


def restore_book(data,current,store=None):
    if not isinstance(data,bytes) or len(data)>MAX_ZIP_BYTES:
        raise ValueError('Choose a fieldbook JSON or a photo-inclusive ZIP within the 100 MB photo allowance.')
    if data.startswith(b'PK'):
        encoded,assets=read_archive(data,'fieldbook.json',MAX_BYTES)
    else:
        if len(data)>MAX_BYTES:raise ValueError('Choose a fieldbook JSON under 750 KB, or a photo-inclusive ZIP.')
        encoded,assets=data.decode('utf-8'),{}
    incoming=parse_book(encoded)
    references=referenced_photos(incoming['entries'])
    check_archive_references(references,assets)
    merged=merge_entries(current,incoming['entries'])
    store=store or PhotoStore()
    for digest,reference in referenced_photos(merged['entries']).items():
        facts=assets[digest][0] if digest in assets else store.get(digest)[0]
        check_reference(reference,facts)
    # Validation and merge conflicts are resolved before adding any files.
    store.import_assets(assets)
    return merged


def export_question(packet,store=None):
    from core.expert_questions import question_first_markdown,_escaped
    from core.local_photos import EXTENSIONS
    text=question_first_markdown(packet)
    references=referenced_photos([packet])
    if not references:return text.encode('utf-8'),'text/markdown','clovis-question-packet.md'
    text+='\n\n## Original photos recorded with these notes\n\n'
    for row in packet['photos']:
        path='photos/'+row['sha256']+'.'+EXTENSIONS[row['media_type']]
        text+='Original filename: '+_escaped(row['name'])+'\n\n'
        if row['caption']:text+='Recorded caption: '+_escaped(row['caption'])+'\n\n'
        text+='!['+_escaped(row['caption'] or row['name'])+']('+path+')\n\n'
    return archive_bytes('question.md',text.encode('utf-8'),references,store or PhotoStore()),'application/zip','clovis-question-packet.zip'
