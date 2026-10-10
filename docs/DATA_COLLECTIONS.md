> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Downloadable local collections

Open **Atlas → Manage offline collections**. Each card shows its source, reuse rights,
snapshot, record coverage and download/storage sizes. Choose **Download
collection**; progress remains available after a page reload. Open the installed
collection to explore it in the shared atlas search and reader. Internet access is needed for the
initial download and external source pages.

In the shared reader, **Published location → Show published location map**
draws Neotoma's original point or bounding area and PBDB's modern collection
coordinates. It opens only on request and works offline. Multiple original
Neotoma sites stay separate. Missing or invalid coordinates receive no invented
location; a taxon receives no point from its name. The coarse modern land outline
provides orientation, with the publisher's coordinates and qualifications beside
the map. See [offline map sources](OFFLINE_MAP_SOURCES.md).

Multiword Neotoma searches use the two rarest terms to find a bounded set of
original row ordinals, then check remaining terms through those rows' original
parent links. The plan stores at most 1,000 candidate ordinals per evidence
type. Larger candidate sets use the complete existing query; this threshold
does not limit returned records or pagination. Single-term and broad aggregate
searches retain their existing plans.

| Collection | Contents | Download | Installed |
|---|---|---:|---:|
| World archaeological radiocarbon results | 173,946 laboratory determinations; 144 recorded country labels | 17.7 MB | 63.2 MB |
| Dinosaur taxa and fossil sites | 37,852 published occurrences; 14,371 collections; 12,996 original taxonomic names across ranks, including synonyms | 27.8 MB | 266.8 MB |
| Neolithic food, farming and animal remains | 96,115 source rows in twelve linked UCL EUROEVOL tables; 4,757 sites and 2,807 occupation phases | 17.0 MB | 103.1 MB |
| Excavation contexts, finds and survey effort | 153,867 distinct source subjects from Gabii, Petra and Eastern Korinthia; original observation documents, tables and field definitions | 243.2 MB | 576.6 MB |
| Sites, samples and past environments | 17,882,630 readable records within 20,447,331 original Neotoma scientific rows; 32,061 source sites | 562.4 MB | 2.67 GB |
| Anatolian animal-bone records | 242,457 published subject IDs, 4,026 context references and 814 aggregate rows; 838,710 original rows in 37 table editions | 456.7 MB | 981.6 MB |
| Excavation assemblages and refits | 153,796 original records: 64 matrices/spectra and 122 publisher documents across eight source corpora in seven countries | 163.5 MB | 531.4 MB |

The existing museum, newspaper, map, geology and mineral catalogs remain
bundled. These additional collections are optional; the initial application
still includes those existing large catalogs.

## Anatolian animal-bone records

Search a place such as **Catalhoyuk** or **okuzini**, a taxon, element,
recovery method or original Open Context identifier. Use **Limit to a source →
Open Context · Anatolian animal-bone records** to focus the collection.
Open a subject, follow its **Recorded context references**, or read its
**Original table rows and measurements** in the same source reader.

All 838,710 original table rows retain their ordered fields and publisher IDs.
Separate editions preserve source taxonomy, anatomy, tooth wear, taphonomy,
biometrics, quantities, study flags and recovery methods. Original fields open
under each table edition. Repeated column names, zero values, blanks and
disagreements remain visible. Some old source fields contain undecodable bytes;
Clovis shows those bytes explicitly, without guessing their characters.

These are 242,457 published subject identifiers, 4,026 context references and
814 aggregate rows. Subjects may appear in multiple editions. Counts do not
describe 838,710 different bones. Measurement-only records, secure subsets,
excluded seasons and original recovery flags retain their qualifications.
Context references come from specimen tables; the collection supplies no
independent excavation-unit documents or deposit sequence. Geographic and
calendar-BP annotations are editorial context, rather than specimen GPS or
direct dating measurements. Unspecified precision and measurement units remain
unspecified.

Source: [Open Context EOL zooarchaeology repository](https://github.com/ekansa/opencontext-eol-zooarch),
pinned edition `1402f66d445aa36bab044c34f3f10b758fc4c5ef`. This particular
repository edition declares **CC BY 3.0**. Original contributor names, project
and context URIs, table URLs and SHA-256 citations accompany records and saved
references. Download once for local reading; original external source pages
require internet access.

## Excavation assemblages and refits

Search **Hoedjiespunt**, **Macrofauna**, **K11-9-1**, **Sikait**, **Berenike**,
**RF.c_205** or **RF_Connections_Correlation**. Open the collection card or
choose **Limit to a source → Excavation & survey assemblages**.
Use the shared reader's **Associated evidence** to follow field recordings,
original lithic-analysis keys, recorded loci, pottery-bag references and refit
endpoints. Every matching source row remains available through pagination.

Hoedjiespunt retains all twelve original tables: 1,852 field records, bulk
recovery, lithic attributes and measurements, fauna, ochre and recording codes.
Recovery quantities retain original units and zero values. Linked field
records retain the original LITER volume field. Exact source identifiers and
derived unambiguous suffix-zero associations are labelled separately.
Source geological order refers to layers, while excavation UNIT refers to a
square. Local XYZ coordinates and recording dates are retained as recorded.

Berenike and Sikait retain all four original pottery and chronology workbooks.
Their 10,653 pottery rows are grouped observations; recorded Total values sum
to 58,175 Berenike fragments and 20,399 Sikait fragments. Formula expressions
and publisher-cached results remain separate, without recalculation. Original
cell positions, types, styles, merged anchors, chronological labels and mixture
notes stay available. Qualified section links cite their heading cells; blank
original trench/locus cells remain blank. Parallel chronology sections, ranges
and campaign-qualified trench labels stay distinct. Adjacent chronology-strength
legends do not become row confidence scores.

Fumane retains all seven original refit/attribute tables and all 948 specimen
metadata rows. Repeated endpoint columns retain their positions. Fragment IDs,
reconstructed blank numbers and full RF artifact identifiers have separate
namespaces. Both RF.c_205 model-metadata rows remain, with their different mesh
resolution. Clovis includes metadata under the fixed edition's recorded CC BY
4.0 rights. Its README also describes non-commercial model use and contains
an inconsistent Bombrini overview; meshes and that overview are not imported.

These rows, recording codes and annotations describe different quantities,
including overlapping analyses. They do not count unique artifacts or digs.
Undeclared units, geographic transformations and missing occupation dates are
not inferred. A refit or connection note does not establish deposit order.
Full original fields start closed; saving a reference retains contributors,
the particular source edition, original file hash and row locator.

The expanded edition adds the Chengdu Plain survey in China, Hacienda El
Progreso in Ecuador, Khao Toh Chong in Thailand and Madjedbebe in Australia.
Search **Chengdu**, **El Progreso**, **Madjedbebe**, **Banda Neira pH** or
**PTTDBDT**. Publisher context documents and laboratory readings have their
own record labels. Collection updates retain prior installed versions for
offline use, and the interface still shows seven collection cards.

Chengdu retains all 80,656 original CSV rows, including layers, sampling
waypoints, artifact bags, sherd observations, area-period summaries and tombs.
Negative soil observations remain evidence. Bag correspondence distinguishes
18,274 complete-key matches from 537 dictionary-supported FCN/waypoint matches
whose original Bag Number remains blank. Eighteen unmatched and nineteen
ambiguous sherd rows remain unresolved. Context containment does not establish
deposit order. Published WGS-84 reference points retain location-inference
wording; they do not establish an individual artifact's measured position.

El Progreso's 4,722 grouped faunal rows contain 25,492 recorded specimens;
these quantities are distinct. Literal locale/unit/level identifiers, weights,
taxonomic and anatomical identifications, burning and breakage remain available.
The row weights sum to 118,880 g, while project prose reports 118,820 g;
both statements retain their attribution. The publisher's public-domain label
and CC0 machine URI are retained separately.

Khao Toh Chong includes material recording, radiocarbon, 31 particle-size runs,
all 31,559 points in nine original diffraction spectra, and nineteen distinct
laboratory matrix sections. Its particle export's malformed header and NUL
trailer remain available separately from readable bindings. Banda Neira Unit 5
is a separately labelled source block. Blank templates, laboratory controls,
filename/title conflicts and undeclared signal units remain explicit.

Madjedbebe's fixed 1989-excavation compendium retains all six original CSVs.
Compound square/spit identifiers and calibration editions stay separate.
Two original serialized reproduction results are retained as opaque data
attachments; posterior draws are not counted as dates or excavated specimens.
These two Figshare compendia dedicate data to CC0 in their READMEs, while the
archive metadata states CC BY 4.0. Publisher R and other code is not executed
or included in the collection.

Additional sources: [Chengdu survey](https://opencontext.org/projects/968ea7e8-d521-4b4c-951c-01adcac7307f),
[El Progreso fauna](https://doi.org/10.6078/M7MS3QTG),
[Khao Toh Chong v4](https://doi.org/10.6084/m9.figshare.2065602.v4), and
[Madjedbebe v4](https://doi.org/10.6084/m9.figshare.1297059.v4).

Sources: [Hoedjiespunt 1](https://doi.org/10.5281/zenodo.10731129),
[Berenike and Sikait pottery](https://doi.org/10.5281/zenodo.18681814),
[Fumane specimen metadata](https://doi.org/10.5281/zenodo.15382869), and
[Fumane research compendium](https://github.com/ArmandoFalcucci/Refitting-The-Context),
pinned to `f6082f21e1c0d0f2ed8f81716cb7c2a1abfc5645`. Data editions retain CC BY
4.0 contributor attribution. The fixed publication reproduction edition and
developmental repository edition remain separate. The expanded collection
requires Clovis 0.18 or newer; the original 0.17 snapshot remains available.

## Radiocarbon results

Search charcoal, shell, a laboratory identifier such as **A-0034**, a recorded
site name, or a reference. Filter by recorded country and, if useful, integer
laboratory ages using **Specialist searches → Radiocarbon dates**. Read material, method, uncertainty, site labels and original
references before saving a dating reference to your fieldbook.

The source ages are **uncalibrated radiocarbon years BP**. Errors are the original
one-sigma standard errors. The collection supplies no calibrated BCE/CE dates
and does not date your own find. Source material, taxonomic labels, δ13C,
methods, periods, site labels and references remain source-supplied, with the
compilation's qualifications. Some contributors used zero for missing δ13C.
Coordinates are omitted; missing fields remain unknown.

Source: [p3k14c](https://github.com/people3k/p3k14c), release 2025.07, pinned
public scrubbed/fuzzed CSV. Data are CC0 1.0. Attribution and the
[publication](https://doi.org/10.1038/s41597-022-01118-7) remain with every
collection. A source release is not the date of every laboratory result.

## Dinosaur taxonomy and fossil sites

In **Specialist searches → Dinosaur taxa & sites**, choose **Published fossil occurrences** or **Taxonomic names & sites**. Search
**Tyrannosaurus rex**, a formation such as **Morrison**, a collection name or a
reference. Choose non-avian dinosaurs, fossil birds, or all Dinosauria; country
codes retain the source's ISO labels. Read the published identification beside
the snapshot accepted name. **Taxonomic names only** searches identifications
and accepted names; **All record fields** also searches sites, formations and
references. The taxonomy view preserves synonyms and source
name variants, and shows associated occurrences. A taxon without a selected
occurrence receives no inferred location.

The pack includes all occurrences whose accepted or identified original taxon
falls within the source's Dinosauria subtree in the frozen 20 September 2026
snapshot. Of these, 22,662 are non-avian and 15,190 are avian. It preserves
17,346 taxonomic variant records for 12,996 original taxonomic IDs. These are
names across multiple ranks, including synonyms; they are **not species counts**.
7,063 original IDs have associated selected occurrences.

Locations are **reported collection points**, with the original latitude,
longitude, location basis, precision description and geographic scale. They
are not individual specimen GPS fixes. Source protected-land codes retain their
land-status meaning. Geological age bounds retain their numerical strings;
**Ma** means millions of years ago. Occurrence records, collections, taxonomic
names and physical specimens are separate quantities.

Source: [Paleobiology Database snapshot](https://zenodo.org/records/22870967),
archived for Chronosphere. The archive is CC BY 4.0; its original API metadata
declares CC0. Attribution, original references and the frozen source DOI are
included. Contributor account fields and images are omitted. This published
corpus does not cover every unreported find or absent museum specimen.

## Neolithic assemblages

Search **Arbon**, **barley**, **Bos taurus**, a culture or a source identifier.
Use **Limit to a source → UCL · Neolithic assemblages** to focus on this pack.
Read a site or occupation phase, then follow **Associated evidence** to its
animal observations, plants or dating samples. Related lists use the same
search, reader and pagination. Bone records link to their original phase and
measurements; recovery methods and original source fields remain readable.

The twelve tables contain 4,757 published site labels, 2,807 occupation phases,
10,318 animal observations, 8,327 plant observations, 16,737 bone records,
36,483 measurements and 14,053 dating samples, plus recovery and taxonomic
tables. These counts describe different kinds of source rows. Presence-only
observations stay separate from quantitative specimen or plant counts; source
zeros and unknowns remain distinct. Ages remain uncalibrated BP, bone measurements
remain in mm, and original method and mesh-size strings are retained. All twelve
publisher field dictionaries accompany the pack.

Coverage is Central and Northwest Europe with 16 source country labels. Only
72 phases have animals, plants and linked dates together; 7,726 date rows have
no recorded phase. An occupation phase association does not establish an
individual deposit, a stratigraphic sequence or equal recovery effort.
Coordinates are omitted. Dating samples overlap other compilations: 4,511
laboratory-code strings also occur in the radiocarbon pack. Each source retains
its attribution; the pack does not claim those are distinct new dates.

Source: [UCL EUROEVOL](https://discovery.ucl.ac.uk/id/eprint/1469811/), supplied
2015 tables, with the publisher's CC0 waiver and original attribution.

## Excavation contexts and survey effort

Search **5016**, **pottery**, **charcoal**, a project name or an original Open
Context subject URL. Use **Limit to a source → Open Context · excavations &
surveys** to focus the search. Open a record, then follow **Associated evidence**
to its recorded parent context, finds or samples. **More associated evidence**
contains the publisher's typed links, including fills and above/below relations
where actually recorded. These lists use the same reader and pagination.

The collection includes 9,008 original individual documents, 38 published
table versions containing 146,474 overlapping rows, and 834 original field
definitions. Its 153,867 distinct subjects include excavation units, objects,
samples and survey contexts. Some subjects have only table fields or a publisher
query summary; the reader identifies the available evidence. These counts are
not individual finds, separate excavations or a worldwide census.

Read recovery methods, recorded zero counts and survey procedures beside their
original observations. Empty values remain distinct from zeros and `False`.
**Field meanings and units** explains the source fields. For example, EKAS Area
is expressed in square metres calculated through ArcGIS, an analytical addition
rather than an original field measurement. Survey classes and collected specimens
remain distinct from observed counts. Separate table versions retain their
citations without inflating the unique subject count.

**Published location and time** retains original geometry, specified/inferred
references, precision notes and ISO years. An inherited location does not become
an individual find GPS fix. Named spatial containment, recorder identities and
free-text mentions do not become stratigraphic links. Saving a source reference
preserves authors, source identifiers, source hashes and location/time qualifiers.

Sources: [Michigan Gabii](https://opencontext.org/projects/3585b372-8d2d-436c-9a4c-b5c10fce3ccd),
[Brown Petra Great Temple](https://opencontext.org/projects/a5ddbea2-b3c8-43f9-8151-33343cbdc857)
and [Eastern Korinthia Archaeological Survey](https://opencontext.org/projects/bc71c724-eb1e-47d6-9d45-b586ddafdcfe),
published through Open Context under CC BY 4.0. Original authors, licenses and
table versions accompany the collection. External media remain source links.

## Sites, samples and past environments

Search **Meadowcroft Mammalia**, **charcoal**, **pollen**, a published site,
region or an original identifier such as **observation:918211**. Use **Limit to
a source → Neotoma · sites, samples & environments** to focus this collection.
Follow **Associated evidence** from the original site or collection context to
samples, observations and dating evidence. These lists use the shared Atlas
search, reader and pagination.

The original public snapshot includes 12,598,201 observations, 1,069,197
samples, 994,319 analysis units, 62,624 datasets, 45,553 collection units,
32,061 sites, 45,448 age models, 415,615 chronology controls, 52,381 dating
measurements and 2,567,231 sample-age assignments. Scientific dictionaries,
taxa, publications and original identity links are also included. The
20,447,331 scientific rows describe different quantities; modern surfaces,
cores, animal middens and excavations retain their recorded methods.

An observation retains its original value, variable, unit, taxon or measured
parameter, preparation notes and uncertainties. Presence/absence is distinct
from specimen counts. **Sample age assignments** shows every original model,
age type, default flag and bound. A model range remains a range when its
central age is unknown; infinite dating measurements remain greater-than
results. Dating measurements and chronology controls are separate evidence.
Original source fields and specialist details start closed.

Published points, bounding areas and collection GPS fields remain unchanged.
Some rectangles intentionally obscure a site's position and are not centred
on it. Site-area documentation differs between Neotoma's schema and DataBUS;
original values remain unchanged without unit conversion. Original publication
citations, constituent databases, investigator names and DOI records accompany
the evidence. Contact phone, fax, email, address and contact notes are omitted
from the product; scientific attribution remains.

Source: [Neotoma public snapshot](https://www.neotomadb.org/data/db-snapshots),
5 October 2026, under its [CC BY 4.0 data policy](https://www.neotomadb.org/data/data-use-and-embargo-policy).
Source IDs establish associations within this snapshot; similar names do not
establish matches to other collections. Downloading this optional pack requires
Clovis 0.14 or newer. All installed reference searches work offline.

## Storage, updates and offline transfers

Collections live in **`~/Clovis Local/packs`**, separately from the application,
browser fieldbook and local dig-record database. Downloads resume after an
interruption. The published archive and every expanded file must match their
checksums; database integrity, schema, row counts and relationships are checked
before activation. Failed downloads leave installed collections and dig records
intact. Repairs preserve damaged files; updates retain earlier snapshots.

For an offline transfer, download the official ZIP using its collection card's
source/release links, copy it to the computer, then install it with the app's
Python environment:

```sh
python -m core.data_packs list
python -m core.data_packs install radiocarbon-world --archive clovis-radiocarbon-world-2025.07.zip
python -m core.data_packs install dinosaur-sites --archive clovis-dinosaur-sites-2026.09.20.zip
python -m core.data_packs install neolithic-assemblages --archive clovis-neolithic-assemblages-2015.07.zip
python -m core.data_packs install excavations-surveys --archive clovis-excavations-surveys-2026.10.08.zip
python -m core.data_packs install dated-environments --archive clovis-dated-environments-2026.10.05.zip
python -m core.data_packs install anatolian-zooarchaeology --archive clovis-anatolian-zooarchaeology-2026.10.09.zip
python -m core.data_packs install excavation-assemblages --archive clovis-excavation-assemblages-2026.10.09.zip
```

Use the exact official archive; unpacked or edited databases are not accepted.
Saved references preserve source context and do not inherit the selected town.
Pack removal and automatic scheduled updates are not supplied in this edition.
