"""Read Finnish Antiquities Record sites without turning register entries into digs."""
import base64
from contextlib import closing
from datetime import datetime, timezone
import gzip
import hashlib
import json
import re
import sqlite3
import struct
import threading
import unicodedata

from core.data_packs import PackStore

PACK='finland-antiquities'
PAGE_SIZE=24
SOURCE_CRS=3067
LICENSE=('CC BY 4.0 · Finnish Heritage Agency (Museovirasto), Antiquities Record spatial data; attribute the agency '
         'and the export date. Linked register pages, reports and images have separate terms.')
LICENSE_URL='https://creativecommons.org/licenses/by/4.0/'
POLICY=('https://www.museovirasto.fi/en/services-and-guidelines/data-systems/kulttuuriympaeristoen-tietojaerjestelmae/'
        'kulttuuriympaeristoen-paikkatietoaineistot')
FIELDS={'all':'Original register metadata','names':'Site names only',
        'municipality':'Recorded municipality (kunta) name only','identifiers':'Register identifiers only'}
CLASSES={
    'kiinteä muinaisjäännös':'Fixed ancient monument (protected by law)',
    'mahdollinen muinaisjäännös':'Possible ancient monument',
    'havaintokohde':'Observation site',
    'löytöpaikka':'Find spot (where finds were reported)',
    'muu kulttuuriperintökohde':'Other cultural heritage site',
    'muu kohde':'Other site',
    'poistettu kiinteä muinaisjäännös (ei rauhoitettu)':'Removed ancient monument (no longer protected)',
    'luonnonmuodostuma':'Natural formation',
}
DATINGS={
    'kivikautinen':'Stone Age','varhaismetallikautinen':'Early Metal Age','pronssikautinen':'Bronze Age',
    'rautakautinen':'Iron Age','esihistoriallinen':'Prehistoric','keskiaikainen':'Medieval',
    'historiallinen':'Historical period','moderni':'Modern','ajoittamaton':'Undated',
}
ACCURACY={
    'Tarkka (< 10 m)':'Declared accurate to under 10 m','Ohjeellinen (10 - 100 m)':'Declared indicative, 10–100 m',
    'Suuntaa antava (100 - 1000 m)':'Declared approximate, 100–1000 m','> 1000m':'Declared over 1000 m',
    'Ei tiedossa':'Declared not known',
}
LAYERS={'arkeologiset_kohteet_piste_t':'Register site point','arkeologiset_kohteet_alue_t':'Register site area',
        'arkeologiset_kohteet_alakohteet_piste':'Sub-site point'}
NOTES=(
    'One Finnish Antiquities Record site identifier (mjtunnus) per record, with every point, area and sub-site row of this export. A register site is not an excavation event; a record does not establish that fieldwork occurred.',
    'Native classes stay separate: fixed ancient monuments, possible monuments, observation sites, find spots, other cultural heritage sites, removed monuments and natural formations. A find spot records where finds were reported, not the finds.',
    'Geometry is published register geometry in ETRS-TM35FIN (EPSG:3067). Declared location accuracy is missing for many points. A point or area is not an exact find location, excavation footprint or property boundary.',
    'Creation and modification dates are register administrative dates, not fieldwork or occupation dates. Dating values are broad register period labels.',
    'Coverage is one daily national export. Missing records do not establish absence of archaeology; overlaps with other catalogues are unresolved.',
    'The spatial data are CC BY 4.0. Linked register pages, reports and photographs have separate terms and are not included.',
)
KEY=re.compile(r'fi-mj/[0-9]{1,15}~[a-f0-9]{64}\Z')
MAX_EDITION_BYTES=40_000_000
_LOCAL=threading.local()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store=PackStore()
    return store.resolve_file(PACK,'finland.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def place_key(value):
    """Compare whole names as the text index does: ignore case and diacritics."""
    text=unicodedata.normalize('NFKD',value)
    return ' '.join(''.join(char for char in text if not unicodedata.combining(char)).casefold().split())


def _names_match(value,wanted):
    # Native multi-municipality values list several names separated by commas.
    return int(isinstance(value,str) and any(place_key(name)==wanted for name in value.split(',')))


def connect(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA trusted_schema=OFF')
    db.create_function('clovis_place_names',2,_names_match,deterministic=True)
    return db


def validate_parameters(query='',page=1,site_class='',dating='',field='all'):
    if (any(not isinstance(value,str) or len(value)>120 or any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in value)
            for value in (query,site_class,dating))
            or type(page) is not int or not 1<=page<=1_000_000 or field not in FIELDS):
        raise ValueError('Choose original Finnish register classes, dating and text fields.')


def stats():
    path=database()
    if path is None:return None
    with closing(connect(path)) as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def choices(column):
    if column not in ('site_class','dating'):
        raise ValueError('Choose a listed register field.')
    path=database()
    if path is None:return []
    labels=CLASSES if column=='site_class' else DATINGS
    with closing(connect(path)) as db:
        # The column name comes from the closed list above; values are not interpolated.
        rows=db.execute('SELECT '+column+' AS value,count(*) AS records FROM resources '  # nosec B608
            'GROUP BY '+column+' ORDER BY records DESC,value').fetchall()
    return [{'value':row['value'],'label':labels.get(row['value'],'Original value')+' / '+(row['value'] or 'not recorded'),
        'records':row['records']} for row in rows]


def search(query='',page=1,site_class='',dating='',field='all'):
    validate_parameters(query,page,site_class,dating,field)
    path=database()
    if path is None:return {'rows':[],'total':0,'page':1,'installed':False}
    clauses,parameters=[],[]
    for column,value in (('site_class',site_class),('dating',dating)):
        if value:
            clauses.append(column+'=?')
            parameters.append(value)
    words=re.findall(r'[^\W_]+',query,flags=re.UNICODE)
    if words:
        column={'all':'all_text','names':'names','municipality':'municipality','identifiers':'identifiers'}[field]
        clauses.append('rowid IN (SELECT rowid FROM resource_fts WHERE '+column+' MATCH ?)')  # nosec B608
        parameters.append(' AND '.join('"'+word+'"' for word in words))
        if field=='municipality':
            # The text index narrows candidates; a whole recorded name must then match.
            clauses.append('clovis_place_names(municipality,?)')
            parameters.append(place_key(query))
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    with closing(connect(path)) as db:
        # Clause text uses only the closed mappings above; all supplied values are bound.
        total=db.execute('SELECT count(*) FROM resources'+where,parameters).fetchone()[0]  # nosec B608
        page=min(page,max(1,(total+PAGE_SIZE-1)//PAGE_SIZE))
        rows=db.execute('SELECT record_key AS id,mjtunnus,name,municipality,site_class,site_type,dating,'  # nosec B608
            'point_rows,area_rows,subsite_rows FROM resources'+where+' ORDER BY mjtunnus LIMIT ? OFFSET ?',
            (*parameters,PAGE_SIZE,(page-1)*PAGE_SIZE)).fetchall()
    cards=[]
    for row in rows:
        title=(row['name'] or 'Unnamed register site')+' · '+(row['municipality'] or 'municipality not recorded')
        parts=[CLASSES.get(row['site_class'],row['site_class'] or 'Class not recorded'),row['site_type'] or 'type not recorded',
               DATINGS.get(row['dating'],row['dating'] or 'dating not recorded')]
        cards.append({**dict(row),'title':title,'category':'Antiquities Record register site',
            'subtitle':' · '.join(parts)+f" · register {row['mjtunnus']}"})
    return {'rows':cards,'total':total,'page':page,'installed':True}


def unpack(blob,expected):
    raw=gzip.decompress(blob)
    if len(raw)>MAX_EDITION_BYTES or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('The complete register site edition failed verification.')
    return json.loads(raw)


def get_record(key):
    if not isinstance(key,str) or not KEY.fullmatch(key):return None
    path=database()
    if path is None:return None
    with closing(connect(path)) as db:
        row=db.execute('SELECT * FROM resources WHERE record_key=?',(key,)).fetchone()
        if row is None:return None
        result=dict(row)
    original=unpack(result.pop('payload_gzip'),result['edition_sha256'])
    if original.get('mjtunnus')!=result['mjtunnus'] or key!=f"fi-mj/{result['mjtunnus']}~{result['edition_sha256']}":
        raise ValueError('The register site identifier differs from its cited edition.')
    title=(result['name'] or 'Unnamed register site')+' · '+(result['municipality'] or 'municipality not recorded')
    result.update(id=key,title=title,category='Antiquities Record register site',
        subtitle=CLASSES.get(result['site_class'],result['site_class'] or 'Class not recorded'),original=original,
        source_url=result['register_url'] or POLICY)
    return result


def _literal(value):
    if value is None:return 'Not recorded (null in source)'
    text=str(value)
    return text if text.strip() else 'Blank in source ('+repr(text)+')'


def fields(row):
    original=row['original']
    receipt=original['source']['receipt']
    facts=[('Register site identifier (mjtunnus)',str(row['mjtunnus'])),
        ('Native class (Laji)',(row['site_class'] or 'Not recorded')+' · '+CLASSES.get(row['site_class'],'No authored translation; retain original wording.')),
        ('Recorded municipality (kunta)',_literal(row['municipality'])),('Original type / subtype',_literal(row['site_type'])+' / '+_literal(row['subtype'])),
        ('Original dating (ajoitus)',(row['dating'] or 'Not recorded')+' · '+DATINGS.get(row['dating'],'Original value')),
        ('Underwater flag (vedenalainen)',_literal(row['underwater'])),
        ('Declared location accuracy',(row['accuracy'] or 'Not recorded')+(' · '+ACCURACY[row['accuracy']] if row['accuracy'] in ACCURACY else '')),
        ('Location method (paikannustapa)',_literal(row['location_method'])),
        ('Rows in this export',f"{row['point_rows']} point · {row['area_rows']} area · {row['subsite_rows']} sub-site"),
        ('Publisher','Finnish Heritage Agency (Museovirasto)'),
        ('Export edition',receipt['last_modified']+' · retrieved '+receipt['retrieved_utc']),
        ('Original export SHA-256',receipt['sha256']),('Site edition SHA-256',row['edition_sha256'])]
    for feature in original['features']:
        prefix=LAYERS.get(feature['layer'],feature['layer'])+' · fid '+str(feature['fid'])+' · '
        facts.extend((prefix+name,_literal(value)) for name,value in feature['attributes'].items())
    return facts


def _transformer():
    # Building a transformer is costly and pyproj transformers are not thread-safe.
    transformer=getattr(_LOCAL,'transformer',None)
    if transformer is None:
        from pyproj import Transformer
        transformer=_LOCAL.transformer=Transformer.from_crs(SOURCE_CRS,4326,always_xy=True)
    return transformer


def published_geometries(row):
    """Transform display copies offline; original GeoPackage bytes and CRS stay in the edition."""
    from shapely import from_wkb
    from shapely.geometry import mapping
    from shapely.ops import transform
    from core.published_locations import geometry_points
    transformer=_transformer()
    result=[]
    for feature in row['original']['features']:
        if feature['geometry_gpkg_base64'] is None:
            continue  # The native row has no published geometry; nothing is inferred.
        raw=base64.b64decode(feature['geometry_gpkg_base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=feature['geometry_sha256'] or raw[:3]!=b'GP\x00':
            raise ValueError('The original register geometry failed verification.')
        flag=raw[3]
        envelope=(flag>>1)&7
        lengths={0:0,1:4,2:6,3:6,4:8}
        if envelope not in lengths or flag&32:
            raise ValueError('The original geometry has an unsupported encoding.')
        if struct.unpack('<i' if flag&1 else '>i',raw[4:8])[0]!=SOURCE_CRS:
            raise ValueError('The register geometry CRS requires review; no coordinates are inferred.')
        shape=from_wkb(raw[8+8*lengths[envelope]:])
        if shape.is_empty:
            continue
        geometry=json.loads(json.dumps(mapping(transform(transformer.transform,shape))))
        points=geometry_points(geometry)
        if not points:
            raise ValueError('The transformed register geometry could not be plotted without omission.')
        accuracy=feature['attributes'].get('paikannustarkkuus')
        note=('Display transformed offline from ETRS-TM35FIN (EPSG:3067) to WGS 84; original bytes remain in the edition. '
              'Declared accuracy: '+(ACCURACY.get(accuracy,accuracy) if accuracy else 'not recorded')+'. '
              'A register geometry is not an exact find location, excavation footprint or property boundary.')
        label=LAYERS.get(feature['layer'],feature['layer'])+' · fid '+str(feature['fid'])
        if shape.geom_type=='Point':
            result.append({'id':f"{row['mjtunnus']}/{feature['layer']}/{feature['fid']}",'label':label,
                'shape':'point','coordinates':points,'note':note})
        else:
            result.append({'id':f"{row['mjtunnus']}/{feature['layer']}/{feature['fid']}",'label':label,
                'shape':'geojson','geometry':geometry,'coordinates':points,'note':note,'color':'#275840'})
    return result


def reference_entry(key):
    from core.fieldbook import validate_citation_entry
    from core.resident_context import _md
    row=get_record(key)
    if row is None:raise ValueError('Choose an installed Finnish register site edition.')
    literal=lambda text:'\n'.join(_md(line) for line in text.split('\n'))
    lines=['# Finnish Antiquities Record site · '+str(row['mjtunnus']),'',literal(row['title']),'',
           literal(LICENSE),LICENSE_URL,POLICY,row['source_url'],'']
    lines.extend(literal(label+': '+value)+'\n' for label,value in fields(row))
    lines.extend(literal(note)+'\n' for note in NOTES)
    archive=base64.b64encode(gzip.compress(canonical(row['original']),mtime=0)).decode('ascii')
    lines.extend(['## Complete register site edition','',
        'Encoding: base64 of gzip-compressed UTF-8 JSON with every original attribute and GeoPackage geometry byte.',
        'Decoded JSON SHA-256: '+row['edition_sha256'],'Edition archive base64:',archive])
    markdown='\n'.join(lines)
    entry={'id':hashlib.sha256(markdown.encode('utf-8')).hexdigest()[:24],'kind':'investigation',
        'title':('Finland · '+row['title']).encode('utf-8')[:120].decode('utf-8','ignore'),
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'source':'Finnish Heritage Agency Antiquities Record · '+str(row['mjtunnus']),
            'outcome':'Published register site; no new field observation'},'markdown':markdown}
    return validate_citation_entry(entry)
