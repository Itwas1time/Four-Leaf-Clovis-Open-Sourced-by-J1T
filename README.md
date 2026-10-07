# four.leaf.clovis — archaeological research planner

Clovis helps research teams review published archaeological projects, organize
questions and partner/permit checks, and export research briefs. This public
edition contains reviewed source code and a coordinate-free public directory.

## What works here

- Ten sourced project leads, their support routes, institutions, and jurisdiction starting links.
- Coordinate-free public directory records from Wikidata and authored researched project pages.
- Brief previews/downloads and input/security validation.
- Broad project-region navigation, capped at zoom 9, with no archaeological pin search index.
- Area geometry and candidate schema handling, with explicit missing evidence.
- Comparison of up to 25 study areas using sourced, user-supplied observations.
  An ordinal index requires two distinct evidence kinds and sources, including
  prior survey evidence. Strengths are unverified judgments; the index has no
  demonstrated predictive accuracy and is not a discovery probability.

**No spatial source datasets are bundled.** Raw/processed archaeology and fossil
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

The Dash app binds to localhost at port 8050. Map tiles and external style
assets need network access; public directory searches and brief generation
use the bundled coordinate-free snapshot. Public hosting needs a separate
deployment review; this package has no authentication or multi-user design.
Optional API keys belong in private environment/config files, never Git.

## Sources and publication status

Wikidata structured records are [CC0](https://www.wikidata.org/wiki/Wikidata:Licensing).
The directory contains public names, countries/regions, IDs, and source links;
it does not grant excavation rights, data rights in external sources, or an
institutional partnership. Project descriptions have source links and dated
checks; verify seasons, permission, and support terms before acting. Source
documentation retained under `docs/` has a scope banner where it describes
optional datasets that are absent from this edition.

This public edition contains runtime source, user documentation, installation
manifests, and the reviewed directory. Keep acquired datasets, coordinates,
credentials, raw responses, screenshots, and local environment files private.
Software licensing is separate from third-party data rights. See
[security](SECURITY.md) and [setup](docs/SETUP.md).
