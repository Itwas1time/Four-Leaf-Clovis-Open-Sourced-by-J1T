# four.leaf.clovis — explore places and plan research

Clovis helps residents explore what historical objects, fossils and geological
materials might be present around a U.S. town. It also helps research teams
review published archaeological projects and export source-linked briefs.
This public edition contains reviewed code, a public town lookup and a
coordinate-free archaeological directory.

## What works here

- **Explore a town.** Choose a state, town and known land-use context.
  Explore conditional historical object types, optionally request live regional
  geology, and download a source-linked context report. No address is required.
- **Start in any state.** Reviewed statewide mineral learning examples and
  sources appear immediately for all 50 states, DC and Puerto Rico. These are
  background, not claims about a deposit in a yard.
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

```sh
git clone https://github.com/Itwas1time/four.leaf.clovis.git
cd four.leaf.clovis
git switch clovis-handoff-2026-10-05
python -m venv .venv
# Activate .venv using your shell's normal command.
python -m pip install .
python -m atlas.gui.app
```

The Dash app binds to localhost at port 8050. Start with **Explore a town**:
select a state and town, choose known past land use, then select
**Explore this town**. Click the town box and type in its search field:
`Santa Rosa`, `Santa Rosa, CA` and `Santa Rosa, California` all work.
**Include local rock maps (online)** is selected by default; uncheck for an
offline report. The lookup runs only when Explore is pressed. Read the
**At a glance** summary, inspect the sources and download the report.
**A little curiosity, Dig deeper.**
Use **Research projects** for the directory and research briefs.
Its **Move the research map** search accepts towns as well as regions and
projects. It moves the map; use Explore a town for a resident report.

The light workspace adapts to mobile screens. Switch between Terrain,
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
The town workflow needs no API key. Its online option sends only a public
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

This public edition contains runtime source, user documentation, installation
metadata, public Census town points and a coordinate-free directory. Keep
credentials, personal details, sensitive locations and acquired datasets out
of Git. Software licensing is separate from third-party data rights.
See [security](SECURITY.md) and
[setup](docs/SETUP.md).
