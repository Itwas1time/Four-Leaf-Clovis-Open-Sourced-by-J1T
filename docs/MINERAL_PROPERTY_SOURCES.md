> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Mineral chemistry and physical properties

This reference catalog contains Wikidata records for mineral species, mineral
varieties, and items directly classified as minerals. It stores source-reported
chemistry, physical properties, crystallography, and mineral classification.
It contains no specimen records, collection localities, coordinates, or
collector/donor information.

In **Library → Mineral properties**, search by name, formula or property, read
each recorded statement with its unit, rank, quantity bounds and qualifiers,
and save an attributed reference to Fieldbook. The saved record inherits no
selected town or observation. Repeated claims remain separate; Clovis does
not choose a consensus value or identify a local specimen.

The 8 October 2026 snapshot contains **6,381 mineral records and 43,922 active
property statements** from 6,485 queried items. The remaining 104 items had no
selected useful properties. All original entity batches were hash checked and
their identifiers compared with the complete source query. Missing labels for
units, qualifiers and cited items were fetched separately; no mineral entity
was downloaded again. Source statement links and the original units remain
available, including different density units. Units are not converted.

## Source and reuse terms

The source is Wikidata's public structured data, queried through the official
[Wikidata Query Service](https://query.wikidata.org/) and its
[entity data API](https://www.wikidata.org/w/api.php). The item index selects
direct statements of **instance of** mineral species (`Q12089225`), mineral
variety (`Q429795`), or mineral (`Q7946`). The build does not expand a broad
transitive subclass tree, so the recorded distinction follows the item's own
source classification.

Wikidata's [copyright policy](https://www.wikidata.org/wiki/Wikidata:Copyright)
states that structured data in the main, Property, Lexeme, and EntitySchema
namespaces is available under CC0. The catalog uses those structured labels
and claims only. It does not copy Wikidata article prose or descriptions, which
use different terms. Source claim references are preserved as citation data;
the catalog does not scrape or copy the linked reference pages.

Raw query responses, API entity batches, their SHA-256 hashes, and the build
report remain under the ignored `release/data-research/mineral-properties/`
directory. The runtime database is
`atlas/gui/data/mineral_properties.sqlite`. It is built offline from those
hash-checked source files and is capped below 90 MB.

## Facts retained

Each active Wikidata claim is kept as a separate property statement. The
catalog retains the English property label, source value, English label for
item values, Wikidata item ID, source quantity unit and its readable label,
quantity bounds, statement rank, qualifiers, source citation snaks, and a
source URL. Quantity values and units are not converted. Deprecated statements
are excluded from the reading catalog; preferred and normal ranks remain
visible. Empty/missing properties are left empty, and an item with no selected
facts is omitted and counted.

| Property | Wikidata property | Reading use |
| --- | --- | --- |
| Chemical formula | [P274](https://www.wikidata.org/wiki/Property:P274) | Formula string as entered |
| Mohs hardness | [P1088](https://www.wikidata.org/wiki/Property:P1088) | Source quantity, with unit and claim qualifiers |
| Density | [P2054](https://www.wikidata.org/wiki/Property:P2054) | Source quantity and unit; not converted to or relabeled as specific gravity |
| Crystal system | [P556](https://www.wikidata.org/wiki/Property:P556) | Crystal-system item label |
| Point group and space group | [P589](https://www.wikidata.org/wiki/Property:P589), [P690](https://www.wikidata.org/wiki/Property:P690), [P9733](https://www.wikidata.org/wiki/Property:P9733) | Source crystallographic labels and number |
| Streak, cleavage, fracture, habit, twinning | [P534](https://www.wikidata.org/wiki/Property:P534), [P693](https://www.wikidata.org/wiki/Property:P693), [P538](https://www.wikidata.org/wiki/Property:P538), [P565](https://www.wikidata.org/wiki/Property:P565), [P537](https://www.wikidata.org/wiki/Property:P537) | Source physical descriptions as structured items |
| Color and refractive index | [P462](https://www.wikidata.org/wiki/Property:P462), [P1109](https://www.wikidata.org/wiki/Property:P1109) | Source item or quantity values |
| IMA rank and symbol | [P579](https://www.wikidata.org/wiki/Property:P579), [P10113](https://www.wikidata.org/wiki/Property:P10113) | Mineral-status and approved-symbol claims |
| Strunz classification | [P711](https://www.wikidata.org/wiki/Property:P711), [P712](https://www.wikidata.org/wiki/Property:P712), [P713](https://www.wikidata.org/wiki/Property:P713) | Source classification codes |
| Hermann–Mauguin notation | [P1632](https://www.wikidata.org/wiki/Property:P1632) | Source crystallographic notation |

Wikidata does not provide a single dedicated luster claim in the selected
mineral property set, so this catalog does not generate one. Density remains
density even where a source reference discusses specific gravity. Formulae,
symbols, and classification codes are not parsed or normalized.

## Catalog API

`core.mineral_property_catalog` provides:

- `catalog_stats()` for item/fact coverage, class distinctions, source hashes,
  omissions, and property coverage.
- `search_minerals(query="", page=1)` for offline full-text search over names,
  formulas, classifications, and retained property values.
- `get_mineral("wikidata:Q...")` for one full record with source-linked
  properties, quantities/units, qualifiers, and references.

`formula` is a compact display field. If Wikidata has multiple active formula
claims, `formula_values` and the full `properties` list retain each distinct
source value. It is not a chemical formula parser or a mineral identification
tool.

Refresh and rebuild the source snapshot with:

```powershell
& .\.venv\Scripts\python.exe -m tools.ingest_mineral_properties --download
```

Rebuild from the saved private source files without network access with:

```powershell
& .\.venv\Scripts\python.exe -m tools.ingest_mineral_properties
```

For the snapshot's retained record/fact totals, property coverage, actual
source-linked examples, source hashes, omissions, and runtime size, see
`qa/2026-10-07/MINERAL_PROPERTY_CATALOG.md` (omitted from this edition; see [edition scope](../README.md#sources-and-publication-status)).
