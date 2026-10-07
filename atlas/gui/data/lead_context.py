"""Public site names and institutional entry points for the fieldwork leads.

An affiliation means a named researcher works at that institution; it does not
assert that the institution has approved sponsorship or a new partnership.
No unpublished site coordinates or permit claims belong in this catalogue.
"""

LEAD_CONTEXT = {
    "big_belt": {
        "site_area": "Two publicly described multicomponent campsites in the Big Belt Mountains",
        "site_note": "The program names the research landscape but does not publish the two campsite names or excavation-unit locations.",
        "jurisdiction_key": "us_forest",
        "first_contact": "Dr. Lauri Travis and the Anthropocene Research Center program team; involve the Forest Service land manager before defining a funded work package.",
        "institutions": (
            {"name": "Anthropocene Research Center", "relationship": "Field-school organizer", "source_url": "https://anthroctr.org/program/2027-us-mt-big-belt/"},
            {"name": "Helena–Lewis and Clark National Forest", "relationship": "Land manager and instructor affiliation", "source_url": "https://anthroctr.org/program/2027-us-mt-big-belt/"},
            {"name": "Travis Archaeological Services", "relationship": "Director affiliation", "source_url": "https://anthroctr.org/program/2027-us-mt-big-belt/"},
        ),
    },
    "castelo": {
        "site_area": "Castelo Velho da Serra d’Ossa and Martes, near Redondo",
        "site_note": "Both named sites have prior fieldwork; the project says the 2027 season will expand excavations in previously investigated areas.",
        "jurisdiction_key": "portugal",
        "first_contact": "The Castelo Archaeological Project co-directors, with Rui Mataloto as the local municipal archaeologist.",
        "institutions": (
            {"name": "Castelo Archaeological Project", "relationship": "Project team", "source_url": "https://www.casteloproject.com/team.html"},
            {"name": "Municipality of Redondo", "relationship": "Co-director's employer", "source_url": "https://www.casteloproject.com/team.html"},
            {"name": "UNIARQ, University of Lisbon", "relationship": "Co-director's research affiliation", "source_url": "https://www.casteloproject.com/team.html"},
        ),
    },
    "santa_susana": {
        "site_area": "Santa Susana Roman villa and the surrounding survey area, Alentejo",
        "site_note": "The 2027 plan names the villa and nearby heritage structures; specific new excavation units should be confirmed with the directors.",
        "jurisdiction_key": "portugal",
        "first_contact": "Dr. Emma Ljung and Rui Mataloto, the published project directors.",
        "institutions": (
            {"name": "Santa Susana Archaeological Project", "relationship": "Project team", "source_url": "https://www.santasusanaproject.com/who-we-are.html"},
            {"name": "Princeton University", "relationship": "Director's employer; institutional sponsorship unconfirmed", "source_url": "https://www.santasusanaproject.com/who-we-are.html"},
            {"name": "Municipality of Redondo", "relationship": "Co-director's employer", "source_url": "https://www.santasusanaproject.com/who-we-are.html"},
        ),
    },
    "gallow_hill": {
        "site_area": "Gallow Hill Fort between Doune and Dunblane",
        "site_note": "The fort is publicly named, but its subsurface deposits have not yet been excavated; do not confuse it with the separate Gallow Hill Cairn.",
        "jurisdiction_key": "scotland",
        "first_contact": "Dr. Murray Cook at Rampart Scotland; ask for landowner consent and the fort's designation record.",
        "institutions": (
            {"name": "Rampart Scotland", "relationship": "Project team", "source_url": "https://www.archaeological.org/fieldwork/gallow-hill-fort-dunblane-2027/"},
        ),
    },
    "argilos": {
        "site_area": "Ancient Argilos commercial and residential sectors",
        "site_note": "The city and working sectors are public; the particular 2027 excavation units should be confirmed with the co-directors.",
        "jurisdiction_key": "greece",
        "first_contact": "Project co-directors Zisis Bonias and Jacques Perreault through the Argilos mission's financing page.",
        "institutions": (
            {"name": "Ephorate of Antiquities of Serres", "relationship": "Named Greek project collaborator", "source_url": "https://argilos.net/", "institution_url": "https://www.culture.gov.gr/en/ministry/SitePages/viewyphresia.aspx?iid=1695"},
            {"name": "Université de Montréal", "relationship": "Named Canadian project collaborator", "source_url": "https://argilos.net/", "institution_url": "https://recherche.umontreal.ca/chercheur/is/in13581/"},
            {"name": "Canadian Institute in Greece", "relationship": "Project auspices", "source_url": "https://argilos.net/", "institution_url": "https://www.cig-icg.gr/argilos/"},
        ),
    },
    "blue_creek": {
        "site_area": "Blue Creek regional project sites in northwestern Belize",
        "site_note": "MRP names Blue Creek and other regional sites, but its 2027 page does not identify the exact excavation site or units.",
        "jurisdiction_key": "belize",
        "first_contact": "Maya Research Program's project leadership; request the 2027 site assignment before restricting a contribution.",
        "institutions": (
            {"name": "Maya Research Program", "relationship": "Project organizer and donation recipient", "source_url": "https://mayaresearchprogram.org/"},
            {"name": "University of Texas at Tyler", "relationship": "Published program affiliation", "source_url": "https://mayaresearchprogram.org/"},
        ),
    },
    "aguntum": {
        "site_area": "Forum and city-center area of Roman Aguntum",
        "site_note": "Earlier excavation is documented in the forum area; the 2027 program should confirm its exact trench and research design.",
        "jurisdiction_key": "austria",
        "first_contact": "Dr. Martin Auer, published site director and University of Innsbruck scientist.",
        "institutions": (
            {"name": "University of Innsbruck", "relationship": "Site director's institution", "source_url": "https://anthroctr.org/program/2027-austria-roman-aguntum/"},
            {"name": "Anthropocene Research Center", "relationship": "Field-school organizer", "source_url": "https://anthroctr.org/program/2027-austria-roman-aguntum/"},
        ),
    },
    "batan_grande": {
        "site_area": "Huaca del Pueblo Batán Grande, Lambayeque",
        "site_note": "The 2027 program names this previously excavated settlement; exact units and survey boundaries still need the team's research plan.",
        "jurisdiction_key": "peru",
        "first_contact": "The project directors, including Sicán National Museum researcher Manuel Antonio Roque Soplapuco, through the Anthropocene Research Center.",
        "institutions": (
            {"name": "Anthropocene Research Center", "relationship": "Field-school organizer", "source_url": "https://anthroctr.org/program/2027-peru-batan-grande/"},
            {"name": "Sicán National Museum", "relationship": "Co-director's research institution", "source_url": "https://anthroctr.org/program/2027-peru-batan-grande/"},
            {"name": "Northern Arizona University", "relationship": "Co-director's research affiliation", "source_url": "https://anthroctr.org/program/2027-peru-batan-grande/"},
        ),
    },
    "cova_gran": {
        "site_area": "Cova Gran de Santa Linya rock shelter, Lleida",
        "site_note": "The public page names the rock shelter but repeats an older trench description; confirm the 2027 sector before funding.",
        "jurisdiction_key": "catalonia",
        "first_contact": "Dr. Javier Sánchez Martínez and Prof. Rafael Mora Torcal through the published field-school page.",
        "institutions": (
            {"name": "IPHES, Catalan Institute of Human Paleoecology and Social Evolution", "relationship": "Director's research institution", "source_url": "https://anthroctr.org/program/2027-spain-cova-gran/"},
            {"name": "Universitat Autònoma de Barcelona", "relationship": "Co-director's institution", "source_url": "https://anthroctr.org/program/2027-spain-cova-gran/"},
            {"name": "Anthropocene Research Center", "relationship": "Field-school organizer", "source_url": "https://anthroctr.org/program/2027-spain-cova-gran/"},
        ),
    },
    "shiya_ras": {
        "site_area": "SHI-4 at Shiya and RJ-142 at Ras al Jinz, Sharqiyah",
        "site_note": "Both site identifiers are published by the project; the January and February 2027 work is assigned to different sites.",
        "jurisdiction_key": "oman",
        "first_contact": "Valentina Azzarà and Alexandre De Rorre through the Time of Magan project team; ask for the Omani institutional counterpart.",
        "institutions": (
            {"name": "Time of Magan", "relationship": "Project team and field-school organizer", "source_url": "https://www.archaeological.org/fieldwork/the-shiyah-project/"},
            {"name": "Netherlands eScience Center", "relationship": "Project leader's affiliation; project sponsorship unconfirmed", "source_url": "https://www.archaeological.org/fieldwork/the-shiyah-project/"},
        ),
    },
}
