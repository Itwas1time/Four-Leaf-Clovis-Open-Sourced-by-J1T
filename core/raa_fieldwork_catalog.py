"""Read Swedish assignment snapshots without turning geometry rows into digs."""
import base64
from contextlib import closing
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import lzma
import re
import sqlite3
import struct

from core.data_packs import PackStore

PACK='raa-fieldwork'
PAGE_SIZE=24
POLICY='https://catalog.raa.se/store/1/resource/105'
LICENSE='Public Domain dataset, as declared by Riksantikvarieämbetet; linked reports and media have separate rights'
FIELDS={'all':'Original assignment metadata','places':'Recorded place text only','identifiers':'Original identifiers only'}
GROUND={'all':'All geometry coverage','recorded':'Recorded disturbed-ground geometry','unrecorded':'No disturbed-ground geometry recorded in this snapshot'}
TYPES={
    'Arkeologisk utredning':'Archaeological assessment',
    'Arkeologisk förundersökning':'Preliminary archaeological investigation',
    'Arkeologisk undersökning':'Archaeological investigation',
    'Schaktningsövervakning':'Watching brief',
    'Arkeologisk kontroll':'Archaeological control',
    'Inventering':'Inventory survey',
    'Forskningsundersökning':'Research investigation',
    'Efterundersökning':'Follow-up investigation',
    'Utredning utan KML-beslut':'Assessment without a KML decision',
    'Övriga uppdrag 2 kap. KML':'Other KML chapter 2 assignment',
    'Kunskapsunderlag':'Knowledge assessment',
    'Övrig fältregistrering':'Other field registration',
    'Obestämbar vid import':'Unclassified on import',
}
STATUSES={'Planerad':'Planned','Pågående':'Ongoing','Avslutad':'Completed','Importerad':'Imported'}
ROLES={'assignment':'Assignment extent','disturbed':'Recorded disturbed-ground area'}
NOTES=(
    'One native Swedish assignment UUID per source snapshot, not one excavation per geometry. Types include surveys and assessments; status can be planned, ongoing or completed.',
    'Coverage is geographically and historically incomplete. Imported records have quality gaps. Missing records do not establish absence of archaeology.',
    'Assignment extents and disturbed-ground areas have different roles. Missing disturbed-ground geometry does not establish that no ground disturbance occurred, or that remains are absent.',
    'Imported point markers can lie away from actual work. Geometry precision is unestablished. These are not individual find locations.',
    'Decision dates are administrative dates. Imported January 1 values can be year-only placeholders; 0001-01-01 marks an unknown year. No fieldwork dates are inferred.',
    'Original per-feature attributes and geometries are retained. Different values under the same provider UUID remain separate variants. Filtered attributes must co-occur in a native variant.',
)
KEY=re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}~[a-f0-9]{64}\Z')
UUID=re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\Z')
MAX_EDITION_BYTES=40_000_000


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store=PackStore()
    return store.resolve_file(PACK,'raa.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def connect(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA trusted_schema=OFF')
    return db


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def unpack(packed,expected):
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
        raw=stream.read(MAX_EDITION_BYTES+1)
    if len(raw)>MAX_EDITION_BYTES or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('The complete original assignment edition failed verification.')
    return json.loads(raw)


def validate_parameters(query='',page=1,method='',status='',ground='all',field='all'):
    values=(query,method,status)
    if (any(not isinstance(value,str) or len(value)>120 or any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in value) for value in values)
            or type(page) is not int or not 1<=page<=1_000_000 or ground not in GROUND or field not in FIELDS):
        raise ValueError('Choose original Swedish assignment types, status, geometry coverage and text fields.')


def stats():
    path=database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def choices(column):
    if column not in ('method','status'):
        raise ValueError('Choose a listed assignment field.')
    path=database()
    if path is None:
        return []
    labels=TYPES if column=='method' else STATUSES
    query={
        'method':"SELECT method,count(DISTINCT uuid) AS records FROM variants WHERE method<>'' GROUP BY method ORDER BY method",
        'status':"SELECT status,count(DISTINCT uuid) AS records FROM variants WHERE status<>'' GROUP BY status ORDER BY status",
    }[column]
    with closing(connect(path)) as db:
        rows=db.execute(query).fetchall()
    return [{'value':row[column],'label':labels.get(row[column],'Original value')+' / '+row[column],
        'records':row['records']} for row in rows]


def search(query='',page=1,method='',status='',ground='all',field='all'):
    validate_parameters(query,page,method,status,ground,field)
    path=database()
    if path is None:
        return {'rows':[],'total':0,'page':1,'installed':False}
    clauses,parameters=[],[]
    for column,value in (('method',method),('status',status)):
        if value:
            clauses.append('v.'+column+'=?')
            parameters.append(value)
    if ground!='all':
        clauses.append('r.disturbed_features>0' if ground=='recorded' else 'r.disturbed_features=0')
    words=re.findall(r'[^\W_]+',query,flags=re.UNICODE)
    if words:
        expression=' AND '.join('"'+word+'"' for word in words)
        clauses.append({
            'all':'v.rowid IN (SELECT rowid FROM variant_fts WHERE all_text MATCH ?)',
            'places':'v.rowid IN (SELECT rowid FROM variant_fts WHERE places MATCH ?)',
            'identifiers':'v.rowid IN (SELECT rowid FROM variant_fts WHERE identifiers MATCH ?)',
        }[field])
        parameters.append(expression)
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    selection=' FROM resources r JOIN variants v ON v.uuid=r.uuid'+where
    with closing(connect(path)) as db:
        total=db.execute('SELECT count(DISTINCT r.uuid)'+selection,parameters).fetchone()[0]
        page=min(page,max(1,(total+PAGE_SIZE-1)//PAGE_SIZE))
        rows=db.execute('SELECT DISTINCT r.uuid,r.record_key,r.title,r.number,r.assignment_features,r.disturbed_features,r.variant_count'+selection
            +' ORDER BY r.number,r.uuid LIMIT ? OFFSET ?',(*parameters,PAGE_SIZE,(page-1)*PAGE_SIZE)).fetchall()
    cards=[{**dict(row),'id':row['record_key'],'category':'Fieldwork assignment metadata',
        'subtitle':f"{row['assignment_features']:,} assignment geometry rows · {row['disturbed_features']:,} disturbed-ground rows · {row['variant_count']:,} native attribute variant(s)"} for row in rows]
    return {'rows':cards,'total':total,'page':page,'installed':True}


def get_record(key):
    if not isinstance(key,str) or not KEY.fullmatch(key):
        return None
    path=database()
    if path is None:
        return None
    with closing(connect(path)) as db:
        row=db.execute('SELECT * FROM resources WHERE record_key=?',(key,)).fetchone()
        if row is None:
            return None
        result=dict(row)
    original=unpack(result.pop('payload_gzip'),result['edition_sha256'])
    if original.get('uuid')!=result['uuid']:
        raise ValueError('The original assignment UUID differs from its index.')
    result.update(id=key,category='Fieldwork assignment metadata',
        subtitle=f"{result['assignment_features']:,} assignment geometry rows · {result['disturbed_features']:,} disturbed-ground rows",
        original=original,source_url='https://pub.raa.se/visa/aktivitet/arkeologisktuppdrag/'+result['uuid'])
    return result


def decision_note(value):
    if not value:
        return 'No decision date recorded.'
    if str(value).startswith('0001-01-01'):
        return 'Unknown-year placeholder documented by the provider; not a year-one fieldwork date.'
    if re.match(r'\d{4}-01-01',str(value)):
        return 'January 1 can be a year-only placeholder in imported records; day precision is unestablished here. Not a fieldwork date.'
    return 'Administrative decision date; not a fieldwork or occupation date.'


def fields(row):
    original=row['original']
    facts=[('Original assignment UUID',row['uuid']),('Original assignment number(s)',row['number']),
        ('Source edition SHA-256',row['edition_sha256']),('Assignment geometry rows',str(row['assignment_features'])),
        ('Recorded disturbed-ground geometry rows',str(row['disturbed_features'])),
        ('Native attribute variants',str(row['variant_count']))]
    labels={'uppdragstyp':'Original work type','status':'Original status','beslutsdatum':'Original decision date',
        'kommun':'Original municipality text','lan':'Original county text','socken':'Original parish text',
        'beslutande_myndighet':'Deciding authority','diarienummer':'Original case number',
        'utforande_organisation':'Performing organization','nollresultat':'Original nollresultat declaration (uninterpreted)'}
    for index,variant in enumerate(original['variants'],1):
        attributes=variant['attributes']
        prefix=f'Variant {index} · ' if len(original['variants'])>1 else ''
        facts.extend((prefix+label,str(attributes.get(key)) if attributes.get(key) is not None else 'Not recorded') for key,label in labels.items())
        facts.append((prefix+'Decision date qualification',decision_note(attributes.get('beslutsdatum'))))
        facts.append((prefix+'Type explanation (Clovis translation)',TYPES.get(attributes.get('uppdragstyp'),'No authored translation; retain original wording.')))
    return facts


def published_geometries(row):
    """Transform display copies; retain original GeoPackage bytes and topology."""
    from pyproj import Transformer
    from shapely import from_wkb
    from shapely.geometry import mapping
    from shapely.ops import transform
    from core.published_locations import geometry_points
    transformer=Transformer.from_crs(3006,4326,always_xy=True,allow_ballpark=False)
    result=[]
    grouped={'assignment':[],'disturbed':[]}
    for feature in row['original']['features']:
        encoded=feature['geometry_gpkg_base64']
        if encoded is None:
            continue
        raw=base64.b64decode(encoded,validate=True)
        if hashlib.sha256(raw).hexdigest()!=feature['geometry_sha256'] or raw[:3]!=b'GP\x00':
            raise ValueError('The original source geometry failed verification.')
        flag=raw[3]
        envelope=(flag>>1)&7
        lengths={0:0,1:4,2:6,3:6,4:8}
        if envelope not in lengths or flag&32:
            raise ValueError('The original geometry has an unsupported encoding.')
        srs=struct.unpack('<i' if flag&1 else '>i',raw[4:8])[0]
        if srs!=3006 or feature['srs_id']!=3006:
            raise ValueError('The source geometry CRS requires review; no coordinates are inferred.')
        shape=from_wkb(raw[8+8*lengths[envelope]:])
        if shape.is_empty:
            continue
        projected=transform(transformer.transform,shape)
        geometry=json.loads(json.dumps(mapping(projected)))
        points=geometry_points(geometry)
        if not points:
            raise ValueError('The transformed source geometry could not be plotted without omission.')
        role=feature['role']
        note=('Display transformed offline from original SWEREF 99 TM (EPSG:3006) to WGS 84. '
            'Native geometry bytes and CRS remain in the complete edition. Precision is unestablished; this is not an individual find location. ')
        if shape.geom_type=='Point':
            result.append({'id':row['uuid']+'/'+feature['source_file']+'/'+str(feature['source_fid']),
                'label':ROLES[role]+' · coarse imported point marker','shape':'point','coordinates':points,
                'note':note+'The provider warns that imported markers can lie away from the actual work.'})
        else:
            grouped[role].append(geometry)
    for role,geometries in grouped.items():
        if not geometries:
            continue
        geometry={'type':'GeometryCollection','geometries':geometries}
        note=('Display transformed offline from original SWEREF 99 TM (EPSG:3006) to WGS 84. '
            'All rings and component geometries are retained. Precision is unestablished; this is not an individual find location. ')
        note+=('Assignment extents are not a declaration that all ground was excavated.' if role=='assignment'
            else 'Recorded ground disturbance does not establish that the whole site was excavated or that no remains survive.')
        result.append({'id':row['uuid']+'/'+role,'label':ROLES[role]+f' · {len(geometries):,} source features',
            'shape':'geojson','geometry':geometry,'coordinates':geometry_points(geometry),'note':note,
            'color':'#275840' if role=='assignment' else '#a65f2b'})
    return result


def reference_entry(key):
    row=get_record(key)
    if row is None:
        raise ValueError('Choose an installed Swedish assignment edition.')
    return _reference_entry(row)


def _reference_entry(row):
    from core.fieldbook import validate_citation_entry
    from core.resident_context import _md
    packed=gzip.compress(canonical(row['original']),mtime=0)
    codec='gzip'
    if len(packed)*4//3>1_800_000:
        alternative=lzma.compress(canonical(row['original']),preset=6)
        if len(alternative)<len(packed):
            packed,codec=alternative,'xz'
    lines=['# Swedish assignment source edition · '+row['uuid'],row['source_url'],'',
        'Attribution: Riksantikvarieämbetet / Kulturmiljöregistret.',LICENSE,POLICY,'',*NOTES,'']
    lines.extend(label+': '+_md(value) for label,value in fields(row))
    lines.extend(['','## Complete source edition archive',
        'Encoding: base64 of '+codec+'-compressed UTF-8 JSON. Contains every original feature attribute and GeoPackage geometry byte, original table/fid, geometry role, CRS metadata and source receipts. No features are omitted.',
        'Decoded JSON SHA-256: '+row['edition_sha256'],
        'Source edition archive base64:',base64.b64encode(packed).decode('ascii')])
    markdown='\n'.join(lines)
    entry={'id':hashlib.sha256(markdown.encode('utf-8')).hexdigest()[:24],'kind':'investigation',
        'title':('RAÄ · '+row['number']+' · '+row['uuid'])[:120],
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'source':'Riksantikvarieämbetet · '+row['uuid']},'markdown':markdown}
    return validate_citation_entry(entry)


def captured_payload(entry):
    """Recover a complete saved edition without the original collection installed."""
    from core.fieldbook import validate_citation_entry
    validate_citation_entry(entry)
    text=entry['markdown']
    marker='Source edition archive base64:\n'
    if text.count(marker)!=1:
        raise ValueError('The captured Swedish source archive is missing or ambiguous.')
    hashes=re.findall(r'^Decoded JSON SHA-256: ([a-f0-9]{64})$',text,re.MULTILINE)
    codecs=re.findall(r'^Encoding: base64 of (gzip|xz)-compressed UTF-8 JSON\.',text,re.MULTILINE)
    if len(hashes)!=1 or len(codecs)!=1:
        raise ValueError('The captured source checksum or encoding is unsupported.')
    try:
        packed=base64.b64decode(text.split(marker,1)[1],validate=True)
        if codecs[0]=='gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
                raw=stream.read(MAX_EDITION_BYTES+1)
        else:
            decoder=lzma.LZMADecompressor(memlimit=64_000_000)
            raw=decoder.decompress(packed,max_length=MAX_EDITION_BYTES+1)
            if not decoder.eof or decoder.unused_data:
                raise ValueError('Incomplete or trailing source archive data.')
        if len(raw)>MAX_EDITION_BYTES or hashlib.sha256(raw).hexdigest()!=hashes[0]:
            raise ValueError('The captured complete source edition failed its checksum.')
        payload=json.loads(raw)
    except (ValueError,OSError,lzma.LZMAError,EOFError) as error:
        raise ValueError('The captured source edition could not be recovered intact.') from error
    if payload.get('format')!='clovis-raa-assignment-edition-1' or not UUID.fullmatch(payload.get('uuid','')):
        raise ValueError('The captured source edition has an unsupported identity.')
    return payload


def reading_text(entry):
    """Read the citation without rendering its portable binary archive as prose."""
    from core.fieldbook import readable_text
    captured_payload(entry)
    marker='\n## Complete source edition archive\n'
    if entry['markdown'].count(marker)!=1:
        raise ValueError('The captured Swedish citation has an unsupported reading format.')
    text=entry['markdown'].split(marker,1)[0]
    return (readable_text(text)+'\n\nComplete original source metadata and geometry are preserved with this citation. '
        'Use Download captured source record to inspect the full source, or Show captured source geometry to open its map.')
