"""The first screen as plain data, so any interface (desktop now, mobile later) can render it.

Owner direction (29 Oct 2026): three big doors, plus easy access to free-roam on the map.
Each action names a destination the interface understands: 'town', 'inspect', 'library',
'map' or 'notebook'.
"""

DOORS = (
    {'key': 'start-town', 'action': 'town', 'label': 'What is around me',
     'detail': 'Choose a town to see who lived there, old maps, rocks, known burial grounds and what the law asks.'},
    {'key': 'start-found', 'action': 'inspect', 'label': 'I found something',
     'detail': 'Describe it to get dating clues, things to check and what the law asks. Clovis explains; it never names your find.'},
    {'key': 'start-library', 'action': 'library', 'label': 'Research a topic',
     'detail': 'Search studies, museum objects, sites and original tables offline, each with its source.'},
)

SHORTCUTS = (
    {'key': 'start-roam', 'action': 'map', 'label': 'Just curious? Wander the map →'},
    {'key': 'start-notes', 'action': 'notebook', 'label': 'My fieldbook →'},
)
