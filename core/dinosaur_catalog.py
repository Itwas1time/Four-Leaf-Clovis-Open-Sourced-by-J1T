"""Published fossil occurrences with a retained specialist Dinosauria view."""
from contextlib import closing
from functools import lru_cache
import hashlib
import json
import re
import sqlite3
from core.data_packs import PackStore
from core import pbdb_source

PACK = 'dinosaur-sites'
PAGE_SIZE = 24

def definition():
    return PackStore().definition(PACK)

def database():
    return PackStore().resolve_file(PACK,'dinosaurs.sqlite')

def databases():
    store = PackStore()
    installed = store.installed_definition(PACK)
    if installed is None:
        return None
    names = ['dinosaurs.sqlite', *[row['name'] for row in installed['files']
                                 if row['name'].endswith('.sqlite') and row['name']!='dinosaurs.sqlite']]
    return tuple(store.resolve_file(PACK,name) for name in names)

def _full_snapshot(connection):
    return connection.execute('PRAGMA user_version').fetchone()[0]==2

def _native_source(connection,path,kind,number,shard=None):
    if kind=='taxa':
        name='taxonomy-source.sqlite'
    elif type(shard) is int and 0<=shard<4:
        name='fossil-source-'+str(shard)+'.sqlite'
    else:
        raise ValueError('The native fossil source partition is invalid.')
    headers=json.loads(connection.execute('SELECT headers_json FROM source_headers WHERE kind=?',(kind,)).fetchone()[0])
    # Read from the same already-verified installation as the catalog. A later
    # active-pointer change must never pair old indexes with new source cells.
    source_path=path.parent/name
    if source_path.is_symlink() or source_path.resolve().parent!=path.parent:
        raise ValueError('The native fossil source must stay inside its verified installation.')
    with closing(_connect(source_path)) as native:
        if native.execute('PRAGMA user_version').fetchone()[0]==3:
            row=native.execute('SELECT s.block_ordinal,b.source_bytes,b.source_values,b.rows FROM source_rows s '
                'JOIN source_blocks b ON b.block_no=s.block_no WHERE s.source_id=?',(number,)).fetchone()
            if row is None:
                raise ValueError('The native fossil source row is absent.')
            return pbdb_source.decode_block(row['source_values'],row['source_bytes'],row['block_ordinal'],row['rows'],headers)
        row=native.execute('SELECT source_bytes,source_values FROM source_rows WHERE source_id=?',(number,)).fetchone()
    if row is None:
        raise ValueError('The native fossil source row is absent.')
    return pbdb_source.decode(row['source_values'],row['source_bytes'],headers)

def result_context(row):
    return row if 'collection_name' in row else json.loads(row.get('source_json','{}'))

def _connect(path):
    connection = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
    connection.row_factory = sqlite3.Row
    search=connection.execute("SELECT value FROM metadata WHERE key='search_database'").fetchone()
    if search is not None:
        if json.loads(search[0])!='fossil-search.sqlite':
            connection.close()
            raise ValueError('The fossil search file is invalid.')
        search_path=path.parent/'fossil-search.sqlite'
        if search_path.is_symlink() or search_path.resolve().parent!=path.parent:
            connection.close()
            raise ValueError('The fossil search must stay inside its verified installation.')
        connection.execute('ATTACH DATABASE ? AS fossil_search',(search_path.as_uri()+'?mode=ro&immutable=1',))
    return connection

def stats():
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])

def _location_value(value):
    return (isinstance(value,str) and len(value)<=160
            and not any(ord(char)<32 or 0xD800<=ord(char)<=0xDFFF for char in value))


def validate_location_filters(country='all', state=None, collection_no=''):
    if (not _location_value(country) or state is not None and not _location_value(state)
            or not isinstance(collection_no,str) or collection_no and not re.fullmatch(r'[0-9]{1,12}',collection_no)):
        raise ValueError('Choose a valid published fossil location or collection.')


@lru_cache(maxsize=64)
def _location_counts(path, signature, country, lineage, column):
    if column not in ('country','state'):
        raise ValueError('Choose a recorded location field.')
    clauses, values = [], []
    with closing(_connect(path)) as connection:
        if _full_snapshot(connection) and lineage!='fossils':
            clauses.append('is_dinosaur=1')
        if lineage not in ('all','fossils'):
            clauses.append('is_avian=?')
            values.append(int(lineage=='avian'))
        if country!='all':
            clauses.append('country=?')
            values.append('' if country=='__unknown__' else country)
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        return tuple(connection.execute('SELECT '+column+',count(*) FROM occurrences'+where+' GROUP BY '+column+' ORDER BY '+column,values))  # nosec B608


def states(country='all', lineage='fossils'):
    """Literal source regions, with counts of occurrences in the chosen group."""
    if not _location_value(country) or lineage not in ('all','nonavian','avian','fossils'):
        raise ValueError('Choose a valid fossil location filter.')
    path=database()
    if path is None:
        return []
    stat=path.stat()
    rows=_location_counts(path,(stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size),country,lineage,'state')
    # Prefix every UI value so native labels such as "all" cannot collide
    # with the chooser's all-regions action. An empty source stays empty.
    return [{'label':state or 'Not recorded (blank)', 'value':'region:'+state, 'records':count}
            for state,count in rows]


def countries(lineage='fossils'):
    """Country counts for the selected fossil group, rather than all Dinosauria."""
    if lineage not in ('all','nonavian','avian','fossils'):
        raise ValueError('Choose a fossil group.')
    path=database()
    if path is None:
        return []
    stat=path.stat()
    rows=_location_counts(path,(stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size),'all',lineage,'country')
    return [{'label':country or 'Not recorded','value':country or '__unknown__','records':count} for country,count in rows]


def search(query='', country='all', lineage='nonavian', view='occurrences', page=1, names_only=False, state=None, collection_no=''):
    validate_location_filters(country,state,collection_no)
    if (not isinstance(query,str) or len(query)>160 or any(ord(char)<32 or 0xD800<=ord(char)<=0xDFFF for char in query)
            or lineage not in ('all','nonavian','avian','fossils') or view not in ('occurrences','taxa')
            or type(names_only) is not bool
            or type(page) is not int or not 1<=page<=100_000):
        raise ValueError('Choose a valid fossil collection search.')
    path = database()
    if path is None:
        return {'rows':[],'total':0,'page':1,'pages':1,'installed':False,'view':view}
    clauses, parameters = [], []
    # unicode61 separates underscores; each emitted prefix is one token so
    # coded source values work with the compact column-detail index too.
    collection_id=re.fullmatch(r'collection:([0-9]{1,12})',query.strip())
    if collection_id:
        if collection_no and collection_no!=collection_id.group(1):
            clauses.append('0')
        collection_no=collection_id.group(1)
    terms = [] if collection_id else re.findall(r'[^\W_]+',query,flags=re.UNICODE)[:8]
    table = 'occurrences' if view=='occurrences' else 'taxa'
    if terms:
        clauses.append(f'r.rowid IN (SELECT rowid FROM {table}_fts WHERE {table}_fts MATCH ?)')  # nosec B608: fixed table choices
        expression = ' AND '.join('"'+term+'"*' for term in terms)
        if names_only:
            columns = 'accepted_name identified_name' if view=='occurrences' else 'name accepted_name'
            expression = '{'+columns+'} : ('+expression+')'
        parameters.append(expression)
    with closing(_connect(path)) as connection:
        full_snapshot=_full_snapshot(connection)
    if full_snapshot and lineage!='fossils':
        clauses.append('r.is_dinosaur=1')
    if lineage not in ('all','fossils'):
        clauses.append('r.is_avian=?')
        parameters.append(int(lineage=='avian'))
    location_clauses, location_values = [], []
    for column,value,include in (('country',country,country!='all'),('state',state,state is not None),
                                 ('collection_no',collection_no,bool(collection_no))):
        if include:
            location_clauses.append(column+'=?')
            location_values.append('' if column=='country' and value=='__unknown__' else value)
    if location_clauses:
        location_where=' AND '.join(location_clauses)
        if view=='occurrences':
            clauses.extend('r.'+clause for clause in location_clauses)
            parameters.extend(location_values)
        else:
            # Country and region must be recorded on the SAME occurrence.
            # Otherwise a taxon's Canadian Ontario and US Ohio records could
            # incorrectly establish an occurrence in US Ontario.
            # Each clause above uses a fixed column and a bound value.
            clauses.append('r.orig_no IN (SELECT accepted_no FROM occurrences WHERE '+location_where+' UNION SELECT identified_no FROM occurrences WHERE '+location_where+')')  # nosec B608
            parameters.extend([*location_values,*location_values])
    where = ' WHERE '+' AND '.join(clauses) if clauses else ''
    ordering = 'r.accepted_name,r.occurrence_no' if view=='occurrences' else 'r.name,r.orig_no'
    ordering_parameters=[]
    if terms:
        left,right=('r.accepted_name','r.identified_name') if view=='occurrences' else ('r.name','r.accepted_name')
        literal=query.strip().casefold()
        prefix=literal.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        ordering=('CASE WHEN lower('+left+')=? OR lower('+right+')=? THEN 0 '
                  'WHEN lower('+left+") LIKE ? ESCAPE '\\' OR lower("+right+") LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,"+ordering)  # nosec B608: fixed field choices with bound search values
        ordering_parameters=[literal,literal,prefix,prefix]
    with closing(_connect(path)) as connection:
        total = connection.execute(f'SELECT count(*) FROM {table} r'+where,parameters).fetchone()[0]  # nosec B608: fixed SQL choices and parameterized values
        pages = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
        page = min(page,pages)
        rows = [dict(row) for row in connection.execute(f'SELECT r.* FROM {table} r'+where+' ORDER BY '+ordering+' LIMIT ? OFFSET ?',  # nosec B608: fixed clauses, parameterized values
            [*parameters,*ordering_parameters,PAGE_SIZE,(page-1)*PAGE_SIZE])]
    for row in rows:
        row.pop('rowid',None)
        row['id'] = ('occ:' if view=='occurrences' else 'taxon:')+row['occurrence_no' if view=='occurrences' else 'orig_no']
    return {'rows':rows,'total':total,'page':page,'pages':pages,'installed':True,'view':view}

def relationships(record):
    """Browse explicit source collection IDs and literal region fields only."""
    if record['kind']!='occ':
        return []
    number=record['collection_no']
    country,state=record['country'],record['state']
    path=database()
    if path is None:
        return []
    with closing(_connect(path)) as connection:
        count=connection.execute('SELECT count(*) FROM occurrences WHERE collection_no=?',(number,)).fetchone()[0]
        links=[{'key':'collection','label':'Same published collection · '+number,'total':count,
                'parameters':{'collection':'dinosaurs','collection_no':number}}]
        # A blank is absence of a recorded region, not a shared place.
        if country and state and country not in ('all','__unknown__'):
            count=connection.execute('SELECT count(*) FROM occurrences WHERE country=? AND state=?',(country,state)).fetchone()[0]
            links.append({'key':'country-state','label':'Recorded region · '+state+', '+country,'total':count,
                          'parameters':{'collection':'dinosaurs','country':country,'state':state}})
    return links


def get_record(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'(?:occ|taxon):[0-9]{1,12}',identifier):
        return None
    kind,number = identifier.split(':')
    path = database()
    if path is None:
        return None
    table,key = ('occurrences','occurrence_no') if kind=='occ' else ('taxa','orig_no')
    with closing(_connect(path)) as connection:
        row = connection.execute(f'SELECT * FROM {table} WHERE {key}=?',(number,)).fetchone()  # nosec B608: two fixed identifier pairs
        if row is None:
            return None
        result = dict(row)
        result.pop('rowid',None)
        if _full_snapshot(connection):
            source,fields=_native_source(connection,path,'occurrences' if kind=='occ' else 'taxa',
                                         number if kind=='occ' else result['variant_no'],result.get('source_shard'))
            result.update(id=identifier,kind=kind,source=source,source_fields=fields)
        else:
            result.update(id=identifier,kind=kind,source=json.loads(result.pop('source_json')))
        if kind=='taxon':
            if _full_snapshot(connection):
                result['variants'] = [_native_source(connection,path,'taxa',row[0])[0] for row in
                    connection.execute('SELECT variant_no FROM taxon_variants WHERE orig_no=? ORDER BY variant_no',(number,))]
            else:
                result['variants'] = [json.loads(row[0]) for row in connection.execute('SELECT source_json FROM taxon_variants WHERE orig_no=? ORDER BY variant_no',(number,))]
            result['occurrences'] = [dict(row) for row in connection.execute('SELECT occurrence_no,accepted_name,identified_name,collection_no,country,state FROM occurrences WHERE accepted_no=? OR identified_no=? ORDER BY country,collection_no,occurrence_no LIMIT 24',(number,number))]
    return result

def source_url(record):
    number = record['source'].get('collection_no') if record['kind']=='occ' else record['orig_no']
    return ('https://paleobiodb.org/classic/basicCollectionSearch?collection_no=' if record['kind']=='occ' else 'https://paleobiodb.org/classic/basicTaxonInfo?taxon_no=')+number

def facts(record):
    source = record['source']
    if record['kind']=='taxon':
        return [('Original taxonomic name',source.get('taxon_name','')),('Snapshot accepted name',source.get('accepted_name','')),
                ('Original taxon ID',record['orig_no']),('Source rank',source.get('taxon_rank','')),
                ('Source name status / difference',source.get('difference','') or 'Not recorded'),
                ('Parent taxon',source.get('parent_name','')),('Source extant status',source.get('is_extant','')),
                ('Selected published occurrences',str(record['n_occurrences'])),
                ('Original taxonomic reference',source.get('primary_reference','') or 'Not recorded')]
    fields = [('Published identification','identified_name'),('Snapshot accepted name','accepted_name'),
              ('Source phylum','phylum'),('Source class','class'),('Source order','order'),('Source family','family'),
              ('Occurrence ID','occurrence_no'),('Collection / site ID','collection_no'),('Collection / site name','collection_name'),
              ('Source country code','cc'),('State / province','state'),('County / municipal area','county'),
              ('Reported latitude','lat'),('Reported longitude','lng'),('Location basis','latlng_basis'),
              ('Source coordinate precision','latlng_precision'),('Geographic scale','geogscale'),('Location comments','geogcomments'),
              ('Early interval','early_interval'),('Late interval','late_interval'),('Maximum age (Ma)','max_ma'),('Minimum age (Ma)','min_ma'),
              ('Formation','formation'),('Geological group','geological_group'),('Member','member'),('Lithology','lithology1'),
              ('Environment','environment'),('Collection methods','collection_methods'),('Museum / repository','museum'),
              ('Original reference','primary_reference'),('Reference ID','reference_no'),('Source protected-land code','protected')]
    return [(label,source.get(key,'') or 'Not recorded') for label,key in fields]

def reference_entry(identifier):
    from datetime import datetime, timezone
    from core.fieldbook import validate_book
    from core.resident_context import _md
    record = get_record(identifier)
    if record is None:
        raise ValueError('Choose a published record from the installed fossil collection.')
    summary = stats()
    title = (record['accepted_name'] or record['identified_name'] or 'Occurrence '+record['occurrence_no']) if record['kind']=='occ' else record['name']
    label='dinosaur' if record.get('is_dinosaur',True) else 'fossil'
    lines = ['# Published '+label+' reference — '+_md(title),'']
    lines.extend('- '+label+': '+_md(value) for label,value in facts(record))
    lines.extend(['','## Source conventions',summary['location_note'],summary['count_note'],summary['scope'],
                  'No selected town or observation is assigned to this reference.','',source_url(record),
                  summary['citation'],summary['citation_url'],'Snapshot: '+summary['source_release'],'Rights: '+summary['license']])
    text = '\n'.join(lines)
    entry = {'id':hashlib.sha256(('dinosaur:'+identifier+':'+text).encode()).hexdigest()[:24],
        'kind':'investigation','title':label.capitalize()+' reference · '+title,
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'mission':'Published '+label+' reference','source':source_url(record),'outcome':identifier},'markdown':text}
    validate_book({'version':1,'entries':[entry]})
    return entry
