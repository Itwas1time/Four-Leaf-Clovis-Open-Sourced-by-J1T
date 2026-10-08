"""Observation records for guided, in-app investigations."""
from datetime import datetime, timezone
import hashlib

from core.fieldbook import validate_book
from core.resident_context import _md
from core.us_places import get_place

MISSIONS = {
    'rocks': {'title': 'Read the rocks', 'subtitle': 'Compare map evidence with what you can actually see.',
              'steps': ('Read the mapped material', 'Compare visible grains or layers', 'Record the differences'),
              'prompt': 'Describe grains, layers, colour and whether the material was in fill. Which details agree with the selected map, and which do not?'},
    'history': {'title': 'Trace a place through time', 'subtitle': 'Read an old map and record visible clues.',
                'steps': ('Read the map title and date', 'Locate familiar streets or landmarks', 'Record buildings or land-use clues'),
                'prompt': 'Record the map title, date and sheet. Describe a building, street, rail line or watercourse you can see. Keep uncertain matches explicit.'},
    'find': {'title': 'Document an exposed object', 'subtitle': 'Build an observation record before guessing an identity.',
             'steps': ('Describe its material and features', 'Record context and scale', 'Write questions for an expert'),
             'prompt': 'Describe the exposed object, its setting and scale. Use Inspect a find for material-specific comparisons and a browser-local photo.'},
}
OUTCOMES = {'open': 'I cannot tell yet', 'matches': 'Some observed details match', 'differs': 'Observed details differ'}


def investigation_entry(mission, state, geoid, source, date, notes, outcome, steps):
    if not isinstance(mission, str) or mission not in MISSIONS:
        raise ValueError('Choose an investigation.')
    place = get_place(geoid, state)
    if place is None:
        raise ValueError('Choose a public town for these notes.')
    for value, limit in ((source, 1000), (date, 120), (notes, 1500)):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError('Keep source text under 1,000 characters, dates under 120 and observations under 1,500.')
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise ValueError('Use valid text in your investigation.') from None
    if not notes.strip():
        raise ValueError('Write what you observed before saving.')
    if not isinstance(outcome, str) or outcome not in OUTCOMES:
        raise ValueError('Choose a comparison outcome.')
    if not isinstance(steps, list) or len(steps) > 3 or any(type(s) is not int or s not in (0, 1, 2) for s in steps) or len(set(steps)) != len(steps):
        raise ValueError('Choose only the listed investigation steps.')
    guide = MISSIONS[mission]
    place_name = f"{place['name']}, {place['state']}"
    lines = [f"# {guide['title']} — {_md(place_name)}", '',
             f"Source or map: {_md(source.strip()) or 'Not recorded'}", '',
             f"Date or geological interval: {_md(date.strip()) or 'Not recorded'}", '',
             '## Your observations', '', _md(notes.strip()), '',
             f"Comparison: **{OUTCOMES[outcome]}**. This is your recorded assessment, not a verified identification.", '',
             '## Steps you marked complete', '',
             *[f"- {guide['steps'][step]}" for step in sorted(steps)], '',
             'These notes concern a public town and user-recorded observations. They do not verify a property match, an object identity, collection permission or discovery odds.', '']
    text = '\n'.join(lines)
    clip = lambda value: value.encode('utf-8')[:1500].decode('utf-8', 'ignore')
    row = {'id': hashlib.sha256(('investigation' + text).encode()).hexdigest()[:24],
           'kind': 'investigation', 'title': (guide['title'] + ' · ' + place_name).encode('utf-8')[:120].decode('utf-8', 'ignore'),
           'created': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           'summary': {'place': place_name, 'mission': guide['title'], 'source': clip(source.strip()),
                       'date': date.strip(), 'outcome': OUTCOMES[outcome],
                       'steps': f"{len(steps)}/3 reported steps", 'follow_up': clip(notes.strip())}, 'markdown': text}
    validate_book({'version': 1, 'entries': [row]})
    return row
