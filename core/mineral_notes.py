"""Preserve source-reported mineral properties separately from observations."""
from datetime import datetime, timezone
import hashlib

from core import mineral_property_catalog as catalog
from core.fieldbook import validate_book
from core.resident_context import _md

MAX_PROPERTIES = 100


def value_text(fact):
    unit = fact.get('unit','')
    if unit == '1':
        unit = 'dimensionless'
    return ' '.join(value for value in (fact.get('value',''),unit) if value)


def property_notes(fact):
    notes = [('Source rank',fact.get('rank',''))]
    bounds = fact.get('quantity_bounds',{})
    if bounds:
        notes.append(('Recorded quantity bounds','; '.join(f'{key}: {value}' for key,value in bounds.items())))
    for qualifier in fact.get('qualifier',[]):
        notes.append((qualifier['name'],value_text(qualifier)))
    return [(label,value) for label,value in notes if value]


def reference_entry(identifier):
    record = catalog.get_mineral(identifier)
    if record is None:
        raise ValueError('Choose a mineral record from the current library.')
    lines = ['# Mineral reference — '+_md(record['name']),'',
             'Source-reported properties of this mineral; this does not identify or measure a separate specimen.','',
             '- Classification: '+_md(record['kind']),'- Source record: '+_md(record['source_url']),
             '- Metadata rights: '+_md(record['license']),
             '- Snapshot: '+_md(catalog.catalog_stats()['snapshot_date'])]
    for fact in record['properties'][:MAX_PROPERTIES]:
        lines.extend(['','## '+_md(fact['name']),_md(value_text(fact))])
        for label,value in property_notes(fact):
            lines.append('- '+_md(label)+': '+_md(value))
        lines.append('- Statement: '+_md(fact['statement_id']))
        lines.append('- Source: '+_md(fact['source_url']))
        for source in fact.get('sources',[]):
            lines.append('- '+_md(source['name'])+': '+_md(value_text(source)))
    if len(record['properties']) > MAX_PROPERTIES:
        lines.extend(['',f'Saved the first {MAX_PROPERTIES} of {len(record["properties"])} source statements. Open the source for the complete record.'])
    lines.extend(['','Source values and units are retained without conversion. Missing properties remain unknown. No observation, local occurrence, photograph or selected town is inferred.'])
    markdown = '\n'.join(lines)
    row = {'id':hashlib.sha256(('mineral-reference:'+record['id']+markdown).encode()).hexdigest()[:24],
           'kind':'investigation','title':('Mineral reference · '+record['name']).encode()[:120].decode('utf-8','ignore'),
           'created':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           'summary':{'mission':'Mineral reference','source':record['source_url'],
                      'material':record['name'].encode()[:1500].decode('utf-8','ignore'),
                      'outcome':'Source-reported properties; not a specimen identification'},'markdown':markdown}
    validate_book({'version':1,'entries':[row]})
    return row
