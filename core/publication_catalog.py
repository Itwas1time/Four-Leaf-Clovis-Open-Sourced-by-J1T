"""Small, pinned full-text editions and original source tables, entirely offline."""
from copy import deepcopy
import base64
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import hashlib
import gzip
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile, ZIP_DEFLATED

EDITION = 'panama-0335678'
DIRECTORY = Path(__file__).resolve().parents[1]/'atlas/gui/data/offline-publications'/EDITION
EDITION_SHA256 = '66c3971aa0dee23e8b115d2cca5336d97f833e35a97503497ae8302641c97a3d'
PAGE_SIZE = 24
NOTES = [
    'One publication and its ten supporting tables. These are source components, not eleven excavations.',
    'Earlier published measurements remain identified in the source captions and yellow workbook highlights. Overlapping rows are not new individuals or specimens.',
    'Source numbers, units, blanks, native categories, formulas and cached formula values are retained. Clovis does not recalculate the publisher workbooks.',
    'S7 Table describes modern river-water samples. Its coordinates do not locate archaeological finds.',
]


@lru_cache(maxsize=1)
def _edition():
    raw = (DIRECTORY/'edition.json').read_bytes().replace(b'\r\n',b'\n')
    if len(raw)>1_000_000 or hashlib.sha256(raw).hexdigest()!=EDITION_SHA256:
        raise ValueError('The bundled publication differs from its reviewed edition.')
    result = json.loads(raw)
    if result.get('schema')!=1 or result.get('id')!=EDITION or result.get('doi')!='10.1371/journal.pone.0335678':
        raise ValueError('The bundled publication needs review.')
    return result


def _normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def _records():
    edition = _edition()
    metadata = {key:edition[key] for key in ('doi','authors','publisher','published','citation','scope','rights','content_note')}
    inventory = [{key:value for key,value in item.items() if key!='workbook'} for item in edition['supplements']]
    article = {**metadata,'id':EDITION,'native_id':edition['doi'],'title':edition['title'],
        'category':'Research publication','subtitle':'Panama · Cerro Juan Díaz · Full text and methods offline',
        'description':'Complete paper text and two main tables, with ten separately readable supporting workbooks.',
        'file':edition['manuscript']['file'],'receipt':edition['manuscript']['receipt'],
        'blocks':edition['blocks'],'supplements':inventory}
    tables = [{**metadata,**item,'category':'Supporting source table',
        'title':item['label']+' · '+item['caption'].split('. ',1)[0].rstrip('.'),
        'subtitle':'Panama · Cerro Juan Díaz · Original table offline',
        'description':item['caption'],'parent':EDITION}
        for item in edition['supplements'] if item['included']]
    return (article,*tables)


def get_record(identifier):
    if not isinstance(identifier,str): return None
    try:
        return next((deepcopy(row) for row in _records() if row['id']==identifier),None)
    except (OSError,ValueError,KeyError,TypeError):
        return None


def search(query='',page=1):
    if not isinstance(query,str) or len(query)>120 or type(page) is not int or page<1:
        raise ValueError('Use a publication search of up to 120 characters and a positive page.')
    words = _normalize(query).split()
    exact = _normalize(query.strip()).removeprefix('https://doi.org/').removeprefix('doi:')
    direct = [row for row in _records() if exact in (_normalize(row['id']),_normalize(row['native_id']))]
    rows = direct or [row for row,haystack in _search_rows() if all(word in haystack for word in words)]
    return {'total':len(rows),'page':page,'rows':deepcopy(rows[(page-1)*PAGE_SIZE:page*PAGE_SIZE])}


@lru_cache(maxsize=1)
def _search_rows():
    return tuple((row,_normalize(json.dumps(row,ensure_ascii=False))) for row in _records())


def fields(row):
    return [('Original source ID',row['native_id']),('Source publication',row['doi']),
        ('Published',row['published']),('Content available offline',row['description']),
        ('Geographic scope',row['scope']),('Source edition retrieved',row['receipt']['retrieved_utc']),
        ('Original file SHA-256',row['receipt']['sha256'])]


def _cell_text(cell):
    return '' if cell[1] is None else str(cell[1])


def reading_text(row):
    lines = [row['title'],'',row['citation'],'Original source ID: '+row['native_id'],
        'Retrieved: '+row['receipt']['retrieved_utc'],'Original file SHA-256: '+row['receipt']['sha256'],
        row['rights']['label']+' · '+row['rights']['url'],'',row['scope'],row['content_note'],'']
    if 'workbook' in row:
        lines.extend([row['caption'],row['workbook']['projection_note'],''])
        for sheet in row['workbook']['sheets']:
            lines.extend(['Sheet: '+sheet['name']+' · '+sheet['dimension'],
                'Each original cell address is followed by its literal value; blank cells remain blank.'])
            for address,cell in sheet['cells'].items():
                formula = ' [source formula: '+cell[3]['text']+'; shown value is its source cache]' if len(cell)>3 else ''
                style = row['workbook']['styles'][cell[2]]
                flags = (' [source fill '+json.dumps(style['fill'])+']') if style['fill'] else ''
                lines.append(address+'\t'+_cell_text(cell)+formula+flags)
            lines.append('')
    else:
        for block in row['blocks']:
            if block['type']=='table':
                lines.extend([block['label']+'. '+block['caption'],'Original table ID: '+block['native_id']])
                lines.extend('\t'.join(cell['text'] for cell in cells) for cells in block['rows'])
                lines.append(block['footnotes'])
            else:
                lines.append(block['text'])
            lines.append('')
    return '\n'.join(lines)


def reference_entry(identifier):
    from core.fieldbook import validate_book
    from core.resident_context import _md
    row = get_record(identifier)
    if row is None: raise ValueError('Choose an available publication or original source table.')
    literal = lambda value:'\n'.join(_md(line) for line in value.split('\n'))
    markdown = '# Published research source\n\n'+literal(reading_text(row))
    snapshot=deepcopy(row)
    raw,name=original_bytes(identifier)
    # The visible reading already carries the complete article text. Retaining
    # the exact native XML in compressed form avoids a second, larger text tree.
    # Table projections keep their cell-level fields and the exact XLSX original.
    if 'blocks' in snapshot:
        snapshot.pop('blocks')
        payload,encoding=gzip.compress(raw,mtime=0),'gzip+base64'
    else:
        payload,encoding=raw,'base64'
    snapshot['native_original']={'file':name,'encoding':encoding,'bytes':len(raw),
        'sha256':row['receipt']['sha256'],'data':base64.b64encode(payload).decode('ascii')}
    markdown += '\n\n## Complete source snapshot JSON\n\n'+literal(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')))
    entry = {'id':hashlib.sha256(('publication:'+identifier+markdown).encode()).hexdigest()[:24],
        'kind':'investigation','title':row['title'].encode()[:120].decode('utf-8','ignore'),
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'mission':'Published research source','source':row['citation'],
            'date':row['published'],'outcome':row['category']+'; original source evidence, not a new field observation'},
        'markdown':markdown}
    validate_book({'version':1,'entries':[entry]})
    return entry


def saved_reading(entry):
    """Keep machine provenance in backups while presenting the complete reading."""
    if entry.get('summary',{}).get('mission')!='Published research source': return None
    from core.fieldbook import readable_text
    text=readable_text(entry['markdown'])
    reading,separator,snapshot=text.partition('\n\nComplete source snapshot JSON\n\n')
    if not separator: return text
    _source,followed,note=snapshot.partition('\n\nYour follow-up note\n\n')
    return (reading.rstrip()+'\n\nThe complete native source and provenance are retained in the fieldbook backup and Download note text.'
        + ('\n\nYour follow-up note\n\n'+note if followed else ''))


def original_bytes(identifier):
    row = get_record(identifier)
    if row is None: raise ValueError('This source original is unavailable.')
    name = row['file']
    if name not in ('manuscript.xml',*('s%03d.xlsx'%i for i in range(7,17))):
        raise ValueError('This source file is outside the reviewed edition.')
    raw = (DIRECTORY/name).read_bytes()
    if len(raw)!=row['receipt']['bytes'] or hashlib.sha256(raw).hexdigest()!=row['receipt']['sha256']:
        raise ValueError('This source original differs from its reviewed edition.')
    return raw,name


def _coordinate(address):
    column,row = re.fullmatch(r'([A-Z]+)([0-9]+)',address).groups()
    number = 0
    for letter in column: number=number*26+ord(letter)-64
    return int(row),number


def _column(number):
    result = ''
    while number:
        number,remainder = divmod(number-1,26)
        result=chr(65+remainder)+result
    return result


def _display(cell,style):
    value = _cell_text(cell)
    number_format = style['number_format']
    if cell[0]=='n' and value and number_format=='General':
        try:
            shown=format(Decimal(value),'.15g')
            mantissa,separator,exponent=shown.partition('e')
            if '.' in mantissa: mantissa=mantissa.rstrip('0').rstrip('.')
            return mantissa+(separator+exponent if separator else '')
        except InvalidOperation: pass
    if cell[0]=='n' and value and re.fullmatch(r'0(?:\.0+)?%?',number_format):
        try:
            number = Decimal(value)*(100 if number_format.endswith('%') else 1)
            places = len(number_format.rstrip('%').split('.')[1]) if '.' in number_format else 0
            return f'{number:.{places}f}'+('%' if number_format.endswith('%') else '')
        except InvalidOperation: pass
    return value


def _workbook_html(workbook):
    parts = ['<p>'+escape(workbook['projection_note'])+'</p>']
    for sheet in workbook['sheets']:
        coordinates = [_coordinate(address) for address in sheet['cells']]
        max_row,max_column = max(r for r,c in coordinates),max(c for r,c in coordinates)
        active={}
        for address,cell in sheet['cells'].items():
            if cell[1] not in (None,''):
                active.setdefault(_coordinate(address)[0],[]).append((address,cell))
        notes={r:items[0] for r,items in active.items() if len(items)==1
            and items[0][1][0] in ('s','inlineStr') and len(_cell_text(items[0][1]))>160}
        parts.extend(['<h2>'+escape(sheet['name'])+'</h2>',
            '<p>Source sheet '+escape(sheet['dimension'])+'. Scroll the table sideways for further columns. General-format numbers display at up to 15 significant digits; cell details retain the exact original numeric token and number format. Source colors retain the publisher highlights.</p>'])
        for _r,(address,cell) in sorted(notes.items()):
            parts.append('<aside class="clovis-source-cell-note"><strong>Source note from cell '+address+'</strong><p>'+escape(_cell_text(cell))+'</p></aside>')
        parts.append('<div class="clovis-source-table" tabindex="0" role="region" aria-label="'+escape(sheet['name'],quote=True)+'"><table><thead><tr><th>Cell</th>')
        parts.extend('<th scope="col">'+_column(c)+'</th>' for c in range(1,max_column+1))
        parts.append('</tr></thead><tbody>')
        merged,covered = {},set()
        for span in sheet['merged']:
            first,last = span.split(':') if ':' in span else (span,span)
            r1,c1 = _coordinate(first); r2,c2 = _coordinate(last)
            merged[(r1,c1)] = (r2-r1+1,c2-c1+1)
            covered.update((r,c) for r in range(r1,r2+1) for c in range(c1,c2+1) if (r,c)!=(r1,c1))
        for r in range(1,max_row+1):
            if r in notes: continue
            parts.append('<tr><th scope="row">'+str(r)+'</th>')
            for c in range(1,max_column+1):
                if (r,c) in covered: continue
                address = _column(c)+str(r)
                cell = sheet['cells'].get(address,['n',None,0])
                style = workbook['styles'][cell[2]]
                css = []
                for attr,key in (('background-color','fill'),('color','color')):
                    color = style[key].get('rgb','')
                    if re.fullmatch(r'[A-Fa-f0-9]{8}',color): css.append(attr+':#'+color[-6:])
                if style['bold']: css.append('font-weight:700')
                if style['italic']: css.append('font-style:italic')
                title = address+' · Source value: '+_cell_text(cell)+' · Format: '+style['number_format']
                if len(cell)>3: title+=' · Source formula (not recalculated): '+cell[3]['text']
                rowspan,colspan = merged.get((r,c),(1,1))
                parts.append('<td rowspan="'+str(rowspan)+'" colspan="'+str(colspan)+'" title="'+escape(title,quote=True)+'" style="'+(';'.join(css))+'">'+escape(_display(cell,style))+'</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
    return ''.join(parts)


def render_html(row):
    esc = escape
    base = '/reference/publication/'+row['id']
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>'+esc(row['title'])+' · Clovis source</title><link rel="stylesheet" href="/assets/offline_reference.css"></head>',
        '<body class="clovis-local-reference"><main><p class="eyebrow">Clovis · Published evidence offline</p>',
        '<h1>'+esc(row['title'])+'</h1><p>'+esc(row['citation'])+'</p>',
        '<p class="scope">'+esc(row['scope'])+'</p><p>'+esc(row['content_note'])+'</p>',
        '<p><a href="'+base+'/original">Download unchanged original '+('XLSX' if 'workbook' in row else 'XML')+'</a> · <a href="'+base+'/text">Download readable source text</a></p>',
        '<p><a href="/reference/publication/'+EDITION+'/bundle">Download complete study for offline reading</a></p>']
    if 'workbook' in row:
        parts.append('<p>'+esc(row['caption'])+'</p><p><a href="/reference/publication/'+EDITION+'">Read the full paper and methods</a></p>')
        parts.append(_workbook_html(row['workbook']))
    else:
        parts.append('<nav aria-label="Source contents"><ul>')
        parts.extend('<li><a href="#'+esc(block.get('source_id') or 'section-'+str(i),quote=True)+'">'+esc(block['text'])+'</a></li>'
            for i,block in enumerate(row['blocks']) if block['type']=='heading')
        parts.append('</ul><p>Supporting tables</p><ul>')
        parts.extend('<li><a href="/reference/publication/'+item['id']+'">'+esc(item['label']+' · '+item['caption'])+'</a></li>'
            for item in row['supplements'] if item['included'])
        parts.append('</ul></nav><article aria-label="Original publication text">')
        for i,block in enumerate(row['blocks']):
            identifier = esc(block.get('source_id') or 'section-'+str(i),quote=True)
            if block['type']=='heading':
                level = str(block['level'])
                parts.append('<h'+level+' id="'+identifier+'">'+esc(block['text'])+'</h'+level+'>')
            elif block['type']=='table':
                parts.append('<h3 id="'+identifier+'">'+esc(block['label']+'. '+block['caption'])+'</h3><div class="clovis-source-table" tabindex="0"><table>')
                for cells in block['rows']:
                    parts.append('<tr>')
                    for cell in cells:
                        tag = 'th' if cell['header'] else 'td'
                        parts.append('<'+tag+' rowspan="'+str(cell['rowspan'])+'" colspan="'+str(cell['colspan'])+'">'+esc(cell['text'])+'</'+tag+'>')
                    parts.append('</tr>')
                parts.append('</table></div><p>'+esc(block['footnotes'])+'</p>')
            else: parts.append('<p id="'+identifier+'">'+esc(block['text'])+'</p>')
        parts.append('</article>')
    parts.extend(['<footer><h2>Source edition and rights</h2><p>'+esc(row['rights']['original_text'])+'</p>',
        '<p>Retrieved '+esc(row['receipt']['retrieved_utc'])+'</p><p>Original file SHA-256: <code>'+row['receipt']['sha256']+'</code></p>',
        '<p>Original source ID: '+esc(row['native_id'])+'</p>',
        '<p>Return to your Clovis tab to save this complete source component to a fieldbook or project. The paper and each supporting table have separate Atlas records.</p></footer></main></body></html>'])
    return ''.join(parts)


def bundle_bytes():
    """One portable study, with relative readers and unchanged native originals."""
    rows = _records()
    output = BytesIO()
    routes = {row['id']:('index.html' if row['id']==EDITION else row['id']+'.html') for row in rows}
    with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('source.css',(DIRECTORY.parents[2]/'assets/offline_reference.css').read_bytes())
        archive.writestr('source-edition.json',json.dumps(_edition(),ensure_ascii=False,separators=(',',':')))
        for row in rows:
            raw,name = original_bytes(row['id'])
            archive.writestr('originals/'+name,raw)
            archive.writestr(row['id']+'.txt',reading_text(row))
            document = render_html(row).replace('/assets/offline_reference.css','source.css')
            document = document.replace('/reference/publication/'+EDITION+'/bundle','index.html')
            for identifier,target in routes.items():
                document = document.replace('/reference/publication/'+identifier+'/original','originals/'+next(item['file'] for item in rows if item['id']==identifier))
                document = document.replace('/reference/publication/'+identifier+'/text',identifier+'.txt')
            # Replace longer table IDs first, so the parent prefix does not consume them.
            for identifier,target in sorted(routes.items(),key=lambda item:len(item[0]),reverse=True):
                document = document.replace('/reference/publication/'+identifier,target)
            archive.writestr(routes[row['id']],document)
    return output.getvalue()


def register_routes(server):
    from flask import Response
    headers = {'Content-Security-Policy':"default-src 'none'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",'X-Content-Type-Options':'nosniff'}

    @server.get('/reference/publication/<identifier>')
    @server.get('/reference/publication/<identifier>/<operation>')
    def publication_source(identifier,operation=None):
        row = get_record(identifier)
        if row is None or operation not in (None,'text','original','bundle') or operation=='bundle' and identifier!=EDITION:
            return Response('This offline source is unavailable.',status=404,mimetype='text/plain')
        if operation=='bundle':
            try: raw=bundle_bytes()
            except (OSError,ValueError): return Response('The complete reviewed study is unavailable.',status=404,mimetype='text/plain')
            return Response(raw,mimetype='application/zip',headers={**headers,'Content-Disposition':'attachment; filename="clovis-panama-isotope-study.zip"'})
        if operation=='original':
            try: raw,name=original_bytes(identifier)
            except (OSError,ValueError): return Response('The reviewed original is unavailable.',status=404,mimetype='text/plain')
            mime = 'application/xml' if name.endswith('.xml') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return Response(raw,mimetype=mime,headers={**headers,'Content-Disposition':'attachment; filename="pone.0335678.'+name+'"'})
        if operation=='text':
            return Response(reading_text(row),mimetype='text/plain',headers={**headers,'Content-Disposition':'attachment; filename="'+identifier+'.txt"'})
        return Response(render_html(row),mimetype='text/html',headers=headers)
