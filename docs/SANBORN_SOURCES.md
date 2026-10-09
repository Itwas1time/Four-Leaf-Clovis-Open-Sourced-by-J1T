> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Offline Sanborn atlas catalog

Clovis includes original, coordinate-free catalog metadata for **50,578 US atlas records**, indexed under **9,758 town/state names** across **all 50 states and the District of Columbia**. The source snapshot contains 35,104 digitized US records; other records still provide dates and source citations. Puerto Rico has no records in this package. This is an atlas catalog, not a claim that every town, street or neighborhood was mapped.

## Official source and rights

- [Library of Congress bulk package](https://data.labs.loc.gov/sanborn/): 50,600 worldwide atlas records; package updated April 9, 2024. The page identifies the online Sanborn collection as public domain and free to use and reuse.
- [Official package README](https://loc-sanborn-maps.s3.amazonaws.com/README.html): metadata compiled in January 2024; includes digitized and non-digitized atlases, original City_text/State_text indexing, dates, physical notes and previews. The README explains that location metadata is imperfect and atlas coverage is incomplete.
- [Official bulk metadata](https://loc-sanborn-maps.s3.amazonaws.com/metadata.jsonl): downloaded October 7, 2026. SHA-256: `c553e098012136d1942dbbd421eac6af9c9d587cf6fe69272c2bc2e97c0f16be`.
- [Collection rights and access](https://www.loc.gov/collections/sanborn-maps/about-this-collection/rights-and-access/): official source for reuse status.
- [Library of Congress JSON API](https://www.loc.gov/apis/json-and-yaml/requests/endpoints/): retained for explicit online search and sheet loading.

The bundled SQLite catalog is 29,188,096 bytes. SHA-256: `d1ef1be8eea12ffbd1605fdebbee9fdb486820a33dee540febffe33e28288822`. Known source dates span 1867–1981; these endpoints summarize parseable catalog dates, not a newly inferred history of map coverage.

## What is retained

An atlas record contains its original bounded title and date, official LOC item identifier and HTTPS source link, an official preview URL when supplied, digitization status, and a short description generated from the catalog's map purpose and snapshot status. Sheet counts come only from explicit `N sheet(s).` physical notes; file counts are not substituted for sheet counts. Descriptions are original summaries. No map images are bundled.

Town indexing uses the original City_text and State_text lists. Matching applies Unicode compatibility normalization, case folding, punctuation-to-space and whitespace normalization. Selected Census place names first lose only their administrative suffix, such as “city” or “CDP.” There is no fuzzy matching, Saint/St. expansion, guessed former-name matching or inference from nearby coordinates. A missing exact name match offers explicitly labeled statewide records. State browse and date pagination remain available even when a town has no exact entry.

Excluded from the 50,600 source records: 16 foreign records, three US records assigned only to “Multiple States - Us,” and three records with malformed item identifiers. Their missing or unusual identifiers are not guessed or repaired. Numeric and fractional official item identifiers are retained within strict path bounds.

## Data boundary and use

The runtime schema contains no latitude, longitude, enriched Location records, OpenStreetMap references, repository mailing addresses, personal contacts, archaeological find coordinates or fossil find coordinates. It does not incorporate NRHP or private field records. Census data continues to serve the existing public town selection, independently of this catalog.

Catalog browsing and metadata selection use local files. Selecting an available preview loads the official image directly in the browser. A record without a preview can supply an investigation citation explicitly labeled “Catalog record only; no sheet viewed.” “Search more maps online” and “Load map sheets online” are explicit online actions using fixed official endpoints. Source links provide current availability; January 2024 digitization status may have changed. Dates, titles, map extent and legends should be checked before recording an observation. An atlas record or visible building does not establish present-day survival, access permission or a find location.
