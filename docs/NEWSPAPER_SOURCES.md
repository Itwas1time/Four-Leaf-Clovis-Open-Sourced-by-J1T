> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Offline U.S. newspaper title catalog

Clovis bundles a **partial, offline prefix** of the Library of Congress (LOC) newspaper directory. The current database contains 46,871 U.S. title records from 47,500 fetched directory records. LOC pagination reported 159,085 records across 637 pages during this harvest; only pages 1–190 are in the bundle. **Every count and search result is incomplete. A title missing from this snapshot must not be treated as absent from the LOC directory or from local history.**

## Official source and reuse

- [Directory of U.S. Newspapers in American Libraries](https://www.loc.gov/collections/directory-of-us-newspapers-in-american-libraries/): searchable LOC index of newspapers published in the United States since 1690. LOC cautions that it does not hold every title listed. Clovis does not bundle holdings records, so a directory title link alone does not establish which institution holds a copy.
- [LOC guide and directory FAQ](https://guides.loc.gov/directory-of-us-newspapers/frequently-asked-questions): describes the directory records as an **open-access resource**, derived from CONSER/WorldCat bibliographic records. LOC says it harvests authenticated title records about every six months and updates U.S. newspaper holdings information about every two years. LOC does not state a CC0 license on this guide. Clovis keeps structured factual metadata and original summaries generated from those facts; it does not keep source free-text descriptions.
- [LOC JSON API](https://www.loc.gov/apis/json-and-yaml/): public, unauthenticated API used for the paged harvest. The fixed query is `fo=json&at=results,pagination&c=250`; page requests are sequential and rate limited.
- [Chronicling America rights and access](https://www.loc.gov/collections/chronicling-america/about-this-collection/rights-and-access/): rights information for actual digitized newspaper content. LOC believes the newspapers in that collection are public domain or have no known restrictions, while some items under 95 years may contain separately copyrighted third-party material. This catalog does not download article pages, OCR, or images. Bibliographic metadata status does not change rights for an issue.

## Snapshot and observed coverage

- Snapshot build date: **2026-10-08 UTC**. The source prefix contains LOC extract timestamps from 2026-05-19 through 2026-10-05.
- Pagination total reported during the harvest: **159,085 records / 637 pages**. Successfully saved prefix: **47,500 records / 190 complete pages** (about 29.9% of the reported total).
- U.S. title records retained from the prefix: **46,871**. Another **629** records lacked a recognized U.S. country/state signal and were excluded from the U.S. index. The prefix included **53 recognized state/territory codes** and **10,109 distinct indexed state/town pairs**; these are observed-prefix counts, not a full coverage census.
- The prefix includes **2,706** title records whose LOC digitization flag is true. This flag does not promise every issue or year is online.
- Publication dates are retained as LOC supplied them. Parsed years are approximate sorting aids: earliest parsed start year **1700** and latest parsed year **2026**. LOC uses `2099` for open `20??` ranges and `2029` for open `202?` ranges in some records; these sentinels are not treated as publication end years. The raw date strings remain available in each record.
- The download stopped before the full directory harvest completed. The saved prefix is preserved for a future respectful resume.
- **Selected-field source prefix SHA-256:** `7b110d49f310191e72d27b958ec5907bef061b0538971a617ad4c561482d58f1` (`release/data-research/newspaper_directory.jsonl.gz.20261008T061023Z.partial`, ignored/private source snapshot).
- **Runtime SQLite SHA-256:** `00e147165167b7277cf00e98e3d3f1f5414e9d62729bf169ec62ddc7c8a85b8b`; size **34,299,904 bytes**, under the 100 MB per-file limit.

This is not a live inventory or a complete directory harvest. It is intentionally marked `snapshot_complete=false`; state counts, town counts, and search results reflect only the observed prefix. A missing town, state, language, date, or title can be due to missing pages. No entry does not establish that a local newspaper never existed.

## Included fields and search behavior

The runtime file `atlas/gui/data/newspaper_catalog.sqlite` contains LOC item IDs, display titles, original date/date-range strings, approximate parsed start/end years, language, publication frequency, the LOC digitized flag, and canonical LOC item URLs. IDs are accepted only from a fixed LOC host and a bounded item-ID format; no source URL is retained as a navigable target. The `summary` is generated by Clovis from title, place, date, language, frequency, and digitization facts. It does not retain LOC/CONSER free-text descriptions, holdings narratives, institutions, coordinates, addresses, individual identities, issue text, OCR, or images.

The `places` table contains recognized state/territory codes and LOC city labels. Only LOC structured geography is used; no neighboring-city or historical-alias inference is added. Catalog facts support historical place/time research even when the prefix has no digitized issue for a title.

`core.newspaper_catalog` is read-only and works offline:

- `catalog_stats(state='', town='')` returns counts and source completeness. A town statistic never silently substitutes a statewide count.
- `search_titles(state='', town='', query='', page=1)` returns stable 24-row pages. Exact town matches use the LOC city/state index. If a town is absent and a state is supplied, results are explicitly marked `scope='state'` and `exact_town=False`. Without a state, a missing town returns no results. All results include `snapshot_complete` and observed/expected page counts.
- `get_title(id)` retrieves one record by a validated stable LOC item ID.

In the current partial snapshot, even an exact town match is only exact within pages 1–190; the town may have additional titles on unharvested pages. An absent town or title is not a reliable negative result.

## Rebuild and resume

Run `python tools/ingest_newspaper_catalog.py` to resume from preserved complete pages and build the database after LOC pagination completes. Add `--refresh` to fetch a fresh sequence from page one. Requests are one at a time and honor the LOC `Retry-After` response. A preserved prefix can also be built for review with `--partial-snapshot <path> --expected-records 159085 --expected-pages 637`; that mode explicitly records incomplete coverage in SQLite and does not contact LOC.
