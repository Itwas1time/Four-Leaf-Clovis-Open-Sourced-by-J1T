"""Plain-data summaries for the town screen's visible cards (no interface code).

Each answers a question people bring to a place: who lived here, are there known burial
grounds nearby, and what does the law ask of someone digging. Full detail stays in the report.
"""
import re
import sqlite3

from core import known_cemeteries, offline_references


def who_lived_here(state):
    """Ohio: the NPS timeline periods; elsewhere None until a reviewed regional source exists."""
    if state != 'OH':
        return None
    article = offline_references.get(offline_references.TIMELINE)
    if article is None:
        return None
    periods = [block['text'] for block in article['blocks'] if block['type'] == 'heading']
    return {'title': 'Who lived here before you',
            'text': 'Indigenous peoples have lived in what is now Ohio for at least 13,000 years.',
            'items': periods,
            'note': 'NPS timeline written for Northeast Ohio. In southwest Ohio the late prehistoric people are known '
                    'as Fort Ancient, as at SunWatch Village in Dayton.',
            'href': '/reference/local/' + article['id']}


def burial_grounds(place):
    """Named cemeteries near the public town point, with the limits stated."""
    try:
        rows, total = known_cemeteries.nearby(place['latitude'], place['longitude'])
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):  # never break the town screen
        return None
    if not total:
        return {'title': 'Known cemeteries nearby', 'text': 'GNIS names no cemetery within 8 km of the town point.',
                'items': [], 'note': 'Unmarked, family and Native burials are often unrecorded.'}
    return {'title': f'{total} known cemeteries within 8 km',
            'text': 'Nearest to the town point (not your yard):',
            'items': [f"{row['name']} · {row['distance_km']:.1f} km" for row in rows[:3]],
            'note': 'USGS GNIS, 2021. Unmarked, family and Native burials are often unrecorded.'}


def law_summary(state):
    """Verified digger rules where reviewed; otherwise an honest pointer to the state office."""
    from atlas.gui.data.archaeology_laws import SHPO_DIRECTORY, get_archaeology_laws
    reference = get_archaeology_laws().get(state, {})
    name = reference.get('state_name', state)
    rules = reference.get('digger_rules')
    if rules:
        return {'title': f'The law where you are · {name}',
                'items': [f"{rule['topic']} ({re.match(r'[A-Z]+ [0-9.]+', rule['citation']).group()})" for rule in rules],
                'note': f"Read on the official code {reference['checked_on']}; information, not legal advice.",
                'href': rules[0]['url']}
    return {'title': f'The law where you are · {name}',
            'items': [], 'note': f'Clovis has not yet reviewed {name} law. Your State Historic Preservation Office can tell you what applies.',
            'href': SHPO_DIRECTORY}


def old_topo_maps(place):
    """USGS historical topographic sheets covering the town point (index offline, images online)."""
    from core import historical_topos
    try:
        found = historical_topos.summary(place['latitude'], place['longitude'])
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return None
    if not found['total']:
        return None
    span = f"{found['earliest']}–{found['latest']}" if found['earliest'] else 'undated'
    return {'title': f"{found['total']} old USGS topographic maps · {span}",
            'text': 'Sheets that cover the town point, oldest first:',
            'items': [f"{sheet['date'] or 'Undated'} · {sheet['name']} (1:{sheet['scale']:,})" for sheet in found['oldest']],
            'note': 'USGS Historical Topographic Map Collection (public domain). The list is offline; the map images open online.',
            'href': found['oldest'][0]['pdf_url']}
