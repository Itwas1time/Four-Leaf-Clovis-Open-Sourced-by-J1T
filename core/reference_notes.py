"""Save a catalog reference, explicitly separate from an observed local find."""
from datetime import datetime, timezone
import hashlib
import re
from core.fieldbook import validate_book
from core.resident_context import _md
from core.reference_catalog import facts


def reference_entry(record):
    if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch(r'(?:met:[1-9][0-9]{0,9}|si:[A-Za-z0-9_-]{1,120})',record['id']):
        raise ValueError('Choose a museum object from the reference library.')
    fields={}
    for key in ('title','object_type','material','date','culture','institution','source_url','license','catalog_number','topic','material_basis'):
        value=record.get(key,'')
        if not isinstance(value,str) or len(value.encode('utf-8'))>12000:
            raise ValueError('This reference contains unsupported text.')
        fields[key]=value
    lines=[f"# Museum reference — {_md(fields['title'])}",'','A cataloged museum object, not an observation or find at your town.','']
    for label,value in facts(record):
        if len(value.encode('utf-8'))>12000:
            raise ValueError('This reference contains unsupported text.')
        lines.append(f"- {label}: {_md(value)}")
    for label,key in [('Source record','source_url'),('Metadata rights','license')]:
        if fields[key]:
            lines.append(f"- {label}: {_md(fields[key])}")
    lines += ['',f"Catalog identifier: {_md(record['id'])}",'','Catalog dates describe the reference object. They do not date a separate object by resemblance. Reference photographs are not included.']
    text='\n'.join(lines)
    row={'id':hashlib.sha256(('museum-reference:'+record['id']+text).encode()).hexdigest()[:24],
         'kind':'investigation','title':('Reference · '+fields['title']).encode()[:120].decode('utf-8','ignore'),
         'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
         'summary':{'mission':'Museum reference','source':fields['source_url'].encode()[:1500].decode('utf-8','ignore'),
                    'material':fields['material'].encode()[:1500].decode('utf-8','ignore'),
                    'date':fields['date'].encode()[:1500].decode('utf-8','ignore'),
                    'outcome':'Catalog reference; not a local find'},'markdown':text}
    validate_book({'version':1,'entries':[row]})
    return row
