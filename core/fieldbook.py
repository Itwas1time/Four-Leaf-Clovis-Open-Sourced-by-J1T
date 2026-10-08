"""Portable, bounded field notes. Imported Markdown is displayed as plain text."""
from datetime import datetime, timezone
import hashlib
import json
import re

MAX_ENTRIES = 50
MAX_BYTES = 750_000
EMPTY_BOOK = {'version':1,'entries':[]}
FIELDS = {'place','material','history','maps','setting','features','size','follow_up','mission','source','date','outcome','steps'}


def validate_book(value):
    if not isinstance(value,dict) or set(value) != {'version','entries'} or type(value['version']) is not int or value['version'] != 1 or not isinstance(value['entries'],list) or len(value['entries'])>MAX_ENTRIES:
        raise ValueError('Use a Clovis fieldbook with up to 50 investigations.')
    try: size=len(json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8'))
    except (ValueError,TypeError,UnicodeError): raise ValueError('The fieldbook has invalid text.') from None
    if size>MAX_BYTES: raise ValueError('Keep the fieldbook under 750 KB; export a backup before starting another.')
    ids=set()
    for row in value['entries']:
        if not isinstance(row,dict) or set(row) != {'id','kind','title','created','summary','markdown'}:
            raise ValueError('A saved investigation has an unsupported format.')
        if row['kind'] not in ('town','find','investigation') or not isinstance(row['id'],str) or not re.fullmatch(r'[a-f0-9]{24}',row['id']) or row['id'] in ids:
            raise ValueError('A saved investigation has an invalid identifier.')
        ids.add(row['id'])
        for key,limit in (('title',120),('created',32),('markdown',100_000)):
            if not isinstance(row[key],str) or len(row[key].encode('utf-8'))>limit or not row[key].strip():
                raise ValueError('A saved investigation has invalid or oversized text.')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00',row['created']):
            raise ValueError('Use a valid fieldbook date.')
        try: datetime.fromisoformat(row['created'])
        except ValueError: raise ValueError('Use a valid fieldbook date.') from None
        if not isinstance(row['summary'],dict) or not set(row['summary']).issubset(FIELDS):
            raise ValueError('A saved investigation has unsupported comparison fields.')
        if any(not isinstance(v,str) or len(v.encode('utf-8'))>1500 for v in row['summary'].values()):
            raise ValueError('A saved comparison field is too long.')
    return value


def new_entry(kind,report):
    from core.find_inspection import MATERIALS, SETTINGS, FEATURES
    from core.resident_context import CONTEXTS
    if kind == 'town':
        title=f"{report['place']['name']}, {report['place']['state']}"
        summary={'place':title,'history':CONTEXTS[report['key'][2]],
                 'maps':(report['geology_status'] + ': ' + '; '.join(report['mapped_units'])).encode('utf-8')[:1500].decode('utf-8','ignore')}
    else:
        title=MATERIALS[report['material']] + ' observation'
        summary={'material':MATERIALS[report['material']],'setting':SETTINGS[report['setting']],
                 'features':', '.join(FEATURES[f] for f in report['features']) or 'Not recorded',
                 'size':report['size'] or 'Not recorded'}
        if report.get('place'):
            summary['place'] = report['place']
            title += ' · ' + report['place']
    text=report['markdown']
    row={'id':hashlib.sha256((kind+text).encode()).hexdigest()[:24], 'kind':kind,
         'title':title.encode('utf-8')[:120].decode('utf-8','ignore'), 'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
         'summary':summary,'markdown':text}
    validate_book({'version':1,'entries':[row]})
    return row


def merge_entries(book,entries):
    current=validate_book(book)
    incoming=validate_book({'version':1,'entries':entries})
    known={row['id'] for row in current['entries']}
    merged={'version':1,'entries':[*current['entries'],*[row for row in incoming['entries'] if row['id'] not in known]]}
    return validate_book(merged)


def follow_up_entry(row, notes):
    """Keep the original snapshot and create a separately dated follow-up."""
    from core.resident_context import _md
    validate_book({'version':1,'entries':[row]})
    if not isinstance(notes,str) or not notes.strip() or len(notes)>1500:
        raise ValueError('Write a follow-up note of up to 1,500 characters.')
    updated=json.loads(json.dumps(row))
    updated['markdown'] += '\n\n## Your follow-up note\n\n' + _md(notes.strip()) + '\n\nUser-recorded observations; Clovis has not verified this source or interpretation.\n'
    updated['summary']['follow_up']=notes.strip().encode('utf-8')[:1500].decode('utf-8','ignore')
    updated['id']=hashlib.sha256((row['kind']+updated['markdown']).encode()).hexdigest()[:24]
    updated['title']=(row['title']+' · follow-up').encode('utf-8')[:120].decode('utf-8','ignore')
    updated['created']=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    validate_book({'version':1,'entries':[updated]})
    return updated


def readable_text(markdown):
    """Show saved notes as readable literal text; never interpret imported markup."""
    text=re.sub(r'^#{1,6}\s+','',markdown,flags=re.M)
    text=text.replace('**','')
    text=re.sub(r'\[([^\]\n]+)\]\((https://[^)\s]+)\)',r'\1 — \2',text)
    return re.sub(r'\\([\\`*_{}\[\]<>()!#|~+\-.=])',r'\1',text)
