"""Preserve source learning guides separately from personal observations."""
from datetime import datetime,timezone
import hashlib
from core.fieldbook import validate_book
from core.resident_context import _md


def reference_entry(guide):
    lines=['# Object reading guide — '+_md(guide['title']),'',_md(guide['summary']),
           '','Source learning notes; no individual object was identified or observed.','']
    for fact in guide['facts']:
        lines+=['- '+_md(fact['text'])]
        lines.extend('  '+_md(source['name'])+' '+_md(source['url']) for source in fact['sources'])
    lines+=['','## Questions to examine']+['- '+_md(question) for question in guide['questions']]
    lines+=['','## Details to record']+['- '+_md(prompt) for prompt in guide['record']]
    markdown='\n'.join(lines)
    row={'id':hashlib.sha256(('object-guide:'+guide['id']+markdown).encode()).hexdigest()[:24],
         'kind':'investigation','title':('Object guide · '+guide['title']).encode()[:120].decode('utf-8','ignore'),
         'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
         'summary':{'mission':'Object guide','material':guide['category'],'source':guide['sources'][0]['url'],
                    'outcome':'Source learning guide; not an object identification'},'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row
