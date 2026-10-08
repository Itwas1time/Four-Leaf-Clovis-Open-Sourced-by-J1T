> **Public edition:** Census town points and reviewed reference catalogs are bundled. Precise archaeological and fossil find locations are excluded. See the [README](../README.md) for the data inventory.

# Downloadable local collections

Open **Library → Data collections**. Each card shows its source, reuse rights,
snapshot, record coverage and download/storage sizes. Choose **Download
collection**; progress remains available after a page reload. Open the installed
collection to search and read it locally. Internet access is needed for the
initial download and external source pages.

| Collection | Contents | Download | Installed |
|---|---|---:|---:|
| World archaeological radiocarbon results | 173,946 laboratory determinations; 144 recorded country labels | 17.7 MB | 63.2 MB |
| Dinosaur taxa and fossil sites | 37,852 published occurrences; 14,371 collections; 12,996 original taxonomic names across ranks, including synonyms | 27.8 MB | 266.8 MB |

The existing museum, newspaper, map, geology and mineral catalogs remain
bundled. These two additional collections are optional; the initial application
still includes those existing large catalogs.

## Radiocarbon results

Search charcoal, shell, a laboratory identifier such as **A-0034**, a recorded
site name, or a reference. Filter by recorded country and, if useful, integer
laboratory ages. Read material, method, uncertainty, site labels and original
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

Choose **Published fossil occurrences** or **Taxonomic names & sites**. Search
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
```

Use the exact official archive; unpacked or edited databases are not accepted.
Saved references preserve source context and do not inherit the selected town.
Pack removal and automatic scheduled updates are not supplied in this edition.
