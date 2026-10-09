> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# NMNH Paleobiology reference catalog

## Sources and snapshot

The catalog is built from the Smithsonian Institution's official [Open Access repository](https://github.com/Smithsonian/OpenAccess), specifically its [NMNH Paleobiology shard index](https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhpaleo/index.txt) and the 256 JSONL shards listed there. The collection is identified in Smithsonian's [unit directory](https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/index.txt) as `NMNHPALEO` / “NMNH - Paleobiology Dept.”. The downloaded source snapshot totals 1,818,431,078 bytes. Its S3 `Last-Modified` headers span 5 October 2026, 07:35:16–07:36:23 UTC; this is a source-file timestamp, not a specimen or geologic date.

Smithsonian's [NMNH data access page](https://naturalhistory.si.edu/research/idsc/data-access) says collection metadata and media are made available in part under CC0. The importer checks `descriptiveNonRepeating.metadata_usage.access` on every record and includes metadata only when that record says CC0. A media URL is retained only when that individual media entry's `usage.access` also says CC0. The [Paleobiology Collections Search](https://collections.nmnh.si.edu/search/paleo/) describes the online specimen catalog and notes that the online records do not represent every specimen in the department. This local library is a filtered reference set from the EDAN snapshot, not a complete inventory of NMNH holdings.

Raw JSONL shards, their SHA-256/ETag/Last-Modified sidecars, the exact-byte index snapshot, and the build report stay under ignored `release/data-research/`. Runtime specimen records are bundled as `atlas/gui/data/fossil_references_paleo_XX.sqlite`, the stable-ID route and shard manifest is `fossil_references_index_paleo.sqlite`, and grouped taxon search is stored in `fossil_references_taxa_paleo_XX.sqlite`. Per-shard hashes, source URLs, timestamps, record counts, field coverage, and exclusions are available from `catalog_stats()` and the private QA report.

## Record selection and privacy

The importer keeps records whose metadata is marked CC0, whose unit is exactly `NMNHPALEO`, which have a stable EDAN `record_ID`, a source-reported taxon name, and at least one source taxonomy hierarchy value. A named, classified record remains useful when age or formation data are absent; those blanks stay blank and are counted separately. Records without a name or any taxonomy hierarchy are omitted. The importer does not infer a geological age or formation from a title, locality, collection date, or taxon.

Records mentioning humans or hominins, human remains, funerary/burial contexts, repatriation, or sacred material are withheld. Collector, donor, vessel, expedition, and other `name` fields are never copied. Place, site, coordinates, and all geographic fields are never copied. Collection dates and record-modified dates are not catalog fields and are never used as geological age. Only narrowly labeled source entries such as `Geologic Age`, `Stratigraphy`, and `Skeletal Morphology` are selected from free text; their values are retained after whitespace/control-character cleanup, while general notes are not exported.

The catalog contains source-reported names and classifications. It does not check current taxonomy, revise identifications, or infer that a specimen is locally likely to occur. A taxon's spelling and hierarchy remain as Smithsonian reported them. Search groups filter by the source-reported `tax_kingdom` value (for example `Animalia` or `Plantae`).

## Field mapping

| Catalog field | Source fields retained |
| --- | --- |
| `title`, `source_url`, stable ID | EDAN descriptive title, record link, and `record_ID` |
| `taxon_name` | `indexedStructured.scientific_name`, or labeled `Published Name` if that key is absent; `taxon_name_source` shows which |
| `taxonomic_hierarchy` | Source `indexedStructured.tax_*` values |
| `geological_age` | Source `indexedStructured.geo_age-*` / `geo_age_*` values |
| `geological_age_text` | Exact labeled `Geologic Age` entry |
| `stratigraphy` | Source `indexedStructured.strat_*` values |
| `stratigraphy_text` | Exact labeled `Stratigraphy` entry |
| `specimen_number` | Labeled `USNM Number` |
| `measurements` | Explicit length, width, height, depth, diameter, thickness, circumference, weight, volume, minimum, or maximum labels and their original text values |
| `physical_description`, `materials` | Labeled `Skeletal Morphology` and explicit material entries only |
| `type_status`, `type_citation` | Labeled `Type Status` and `Type Citation` |
| `categories` | Source `indexedStructured.topic` values |
| `image_url` | An official Smithsonian media URL whose individual media usage is marked CC0 |

Measurement labels and values are retained as supplied; units are not converted or inferred. Some source records have no explicit material or measurement values, and those fields remain empty.

## Search API

`core.fossil_reference_catalog` provides:

- `catalog_stats()` for source coverage, per-shard hashes, exclusion counts, and field coverage.
- `search_fossils(query="", group="all", page=1)` for specimen-level records with global stable pagination.
- `get_fossil(id)` for a record identified as `paleo:<EDAN record_ID>`.
- `search_taxa(query="", group="all", page=1)` for distinct source name/hierarchy groups, specimen counts, and up to four specimen IDs that route to details.

The runtime reader opens bundled SQLite files read-only. Each runtime SQLite file is capped below 100 MB; the builder currently enforces a 90 MB ceiling for specimen, route, and taxon files.

Reference photographs load only after an explicit click. The local server
retrieves the same individually CC0 Smithsonian asset at a bounded display
size; browser-to-museum image delivery can fail independently of metadata.
The route accepts only catalog specimen IDs, rejects redirects and non-image
responses, limits bytes, dimensions, duration and simultaneous requests, and
keeps a small temporary memory cache. It cannot retrieve user-supplied URLs or
personal uploads. A failed image is hidden with a short status; the catalog
facts and source remain readable. Photographs are not attached to fieldbook
references. See [Smithsonian image delivery](https://sirismm.si.edu/siris/ImageDisplay.htm).

## Provenance and interpretation

Each record links to the Smithsonian record URL and carries the metadata license. `catalog_stats()` exposes the exact source-index hash and the per-shard SHA-256, ETag, HTTP `Last-Modified`, byte count, and source record count. The date used as `snapshot_date` is derived only from S3 `Last-Modified` response headers. No collection/acquisition dates or the `Record Last Modified` free-text field are interpreted as specimen or geologic dates.

For the snapshot's inclusion totals, named taxon groups, field coverage, sample factual records, and focused test results, see `qa/2026-10-07/FOSSIL_REFERENCE_CATALOG.md` (omitted from this edition; see [edition scope](../README.md#sources-and-publication-status)).
