"""Who lived here before you: reviewed public-domain regional summaries, one entry per state.

Each entry names a bundled, hash-checked reference (core.offline_references) and states the
summary's real scope honestly, so a regional source is never presented as statewide truth.
To add a state: capture the source with tools/acquire_nps_yosemite_reference.py, register it in
offline_references.REFERENCES, then add an entry here with its intro, link label, the area it
really covers and scope notes. Check each intro sentence against the source text itself.
"""
from core import offline_references

REGIONS = {
    'OH': {
        'reference': 'nps-native-american-cultures-timeline',
        'covers': 'Northeast Ohio; southwest noted',
        'intro': 'Indigenous peoples have lived in what is now Ohio for at least 13,000 years.',
        'source_label': 'Cuyahoga Valley National Park',
        'link_label': 'Read the full timeline offline',
        'card_note': 'NPS timeline written for Northeast Ohio. In southwest Ohio the late prehistoric people are known '
                     'as Fort Ancient, as at SunWatch Village in Dayton.',
        'report_note': 'It was written for Northeast Ohio, where the late prehistoric people were the Whittlesey. In '
                       'southwest Ohio they are known as Fort Ancient: SunWatch Village in Dayton preserves the remains '
                       'of a 12th-century Fort Ancient settlement ([Dayton Society of Natural History]'
                       '(https://boonshoft.org/sunwatch/)).',
    },
    'FL': {
        'reference': 'nps-florida-earliest-peoples',
        'covers': 'statewide summary',
        'intro': 'People have lived in what is now Florida for about 12,000 years.',
        'source_label': 'Castillo de San Marcos National Monument',
        'link_label': 'Read the full page offline',
        # The page opens with the first arrivals before its first heading; "Paleo-Indians" is its own term.
        'opening_period': 'Paleo-Indians',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': "NPS park summary. Its dates are approximate, as the page says, and it names only some of "
                     "Florida's peoples.",
        'report_note': 'Its dates are approximate, as the page says, and it names only some of the peoples of Florida.',
    },
    'TX': {
        'reference': 'nps-big-bend-first-inhabitants',
        'covers': 'Big Bend (West Texas) only',
        'intro': 'The earliest inhabitants of the Big Bend region of West Texas lived in the Late Paleo-Indian period '
                 '(ca. 8000–6500 BCE).',
        'source_label': 'Big Bend National Park',
        'link_label': 'Read the full page offline',
        'card_note': 'NPS summary for the Big Bend region of West Texas only. It does not describe the rest of Texas, '
                     'which Clovis has not yet covered.',
        'report_note': 'It describes the Big Bend region of West Texas only; Clovis has not yet reviewed a source for '
                       'the rest of Texas.',
    },
}


def summary(state):
    """(entry, article, [(period heading, its first paragraph)]) for a reviewed state, else None.

    An entry's optional 'opening_period' names the paragraph a page gives before its first heading.
    """
    entry = REGIONS.get(state)
    article = offline_references.get(entry['reference']) if entry else None
    if article is None:
        return None
    periods, heading = [], entry.get('opening_period')
    for block in article['blocks']:
        if block['type'] == 'heading':
            heading = block['text']
        elif heading and block['type'] == 'paragraph':
            periods.append((heading, block['text']))
            heading = None
    return entry, article, periods
