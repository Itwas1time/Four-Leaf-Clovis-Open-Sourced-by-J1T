"""
Timeline data for the TimeSlider - key periods from 25,000 BP to present.
"""

DEFAULT_TIME_SLIDER_BP = 1000


TIMELINE_ENTRIES = [
    {
        "years_bp": 25000,
        "label": "c. 25,000 BP",
        "sea_level_m": -80,
        "ice_coverage": "Advancing glaciation",
        "cultural_period": "Very early horizon; archaeological expectations are sparse and highly provisional.",
    },
    {
        "years_bp": 20000,
        "label": "c. 20,000 BP",
        "sea_level_m": -120,
        "ice_coverage": "Maximum - Laurentide ice sheet covers northern third of continent",
        "cultural_period": "Glacial maximum horizon; any archaeological interpretation is strongly conditioned by ice and shelf exposure.",
    },
    {
        "years_bp": 16000,
        "label": "c. 16,000 BP",
        "sea_level_m": -100,
        "ice_coverage": "Retreating - ice-free corridor opening",
        "cultural_period": "Late-glacial horizon; coastal and interior pathways remain regionally contested.",
    },
    {
        "years_bp": 13500,
        "label": "c. 13,500 BP",
        "sea_level_m": -70,
        "ice_coverage": "Rapid retreat - Great Lakes forming",
        "cultural_period": "Paleoindian horizon; regional expressions vary and are not reducible to one culture label.",
    },
    {
        "years_bp": 12900,
        "label": "c. 12,900 BP",
        "sea_level_m": -60,
        "ice_coverage": "Brief re-advance - cold snap",
        "cultural_period": "Terminal Paleoindian horizon; climate stress and regional adaptation dominate interpretation.",
    },
    {
        "years_bp": 10000,
        "label": "c. 10,000 BP",
        "sea_level_m": -40,
        "ice_coverage": "Minimal - remnant ice in Canada",
        "cultural_period": "Early Holocene horizon; localized Archaic and post-Paleoindian adaptations vary widely.",
    },
    {
        "years_bp": 5000,
        "label": "c. 5,000 BP",
        "sea_level_m": -5,
        "ice_coverage": "None - modern conditions",
        "cultural_period": "Middle-to-late Holocene horizon; regional Archaic traditions and early monumentality vary across the U.S.",
    },
    {
        "years_bp": 3000,
        "label": "c. 3,000 BP",
        "sea_level_m": -2,
        "ice_coverage": "None",
        "cultural_period": "Later precontact horizon; Woodland and regionally distinct developments vary by landscape.",
    },
    {
        "years_bp": 1000,
        "label": "c. 1,000 BP",
        "sea_level_m": 0,
        "ice_coverage": "None",
        "cultural_period": "Late precontact horizon; local traditions differ sharply across the United States.",
    },
    {
        "years_bp": 500,
        "label": "c. 500 BP",
        "sea_level_m": 0,
        "ice_coverage": "None",
        "cultural_period": "Contact-era horizon; archaeological signals blend Indigenous continuity with early colonial disruption.",
    },
    {
        "years_bp": 0,
        "label": "Present",
        "sea_level_m": 0,
        "ice_coverage": "None",
        "cultural_period": "Present-day reference horizon; archaeological layers combine many older periods with modern context.",
    },
]

# Slider marks: {value: label} - value is years BP
SLIDER_MARKS = {
    entry["years_bp"]: entry["label"]
    for entry in TIMELINE_ENTRIES
}


def format_year_bp(years_bp: int | None) -> str:
    years_bp = 0 if years_bp is None else int(years_bp)
    return "Present" if years_bp == 0 else f"{years_bp:,} BP"


def interpolate_timeline(years_bp: int) -> dict:
    """Interpolate sea level and cultural info for an arbitrary year."""
    entries = TIMELINE_ENTRIES
    if years_bp >= entries[0]["years_bp"]:
        return entries[0]
    if years_bp <= entries[-1]["years_bp"]:
        return entries[-1]

    for i in range(len(entries) - 1):
        older = entries[i]
        newer = entries[i + 1]
        if newer["years_bp"] <= years_bp <= older["years_bp"]:
            span = older["years_bp"] - newer["years_bp"]
            t = (older["years_bp"] - years_bp) / span if span > 0 else 0
            sea_level = older["sea_level_m"] + t * (newer["sea_level_m"] - older["sea_level_m"])
            return {
                "years_bp": years_bp,
                "label": newer["label"],
                "sea_level_m": round(sea_level, 1),
                "ice_coverage": newer["ice_coverage"],
                "cultural_period": newer["cultural_period"],
            }

    return entries[-1]
