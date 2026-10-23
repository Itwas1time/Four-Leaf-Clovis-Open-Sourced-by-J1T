"""Read native French operation rows without turning categories into dig counts."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3

from core.data_packs import PackStore

PACK='france-fieldwork'
PAGE_SIZE=24
LICENSE='Licence Ouverte 2.0 (native license ID lov2); attribute Département des Alpes de Haute-Provence and source update 8 January 2020. Linked reports and images have separate rights.'
POLICY='https://www.data.gouv.fr/pages/legal/licences/etalab-2.0'
FIELDS={'all':'Original operation metadata','places':'Recorded municipality / place only','identifiers':'Original SDA / SRA identifiers only'}
EXCAVATION=('Fouille programmée','Fouille préventive')
TYPES={
    'Diagnostic':'Diagnostic assessment','Fouille programmée':'Research excavation',
    'Fouille préventive':'Preventive excavation','Urgence absolue':'Emergency work',
    'Prospection-inventaire':'Inventory survey','/':'Original placeholder /',
    '[Porteur extérieur]':'External lead (original label)','Sondage':'Test investigation',
    'PCR':'Collective research programme','Prospection thématique':'Thematic survey',
}
EXCAVATION_LABEL='Excavation categories · Fouille programmée + Fouille préventive'
NOTES=(
    'One original operation-table row in a regional 2011–2019 table. The publisher describes completed operations with submitted and validated reports. This is not a French national or worldwide excavation census.',
    'Authorization categories include diagnostics, surveys and other work. Fouille programmée is a research-excavation category, not a planned/future status. The two explicit Fouille categories do not capture every possible excavation activity.',
    'Native SDA codes are local identifiers; SRA values are separate original strings. Repeated SRA values do not establish identity. Same-site operations and overlap with other catalogs remain unresolved.',
    'Municipality and place names are original text. This table supplies no coordinates, property boundaries or location precision. No point is inferred from a town name.',
    'Prescription, received-prescription, start, end, report and year fields remain separate original strings. No fieldwork date is derived from an identifier year. Empty fields and source placeholders remain distinct.',
    'Emprise m² is the original stated project area field, not an inferred excavated area, material quantity or find count. No area total or unit conversion is supplied.',
)
KEY=re.compile(r'alpes04/[A-Za-z0-9][A-Za-z0-9._/-]{0,79}~[a-f0-9]{64}\Z')


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def advertised():
    return PACK in {row['id'] for row in PackStore().definitions}


def database():
    store=PackStore()
    return store.resolve_file(PACK,'france.sqlite') if PACK in {row['id'] for row in store.definitions} else None


def connect(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA trusted_schema=OFF')
    return db


def validate_parameters(query='',page=1,method='',field='all'):
    if (not isinstance(query,str) or len(query)>120 or any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in query)
            or type(page) is not int or not 1<=page<=1_000_000
            or not isinstance(method,str) or method not in ('','excavation',*TYPES)
            or not isinstance(field,str) or field not in FIELDS):
        raise ValueError('Choose a French operation category and original text field.')


def stats():
    path=database()
    if path is None:return None
    with closing(connect(path)) as db:
        return json.loads(db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])


def choices():
    path=database()
    if path is None:return []
    with closing(connect(path)) as db:
        rows=db.execute('SELECT method,count(*) AS records FROM resources GROUP BY method ORDER BY method').fetchall()
    return [{'value':row['method'],'label':row['method']+' · '+TYPES.get(row['method'],'Original value'),
        'records':row['records']} for row in rows]


def search(query='',page=1,method='',field='all'):
    validate_parameters(query,page,method,field)
    path=database()
    if path is None:return {'rows':[],'total':0,'page':1,'installed':False}
    clauses,parameters=[],[]
    if method=='excavation':
        clauses.append('method IN (?,?)')
        parameters.extend(EXCAVATION)
    elif method:
        clauses.append('method=?')
        parameters.append(method)
    words=re.findall(r'[^\W_]+',query,flags=re.UNICODE)
    if words:
        column={'all':'all_text','places':'places','identifiers':'identifiers'}[field]
        clauses.append('rowid IN (SELECT rowid FROM resource_fts WHERE '+column+' MATCH ?)')  # nosec B608
        parameters.append(' AND '.join('"'+word+'"' for word in words))
    where=' WHERE '+' AND '.join(clauses) if clauses else ''
    with closing(connect(path)) as db:
        total=db.execute('SELECT count(*) FROM resources'+where,parameters).fetchone()[0]  # nosec B608
        page=min(page,max(1,(total+PAGE_SIZE-1)//PAGE_SIZE))
        # Clause text uses only the closed mappings above; all supplied values are bound.
        rows=db.execute('SELECT record_key AS id,code,title,method,place_text FROM resources'+where+  # nosec B608
            ' ORDER BY code,record_key LIMIT ? OFFSET ?',(*parameters,PAGE_SIZE,(page-1)*PAGE_SIZE)).fetchall()
    return {'rows':[{**dict(row),'category':'Published operation-table row',
        'subtitle':row['method']+' · '+row['place_text']} for row in rows],
        'total':total,'page':page,'installed':True}


def get_record(key):
    if not isinstance(key,str) or not KEY.fullmatch(key):return None
    path=database()
    if path is None:return None
    with closing(connect(path)) as db:
        row=db.execute('SELECT * FROM resources WHERE record_key=?',(key,)).fetchone()
        if row is None:return None
        source=json.loads(db.execute("SELECT value FROM metadata WHERE key='source'").fetchone()[0])
    result=dict(row)
    original={'format':'clovis-france-operation-row-1','source':source,
        'row_ordinal':result['ordinal'],'headers':source['headers'],'values':json.loads(result.pop('values_json'))}
    if (hashlib.sha256(canonical(original)).hexdigest()!=result['edition_sha256']
            or key!='alpes04/'+original['values'][0]+'~'+result['edition_sha256']):
        raise ValueError('The original operation row differs from its cited edition.')
    result.update(id=key,category='Published operation-table row',subtitle=result['method']+' · '+result['place_text'],
        original=original,source_url=source['catalog']['page'])
    return result


def fields(row):
    original=row['original']
    source=original['source']
    return [('Publisher','Département des Alpes de Haute-Provence'),
        ('Native catalog ID',source['catalog']['id']),('Native CSV resource UUID',source['receipt']['resource_id']),
        ('Source resource edition',source['receipt']['declared_resource_modified']),
        ('Original CSV SHA-256',source['receipt']['sha256']),('Source row ordinal (not a global event ID)',str(original['row_ordinal'])),
        ('Parsed row edition SHA-256',row['edition_sha256']),
        *[(label,value if value!='' else 'Not recorded (empty source field)') for label,value in zip(original['headers'],original['values'],strict=True)]]


def reference_entry(key):
    from core.fieldbook import validate_citation_entry
    from core.resident_context import _md
    row=get_record(key)
    if row is None:raise ValueError('Choose a current French operation source row.')
    literal=lambda text:'\n'.join(_md(line) for line in text.split('\n'))
    lines=['# Published French operation source row','',literal(row['title']),'',literal(LICENSE),POLICY,row['source_url'],'']
    lines.extend(literal(label+': '+value)+'\n' for label,value in fields(row))
    lines.extend(literal(note)+'\n' for note in NOTES)
    lines.extend(['## Complete original row and catalog edition JSON','',literal(json.dumps(row['original'],ensure_ascii=False,indent=2))])
    markdown='\n'.join(lines)
    entry={'id':hashlib.sha256(markdown.encode('utf-8')).hexdigest()[:24],'kind':'investigation',
        'title':('France · '+row['code']+' · '+row['place_text']).encode('utf-8')[:120].decode('utf-8','ignore'),
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'source':'Département des Alpes de Haute-Provence · '+row['code'],
            'outcome':'Published source metadata; no new field observation'},'markdown':markdown}
    return validate_citation_entry(entry)
