"""Readable national map facts and immutable regional-geology references."""
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urlsplit
from core.fieldbook import validate_book
from core.resident_context import _md


def _quoted_url(value):
    # A URL embedded in bibliographic prose is literal source text. Keep its
    # punctuation/underscores without letting Markdown autolink escaped text.
    width=max((len(match[0]) for match in re.finditer(r'`+',value)),default=0)+1
    fence='`'*width
    return fence+' '+value+' '+fence


def citation_markdown(citation):
    """Escape source prose separately from its explicit original URL."""
    text=citation.get('text','')
    text=text if isinstance(text,str) else ''
    parts=re.split(r'(https?://\S+)',text)
    prose=''.join(_quoted_url(part) if index%2 else _md(part) for index,part in enumerate(parts))
    url=citation.get('url','')
    if not isinstance(url,str) or not url:
        return prose
    try:
        parsed=urlsplit(url)
        safe=(parsed.scheme in ('http','https') and bool(parsed.hostname) and not parsed.username
              and not parsed.password and parsed.port in (None,80,443) and len(url)<=2048
              and not any(character.isspace() or ord(character)<32 or character in '\\<>"`' for character in url))
    except ValueError:
        safe=False
    link='[Read original map source](<'+url+'>)' if safe else _quoted_url(url)
    return prose+' '+link


def facts(unit):
    fields=(('Map theme','layer_label'),('Map unit','map_unit'),('Full unit name','full_name'),
            ('Geological age','age'),('Geomaterial','geomaterial'),('Description','description'))
    return [(label,unit[key]) for label,key in fields if isinstance(unit.get(key),str) and unit[key].strip()]


def reference_entry(unit,place=None):
    if not isinstance(unit,dict) or not isinstance(unit.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',unit['id']):
        raise ValueError('Choose a mapped unit from the geology library.')
    lines=['# Regional geology reference — '+_md(unit['name']),'',
           'USGS Cooperative National Geologic Map v2 (2026) · 1:500,000 scale.']
    summary={'mission':'Geology reference','source':'https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm',
             'outcome':'Regional map context; not a property assessment'}
    if isinstance(place,dict):
        label=place['name']+', '+place['state']
        lines+=['','Mapped at the public Census representative point for '+_md(label)+'.']
        summary['place']=label
    lines.append('')
    for label,value in facts(unit):
        lines.append(f'- {label}: {_md(value)}')
    sources=unit.get('source_units',[])
    for source in sources[:10]:
        lines+=['','## Recorded source-map unit',_md(source.get('source_name') or source.get('source_mapunit') or '')]
        if not source.get('source_name') and not source.get('source_full_name'):
            lines.append('The USGS source table does not provide a description for this mapped source code.')
        for key,label in (('source_mapunit','Source map unit'),('source_age','Recorded age'),
                          ('geomaterial','Geomaterial'),('source_description','Source description')):
            if isinstance(source.get(key),str) and source[key].strip():
                lines.append(f'- {label}: {_md(source[key])}')
        for citation in source.get('source_citations',[])[:10]:
            lines.append(citation_markdown(citation))
    if len(sources)>10:
        lines+=['',f'Included the first 10 of {len(sources)} returned source-map units; the library retains the other units.']
    lines+=['','## Source citations']
    for citation in unit.get('source_citations',[])[:20]:
        lines.append(citation_markdown(citation))
    lines+=['','https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm','USGS release data: CC0 1.0.',
            'The four map themes are separate mapping products, not a measured soil profile or a find prediction.']
    markdown='\n'.join(lines)
    row={'id':hashlib.sha256(('usgs-reference:'+unit['id']+markdown).encode()).hexdigest()[:24],
         'kind':'investigation','title':('Geology reference · '+unit['name']).encode()[:120].decode('utf-8','ignore'),
         'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'summary':summary,'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row
