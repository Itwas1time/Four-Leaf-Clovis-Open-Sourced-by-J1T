"""Project bounded original XLSX cells without altering publisher bytes."""
from io import BytesIO
import re
from zipfile import ZipFile
from defusedxml import ElementTree as ET

S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def project_workbook(raw):
    """Read OOXML without editing, evaluating formulas, or converting numeric tokens."""
    with ZipFile(BytesIO(raw)) as archive:
        if len(archive.infolist())>2048 or any(item.file_size>4_000_000 for item in archive.infolist()) or sum(item.file_size for item in archive.infolist())>10_000_000:
            raise ValueError('Review the changed workbook expansion size.')
        root = ET.fromstring(archive.read('xl/workbook.xml'))
        relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {item.get('Id'):item.get('Target') for item in relations}
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall(S+'si'):
                strings.append(''.join(node.text or '' for node in item.iter(S+'t')))
        style_root = ET.fromstring(archive.read('xl/styles.xml'))
        formats = {item.get('numFmtId'):item.get('formatCode') for item in style_root.findall(S+'numFmts/'+S+'numFmt')}
        # Built-in formats used by these source workbooks; custom formats stay literal.
        formats = {'0':'General','1':'0','2':'0.00','9':'0%','10':'0.00%', **formats}
        fills = [item.find(S+'patternFill') for item in style_root.findall(S+'fills/'+S+'fill')]
        fonts = style_root.findall(S+'fonts/'+S+'font')
        styles = []
        for item in style_root.findall(S+'cellXfs/'+S+'xf'):
            fill, font = fills[int(item.get('fillId','0'))], fonts[int(item.get('fontId','0'))]
            color = fill.find(S+'fgColor') if fill is not None else None
            font_color = font.find(S+'color')
            styles.append({'number_format':formats.get(item.get('numFmtId','0'),'builtin:'+item.get('numFmtId','0')),
                'fill':dict(color.attrib) if color is not None else {},
                'color':dict(font_color.attrib) if font_color is not None else {},
                'bold':font.find(S+'b') is not None,'italic':font.find(S+'i') is not None})
        sheets = []
        for sheet in root.findall(S+'sheets/'+S+'sheet'):
            target = targets[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            path = target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if not re.fullmatch(r'xl/worksheets/sheet[0-9]+\.xml',path):
                raise ValueError('Review the changed workbook sheet target.')
            data = ET.fromstring(archive.read(path))
            cells = {}
            for cell in data.iter(S+'c'):
                address, kind = cell.get('r'), cell.get('t','n')
                if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,4}',address or ''):
                    raise ValueError('Review the changed cell address.')
                value = cell.find(S+'v')
                literal = value.text if value is not None else None
                if kind=='s' and literal is not None:
                    literal = strings[int(literal)]
                elif kind=='inlineStr':
                    literal = ''.join(item.text or '' for item in cell.iter(S+'t'))
                entry = [kind,literal,int(cell.get('s','0'))]
                formula = cell.find(S+'f')
                if formula is not None:
                    entry.append({'text':formula.text or '', 'attributes':dict(formula.attrib)})
                cells[address] = entry
            sheets.append({'name':sheet.get('name'),'state':sheet.get('state','visible'),
                'dimension':data.find(S+'dimension').get('ref'),'cells':cells,
                'merged':[item.get('ref') for item in data.findall(S+'mergeCells/'+S+'mergeCell')],
                'hidden_rows':[item.get('r') for item in data.findall(S+'sheetData/'+S+'row') if item.get('hidden')=='1'],
                'hidden_columns':[dict(item.attrib) for item in data.findall(S+'cols/'+S+'col') if item.get('hidden')=='1']})
        return {'sheets':sheets,'styles':styles,
            'projection_note':'Cell addresses, source numeric tokens, strings, cached formula values, formulas, number formats and source highlights are retained. Formulas are not recalculated. Download the unchanged XLSX for its full native layout and metadata.'}
