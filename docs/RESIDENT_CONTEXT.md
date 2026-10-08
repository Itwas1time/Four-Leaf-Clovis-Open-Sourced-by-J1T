> **Public edition:** public Census town points are bundled as spatial context; archaeological/fossil locations are not. See the [README](../README.md). Other datasets described below are optional and are not bundled.

# What might be here?

The integrated workbench adds selectable geological evidence, an in-app
historical-map viewer and saved guided investigations. Start with the
[workbench guide](WORKBENCH.md) for the current step-by-step workflow.

Clovis helps residents explore historical objects, fossils and geological
materials in a U.S. town's context. It is a starting point for local research
and identification. It does not identify a deposit in a yard, choose a dig
location, determine collection rights or estimate a discovery probability.

## Try it

1. Start the Dash app with `python -m atlas.gui.app`.
2. Select **Explore a town**, a state and a town or Census place. Type a
   town name in the dropdown's search field to narrow the list; each search
   shows up to 30 results. `Santa Rosa, CA` and `Santa Rosa, California` work too.
   Selecting a state immediately shows reviewed statewide background and sources.
   **Choose town** in the header or field-notes panel opens the same editable
   selector on the left; it remains available from other workflows too.
3. Choose the land-use history you know. This selection remains explicitly
   user-reported; the app does not verify a building or former farm.
4. **Include local rock maps (online)** is selected by default. Uncheck it for
   an offline report, or leave it selected and press **Explore this town**
   at the top of **Your field notes**. Selecting a town moves the map and
   enables Explore; it does not build the report automatically.
   No geology request runs until you press Explore.
5. Open geological cards in **Local evidence**, search and inspect sheets in
   **Historical maps**, or start a guided task in **Investigations**. Save your
   sourced observations to the fieldbook. The right panel retains downloadable
   full notes. Changing an input invalidates the previous report and download.


The report begins with **At a glance**, including the names of actual returned
map units or a clear provider-status message. **What the maps describe** shows
the first three returned units' materials, intervals and bounded original
description excerpts before the research checklist. Full notes retain all
units and original references. Statewide background folds away when a town
is selected so it cannot be mistaken for the town's results.
Every state, DC and Puerto Rico
has reviewed statewide background, including sources for further learning.
State mineral-industry examples are not a list of collectible rocks or an
inference about deposits at the selected town. Broad fossil examples are
learning topics, with missing reviewed coverage made explicit.
Short definitions linked to the [USGS glossary](https://water.usgs.gov/water-basics_glossary.html)
explain selected map wording such as alluvium, sedimentary rock and shale.
They explain terms in map names and materials, without identifying specimens.

The built-in historical-map tool searches Library of Congress and displays
record sheets inside Clovis. It has zoom, drag, rotation and browser-local
image viewing. Search relevance and digitization do not establish coverage,
rights or a property match. Source links retain provenance and rights details;
the report also includes external USGS MapView for further map research.
Record a source, date and visible clues in a guided investigation.


The offline report explains conditional object types and research gaps. The
online option adds original map-unit descriptions and references from
Macrostrat at the place's public representative point. Overlapping regional
maps are not independent observations or a vertical soil profile. Even a
correct town-scale map may differ from the soil or imported fill in a yard.
Fossil mentions are presented as wording to inspect, not verified local finds.
No fossil taxon is inferred from rock age alone.
Eight reviewed guides add published fossil examples only when a returned map
names Grant Lake (OH/KY), Green River (WY/CO/UT), Morrison (selected western
states), Hell Creek (ND/SD), Cedar Valley (IA), Ohio Shale (OH), Lockport (NY)
or Casselman (PA). They cite original USGS, NPS and state sources, contain no specimen
locations and do not confirm a fossil on a property. Other formations have
explicitly missing guide coverage; this is not a national fossil inventory.

Choose **Research projects** for the directory, published projects,
project briefs and study-area tools. Those tools remain separate from a
resident's town report.
**Move the research map** searches public towns, states, regions and project
areas; choosing a result moves the map. Switch to Explore a town to build a
resident report.

## Likelihood

Every current resident report states **likelihood cannot be estimated**. The
app has no connected representative backyard survey recording comparable
methods, area, depth, positive outcomes and negative outcomes. Nearby records,
map units and land-use selections cannot supply that denominator. Missing
records are not evidence of absence. A future rate needs population definition,
provenance, sampling review and validation on held-out outcomes before being
shown as a predictive probability.

## Data rights and provenance

- **USGS state mineral-industry overviews and NPS fossil learning guide.**
  Authored selections in `core/state_context.py` cover all 50 states, DC and
  Puerto Rico. Fifty-one linked [USGS state overviews](https://www.usgs.gov/centers/national-minerals-information-center/state-minerals-statistics-and-information)
  supply mineral examples for the states and Puerto Rico; DC has research
  starting links. Sources were reviewed 7 October 2026. The industry pages
  describe different historical reporting periods; these are selected learning
  examples, not current production statistics or a complete mineral inventory.
  Delaware's overview describes crushed stone sold from out-of-state quarries,
  so that commodity is deliberately excluded from its derived examples.
  The [NPS fossil guide](https://www.nps.gov/subjects/fossils/official-state-fossils.htm),
  updated 13 August 2024, supplies broad organism categories where covered.
  Clovis does not assert current official state designations or a complete
  fossil inventory. Each record stores its source, review date and optional
  geological-survey organization link. No original page text, photographs,
  personal contacts, specimen records or find coordinates are bundled.
- **U.S. Census Bureau, 2026 National Places Gazetteer.**
  [Source and scope](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html),
  [source ZIP](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/2026_Gaz_place_national.zip),
  [public-data policy](https://www.census.gov/topics/research/research-transparency-public-access/open-data.html),
  [copyright policy](https://www2.census.gov/foia/ds_policies/ds027.pdf).
  Retrieved 7 October 2026. Source ZIP SHA256:
  `af678e2d990827c89ee39b98c82de6e90b693c7361ff0e559ae3076670dd2863`.
  The derived CSV contains 32,363 place codes, state abbreviations, names and
  representative points; other columns are omitted. Its SHA256 is
  `c6297f45453e00a2d70b9e32a490d4717c8a9adb8bb808098ed69fe201b5d062`.
  It covers the 50 states, DC and Puerto Rico; other Island Areas and locations
  outside Census places are not included. These are public geographic facts,
  with no household, user or archaeological locations. Census employee works
  generally have no U.S. copyright protection; other jurisdictions and third
  party works may differ. Attribute Census as the original data provider.
- **Macrostrat v2 geologic map service.** Optional live data under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), per its
  [official service documentation](https://dev.macrostrat.org/docs/data-services).
  Responses must declare that license and supply original map references.
  Clovis retains map/source IDs and references for each unit, labels shortened
  descriptions as excerpts and attributes Macrostrat and the original maps.
  Original provider map comments are retained as bounded excerpts. Map labels
  can be geographically surprising or reflect broad maps; check the original
  legend and scope. A successful response is not a check of local map accuracy.
  Its interpretations are authored separately. Provider data is not bundled.
- The NPS [artifact recognition guide](https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm)
  and [fossil background](https://www.nps.gov/subjects/fossils/what-is-a-fossil.htm)
  support general examples. They establish neither occurrence nor legal
  permission on an individual property. Clovis links to them and uses authored
  summaries; no source photographs or specimen records are copied.
- Authored formation summaries cite [USGS Grant Lake](https://ngmdb.usgs.gov/Geolex/UnitRefs/GrantLakeRefs_1858.html),
  [USGS Green River](https://ngmdb.usgs.gov/Geolex/UnitRefs/GreenRiverRefs_8483.html)
  and [NPS Morrison](https://www.nps.gov/subjects/fossils/the-morrison-formation.htm).
  Checked 7 October 2026. No underlying publication or specimen dataset is copied.
- Added guides cite [USGS Hell Creek research](https://www.usgs.gov/publications/vertebrate-biostratigraphy-hell-creek-formation-southwestern-north-dakota-and),
  [Iowa DNR Cedar Valley context](https://www.iowadnr.gov/places-go/state-preserves/merrill-s-stainbrook-state-preserve),
  [USGS Ohio Shale paleontology](https://www.usgs.gov/geology-and-ecology-of-national-parks/geology-cuyahoga-valley-national-park),
  [USGS Lockport coral research](https://pubs.usgs.gov/publication/pp414G)
  and [Lockport stratigraphic scope](https://ngmdb.usgs.gov/Geolex/UnitRefs/EramosaRefs_1556.html),
  and Pennsylvania Geology, Summer/Fall 1998, “Problematic Tracks in the
  Casselman Formation of Cambria County.” Summaries retain bed variation and
  unidentified track-maker limits. Source locations and collection directions
  are not copied. Checked 7 October 2026.

The lookup is a fixed, reviewed Census snapshot. Data updates require a
fresh provenance review. The application's MIT license does not change
external data terms.

## Privacy and request bounds

The resident form has no address, personal name, free-text notes or arbitrary
URL field. The online option sends a Census town point to a fixed HTTPS
Macrostrat endpoint. Network metadata is visible to that provider. External
map tiles and styles have their own providers. Tile images send only the
application origin as a referrer, without a page path or query. Other outbound
links retain the app's `no-referrer` policy. Search text is handled locally.
The background map has a provider selector and an outage notice; town lookup
and offline report generation remain available if tiles cannot load.

No resident report or provider response is written to disk by the app. Memory
caches hold at most 128 reports and 128 public town responses; downloads expire
after an hour. Restarting clears memory. Failed requests are cached briefly.
Downloads are saved only if requested by the user. HTTP requests have a
timeout, response size limit and redirect prohibition. A nonblocking gate
prevents concurrent external request queues. Browser exports refer to a random
server-owned report token and must match its original inputs. A changed,
expired, guessed or malformed token cannot provide an old report download.

The maintained server binds to loopback. This feature does not make it a
multi-user internet deployment; deployment controls are described in
[SECURITY.md](../SECURITY.md).
