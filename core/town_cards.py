"""Plain-data summaries for the town screen's visible cards (no interface code).

Each answers a question people bring to a place: who lived here, are there known burial
grounds nearby, and what does the law ask of someone digging. Full detail stays in the report.
"""
import re
import sqlite3

from core import known_cemeteries, offline_references


def who_lived_here(state):
    """The reviewed regional summary's periods; None until a reviewed source exists for the state."""
    from core import regional_history
    found = regional_history.summary(state)
    if found is None:
        return None
    entry, article, periods = found
    return {'title': 'Who lived here before you', 'text': entry['intro'], 'items': [name for name, _ in periods],
            'note': entry['card_note'], 'href': '/reference/local/' + article['id'], 'link': entry['link_label'] + ' →'}


def _point(place, spot):
    """Coordinates and wording: the person's own spot when given, else the public town point."""
    if spot:
        return spot['lat'], spot['lon'], 'your spot'
    return place['latitude'], place['longitude'], 'the town point'


def burial_grounds(place, spot=None):
    """Named cemeteries near the person's spot (or the public town point), with the limits stated."""
    try:
        lat, lon, where = _point(place, spot)
        rows, total = known_cemeteries.nearby(lat, lon)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):  # never break the town screen
        return None
    if not total:
        return {'title': 'Known cemeteries nearby', 'text': f'GNIS names no cemetery within 8 km of {where}.',
                'items': [], 'note': 'Unmarked, family and Native burials are often unrecorded.'}
    return {'title': f'{total} known cemeteries within 8 km',
            'text': 'Nearest to your spot:' if spot else 'Nearest to the town point (not your yard):',
            'items': [f"{row['name']} · {row['distance_km']:.1f} km" for row in rows[:3]],
            'note': 'USGS GNIS, 2021. Unmarked, family and Native burials are often unrecorded.'}


def citation_label(citation):
    """'ORC 2921.22(C), (K) (effective ...)' -> 'ORC 2921.22'; 'Fla. Stat. 556.105, 556.108 (2026 edition)' kept."""
    return re.sub(r'\([A-Za-z0-9]+\)', '', citation.split(' (')[0]).rstrip(', ')


def law_summary(state):
    """Verified digger rules where reviewed; otherwise an honest pointer to the state office."""
    from atlas.gui.data.archaeology_laws import SHPO_DIRECTORY, get_archaeology_laws
    reference = get_archaeology_laws().get(state, {})
    name = reference.get('state_name', state)
    rules = reference.get('digger_rules')
    if rules:
        return {'title': f'The law where you are · {name}',
                'items': [f"{rule['topic']} ({citation_label(rule['citation'])})" for rule in rules],
                'note': f"Read on the official code {reference['checked_on']}; information, not legal advice.",
                'href': rules[0]['url']}
    # Not yet read state by state: what applies everywhere, and where the state's own rules are kept.
    return {'title': f'The law where you are · {name}',
            'items': ["Before you dig: call 811, the free national call-before-you-dig number for your state's one-call center",
                      'Federal and tribal land: digging up archaeological objects needs a federal permit (ARPA)',
                      'Native American graves on federal or tribal land are protected by NAGPRA',
                      f'Private land, burials and reporting finds in {name}: ask the State Historic Preservation Office'],
            'note': f"Clovis has not yet read {name}'s own statutes, so they are not summarized here. Sources: call811.com; "
                    'NPS pages on ARPA and NAGPRA. Information, not legal advice.',
            'href': SHPO_DIRECTORY, 'link': f'Find the {name} office →'}


def old_topo_maps(place, spot=None):
    """USGS historical topographic sheets covering the spot or town point (index offline, images online)."""
    from core import historical_topos
    try:
        lat, lon, where = _point(place, spot)
        found = historical_topos.summary(lat, lon)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return None
    if not found['total']:
        return None
    span = f"{found['earliest']}–{found['latest']}" if found['earliest'] else 'undated'
    return {'title': f"{found['total']} old USGS topographic maps · {span}",
            'text': f'Sheets that cover {where}, oldest first:',
            'items': [f"{sheet['date'] or 'Undated'} · {sheet['name']} (1:{sheet['scale']:,})" for sheet in found['oldest']],
            'note': 'USGS Historical Topographic Map Collection (public domain). The list is offline; the map images open online.',
            'href': found['oldest'][0]['pdf_url']}


def one_page(place, state, spot=None, today=None):
    """A printable one-page summary of the same answers shown on screen (title, plain text)."""
    from datetime import date
    from core import my_spot
    title = f"{place['name']}, {place['state']}: what is known about this place"
    where = (f"Your spot: {my_spot.describe(spot)}" if spot
             else f"Public town point {place['latitude']:.4f}, {place['longitude']:.4f} (not your yard)")
    lines = [f"Printed from Clovis on {(today or date.today()).isoformat()}. {where}.", ""]
    for card in (who_lived_here(state), burial_grounds(place, spot), old_topo_maps(place, spot), law_summary(state)):
        if not card:
            continue
        lines.append(card['title'].upper())
        if card.get('text'):
            lines.append(card['text'])
        lines += [f"  - {item}" for item in card.get('items', [])]
        if card.get('note'):
            lines.append(card['note'])
        if str(card.get('href', '')).startswith('https://'):  # in-app links mean nothing on paper
            lines.append(f"Source: {card['href']}")
        lines.append("")
    lines += ["Clovis explains; it does not identify finds or choose where to dig. Rules are information, not legal",
              "advice: follow the links for the current official text. Missing records never mean nothing is there."]
    return title, "\n".join(lines)


# What turns up in yards, as one-tap starting points into Inspect a find: (label, material, feature).
FIND_KINDS = {
    'homes': (('Bottle or window glass', 'glass', None), ('Nails', 'metal', 'nail'), ('Dish or crock pieces', 'ceramic', 'dish'),
              ('Clay pipe stems', 'ceramic', 'pipe'), ('Marbles', 'ceramic', 'marble'), ('Buttons', 'metal', 'button'),
              ('Brick', 'ceramic', 'brick'), ('Tin cans', 'metal', 'can')),
    'earlier': (('Worked stone: flakes, tools, points', 'rock', 'worked'), ('Pottery pieces', 'ceramic', 'sherd')),
    'fossils': (('A possible fossil', 'fossil', None),),
}


def find_here(place, state):
    """What people commonly find in the ground here, from the place's own dated maps and the state's fossils."""
    from core import historical_topos
    from core.state_fossil_library import state_reading
    from core.town_knowledge import knowledge_for_place
    years = []
    try:
        sanborn = knowledge_for_place(place)['maps']
        if str(sanborn.get('earliest', '')).isdigit():
            years.append((int(sanborn['earliest']), 'Sanborn fire-insurance maps'))
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        pass
    try:
        topo = historical_topos.summary(place['latitude'], place['longitude'])
        if topo.get('earliest'):
            years.append((int(topo['earliest']), 'USGS topographic maps'))
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        pass
    since, source = min(years) if years else (None, None)
    homes = (f"Homes, farms and streets have been mapped here since {since} ({source}). Their everyday "
             "leftovers are what most often turns up in yards and gardens:" if since else
             "Where people have lived and built in the last two centuries, their everyday leftovers are what "
             "most often turns up in yards and gardens:")
    groups = [{'label': 'From homes and farms', 'text': homes, 'kinds': FIND_KINDS['homes']},
              {'label': 'From earlier peoples', 'text': 'Indigenous peoples lived here long before. Stone flakes '
               'from toolmaking are their commonest trace; tools, points and pottery pieces also turn up.',
               'kinds': FIND_KINDS['earlier']}]
    reading = state_reading(state)
    if reading and reading.get('facts'):
        fact = reading['facts'][0]
        groups.append({'label': 'Fossils in ' + reading['name'], 'text': fact['text'],
                       'source': fact['sources'][0] if fact.get('sources') else None, 'kinds': FIND_KINDS['fossils']})
    return {'title': 'What you might find in the ground here', 'groups': groups,
            'note': 'Typical finds, not a forecast for your yard. Tap one to see how to look at it and roughly date it.'}
