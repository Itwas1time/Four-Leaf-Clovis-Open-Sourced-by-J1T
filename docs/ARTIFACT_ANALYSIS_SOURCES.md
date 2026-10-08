> **Public edition:** Census town points and reviewed reference catalogs are bundled. Precise archaeological and fossil find locations are excluded. See the [README](../README.md) for the data inventory.

# Ceramic analytical samples: sources and reuse

This catalog adds coordinate-free ceramic composition records with measured elemental values and a small set of source-defined typology, date, fabric, and weight fields. It is built from four fixed Open Context bulk tables. Three table projects publish their data under the Public Domain Mark 1.0; one table is also preserved in Zenodo under CC BY 4.0. The catalog stores the applicable rights and attribution on each record. It does not include source software or copied GPL code.

## Rights and source records

Open Context's [Terms of Use](https://opencontext.org/about/terms) explain the reuse terms and API request limit. Its [data recipes](https://opencontext.org/about/recipes) describe the prepared CSV tables used here. The source-level rights were checked on the individual project records and, for `oc-naa-04`, Zenodo archive metadata. Rights are recorded per source because Open Context hosts data with different terms.

| Source key | Prepared bulk table | Project record | Rights | Attribution |
| --- | --- | --- | --- | --- |
| `oc-naa-01` | [CSV table](https://opencontext.org/tables/036dbdc0-5ef6-4576-8421-f09ab0f8cec8) | [Open Context project](https://opencontext.org/projects/45c12f7c-8744-47bb-902a-523d11ce0c32) | Public Domain Mark 1.0 | Pavol Hnila, Carolyn Aslan, Diane Thumm-Dograyan, Wendy Rigter, Peter Grave, Lisa Kealhofer, and Ben Marsh; Open Context; DOI [10.6078/M7KH0KFP](https://doi.org/10.6078/M7KH0KFP). |
| `oc-naa-02` | [CSV table](https://opencontext.org/tables/10a33c66-0bc1-40fb-b832-8f55aca970c5) | [Open Context project](https://opencontext.org/projects/81d1157d-28f4-46ff-98dd-94899c1688f8) | Public Domain Mark 1.0 | Marie-Henriette Gates, Peter Grave, Lisa Kealhofer, and Ben Marsh; Open Context; DOI [10.6078/M79C6VH9](https://doi.org/10.6078/M79C6VH9). |
| `oc-naa-03` | [CSV table](https://opencontext.org/tables/e653f4f9-78a6-40c8-9d85-2a62bd4f48db) | [Open Context project](https://opencontext.org/projects/cbd24bbb-c6fc-44ed-bd67-6f844f120ad5) | Public Domain Mark 1.0 | Lisa Kealhofer, Peter Grave, and Ben Marsh; Open Context; DOI [10.6078/M74Q7S2X](https://doi.org/10.6078/M74Q7S2X). |
| `oc-naa-04` | [Open Context table](https://opencontext.org/tables/16c1b1c7-433c-621b-bc5d-91ea25184f30); [archived CSV](https://zenodo.org/records/10742093) | [Open Context project](https://opencontext.org/projects/ababd13c-a69f-499e-ca7f-5118f3684e4d) | CC BY 4.0 | Attila Stopic, Ben Marsh, John W. Bennett, Jürgen Seeher, Lisa Kealhofer, Peter Grave, and Ulf-Dietrich Schoop; Open Context; DOI [10.6078/M70V89RM](https://doi.org/10.6078/M70V89RM); Zenodo DOI [10.5281/zenodo.10742093](https://doi.org/10.5281/zenodo.10742093). |

The [Public Domain Mark 1.0](https://creativecommons.org/publicdomain/mark/1.0/) identifies material believed to be free of known copyright restrictions; it is a rights statement rather than a license. The fourth source is reused under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Record-level attribution follows the source metadata. The data are factual values and source labels; this catalog does not redistribute Open Context software.

## What is included

The four exports contain 2,199 rows. The builder retains 2,040 actual pottery or ceramic samples with at least one elemental result. The retained catalog has 46,657 elemental observations across 27 element symbols, 849 samples with a recorded weight, and 5,663 values whose source labels explicitly state a unit. The SQLite file is 12,324,864 bytes.

For each record, the database stores a stable `oc:<subject UUID>` ID, a fixed Open Context subject URL, source key, sample label, applicable rights and attribution, source identifiers, selected source-defined attributes, and the original measurement label and value. Numeric readings are also parsed when possible. Units are normalized only when a table label states them; original labels and raw values are preserved. For elemental values without an explicit unit, `unit` remains null. Repeated semicolon-separated values remain separate observations with a replicate number. A source field named `NAA` remains an opaque `source_numeric` value; it is not guessed to be an element or physical unit.

Selected attributes are limited to source fields for period/date, ware, fabric, form, vessel part, decoration, analysis, or sample type. The export excludes free-text context, project/site and geographic fields, coordinates, and source-person fields. Only the generic Open Context subject URL is kept as a fixed record link. Records flagged by the selected sensitive-context terms are excluded.

## Filtering applied

Filtering is source-specific because the four tables use different category fields:

* `oc-naa-01`: retained rows whose `Item Category` is `pottery`.
* `oc-naa-02`: excluded rows marked as sediment, soil, clay, sand, rock, or geological/geochemical references in the sample description fields; ceramic samples remain eligible.
* `oc-naa-03`: retained rows whose `Sample Type` is `pottery`.
* `oc-naa-04`: retained rows whose `Type` is blank, begins with `ceramic`, or equals `pottery`; geological reference types and other sample types are excluded.
* All sources: records without any recognizable elemental measurement are excluded. Only element-symbol columns from the periodic table are treated as elemental analyses.

This pass excluded 126 geological references, 32 non-pottery records, and one record without an elemental measurement. A repeated subject UUID would be skipped rather than duplicated. The builder rejects a changed or malformed source file, an HTML challenge response, redirects outside the fixed source hosts and declared Open Context export storage, source CSVs over 25 MB, or a runtime database over 90 MB.

## Rebuild

The downloaded source files belong under the ignored `release/data-research/` directory. They are not runtime assets. To download the fixed bulk tables and build the bundled read-only catalog, run:

```powershell
.venv/Scripts/python.exe tools/ingest_artifact_analysis.py --download
```

The builder requests only the four published CSV resources, sequentially and with retry delays honoring `Retry-After`. It does not harvest subject pages or the Open Context API. Source hashes, row counts, inclusions, exclusions, field coverage, and the combined source hash are written to `release/data-research/artifact-analysis-build-report.json`.
