"""Keep factual newspaper title references as portable fieldbook entries."""
from datetime import datetime,timezone
import hashlib
import re
from core.fieldbook import validate_book
from core.resident_context import _md


def facts(record):
    rows=[(label,record.get(key,'')) for label,key in [('Publication dates','publication_dates'),
           ('Language','languages'),('Frequency','frequency')] if isinstance(record.get(key),str) and record[key]]
    places=record.get('places',[])
    if isinstance(places,list):
        labels=[', '.join(v for v in (p.get('town',''),p.get('state_name','')) if isinstance(v,str) and v)
                for p in places if isinstance(p,dict)]
        if labels:
            rows.append(('Indexed places','; '.join(dict.fromkeys(labels))))
    rows.append(('LOC digitization flag','Digitized title' if record.get('digitized') is True else 'No digitized title flagged in this snapshot'))
    return rows


def reference_entry(record):
    if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch(r'(?:[a-z]{2,3}[0-9]{8,10}|[0-9]{8,10})',record['id'],re.I):
        raise ValueError('Choose a title from the newspaper catalog.')
    for key in ('title','url'):
        if not isinstance(record.get(key),str) or not record[key] or len(record[key].encode('utf-8'))>2000:
            raise ValueError('This newspaper reference contains unsupported text.')
    lines=['# Newspaper title reference — '+_md(record['title']),'','Bibliographic record; no newspaper issue or article was read.','']
    for label,value in facts(record):
        if len(value.encode('utf-8'))>12000:
            raise ValueError('This newspaper reference contains oversized text.')
        lines.append(f'- {label}: {_md(value)}')
    lines.extend(['','Source: '+_md(record['url']),'LCCN: '+_md(record['id'])])
    if record.get('snapshot_complete') is False:
        lines+=['',f"Partial LOC directory snapshot: {record.get('source_pages_observed',0)} of {record.get('source_pages_expected',0)} pages. This title's facts are recorded; absent titles are not evidence of absence."]
    markdown='\n'.join(lines)
    row={'id':hashlib.sha256(('newspaper-reference:'+record['id']+markdown).encode()).hexdigest()[:24],
         'kind':'investigation','title':('Newspaper · '+record['title']).encode()[:120].decode('utf-8','ignore'),
         'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
         'summary':{'mission':'Newspaper reference','source':record['url'].encode()[:1500].decode('utf-8','ignore'),
                    'date':str(record.get('publication_dates','')).encode()[:1500].decode('utf-8','ignore'),
                    'outcome':'Title citation; no article read'},'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row
