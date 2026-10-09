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
The separate town map's optional detailed background tiles still need internet.
