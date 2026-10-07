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
)


def matching_guides(state, units):
    # Require a mapped formation name and geographic scope. An age or a fossil
    # mention alone cannot assign these find classes. Coverage is deliberately
    # limited to reviewed guides, not presented as a national fossil inventory.
    return [dict(guide) for guide in GUIDES if state in guide["states"]
            and any(re.search(guide["pattern"], unit["name"], re.I) for unit in units)]
