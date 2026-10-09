> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Smithsonian object reference catalog

The Smithsonian NMNH Anthropology reference catalog is built from the
Smithsonian Open Access bulk metadata files. Smithsonian's OpenAccess repository
documents the AWS bulk archive and its line-delimited JSON format; the GitHub
repository is archived. The source bucket is partitioned by the first two
characters of each record's serialization hash.

## Sources and license

- [Smithsonian Open Access](https://www.si.edu/openaccess)
- [Smithsonian OpenAccess data repository](https://github.com/Smithsonian/OpenAccess)
- [Smithsonian Open Access AWS registry](https://registry.opendata.aws/smithsonian-open-access/)
- [EDAN Open Access documentation](https://edan.si.edu/openaccess/docs/)
- NMNH Anthropology shard index: `https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhanthro/index.txt`
- Local reviewed source list: `release/data-research/nmnhanthro-index.txt`

Each included record must mark
`content.descriptiveNonRepeating.metadata_usage.access` as `CC0`. Records
without that explicit metadata flag are excluded. Smithsonian's metadata flag
does not itself establish image rights, so an image URL is kept only when its
individual media entry also marks `usage.access` as `CC0` and its HTTPS host is
on the Smithsonian image allowlist. The ingester never downloads images.

## Included fields

The stable identifier comes from Smithsonian's `record_ID` field and is exposed
as `si:<record_ID>`. The catalog keeps the source title and record link, source
object type, USNM catalog number, explicit culture labels, exact object-date
labels, topic labels, and labeled measurements. Accession dates and collection
dates are not treated as object dates. Measurements retain their source label
and value.

Material tags are a transparent text heuristic over the source title and
object-type fields. They are returned in `material_tags`, with `material` as a
searchable comma-separated string and `material_basis` set to
`Title/object-type keyword tags` when tags exist. A tag is a searchable source
text classification, not an independent material identification.

## Exclusions and privacy

The SQLite records do not copy donor names, collector names, place or site
fields, coordinates, accession numbers, free-text notes, or source payloads.
They do not derive a map location from a title or source link. Records whose
public metadata contains a flag for human remains, funerary or burial context,
repatriation, sacred objects, or mummies are withheld and counted in the private
build report. Non-CC0 metadata, malformed JSONL records, records outside
NMNHANTHRO, records without a stable ID or descriptive title, and duplicate
stable IDs are also excluded or cause the source shard to fail validation.

## Build and local storage

Run `python tools/ingest_smithsonian_references.py` to download or resume the
256 shards listed in the local manifest and build one SQLite file per source
shard in `atlas/gui/data/`. Downloads use three or fewer workers, bounded
timeouts and retries, source-host checks, and ETag and byte-length validation.
Raw JSONL and the per-shard build report stay under the ignored private
`release/data-research/` directory. Raw files are preserved so a database can
be rebuilt with `--force` without another download.

Each generated database is limited to less than 45 MiB. A compact
`smithsonian_reference_index.sqlite` maps stable record IDs to one source
shard for fast detail lookups. The local API in
`core/smithsonian_reference_catalog.py` searches the SQLite shards read-only,
returns 24 rows per page, and provides global counts and per-shard SHA-256
provenance. Rows carry object facts alongside their Smithsonian source link so
the catalog can support comparison rather than acting as a link list.
