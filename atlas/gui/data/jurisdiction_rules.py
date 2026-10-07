"""Jurisdiction-level archaeology checks, sourced to official authorities.

These describe questions for a project director and regulator. They do not
establish that a listed project's 2027 permits, land access, or consultations
have been completed. Local rules and authority assignments can change.
"""

JURISDICTION_RULES = {
    "us_forest": {
        "jurisdiction": "United States · National Forest land",
        "authority": "U.S. Forest Service, Helena–Lewis and Clark National Forest",
        "rule": "Excavation or removal of archaeological resources on federal land requires a qualified team's archaeological investigations permit. Excavated federal resources remain U.S. property and require appropriate curation.",
        "verify": "Ask the Forest Service which permit covers the 2027 work, what land and curation terms apply, and how it is handling consultation with Tribes and other affected parties.",
        "source_url": "https://www.fs.usda.gov/media/159035",
        "additional_url": "https://www.achp.gov/Section_106_Archaeology_Guidance/Questions%20and%20Answers/Section%20106%20consultation%20about%20archaeology",
    },
    "portugal": {
        "jurisdiction": "Portugal · Alentejo",
        "authority": "Património Cultural, I.P. and the competent regional heritage service",
        "rule": "Portugal's Archaeological Works Regulation requires authorization for archaeological work and prior consent from the landowner. The regulation names an earlier agency, so the present filing authority should be confirmed.",
        "verify": "Request the project's current authorization, scientific director, approved research plan, landowner consent, curation arrangements, and the responsible regional service.",
        "source_url": "https://diariodarepublica.pt/dr/detalhe/decreto-lei/164-2014-58728911",
        "additional_url": "https://www.patrimoniocultural.gov.pt/instituicao/apresentacao/",
    },
    "scotland": {
        "jurisdiction": "Scotland · Gallow Hill Fort, Dunblane",
        "authority": "Historic Environment Scotland if scheduled; landowner and local archaeological authorities in any case",
        "rule": "Excavation of a scheduled monument requires Scheduled Monument Consent, and the owner must also allow the work. Whether this particular fort is scheduled has not been established in the catalogue.",
        "verify": "Check the correct fort's designation record, then ask the director for consent and land access evidence; the similarly named Gallow Hill Cairn is a separate site.",
        "source_url": "https://www.historicenvironment.scot/protect-and-care/owning-managing-and-visiting/consents-and-permissions/scheduled-monuments/what-needs-consent/",
        "additional_url": "https://portal.historicenvironment.scot/apex/f?p=PORTAL%3Asearch",
    },
    "greece": {
        "jurisdiction": "Greece · Ancient Argilos",
        "authority": "Hellenic Ministry of Culture and Ephorate of Antiquities of Serres",
        "rule": "Archaeological research is controlled under Greece's heritage legislation. The Argilos mission names the Serres Ephorate and Université de Montréal as collaborators; that does not itself prove a particular 2027 permit or sponsor right.",
        "verify": "Ask the mission and Ephorate to confirm 2027 authorization, allowed activities, conservation and publication duties, and any terms for a financial contributor.",
        "source_url": "https://api.et.gr/apiLAW/1/2021/4858/pdf",
        "additional_url": "https://www.culture.gov.gr/en/ministry/SitePages/viewyphresia.aspx?iid=1695",
    },
    "belize": {
        "jurisdiction": "Belize · Blue Creek region",
        "authority": "National Institute of Culture and History, Institute of Archaeology",
        "rule": "Belize's published archaeological research policy calls for an Institute of Archaeology research permit, research proposal, budget, and curation plan; the permit holder must identify the site or area.",
        "verify": "Confirm the 2027 permitted sites, principal investigator, any funder disclosure required by the permit, local consultation, and approved storage and publication plan.",
        "source_url": "https://nichbelize.org/wp-content/uploads/2025/02/Archaeological-Research-Policy-2024.pdf",
        "additional_url": "https://nichbelize.org/institute-of-archaeology/",
    },
    "austria": {
        "jurisdiction": "Austria · Roman Aguntum",
        "authority": "Bundesdenkmalamt, Federal Monuments Office",
        "rule": "Austria's Federal Monuments Office says archaeological excavation and prospection with technical equipment require its authorization, which is granted to people with a relevant completed degree.",
        "verify": "Ask the University of Innsbruck site director for the 2027 approval, land access, finds reporting, conservation, and curation terms.",
        "source_url": "https://www.bda.gv.at/service/archaeologie.html",
        "additional_url": "https://www.bda.gv.at/service/haeufige-fragen/archaeologie.html",
    },
    "peru": {
        "jurisdiction": "Peru · Lambayeque",
        "authority": "Ministerio de Cultura, archaeological intervention authorization office",
        "rule": "A research archaeology project involving survey or excavation requires prior Ministry of Culture authorization. The regulatory text was amended in 2025, so current project conditions must be checked.",
        "verify": "Ask the Peruvian project lead to show the 2027 research authorization, site boundaries, local partnerships, custody of finds, and the approved sampling and publication plan.",
        "source_url": "https://www.gob.pe/en/527-autorizar-la-ejecucion-de-un-proyecto-de-investigacion-arqueologica-pia",
        "additional_url": "https://www.gob.pe/institucion/cultura/campa%C3%B1as/27839-direccion-de-calificacion-de-intervenciones-arqueologicas",
    },
    "catalonia": {
        "jurisdiction": "Spain · Catalonia",
        "authority": "Generalitat de Catalunya, Direcció General del Patrimoni Cultural",
        "rule": "Catalan heritage law requires prior authorization for archaeological interventions, including survey and excavation. Ownership permission and any applicable municipal approval are separate issues.",
        "verify": "Ask the scientific directors for the 2027 research authorization, approved sector, landowner consent, sampling and curation arrangements, and any additional protected-site conditions.",
        "source_url": "https://cultura.gencat.cat/web/.content/dgpc/arxius_i_gestio_documental/07_marc_normatiu/static_file/llei_09_1993.pdf",
        "additional_url": "https://tramits.gencat.cat/ca/tramits/tramits-temes/Autoritzacio-dintervencions-arqueologiques-o-paleontologiques-preventives",
    },
    "oman": {
        "jurisdiction": "Oman · Sharqiyah",
        "authority": "Ministry of Heritage and Tourism; confirm the competent office under the 2026 amendment",
        "rule": "Oman's Cultural Heritage Law governs archaeological survey and excavation. Royal Decree 62/2026 assigns the competent authority by remit across the heritage and culture ministries. A participant visa does not confirm the research team's fieldwork authorization.",
        "verify": "Ask Time of Magan and the competent Omani authority to confirm the 2027 authorization, institutional partner, land access, finds custody, and conditions for any external sponsor.",
        "source_url": "https://www.mjla.gov.om/laws/ar/1/show/164",
        "additional_url": "https://mht.gov.om/ar/%D8%A7%D9%84%D9%85%D8%B1%D9%83%D8%B2-%D8%A7%D9%84%D8%A5%D8%B9%D9%84%D8%A7%D9%85%D9%8A/%D8%A7%D9%84%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1/%D9%85%D8%B1%D8%B3%D9%88%D9%85-%D8%B3%D9%84%D8%B7%D8%A7%D9%86%D9%8A-%D8%A8%D8%AA%D8%B9%D8%AF%D9%8A%D9%84-%D8%A8%D8%B9%D8%B6-%D8%A3%D8%AD%D9%83%D8%A7%D9%85-%D9%82%D8%A7%D9%86%D9%88%D9%86-%D8%A7%D9%84%D8%AA%D8%B1%D8%A7%D8%AB-%D8%A7%D9%84%D8%AB%D9%82%D8%A7%D9%81%D9%8A/",
    },
}
