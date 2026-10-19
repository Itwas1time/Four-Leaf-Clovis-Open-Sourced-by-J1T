"""Original local photo bytes, bounded references and portable archive members."""
import hashlib
from io import BytesIO
import re
import sqlite3
import warnings
import zipfile

from PIL import Image

MAX_PHOTO_BYTES=5_000_000
MAX_PHOTO_PIXELS=40_000_000
MAX_RECORD_PHOTOS=12
MAX_ARCHIVE_PHOTOS=1024
MAX_ARCHIVE_PHOTO_BYTES=100_000_000
ZIP_OVERHEAD=1_000_000
MEDIA={'JPEG':('image/jpeg','jpg'),'PNG':('image/png','png'),'WEBP':('image/webp','webp')}
EXTENSIONS={value[0]:value[1] for value in MEDIA.values()}
PHOTO_COLUMNS=('sha256','media_type','bytes','width','height','original')
HASH=re.compile(r'[a-f0-9]{64}\Z')


def photo_name(value):
    if (not isinstance(value,str) or not value.strip() or len(value)>255 or len(value.encode('utf-8'))>1020
            or any(ord(c)<32 or c in '/\\' for c in value) or value in ('.','..')):
        raise ValueError('Use a photo filename of up to 255 characters without a path.')
    return value


def validate_refs(values):
    if not isinstance(values,list) or len(values)>MAX_RECORD_PHOTOS:
        raise ValueError('Keep up to 12 photos with each observation or record.')
    seen=set()
    for row in values:
        if not isinstance(row,dict) or set(row)!={'sha256','media_type','bytes','width','height','name','caption'}:
            raise ValueError('A saved photo reference has an unsupported format.')
        digest=row['sha256']
        if not isinstance(digest,str) or not HASH.fullmatch(digest) or digest in seen:
            raise ValueError('A photo reference is invalid or repeated.')
        seen.add(digest)
        if (not isinstance(row['media_type'],str) or row['media_type'] not in EXTENSIONS or type(row['bytes']) is not int or not 1<=row['bytes']<=MAX_PHOTO_BYTES
                or any(type(row[k]) is not int or row[k]<1 for k in ('width','height'))
                or row['width']*row['height']>MAX_PHOTO_PIXELS):
            raise ValueError('A photo reference has unsupported image dimensions or size.')
        photo_name(row['name'])
        if (not isinstance(row['caption'],str) or len(row['caption'].encode('utf-8'))>1500
                or any(ord(c)<32 and c not in '\n\t' for c in row['caption'])):
            raise ValueError('Shorten this photo caption before saving.')
    return values


def image_facts(data):
    if not isinstance(data,bytes) or not 1<=len(data)<=MAX_PHOTO_BYTES:
        raise ValueError('Choose a still JPEG, PNG or WebP photo under 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if (image.format not in MEDIA or image.width*image.height>MAX_PHOTO_PIXELS
                        or getattr(image,'n_frames',1)!=1):
                    raise ValueError('Choose a still JPEG, PNG or WebP image up to 40 million pixels.')
                facts={'sha256':hashlib.sha256(data).hexdigest(),'media_type':MEDIA[image.format][0],
                    'bytes':len(data),'width':image.width,'height':image.height}
                image.verify()
            # Verify the complete image, not only its header. Original bytes are never re-encoded.
            with Image.open(BytesIO(data)) as image:
                image.load()
    except (OSError,SyntaxError,Image.DecompressionBombWarning,Image.DecompressionBombError):
        raise ValueError('The photo could not be read intact. Choose a still JPEG, PNG or WebP image.') from None
    return facts


def check_reference(reference,facts):
    if any(reference[key]!=facts[key] for key in ('sha256','media_type','bytes','width','height')):
        raise ValueError('A saved photo reference differs from its original file.')


def captioned_refs(references,identifiers,values,prefix):
    import copy
    validate_refs(references)
    if not isinstance(identifiers,list) or not isinstance(values,list) or len(identifiers)!=len(values):
        raise ValueError('Reopen the photo captions before saving.')
    captions={}
    for identifier,value in zip(identifiers,values):
        if (not isinstance(identifier,dict) or set(identifier)!={'type','index'}
                or identifier['type']!=prefix+'-photo-caption' or not isinstance(identifier['index'],str)
                or not HASH.fullmatch(identifier['index']) or identifier['index'] in captions):
            raise ValueError('Reopen the photo captions before saving.')
        captions[identifier['index']]=value
    if set(captions)!={row['sha256'] for row in references}:
        raise ValueError('Wait for the photo captions to finish opening before saving.')
    result=copy.deepcopy(references)
    for row in result:row['caption']=captions[row['sha256']] or ''
    return validate_refs(result)


def read_photo(connection,digest):
    if not isinstance(digest,str) or not HASH.fullmatch(digest):
        raise ValueError('Choose a saved photo.')
    try:
        row=connection.execute('SELECT * FROM photos WHERE sha256=?',(digest,)).fetchone()
    except sqlite3.OperationalError:
        row=None
    if row is None:
        raise ValueError('An original photo is missing. Restore its photo-inclusive ZIP backup.')
    row=dict(row)
    data=row.pop('original')
    if (not isinstance(data,bytes) or row['media_type'] not in EXTENSIONS or len(data)!=row['bytes']
            or hashlib.sha256(data).hexdigest()!=digest):
        raise ValueError('An original saved photo failed its integrity check.')
    with Image.open(BytesIO(data)) as image:
        if image.format not in MEDIA or (MEDIA[image.format][0],image.width,image.height)!=(row['media_type'],row['width'],row['height']):
            raise ValueError('The saved photo metadata differs from its original image.')
    return row,data


def insert_photos(connection,assets):
    for digest,(facts,data) in assets.items():
        if digest!=facts['sha256'] or hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError('An imported photo failed its checksum.')
        existing=connection.execute('SELECT sha256 FROM photos WHERE sha256=?',(digest,)).fetchone()
        if existing:
            old,original=read_photo(connection,digest)
            if old!=facts or original!=data:
                raise ValueError('An imported photo conflicts with an existing original.')
        else:
            connection.execute('INSERT INTO photos VALUES(?,?,?,?,?,?)',
                (digest,facts['media_type'],facts['bytes'],facts['width'],facts['height'],data))


class PhotoStore:
    """Shares the notebook database so project photo restore is one transaction."""
    def __init__(self,path=None):
        from core.dig_records import DigBook
        self.book=DigBook(path)

    def add(self,data,name):
        photo_name(name)
        facts=image_facts(data)
        with self.book._connection(True,4) as connection:
            insert_photos(connection,{facts['sha256']:(facts,data)})
        return {**facts,'name':name,'caption':''}

    def get(self,digest):
        if not self.book.path.is_file():
            raise ValueError('The original photo is not stored on this computer. Restore its ZIP backup.')
        with self.book._connection() as connection:
            return read_photo(connection,digest)

    def check(self,references):
        validate_refs(references)
        for reference in references:
            facts,_=self.get(reference['sha256'])
            check_reference(reference,facts)
        return references

    def import_assets(self,assets):
        if not assets:return
        with self.book._connection(True,4) as connection:
            insert_photos(connection,assets)


def referenced_photos(rows):
    result={}
    for row in rows:
        for reference in validate_refs(row.get('photos',[])):
            digest=reference['sha256']
            if digest in result:check_reference(reference,result[digest])
            result[digest]=reference
    if len(result)>MAX_ARCHIVE_PHOTOS or sum(row['bytes'] for row in result.values())>MAX_ARCHIVE_PHOTO_BYTES:
        raise ValueError('A portable backup supports up to 100 MB of original photos and 1,024 distinct images.')
    return result


def archive_bytes(metadata_name,encoded,references,store):
    out=BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        archive.writestr(metadata_name,encoded,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        for digest,reference in sorted(references.items()):
            facts,data=store.get(digest)
            check_reference(reference,facts)
            archive.writestr('photos/'+digest+'.'+EXTENSIONS[facts['media_type']],data,compress_type=zipfile.ZIP_STORED)
    return out.getvalue()


def read_archive(data,metadata_name,max_metadata_bytes):
    if not isinstance(data,bytes) or len(data)>max_metadata_bytes+MAX_ARCHIVE_PHOTO_BYTES+ZIP_OVERHEAD:
        raise ValueError('The portable backup exceeds its metadata and 100 MB photo allowance.')
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            entries=archive.infolist()
            if not 1<=len(entries)<=MAX_ARCHIVE_PHOTOS+1 or len({info.filename for info in entries})!=len(entries):
                raise ValueError('The backup repeats a file or has too many files.')
            encoded=None
            assets={}
            total=0
            for info in entries:
                if (info.flag_bits&1 or info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                        or (info.external_attr>>16)&0o170000==0o120000):
                    raise ValueError('Use an unencrypted backup of ordinary files.')
                is_metadata=info.filename==metadata_name
                match=re.fullmatch(r'photos/([a-f0-9]{64})\.(jpg|png|webp)',info.filename)
                if not is_metadata and not match:
                    raise ValueError('The backup contains an unsupported file or path.')
                limit=max_metadata_bytes if is_metadata else MAX_PHOTO_BYTES
                total+=0 if is_metadata else info.file_size
                if info.file_size>limit or total>MAX_ARCHIVE_PHOTO_BYTES:
                    raise ValueError('An expanded backup file exceeds its allowance.')
                with archive.open(info) as stream:raw=stream.read(limit+1)
                if len(raw)>limit:raise ValueError('An expanded backup file exceeds its allowance.')
                if is_metadata:
                    encoded=raw.decode('utf-8')
                else:
                    facts=image_facts(raw)
                    if facts['sha256']!=match[1] or EXTENSIONS[facts['media_type']]!=match[2] or facts['sha256'] in assets:
                        raise ValueError('A backup photo differs from its declared file identifier.')
                    assets[facts['sha256']]=(facts,raw)
            if encoded is None:raise ValueError('The backup is missing its notes file.')
            return encoded,assets
    except (zipfile.BadZipFile,UnicodeError,RuntimeError,NotImplementedError,EOFError):
        raise ValueError('Use a valid, unencrypted Clovis ZIP backup.') from None


def check_archive_references(references,assets):
    if set(references)!=set(assets):
        raise ValueError('The backup must include exactly the original photos referenced by its notes and revisions.')
    for digest,reference in references.items():check_reference(reference,assets[digest][0])
