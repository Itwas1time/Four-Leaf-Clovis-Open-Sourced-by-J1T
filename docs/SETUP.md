# Local setup

The maintained interface is the Dash place-context and research planner.
Python 3.11 or newer is required. The town lookup, directory and planner need
no API keys. Local rock maps are selected by default; the online request runs
only when Explore is pressed. Uncheck the option for an offline report.

## Windows PowerShell

```powershell
git clone https://github.com/Itwas1time/four.leaf.clovis.git
Set-Location four.leaf.clovis
git switch clovis-handoff-2026-10-05
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install .
& .\.venv\Scripts\python.exe -m atlas.gui.app
```

Use the environment's Python directly; no execution-policy change is needed.

## macOS or Linux

```sh
git clone https://github.com/Itwas1time/four.leaf.clovis.git
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
the optional past land use and online setting. Leave **Include local rock maps (online)** selected for map
evidence or uncheck for an offline report, then select
**Explore this town**. A marker shows the public Census town point. The central workbench has
**Rocks & fossils**, **Old maps** and **Investigation**. The Rocks & fossils map
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

## Observe, save and return

Choose **Inspect a find** to describe an already exposed object. Select visible
features, record size and context, and read the feature-specific questions in the
center. The links beside the form and guide let you jump between them on a small
screen. Save or download actions sit above the guide. You can explicitly include
the selected public town as broad context; changing town clears that choice.
An optional photo stays in the browser; it is not sent to the server, analyzed or
saved. Save the written notes, or save a report from **Explore a town**.

In **Fieldbook**, open a card and choose another investigation to compare.
Add a follow-up after checking a map: record its title, date, sheet and source,
plus what you observed. A dated entry preserves the original. Print selected
notes or use the browser's Save as PDF option. Download JSON to back up the
fieldbook or move devices; Restore merges valid notes with existing work.
Limits are 50 entries and 750 KB. Browser storage is specific to the device
and app origin. See [observations and fieldbook](OBSERVATIONS.md).

## Background maps

Use Terrain, Topographic or Satellite above the map. Terrain uses Stadia's
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
