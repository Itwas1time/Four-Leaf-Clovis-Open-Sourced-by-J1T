# Local setup

The maintained interface is the Dash research planner. Python 3.11 or newer is
required. The local directory and planner need no API keys.

```sh
git clone https://github.com/Itwas1time/four.leaf.clovis.git
cd four.leaf.clovis
git switch clovis-handoff-2026-10-05
python -m venv .venv
# Activate .venv for your shell, or use its Python executable directly.
python -m pip install .
python -m atlas.gui.app
```

On Windows the environment's Python is `.venv\Scripts\python.exe`; on Linux
and macOS it is `.venv/bin/python`. Open `http://127.0.0.1:8050`; stop with Ctrl+C.
Another loopback port is available with `archaeo serve --host 127.0.0.1 --port 8055`.
Keep debug disabled and the server local. See [SECURITY.md](../SECURITY.md).

## Program limits

No spatial source datasets are bundled. Unsupported areas remain unranked;
empty results indicate missing evidence, not an absence of archaeology.
Candidate uploads accept 1–25 areas, at most 1 MB of JSON, and at most 100
observations per candidate. Drawings accept 25 shapes and 5,000 total vertices,
with review buffers from 0 to 5 km. Exported briefs contain source links.

Optional collectors use private environment/configuration files based on
`.env.example` or `tools/config.example.json`. Obtain source permissions and
review sensitivity and redistribution rights before importing or sharing data.
The experimental citizen API keeps at most 500 reports in memory. Photo
classification is off by default; enabling it sends approved image bytes to
the configured model provider and requires consent. Rounded displays do not
guarantee anonymity.

## Separate experimental frontend

The MapLibre frontend is separate from the maintained Dash planner and contains
no bundled site demo. Its Node dependencies and build command are retained for
running that interface:

```sh
npm ci --ignore-scripts --prefix atlas/frontend
npm run build --prefix atlas/frontend
```

Map tiles and external styles can require internet access. Keep local servers
on loopback; this edition has no authentication or multi-user access controls.
