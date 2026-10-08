"""Published Dinosauria taxonomy and occurrences in an optional local pack."""
from contextlib import closing
import hashlib
import json
import re
import sqlite3
from core.data_packs import PackStore

PACK = 'dinosaur-sites'
PAGE_SIZE = 24

def definition():
    return PackStore().definition(PACK)

def database():
    return PackStore().resolve_file(PACK,'dinosaurs.sqlite')

def _connect(path):
    connection = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
    connection.row_factory = sqlite3.Row
    return connection

def stats():
    path = database()
    if path is None:
        return None
    with closing(_connect(path)) as connection:
        return json.loads(connection.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])

def search(query='', country='all', lineage='nonavian', view='occurrences', page=1, names_only=False):
    if (not isinstance(query,str) or len(query)>160 or any(ord(char)<32 or 0xD800<=ord(char)<=0xDFFF for char in query)
            or not isinstance(country,str) or len(country)>80 or any(ord(char)<32 for char in country)
            or lineage not in ('all','nonavian','avian') or view not in ('occurrences','taxa')
            or type(names_only) is not bool
            or type(page) is not int or not 1<=page<=100_000):
        raise ValueError('Choose a valid dinosaur collection search.')
    path = database()
    if path is None:
        return {'rows':[],'total':0,'page':1,'pages':1,'installed':False,'view':view}
    clauses, parameters = [], []
    terms = re.findall(r'\w+',query,flags=re.UNICODE)[:8]
    table = 'occurrences' if view=='occurrences' else 'taxa'
    if terms:
        clauses.append(f'r.rowid IN (SELECT rowid FROM {table}_fts WHERE {table}_fts MATCH ?)')  # nosec B608: fixed table choices
        expression = ' AND '.join('"'+term+'"*' for term in terms)
        if names_only:
            columns = 'accepted_name identified_name' if view=='occurrences' else 'name accepted_name'
            expression = '{'+columns+'} : ('+expression+')'
        parameters.append(expression)
    if lineage!='all':
        clauses.append('r.is_avian=?')
        parameters.append(int(lineage=='avian'))
    if country!='all':
        country = '' if country=='__unknown__' else country
        if view=='occurrences':
            clauses.append('r.country=?')
        else:
            clauses.append('r.orig_no IN (SELECT accepted_no FROM occurrences WHERE country=? UNION SELECT identified_no FROM occurrences WHERE country=?)')
            parameters.append(country)
        parameters.append(country)
    where = ' WHERE '+' AND '.join(clauses) if clauses else ''
    ordering = 'r.accepted_name,r.occurrence_no' if view=='occurrences' else 'r.name,r.orig_no'
    with closing(_connect(path)) as connection:
        total = connection.execute(f'SELECT count(*) FROM {table} r'+where,parameters).fetchone()[0]  # nosec B608: fixed SQL choices and parameterized values
        pages = max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
        page = min(page,pages)
        rows = [dict(row) for row in connection.execute(f'SELECT r.* FROM {table} r'+where+' ORDER BY '+ordering+' LIMIT ? OFFSET ?',  # nosec B608: fixed clauses, parameterized values
            [*parameters,PAGE_SIZE,(page-1)*PAGE_SIZE])]
    for row in rows:
        row.pop('rowid',None)
        row['id'] = ('occ:' if view=='occurrences' else 'taxon:')+row['occurrence_no' if view=='occurrences' else 'orig_no']
    return {'rows':rows,'total':total,'page':page,'pages':pages,'installed':True,'view':view}

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
        result.update(id=identifier,kind=kind,source=json.loads(result.pop('source_json')))
        if kind=='taxon':
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
        raise ValueError('Choose a published record from the installed dinosaur collection.')
    summary = stats()
    title = record['accepted_name'] if record['kind']=='occ' else record['name']
    lines = ['# Published dinosaur reference — '+_md(title),'']
    lines.extend('- '+label+': '+_md(value) for label,value in facts(record))
    lines.extend(['','## Source conventions',summary['location_note'],summary['count_note'],summary['scope'],
                  'No selected town or observation is assigned to this reference.','',source_url(record),
                  summary['citation'],summary['citation_url'],'Snapshot: '+summary['source_release'],'Rights: '+summary['license']])
    text = '\n'.join(lines)
    entry = {'id':hashlib.sha256(('dinosaur:'+identifier+':'+text).encode()).hexdigest()[:24],
        'kind':'investigation','title':'Dinosaur reference · '+title,
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'mission':'Published dinosaur reference','source':source_url(record),'outcome':identifier},'markdown':text}
    validate_book({'version':1,'entries':[entry]})
    return entry
