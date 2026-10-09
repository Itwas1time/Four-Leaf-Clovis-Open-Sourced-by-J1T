> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Archaeological publication catalog

The Library's **Archaeological projects** reader contains bibliographic fields
from Open Context's worldwide **Data Publication** category. This includes
excavations, surveys, specialist analyses and comparative databases. A data
publication is not necessarily one dig, an active excavation or an opportunity
to participate. The catalog is one publisher's contribution to Clovis's larger
global-data objective.

## Source and coverage

The importer uses the official [Open Context query API](https://opencontext.org/about/services)
with `type=projects`, `cat=oc-gen-cat-data-publication`, `rows=100` and stable
item ordering. The 8 October 2026 snapshot checked all **204 publication records
on three pages**. It includes **203** records carrying supported reuse licenses.
One CC BY-NC record remains at its publisher and is not redistributed here.

The unfiltered projects endpoint also includes tens of thousands of collection
records, mostly within DINAA. Those collections are not counted as separate
excavation projects. Query result features include geographic facets as well
as item records. Only item records are imported, including the separate
`oc-api:has-no-geo-results` list. The builder refuses missing rows, repeated
identifiers, changing totals or prematurely ended pagination. A complete
publisher query does not establish complete coverage of archaeology worldwide.

Country context is taken from the first two levels of the publisher's public
context hierarchy. Deeper site, trench and context names are omitted. Country
context absent from that hierarchy remains **Not recorded**, including records
whose titles mention a place. Searching the title or description can find
such records without inventing a geographic classification. Counts and gaps
remain in the bundled catalog's metadata and are shown in the reader.

## Fields and dates

Clovis preserves titles, short source descriptions, published creators,
subject labels, coverage labels, publication dates, source modification dates,
source links, DOI links when supplied, and per-record license URLs.
Descriptions are converted to literal plain text. The reader distinguishes
source time coverage from publication and modification dates. Source coverage
labels can describe places or periods; they are not automatically treated as
dates. Signed numerical years are presented as recorded BCE/CE years. Missing
fields remain unknown. No date is inferred for a user's separate observation.

## Rights and attribution

[Open Context's intellectual-property policy](https://opencontext.org/about/intellectual-property)
describes its Creative Commons publication model. Licenses are checked on
each project's item response rather than assumed from the publisher's name.
Supported metadata licenses are CC BY 2.0, 2.5, 3.0 or 4.0, CC BY-SA 4.0 and
CC0 1.0. The current snapshot includes 202 CC BY publications and one
[Historic Fort Snelling publication](https://opencontext.org/projects/fab0532a-2953-4f13-aa97-8a9d7e992dbe)
under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Each selected source record and any Clovis selection or plain-text rendering
of its fields retain that record's linked metadata license, including the
Fort Snelling record's ShareAlike license. These third-party source fields are
not relicensed under the application's MIT software license. The reader and
saved fieldbook references retain published creators, title, source URL,
available DOI, date, license and a notice of field selection/plain-text
rendering. User-written observations remain separate from these source fields.

API requests use the documented `oc-api-client` user agent, at most one request
per second and bounded retry delays. This stays below the rate ceiling in
[Open Context's terms](https://opencontext.org/about/terms). Requests contain
public catalog identifiers only. They do not submit observations or photos.

## Excluded content and reproducibility

No raw geometry, coordinates, photographs, full abstract HTML, person-resource
identifiers or deeper excavation context hierarchy is bundled. A short
description containing coordinate or address indicators is withheld and
replaced by a route to the source. All raw responses and ingestion caches stay
private under ignored `release/`. The runtime database has only `metadata`
and `projects` tables. The private inventory pins its exact hash and schema.

Save a publication to Fieldbook to keep its attributed source metadata.
It inherits no selected town and includes no photograph. JSON export/restore
preserves that snapshot. Search, paging and source reading work offline;
opening the publisher's complete dataset or DOI requires internet access.

This catalog does not yet ingest the projects' context, artifact or sample
tables, establish survey effort, establish current project status, accept
research-team submissions or implement a multi-publisher update service.
