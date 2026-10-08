"""Museum collection routing and readable, source-labeled catalog facts."""
from functools import lru_cache
import re
from core import object_reference_catalog as met
from core import smithsonian_reference_catalog as smithsonian


COLLECTIONS = {'met': 'Met · dated object references', 'si': 'Smithsonian · anthropology'}
MET_GROUPS = {'all': 'All groups', 'glass_containers': 'Glass', 'ceramic_vessels': 'Ceramics',
              'metal_implements_hardware': 'Metal tools & hardware', 'coins_medals_tokens': 'Coins, medals & tokens',
              'buttons': 'Buttons', 'stone_implements': 'Stone implements'}
SI_GROUPS = {'all': 'All source tags', 'stone': 'Stone', 'ceramic': 'Ceramic', 'glass': 'Glass',
             'metal': 'Metal', 'wood': 'Wood', 'shell': 'Shell', 'bone': 'Bone'}


def collection_key(value):
    return value if isinstance(value, str) and value in COLLECTIONS else 'met'


@lru_cache(maxsize=2)
def catalog_stats(collection='met'):
    return (smithsonian if collection_key(collection) == 'si' else met).catalog_stats()


def search_objects(collection='met', query='', category='all', era='historic', page=1):
    if collection_key(collection) == 'si':
        return smithsonian.search_objects(query=query, material=category if category in SI_GROUPS else 'all', page=page)
    dates = {'historic': (None, 1950), 'early': (None, 1799), 'industrial': (1800, 1950), 'all': (None, None)}
    begin, end = dates.get(era, dates['historic'])
    return met.search_objects(query=query, category=category if category in MET_GROUPS else 'all',
                              date_from=begin, date_to=end, page=page)


def get_object(identifier):
    if not isinstance(identifier, str):
        return None
    if re.fullmatch(r'met:[1-9][0-9]{0,9}', identifier):
        return met.get_object(identifier)
    if re.fullmatch(r'si:[A-Za-z0-9_-]{1,120}', identifier):
        return smithsonian.get_object(identifier)
    return None


def facts(record):
    """Preserve catalog wording; don't promote inferred material tags to measurements."""
    definitions = [('Object type', 'object_type'), ('Catalog number', 'catalog_number'),
                   ('Source text tags' if record.get('material_basis') else 'Material', 'material'),
                   ('Recorded date', 'date'), ('Culture', 'culture'), ('Period', 'period'),
                   ('Dynasty', 'dynasty'), ('Reign', 'reign'), ('Classification', 'classification'), ('Dimensions', 'dimensions'),
                   ('Subject', 'topic'), ('Collection', 'institution')]
    rows = []
    for label, key in definitions:
        value = record.get(key, '')
        if key == 'dimensions' and isinstance(value, list):
            value = '; '.join(f"{item.get('label', '')}: {item.get('value', '')}".strip(': ')
                              for item in value if isinstance(item, dict) and item.get('value'))
        if isinstance(value, str) and value and value.casefold() not in {'not given', 'unknown', 'not recorded'}:
            rows.append((label, value))
    return rows
