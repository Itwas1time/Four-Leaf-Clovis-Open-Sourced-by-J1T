"""Limited, sourced fossil examples for explicitly named map formations.

Authored summaries, checked 2026-10-07. No specimen locations or collection
directions. A formation match supports context, never occurrence or odds.
"""
import re

GUIDES = (
    {
        "name": "Grant Lake",
        "pattern": r"\bgrant lake (?:and fairview )?(?:formations?|limestone)\b",
        "states": {"OH", "KY"},
        "examples": "brachiopod shells, bryozoan colonies, mollusks, crinoids and trilobites",
        "source": "https://ngmdb.usgs.gov/Geolex/UnitRefs/GrantLakeRefs_1858.html",
        "source_name": "USGS Geolex: Grant Lake publications",
    },
    {
        "name": "Green River Formation",
        "pattern": r"\bgreen river (?:formation|fm)\b",
        "states": {"WY", "CO", "UT"},
        "examples": "fish remains, plant impressions, gastropods and ostracods",
        "source": "https://ngmdb.usgs.gov/Geolex/UnitRefs/GreenRiverRefs_8483.html",
        "source_name": "USGS Geolex: Green River publications",
    },
    {
        "name": "Morrison Formation",
        "pattern": r"\bmorrison (?:formation|fm)\b",
        "states": {"CO", "UT", "WY", "MT", "NM", "OK", "SD", "TX"},
        "examples": "dinosaur remains and plant fossils",
        "source": "https://www.nps.gov/subjects/fossils/the-morrison-formation.htm",
        "source_name": "NPS: The Morrison Formation",
    },
    {
        "name": "Hell Creek Formation",
        "pattern": r"\bhell creek (?:formation|fm)\b",
        "states": {"ND", "SD"},
        "examples": "fish, dinosaur, turtle and crocodilian remains in documented beds; fossil occurrence varies between beds",
        "source": "https://www.usgs.gov/publications/vertebrate-biostratigraphy-hell-creek-formation-southwestern-north-dakota-and",
        "source_name": "USGS: Hell Creek vertebrate biostratigraphy",
    },
    {
        "name": "Cedar Valley Group",
        "pattern": r"\bcedar valley (?:group|limestone)\b",
        "states": {"IA"},
        "examples": "brachiopods and colonial corals in documented parts of the group, including the Rapid and Coralville units",
        "source": "https://www.iowadnr.gov/places-go/state-preserves/merrill-s-stainbrook-state-preserve",
        "source_name": "Iowa DNR: Cedar Valley geology and fossils",
    },
    {
        "name": "Ohio Shale",
        "pattern": r"\bohio shale\b",
        "states": {"OH"},
        "examples": "armored fish and early shark remains in documented fossil-bearing beds",
        "source": "https://www.usgs.gov/geology-and-ecology-of-national-parks/geology-cuyahoga-valley-national-park",
        "source_name": "USGS: Cuyahoga Valley geology and paleontology",
    },
    {
        "name": "Lockport Group / Dolomite",
        "pattern": r"\blockport (?:group|dolomite|formation)\b",
        "states": {"NY"},
        "examples": "corals in documented parts of the Lockport dolomite sequence; some beds are described as nonfossiliferous",
        "source": "https://pubs.usgs.gov/publication/pp414G",
        "source_name": "USGS: Corals from the Lockport Dolomite",
        "scope_source": "https://ngmdb.usgs.gov/Geolex/UnitRefs/EramosaRefs_1556.html",
    },
    {
        "name": "Casselman Formation",
        "pattern": r"\bcasselman (?:formation|fm)\b",
        "states": {"PA"},
        "examples": "a published trace-fossil trackway whose maker was not identified; this does not establish a particular animal",
        "source": "https://elibrary.dcnr.pa.gov/PDFProvider.ashx?PromptToSave=True&Size=478170&ViewerMode=1&action=PDFStream&docID=1752368&docName=PaGeoMag_v29no2-3&nativeExt=pdf&revision=0",
        "source_name": "Pennsylvania Geology, Summer/Fall 1998: Casselman tracks",
    },
)


def matching_guides(state, units):
    # Require a mapped formation name and geographic scope. An age or a fossil
    # mention alone cannot assign these find classes. Coverage is deliberately
    # limited to reviewed guides, not presented as a national fossil inventory.
    return [dict(guide) for guide in GUIDES if state in guide["states"]
            and any(re.search(guide["pattern"], unit["name"], re.I) for unit in units)]
