"""Who lived here before you: reviewed public-domain regional summaries, one entry per state.

Each entry names a bundled, hash-checked reference (core.offline_references) and states the
summary's real scope honestly, so a regional source is never presented as statewide truth.
To add a state: capture the source with tools/acquire_nps_yosemite_reference.py, register it in
offline_references.REFERENCES, then add an entry here with its intro, link label, the area it
really covers and scope notes. Check each intro sentence against the source text itself.
A park that publishes one page per period lists them in 'periods': (name, reference, verbatim
sentences); a sentence that is no longer in its checked edition is never shown.
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
                       'southwest Ohio they are known as Fort Ancient: SunWatch Village in Dayton preserves the '
                       'remains '
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
    'GA': {
        'reference': 'nps-ocmulgee-paleo-indian-culture',
        'periods': [
            ('Paleo Indian (15,000–9,600 BCE)', 'nps-ocmulgee-paleo-indian-culture',
             ('Clovis spear points characterize the first subperiod, Early Paleo Indian.',
              'Archaeologists believe that the distribution of these points throughout all the environmental zones in '
              'the southeast represents the initial exploration and colonization of the region.')),
            ('Archaic (9,600–1,000 BCE)', 'nps-ocmulgee-archaic-culture',
             ('The Archaic period was unique from the Paleo Indian period before it by the differences in stone point '
              'types, the appearance of new artifacts, and changes in economic orientation.',
              'At the end of the Late Archaic subperiod fiber-tempered ceramics – both plain and decorated – appeared '
              'along the South-Atlantic coast.')),
            ('Woodland (1,000 BCE–900 CE)', 'nps-ocmulgee-woodland-culture',
             ('The Woodland Indians made several crucial advancements in their society that helped them flourish from '
              '1,000 BCE – 900 CE.', 'One major advancement was creating permanent settlements.')),
            ('Mississippian (from about 900 CE)', 'nps-ocmulgee-mississippian-culture',
             ('Around 900 CE a group of newcomers arrived in central Georgia, pushing out the existing Woodland '
              'culture '
              'and establishing various settlements.',
              'The Mississippians constructed a large ceremonial complex and town on the Macon Plateau near the '
              'Ocmulgee '
              'River at present-day Macon, Georgia.')),
            ('Lamar (about 1300–1650 CE)', 'nps-ocmulgee-lamar-culture',
             ('The Lamar Culture blanketed Georgia and portions of five neighboring states from about 1300 CE until at '
              'least 1650 CE.',)),
            ('The Muscogee (Creek) Nation, forcibly removed 1836–1837', 'nps-ocmulgee-the-muscogee-nation',
             ('When the early English explorers and traders first encountered the native people that are now called '
              'the Muscogee, they were living in the valley of the Ocmulgee River.',
              'During the summer and winter of 1836-early 1837, over 14,000 Muscogee Indians made the three-month '
              'journey to Oklahoma, a trip of over 800 land miles and another 400 by water.')),
        ],
        'covers': 'Central Georgia (Macon Plateau)',
        'intro': 'People have lived on the Macon Plateau in central Georgia since the Paleo Indian period, which '
                 'Ocmulgee Mounds dates from about 15,000 BCE.',
        'source_label': 'Ocmulgee Mounds National Historical Park',
        'link_label': 'Read the Paleo Indian page offline',
        'lead_in': 'The park describes these periods and peoples of the Macon Plateau:',
        'card_note': 'NPS park pages about the Macon Plateau in central Georgia. Coastal, mountain and other regions '
                     'of '
                     'Georgia had their own local histories, which Clovis has not yet reviewed.',
        'report_note': 'They were written about the Macon Plateau in central Georgia. The Lamar culture they describe '
                       'blanketed Georgia, but other parts of the state have their own local histories, which '
                       'Clovis has not yet reviewed.',
    },
    'AZ': {
        'reference': 'nps-tuzigoot-human-history',
        'periods': [
            ('The first people (about 10,000 years ago)', 'nps-tuzigoot-human-history',
             ('The human history of the Verde Valley begins around 10,000 years ago, when the southwest was cooler '
              'and wetter than it is today.',
              'Today we know of their presence from a handful of Clovis points - distinctive stone points that were '
              'probably used with spears - that have been found in and near the valley.')),
            ('The Sinagua (from about 650)', 'nps-tuzigoot-human-history',
             ('Around the year 650, 1400 years ago, people began settling in the Verde Valley.',)),
            ('Verde Valley pueblos (from about 1000)', 'nps-tuzigoot-human-history',
             ('Construction of multi-room pueblos began by the year 1000.',)),
            ('Trade', 'nps-tuzigoot-human-history',
             ('During the excavation of Tuzigoot pueblo, trade items and materials from hundreds of miles away were '
              'found.',)),
            ('Moving on (1300s)', 'nps-tuzigoot-human-history',
             ('For the Hopi, the Verde Valley villages were stops in a much longer migration to the Hopi Mesas, and '
              'were never intended to be permanent settlements.',
              'Ancestors of the Yavapai left the pueblos and farms for a more mobile lifestyle of hunting and '
              'gathering.')),
        ],
        'covers': 'Verde Valley (central Arizona) only',
        'intro': 'The human history of the Verde Valley in central Arizona begins around 10,000 years ago.',
        'source_label': 'Tuzigoot National Monument',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about the Verde Valley of central Arizona only. Its dates are approximate; it does '
                     'not describe the rest of Arizona, which Clovis has not yet covered.',
        'report_note': 'It describes the Verde Valley of central Arizona only, with approximate dates; Clovis has '
                       'not yet reviewed a source for the rest of Arizona.',
    },
    'CA': {
        'reference': 'nps-ohlones-and-coast-miwoks',
        'periods': [
            ('Ohlone and Coast Miwok homelands', 'nps-ohlones-and-coast-miwoks',
             ('Park areas south of the Golden Gate, from the San Francisco Peninsula, to the East Bay and south to '
              'Monterey, are the aboriginal lands of the Ohlones (also called Costanoans).',
              'Park lands north of the Golden Gate, primarily in Marin County and Southern Sonoma County, are the '
              'aboriginal lands of the Coast Miwoks.')),
            ('Tribes and villages', 'nps-ohlones-and-coast-miwoks',
             ('Both the Ohlone and Coast Miwok peoples were organized into small, politically independent societal '
              'groups or tribes; the Ohlones had about 50 tribes and the Coast Miwoks had approximately14 tribes.',)),
            ('Spanish missions (from 1776)', 'nps-ohlones-and-coast-miwoks',
             ('In 1776, when Spanish military and civilian settlers arrived in the Bay Area to establish military '
              'garrisons (presidios), Franciscan missions, and civil settlements (pueblos), life abruptly and '
              'dramatically changed for the native people of the San Francisco Bay Area.',)),
            ('Today', 'nps-ohlones-and-coast-miwoks',
             ('Today, descendants of Ohlone and Coast Miwok peoples live throughout the Bay Area.',)),
        ],
        'covers': 'San Francisco Bay Area only',
        'intro': 'Native Americans have lived in the San Francisco Bay region for over 10,000 years.',
        'source_label': 'Golden Gate National Recreation Area',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about the San Francisco Bay region only. Its dates are approximate; it does not '
                     'describe the rest of California, which Clovis has not yet covered.',
        'report_note': 'It describes the San Francisco Bay region only, with approximate dates; Clovis has not yet '
                       'reviewed a source for the rest of California.',
    },
    'CO': {
        'reference': 'nps-mesa-verde-people',
        'periods': [
            ('Paleoindian hunters (about 12,000 years ago)', 'nps-mesa-verde-people',
             ('Human history at Mesa Verde goes back approximately 12,000 years, to a time when people were hunting '
              'mammoths, ground sloths, and giant bison by spearpoints.',)),
            ('Ancestral Pueblo people (500–1300 CE)', 'nps-mesa-verde-people',
             ('Between 500 CE and 1300 CE, the Four Corners region of modern-day Colorado, New Mexico, Arizona, and '
              'Utah was home to tens of thousands of Ancestral Pueblo people.',)),
            ('Farmers of corn, beans and squash', 'nps-mesa-verde-people',
             ('Between the 500s and the 1200s, people chose to transition from a life where farming, hunting, and '
              'gathering held equal weight, to one where the crops of corn, beans, and squash made up 90% of '
              "people's diet.",)),
            ('Leaving Mesa Verde (late 1200s)', 'nps-mesa-verde-people',
             ('Even with this ebb and flow of population, life in the Mesa Verde area continued until the mid 1200s, '
              'when people started to move south.',
              'Over the course of several decades, the Ancestral Pueblo people left Mesa Verde entirely.')),
            ('Pueblo and Hopi descendants', 'nps-mesa-verde-people',
             ('The Pueblo and Hopi people are the direct descendants of those who built and lived in the communities '
              'at Mesa Verde and surrounding sites.',)),
            ('Ute, Navajo (Diné) and Apache', 'nps-mesa-verde-people',
             ('Ute, Navajo, and Apache also call this place home.',
              'Together, they form the 27 associated Pueblos and Tribes of Mesa Verde.')),
        ],
        'covers': 'Mesa Verde (southwest Colorado) only',
        'intro': 'People have lived at Mesa Verde in southwest Colorado for about 12,000 years.',
        'source_label': 'Mesa Verde National Park',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about Mesa Verde in southwest Colorado only. Its dates are approximate; it does not '
                     'describe the rest of Colorado, which Clovis has not yet covered.',
        'report_note': 'It describes Mesa Verde in southwest Colorado only, with approximate dates; Clovis has not '
                       'yet reviewed a source for the rest of Colorado.',
    },
    'IN': {
        'reference': 'nps-indiana-dunes-indigenous-peoples',
        'periods': [
            ('Paleo-Indian (about 10,500 years ago)', 'nps-indiana-dunes-indigenous-peoples',
             ('The Indiana Dunes area has been inhabited by Indigenous peoples for thousands of years, with '
              'archaeological evidence showing human activity dating back approximately 10,500 years.',
              'This Paleo-Indian period involved small, mobile hunter-gatherer groups who utilized the lakeshore’s '
              'freshwater, plant life, and animal resources.')),
            ('Archaic', 'nps-indiana-dunes-indigenous-peoples',
             ('In the Archaic period (10,000 to 2,000 years ago), communities became more settled, and their tool '
              'use and regional trade networks expanded.',)),
            ('Woodland', 'nps-indiana-dunes-indigenous-peoples',
             ('During the Woodland period (about 2,000 years ago to 500 years ago), Indigenous peoples established '
              'semi-permanent settlements and engaged in early agriculture, cultivating crops such as corn.',)),
            ('Miami and Potawatomi', 'nps-indiana-dunes-indigenous-peoples',
             ('By the late 1600s, the Miami tribe was the principal Indigenous group near southern Lake Michigan, '
              'including the St. Joseph River valley.',
              'Following the Iroquois retreat, the Potawatomi moved into the southern Lake Michigan region, '
              'solidifying control over former Miami territories by the mid-1700s.')),
        ],
        'covers': 'Indiana Dunes (Lake Michigan shore) only',
        'intro': 'Indigenous peoples have lived in the Indiana Dunes area for about 10,500 years.',
        'source_label': 'Indiana Dunes National Park',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about the Indiana Dunes on the southern shore of Lake Michigan only. Its dates are '
                     'approximate; it does not describe the rest of Indiana, which Clovis has not yet covered.',
        'report_note': 'It describes the Indiana Dunes on the southern shore of Lake Michigan only, with approximate '
                       'dates; Clovis has not yet reviewed a source for the rest of Indiana.',
    },
    'KY': {
        'reference': 'nps-mammoth-cave-native-americans',
        'periods': [
            ('First people (by 12,000 years ago)', 'nps-mammoth-cave-native-americans',
             ('The human history of the Mammoth Cave area began by 12,000 years ago with the exploration of Mammoth '
              'Cave itself dating back between 5,000 to 4,000 years ago.',)),
            ('Late Archaic and Early Woodland', 'nps-mammoth-cave-native-americans',
             ('Prehistoric people from the Late Archaic and Early Woodland period once inhabited the forests and '
              'plains of Kentucky, with a focus on the river valleys and their abundant resources.',)),
            ('Cave miners (by 1200 BCE)', 'nps-mammoth-cave-native-americans',
             ('By 1200 BCE (before common era) prehistoric people mined gypsum, mirabilite, epsomite, and other '
              'related minerals from the passageways of Mammoth Cave and other caves found in the region.',
              'Torches made from river cane were used to light their way.')),
            ('Traditionally affiliated nations today', 'nps-mammoth-cave-native-americans',
             ('Park staff continue to consult with members of seven nations that have been shown to be traditionally '
              'affiliated with the park lands: the Eastern Band of Cherokee Indians, Cherokee Nation, United '
              'Keetoowah Band of Cherokee Indians, Shawnee Tribe, Eastern Shawnee Tribe of Oklahoma, Absentee '
              'Shawnee Tribe, and the Chickasaw Nation.',)),
        ],
        'covers': 'Mammoth Cave area (south-central Kentucky) only',
        'intro': 'People have lived in the Mammoth Cave area of Kentucky for at least 12,000 years.',
        'source_label': 'Mammoth Cave National Park',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about the Mammoth Cave area of south-central Kentucky only. Its dates are '
                     'approximate; it does not describe the rest of Kentucky, which Clovis has not yet covered.',
        'report_note': 'It describes the Mammoth Cave area of south-central Kentucky only, with approximate dates; '
                       'Clovis has not yet reviewed a source for the rest of Kentucky.',
    },
    'NM': {
        'reference': 'nps-chaco-history-culture',
        'periods': [
            ('Chacoan flowering (mid 800s)', 'nps-chaco-history-culture',
             ('The cultural flowering of the Chacoan people began in the mid 800s and lasted more than 300 years.',)),
            ('Great houses (800s–1000s)', 'nps-chaco-history-culture',
             ('During the middle and late 800s, the great houses of Pueblo Bonito, Una Vida, and Peñasco Blanco were '
              'constructed, followed by Hungo Pavi, Chetro Ketl, Pueblo Alto, and others.',)),
            ('Center of the San Juan Basin (by 1050)', 'nps-chaco-history-culture',
             ('By 1050, Chaco had become the ceremonial, administrative, and economic center of the San Juan Basin.',)),
            ('Change and migration (1100s–1200s)', 'nps-chaco-history-culture',
             ("In the 1100s and 1200s, change came to Chaco as new construction slowed and Chaco's role as a "
              'regional center shifted.',
              'In time, the people shifted away from Chacoan ways, migrated to new areas, reorganized their world, '
              'and eventually interacted with foreign cultures.')),
            ('Pueblo and Navajo connections', 'nps-chaco-history-culture',
             ('Pueblo descendants say that Chaco was a special gathering place where many peoples and clans '
              'converged to share their ceremonies, traditions, and knowledge.',
              'Chaco is central to the origins of several Navajo clans and ceremonies.')),
        ],
        'covers': 'Chaco Canyon (northwest New Mexico) only',
        'intro': 'A thousand years ago Chaco Canyon in northwest New Mexico was the center of a thriving ancestral '
                 'Puebloan culture.',
        'source_label': 'Chaco Culture National Historical Park',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about Chaco Canyon in northwest New Mexico only. Its dates are approximate; it does '
                     'not describe the rest of New Mexico, which Clovis has not yet covered.',
        'report_note': 'It describes Chaco Canyon in northwest New Mexico only, with approximate dates; Clovis has '
                       'not yet reviewed a source for the rest of New Mexico.',
    },
    'NY': {
        'reference': 'nps-adirondacks-native-americans',
        'periods': [
            ('Paleo-Indian', 'nps-adirondacks-native-americans',
             ('Paleo-Indian (15,000 to 7000 B.C.) sites have been found around the region dating to 9000 B.C.',)),
            ('Archaic', 'nps-adirondacks-native-americans',
             ('The first Archaic (8000 to 1000 B.C.) people in New York came from the St. Lawrence River Valley to '
              'the area around Lake Champlain and into the Hudson River Valley.',)),
            ('Woodland', 'nps-adirondacks-native-americans',
             ('Early Woodlands cultures in the Adirondack region included the Middlesex culture, which was related '
              'to the Adena culture in the Ohio Valley.',
              'This culture was followed by the Point Peninsula culture in the Middle Woodland period.')),
            ('Mohawk, Oneida and Mahican lands', 'nps-adirondacks-native-americans',
             ('Iroquoian peoples arrived between 1,200 and 4,000 years ago, and both the Mohawk and the Oneida '
              'consider the Adirondacks to be part of their territory.',
              'The Algonquian-speaking Mahicans also claimed the mountains as their lands, particularly the area '
              'east of Lake George to southern Lake Champlain.')),
        ],
        'covers': 'Adirondacks (northern New York) only',
        'intro': 'People have lived in and around the Adirondacks of northern New York since the Paleo-Indian period.',
        'source_label': 'National Park Service',
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': 'NPS page about the Adirondack region of northern New York only. Its dates are approximate; it '
                     'does not describe the rest of New York, which Clovis has not yet covered.',
        'report_note': 'It describes the Adirondack region of northern New York only, with approximate dates; Clovis '
                       'has not yet reviewed a source for the rest of New York.',
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
    if 'periods' in entry:
        periods = [(name, ' '.join(sentences)) for name, reference, sentences in entry['periods']
                   if _quoted(offline_references.get(reference), sentences)]
        return (entry, article, periods) if periods else None
    periods, heading = [], entry.get('opening_period')
    for block in article['blocks']:
        if block['type'] == 'heading':
            heading = block['text']
        elif heading and block['type'] == 'paragraph':
            periods.append((heading, block['text']))
            heading = None
    return entry, article, periods


def _quoted(article, sentences):
    """True when every sentence is still, word for word, in a paragraph of the checked edition."""
    paragraphs = [block['text'] for block in article['blocks'] if block['type'] == 'paragraph'] if article else []
    return all(any(sentence in text for text in paragraphs) for sentence in sentences)
