"""Capture authoritative local Atlas citations as project source documents."""
from urllib.parse import urlsplit

from core import atlas_catalog
from core.dig_records import DigBook


def capture(project,code,identifier,*,book=None):
    book=book or DigBook()
    if not any(row['id']==project for row in book.projects()):
        raise ValueError('Choose a saved local dig project.')
    record=atlas_catalog.get_record(identifier)
    if record is None:
        raise ValueError('Choose a current Atlas source.')
    entry=atlas_catalog.reference_entry(identifier)
    url=record['source_url']
    try:
        parsed=urlsplit(url)
        safe=(len(url)<=2000 and parsed.scheme=='https' and bool(parsed.hostname)
            and not parsed.username and not parsed.password and parsed.port in (None,443)
            and not any(char.isspace() or ord(char)<32 for char in url))
    except (TypeError,ValueError):
        safe=False
    return book.capture_source(project,code,{'atlas_id':identifier,'entry':entry},url if safe else '')
