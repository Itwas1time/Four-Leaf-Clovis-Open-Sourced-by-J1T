> **Public edition:** public Census town points are bundled as spatial context; archaeological/fossil locations are not. See the [README](../README.md). Other datasets described below are optional and are not bundled.

# What might be here?

Clovis helps residents explore historical objects, fossils and geological
materials in a U.S. town's context. It is a starting point for local research
and identification. It does not identify a deposit in a yard, choose a dig
location, determine collection rights or estimate a discovery probability.

## Try it

1. Start the Dash app with `python -m atlas.gui.app`.
2. Select **What might be here?**, a state and a town or Census place. Type a
   town name to narrow the list; each search shows up to 30 results.
3. Choose the land-use history you know. This selection remains explicitly
   user-reported; the app does not verify a building or former farm.
4. Optionally request regional geology, then select **Explore this town**.
5. Read the report and download its Markdown copy. Changing an input clears
   the previous preview and disables its download until a new report is built.

The offline report explains conditional object types and research gaps. The
online option adds original map-unit descriptions and references from
Macrostrat at the place's public representative point. Overlapping regional
maps are not independent observations or a vertical soil profile. Even a
correct town-scale map may differ from the soil or imported fill in a yard.
Fossil mentions are presented as wording to inspect, not verified local finds.
No fossil taxon is inferred from rock age alone.
Three reviewed formation guides add published fossil examples only when a
returned map names Grant Lake (OH/KY), Green River (WY/CO/UT) or Morrison
(selected western states). They cite USGS Geolex or NPS, contain no specimen
locations and do not confirm a fossil on a property. Other formations have
explicitly missing guide coverage; this is not a national fossil inventory.

Choose **Research projects and areas** for the directory, published projects,
project briefs and study-area tools. Those tools remain separate from a
resident's town report.

## Likelihood

Every current resident report states **likelihood cannot be estimated**. The
app has no connected representative backyard survey recording comparable
methods, area, depth, positive outcomes and negative outcomes. Nearby records,
map units and land-use selections cannot supply that denominator. Missing
records are not evidence of absence. A future rate needs population definition,
provenance, sampling review and validation on held-out outcomes before being
shown as a predictive probability.

## Data rights and provenance

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

The lookup is a fixed, reviewed Census snapshot. Data updates require a
fresh provenance review. The application's MIT license does not change
external data terms.

## Privacy and request bounds

The resident form has no address, personal name, free-text notes or arbitrary
URL field. The online option sends a Census town point to a fixed HTTPS
Macrostrat endpoint. Network metadata is visible to that provider. External
map tiles and styles have their own providers. Search text is handled locally.

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
