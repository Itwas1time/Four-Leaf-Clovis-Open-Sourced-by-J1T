"""Published records near a public town point, from each installed collection's own coordinates.

Each collection's published coordinates are copied once into a derived spatial
index outside the verified pack (installed packs must keep their exact files).
Only coordinates the publishers released are used; nothing is geocoded from
names, and approximate or obscured positions keep their source qualification.
A short or empty list is a coverage statement, never evidence of absence.
"""
import gzip
import hashlib
import json
from math import asin, cos, isfinite, radians, sin, sqrt
import os
from pathlib import Path
import sqlite3
from threading import Lock, Thread
import zlib
from uuid import uuid4

from core.data_packs import PackStore

LABELS = {'environments': 'Neotoma · published sites', 'site_registers': 'DINAA · site register reference points',
          'dinosaurs': 'Paleobiology Database · fossil collections', 'finland': 'Finland · Antiquities Record sites'}
NOTES = {
    'environments': 'Neotoma publishes a point or a bounding area; an area can describe extent, uncertainty or an obscured location. Distances use its centre.',
    'site_registers': 'DINAA reference points are usually approximated for site protection or are county centroids. They are not site or find positions.',
    'dinosaurs': 'Paleobiology Database collection coordinates have source-defined precision and describe fossil collections, not archaeology.',
    'finland': 'Finnish register points use the register geometry; declared accuracy is often missing. Register sites are not excavations.',
}
COVERAGE = ('Only collections installed on this computer with published coordinates are searched. Coverage differs by region '
            '(for example, the DINAA collection covers parts of the south-eastern US). An empty list does not mean no archaeology.')
_LOCK = Lock()
_BUILDING = set()
_ERRORS = {}
_ERROR_KEYS = {}


def root():
    return Path(os.environ.get('CLOVIS_DERIVED_PATH') or Path.home() / 'Clovis Local' / 'derived') / 'nearby'


def _databases(sources=None):
    store = PackStore()
    ids = {row['id'] for row in store.definitions}
    found = {}
    for source, pack, name in (('environments', 'dated-environments', 'environment.sqlite'),
                               ('site_registers', 'north-american-sites', 'sites.sqlite'),
                               ('dinosaurs', 'dinosaur-sites', 'dinosaurs.sqlite'),
                               ('finland', 'finland-antiquities', 'finland.sqlite')):
        if sources is not None and source not in sources:
            continue
        if pack in ids:
            try:
                path = store.resolve_file(pack, name)
            except (ValueError, OSError):
                path = None
            if path is not None:
                found[source] = Path(path)
    return found


def _index_path(source, database):
    details = database.stat()
    identity = f'{source}|{database.resolve()}|{details.st_size}|{details.st_mtime_ns}'
    return root() / f'{source}-{hashlib.sha256(identity.encode()).hexdigest()[:20]}.sqlite'


def _pbdb_collections(con, database):
    """Read each collection's actual native context, including compact editions.

    Read requested source blocks once rather than decompressing one block for
    every occurrence. The temporary join never writes to the verified pack.
    """
    columns={row[1] for row in con.execute('PRAGMA table_info(collections)')}
    if 'source_json' in columns:
        for number,name,document in con.execute('SELECT collection_no,name,source_json FROM collections'):
            yield str(number),name,json.loads(document),None
        return
    from core import pbdb_source
    headers=json.loads(con.execute("SELECT headers_json FROM source_headers WHERE kind='occurrences'").fetchone()[0])
    for shard in range(4):
        source_path=database.parent/('fossil-source-'+str(shard)+'.sqlite')
        if source_path.is_symlink() or source_path.resolve().parent!=database.resolve().parent:
            raise ValueError('The native fossil source must remain in its verified installation.')
        wanted=con.execute('SELECT cc.source_occurrence_no,cc.collection_no,c.name FROM collection_contexts cc '
            'JOIN collections c USING(collection_no) JOIN occurrences o ON o.occurrence_no=cc.source_occurrence_no '
            'WHERE o.source_shard=?',(shard,)).fetchall()
        if not wanted:
            continue
        native=sqlite3.connect(source_path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            native.execute('PRAGMA temp_store=MEMORY')
            native.execute('CREATE TEMP TABLE requested(source_id TEXT PRIMARY KEY,collection_no TEXT,name TEXT)')
            native.executemany('INSERT INTO requested VALUES(?,?,?)',wanted)
            compact=native.execute('PRAGMA user_version').fetchone()[0]==3
            if compact:
                matched=native.execute('SELECT count(*) FROM requested JOIN source_rows USING(source_id)').fetchone()[0]
                if matched!=len(wanted):
                    raise ValueError('A fossil collection context is missing its native source row.')
                previous=None
                values=[]
                for occurrence,number,name,block,ordinal in native.execute(
                        'SELECT w.source_id,w.collection_no,w.name,r.block_no,r.block_ordinal FROM requested w '
                        'JOIN source_rows r USING(source_id) ORDER BY r.block_no,r.block_ordinal'):
                    if block!=previous:
                        size,payload,rows=native.execute('SELECT source_bytes,source_values,rows FROM source_blocks WHERE block_no=?',(block,)).fetchone()
                        values=pbdb_source._inflate(payload,size,pbdb_source.MAX_BLOCK_BYTES)
                        if (type(rows) is not int or not 1<=rows<=pbdb_source.MAX_BLOCK_ROWS
                                or not isinstance(values,list) or len(values)!=rows):
                            raise ValueError('A native fossil source block has an invalid row count.')
                        previous=block
                    if type(ordinal) is not int or not 0<=ordinal<len(values):
                        raise ValueError('A fossil context has an invalid native block position.')
                    source_row,_fields=pbdb_source._cells(values[ordinal],headers)
                    if source_row.get('occurrence_no')!=occurrence or source_row.get('collection_no')!=number:
                        raise ValueError('A fossil context disagrees with its native identifiers.')
                    yield number,name,source_row,occurrence
            else:
                for occurrence,number,name,size,payload in native.execute(
                        'SELECT w.source_id,w.collection_no,w.name,r.source_bytes,r.source_values FROM requested w '
                        'JOIN source_rows r USING(source_id) ORDER BY w.source_id'):
                    source_row,_fields=pbdb_source.decode(payload,size,headers)
                    if source_row.get('occurrence_no')!=occurrence or source_row.get('collection_no')!=number:
                        raise ValueError('A fossil context disagrees with its native identifiers.')
                    yield number,name,source_row,occurrence
        finally:
            native.close()


def _read(source, database):
    """Yield (reference, label, latitude, longitude, south, north, west, east, note) from published fields only."""
    con = sqlite3.connect(database.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        if source == 'environments':
            for siteid, name, east, north, west, south in con.execute(
                    'SELECT siteid,sitename,longitudeeast,latitudenorth,longitudewest,latitudesouth FROM ndb__sites'):
                try:
                    east, north, west, south = (float(value) for value in (east, north, west, south))
                except (TypeError, ValueError):
                    continue
                if not (-90 <= south <= north <= 90 and -180 <= west <= 180 and -180 <= east <= 180):
                    continue
                if west > east:
                    # The area crosses the antimeridian: unwrap for its centre and keep a full-longitude extent.
                    centre = ((west + east + 360) / 2 + 180) % 360 - 180
                    yield ('site:' + str(siteid), name or 'Published site', (south + north) / 2, centre,
                           south, north, -180.0, 180.0, 'Bounding area crossing the antimeridian')
                    continue
                yield ('site:' + str(siteid), name or 'Published site', (south + north) / 2, (west + east) / 2,
                       south, north, west, east, 'Point' if (south, west) == (north, east) else 'Bounding area')
        elif source == 'site_registers':
            positions = {}
            for edition, headers in con.execute('SELECT id,headers FROM editions'):
                names = json.loads(zlib.decompress(headers))
                if 'Latitude (WGS-84)' in names and 'Longitude (WGS-84)' in names:
                    positions[edition] = tuple(names.index(key) if key in names else None
                                               for key in ('Latitude (WGS-84)', 'Longitude (WGS-84)', 'Geospatial note'))
            sites = {rowid: (identifier, title) for rowid, identifier, title in con.execute('SELECT rowid,id,title FROM sites')}
            seen = set()
            for site_key, edition, values in con.execute(
                    'SELECT site_key,edition,source_values FROM records WHERE site_key IS NOT NULL ORDER BY site_key,edition,ordinal'):
                if site_key in seen or edition not in positions or site_key not in sites:
                    continue
                cells = json.loads(zlib.decompress(values))
                latitude_index, longitude_index, note_index = positions[edition]
                try:
                    latitude, longitude = float(cells[latitude_index]), float(cells[longitude_index])
                except (IndexError, TypeError, ValueError):
                    continue
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    continue
                seen.add(site_key)
                note = cells[note_index] if note_index is not None and note_index < len(cells) else ''
                identifier, title = sites[site_key]
                yield ('site:' + identifier, title, latitude, longitude, latitude, latitude, longitude, longitude,
                       note or 'Location note not recorded')
        elif source == 'dinosaurs':
            for number, name, source_row, occurrence in _pbdb_collections(con,database):
                try:
                    latitude, longitude = float(source_row.get('lat')), float(source_row.get('lng'))
                except (TypeError, ValueError):
                    continue
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    continue
                precision = ' · '.join(str(source_row[key]) for key in ('latlng_precision', 'geogscale') if source_row.get(key))
                note='Source precision: '+(precision or 'not recorded')
                if source_row.get('latlng_basis'):
                    note+=' · Basis: '+source_row['latlng_basis']
                if occurrence is not None:
                    note+=' · Native context occurrence: '+occurrence
                yield ('collection:' + str(number), name or 'Published fossil collection', latitude, longitude,
                       latitude, latitude, longitude, longitude, note)
        elif source == 'finland':
            from pyproj import Transformer
            transformer = Transformer.from_crs(3067, 4326, always_xy=True)
            for key, name, municipality, payload in con.execute(
                    'SELECT record_key,name,municipality,payload_gzip FROM resources'):
                features = json.loads(gzip.decompress(payload))['features']
                point = next((feature['attributes'] for feature in features
                              if feature['layer'] == 'arkeologiset_kohteet_piste_t'
                              and isinstance(feature['attributes'].get('x'), (int, float))), None)
                if point is None:
                    continue
                longitude, latitude = transformer.transform(point['x'], point['y'])
                accuracy = point.get('paikannustarkkuus') or 'not recorded'
                yield (key, (name or 'Unnamed register site') + ' · ' + (municipality or ''), latitude, longitude,
                       latitude, latitude, longitude, longitude, 'Declared accuracy: ' + accuracy)
    finally:
        con.close()


def _build(source, database, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name+'.'+uuid4().hex+'.partial')
    con = sqlite3.connect(partial)
    try:
        con.executescript('''CREATE TABLE points(id INTEGER PRIMARY KEY,ref TEXT NOT NULL,label TEXT NOT NULL,
                                 latitude REAL NOT NULL,longitude REAL NOT NULL,note TEXT NOT NULL);
                             CREATE VIRTUAL TABLE extent USING rtree(id,south,north,west,east);''')
        for number, (ref, label, latitude, longitude, south, north, west, east, note) in enumerate(_read(source, database), 1):
            con.execute('INSERT INTO points VALUES(?,?,?,?,?,?)', (number, ref, str(label), latitude, longitude, note))
            con.execute('INSERT INTO extent VALUES(?,?,?,?,?)', (number, south, north, west, east))
        con.commit()
    finally:
        con.close()
    partial.replace(target)


def _ensure(source, database):
    target = _index_path(source, database)
    if target.exists():
        return target
    with _LOCK:
        if _ERROR_KEYS.get(source)==str(target):
            return None
        if source in _BUILDING:
            return None
        _BUILDING.add(source)

    def work():
        try:
            _build(source, database, target)
            _ERRORS.pop(source, None)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, sqlite3.Error) as error:
            _ERRORS[source] = str(error)
            _ERROR_KEYS[source] = str(target)
        finally:
            with _LOCK:
                _BUILDING.discard(source)
    Thread(target=work, name='clovis-nearby-' + source, daemon=True).start()
    return None


def _distance(latitude, longitude, other_latitude, other_longitude):
    a = (sin(radians(other_latitude - latitude) / 2) ** 2
         + cos(radians(latitude)) * cos(radians(other_latitude)) * sin(radians(other_longitude - longitude) / 2) ** 2)
    return 2 * 6371.0088 * asin(sqrt(max(0,min(1,a))))


def nearby(latitude, longitude, radius_km=30, limit=6, sources=None):
    """Group published records within radius_km of a public point; report sources still preparing."""
    if (any(type(value) not in (int,float) or not isfinite(value) for value in (latitude,longitude,radius_km))
            or not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or not 0 < radius_km <= 200
            or type(limit) is not int or not 1<=limit<=24
            or sources is not None and (not isinstance(sources,(tuple,list)) or any(source not in LABELS for source in sources))):
        raise ValueError('Choose a public town point and a distance up to 200 km.')
    groups, preparing, errors = [], [], {}
    span_latitude = radius_km / 111.0
    span_longitude = radius_km / max(1e-6, 111.0 * cos(radians(latitude)))
    for source, database in _databases(sources).items():
        if sources is not None and source not in sources:
            continue
        index = _ensure(source, database)
        if index is None:
            if source in _ERRORS and _ERROR_KEYS.get(source)==str(_index_path(source,database)):
                errors[source]='Published coordinate indexing is unavailable for this installed edition. Its Atlas records remain readable.'
            else:
                preparing.append(LABELS[source])
            continue
        con = sqlite3.connect(index.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            west,east=longitude-span_longitude,longitude+span_longitude
            windows=([(-180,180)] if span_longitude>=180 else
                     [(-180,east),(west+360,180)] if west<-180 else
                     [(west,180),(-180,east-360)] if east>180 else [(west,east)])
            found={}
            for west,east in windows:
                for row in con.execute('SELECT p.id,p.ref,p.label,p.latitude,p.longitude,p.note FROM extent e JOIN points p ON p.id=e.id '
                                       'WHERE e.north>=? AND e.south<=? AND e.east>=? AND e.west<=?',
                                       (latitude-span_latitude,latitude+span_latitude,west,east)):
                    found[row[0]]=row[1:]
            rows=[(key,*row) for key,row in found.items()]
        finally:
            con.close()
        within = sorted(((_distance(latitude, longitude, row[3], row[4]), row) for row in rows), key=lambda item: item[0])
        within = [(distance, row) for distance, row in within if distance <= radius_km]
        if within:
            groups.append({'source': source, 'label': LABELS[source], 'note': NOTES[source], 'total': len(within),
                           'rows': [{'point_id':row[0],'ref': row[1], 'label': row[2], 'distance_km': round(distance, 1), 'note': row[5]}
                                    for distance, row in within[:limit]]})
    groups.sort(key=lambda group: group['rows'][0]['distance_km'])
    return {'radius_km': radius_km, 'groups': groups, 'preparing': preparing,
            'errors': errors, 'coverage': COVERAGE}
