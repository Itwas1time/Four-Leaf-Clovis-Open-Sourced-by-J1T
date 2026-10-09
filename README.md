# four.leaf.clovis — explore places and plan research

<img src="atlas/gui/assets/clovis-bone-clover.svg" alt="Clovis four-leaf clover formed from bones" width="72" height="72">

**A little curiosity, Dig deeper.**

Clovis helps residents explore what historical objects, fossils and geological
materials might be present around a U.S. town. It also helps research teams
review published archaeological projects and export source-linked briefs.
This edition contains dated historical maps, museum reference collections,
state fossil chapters, a public town lookup and a coordinate-free research directory.

## What works here

- **Explore a town.** Choose a state, town and known land-use context.
  Explore conditional historical object types, optionally request live regional
  geology, and download a source-linked context report. No address is required.
- **Start in any state.** Expand Statewide background and sources for reviewed
  mineral learning examples across all 50 states, DC and Puerto Rico. These are
  background, not claims about a deposit in a yard.
- **Read historical records.** Browse 50,578 Sanborn atlas records under 9,758
  town/state names across all 50 states and DC, with dated catalog citations,
  chronological pages and an in-app sheet viewer. Catalog searches work offline.
- **Compare museum references.** Search 563,454 source objects from the Met and
  Smithsonian in **Atlas**. Read materials, dates, cultures, labeled dimensions
  and catalog numbers where recorded. Request eligible Met reference photographs
  and save a sourced comparison to the fieldbook. State fossil chapters supply
  three cited facts for every state, DC and Puerto Rico.
- **Read mineral properties.** Search 6,381 Wikidata mineral records with 43,922
  source statements in **Atlas → Specialist searches → Mineral properties**. Read formulas,
  hardness, density and crystal-system claims with original units, qualifiers
  and sources; save a reference to Fieldbook without attaching a town.
- **Take a next step.** The dashboard marks the public town point. Open
  **Read rock evidence · materials, ages & sources** below the Rocks & fossils
  map for unit cards, source details and matched formation guides. Historical
  maps and guided investigations help turn a source into written observations.
  Expand the full field notes for map descriptions, sources and limits.
- **Inspect a find.** Record visible features, size and context for glass,
  ceramics, metal, rocks, possible fossils or bone. Get comparison questions
  and a browser-local photo viewer with zoom, drag, rotation, fit and removal.
  There is no image analysis or automatic identification.
- **Keep a fieldbook.** Save reports and observations, compare two investigations,
  add dated follow-ups after checking maps, and print selected notes. Export or
  restore JSON to move devices; restoring preserves saved work.
- **Ask a clearer question.** Preview, download or save a question packet about
  saved notes. Record an attributed response separately and navigate related
  records, with the original observations and sources preserved. No message is sent.
- Eight sourced fossil guides match named units in reviewed states, including
  Ohio Shale, Cedar Valley, Hell Creek, Lockport and Casselman. These are learning
  examples in documented beds, not yard occurrences or collecting destinations.
- Offline lookup of 32,363 public Census places across the 50 states, DC and Puerto Rico.
- Optional Macrostrat map units with original references and CC BY 4.0 attribution.
  Maps describe a public town point, not an individual yard or vertical soil profile.
- Clear evidence gaps: **discovery likelihood cannot currently be estimated**.
  There is no connected representative survey dataset; no percentages are invented.
- Ten sourced project leads, their support routes, institutions, and jurisdiction starting links.
- Coordinate-free public directory records from Wikidata and authored researched project pages.
- Brief previews/downloads and input/security validation.
- Broad project-region navigation, capped at zoom 9, with no archaeological pin search index.
- Area geometry and candidate schema handling, with explicit missing evidence.
- Comparison of up to 25 study areas using sourced, user-supplied observations.
  An ordinal index requires two distinct evidence kinds and sources, including
  prior survey evidence. Strengths are unverified judgments; the index has no
  demonstrated predictive accuracy and is not a discovery probability.

**No archaeological or fossil location datasets are bundled.** Raw/processed archaeology and fossil
records, Google geocodes, Native Land/boundary polygons, environmental data,
embedded site datasets, and old QA traces/screenshots are excluded. The NRHP
portion of the public directory is also excluded. The legacy frontend's demo
returns empty collections. Broad authored navigation defaults are not an archaeological inventory.

Drawn-area review therefore shows no bundled known sites, finds, tribal data,
or research ranking. An empty result means missing local data, not that an area
lacks archaeology. Import independently rights-cleared, sensitivity-reviewed
local data and documented observations before meaningful AOI review. Do not
restore withheld locations using guessed geocodes or publish restricted data.

## Run locally

Python 3.11 or newer is required.

**Fieldbook → Dig records** keeps named local projects with linked units,
contexts, finds, samples and source documents. Preserve depth units and datums,
bag identifiers, explicit context relationships and dated corrections. Download
a project ZIP backup with its full history; restore checks links and refuses
conflicting revisions. See [dig records](docs/DIG_RECORDS.md) for storage and bounds.

**Atlas → Manage offline collections** adds optional local downloads: **173,946
published radiocarbon determinations** (17.7 MB) and **37,852 dinosaur fossil
occurrences linked to 14,371 collections** (27.8 MB), **96,115 UCL EUROEVOL
source rows** (17.0 MB) linking sites and occupation phases to animal remains,
plants, measurements, dating samples and recovery methods, and **153,867
excavation and survey source records** (243.2 MB) from Gabii, Petra and Eastern
Korinthia. Follow recorded deposits, finds and samples in the same Atlas reader;
read original recovery conditions, survey effort, field meanings and units.
Search materials, methods,
uncertainty, taxonomy, sites and original references. Read source location
precision and save attributed references. See [collections](docs/DATA_COLLECTIONS.md)
for coverage, reuse rights, original units and offline installation.

```sh
git clone https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T.git four.leaf.clovis
cd four.leaf.clovis
git switch clovis-handoff-2026-10-05
python -m venv .venv
# Activate .venv using your shell's normal command.
python -m pip install .
python -m atlas.gui.app
```

The Dash app binds to localhost at port 8050. **Explore** opens on **Atlas**,
with one search and a shared reader across **1,652,762 source records** when
all four optional packs are installed. Search published places, cultures,
materials or fossils and follow the original source. **Specialist searches**
keeps detailed collection filters available. Counts mix different record types
and can overlap between sources; they do not count unique excavated finds.

For local map research, choose **Rocks & fossils** or **Choose town**:
select a state and town, then select
**Explore this town** directly below the town box. Selecting a town
moves the map and enables Explore; press it to build the report. **Choose
town** in the header or notes panel opens the same editable place selector.
Click the town box and type in its search field:
`Santa Rosa`, `Santa Rosa, CA` and `Santa Rosa, California` all work.
Open **Options & land-use context** for known past land use and the online setting.
**Include local rock maps (online)** is selected by default; uncheck for an
offline report. The lookup runs only when Explore is pressed. The central
workbench has **Rocks & fossils**, **Old maps**, **Investigation** and **Atlas**. The Rocks &
fossils map fills the center. Open **Read rock evidence · materials, ages &
sources** below it to read and select unit cards, source details and matched
formation guides. This drawer starts closed and contains **Map overlay &
sources**. **Words in this source** explains reviewed materials and ages beside
the selected unit. Open **Rock words & geological time** to search definitions
and relative age order without an online lookup. Definitions do not identify a
loose object or predict a find. Read a unit's source, then use its investigation action to carry the
source and interval into written notes. Inspect Library of Congress map sheets
with built-in zoom/drag/rotation, then record a sourced,
dated investigation and save it to **Fieldbook**. The compact **Try an example**
action randomly picks one of 100 public-town questions across all 50 states.
After a click, the question appears as a compact summary with instructions
closed; click the question to read them. Dismissing the example keeps your town
and report.
The header **Dark / Light** toggle remembers this browser's preference while
images retain their colours and printed notes remain light. Local map images stay
in the browser. Source links support attribution and further research.
Library searches use the bundled museum records. Choose a collection, enter a
term, then select a record. The Met has object-group and recorded-date filters;
Smithsonian tags derive from source titles and object types and its snapshot
has no explicit object dates or CC0 media. **Load reference photograph** is an
explicit online action. Museum references save without a town or attached image.
See the [workbench guide](docs/WORKBENCH.md) for a practical walkthrough.
Use **Inspect a find** for an already exposed object. Selected features produce
specific observation question cards first in the center. **Record this detail**
returns to your notes; full comparison notes and sources open on request.
Zoom, drag, rotate, fit or remove a local photo without changing its original
file. Save/download actions sit above the cards, with jump links for small
screens. Including the selected public town
is optional; changing town clears that choice. Use **Fieldbook** to return to
written notes. Select a record to **Prepare a question about these notes**;
preview the packet before downloading or saving. On a saved question, **Record
a response to this question** with its source, date and remaining uncertainty.
Related saved records connect the source, question and responses. The new
question or response leads readers and note downloads; preserved source notes
follow. Photos are not attached and Clovis contacts nobody.
Saved entries stay in this browser; export a backup.
Print or save selected notes as PDF using the browser's print dialog.
See [observations and fieldbook](docs/OBSERVATIONS.md) for a practical walkthrough
and privacy details. Photos stay in the browser and are not saved or analyzed.
Use **Research** for the directory and research briefs.
Its **Move the research map** search accepts towns as well as regions and
projects. It moves the map; use Explore a town for a resident report.

The archaeology field-notebook theme uses warm paper, archival ink, olive
controls and readable serif headings, with a bone-clover vector mark in the
header and browser tab, and adapts to mobile screens. Switch between Terrain,
Topographic and Satellite above the map. Background maps need internet access;
local reports remain available during a tile outage. Map images send only the
app origin as a referrer. Terrain uses Stadia's local development access;
hosting requires provider authorization. See [setup](docs/SETUP.md).
See the [resident workflow and data provenance](docs/RESIDENT_CONTEXT.md).
An [actual demonstration report](docs/examples/cincinnati-town-context.md)
uses Cincinnati's public town point and a hypothetical older-building history.

Map tiles and external style
assets need network access; public directory searches and brief generation
use the bundled coordinate-free snapshot. Public hosting needs a separate
deployment review; this package has no authentication or multi-user design.
Optional API keys belong in private environment/config files, never Git.
The town workflow and offline catalogs need no API key. Optional reference
photographs send a public museum object ID to the Met API and load an eligible
image from its host; local notes, town choices and photographs are not sent.
The town online option sends only a public
Census town point to Macrostrat. Reports and provider responses stay in bounded
server memory; the app does not write them to disk. Input changes invalidate
downloads, and server-owned report tokens expire after an hour.

## Sources and publication status

Wikidata structured records are [CC0](https://www.wikidata.org/wiki/Wikidata:Licensing).
The directory contains public names, countries/regions, IDs, and source links;
it does not grant excavation rights, data rights in external sources, or an
institutional partnership. Project descriptions have source links and dated
checks; verify seasons, permission, and support terms before acting. Source
documentation retained under `docs/` has a scope banner where it describes
optional datasets that are absent from this edition.

The [Sanborn source notes](docs/SANBORN_SOURCES.md),
[Met source notes](docs/OBJECT_REFERENCE_SOURCES.md),
[Smithsonian source notes](docs/SMITHSONIAN_REFERENCE_SOURCES.md), and
[state fossil sources](docs/STATE_FOSSIL_SOURCES.md) document the bundled
snapshots, factual fields, reuse rights and selection. Museum metadata are CC0;
image rights are checked separately. Sanborn catalog metadata and the LOC
collection are public domain. Searchable reference databases currently occupy
about 1.84 GB before compression; images and raw source downloads are not bundled.

**Archaeological projects** in Library reads 203
Open Context data publications. Search titles, creators, subjects and short
source descriptions, then save attributed metadata to Fieldbook. Archaeological
time coverage and publication dates are labeled separately. The full 204-record
publisher query was checked; unsupported reuse licenses are excluded. This is
one publisher's catalog, not a census of digs. See
[archaeology source and license notes](docs/ARCHAEOLOGY_PROJECT_SOURCES.md).

This public edition contains runtime source, user documentation, installation
metadata, public Census town points and reviewed reference catalogs. Keep
credentials, personal details, sensitive locations and acquired datasets out
of Git. Software licensing is separate from third-party data rights.
See [security](SECURITY.md) and
[setup](docs/SETUP.md).
