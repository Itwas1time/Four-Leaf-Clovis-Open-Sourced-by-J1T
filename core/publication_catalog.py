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
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

OFFLINE_PUBLICATIONS = Path(__file__).resolve().parents[1]/'atlas/gui/data/offline-publications'
PAGE_SIZE = 24
METADATA = ('doi','authors','publisher','published','citation','scope','rights','content_note')

# Reviewed offline studies. To add one: build its folder with its acquisition tool, review the
# edition, then add an entry here (its pinned edition hash is the review gate) together with
# its public export allowlist entry in tools/build_public_release.py and a test.
#   tag_rows: rows carry an 'edition' field (the first study predates it and stays untagged)
#   article_description: None uses the edition's content note
#   figures: reviewed figure image files bundled with the study
#   prepared_study_sha256: a reviewed prebuilt study ZIP served instead of building one
STUDIES = {
    'panama-0335678': {
        'name':'Panama','doi':'10.1371/journal.pone.0335678',
        'sha256':'66c3971aa0dee23e8b115d2cca5336d97f833e35a97503497ae8302641c97a3d',
        'article_subtitle':'Panama · Cerro Juan Díaz · Full text and methods offline',
        'table_subtitle':'Panama · Cerro Juan Díaz · Original table offline',
        'article_description':'Complete paper text and two main tables, with ten separately readable supporting workbooks.',
        'separator':' · ','tag_rows':False,
        'notes':[
            'One publication and its ten supporting tables. These are source components, not eleven excavations.',
            'Earlier published measurements remain identified in the source captions and yellow workbook highlights. Overlapping rows are not new individuals or specimens.',
            'Source numbers, units, blanks, native categories, formulas and cached formula values are retained. Clovis does not recalculate the publisher workbooks.',
            'S7 Table describes modern river-water samples. Its coordinates do not locate archaeological finds.',
        ]},
    'cambodia-0216895': {
        'name':'Cambodia','doi':'10.1371/journal.pone.0216895',
        'sha256':'1e3979cf72ecd5496519bc8bcc30df92c61107cc188236ce8cf933e2379001bc',
        'article_subtitle':'Cambodia - Longvek and Thai reference samples - full text offline',
        'table_subtitle':'Cambodia - Longvek and Thai reference samples - original table offline',
        'article_description':None,'separator':' - ','tag_rows':True,
        'figures':('g004.png','g005.png','g006.png','g007.png'),
        'notes':[
            'One publication and four supporting source workbooks; these are not five excavations.',
            'The study includes 102 sherd samples, including Thai reference material. Workbook rows and analyses overlap and are not additional finds.',
            'Measurements, units, native sample identifiers and uncertainty remain as published; Clovis does not recalculate the workbooks.',
            'Locations describe the published study and reference groups; they do not locate a private property or newly observed object.',
        ]},
    'senegal-0329824': {
        'name':'Senegal','doi':'10.1371/journal.pone.0329824',
        'sha256':'c3f09b47b116f7eafa8b9fbe676d908cfa14162123441491b32b25b8e4b711ee',
        'prepared_study_sha256':'85ea362b1fc5fd4ca4dcd19ef15df8c3296870c6bb26e725432b8f9aea0ef473',
        'article_subtitle':'Senegal - Ravin Blanc X - full text offline',
        'table_subtitle':'Senegal - Ravin Blanc X - original lithic inventory offline',
        'article_description':None,'separator':' - ','tag_rows':True,
        'notes':[
            'One published study and its lithic inventory; source components are not new excavations.',
            'Inventory rows include fragments and refits and should not be counted as newly recorded finds.',
            'The original spreadsheet retains its source identifiers, categories, measurements and remarks.',
            'The published site location does not locate a private property or a newly observed object.',
        ]},
    'kakapel-0328805': {
        'name':'Kakapel','doi':'10.1371/journal.pone.0328805',
        'sha256':'ae51ac3c23084b62663229f8de21d412425cf9320ab3d0e31f3907b9546330dd',
        'article_subtitle':'Kenya - Kakapel Rockshelter - full text offline',
        'table_subtitle':'Kenya - Kakapel Rockshelter - original shell-bead table offline',
        'article_description':None,'separator':' - ','tag_rows':True,
        'notes':[
            'One published study, its shell-bead workbook and its excavation-context descriptions; these are source components, not separate excavations.',
            'The paper summarizes assemblages by phase and context. Radiocarbon, phase and assemblage tables overlap and are not independent finds or events.',
            'Bead rows, measurements, context numbers and radiocarbon rows keep the publisher identifiers and units; Clovis does not recalculate them.',
            'Published coordinates locate the surveyed rock shelters, not a private property or a newly observed object. Missing records do not show an absence of archaeology.',
        ]},
}
EDITION, CAMBODIA, SENEGAL, KAKAPEL = STUDIES
# Folder per study; tests replace an entry to simulate a missing edition.
DIRECTORIES = {identifier: OFFLINE_PUBLICATIONS/identifier for identifier in STUDIES}
DIRECTORY, CAMBODIA_DIRECTORY, SENEGAL_DIRECTORY, KAKAPEL_DIRECTORY = DIRECTORIES.values()
NOTES = STUDIES[EDITION]['notes']


def _directory(identifier):
    return DIRECTORIES[identifier]


@lru_cache(maxsize=len(STUDIES))
def _edition(identifier=EDITION):
    study = STUDIES.get(identifier)
    if study is None:
        raise ValueError('The publication edition is unavailable.')
    raw=(_directory(identifier)/'edition.json').read_bytes().replace(b'\r\n',b'\n')
    if len(raw)>4_000_000 or hashlib.sha256(raw).hexdigest()!=study['sha256']:
        raise ValueError('The bundled publication differs from its reviewed edition.')
    result=json.loads(raw)
    if result.get('schema')!=1 or result.get('id')!=identifier or result.get('doi')!=study['doi']:
        raise ValueError('The bundled publication needs review.')
    return result


def notes_for(row):
    return list(STUDIES.get(row.get('edition'), STUDIES[EDITION])['notes'])


def _normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c))


def _study_records(identifier):
    study, edition = STUDIES[identifier], _edition(identifier)
    metadata = {key:edition[key] for key in METADATA}
    tag = {'edition':identifier} if study['tag_rows'] else {}
    inventory = [{key:value for key,value in item.items() if key!='workbook'} for item in edition['supplements']]
    article = {**metadata,**tag,'id':identifier,'native_id':edition['doi'],'title':edition['title'],
        'category':'Research publication','subtitle':study['article_subtitle'],
        'description':study['article_description'] or edition['content_note'],
        'file':edition['manuscript']['file'],'receipt':edition['manuscript']['receipt'],
        'blocks':edition['blocks'],'supplements':inventory}
    if study.get('figures'):
        article['figures'] = edition['figures']
    tables = [{**metadata,**item,**tag,'category':'Supporting source table',
        'title':item['label']+study['separator']+item['caption'].split('. ',1)[0].rstrip('.'),
        'subtitle':study['table_subtitle'],'description':item['caption'],'parent':identifier}
        for item in edition['supplements'] if item['included']]
    return (article,*tables)


@lru_cache(maxsize=1)
def _records():
    rows=[]
    for identifier in STUDIES:
        try:
            rows.extend(_study_records(identifier))
        except (OSError,ValueError,KeyError,TypeError):
            continue
    return tuple(rows)


def get_record(identifier):
    if not isinstance(identifier,str): return None
    try:
        return next((deepcopy(row) for row in _records() if row['id']==identifier),None)
    except (OSError,ValueError,KeyError,TypeError):
        return None


def get_summary(identifier):
    """Return catalogue facts without copying the publication or workbook body."""
    if not isinstance(identifier,str): return None
    row=next((row for row in _records() if row['id']==identifier),None)
    return deepcopy({key:value for key,value in row.items() if key not in ('workbook','blocks')}) if row else None


def search(query='',page=1,*,summary=False):
    if not isinstance(query,str) or len(query)>120 or type(page) is not int or page<1:
        raise ValueError('Use a publication search of up to 120 characters and a positive page.')
    words = _normalize(query).split()
    exact = _normalize(query.strip()).removeprefix('https://doi.org/').removeprefix('doi:')
    direct = [row for row in _records() if exact in (_normalize(row['id']),_normalize(row['native_id']))]
    rows = direct or [row for row,haystack in _search_rows() if all(word in haystack for word in words)]
    available={row['id'] for row in _records()}
    missing=[study['name']+' edition unavailable. Restore the application files and restart.'
             for identifier,study in STUDIES.items() if identifier not in available]
    selected=rows[(page-1)*PAGE_SIZE:page*PAGE_SIZE]
    if summary:
        selected=[{key:value for key,value in row.items() if key not in ('workbook','blocks')} for row in selected]
    return {'total':len(rows),'page':page,'rows':deepcopy(selected),'missing_editions':missing}


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
    from core.fieldbook import validate_book,MAX_ENTRY_BYTES
    from core.resident_context import _md
    row = get_record(identifier)
    if row is None: raise ValueError('Choose an available publication or original source table.')
    literal = lambda value:'\n'.join(_md(line) for line in value.split('\n'))
    raw,name=_original_bytes_for(row)
    # Large originals cannot fit alongside their cell projection. Avoid first
    # constructing and escaping a huge projection that will be discarded.
    compact_workbook = 'workbook' in row and (len(raw)*4//3) > MAX_ENTRY_BYTES-10_000
    snapshot=deepcopy({k:v for k,v in row.items() if not (compact_workbook and k=='workbook')})
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
    markdown = '' if compact_workbook else '# Published research source\n\n'+literal(reading_text(row))
    if not compact_workbook:
        markdown += '\n\n## Complete source snapshot JSON\n\n'+literal(json.dumps(snapshot,ensure_ascii=False,separators=(',',':')))
    if compact_workbook or (len(markdown.encode('utf-8')) > MAX_ENTRY_BYTES and 'workbook' in snapshot):
        # Keep the original workbook once. Its complete cell projection is
        # rebuilt from the bounded, checksummed XLSX when the saved note opens.
        snapshot.pop('workbook',None)
        markdown = ('# Published research source\n\n'+literal(row['title'])+'\n\n'+literal(row['citation'])
            +'\n\n'+literal(row['scope'])+'\n\n## Complete native workbook snapshot JSON\n\n'
            +literal(json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))))
    entry = {'id':hashlib.sha256(('publication:'+identifier+markdown).encode()).hexdigest()[:24],
        'kind':'investigation','title':row['title'].encode()[:120].decode('utf-8','ignore'),
        'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'summary':{'mission':'Published research source','source':row['citation'],
            'date':row['published'],'outcome':row['category']+'; original source evidence, not a new field observation'},
        'markdown':markdown}
    from core.fieldbook import validate_citation_entry
    validate_citation_entry(entry)
    return entry


def saved_reading(entry):
    """Keep machine provenance in backups while presenting the complete reading."""
    if entry.get('summary',{}).get('mission')!='Published research source': return None
    from core.fieldbook import readable_text
    text=readable_text(entry['markdown'])
    reading,separator,snapshot=text.partition('\n\nComplete native workbook snapshot JSON\n\n')
    if separator:
        try:
            from core.workbook_reader import project_workbook
            from defusedxml.common import DefusedXmlException
            from xml.etree.ElementTree import ParseError
            row=json.loads(snapshot)
            original=row.pop('native_original')
            if original.get('encoding')!='base64' or type(original.get('bytes')) is not int or original['bytes']>5_000_000:
                raise ValueError('Invalid workbook original.')
            raw=base64.b64decode(original['data'],validate=True)
            if len(raw)!=original['bytes'] or hashlib.sha256(raw).hexdigest()!=original['sha256']:
                raise ValueError('Saved workbook checksum differs.')
            row['workbook']=project_workbook(raw)
            return reading_text(row)+'\n\nThe complete native workbook is retained in the workspace backup and note download.'
        except (ValueError,KeyError,TypeError,OSError,IndexError,OverflowError,BadZipFile,DefusedXmlException,ParseError):
            return 'The saved workbook could not be verified. Restore a complete workspace backup.'
    reading,separator,snapshot=text.partition('\n\nComplete source snapshot JSON\n\n')
    if not separator: return text
    _source,followed,note=snapshot.partition('\n\nYour follow-up note\n\n')
    return (reading.rstrip()+'\n\nThe complete native source and provenance are retained in the fieldbook backup and Download note text.'
        + ('\n\nYour follow-up note\n\n'+note if followed else ''))


def original_bytes(identifier):
    row = get_record(identifier)
    if row is None: raise ValueError('This source original is unavailable.')
    return _original_bytes_for(row)


def _original_bytes_for(row):
    name = row['file']
    if name not in ('manuscript.xml',*('s%03d.xlsx'%i for i in range(1,17))):
        raise ValueError('This source file is outside the reviewed edition.')
    directory=_directory(row.get('edition',EDITION))
    raw = (directory/name).read_bytes()
    if len(raw)!=row['receipt']['bytes'] or hashlib.sha256(raw).hexdigest()!=row['receipt']['sha256']:
        raise ValueError('This source original differs from its reviewed edition.')
    return raw,name


def figure_bytes(identifier, figure_id):
    reviewed=STUDIES.get(identifier,{}).get('figures',()) if isinstance(identifier,str) else ()
    if not reviewed or not isinstance(figure_id,str):
        raise ValueError('The reviewed figure is unavailable.')
    figure=next((item for item in _edition(identifier).get('figures',[]) if item['id']==figure_id),None)
    if not figure or figure['file'] not in reviewed:
        raise ValueError('The reviewed figure is unavailable.')
    raw=(_directory(identifier)/figure['file']).read_bytes()
    if len(raw)!=figure['bytes'] or hashlib.sha256(raw).hexdigest()!=figure['sha256']:
        raise ValueError('The reviewed figure differs from its publisher file.')
    return raw,figure['file']


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


def _workbook_html(workbook, start_row=1, end_row=None):
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
        end = min(max_row, end_row if end_row is not None else max_row)
        for _r,(address,cell) in sorted(notes.items()):
            if not start_row <= _r <= end: continue
            parts.append('<aside class="clovis-source-cell-note"><strong>Source note from cell '+address+'</strong><p>'+escape(_cell_text(cell))+'</p></aside>')
        parts.append('<div class="clovis-source-table" tabindex="0" role="region" aria-label="'+escape(sheet['name'],quote=True)+'"><table><thead><tr><th>Cell</th>')
        parts.extend('<th scope="col">'+_column(c)+'</th>' for c in range(1,max_column+1))
        parts.append('</tr></thead><tbody>')
        merged,covered = {},set()
        for span in sheet['merged']:
            first,last = span.split(':') if ':' in span else (span,span)
            r1,c1 = _coordinate(first); r2,c2 = _coordinate(last)
            if r2 < start_row or r1 > end: continue
            first_visible,last_visible=max(r1,start_row),min(r2,end)
            merged[(first_visible,c1)] = (last_visible-first_visible+1,c2-c1+1,first)
            covered.update((r,c) for r in range(first_visible,last_visible+1) for c in range(c1,c2+1) if (r,c)!=(first_visible,c1))
        for r in range(start_row,end+1):
            if r in notes: continue
            parts.append('<tr><th scope="row">'+str(r)+'</th>')
            for c in range(1,max_column+1):
                if (r,c) in covered: continue
                address = _column(c)+str(r)
                rowspan,colspan,original_address = merged.get((r,c),(1,1,address))
                cell = sheet['cells'].get(original_address,['n',None,0])
                style = workbook['styles'][cell[2]]
                css = []
                for attr,key in (('background-color','fill'),('color','color')):
                    color = style[key].get('rgb','')
                    if re.fullmatch(r'[A-Fa-f0-9]{8}',color): css.append(attr+':#'+color[-6:])
                if style['bold']: css.append('font-weight:700')
                if style['italic']: css.append('font-style:italic')
                title = original_address+' · Source value: '+_cell_text(cell)+' · Format: '+style['number_format']
                if len(cell)>3: title+=' · Source formula (not recalculated): '+cell[3]['text']
                parts.append('<td rowspan="'+str(rowspan)+'" colspan="'+str(colspan)+'" title="'+escape(title,quote=True)+'" style="'+(';'.join(css))+'">'+escape(_display(cell,style))+'</td>')
            parts.append('</tr>')
        parts.append('</tbody></table></div>')
    return ''.join(parts)


def render_html(row):
    esc = escape
    base = '/reference/publication/'+row['id']
    parent = row.get('parent',row['id'])
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>'+esc(row['title'])+' · Clovis source</title><link rel="stylesheet" href="/assets/offline_reference.css"></head>',
        '<body class="clovis-local-reference"><main><p class="eyebrow">Clovis · Published evidence offline</p>',
        '<h1>'+esc(row['title'])+'</h1><p>'+esc(row['citation'])+'</p>',
        '<p class="scope">'+esc(row['scope'])+'</p><p>'+esc(row['content_note'])+'</p>',
        '<p><a href="'+base+'/original">Download unchanged original '+('XLSX' if 'workbook' in row else 'XML')+'</a> · <a href="'+base+'/text">Download readable source text</a></p>',
        '<p><a href="/reference/publication/'+parent+'/bundle">Download complete study for offline reading</a></p>']
    if 'workbook' in row:
        parts.append('<p>'+esc(row['caption'])+'</p><p><a href="/reference/publication/'+parent+'">Read the full paper and methods</a></p>')
        workbook=row['workbook']
        if sum(len(sheet['cells']) for sheet in workbook['sheets']) > 10_000:
            parts.append('<p>This large source has separate sheets to keep reading responsive. Open a sheet to see all its cells.</p><ul>')
            parts.extend('<li><a href="'+base+'/sheet/'+str(index)+'">'+esc(sheet['name'])+'</a></li>' for index,sheet in enumerate(workbook['sheets']))
            parts.append('</ul>')
        else:
            parts.append(_workbook_html(workbook))
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
            else:
                parts.append('<p id="'+identifier+'">'+esc(block['text'])+'</p>')
                if block.get('figure_id'):
                    figure=next((item for item in row.get('figures',[]) if item['id']==block['figure_id']),None)
                    if figure:
                        parts.append('<figure><img style="max-width:100%;height:auto" src="/reference/publication/'+parent+'/figure/'+esc(figure['id'],quote=True)+'" alt="'+esc(block['text'],quote=True)+'"><figcaption>Publisher analytical figure. '+esc(figure['rights'])+'</figcaption></figure>')
        parts.append('</article>')
    parts.extend(['<footer><h2>Source edition and rights</h2><p>'+esc(row['rights']['original_text'])+'</p>',
        '<p>Retrieved '+esc(row['receipt']['retrieved_utc'])+'</p><p>Original file SHA-256: <code>'+row['receipt']['sha256']+'</code></p>',
        '<p>Original source ID: '+esc(row['native_id'])+'</p>',
        '<p>Return to your Clovis tab to save this complete source component to a fieldbook or project. The paper and each supporting table have separate Atlas records.</p></footer></main></body></html>'])
    return ''.join(parts)


ROWS_PER_PAGE = 50
SHEET_PAGE_CELL_THRESHOLD = 50_000


def render_sheet(row, index, page=None):
    if 'workbook' not in row or type(index) is not int or not 0 <= index < len(row['workbook']['sheets']):
        raise ValueError('Choose an available original workbook sheet.')
    sheet=row['workbook']['sheets'][index]
    subset={'sheets':[sheet],'styles':row['workbook']['styles'], 'projection_note':row['workbook']['projection_note']}
    last_row=max(_coordinate(address)[0] for address in sheet['cells'])
    large=len(sheet['cells'])>SHEET_PAGE_CELL_THRESHOLD
    if page is not None and (type(page) is not int or page < 1 or not large or (page-1)*ROWS_PER_PAGE >= last_row):
        raise ValueError('Choose an available row range.')
    if large and page is None:
        body='<p>This large source sheet is divided into row ranges. The first range contains the column headings.</p><ul>'
        body+=''.join('<li><a href="/reference/publication/'+row['id']+'/sheet/'+str(index)+'/rows/'+str(p)+'">Rows '+str((p-1)*ROWS_PER_PAGE+1)+'–'+str(min(p*ROWS_PER_PAGE,last_row))+'</a></li>' for p in range(1,(last_row+ROWS_PER_PAGE-1)//ROWS_PER_PAGE+1))+'</ul>'
    else:
        body=_workbook_html(subset, (page-1)*ROWS_PER_PAGE+1 if page else 1, page*ROWS_PER_PAGE if page else None)
        if page:
            base='/reference/publication/'+row['id']+'/sheet/'+str(index)
            nav='<nav aria-label="Workbook row ranges"><a href="'+base+'">All row ranges</a>'
            if page>1: nav+=' · <a href="'+base+'/rows/'+str(page-1)+'">Previous rows</a>'
            if page*ROWS_PER_PAGE<last_row: nav+=' · <a href="'+base+'/rows/'+str(page+1)+'">Next rows</a>'
            body=nav+'</nav>'+body
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>'+escape(sheet['name'])+' - Clovis source</title><link rel="stylesheet" href="/assets/offline_reference.css"></head>'
        '<body class="clovis-local-reference"><main><p class="eyebrow">Clovis - Published evidence offline</p>'
        '<h1>'+escape(row['title'])+' - '+escape(sheet['name'])+'</h1><p>'+escape(row['citation'])+'</p>'
        '<p><a href="/reference/publication/'+row['id']+'">Return to the original workbook</a></p>'
        +body+'</main></body></html>')


def bundle_bytes(identifier=EDITION, *, prepared=True):
    """One portable study, with relative readers and unchanged native originals."""
    study=STUDIES.get(identifier) if isinstance(identifier,str) else None
    if study and study.get('prepared_study_sha256') and prepared:
        raw=(_directory(identifier)/'study.zip').read_bytes()
        if len(raw)>3_000_000 or hashlib.sha256(raw).hexdigest()!=study['prepared_study_sha256']:
            raise ValueError('The prepared study differs from its reviewed edition.')
        return raw
    rows = tuple(row for row in _records() if row.get('edition',EDITION)==identifier)
    if not rows or study is None: raise ValueError('The publication edition is unavailable.')
    output = BytesIO()
    routes = {row['id']:('index.html' if row['id']==identifier else row['id']+'.html') for row in rows}
    with ZipFile(output,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('source.css',(OFFLINE_PUBLICATIONS.parents[1]/'assets/offline_reference.css').read_bytes())
        archive.writestr('source-edition.json',json.dumps(_edition(identifier),ensure_ascii=False,separators=(',',':')))
        if study.get('figures'):
            for figure in _edition(identifier)['figures']:
                raw,name=figure_bytes(identifier,figure['id'])
                archive.writestr('originals/'+name,raw)
        # Retained originals that are not records of their own (for example a context DOCX).
        for supplement in (item for item in _edition(identifier)['supplements'] if not item['included'] and 'file' in item):
            raw=(_directory(identifier)/supplement['file']).read_bytes()
            if len(raw)!=supplement['receipt']['bytes'] or hashlib.sha256(raw).hexdigest()!=supplement['receipt']['sha256']:
                raise ValueError('The original supporting file differs from its reviewed edition.')
            archive.writestr('originals/'+supplement['file'],raw)
        for row in rows:
            raw,name = original_bytes(row['id'])
            archive.writestr('originals/'+name,raw)
            archive.writestr(row['id']+'.txt',reading_text(row))
            document = render_html(row).replace('/assets/offline_reference.css','source.css')
            document = document.replace('/reference/publication/'+identifier+'/bundle','index.html')
            if study.get('figures'):
                for figure in _edition(identifier)['figures']:
                    document=document.replace('/reference/publication/'+identifier+'/figure/'+figure['id'],'originals/'+figure['file'])
            if 'workbook' in row and sum(len(sheet['cells']) for sheet in row['workbook']['sheets']) > 10_000:
                for index,_sheet in enumerate(row['workbook']['sheets']):
                    sheet_name=row['id']+'-sheet-'+str(index)+'.html'
                    document=document.replace('/reference/publication/'+row['id']+'/sheet/'+str(index),sheet_name)
                    sheet_html=render_sheet(row,index).replace('/assets/offline_reference.css','source.css')
                    if len(_sheet['cells'])>SHEET_PAGE_CELL_THRESHOLD:
                        last=max(_coordinate(address)[0] for address in _sheet['cells'])
                        for page in range(1,(last+ROWS_PER_PAGE-1)//ROWS_PER_PAGE+1):
                            page_name=row['id']+'-sheet-'+str(index)+'-rows-'+str(page)+'.html'
                            sheet_html=sheet_html.replace('/reference/publication/'+row['id']+'/sheet/'+str(index)+'/rows/'+str(page)+'"',page_name+'"')
                            page_html=render_sheet(row,index,page).replace('/assets/offline_reference.css','source.css')
                            for linked in (page-1,page+1):
                                page_html=page_html.replace('/reference/publication/'+row['id']+'/sheet/'+str(index)+'/rows/'+str(linked)+'"',row['id']+'-sheet-'+str(index)+'-rows-'+str(linked)+'.html"')
                            page_html=page_html.replace('/reference/publication/'+row['id']+'/sheet/'+str(index)+'"',sheet_name+'"')
                            page_html=page_html.replace('/reference/publication/'+row['id'],routes[row['id']])
                            archive.writestr(page_name,page_html)
                    sheet_html=sheet_html.replace('/reference/publication/'+row['id'],routes[row['id']])
                    archive.writestr(sheet_name,sheet_html)
            for source_id,target in routes.items():
                document=document.replace('/reference/publication/'+source_id+'/original','originals/'+next(item['file'] for item in rows if item['id']==source_id))
                document=document.replace('/reference/publication/'+source_id+'/text',source_id+'.txt')
            for source_id,target in sorted(routes.items(),key=lambda item:len(item[0]),reverse=True):
                document=document.replace('/reference/publication/'+source_id,target)
            archive.writestr(routes[row['id']],document)
    return output.getvalue()


def register_routes(server):
    from flask import Response
    headers = {'Content-Security-Policy':"default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",'X-Content-Type-Options':'nosniff'}

    @server.get('/reference/publication/<identifier>/figure/<figure_id>')
    def publication_figure(identifier,figure_id):
        try:
            raw,_name=figure_bytes(identifier,figure_id)
            return Response(raw,mimetype='image/png',headers={**headers,'Cache-Control':'public, max-age=3600'})
        except (ValueError,OSError):
            return Response('This reviewed figure is unavailable.',status=404,mimetype='text/plain')

    @server.get('/reference/publication/<identifier>/sheet/<int:index>')
    def publication_sheet(identifier,index):
        row=get_record(identifier)
        if row is None: return Response('This offline source is unavailable.',status=404,mimetype='text/plain')
        try: return Response(render_sheet(row,index),mimetype='text/html',headers=headers)
        except (ValueError,KeyError,TypeError): return Response('This workbook sheet is unavailable.',status=404,mimetype='text/plain')

    @server.get('/reference/publication/<identifier>/sheet/<int:index>/rows/<int:page>')
    def publication_sheet_rows(identifier,index,page):
        row=get_record(identifier)
        if row is None: return Response('This offline source is unavailable.',status=404,mimetype='text/plain')
        try: return Response(render_sheet(row,index,page),mimetype='text/html',headers=headers)
        except (ValueError,KeyError,TypeError): return Response('This workbook row range is unavailable.',status=404,mimetype='text/plain')

    @server.get('/reference/publication/<identifier>')
    @server.get('/reference/publication/<identifier>/<operation>')
    def publication_source(identifier,operation=None):
        row = get_record(identifier)
        if row is None or operation not in (None,'text','original','bundle') or operation=='bundle' and identifier not in STUDIES:
            return Response('This offline source is unavailable.',status=404,mimetype='text/plain')
        if operation=='bundle':
            try: raw=bundle_bytes(identifier)
            except (OSError,ValueError): return Response('The complete reviewed study is unavailable.',status=404,mimetype='text/plain')
            return Response(raw,mimetype='application/zip',headers={**headers,'Content-Disposition':'attachment; filename="clovis-source-study.zip"'})
        if operation=='original':
            try: raw,name=original_bytes(identifier)
            except (OSError,ValueError): return Response('The reviewed original is unavailable.',status=404,mimetype='text/plain')
            mime = 'application/xml' if name.endswith('.xml') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return Response(raw,mimetype=mime,headers={**headers,'Content-Disposition':'attachment; filename="'+identifier+'-'+name+'"'})
        if operation=='text':
            return Response(reading_text(row),mimetype='text/plain',headers={**headers,'Content-Disposition':'attachment; filename="'+identifier+'.txt"'})
        return Response(render_html(row),mimetype='text/html',headers=headers)
