# Local setup

The maintained interface is the Dash place-context and research planner.
Python 3.11 or newer is required. The town lookup, directory and planner need
no API keys. The app opens on Atlas search. Town reports start with online
rock maps off; select the option when wanted. The online request runs only
when Explore is pressed. The map starts offline, with a world land outline
and regional U.S. county outlines and public town labels. **Show regional view**
recovers county context after a close zoom. Streets and property detail are
not bundled. See [map sources and coverage](OFFLINE_MAP_SOURCES.md).

## Windows PowerShell

```powershell
git clone https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T.git four.leaf.clovis
Set-Location four.leaf.clovis
git switch clovis-handoff-2026-10-05
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install .
& .\.venv\Scripts\python.exe -m atlas.gui.app
```

Use the environment's Python directly; no execution-policy change is needed.

## macOS or Linux

```sh
git clone https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T.git four.leaf.clovis
cd four.leaf.clovis
git switch clovis-handoff-2026-10-05
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m atlas.gui.app
```

Open `http://127.0.0.1:8050`; stop with Ctrl+C. Another loopback port is available
with `archaeo serve --host 127.0.0.1 --port 8055`. Keep debug disabled and the
server local. See [security](../SECURITY.md).

## Explore a town

Select a state and expand **Statewide background and sources** for learning context.
Click the town box, type a town name in its search field and choose a Census
place. `Santa Rosa, CA` or `Santa Rosa, California` also works. Select **Explore
this town** directly below the town box. **Options & land-use context** contains
the optional past land use and online setting. **Include local rock maps (online)** starts off.
Select it for an online map lookup or keep it off for an offline report, then select
**Explore this town**. A marker shows the public Census town point. The central workbench has
**Rocks & fossils**, **Old maps**, **Investigation** and **Atlas**. The Rocks & fossils map
fills the center. Open **Read rock evidence · materials, ages & sources** below
it to read and select unit cards, source details and matched formation guides.
This drawer starts closed and contains **Map overlay & sources**. **Words in
this source** explains reviewed material and age terms beside the selected unit.
Open **Rock words & geological time** to search the offline guide, including
relative age order. These definitions do not identify a loose object or predict
a find. Read a unit's source, then use its investigation action to carry the source and interval into
written notes. Inspect Library of Congress map sheets inside Clovis, then save
sourced observations to the fieldbook. The
compact **Try an example** action randomly picks one of 100 town questions,
two distinct towns per state. After that click, the question appears as a compact
summary with instructions closed; click the question to read them. Dismissing
the example preserves your town and report. The header **Dark / Light** toggle remembers
your browser preference; images retain their colours and printing stays light. Source
links support attribution and rights. No address is required. See the
[workbench guide](WORKBENCH.md).
The report explains conditional historical object types, mapped rock context,
limited formation-specific fossil examples and evidence still needed.
Discovery likelihood cannot currently be estimated. A town point is not an
individual yard or a vertical soil profile. See [resident context and data
rights](RESIDENT_CONTEXT.md) and the [Cincinnati example](examples/cincinnati-town-context.md).

Choose **Research projects** for the directory and project briefs.
Its **Move the research map** search accepts towns, regions and project areas;
it moves the map and does not generate a resident report.
Town searches, directory searches and report generation work locally; the
geology option and map tiles/styles require internet access. Changing report
inputs invalidates the previous download.

## Read the reference catalogs

**Old maps** loads the offline dated Sanborn catalog for the selected town,
with an explicitly labeled state catalog if there is no exact town-name match.
Choose a date order, turn pages and read a record. **Load map sheets online**
requests digitized sheets; **Search more maps online** retains live LOC search.
Catalog-only records can supply a citation without claiming that a sheet was viewed.

**Atlas** opens on one search and a shared source reader without choosing a town.
Search places, cultures, materials or fossils, and follow each source's evidence.
Use optional evidence/source filters or expand **Specialist searches** for
collection-specific readers. In its Museum objects reader, choose the Met or Smithsonian collection,
search and select a record to read actual source fields. Met object groups and
date ranges filter museum records; Smithsonian text tags are labeled separately
from measured materials. Use **Load reference photograph** on an eligible Met
record. **Save reference to fieldbook** keeps its source, with no town or photo.
**Geology & fossils** supplies short cited chapters for all 50 states, DC and
Puerto Rico. See [the workbench guide](WORKBENCH.md) and the individual source notes.

## Observe, save and return

**Atlas → Manage offline collections** offers radiocarbon, dinosaur taxa and
sites, Neolithic assemblages, excavation and survey records, past environments,
Anatolian animal-bone records, and excavation assemblages and refits. Read
coverage, rights and storage sizes, then choose
**Download collection**. Downloads resume and verify before activation. Search
installed records locally and save attributed references. See
[downloadable collections](DATA_COLLECTIONS.md) for source conventions, storage,
updates and offline ZIP installation.

Choose **Inspect a find** to describe an already exposed object. Select visible
features, record size and context, and read the feature-specific question cards
first in the center. **Record this detail** focuses your notes without changing
them. Full comparison notes and sources open on request. The links beside the
form and cards let you jump between them on a small screen. Save or download
actions sit above the cards. You can explicitly include
the selected public town as broad context; changing town clears that choice.
Add and caption an original photo, then zoom, drag, rotate or fit it without
changing the file. The local app stores the original without analysis or
re-encoding. Save the observation and its photo references, or save a report
from **Explore a town**. Removing a working attachment preserves saved notes.

In **Fieldbook**, open a card and choose another investigation to compare.
Add a follow-up after checking a map: record its title, date, sheet and source,
plus what you observed. A dated entry preserves the original. To prepare a
question packet, open **Prepare a question about these notes**, write your
question, preview, then download or save it. On a saved question, **Record a
response to this question** with its source, date and remaining uncertainty.
Use **Related saved records** to navigate the source, question and responses.
Original notes and attached personal photos remain intact. A question packet
with photos downloads as readable Markdown and originals in a ZIP. Clovis sends
no messages. Print selected note text or use the browser's Save as PDF option.
Download the complete fieldbook as JSON for notes alone, or ZIP with original
photos. Restore merges valid notes and originals with existing work.
Limits are 50 entries / 750 KB of note metadata and 100 MB of original photos.
Browser storage is specific to the device
and app origin. See [observations and fieldbook](OBSERVATIONS.md).

For structured recording select **Fieldbook → Dig records**. Keep named local
projects, units, contexts, finds, samples and source documents connected.
Record measured depths with their units and datums, bag identifiers and
explicit context relationships. Corrections preserve stable IDs and dated
revisions. Project ZIP backups include the full history; restoring merges
matching revisions and refuses conflicts. Personal photos and captions remain
with dated revisions, including after removal from the current record. Complete
project backups retain those originals. These records persist on the local
computer outside the installed package. See [dig records](DIG_RECORDS.md) for
the storage path, limits and recording references.

Add **Sample measurement / processing** records linked to a saved sample to
record quantities, original units, mesh, fractions, methods and analysis status.
Keep zero results distinct from unknown amounts and unanalysed material.
Sample readers page through all linked observations. Projects using the new
record type have version 2 backups; older Clovis builds refuse the new database
format, and current Clovis retains older records without rewriting them.

In Atlas, expand **Use in a dig project**, choose a saved project and source
code, then **Save and open project source**. Its complete generated citation
remains readable after a collection is removed. Link and reopen the source from
supporting field records. Repeat saves keep your annotations; changed cited
content needs a separate record. Captured citations use version 3 project
backups. Photo-inclusive histories use version 4; the current build reads all
four project versions. See [photo portability](LOCAL_PHOTOS.md).

Atlas **Search ideas** offers related field terms when you type familiar words.
Choose a suggestion to replace the query while keeping the current evidence,
source and published association. **What these words mean** contains short
sourced explanations that work offline. These are separate text searches;
check the source's evidence type and original wording before interpreting a
match. See [downloadable collections](DATA_COLLECTIONS.md).

## Background maps

The bundled world outline works offline. Terrain, Topographic and Satellite
are explicit online choices above the map. Terrain uses Stadia's
localhost development access, with no key for `localhost` or `127.0.0.1`.
Tile images send only the app origin as a referrer, without a page path or
query, so the provider can recognize local access. The rest of the app keeps
its `no-referrer` policy. If tiles fail, a notice appears and local reports
remain usable. Hosted terrain maps require provider-authorized domain or
API-key configuration; see [Stadia authentication](https://docs.stadiamaps.com/authentication/).

## Program limits

Public Census town points are bundled; archaeological and fossil locations
are not. Unsupported study areas remain unranked. Empty results indicate
missing evidence, not an absence of archaeology. Candidate uploads accept
1–25 areas, at most 1 MB of JSON and at most 100 observations per candidate.
Drawings accept 25 shapes and 5,000 total vertices, with review buffers from
0 to 5 km. Exported briefs contain source links.

Optional collectors use private environment/configuration files based on
`.env.example` or `tools/config.example.json`. Obtain source permissions and
review sensitivity and redistribution rights before importing or sharing data.
The experimental citizen API keeps at most 500 reports in memory. Photo
classification is off by default; enabling it sends approved image bytes to
the configured model provider and requires consent. Rounded displays do not
guarantee anonymity.

## Separate experimental frontend

The MapLibre frontend is separate from the maintained Dash planner and contains
no bundled site demo. Its Node dependencies and build command are retained:

```sh
npm ci --ignore-scripts --prefix atlas/frontend
npm run build --prefix atlas/frontend
```

Keep local servers on loopback; this edition has no authentication or multi-user
access controls. Publishing this repository does not deploy an internet app.
