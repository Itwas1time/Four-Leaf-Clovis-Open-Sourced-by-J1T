> **Public edition:** Census town points and reviewed reference catalogs are bundled. Precise archaeological and fossil find locations are excluded. See the [README](../README.md) for the data inventory.

# USGS Cooperative National Geologic Map unit library

## Source and version

The bundled catalog is built from the U.S. Geological Survey (USGS) Cooperative
National Geologic Map, version 2.0.0 (2026). The National Geologic Map Database
product page lists the four thematic map products, the complete v2 geospatial
database, a map scale of 1:500,000, and the release citations. The USGS
September 3, 2026 announcement says v2 adds Alaska, Hawaii, and most U.S.
territories, completing coverage of all 50 states.

The builder verifies that each pinned ArcGIS item is owned by USGS, its title
identifies v2 (2026), and its service URL matches the official item URL. It
reads all four services' unit-description and citation tables, then queries
only map polygons intersecting each state's combined Census place points. The
report records a SHA-256 digest over the canonical retrieved table and polygon
records, plus the Census file's own SHA-256.

| Theme | USGS data release | Public ArcGIS service |
|---|---|---|
| Earth surface | [10.5066/P146VGVM](https://doi.org/10.5066/P146VGVM) | `National_Earth_Surface_v2` |
| Quaternary | [10.5066/P16SJAC6](https://doi.org/10.5066/P16SJAC6) | `National_Quaternary_v2` |
| Pre-Quaternary | [10.5066/P147SGSS](https://doi.org/10.5066/P147SGSS) | `National_PreQuaternary_v2` |
| Precambrian | [10.5066/P13TSV2J](https://doi.org/10.5066/P13TSV2J) | `National_Precambrian_v2` |

The product citations and full service URLs are also retained in the offline
database metadata. The source descriptions, age labels, geomaterial classes,
source map names, and citations come from USGS `DescriptionOfMapUnits`,
`Source_DescriptionOfMapUnits`, `Synthesis_to_Source_Units`, and `DataSources`
records. The catalog does not substitute Macrostrat values.

The hosted ArcGIS tables have regenerated `OBJECTID` values. Numeric
`DescriptionOfMapUnitsID` and `Source_DescriptionOfMapUnitsID` values in
`Synthesis_to_Source_Units` refer to the original geodatabase and must not be
joined to those hosted row numbers. Clovis joins the declared `MapUnit` and
`Source_MapUnit` codes exactly and rejects ambiguous codes or inconsistent map
identifiers. Each of the 24,108 declared relationships is retained. The source
tables omit descriptions for `127|Klc` and `127|Koba` in all four themes; those
relationships keep their recorded codes and mark the description unavailable.

On 8 October 2026 the bundled source descriptions were rebuilt from complete
official tables retrieved that day. The 129,410 existing Census-point
intersections, their exact place citations, national unit facts and coverage
tables were preserved and compared in full. Metadata retains the original
spatial snapshot digest and a separate source-relationship table digest.

## Place mapping

The join input is the checked-in 2026 Census Gazetteer place file,
`atlas/gui/data/us_places_2026.csv`. It has 32,363 public Census place points
across 52 two-letter Census state or territory codes. For each state and theme,
the builder sends one statewide multipoint query to the official USGS Map Units
polygon layer, fetches the returned polygon features in pages of at most 500,
and performs an exact local Shapely point-in-polygon join in WGS 84. It does not
make one network request per town.

The runtime SQLite file stores the seven-digit Census GEOID, state code, map
unit identifier, source map-unit identifiers, and source citations. It does
not contain town coordinates or polygon geometry. Every exact point/polygon
intersection is retained; if a point intersects multiple polygons, all
intersecting units are recorded. A place with no intersecting polygon in a
theme receives no mapped unit for that theme. The build report lists exact
intersection, multi-polygon, and no-hit counts by state and by thematic layer.

The mapping describes geology at the Census Gazetteer point and at the
national product's 1:500,000 scale. It is regional context, not a property
boundary, a site-scale geological determination, an access determination, or
an estimate of whether archaeological material or fossils will be found.

## Rights and attribution

The USGS source pages for all four thematic releases mark the data CC0 1.0
Universal. The full database is data release DOI 10.5066/P1DC4XFG. USGS and
source-map citations are retained in the catalog and returned with unit
searches and place lookups.

The Census Gazetteer is an official public U.S. Census Bureau reference file;
its source URL and local file SHA-256 are recorded in the build report.

## Rebuild

The runtime export contains only reviewed unit facts, their source citations,
state coverage counts, and the public Census GEOID-to-unit crosswalk. Raw
geometries and town coordinates are used only in memory during the build.

```powershell
.\.venv\Scripts\python.exe tools\ingest_usgs_units.py --verbose
```

The builder writes `atlas/gui/data/usgs_units.sqlite` and
`release/data-research/usgs_cngm_v2_build_report.json`. The report includes
the canonical source snapshot SHA-256, Census file SHA-256, service item
metadata, source-table counts, exact spatial-join and overlap counts, per-layer
and per-state gaps, and the runtime database SHA-256.

## Primary references

- [NGMDB product description: Cooperative National Geologic Map v2](https://ngmdb.usgs.gov/Prodesc/proddesc_118545.htm)
- [USGS v2 coverage announcement, September 3, 2026](https://www.usgs.gov/news/national-news-release/usgs-cooperative-national-geologic-map-now-covers-50-states-us)
- [USGS full geospatial database release, DOI 10.5066/P1DC4XFG](https://doi.org/10.5066/P1DC4XFG)
- [USGS Earth surface data release and CC0 rights statement](https://www.usgs.gov/data/cooperative-national-geologic-map-earths-surface-geology)
- [USGS Quaternary data release and CC0 rights statement](https://www.usgs.gov/data/cooperative-national-geologic-map-quaternary-geology)
- [USGS Pre-Quaternary data release and CC0 rights statement](https://www.usgs.gov/data/cooperative-national-geologic-map-pre-quaternary-geology)
- [USGS Precambrian data release and CC0 rights statement](https://www.usgs.gov/data/cooperative-national-geologic-map-precambrian-geology)
- [Census Gazetteer files](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html)
