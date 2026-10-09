> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# State fossil geology readings: sources and method

Reviewed 2026-10-07. The offline reading library in
`core/state_fossil_library.py` contains 52 entries: all 50 states, the District
of Columbia, and Puerto Rico. Each entry has three short, authored facts with
citations attached to the individual claim. The GUI data module re-exports the
same reader without duplicating the research data.

## How to read the status labels

The National Park Service's [Official State Fossils page](https://www.nps.gov/subjects/fossils/official-state-fossils.htm)
is the shared starting index for state fossils, state dinosaurs, and fossiliferous
state stones. It was last updated August 13, 2024 when reviewed here. Some entries
are state stones or proposed examples, so each reading states that distinction.
When an entry says that no example is listed, it means only that the NPS page has
no entry for that jurisdiction; it does not claim that the jurisdiction has no
official designation or no fossils.

State statutes and state geological surveys were used to verify designations,
names, and ages. Where an older NPS entry disagrees with a more current state
source, the reading follows the state source. For Missouri, for example, the
Missouri Geological Survey places the official crinoid in Mississippian-age
Burlington Limestone, and the Secretary of State uses *Parrosaurus missouriensis*
for the state dinosaur.

## Geologic context and sources

The [NPS state geologic map directory](https://www.nps.gov/subjects/geology/state-geologic-maps.htm)
links to bedrock or surficial maps maintained by state surveys and USGS. The
[USGS Cooperative National Geologic Map v2](https://www.usgs.gov/news/national-news-release/usgs-cooperative-national-geologic-map-now-covers-50-states-us)
was released September 3, 2026 and supplies standardized map context for all
50 states and most territories, including Puerto Rico. A geology map is a map
of rock units, materials, and ages; it is not a fossil occurrence or collection
inventory. Statewide units do not establish what is present at a town or parcel.

For jurisdictions absent from the NPS index, summaries use primary government
or university survey sources:

- Arkansas Geological Survey, [Fossils in Arkansas](https://geology.arkansas.gov/geology/fossils.html): common invertebrates, occasional Cretaceous vertebrate remains, Pleistocene mammals, and pseudofossil comparisons.
- USGS Hawaiian Volcano Observatory, [Fossils reveal Hawaiʻi's past birdlife](https://www.usgs.gov/news/volcano-watch-fossils-reveal-birdlife-hawaiis-past): bird remains in dunes, sinkholes, and lava tubes; most dated bones are only a few thousand years old.
- Iowa Geological Survey, [Fossils](https://iowageologicalsurvey.uiowa.edu/iowa-geology/popular-interest/fossils) and [Paleozoic Plateau](https://iowageologicalsurvey.uiowa.edu/iowa-geology/landforms-iowa/paleozoic-plateau): fossil groups and older marine settings.
- Minnesota Geological Survey, [Fossils](https://cse.umn.edu/mgs/fossils) and [Paleozoic geology](https://cse.umn.edu/mgs/paleozoic-geology): stromatolites, marine fossils, Cretaceous deposits, Pleistocene mammals, and gaps in the preserved rock record.
- USGS, [Fossils of the Littleton Formation, New Hampshire](https://www.usgs.gov/publications/fossils-littleton-formation-lower-devonian-new-hampshire) and [Littleton-area stratigraphy field guide](https://pubs.usgs.gov/of/2014/1026/pdf/ofr2014-1026.pdf): documented fossils in metamorphosed Silurian and Devonian rocks.
- USGS, [Puerto Rico regional geology](https://pubs.usgs.gov/ha/ha730/ch_n/N-PR_VItext1.html) and [Professional Paper 953](https://pubs.usgs.gov/pp/0953/report.pdf): Oligocene–Pliocene coastal limestones and fossiliferous shallow-marine formations.

Other primary NPS, USGS, state survey, museum, and university references are
attached directly to the facts they support in the data module. The source
directory in `docs/` does not replace those claim-level citations.

The reader contract is `state_reading(code)`. It returns a detached record with
the jurisdiction name, chapter title, sourced facts, fossil groups, period
labels, review date, and designation status; unknown codes return `None`.

## Editorial and reuse notes

The fact text is original paraphrase, generally one or two sentences. It does
not reproduce source articles, tables, or images. Source URLs are supplied for
verification; a citation is not a grant of reuse rights for source material.
No raw website copies or downloaded map datasets are shipped with this reading
library.

The readings are educational comparisons. They name geologic periods and fossil
groups, distinguish body fossils from traces where useful, and keep formation
or map context separate from local occurrence. They do not provide exact find
coordinates, collection directions, property-level odds, or calendar dates for
individual specimens.
