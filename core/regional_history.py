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


# 11 Nov 2026: eight more regions from captured NPS editions (quotes re-checked at display time).
def _region(reference, periods, covers, intro, park, area, rest):
    return {
        'reference': reference, 'periods': periods, 'covers': covers, 'intro': intro, 'source_label': park,
        'link_label': 'Read the full page offline',
        'lead_in': 'The National Park Service describes these periods and peoples:',
        'card_note': f'NPS page about {area} only. Its dates are approximate; it does not describe {rest}, '
                     'which Clovis has not yet covered.',
        'report_note': f'It describes {area} only, with approximate dates; Clovis has not yet reviewed a source '
                       f'for {rest}.',
    }


CHESAPEAKE = 'nps-chesapeake-deep-history'
_chesapeake_periods = [
    ('Paleoindian (15,000 to 10,000 years ago)', CHESAPEAKE,
     ('Small groups of hunter-fisher-gatherers traveled frequently in search of the game they hunted and sites where they could mine stone.',)),
    ('Archaic (10,000 to 3,200 years ago)', CHESAPEAKE,
     ('People were not yet farmers, but rather skilled hunters, fishers, and foragers.',
      'Warmer weather meant more food, and therefore the ability to support a larger population.')),
    ('Woodland (3,200 to 400 years ago)', CHESAPEAKE,
     ('The Woodland Period is marked by the adoption of agriculture in the Chesapeake.',
      'By 3,200 years ago, fired clay pottery also appears in the archeological record.',
      'Complex political systems arose by the end of the Woodland Period, for example, the tributary system of the Powhatan peoples.')),
]
MOCCASIN = 'nps-moccasin-bend'
RUSSELL, RUSSELL_PALEO = 'nps-russell-cave-prehistoric-cultures', 'nps-russell-cave-paleo-indian'
NEW_ENGLAND = 'nps-new-england-archeological-periods'
OLYMPIC = 'nps-olympic-peoples'
CANYONLANDS = 'nps-canyonlands-native-americans'
BUFFALO = 'nps-buffalo-river-people'

NEW_REGIONS = {
    'MD': _region(CHESAPEAKE, _chesapeake_periods, 'Chesapeake Bay region (tidewater Maryland) only',
                  'Human habitation of the Chesapeake Bay region dates to before the Bay itself was fully formed.',
                  'Captain John Smith Chesapeake National Historic Trail', 'the Chesapeake Bay region',
                  'western Maryland'),
    'VA': _region(CHESAPEAKE, _chesapeake_periods, 'Chesapeake Bay region (tidewater Virginia) only',
                  'Human habitation of the Chesapeake Bay region dates to before the Bay itself was fully formed.',
                  'Captain John Smith Chesapeake National Historic Trail', 'the Chesapeake Bay region',
                  "Virginia's Piedmont, Blue Ridge and southwest"),
    'TN': _region(MOCCASIN, [
        ('Paleo-Indian (10,000–8000 B.C.)', MOCCASIN,
         ('The Paleo-Indian Period (10,000 B.C.- 8000 B.C.) witnessed the first human inhabitants on Moccasin Bend.',)),
        ('Archaic (8000–700 B.C.)', MOCCASIN,
         ('The Archaic Period (8000 B.C.-700 B.C.) saw the development of stone tools.',)),
        ('Woodland (700 B.C.–A.D. 1000)', MOCCASIN,
         ('The Woodland Period (700 B.C.-1000 A.D.) is possibly the best represented on Moccasin Bend.',
          'This period is notable for the introduction of ceramic pottery and the beginnings of agriculture.')),
        ('Mississippian (A.D. 900–1650)', MOCCASIN,
         ('The Mississippian Period (900 A.D. -1650A.D.) marked the time when the native people began building large mound complexes, farming larger tracts of land and having a strong socio-political structure based on kinship ties.',)),
        ('Cherokee removal (1838–39)', MOCCASIN,
         ('In 1838-39, Cherokees in the area were rounded up and placed in various deportation camps to await removal to Oklahoma.',)),
    ], 'Moccasin Bend, Chattanooga (southeast Tennessee) only',
        'Moccasin Bend is one of the most unique units found in the entire National Park Service system, spanning 12,000 years of continuous human habitation.',
        'Chickamauga and Chattanooga National Military Park', 'Moccasin Bend at Chattanooga',
        'the rest of Tennessee'),
    'AL': _region(RUSSELL, [
        ('Paleo-Indian (about 12,000 years ago)', RUSSELL_PALEO,
         ('Roughly 12,000 years ago, Russell Cave was inhabited by people whom we now call the Paleo-Indians.',)),
        ('Archaic (7000 to 500 B.C.)', RUSSELL,
         ('In the Archaic era the basic foundation for American Indian culture was laid, persisting in some areas until European contact.',)),
        ('Woodland (500 B.C. to A.D. 1000)', RUSSELL,
         ('In Woodland times in the Southeast, settled village life grew more important as agriculture and trade with people to the north allowed more time for refinement of political and ceremonial life.',)),
        ('Mississippian (A.D. 1000 to 1600)', RUSSELL,
         ('The Woodland period civilizations that took root in the Mississippi and Tennessee River Valleys flowered in the Mississippian period.',
          'Large towns and ceremonial complexes with huge temple mounds were made possible by the refinement of corn agriculture.')),
    ], 'Russell Cave (northeast Alabama) only',
        'Roughly 12,000 years ago, Russell Cave was inhabited by people whom we now call the Paleo-Indians.',
        'Russell Cave National Monument', 'Russell Cave and the Tennessee River valley of northeast Alabama',
        'the rest of Alabama'),
    'MA': _region(NEW_ENGLAND, [
        ('Paleo Indian (about 12,000 to 9,000 years ago)', NEW_ENGLAND,
         ('About 12,000 to 9,000 years before present (BP) is the earliest period for which we have archeological evidence of occupation of New England, which archeologists call the Paleo Indian period.',)),
        ('Archaic (about 9,000 to 2,500 years ago)', NEW_ENGLAND,
         ('From about 9,000 to 2,500 years BP was what archeologists refer to as the Archaic period.',)),
        ('Woodland (2,500 years ago to the 1400s)', NEW_ENGLAND,
         ('The Woodland period in New England began about 2,500 years BP and ended during the 15th century.',
          'Archeologists characterize the Woodland period by the production and use of ceramics, the cultivation of maize, as well as the use of bow and arrow hunting technology.')),
        ('Pawtucket, and Native history today', NEW_ENGLAND,
         ('The Native Americans that occupied the Saugus Iron Works National Historic Site area before the arrival of colonizers are the Pawtucket.',
          'Native American history does not end with the arrival of the European colonizers in the 17th-century, and it continues today.')),
    ], 'New England framework, written for Saugus (north of Boston)',
        'About 12,000 to 9,000 years before present (BP) is the earliest period for which we have archeological evidence of occupation of New England, which archeologists call the Paleo Indian period.',
        'Saugus Iron Works National Historic Site', 'New England as seen from Saugus, north of Boston',
        'other Massachusetts homelands such as the Wampanoag and Nipmuc'),
    'WA': _region(OLYMPIC, [
        ('More than 13,000 years ago', OLYMPIC,
         ('Over 13,000 years ago, vast continental glaciers were in retreat leaving behind rounded hills and marshy meadows.',
          'It is the earliest evidence of human presence in this region and proof that residents at the time were hunters.')),
        ('10,000 to 3,000 years ago', OLYMPIC,
         ('From 3,000 to 10,000 years ago they hunted deer and elk and gathered plants to survive.',)),
        ('Maritime cultures (from about 3,000 years ago)', OLYMPIC,
         ('By about 3,000 years ago, as the human population increased, early inhabitants shifted their focus to lowland rivers and lakes.',
          'Fishing, hunting sea mammals and gathering shellfish formed the foundation of rich and complex maritime cultures for which the Pacific Northwest is known.')),
        ('Area tribes today', OLYMPIC,
         ("Eight tribes have traditional associations to lands now in Olympic National Park: Hoh, Jamestown S'Klallam, Lower Elwha Klallam, Makah, Port Gamble S'Klallam, Quileute, Quinault and Skokomish.",)),
    ], 'Olympic Peninsula (northwest Washington) only',
        'Over 13,000 years ago, vast continental glaciers were in retreat leaving behind rounded hills and marshy meadows.',
        'Olympic National Park', 'the Olympic Peninsula',
        'Puget Sound, the Cascades or eastern Washington'),
    'UT': _region(CANYONLANDS, [
        ('Hunting and gathering (8,000 to 500 BCE)', CANYONLANDS,
         ('From about 8,000 BCE to 500 BCE, extended family groups roamed nomadically throughout the southwest.',)),
        ('Early farmers: Fremont-era and ancestral Puebloan', CANYONLANDS,
         ('Roughly two thousand years ago, some hunter-gatherers acquired domesticated plants through trade networks.',
          'Archeologists call two groups of these early farmers the Fremont-era people, located around central Utah, and the ancestral Puebloans, located primarily farther south.')),
        ('Migration (around 1300 CE)', CANYONLANDS,
         ('Around 1300 CE, many ancestral Puebloans migrated south into what is now Arizona and New Mexico.',)),
        ('Ute and Paiute', CANYONLANDS,
         ('Local Ute and Paiute cultures, in part, developed from Fremont-era and ancestral Puebloan societies, as well as through immigration from the north.',)),
    ], 'Canyonlands (southeast Utah) only',
        'Canyonlands has been home to people for over 10,000 years.',
        'Canyonlands National Park', 'Canyonlands in southeast Utah',
        'the Wasatch Front, the Great Basin or southwest Utah'),
    'AR': _region(BUFFALO, [
        ('Paleoindian (10,000 to 8,000 BC)', BUFFALO,
         ('The Paleoindian Period is considered the earliest confirmed period of human occupation in the Ozarks.',)),
        ('Archaic (7,000 to 500 BC)', BUFFALO,
         ('The Archaic period is defined by increasing diversity in tool types and a change in subsistence practices.',)),
        ('Woodland (500 BC to AD 900)', BUFFALO,
         ('The Woodland Period is defined by the presence of the first pottery, but otherwise is largely a continuation of trends already seen during the Archaic.',)),
        ('Mississippian (AD 900 to 1541)', BUFFALO,
         ('The Mississippian Period had limited impact on the Ozarks region.',)),
    ], 'Ozarks (northern Arkansas) only',
        'The Paleoindian Period is considered the earliest confirmed period of human occupation in the Ozarks.',
        'Buffalo National River', 'the Ozark region as seen from the Buffalo River',
        'the Arkansas Delta, Little Rock or the Ouachitas'),
}
REGIONS.update(NEW_REGIONS)


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
    """True when every sentence is still, word for word, in a paragraph or list item of the checked edition."""
    paragraphs = [text for block in (article['blocks'] if article else ())
                  for text in ([block['text']] if block['type'] == 'paragraph' else
                               block.get('items', []) if block['type'] == 'list' else [])]
    return all(any(sentence in text for text in paragraphs) for sentence in sentences)
