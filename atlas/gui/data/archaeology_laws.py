"""Official starting points for a U.S. archaeological permission review.

The historical export name and state keys are retained for callers. These
entries are reference pointers, not state-by-state legal determinations.
``permit_required`` is None because no site-specific review has been made.
The former unsourced penalty ranges and private-land collecting assurances
have been removed. Current requirements depend on the place, activity,
ownership, resource, and applicable federal, Tribal, state, and local rules.

Links and the Washington example were checked against primary official
sources on 7 October 2026. No entry establishes access or a project permit.
"""

from __future__ import annotations

from copy import deepcopy

CHECKED_ON = "2026-10-07"
SHPO_DIRECTORY = "https://www.nps.gov/subjects/nationalregister/state-historic-preservation-offices.htm"
TRIBAL_OFFICES = "https://www.nps.gov/orgs/1187/state-and-tribal-historic-preservation-offices.htm"

_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

_FEDERAL_REGULATIONS = [
    {
        "name": "Archaeological Resources Protection Act (ARPA)",
        "description": "NPS overview of resource protection and archaeological permitting on public and Indian lands; confirm the applicable permit with the land manager.",
        "source_url": "https://www.nps.gov/subjects/archeology/archaeological-resources-protection-act.htm",
    },
    {
        "name": "NHPA Section 106",
        "description": "ACHP guidance for federal agencies considering effects of their undertakings on historic properties.",
        "source_url": "https://www.achp.gov/protecting-historic-properties",
    },
    {
        "name": "Native American Graves Protection and Repatriation Act (NAGPRA)",
        "description": "Current NPS regulations and guidance on Native American human remains and cultural items; determine applicability and required consultation with the responsible authority.",
        "source_url": "https://www.nps.gov/subjects/nagpra/index.htm",
    },
]


def _state_reference(name: str) -> dict:
    return {
        "state_name": name,
        "shpo_name": "Locate the current State Historic Preservation Office in the official NPS directory",
        "shpo_url": SHPO_DIRECTORY,
        "state_law": "Obtain current state archaeology, burial, and local preservation rules from the competent authority.",
        "permit_required": None,
        "permit_authority": "Confirm the competent heritage authority, land manager, and relevant Tribal authority for the particular site and activity.",
        "penalties": "Not assessed. Check the applicable current statutes and regulations with the responsible authority.",
        "tribal_nations": [],
        "tribal_nations_note": "No site-specific Tribal jurisdiction or consultation review has been made. An empty list does not mean that no Tribal interests apply.",
        "tribal_offices_url": TRIBAL_OFFICES,
        "federal_land_agencies": [],
        "section_106_notes": "Determine whether a federal undertaking triggers Section 106 review; a directory listing alone does not resolve this.",
        "arrowhead_collecting": "Permission has not been assessed. Owner consent alone does not establish that collecting is lawful; resource protection, burial, and other rules may apply on private land.",
        "metal_detecting": "Permission has not been assessed. Confirm the particular place, activity, resource, and any required consents before using equipment.",
        "reporting_requirements": "Leave possible remains and sensitive finds undisturbed; contact the responsible authority to determine reporting and work-stoppage requirements.",
        "key_regulations": deepcopy(_FEDERAL_REGULATIONS),
        "practical_notes": "Use this contact starting point to request a site-specific review. No land access, collecting right, permit, or partnership has been verified.",
        "verification_status": "official reference pointers; site-specific legal review required",
        "checked_on": CHECKED_ON,
        "source_url": SHPO_DIRECTORY,
    }


_LAWS = {code: _state_reference(name) for code, name in _STATES.items()}
_LAWS["WA"].update({
    "state_law": "RCW 27.53.060 addresses disturbing archaeological resources or sites on private and public lands. Its surface-artifact exception is limited; obtain a site-specific determination.",
    "source_url": "https://app.leg.wa.gov/rcw/default.aspx?cite=27.53.060",
    "additional_url": "https://dahp.wa.gov/archaeology/archaeological-permitting",
})
_LAWS["FEDERAL"] = {
    "description": "Official federal archaeology references; determine applicability with the responsible federal land manager and relevant Tribal authority.",
    "permit_required": None,
    "permit_authority": "Responsible federal land manager; confirm authorization, land access, collections arrangements, and consultation for the proposed work.",
    "penalties": "Not assessed. Consult current applicable statutes and regulations rather than an uncited penalty summary.",
    "metal_detecting": "No permission has been assessed for any particular place or use of equipment.",
    "reporting": "Contact the land manager for current discovery reporting, work-stoppage, and consultation procedures; leave sensitive finds undisturbed.",
    "section_106_process": "Use current ACHP guidance to determine whether and how Section 106 applies to the proposed federal undertaking.",
    "tribal_consultation": "Determine applicable government-to-government consultation and NAGPRA requirements with the responsible agencies and Tribes.",
    "key_laws": [row["name"] for row in _FEDERAL_REGULATIONS],
    "key_regulations": deepcopy(_FEDERAL_REGULATIONS),
    "practical_notes": "No entry supplies a permit or establishes land access or permission to disturb, remove, or collect resources.",
    "verification_status": "official reference pointers; site-specific legal review required",
    "checked_on": CHECKED_ON,
    "source_url": _FEDERAL_REGULATIONS[0]["source_url"],
}


def get_archaeology_laws() -> dict:
    """Return independent reference entries keyed by state code, DC, and FEDERAL.

    The historical function name is retained. Callers must interpret a None
    permit flag as unassessed, never as permission to proceed.
    """
    return deepcopy(_LAWS)
