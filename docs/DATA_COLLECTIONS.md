> **Public edition:** Census town points and reviewed reference catalogs are bundled. Precise archaeological and fossil find locations are excluded. See the [README](../README.md) for the data inventory.

# Downloadable local collections

Open **Atlas → Manage offline collections**. Each card shows its source, reuse rights,
snapshot, record coverage and download/storage sizes. Choose **Download
collection**; progress remains available after a page reload. Open the installed
collection to explore it in the shared atlas search and reader. Internet access is needed for the
initial download and external source pages.

| Collection | Contents | Download | Installed |
|---|---|---:|---:|
| World archaeological radiocarbon results | 173,946 laboratory determinations; 144 recorded country labels | 17.7 MB | 63.2 MB |
| Dinosaur taxa and fossil sites | 37,852 published occurrences; 14,371 collections; 12,996 original taxonomic names across ranks, including synonyms | 27.8 MB | 266.8 MB |
| Neolithic food, farming and animal remains | 96,115 source rows in twelve linked UCL EUROEVOL tables; 4,757 sites and 2,807 occupation phases | 17.0 MB | 103.1 MB |
| Excavation contexts, finds and survey effort | 153,867 distinct source subjects from Gabii, Petra and Eastern Korinthia; original observation documents, tables and field definitions | 243.2 MB | 576.6 MB |

The existing museum, newspaper, map, geology and mineral catalogs remain
bundled. These additional collections are optional; the initial application
still includes those existing large catalogs.

## Radiocarbon results

Search charcoal, shell, a laboratory identifier such as **A-0034**, a recorded
site name, or a reference. Filter by recorded country and, if useful, integer
laboratory ages using **Specialist searches → Radiocarbon dates**. Read material, method, uncertainty, site labels and original
references before saving a dating reference to your fieldbook.

The source ages are **uncalibrated radiocarbon years BP**. Errors are the original
one-sigma standard errors. The collection supplies no calibrated BCE/CE dates
and does not date your own find. Source material, taxonomic labels, δ13C,
methods, periods, site labels and references remain source-supplied, with the
compilation's qualifications. Some contributors used zero for missing δ13C.
Coordinates are omitted; missing fields remain unknown.

Source: [p3k14c](https://github.com/people3k/p3k14c), release 2025.07, pinned
public scrubbed/fuzzed CSV. Data are CC0 1.0. Attribution and the
[publication](https://doi.org/10.1038/s41597-022-01118-7) remain with every
collection. A source release is not the date of every laboratory result.

## Dinosaur taxonomy and fossil sites

In **Specialist searches → Dinosaur taxa & sites**, choose **Published fossil occurrences** or **Taxonomic names & sites**. Search
**Tyrannosaurus rex**, a formation such as **Morrison**, a collection name or a
reference. Choose non-avian dinosaurs, fossil birds, or all Dinosauria; country
codes retain the source's ISO labels. Read the published identification beside
the snapshot accepted name. **Taxonomic names only** searches identifications
and accepted names; **All record fields** also searches sites, formations and
references. The taxonomy view preserves synonyms and source
name variants, and shows associated occurrences. A taxon without a selected
occurrence receives no inferred location.

The pack includes all occurrences whose accepted or identified original taxon
falls within the source's Dinosauria subtree in the frozen 20 September 2026
snapshot. Of these, 22,662 are non-avian and 15,190 are avian. It preserves
17,346 taxonomic variant records for 12,996 original taxonomic IDs. These are
names across multiple ranks, including synonyms; they are **not species counts**.
7,063 original IDs have associated selected occurrences.

Locations are **reported collection points**, with the original latitude,
longitude, location basis, precision description and geographic scale. They
are not individual specimen GPS fixes. Source protected-land codes retain their
land-status meaning. Geological age bounds retain their numerical strings;
**Ma** means millions of years ago. Occurrence records, collections, taxonomic
names and physical specimens are separate quantities.

Source: [Paleobiology Database snapshot](https://zenodo.org/records/22870967),
archived for Chronosphere. The archive is CC BY 4.0; its original API metadata
declares CC0. Attribution, original references and the frozen source DOI are
included. Contributor account fields and images are omitted. This published
corpus does not cover every unreported find or absent museum specimen.

## Neolithic assemblages

Search **Arbon**, **barley**, **Bos taurus**, a culture or a source identifier.
Use **Limit to a source → UCL · Neolithic assemblages** to focus on this pack.
Read a site or occupation phase, then follow **Associated evidence** to its
animal observations, plants or dating samples. Related lists use the same
search, reader and pagination. Bone records link to their original phase and
measurements; recovery methods and original source fields remain readable.

The twelve tables contain 4,757 published site labels, 2,807 occupation phases,
10,318 animal observations, 8,327 plant observations, 16,737 bone records,
36,483 measurements and 14,053 dating samples, plus recovery and taxonomic
tables. These counts describe different kinds of source rows. Presence-only
observations stay separate from quantitative specimen or plant counts; source
zeros and unknowns remain distinct. Ages remain uncalibrated BP, bone measurements
remain in mm, and original method and mesh-size strings are retained. All twelve
publisher field dictionaries accompany the pack.

Coverage is Central and Northwest Europe with 16 source country labels. Only
72 phases have animals, plants and linked dates together; 7,726 date rows have
no recorded phase. An occupation phase association does not establish an
individual deposit, a stratigraphic sequence or equal recovery effort.
Coordinates are omitted. Dating samples overlap other compilations: 4,511
laboratory-code strings also occur in the radiocarbon pack. Each source retains
its attribution; the pack does not claim those are distinct new dates.

Source: [UCL EUROEVOL](https://discovery.ucl.ac.uk/id/eprint/1469811/), supplied
2015 tables, with the publisher's CC0 waiver and original attribution.

## Excavation contexts and survey effort

Search **5016**, **pottery**, **charcoal**, a project name or an original Open
Context subject URL. Use **Limit to a source → Open Context · excavations &
surveys** to focus the search. Open a record, then follow **Associated evidence**
to its recorded parent context, finds or samples. **More associated evidence**
contains the publisher's typed links, including fills and above/below relations
where actually recorded. These lists use the same reader and pagination.

The collection includes 9,008 original individual documents, 38 published
table versions containing 146,474 overlapping rows, and 834 original field
definitions. Its 153,867 distinct subjects include excavation units, objects,
samples and survey contexts. Some subjects have only table fields or a publisher
query summary; the reader identifies the available evidence. These counts are
not individual finds, separate excavations or a worldwide census.

Read recovery methods, recorded zero counts and survey procedures beside their
original observations. Empty values remain distinct from zeros and `False`.
**Field meanings and units** explains the source fields. For example, EKAS Area
is expressed in square metres calculated through ArcGIS, an analytical addition
rather than an original field measurement. Survey classes and collected specimens
remain distinct from observed counts. Separate table versions retain their
citations without inflating the unique subject count.

**Published location and time** retains original geometry, specified/inferred
references, precision notes and ISO years. An inherited location does not become
an individual find GPS fix. Named spatial containment, recorder identities and
free-text mentions do not become stratigraphic links. Saving a source reference
preserves authors, source identifiers, source hashes and location/time qualifiers.

Sources: [Michigan Gabii](https://opencontext.org/projects/3585b372-8d2d-436c-9a4c-b5c10fce3ccd),
[Brown Petra Great Temple](https://opencontext.org/projects/a5ddbea2-b3c8-43f9-8151-33343cbdc857)
and [Eastern Korinthia Archaeological Survey](https://opencontext.org/projects/bc71c724-eb1e-47d6-9d45-b586ddafdcfe),
published through Open Context under CC BY 4.0. Original authors, licenses and
table versions accompany the collection. External media remain source links.

## Storage, updates and offline transfers

Collections live in **`~/Clovis Local/packs`**, separately from the application,
browser fieldbook and local dig-record database. Downloads resume after an
interruption. The published archive and every expanded file must match their
checksums; database integrity, schema, row counts and relationships are checked
before activation. Failed downloads leave installed collections and dig records
intact. Repairs preserve damaged files; updates retain earlier snapshots.

For an offline transfer, download the official ZIP using its collection card's
source/release links, copy it to the computer, then install it with the app's
Python environment:

```sh
python -m core.data_packs list
python -m core.data_packs install radiocarbon-world --archive clovis-radiocarbon-world-2025.07.zip
python -m core.data_packs install dinosaur-sites --archive clovis-dinosaur-sites-2026.09.20.zip
python -m core.data_packs install neolithic-assemblages --archive clovis-neolithic-assemblages-2015.07.zip
python -m core.data_packs install excavations-surveys --archive clovis-excavations-surveys-2026.10.08.zip
```

Use the exact official archive; unpacked or edited databases are not accepted.
Saved references preserve source context and do not inherit the selected town.
Pack removal and automatic scheduled updates are not supplied in this edition.
