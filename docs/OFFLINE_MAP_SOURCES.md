> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Offline source location maps

The shared Atlas reader has an optional map within **Published location**.
Neotoma site bounds draw as an area, line or published point; deliberately
obscured areas receive no central site marker. Independent sites reached through
the dataset and analysis-unit paths remain separate. Collection-unit GPS is not
used to refine a published site area. Antimeridian areas retain their original
width. PBDB fossil occurrences use modern collection coordinates, with their
source basis, precision, scale and notes; paleocoordinates are not substituted.
Coordinates remain available in the original source fields.

The map is created only after **Show published location map**. It uses no
remote tiles. Invalid or absent coordinates are disclosed instead of geocoded.
The background is the original [Natural Earth 1:110 million land GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/ca96624a56bd078437bca8184e78163e5039ad19/geojson/ne_110m_land.geojson),
commit `ca96624a56bd078437bca8184e78163e5039ad19`, SHA-256
`9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9`.
Natural Earth is [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
This generalized modern outline provides orientation; it does not describe
ancient coastlines, excavation boundaries or local access. It can be zoomed and
panned while the attributed source shape remains visible.

Leaflet 1.9.4 styles and images are bundled from commit
`d15112c9e8ac339f0f74f563959d0423d291308d` under its BSD 2-Clause license.
Leaflet.draw 1.0.4 styles and sprites are bundled under its MIT license. Resource
URLs are rewritten to local asset names; no map-style CDN is required.
The original license notices, pinned upstream URLs and asset hashes are retained
in [offline-map-sources.json](../atlas/gui/assets/offline-map-sources.json).
The separate town/research map starts with this land outline and now adds
modern U.S. county/equivalent boundaries and public Census town labels at
regional scales. **Show regional view** returns from a close zoom to a useful
county view. Label density adapts to the map's shape, with room around the
selected public town point. No street or property detail is bundled.

The county layer retains all **3,235** original GEOIDs and attributes from the
[U.S. Census Bureau 2025 1:500,000 cartographic boundary edition](https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_500k.zip).
The original ZIP SHA-256 is
`aa976c00b181939755d0da757f4c7c2dc0103c3b3b4530fb2a91c2bb62fc777c`.
NAD83 (EPSG:4269) geometry is transformed to WGS 84 (EPSG:4326), rounded to six
display decimals and compressed by county in the bundled SQLite file. Only
features intersecting the current view are sent to the browser. Native
metadata permits reuse with U.S. Census Bureau acknowledgment, which appears
on the map. It limits use to the intended 1:500,000 or smaller display scale;
the app hides these outlines at close zooms. The data is not for geocoding,
precise geographic relationships or area/perimeter measurements. These are
modern administrative outlines, not historic, archaeological or property
boundaries, and add **zero archaeological records**. Town labels use the
existing reviewed [Census Gazetteer snapshot](RESIDENT_CONTEXT.md).

Outside Census coverage, the offline background remains the world land
outline. The optional source-reader maps described above retain that outline
and the publisher's own location geometry. Terrain, topographic and satellite
backgrounds are explicit online choices; they pause while the map is hidden.
The outline remains underneath them, so a failed online background can fall
back to general land orientation. No provider tiles are downloaded for offline
storage. The phone selector reserves space for the zoom controls.

Town reports also start with online geology off. Existing offline USGS unit
descriptions and citations remain available; users can explicitly enable
Macrostrat data when rebuilding a report. See the
installed Chrome and local-source checks (omitted from this edition; see [edition scope](../README.md#sources-and-publication-status)).
