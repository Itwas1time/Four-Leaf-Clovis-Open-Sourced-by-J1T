"""One hundred public-town research questions; no example findings are invented."""
from functools import lru_cache
import secrets

from core.us_places import get_place, search_places

# Two distinct public Census towns in every state. These are research starting
# points, not archaeological or fossil locations. Resolve against bundled data.
TOWNS = (
    ('AL', 'Birmingham', 'Mobile'), ('AK', 'Anchorage', 'Fairbanks'),
    ('AZ', 'Tucson', 'Flagstaff'), ('AR', 'Little Rock', 'Hot Springs'),
    ('CA', 'Sacramento', 'Santa Rosa'), ('CO', 'Denver', 'Grand Junction'),
    ('CT', 'Hartford', 'New Haven'), ('DE', 'Wilmington', 'Dover'),
    ('FL', 'St. Augustine', 'Gainesville'), ('GA', 'Savannah', 'Athens'),
    ('HI', 'Urban Honolulu', 'Hilo'), ('ID', 'Boise', 'Idaho Falls'),
    ('IL', 'Chicago', 'Galena'), ('IN', 'Indianapolis', 'Evansville'),
    ('IA', 'Dubuque', 'Iowa City'), ('KS', 'Wichita', 'Lawrence'),
    ('KY', 'Louisville', 'Lexington'), ('LA', 'New Orleans', 'Natchitoches'),
    ('ME', 'Portland', 'Bangor'), ('MD', 'Baltimore', 'Frederick'),
    ('MA', 'Boston', 'Lowell'), ('MI', 'Detroit', 'Ann Arbor'),
    ('MN', 'Minneapolis', 'Duluth'), ('MS', 'Natchez', 'Oxford'),
    ('MO', 'St. Louis', 'Springfield'), ('MT', 'Butte', 'Bozeman'),
    ('NE', 'Omaha', 'Lincoln'), ('NV', 'Reno', 'Carson City'),
    ('NH', 'Portsmouth', 'Concord'), ('NJ', 'Trenton', 'Newark'),
    ('NM', 'Santa Fe', 'Albuquerque'), ('NY', 'Albany', 'Rochester'),
    ('NC', 'Wilmington', 'Asheville'), ('ND', 'Bismarck', 'Fargo'),
    ('OH', 'Cincinnati', 'Dayton'), ('OK', 'Tulsa', 'Norman'),
    ('OR', 'Portland', 'Bend'), ('PA', 'Philadelphia', 'Pittsburgh'),
    ('RI', 'Providence', 'Newport'), ('SC', 'Charleston', 'Columbia'),
    ('SD', 'Rapid City', 'Sioux Falls'), ('TN', 'Nashville', 'Knoxville'),
    ('TX', 'San Antonio', 'Austin'), ('UT', 'Salt Lake City', 'Moab'),
    ('VT', 'Burlington', 'Montpelier'), ('VA', 'Richmond', 'Alexandria'),
    ('WA', 'Seattle', 'Spokane'), ('WV', 'Wheeling', 'Morgantown'),
    ('WI', 'Madison', 'Milwaukee'), ('WY', 'Cheyenne', 'Laramie'),
)

HISTORY_QUESTIONS = (
    ('Changing streets', 'How has {town}\'s street pattern changed?',
     'Open Historical maps and find a dated sheet. Compare one street or landmark with today; record an uncertain match as uncertain.'),
    ('Water & settlement', 'What can an old map reveal about water around {town}?',
     'Open Historical maps. Look for a mapped river, shoreline or watercourse, then note its date, purpose and limits.'),
    ('Buildings & land use', 'What buildings can you actually see on a map of {town}?',
     'Open Historical maps. Record one visible building or land-use label with its sheet and date. A symbol does not establish a surviving object.'),
    ('Routes through time', 'Which older routes are mapped around {town}?',
     'Open Historical maps. Check for roads, railways or paths in a dated record. Keep missing features and uncertain alignments explicit.'),
    ('Reading the source', 'How much of {town} does this historical map really show?',
     'Open Historical maps. Check title, date, extent and legend before choosing a feature to investigate; search relevance alone is insufficient.'),
)
ROCK_QUESTIONS = (
    ('Rock materials', 'What materials do the maps describe around {town}?',
     'Select a Local evidence card. Record its materials and original reference, then compare only with something already exposed.'),
    ('Deep time', 'What geological ages are mapped around {town}?',
     'Select a Local evidence card and inspect its interval. Rock age provides context; it does not date a loose object or prove fossil occurrence.'),
    ('Fossil clues', 'Is there sourced fossil context for {town}\'s mapped rocks?',
     'Check Local evidence for a reviewed formation guide or fossil wording in a map description. Missing guide coverage stays unknown.'),
    ('Ground & fill', 'Could a loose rock differ from the map around {town}?',
     'Read the mapped material, then consider transport or imported fill. Save an observation without assuming where an object originated.'),
    ('Comparing maps', 'Do the rock-map sources around {town} agree?',
     'Compare available Local evidence cards and their original references. Overlapping maps are separate sources, not independent finds.'),
)


@lru_cache(maxsize=1)
def catalog():
    rows = []
    for index, (state, historical_town, rock_town) in enumerate(TOWNS):
        for slot, town, profiles in ((1, historical_town, HISTORY_QUESTIONS), (2, rock_town, ROCK_QUESTIONS)):
            choices = search_places(state, town)
            if not choices:
                raise ValueError(f'Example town is absent from the bundled Census lookup: {state} / {town}')
            choice = next((row for row in choices if row['label'] == f'{town} city, {state}'), choices[0])
            topic, question, prompt = profiles[index % len(profiles)]
            place = get_place(choice['value'], state)
            rows.append({'id': f'example-{state.lower()}-{slot}', 'number': len(rows)+1,
                         'state': state, 'geoid': place['geoid'], 'label': choice['label'],
                         'question': question.format(town=town), 'prompt': prompt, 'topic': topic})
    return tuple(rows)


def get_example(example_id):
    if not isinstance(example_id, str) or len(example_id) > 24:
        return None
    row = next((row for row in catalog() if row['id'] == example_id), None)
    return dict(row) if row else None


def pick_example(previous=None):
    """Uniform random selection, excluding the immediately previous example."""
    previous = previous if isinstance(previous, str) else None
    choices = [row for row in catalog() if row['id'] != previous]
    return dict(secrets.choice(choices))
