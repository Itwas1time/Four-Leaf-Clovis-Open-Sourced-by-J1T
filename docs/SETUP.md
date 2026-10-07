# Local setup

The maintained interface is the Dash place-context and research planner.
Python 3.11 or newer is required. The town lookup, directory and planner need
no API keys. Regional geology is an optional online request.

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

Select a state, type a town name and choose a Census place. Choose the past
land use you know, optionally enable regional geology, then select
**Explore this town**. Read or download the report. No address is required.
The report explains conditional historical object types, mapped rock context,
limited formation-specific fossil examples and evidence still needed.
Discovery likelihood cannot currently be estimated. A town point is not an
individual yard or a vertical soil profile. See [resident context and data
rights](RESIDENT_CONTEXT.md) and the [Cincinnati example](examples/cincinnati-town-context.md).

Choose **Research projects and areas** for the directory and project briefs.
Town searches, directory searches and report generation work locally; the
geology option and map tiles/styles require internet access. Changing report
inputs invalidates the previous download.

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
