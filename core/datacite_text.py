"""Text views of public metadata; original values are retained separately."""
import base64
from html import unescape
from html.parser import HTMLParser
import json


class _Description(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, value): self.parts.append(value)
    def handle_starttag(self, tag, attrs): self.parts.append(' ')
    def handle_endtag(self, tag): self.parts.append(' ')


def description_text(value):
    """Return text, never active markup; keep escaped HTML in the native source."""
    if not isinstance(value, str):
        return ''
    parser = _Description()
    parser.feed(unescape(value))
    parser.close()
    return ' '.join(' '.join(parser.parts).split())


def metadata_text(attributes):
    """Search parsed source values and the decoded XML, rather than base64 code."""
    values = dict(attributes)
    xml = values.pop('xml', None)
    text = json.dumps(values, ensure_ascii=False, allow_nan=False)
    if isinstance(xml, str) and xml:
        try:
            text += ' ' + base64.b64decode(xml, validate=True).decode('utf-8')
        except (ValueError, UnicodeError):
            return text + ' ' + xml, 'undecodable_original_xml'
        return text, 'decoded_xml'
    return text, 'xml_not_supplied'
