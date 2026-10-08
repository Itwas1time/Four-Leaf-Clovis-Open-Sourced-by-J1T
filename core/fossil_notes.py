"""Readable, source-preserving fossil specimen references."""
from datetime import datetime, timezone
import hashlib
import re
from core.fieldbook import validate_book
from core.resident_context import _md


def text(value):
    if isinstance(value,str):
        return value
    if isinstance(value,list):
        return '; '.join(text(item) for item in value if text(item))
    if isinstance(value,dict):
        if 'label' in value and 'value' in value:
            return str(value['label'])+': '+str(value['value'])
        return '; '.join(key.replace('_',' ').title()+': '+text(item) for key,item in value.items() if text(item))
    return ''


def facts(record):
    fields=[('Scientific name','taxon_name'),('Specimen number','specimen_number'),
            ('Geological age','geological_age'),('Stratigraphy','stratigraphy'),
            ('Measurements','measurements'),('Specimen description','physical_description'),
            ('Material','materials'),('Type status','type_status'),('Type citation','type_citation'),
            ('Taxonomy','taxonomic_hierarchy'),('Collection','institution')]
    result=[]
    for label,key in fields:
        value=text(record.get(key))
        if not value and key in ('geological_age','stratigraphy'):
            value=text(record.get(key+'_text'))
        if value:
            result.append((label,value))
    return result


def reference_entry(record):
    if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch(r'paleo:[A-Za-z0-9_-]{1,160}',record['id']):
        raise ValueError('Choose a fossil specimen from the library.')
    for key in ('title','source_url','license'):
        if not isinstance(record.get(key),str) or not record[key] or len(record[key].encode('utf-8'))>2000:
            raise ValueError('This fossil reference contains unsupported text.')
    lines=['# Fossil specimen reference — '+_md(record['title']),'','A museum specimen reference, not a documented find at your town.','']
    for label,value in facts(record):
        if len(value.encode('utf-8'))>12000:
            raise ValueError('This fossil reference contains unsupported text.')
        lines.append(f'- {label}: {_md(value)}')
    lines.extend(['','Source record: '+_md(record['source_url']),'Metadata rights: '+_md(record['license']),
                  'Catalog identifier: '+_md(record['id']),'','Geological ages and classifications describe the source specimen. Reference photographs are not attached.'])
    markdown='\n'.join(lines)
    row={'id':hashlib.sha256(('fossil-reference:'+record['id']+markdown).encode()).hexdigest()[:24],
         'kind':'investigation','title':('Fossil reference · '+record['title']).encode()[:120].decode('utf-8','ignore'),
         'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
         'summary':{'mission':'Fossil reference','source':record['source_url'].encode()[:1500].decode('utf-8','ignore'),
                    'outcome':'Museum specimen reference; not a local occurrence'},'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row
