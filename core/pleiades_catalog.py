"""Read complete native ancient-place resources from one optional local pack."""
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
import re
import sqlite3
import unicodedata
import zlib

from core.data_packs import PackStore
from core.fieldbook import validate_book

PACK = 'ancient-places'
PAGE_SIZE = 24
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
MAX_RECORD_BYTES = 128 * 1024**2
SOURCE_URI = re.compile(r'https?://pleiades\.stoa\.org/places/([A-Za-z0-9][A-Za-z0-9_.-]{0,79})/?(?:#this)?\Z')


def name_key(value):
    """A search key only; the source's complete original spelling stays separate."""
    return ' '.join(''.join(character for character in unicodedata.normalize('NFKD',value.casefold())
                            if not unicodedata.combining(character)).split())


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store = PackStore()
    if PACK not in {row['id'] for row in store.definitions}:
        return None
    return store.resolve_file(PACK, 'places.sqlite')


def connect(path):
    connection = sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def stats():
    path = database()
    if not path:
        return None
    with closing(connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def validate_parameters(query='', page=1, place_id='', scope='all', record_id=''):
    if (any(not isinstance(value,str) or len(value)>120 or
            any(ord(character)<32 or 0xD800<=ord(character)<=0xDFFF for character in value)
            for value in (query,place_id,scope,record_id))
            or type(page) is not int or not 1<=page<=100000
            or scope not in ('all','outgoing','incoming')
            or any(value and not IDENTIFIER.fullmatch(value) for value in (place_id,record_id))
            or bool(place_id) != (scope!='all')):
        raise ValueError('Choose a published ancient place or its original connections.')


def search(query='', page=1, place_id='', scope='all', record_id=''):
    validate_parameters(query,page,place_id,scope,record_id)
    path = database()
    if not path:
        return {'rows':[],'total':0,'page':1,'pages':1,'installed':False}
    with closing(connect(path)) as connection:
        query = query.strip()
        source_uri = SOURCE_URI.fullmatch(query)
        exact_id = source_uri.group(1) if source_uri else None
        if not exact_id and IDENTIFIER.fullmatch(query):
            if connection.execute('SELECT 1 FROM places WHERE id=?',(query,)).fetchone():
                exact_id = query
        clauses, values = [], []
        terms = [] if exact_id else re.findall(r'\w+',query,flags=re.UNICODE)[:12]
        if query and not terms and not exact_id:
            return {'rows':[],'total':0,'page':1,'pages':1,'installed':True}
        tables = 'places p'
        ordering = 'p.title COLLATE NOCASE,p.id'
        order_values = []
        if terms:
            tables += ' JOIN place_fts ON place_fts.rowid=p.rowid'
            clauses.append('place_fts MATCH ?')
            values.append(' AND '.join('"'+term.replace('"','""')+'"*' for term in terms))
            # Exact native titles lead, followed by weighted native titles and aliases.
            # Bibliographic and period matches remain in the complete result set.
            ordering = ('CASE WHEN p.title=? COLLATE NOCASE THEN 0 ELSE 1 END,'
                        'bm25(place_fts,20.0,3.0,12.0,1.0,1.0,0.3,0.3),p.title COLLATE NOCASE,p.id')
            order_values.append(query)
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='name_forms'").fetchone():
                # Both SQL fragments are fixed; the normalized name is a bound value.
                ordering = ('CASE WHEN p.id IN (SELECT place_id FROM name_forms WHERE search_key=?) THEN 0 ELSE 1 END,'  # nosec B608
                            + ordering)
                order_values.insert(0,name_key(query))
        if exact_id:
            clauses.append('p.id=?')
            values.append(exact_id)
        if record_id:
            clauses.append('p.id=?')
            values.append(record_id)
        if scope == 'outgoing':
            clauses.append('p.id IN (SELECT target_id FROM connections WHERE place_id=?)')
            values.append(place_id)
        elif scope == 'incoming':
            clauses.append('p.id IN (SELECT place_id FROM connections WHERE target_id=?)')
            values.append(place_id)
        where = ' AND '.join(clauses) or '1=1'
        total = connection.execute('SELECT count(*) FROM '+tables+' WHERE '+where,values).fetchone()[0]  # nosec B608
        pages = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
        page = min(page,pages)
        rows = connection.execute('SELECT p.id,p.title,p.description,p.place_types FROM '+tables+' WHERE '+where+  # nosec B608
            ' ORDER BY '+ordering+' LIMIT ? OFFSET ?',[*values,*order_values,PAGE_SIZE,(page-1)*PAGE_SIZE]).fetchall()
    return {'rows':[{'id':row['id'],'title':row['title'],'subtitle':' · '.join(json.loads(row['place_types'])),
                     'category':'Published ancient place'} for row in rows],
            'total':total,'page':page,'pages':pages,'installed':True}


def _raw(row):
    size = row['source_bytes']
    if type(size) is not int or not 0<size<=MAX_RECORD_BYTES:
        raise ValueError('The original place record has an unsupported size.')
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(row['source_json'],size+1)
    except zlib.error as error:
        raise ValueError('The original place record needs verification.') from error
    if (len(raw)!=size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or hashlib.sha256(raw).hexdigest()!=row['source_sha256']):
        raise ValueError('The original place record failed verification.')
    return raw


def native_json(identifier):
    if not isinstance(identifier,str) or not IDENTIFIER.fullmatch(identifier):
        return None
    path = database()
    if not path:
        return None
    with closing(connect(path)) as connection:
        row = connection.execute('SELECT * FROM places WHERE id=?',(identifier,)).fetchone()
        return _raw(row) if row else None


def license_details(rights):
    choices = (
        ('Creative Commons Attribution 3.0 License','CC BY 3.0','https://creativecommons.org/licenses/by/3.0/'),
        ('Creative Commons Attribution-Share Alike 3.0 License','CC BY-SA 3.0','https://creativecommons.org/licenses/by-sa/3.0/'),
    )
    matches = [(label,url) for fragment,label,url in choices if fragment in rights]
    if len(matches)!=1:
        raise ValueError('Review the original place resource rights.')
    return matches[0]


def get_record(identifier):
    raw = native_json(identifier)
    if raw is None:
        return None
    source = json.loads(raw,parse_float=Decimal)
    if source['id'] != identifier:
        raise ValueError('The native place identifier does not match the selected record.')
    label,url = license_details(source['rights'])
    return {'id':source['id'],'title':source['title'],'subtitle':' · '.join(source['placeTypes']),
            'category':'Published ancient place','description':plain(source['description']),
            'source':source,'source_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),
            'source_url':'https://pleiades.stoa.org/places/'+source['id'],
            'license':label,'license_url':url}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self,tag,attributes):
        if tag in ('script','style'):
            self.ignored += 1
        elif tag in ('p','div','br','li'):
            self.parts.append(' ')

    def handle_endtag(self,tag):
        if tag in ('script','style') and self.ignored:
            self.ignored -= 1
        elif tag in ('p','div','li'):
            self.parts.append(' ')

    def handle_data(self,value):
        if not self.ignored:
            self.parts.append(value)


def plain(value):
    if value is None:
        return ''
    parser = PlainText()
    parser.feed(str(value))
    return ' '.join(''.join(parser.parts).split())


def value_text(value):
    if value is None:
        return 'Not recorded'
    if value == '':
        return 'Not recorded (blank)'
    if isinstance(value,list):
        return '; '.join(value_text(item) for item in value) if value else 'None recorded'
    if isinstance(value,dict):
        return '; '.join(str(key)+': '+value_text(item) for key,item in value.items())
    return str(value)


def facts(record):
    source=record['source']
    return [('Pleiades identifier',source['id']),('Native place types',value_text(source['placeTypes'])),
            ('Names',str(len(source['names']))),('Location records',str(len(source['locations']))),
            ('Published connections',str(len(source['connections']))),
            ('Bibliographic references',str(len(source['references']))),
            ('Initial provenance',source['provenance']),('Resource created',source['created'])]


def authors(source,role):
    return '; '.join(item.get('name') or item.get('username') or 'Unnamed source contributor'
                     for item in source[role])


def relationships(record):
    result=[]
    for scope,label in (('outgoing','Places this resource connects to'),('incoming','Places connecting to this resource')):
        parameters={'place_id':record['id'],'scope':scope}
        total=search(**parameters)['total']
        if total:
            result.append({'key':scope,'label':label,'total':total,'parameters':{'collection':'places',**parameters}})
    return result


def reference_entry(identifier):
    record=get_record(identifier)
    if not record:
        raise ValueError('Choose a current ancient place resource.')
    source=record['source']
    summary=stats()
    text='\n'.join([
        '# '+source['title'],'',
        'Pleiades published place resource: '+source['id'],
        'Source: '+record['source_url'],
        'Snapshot: '+summary['source_edition'],
        'Native export SHA-256: '+summary['native_file_sha256'],
        'Native place-object SHA-256: '+record['source_sha256'],'',
        'Creators: '+authors(source,'creators'),
        'Contributors: '+authors(source,'contributors'),
        source['rights'],record['license_url'],'',
        'Names, location records and connections belong to this place resource; they are not additional places or excavations.',
        'Representative points are publisher-calculated centroids or connected-place estimates, not exact find or excavation coordinates.',
        'Native locations and bibliographic evidence remain in the downloadable complete source record.'])
    entry={'id':hashlib.sha256(('pleiades|'+identifier+'|'+record['source_sha256']).encode()).hexdigest()[:24],
           'kind':'investigation','title':('Pleiades · '+source['title']).encode('utf-8')[:120].decode('utf-8','ignore'),
           'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           'summary':{'source':('Pleiades · '+source['id']).encode('utf-8')[:1500].decode('utf-8','ignore'),
                      'place':source['title'].encode('utf-8')[:1500].decode('utf-8','ignore')},
           'markdown':text}
    validate_book({'version':1,'entries':[entry]})
    return entry


def register_source_routes(server):
    from flask import Response, abort
    endpoint = 'pleiades_native_source'
    if endpoint in server.view_functions:
        return

    def download(identifier):
        try:
            raw = native_json(identifier)
        except (ValueError,OSError,sqlite3.Error):
            abort(404)
        if raw is None:
            abort(404)
        response = Response(raw,mimetype='application/json')
        response.headers['Content-Disposition']='attachment; filename="pleiades-'+identifier+'.json"'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response

    server.add_url_rule('/atlas/source/pleiades/<identifier>.json',endpoint,download,methods=['GET'])
