"""Reference links for future data scraping via the Sync Data feature.

These open-access archaeological databases can supplement embedded baseline data
when internet is available.
"""

SCRAPE_SOURCES = [
    # National databases
    {"name": "National Archeological Database (NADB)", "url": "https://core.tdar.org/collection/31020/national-archeological-database-nadb", "type": "national"},
    {"name": "Digital Index of North American Archaeology (DINAA)", "url": "https://alexandriaarchive.org/dinaa/", "type": "national"},
    {"name": "tDAR - The Digital Archaeological Record", "url": "https://core.tdar.org/", "type": "national"},
    {"name": "National Register of Historic Places", "url": "https://www.nps.gov/subjects/nationalregister/index.htm", "type": "national"},
    {"name": "National Map Downloader (USGS)", "url": "https://apps.nationalmap.gov/downloader/", "type": "national"},

    # Regional databases
    {"name": "Heritage Southwest Database", "url": "https://www.archaeologysouthwest.org/projects/the-heritage-southwest-database/", "type": "regional"},
    {"name": "Crow Canyon Research Reports", "url": "https://www.crowcanyon.org/researchreports/", "type": "regional"},
    {"name": "Canadian Archaeological Radiocarbon Database", "url": "https://www.canadianarchaeology.ca/resources/card", "type": "regional"},
    {"name": "Paleoindian Database of the Americas (PIDBA)", "url": "https://pidba.utk.edu/", "type": "regional"},

    # Open data platforms
    {"name": "Open Context", "url": "https://opencontext.org/", "type": "platform"},
    {"name": "Open Context Archaeology Site Data", "url": "https://opencontext.org/archaeology-site-data/", "type": "platform"},
    {"name": "Open Context - Digital Antiquity", "url": "https://opencontext.org/projects/cdd78c10-e6da-42ef-9829-e792ce55bdd6", "type": "platform"},
    {"name": "Open Archaeo - APIs and Scrapers", "url": "https://open-archaeo.info/tags/api-interfaces-and-web-scrapers/", "type": "tools"},
    {"name": "Open Archaeology Data Journal", "url": "https://openarchaeologydata.metajnl.com/articles", "type": "platform"},

    # Paleoecological / environmental
    {"name": "Neotoma Paleoecology Database", "url": "https://www.neotomadb.org/", "type": "paleo"},
    {"name": "SKOPE - Synthesizing Knowledge of Past Environments", "url": "https://openskope.org/", "type": "paleo"},

    # Synthesis / meta
    {"name": "ArchSynth Resources", "url": "https://www.archsynth.org/resources/data-sources/", "type": "meta"},
    {"name": "GitHub Archaeology Topic", "url": "https://github.com/topics/archaeology", "type": "meta"},
]
