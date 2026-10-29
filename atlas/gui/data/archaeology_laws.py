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
        "reporting_requirements": "If you find human remains, or dig in a known burial ground, state law asks you to stop and contact law enforcement or the coroner and the State Historic Preservation Office. For other finds, confirm any reporting duty with the responsible authority.",
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
# Rules a person digging in Ohio should know. Each was read verbatim on codes.ohio.gov on the
# checked date; paraphrases keep the statute's scope. Add a state only after the same review.
_LAWS["OH"].update({
    "state_law": "Ohio's archaeological permit law covers land owned, controlled or administered by the state or a political subdivision, and dedicated archaeological preserves (ORC 149.54).",
    "source_url": "https://codes.ohio.gov/ohio-revised-code/section-149.54",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Ohio's archaeological survey and salvage permit (written permission of the director of the Ohio History Connection) is required on land owned, controlled or administered by the state or a political subdivision, and at dedicated archaeological preserves. That permit law does not cover ordinary private land; you still need the landowner's permission, and the rules below still apply.",
         "citation": "ORC 149.54 (effective 29 Sep 2015)", "url": "https://codes.ohio.gov/ohio-revised-code/section-149.54",
         "verify": ["owned, controlled, or administered by the state or any political subdivision", "archaeological preserve"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "No one may, without privilege, purposely deface, damage or otherwise physically mistreat an Indian mound or earthwork, a cemetery, or a site of great historical or archaeological interest. \"Cemetery\" means any place of burial, including sites with American Indian burial objects or remains. A violation is desecration, a second-degree misdemeanor.",
         "citation": "ORC 2927.11 (effective 20 Sep 1999)", "url": "https://codes.ohio.gov/ohio-revised-code/section-2927.11",
         "verify": ["Indian mound or earthwork, cemetery", "means any place of burial", "misdemeanor of the second degree"]},
        {"topic": "If you find human remains",
         "rule": "Anyone who discovers a body must report it immediately to a law enforcement officer, an ambulance service, an emergency squad or the coroner where it was found. Failing to report is a fourth-degree misdemeanor.",
         "citation": "ORC 2921.22(C), (K) (effective 21 Mar 2025)", "url": "https://codes.ohio.gov/ohio-revised-code/section-2921.22",
         "verify": ["discovers the body or acquires the first knowledge of the death", "an emergency squad, or the coroner", "misdemeanor of the fourth degree"]},
        {"topic": "Before you dig: buried utilities",
         "rule": "An excavator must notify the utility protection service (call 811) at least two working days, not counting the day of the call, and no more than 16 calendar days before digging. An owner digging their own property must do so where there is a utility easement, a public right-of-way or utility lines serving the property, which covers most house lots. The call is free.",
         "citation": "ORC 3781.28(A), (F)(2) (effective 9 Jun 2026)", "url": "https://codes.ohio.gov/ohio-revised-code/section-3781.28",
         "verify": ["at least two working days", "not more than sixteen calendar days", "If the owner of the property is the excavator", "where utility facilities are known to serve the property"]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Ohio statutes read verbatim on codes.ohio.gov on 2026-10-29; not legal advice",
})
_LAWS["FL"].update({
    "state_law": "Florida's archaeological permit law covers land owned or controlled by the state, water-authority land and designated state archaeological landmarks (Fla. Stat. 267.13).",
    "source_url": "https://www.flsenate.gov/Laws/Statutes/2026/267.13",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Florida's permit requirement for archaeological investigation or excavation applies to land owned or controlled by the state, land owned by a water authority, and designated state archaeological landmarks or landmark zones. It does not cover ordinary private land; you still need the landowner's permission, and the rules below still apply.",
         "citation": "Fla. Stat. 267.13 (2026 edition)", "url": "https://www.flsenate.gov/Laws/Statutes/2026/267.13",
         "verify": ["land owned or controlled by the state, land owned by a water authority", "except in the course of activities pursued under the authority of a permit"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Willfully and knowingly destroying, defacing or removing a burial mound or earthen or shell monument containing human skeletal remains or burial artifacts, or knowingly disturbing the contents of a grave or tomb, are felonies. People acting under the direction or authority of the Division of Historical Resources are exempt.",
         "citation": "Fla. Stat. 872.02 (2026 edition)", "url": "https://www.flsenate.gov/Laws/Statutes/2026/872.02",
         "verify": ["burial mound, earthen or shell monument containing human skeletal remains or associated burial artifacts", "excavates, exposes, moves, removes, or otherwise disturbs the contents of a grave or tomb", "acting under the direction or authority of the Division of Historical Resources"]},
        {"topic": "If you find human remains",
         "rule": "When an unmarked human burial is found on public or private land outside an authorized archaeological excavation, all activity that may disturb it must stop immediately and the district medical examiner must be notified. Anyone who knows an unmarked burial is being unlawfully disturbed must immediately notify local law enforcement.",
         "citation": "Fla. Stat. 872.05 (2026 edition)", "url": "https://www.flsenate.gov/Laws/Statutes/2026/872.05",
         "verify": ["all activity that may disturb the unmarked human burial shall cease immediately", "found upon or within any public or private land in the state, including submerged lands", "shall immediately notify the local law enforcement agency with jurisdiction in the area", "district medical examiner"]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Excavators must notify the one-call system (call 811) not less than 2 full business days before digging; the notice is valid for 30 calendar days. The duty does not apply to the owner of a single-family home digging entirely on that land and no deeper than 10 inches; other conditions apply, so read the official text. The call is free.",
         "citation": "Fla. Stat. 556.105, 556.108 (2026 edition)", "url": "https://www.flsenate.gov/Laws/Statutes/2026/556.105",
         "verify": ["Not less than 2 full business days before beginning any excavation or demolition", "Information provided by an excavator is valid for 30 calendar days after the date"],
         # The homeowner exemption is in a second section; check its own text too.
         "also_verify": [{"url": "https://www.flsenate.gov/Laws/Statutes/2026/556.108",
                          "verify": ["performed by the owner of a single-family residential property", "made entirely on such land, and only up to a depth of 10 inches"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Florida statutes read verbatim on flsenate.gov on 2026-10-29; not legal advice",
})
_LAWS["TX"].update({
    "state_law": "Texas's Antiquities Code makes sites on state, county, city and political-subdivision land state archeological landmarks (Natural Resources Code ch. 191).",
    "source_url": "https://statutes.capitol.texas.gov/Docs/NR/htm/NR.191.htm",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Sites and artifacts on land belonging to Texas or to a county, city or other political subdivision are state archeological landmarks, and removing, damaging or excavating them needs a contract with or permit from the Texas Historical Commission. A site on private land can be designated a landmark only with the landowner's written consent. You still need the landowner's permission.",
         "citation": "Tex. Nat. Res. Code ch. 191", "url": "https://statutes.capitol.texas.gov/Docs/NR/htm/NR.191.htm", "verify_url": "https://tcss.legis.texas.gov/resources/NR/htm/NR.191.htm",
         "verify": ["belonging to the State of Texas or to any county, city, or political subdivision", "salvaged, or excavated without a contract with or permit from the committee", "No site may be designated on private land without the written consent of the landowner"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Without legal authority, knowingly disinterring, disturbing, damaging or carrying away a human corpse is a state jail felony, and treating the place where a corpse is interred in an offensive manner is also an offense.",
         "citation": "Tex. Penal Code 42.08", "url": "https://statutes.capitol.texas.gov/Docs/PE/htm/PE.42.htm", "verify_url": "https://tcss.legis.texas.gov/resources/PE/htm/PE.42.htm",
         "verify": ["disinters, disturbs, damages, dissects, in whole or in part, carries away", "treats in an offensive manner the space in which a human corpse has been interred", "An offense under this section is a state jail felony"]},
        {"topic": "If you find a forgotten cemetery",
         "rule": "A person who discovers an unknown or abandoned cemetery must file notice with the county clerk of the county where it is located no later than the 10th day after the discovery.",
         "citation": "Tex. Health & Safety Code 711.011", "url": "https://statutes.capitol.texas.gov/Docs/HS/htm/HS.711.htm", "verify_url": "https://tcss.legis.texas.gov/resources/HS/htm/HS.711.htm",
         "verify": ["A person who discovers an unknown or abandoned cemetery shall file notice", "with the county clerk of the county in which the cemetery is located", "not later than the 10th day after the date of the discovery"]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Anyone who intends to excavate (disturb soil 16 inches deep or more) must notify a notification center (call 811) no earlier than the 14th day and no later than 48 hours before digging, not counting Saturdays, Sundays and legal holidays. Excavation by a property owner who operates all the underground facilities at the site is excepted. The call is free.",
         "citation": "Tex. Util. Code ch. 251", "url": "https://statutes.capitol.texas.gov/Docs/UT/htm/UT.251.htm", "verify_url": "https://tcss.legis.texas.gov/resources/UT/htm/UT.251.htm",
         "verify": ["not earlier than the 14th day before the date the excavation is to begin", "later than the 48th hour before the time the excavation is to begin", "operates all underground facilities located at the excavation site", "to remove or otherwise disturb soil to a depth of 16 or more inches", "Saturdays, Sundays, and legal holidays"]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Texas statutes read verbatim on the Texas Legislature's statute text on 2026-10-29; not legal advice",
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
