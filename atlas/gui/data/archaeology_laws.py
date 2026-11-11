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
# Reviewed 29 Oct 2026 the same way: drafted from the official pages, every phrase re-checked live by
# tools/check_law_sources.py and each rule read against its section. New Mexico's statutes are PDF-only,
# so its rules cite the administrative code (NMAC) that implements them.
_LAWS["WA"].update({
    "state_law": "Washington's archaeological permit law covers historic and prehistoric archaeological resources and sites on both private and public land, and requires a written permit from the director of the Department of Archaeology and Historic Preservation (RCW 27.53.060).",
    "source_url": "https://app.leg.wa.gov/rcw/default.aspx?cite=27.53.060",
    "additional_url": "https://dahp.wa.gov/archaeology/archaeological-permitting",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Washington's archaeological permit law reaches private land as well as public land. It is unlawful to knowingly remove, alter, dig into or excavate, or to damage, deface or destroy, any historic or prehistoric archaeological resource or site, or to remove any archaeological object from such a site, without a written permit from the director of the Department of Archaeology and Historic Preservation, who must first obtain the property owner's consent. \"Historic archaeological resources\" are properties listed in or eligible for the Washington or national register of historic places. The law does not apply to removing artifacts found exposed on the surface of the ground that are not historic archaeological resources or sites. You still need the landowner's permission, and the rules below still apply.",
         "citation": "RCW 27.53.060, 27.53.030 (as codified; last amended 2002 and 2013)", "url": "https://app.leg.wa.gov/rcw/default.aspx?cite=27.53.060",
         "verify": ["On the private and public lands of this state it shall be unlawful for any person, firm, corporation", "without having obtained a written permit from the director for such activities", "The director must obtain the consent of the private or public property owner", "removal of artifacts found exposed on the surface of the ground which are not historic archaeological resources or sites"],
         "also_verify": [{"url": "https://app.leg.wa.gov/rcw/default.aspx?cite=27.53.030", "verify": ["means those properties which are listed in or eligible for listing in the Washington state register of historic places"]}]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Knowingly removing, mutilating, defacing, injuring or destroying any cairn or grave of any native Indian, or any glyptic or painted record of any tribe or peoples, is a class C felony; knowingly doing the same to a historic grave is also a class C felony. People who disturb native Indian graves through inadvertence, including through construction, mining, logging, agricultural activity or any other activity, must reinter the remains under the supervision of the appropriate Indian tribe (for historic graves, under the supervision of the Department of Archaeology and Historic Preservation). It is a complete defense if the acts were accidental or inadvertent, reasonable efforts were made to preserve the remains, and the discovery or disturbance was properly reported.",
         "citation": "RCW 27.44.040 (1989); RCW 68.60.050 (2009)", "url": "https://app.leg.wa.gov/rcw/default.aspx?cite=27.44.040",
         "verify": ["knowingly removes, mutilates, defaces, injures, or destroys any cairn or grave of any native Indian", "Persons disturbing native Indian graves through inadvertence, including disturbance through construction, mining, logging, agricultural activity", "shall reinter the human remains under the supervision of the appropriate Indian tribe", "complete defense in the prosecution under this section if the defendant can prove by a preponderance of evidence"],
         "also_verify": [{"url": "https://app.leg.wa.gov/rcw/default.aspx?cite=68.60.050", "verify": ["who knowingly removes, mutilates, defaces, injures, or destroys any historic grave shall be guilty of a class C felony", "shall reinter the human remains under the supervision of the department of archaeology and historic preservation"]}]},
        {"topic": "If you find human remains",
         "rule": "Anyone who knows of the existence and location of skeletal human remains must notify the coroner and local law enforcement as quickly as possible, unless they have good reason to believe notice has already been given; failing to do so is a misdemeanor. A person doing ground-disturbing activity who finds skeletal human remains in or on the ground must immediately stop any activity that may cause further disturbance, make a reasonable effort to protect the area, and report the presence and location of the remains to the coroner and local law enforcement. That person is held harmless from criminal and civil liability under this section if the find was an inadvertent discovery, the requirements are met and they are otherwise in compliance with applicable law. If the coroner finds the remains nonforensic, the coroner must notify the Department of Archaeology and Historic Preservation within two business days.",
         "citation": "RCW 68.50.645 (2008)", "url": "https://app.leg.wa.gov/rcw/default.aspx?cite=68.50.645",
         "verify": ["to notify the coroner and local law enforcement in the most expeditious manner possible", "fails to give notice to the coroner and local law enforcement, is guilty of a misdemeanor", "engaged in ground disturbing activity and who encounters or discovers skeletal human remains in or on the ground", "Immediately cease any activity which may cause further disturbance", "the coroner must notify the department of archaeology and historic preservation within two business days"]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Before digging, an excavator must mark the boundary of the dig with white lining or white pin flags and give notice to the one-number locator service (call 811) not less than two full business days and not more than 10 full business days before the scheduled start date, unless the excavator and the facility operators agree otherwise in writing. Operators' markings expire 45 calendar days after the notice; after that, new notice is needed. The notice duty does not apply to an excavation of less than twelve inches in depth on private noncommercial property, if it is performed by the person (or an employee of the person) who owns or occupies the property. Facility operators are prohibited from charging a fee for locating and marking their underground facilities, with the exceptions the statute lists.",
         "citation": "RCW 19.122.030, 19.122.031 (2025 c 292)", "url": "https://app.leg.wa.gov/rcw/default.aspx?cite=19.122.030",
         "verify": ["not less than two full business days and not more than 10 full business days", "markings of underground utilities expire forty-five calendar days from the date that the excavator provided notice", "facility operators are prohibited from charging a fee for locating and marking their underground facilities"],
         "also_verify": [{"url": "https://app.leg.wa.gov/rcw/default.aspx?cite=19.122.031", "verify": ["An excavation of less than twelve inches in depth on private noncommercial property", "performed by the person or an employee of the person who owns or occupies the property"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Washington statutes read verbatim on app.leg.wa.gov on 2026-10-29; not legal advice",
})
_LAWS["NC"].update({
    "state_law": "North Carolina's Archaeological Resources Protection Act requires a permit to excavate or remove archaeological resources on State lands (G.S. 70-13, 70-15), and a separate Article covers unmarked human burials and skeletal remains (G.S. 70-28 to 70-40).",
    "source_url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-15.html",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "North Carolina's Archaeological Resources Protection Act requires a permit from the Department of Natural and Cultural Resources to excavate, remove, damage or otherwise alter or deface any archaeological resource located on State lands. An archaeological resource is material remains of past human life or activities at least 50 years old that are of archaeological interest. \"State lands\" means lands owned, occupied or controlled by the State, with the exception of lands under short-term lease solely for archaeological purposes, and excluding highway rights-of-way. Separately, on lands owned by the State, a public agency or institution, a county or a municipal corporation, excavating, disturbing, removing, destroying or selling any Indian relic or artifact, or the contents of any mound or burial ground, without the written approval of the director of the State Museum or the Secretary of Natural and Cultural Resources is a Class 1 misdemeanor. These permit rules do not cover ordinary private land; you still need the landowner's permission, and the rules below still apply.",
         "citation": "N.C. Gen. Stat. 70-15, 70-12, 70-4", "url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-15.html",
         "verify": ["No person may excavate, remove, damage or otherwise alter or deface any archaeological resource located on State lands", "unless he is acting pursuant to a permit issued under G.S. 70-13"],
         "also_verify": [{"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-12.html", "verify": ["means any material remains of past human life or activities which are at least 50 years old", "means any lands owned, occupied, or controlled by the State of North Carolina", "with the exception of those lands under short term lease solely for archaeological purposes, excluding highway right-of-ways"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-4.html", "verify": ["or any of the contents of any mound or burial ground, on or from any lands owned by the State", "except with the written approval of the director of the State Museum or the Secretary of Natural and Cultural Resources", "shall be guilty of a Class 1 misdemeanor"]}]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Without authorization of law or the consent of the surviving spouse or next of kin of the deceased, it is a Class I felony to knowingly and willfully open, disturb, destroy, remove, vandalize or desecrate any casket or other repository of any human remains, including by plowing under, tearing up, covering over or otherwise obliterating or removing any grave or any portion of it. Knowingly and willfully disturbing, destroying, removing, vandalizing or desecrating human remains that have been interred in a cemetery is a Class H felony. The statute does not apply to a professional archaeologist acting under the unmarked human burials Article (G.S. 70-28 to 70-40), which points to this section for vandalism of unmarked burials. Knowingly acquiring human skeletal remains removed from unmarked burials in North Carolina after 1 October 1981 other than as that Article provides, or knowingly exhibiting or selling them, is a Class H felony.",
         "citation": "N.C. Gen. Stat. 14-149, 70-37, 70-40", "url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_14/GS_14-149.html",
         "verify": ["without authorization of law or the consent of the surviving spouse or next of kin of the deceased", "Open, disturb, destroy, remove, vandalize or desecrate any casket or other repository of any human remains", "by any means including plowing under, tearing up, covering over or otherwise obliterating or removing any grave", "to knowingly and willfully disturb, destroy, remove, vandalize, or desecrate any human remains that have been interred in a cemetery"],
         "also_verify": [{"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-37.html", "verify": ["criminal law concerning vandalism of unmarked human burials or human skeletal remains may be found in G.S. 14-149", "Knowingly exhibit or sell any human skeletal remains acquired from unmarked burials in North Carolina"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-40.html", "verify": ["Violation of the provisions of G.S. 70-37(a) is a Class H felony"]}]},
        {"topic": "If you find human remains",
         "rule": "Anyone who knows or has reasonable grounds to believe that unmarked human burials or human skeletal remains are being disturbed, destroyed, defaced, mutilated, removed or exposed must notify the medical examiner of the county where the remains are encountered immediately; violating this duty is a Class 1 misdemeanor. An unmarked burial is an interment with no grave marker or other historical documentation of the deceased's identity. If remains are encountered during construction or agricultural activities, disturbance must stop immediately and may not resume without authorization from the county medical examiner or the State Archaeologist. If the medical examiner finds the remains are not a medical-examiner case, the State Archaeologist takes charge and has 48 hours to make arrangements with the landowner for protection or removal; after that the State Archaeologist has no authority over the remains and may not prohibit the resumption of construction or agricultural activities without the landowner's permission.",
         "citation": "N.C. Gen. Stat. 70-29, 70-30, 70-28(6), 70-40(a)", "url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-29.html",
         "verify": ["shall notify immediately the medical examiner of the county in which the remains are encountered", "disturbance of the remains shall cease immediately and shall not resume without authorization"],
         "also_verify": [{"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-30.html", "verify": ["shall have 48 hours to make arrangements with the landowner for the protection or removal", "may not prohibit the resumption of the construction or agricultural activities without the permission of the landowner"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-28.html", "verify": ["any interment of human skeletal remains for which there exists no grave marker or any other historical documentation"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_70/GS_70-40.html", "verify": ["Violation of the provisions of G.S. 70-29 is a Class 1 misdemeanor"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Before excavating, the person responsible must give notice to the Notification Center (call 811) no less than three full working days before the proposed start date (10 to 20 full working days for excavation near a subaqueous facility). The notice expires 28 calendar days after the work start date; later digging needs a new notice. The notice requirement does not apply to an excavation by the owner of a single-family residential property on his or her own land that does not encroach on any operator's right-of-way, easement or permitted use, or one that does encroach but is performed with nonmechanized equipment (hand tools and soft dig technologies). Tilling of soil for agricultural or gardening purposes that encroaches on such a right-of-way, easement or permitted use is also exempt if it is less than 12 inches deep. The call is free.",
         "citation": "N.C. Gen. Stat. 87-122(a), 87-124(1)-(3), 87-119, 87-117(15) (last amended S.L. 2025-21)", "url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_87/GS_87-122.html",
         "verify": ["must be given no less than three full working days before the proposed commencement date of the excavation or demolition", "Notice given pursuant to this subsection shall expire 28 calendar days after the work start date"],
         "also_verify": [{"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_87/GS_87-124.html", "verify": ["performed by the owner of a single-family residential property on his or her own land", "or permitted use that is performed with nonmechanized equipment", "tilling of soil for agricultural or gardening purposes that encroaches on any operator", "and is less than 12 inches in depth"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_87/GS_87-119.html", "verify": ["The Notification Center may not impose any charge on any person giving notice to the Notification Center"]}, {"url": "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_87/GS_87-117.html", "verify": ["Nonmechanized equipment. - Hand tools and soft dig technologies"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "North Carolina statutes read verbatim on ncleg.gov on 2026-10-29; not legal advice",
})
_LAWS["VA"].update({
    "state_law": "Virginia's Antiquities Act requires a permit for field investigations that remove, destroy or disturb objects of antiquity on state-controlled land and on designated state archaeological sites and zones (Va. Code 10.1-2302), and a separate permit for archaeological removal of human skeletal remains from unmarked burials regardless of ownership (10.1-2305).",
    "source_url": "https://law.lis.virginia.gov/vacode/10.1-2302/",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Virginia's Antiquities Act makes it unlawful to conduct any field investigation, exploration or recovery operation that removes, destroys or disturbs an object of antiquity on state-controlled land, or on a designated state archaeological site or zone, without a permit from the Director; doing so is a Class 1 misdemeanor. \"State-controlled land\" means land owned by the Commonwealth or under the primary administrative jurisdiction of a state agency, including state parks, state wildlife areas, state recreation areas, highway rights-of-way and state-owned easements. A site or zone on private property can be designated only with the owner's express prior written consent. Intentionally defacing, damaging, destroying, displacing, disturbing or removing an object of antiquity is also unlawful (Class 1 misdemeanor) on designated sites, on state-controlled land, and on land owned by a battlefield preservation organization or on which it holds an easement. Otherwise this permit law does not cover ordinary private land; you still need the landowner's permission, and the rules below still apply.",
         "citation": "Va. Code 10.1-2302, 10.1-2300, 10.1-2304, 10.1-2306 (as displayed on law.lis.virginia.gov, 29 Oct 2026)", "url": "https://law.lis.virginia.gov/vacode/10.1-2302/",
         "verify": ["on state-controlled land, or on a state archaeological site or zone, without first receiving a permit from the Director", "without first obtaining a permit pursuant to subsection A is guilty of a Class 1 misdemeanor"],
         "also_verify": [{"url": "https://law.lis.virginia.gov/vacode/10.1-2300/", "verify": ["means any land owned by the Commonwealth or under the primary administrative jurisdiction of any state agency", "includes state parks, state wildlife areas, state recreation areas, highway rights-of-way, and state-owned easements"]}, {"url": "https://law.lis.virginia.gov/vacode/10.1-2304/", "verify": ["provided that the Director secures the express prior written consent of the owner of the property involved"]}, {"url": "https://law.lis.virginia.gov/vacode/10.1-2306/", "verify": ["intentionally deface, damage, destroy, displace, disturb, or remove any object of antiquity on any designated state archaeological site", "land owned by a battlefield preservation organization or on which such organization holds an easement", "A violation of this section is a Class 1 misdemeanor"]}]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "If a person unlawfully disinters or displaces a dead human body, or any part of one, that has been deposited in any vault, grave or other burial place, it is a Class 4 felony. Separately, it is unlawful to conduct any type of archaeological field investigation that removes human skeletal remains or associated artifacts from any unmarked human burial, regardless of the age of the archaeological site and regardless of ownership, without a permit from the Director of the Department of Historic Resources.",
         "citation": "Va. Code 18.2-126(A); Va. Code 10.1-2305(A) (as displayed on law.lis.virginia.gov, 29 Oct 2026)", "url": "https://law.lis.virginia.gov/vacode/18.2-126/",
         "verify": ["If a person unlawfully disinters or displaces a dead human body", "which has been deposited in any vault, grave or other burial place, he is guilty of a Class 4 felony"],
         "also_verify": [{"url": "https://law.lis.virginia.gov/vacode/10.1-2305/", "verify": ["It is unlawful for any person to conduct any type of archaeological field investigation", "involving the removal of human skeletal remains or associated artifacts from any unmarked human burial", "regardless of age of an archaeological site and regardless of ownership"]}, {"url": "https://law.lis.virginia.gov/vacode/10.1-2200/", "verify": ["means the Director of the Department of Historic Resources"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "No person may make or begin any excavation or demolition without first submitting a locate request to the notification center (call 811). Operators must mark their lines and report to the positive response system by 7:00 a.m. on the third working day after the request, unless a scheduled excavation date is given (between 48 hours and 12 working days out). The notification is valid for 15 working days; the excavator must request re-marking three working days before the end of that period, or whenever the markings become illegible. The Act does not apply to any hand digging performed by an owner or occupant of a property; \"hand digging\" means any excavation involving nonmechanized tools or equipment, including digging with shovels, picks and manual post hole diggers, vacuum excavation or soft digging. It also does not apply to the tilling of soil for agricultural purposes.",
         "citation": "Va. Code 56-265.17, 56-265.15:1, 56-265.15, 56-265.19 (as displayed on law.lis.virginia.gov, 29 Oct 2026)", "url": "https://law.lis.virginia.gov/vacode/56-265.17/",
         "verify": ["No person shall make or begin any excavation or demolition without first submitting a locate request to the notification center", "shall be valid for 15 working days from 7:00 a.m. on the next working day following a locate request", "Three working days before the end of the 15-working-day period"],
         "also_verify": [{"url": "https://law.lis.virginia.gov/vacode/56-265.15:1/", "verify": ["Nothing in this chapter shall apply to: 1. Any hand digging performed by an owner or occupant of a property", "2. The tilling of soil for agricultural purposes"]}, {"url": "https://law.lis.virginia.gov/vacode/56-265.15/", "verify": ["means any excavation involving nonmechanized tools or equipment. Hand digging includes, but is not limited to", "digging with shovels, picks, and manual post hole diggers, vacuum excavation or soft digging"]}, {"url": "https://law.lis.virginia.gov/vacode/56-265.19/", "verify": ["by no later than 7:00 a.m. on the third working day following", "shall not be less than 48 hours nor more than 12 working days from the date of the locate request"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Virginia statutes read verbatim on law.lis.virginia.gov on 2026-10-29; not legal advice",
})
_LAWS["MN"].update({
    "state_law": "Minnesota's Field Archaeology Act reserves field archaeology on state sites to the state archaeologist and licensees (Minn. Stat. 138.33), and its burial law covers all human burials, remains and burial grounds on public or private land (Minn. Stat. 307.08).",
    "source_url": "https://www.revisor.mn.gov/statutes/cite/138.33",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Minnesota's Field Archaeology Act bars anyone other than the state archaeologist and individuals licensed by the director of the Minnesota Historical Society from engaging in field archaeology (studying the traces of human culture by surveying, digging, sampling, excavating or removing objects) on any state site. A \"state site\" is a land or water area owned or leased by, or subject to the paramount right of, the state, a county, a township or a municipality where there are objects or other evidence of archaeological interest; the term includes all aboriginal mounds and earthworks and ancient burial grounds on state land or land subject to the paramount rights of the state. A willful violation is a gross misdemeanor. Ordinary private land is outside that definition; you still need the landowner's permission, and the rules below still apply.",
         "citation": "Minn. Stat. 138.33, 138.31 (subds. 7, 14), 138.41 (2026 statutes)", "url": "https://www.revisor.mn.gov/statutes/cite/138.33",
         "verify": ["shall engage in any field archaeology on any state site", "individuals duly licensed by the director of the Minnesota Historical Society"],
         "also_verify": [{"url": "https://www.revisor.mn.gov/statutes/cite/138.31", "verify": ["owned or leased by or subject to the paramount right of the state, county, township, or municipality", "This term includes all aboriginal mounds and earthworks, ancient burial grounds, prehistoric ruins", "the study of the traces of human culture at any land or water site by means of surveying, digging"]}, {"url": "https://www.revisor.mn.gov/statutes/cite/138.41", "verify": ["or the rules adopted by the commissioner is guilty of a gross misdemeanor"]}]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Minnesota's burial law applies to all human burials, human remains and human burial grounds found on or in all public or private lands or waters in Minnesota, whatever their ethnic origin. A person who intentionally, willfully or knowingly destroys, mutilates or injures human burials, human burial grounds or associated grave goods commits a felony, and so does a person who, without the consent of the appropriate authority, disturbs human burial grounds or removes human remains or associated grave goods. A burial ground is a discrete location known to contain, or with high potential to contain, human remains based on physical evidence, historical records or reliable informant accounts. For non-American Indian burial grounds lacking trustees or not officially defined as abandoned, the appropriate authority is the state archaeologist; for American Indian burial grounds lacking trustees, it is the Indian Affairs Council.",
         "citation": "Minn. Stat. 307.08, subds. 1, 2, 13 (2026 statutes)", "url": "https://www.revisor.mn.gov/statutes/cite/307.08",
         "verify": ["all human burials, human remains, or human burial grounds found on or in all public or private lands or waters", "destroys, mutilates, or injures human burials, human burial grounds, or associated grave goods", "without the consent of the appropriate authority, disturbs human burial grounds or removes human remains or associated grave goods", "the state archaeologist in the case of non-American Indian burial grounds lacking trustees or not officially defined as abandoned"]},
        {"topic": "If you find human remains",
         "rule": "Discovery of bones, body parts and specimens that may be human remains must be promptly reported to the coroner or medical examiner. Unidentified human remains or burials found outside recorded cemeteries, and unplatted graves or burials found within recorded cemeteries, in contexts that indicate antiquity greater than 50 years, must be treated with the utmost respect for all human dignity and dealt with under the burial law: burials that are not American Indian, or whose ethnic identity cannot be ascertained, are dealt with under provisions established by the state archaeologist and other appropriate authority.",
         "citation": "Minn. Stat. 390.11, subd. 8; Minn. Stat. 307.08, subd. 7 (2026 statutes)", "url": "https://www.revisor.mn.gov/statutes/cite/390.11",
         "verify": ["This provision also applies to bones, body parts, and specimens that may be human remains", "Discovery of such bones, body parts, and specimens must be promptly reported to the coroner or medical examiner"],
         "also_verify": [{"url": "https://www.revisor.mn.gov/statutes/cite/307.08", "verify": ["All unidentified human remains or burials found outside of recorded cemeteries", "in contexts which indicate antiquity greater than 50 years shall be treated with the utmost respect for all human dignity", "they shall be dealt with in accordance with provisions established by the state archaeologist and other appropriate authority"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Except in an emergency, an excavator must contact the notification center (call 811) and give notice at least 48 hours, excluding the day of notification, Saturdays, Sundays and holidays, and not more than 14 calendar days before beginning any excavation. The notice is valid for 14 calendar days from the start time stated on it. Minnesota defines \"excavation\" as moving, removing or otherwise disturbing the soil with a motor, engine, hydraulic or pneumatically powered tool, or machine-powered equipment of any kind, or by explosives; it does not include gardening unless the gardening disturbs the soil to a depth of 12 inches or more. Operators must locate and mark their underground facilities without cost to the excavator.",
         "citation": "Minn. Stat. 216D.04, subds. 1, 3; Minn. Stat. 216D.01, subd. 5 (2026 statutes)", "url": "https://www.revisor.mn.gov/statutes/cite/216D.04",
         "verify": ["provide notice at least 48 hours, excluding the day of notification, Saturdays, Sundays, and holidays", "not more than 14 calendar days before beginning any excavation or boundary survey", "The notice is valid for 14 calendar days from the start time stated on the notice", "without cost to the excavator. Prior to the conclusion of the locate period"],
         "also_verify": [{"url": "https://www.revisor.mn.gov/statutes/cite/216D.01", "verify": ["disturbs the soil by use of a motor, engine, hydraulic or pneumatically powered tool, or machine-powered equipment", "gardening unless it disturbs the soil to a depth of 12 inches or more"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Minnesota statutes read verbatim on revisor.mn.gov on 2026-10-29; not legal advice",
})
_LAWS["PA"].update({
    "state_law": "Pennsylvania's archaeology law reserves field investigation of archaeological resources on Commonwealth-owned or -controlled land to the Commonwealth, with permits issued by the Pennsylvania Historical and Museum Commission (37 Pa.C.S. 506).",
    "source_url": "https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=37&div=0&chpt=5&sctn=6&subsctn=0",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Pennsylvania reserves the exclusive right to conduct archaeological field investigations on archaeological resources owned or controlled by the Commonwealth, and the Pennsylvania Historical and Museum Commission may issue permits for those investigations. That section speaks only to land the Commonwealth owns or controls; it sets no permit rule for ordinary private land. You still need the landowner's permission, and the rules below still apply.",
         "citation": "37 Pa.C.S. 506 (amended 28 Nov 1995)", "url": "https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=37&div=0&chpt=5&sctn=6&subsctn=0", "verify_url": "https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=37&div=0&chpt=5&sctn=6&subsctn=0&iFrame=true",
         "verify": ["The Commonwealth reserves the exclusive right to conduct archaeological field investigations on archaeological resources owned or controlled by it", "The commission may issue permits for archaeological field investigations", "archaeological resources located on land owned or controlled by the Commonwealth"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "It is a second-degree misdemeanor to intentionally desecrate a public monument or structure, or a place of worship or burial. Intentionally desecrating a historic burial lot or historic burial place is a first-degree misdemeanor. To desecrate is to deface, damage, pollute or otherwise physically mistreat in a way the person knows will outrage the sensibilities of people likely to observe or discover it. A historic burial place is a tract of land that has been a burial ground for more than 100 years, or that is listed in or eligible for the National Register of Historic Places as determined by the Pennsylvania Historical and Museum Commission. The section does not limit this to public land.",
         "citation": "18 Pa.C.S. 5509 (amended 9 Oct 2008)", "url": "https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=18&div=0&chpt=55&sctn=9&subsctn=0", "verify_url": "https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl=18&div=0&chpt=55&sctn=9&subsctn=0&iFrame=true",
         "verify": ["intentionally desecrates any public monument or structure, or place of worship or burial", "commits a misdemeanor of the first degree if the person intentionally desecrates a historic burial lot or historic burial place", "in a way that the actor knows will outrage the sensibilities of persons likely to observe or discover the action", "in existence as a burial ground for more than 100 years"]},
        {"topic": "Before you dig: buried utilities",
         "rule": "An excavator must submit a locate request through the One Call System not less than three nor more than ten business days before beginning excavation or demolition work, and no work may begin before the lawful start date, which is on or after the third business day after notification (a complex project needs at least ten business days). Saturdays, Sundays and legal holidays are not business days. The Act defines excavation work as the use of powered equipment or explosives to move earth, rock or other material, and an excavator as any person who performs excavation or demolition work for himself or for another person. It does not count soft excavation such as vacuum or high pressure air or water, or tilling of soil for agricultural purposes to a depth of less than eighteen inches.",
         "citation": "Act 287 of 1974 (Underground Utility Line Protection Law) sections 1 and 5, as amended 29 Oct 2024 (Act 127)", "url": "https://www.palegis.us/statutes/unconsolidated/law-information/view-statute?SESSYR=1974&SESSIND=0&ACTNUM=287&txtType=HTM", "verify_url": "https://www.palegis.us/statutes/unconsolidated/law-information/view-statute?SESSYR=1974&SESSIND=0&ACTNUM=287&iFrame=true&txtType=HTM",
         "verify": ["not less than three nor more than ten business days in advance of beginning excavation or demolition work", "No work shall begin earlier than the lawful start date which shall be on or after the third business day", "means the use of powered equipment or explosives in the movement of earth, rock or other material", "means any person who or which performs excavation or demolition work for himself or for another person", "tilling of soil for agricultural purposes to a depth of less than eighteen inches"]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Pennsylvania statutes read verbatim on palegis.us (General Assembly) on 2026-10-29; not legal advice",
})
_LAWS["MO"].update({
    "state_law": "Missouri's unmarked human burial law (RSMo 194.400 to 194.410) applies to private land and to state and local government land, and disturbing a marked or unmarked human burial site is a class E felony.",
    "source_url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.410",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Missouri's law on unmarked human burials and human skeletal remains (sections 194.400 to 194.410) applies when they are encountered during archaeological excavation, construction or other ground disturbing activities, whether on private land or water or on land or water owned by the state or its political subdivisions, agencies or instrumentalities. You still need the landowner's permission, and the rules below still apply.",
         "citation": "RSMo 194.405 (effective 28 Aug 1987)", "url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.405",
         "verify": ["encountered during archaeological excavation, construction, or other ground disturbing activities", "whether found on or in any private lands or waters or on or in any lands or waters"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Anyone who knowingly disturbs, destroys, vandalizes or damages a marked or unmarked human burial site commits a class E felony. Knowingly appropriating, using, selling, buying or transporting human remains for profit without the right of possession is a class A misdemeanor (a class E felony for a second or later violation). The burial law applies on private land as well as state and local government land.",
         "citation": "RSMo 194.410 (effective 1 Jan 2017); 194.405", "url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.410",
         "verify": ["who knowingly disturbs, destroys, vandalizes, or damages a marked or unmarked human burial site commits a class E felony", "knowingly appropriates for profit, uses for profit, sells, purchases or transports for sale or profit any human remains"],
         "also_verify": [{"url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.405", "verify": ["whether found on or in any private lands or waters or on or in any lands or waters"]}]},
        {"topic": "If you find human remains",
         "rule": "Anyone who knows or has reason to know that an unmarked human burial or human skeletal remains are being disturbed, destroyed, defaced, mutilated, removed, excavated or exposed must immediately notify either the state historic preservation officer or the local law enforcement officer with jurisdiction. When remains are encountered through construction or agricultural earth disturbing activities, or by a professional archaeologist in an investigation, those activities must stop immediately within 50 feet of the point of discovery and not resume without authorization from the historic preservation officer or the law enforcement officer who has jurisdiction, who must decide within a reasonable time. If law enforcement finds the remains may be part of a legal investigation it takes over; otherwise the state historic preservation officer does. For construction, the law adds that no construction is to be suspended or delayed more than thirty days.",
         "citation": "RSMo 194.406 (effective 28 Aug 1987); 194.407", "url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.406",
         "verify": ["shall immediately notify either the state historic preservation officer or the local law enforcement officer with jurisdiction for the area", "all such activities shall cease immediately within a radius of fifty feet of the point of discovery", "the human skeletal remains may be involved in a legal investigation, that officer will immediately assume all jurisdiction"],
         "also_verify": [{"url": "https://revisor.mo.gov/main/OneSection.aspx?section=194.407", "verify": ["no construction shall be suspended or delayed more than thirty days"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "An excavator must give notice to the notification center, by toll-free telephone or the internet, at least two working days but not more than ten working days before the expected start of excavation, before excavating in a public street, road or alley, right-of-way, utility easement of record, or within any private street or private property. The notice lasts until 11:59 p.m. twenty-one consecutive calendar days from the start date of work. Excavation means any operation that moves earth, rock or other material by any tools, equipment or explosives; the listed exemptions include tilling of soil for agricultural purposes when it does not exceed sixteen inches in depth.",
         "citation": "RSMo 319.015, 319.025, 319.026 (effective 28 Aug 2025)", "url": "https://revisor.mo.gov/main/OneSection.aspx?section=319.026",
         "verify": ["at least two working days, but not more than ten working days, before the expected date"],
         "also_verify": [{"url": "https://revisor.mo.gov/main/OneSection.aspx?section=319.025", "verify": ["or within any private street or private property until such excavator gives notice to the notification center", "an operational life ending at 11:59 p.m. twenty-one consecutive calendar days from the start date of work"]}, {"url": "https://revisor.mo.gov/main/OneSection.aspx?section=319.015", "verify": ["moved, removed or otherwise displaced by means of any tools, equipment or explosives", "the tilling of soil for agricultural purposes when such excavation does not exceed sixteen inches in depth"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Missouri statutes read verbatim on revisor.mo.gov (Missouri Revisor of Statutes) on 2026-10-29; not legal advice",
})
_LAWS["AZ"].update({
    "state_law": "Arizona requires a permit from the director of the Arizona State Museum to excavate or collect archaeological specimens on state-owned or -controlled land (ARS 41-841, 41-842), and separately requires the director's written permission to intentionally disturb human remains or funerary objects on other land, including private land (ARS 41-865).",
    "source_url": "https://www.azleg.gov/ars/41/00865.htm",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "Arizona's archaeological permit rule covers lands owned or controlled by the state or any state agency: there a person may not knowingly excavate a ruin, burial ground or archaeological site, or collect an archaeological specimen at least 100 years old, without a permit from the director of the Arizona State Museum. A separate rule covers other land, which includes private land: you may not intentionally disturb human remains (a person who died more than fifty years before discovery) or funerary objects without the museum director's written permission. You still need the landowner's permission, and the rules below still apply.",
         "citation": "ARS 41-841, 41-842, 41-865", "url": "https://www.azleg.gov/ars/41/00841.htm",
         "verify": ["a person shall not knowingly collect any archaeological specimen or vertebrate paleontological specimen without obtaining a permit", "which is at least one hundred years old"],
         "also_verify": [{"url": "https://www.azleg.gov/ars/41/00865.htm", "verify": ["shall not intentionally disturb human remains or funerary objects on lands, other than lands owned or controlled by this state", "without obtaining the written permission of the director of the Arizona state museum", "means any remains of a human being who died more than fifty years before the remains are discovered"]}, {"url": "https://www.azleg.gov/ars/41/00842.htm", "verify": ["No such activity may be undertaken until a permit is first secured therefor from the director"]}]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "On land other than state, state-agency, county or municipal land, intentionally disturbing human remains (people who died more than fifty years before discovery) or funerary objects (objects found close to and interred with the remains) without the Arizona State Museum director's written permission is a class 1 misdemeanor. Intentionally possessing, selling or transferring remains or funerary objects removed in violation is a class 5 felony, and the remains, objects and any sale proceeds are forfeited to the museum.",
         "citation": "ARS 41-865(A), (G), (H)", "url": "https://www.azleg.gov/ars/41/00865.htm",
         "verify": ["shall not intentionally disturb human remains or funerary objects on lands, other than lands owned or controlled by this state", "otherwise intentionally violates subsection A or B is guilty of a class 1 misdemeanor", "intentionally possesses, sells or transfers any human remains or funerary objects that are excavated or removed", "means an object discovered in close proximity to human remains and interred with the remains"]},
        {"topic": "If you find human remains",
         "rule": "If you unintentionally disturb human remains or funerary objects on land other than state, state-agency, county or municipal land, you must report the disturbance to the director of the Arizona State Museum and not disturb them further without the director's written permission. The statute gives no deadline for the report. Its rules for permission requests must require the director to respond within ten working days, and a failure to respond in that time is deemed permission to proceed. On state, state-agency, county or municipal land, the person in charge of a survey, excavation or construction must report promptly to the director any archaeological, paleontological or historical site or object at least fifty years old.",
         "citation": "ARS 41-865(B), (C); 41-844(A)", "url": "https://www.azleg.gov/ars/41/00865.htm",
         "verify": ["unintentionally disturbs human remains or funerary objects on lands, other than lands owned or controlled by this state", "shall report the disturbance to the director and shall not further disturb the remains or objects", "his failure to respond to the request is deemed permission to proceed"],
         "also_verify": [{"url": "https://www.azleg.gov/ars/41/00844.htm", "verify": ["shall report promptly to the director of the Arizona state museum the existence of any archaeological"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "Before making or beginning any excavation in a public street, alley, right-of-way dedicated to public use or public utility easement, or in any express or implied private property utility easement (or an apartment community or mobile home park), a person must first determine from each underground facilities operator whether underground facilities will be encountered and where. Operators must respond and mark not later than two working days after the inquiry, and you may not begin before marking is complete or you are told marking is unnecessary; markings are valid for fifteen working days. Excavation means any operation that moves earth, rock or other material by any tools, equipment or explosives. Before a location request, the area must be white-lined, except for excavations a person performs on a single-family residential property that the person owns or occupies. An implied easement is any easement or right-of-way on private property required to provide utility services by underground facilities in the property of the owner requesting the service.",
         "citation": "ARS 40-360.21, 40-360.22", "url": "https://www.azleg.gov/ars/40/00360-22.htm",
         "verify": ["or in any express or implied private property utility easement or in any apartment community or mobile home park", "not later than two working days, by carefully marking the underground facility", "is valid for fifteen working days from the date of the marking", "Does not apply to excavations that are performed by a person on a single-family residential property"],
         "also_verify": [{"url": "https://www.azleg.gov/ars/40/00360-21.htm", "verify": ["means any operation in which earth, rock or other material in the ground is moved, removed or otherwise displaced", "means any easement or right-of-way on private property required to provide utility services by means of underground facilities"]}]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "Arizona statutes read verbatim on azleg.gov on 2026-10-29; not legal advice",
})
_LAWS["NM"].update({
    "state_law": "New Mexico's Cultural Properties Act (NMSA 18-6-1 et seq.), through its rules, requires a permit to excavate an archaeological site on private land with mechanical earth-moving equipment when someone other than the landowner or the landowner's agent does it, and protects unmarked burials on all state and private land.",
    "source_url": "https://srca.nm.gov/parts/title04/04.010.0014.html",
    "digger_rules": [
        {"topic": "Your own private land",
         "rule": "New Mexico's rule on private land applies to anyone proposing to excavate an archaeological site on private land with the aid of mechanical earth-moving equipment (any motorized machine or device capable of displacing or moving earth, including trenchers, backhoes, graders, scrapers, bulldozers and front-end loaders). The Cultural Properties Review Committee issues the permit when a public or private entity other than the landowner or the landowner's agent proposes to do the excavation. The rule does not apply to state or federal land or land held in trust for an Indian tribe. Unmarked human burials have their own rules, below. You still need the landowner's permission, and the rules below still apply.",
         "citation": "4.10.14 NMAC (effective 16 Jan 2019), implementing NMSA 18-6-11", "url": "https://srca.nm.gov/parts/title04/04.010.0014.html",
         "verify": ["proposing to excavate, with the aid of mechanical earth-moving equipment, an archaeological site on private land", "when a public or private entity other than the landowner or the agent of the landowner proposes to conduct excavation", "any motorized machine or device that is capable of displacing, disturbing or moving earth"]},
        {"topic": "Mounds, earthworks and burial places",
         "rule": "Under the rule implementing NMSA 18-6-11.2, excavation, removal, disturbance or destruction of an unmarked human burial or unmarked burial ground may be carried out only by authority of the state medical investigator or of the permitting authority. An unmarked burial ground is a location with a burial that is not visibly marked on the surface in any way traditionally or customarily used for marking burials, including associated funerary objects and artifacts. The law applies to all lands of the state and all private lands in New Mexico, but not to federal land or land held in trust for an Indian tribe by the federal government.",
         "citation": "4.10.11 NMAC, sections 2, 7 and 8 (rule implementing NMSA 18-6-11.2)", "url": "https://srca.nm.gov/parts/title04/04.010.0011.html",
         "verify": ["applies to all lands of the state of New Mexico and all private lands in the state of New Mexico", "It does not apply to federal lands or to lands held in trust for an Indian tribe", "may be carried out only by authority of the state medical investigator or of the permitting authority", "that are not visibly marked on the surface of the ground in any manner traditionally or customarily"]},
        {"topic": "If you find human remains",
         "rule": "Anyone who discovers an unmarked human burial or unmarked burial ground must stop any activity that may disturb it, or any object or artifact associated with it, and notify the local law enforcement agency having jurisdiction. Local law enforcement then notifies the medical investigator and the State Historic Preservation Officer. All unmarked human burials in New Mexico are presumed to fall under the authority of the medical investigator. The rule states no time limit for the notice. On private land, the rules repeat that local law enforcement must be notified if evidence of a human burial or unmarked burial ground is discovered.",
         "citation": "4.10.11.8 NMAC (rule implementing NMSA 18-6-11.2(C)); 4.10.14.8 NMAC", "url": "https://srca.nm.gov/parts/title04/04.010.0011.html",
         "verify": ["Any person who discovers an unmarked human burial or unmarked burial ground shall cease any activity", "and shall notify the local law enforcement agency having jurisdiction in the area", "unmarked burial grounds in the state of New Mexico shall be presumed to fall under the authority of the MI"],
         "also_verify": [{"url": "https://srca.nm.gov/parts/title04/04.010.0014.html", "verify": ["If evidence of a human burial or unmarked burial ground is discovered on private land"]}]},
        {"topic": "Before you dig: buried utilities",
         "rule": "An excavator must make an excavation locate request to the one-call notification system (by telephone or in person during business hours, or by fax or online around the clock) for all projects involving excavation, except subsurface potholing or vacuum excavation done only to expose or locate underground facilities. Facility owners must locate and mark within two full working days from the effective date of the ticket, and the effective date excludes the day of notice and begins at 12:01 a.m. after two full working days. For projects using purely non-mechanical means, a locate request is not required by the state law or this rule but is encouraged.",
         "citation": "18.60.5 NMAC (Excavation Damage Prevention, effective 15 Jan 2019), implementing NMSA 62-14-1 et seq.", "url": "https://srca.nm.gov/parts/title18/18.060.0005.html",
         "verify": ["An excavator shall make an excavation locate request for all projects involving excavation", "locate requests are encouraged for excavation projects involving purely non-mechanical means", "shall locate and mark its underground facilities within two full working days from the effective date", "whereby the computed date shall begin at 12:01 a.m. after two full working days"]},
    ],
    "checked_on": "2026-10-29",
    "verification_status": "New Mexico administrative rules (NMAC) read verbatim on the State Records Center and Archives site (srca.nm.gov) on 2026-10-29, and statutes read verbatim in the official NMOneSource PDF (nmonesource.com); not legal advice",
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
