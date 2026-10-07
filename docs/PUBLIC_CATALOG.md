# Public site and institution directory

The application includes a coordinate-free SQLite snapshot of public records
from Wikidata and authored project pages. It contains public names, IDs,
countries, broad regions, source links, and source notes. It contains no site
coordinates and excludes the NRHP extract. Source dates are available in the
application. [Wikidata structured data are CC0](https://www.wikidata.org/wiki/Wikidata:Licensing).

Search, country/source filters, and 20-record pages run locally using SQLite
FTS5. Counts represent source records, not unique sites or organizations.
An institution's country identifies a documented office, not the project area
or permission to work there. Blank country fields mean the location has not
been established. Curated office source links are retained in
`atlas/gui/data/institution_locations.py`.

Directory entries provide research starting points. Verify publications,
survey coverage, land ownership, relevant communities, and competent heritage
authorities before planning work. Records do not confer excavation rights,
partnerships, funding, or rights to redistribute linked source material.
See [sites, partners, and permits](SITES_PARTNERS_AND_PERMITS.md).

Keep sensitive site locations and restricted source payloads private. This
snapshot is separate from the application's local area-review inputs; empty
area results mean missing local evidence. The [town lookup](RESIDENT_CONTEXT.md)
is a separate public Census place dataset, not an archaeological inventory.
See [security](../SECURITY.md).
