> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Museum object reference catalog

The local catalog contains 35,849 distinct records from The Metropolitan
Museum of Art's Open Access collection. It gives an in-app search across
historical object records; it does not identify an object someone has found
or establish where a record's object was used.

## Source and selection

The source is the Met's official [Open Access CSV](https://github.com/metmuseum/openaccess/blob/master/README.md)
and its [Collection API](https://metmuseum.github.io/). The CSV is a UTF-8
export with one source Object ID per collection record. The Met releases its
Open Access metadata under [CC0 1.0](https://github.com/metmuseum/openaccess/blob/master/LICENSE).
The downloaded source file stays in the ignored `release/data-research/`
directory; the catalog stores only the selected fields and a hash of the full
CSV.

Each retained row is deduplicated by source institution and Met Object ID.
Selection uses the source's `Object Name`, `Medium`, and `Classification`
fields. The six browse groups are simple text filters over those fields:

| Browse group | Source text used |
| --- | --- |
| Coins, medals, and tokens | `Object Name` contains a coin, medal, or token term |
| Buttons | `Object Name` contains a button term |
| Glass containers and vessels | A container or vessel `Object Name` and glass in `Medium` or `Classification` |
| Ceramic containers and vessels | A container or vessel `Object Name` and a ceramic, pottery, clay, or related material term |
| Stone implements | A listed implement `Object Name` and stone, flint, obsidian, chert, lithic, or quartzite in `Medium` or `Classification` |
| Metal implements and hardware | A listed implement or hardware `Object Name` and a metal term in `Medium` or `Classification` |

These groups help browse the records. They are not new object identifications
or interpretations. The Met's original object name, material, classification,
culture, period, date text, numeric date bounds, department, dimensions, and
record URL remain available as source fields. Numeric date bounds come from
the Met's `Object Begin Date` and `Object End Date`; they describe the museum
catalog record and are not a claimed find date.

The importer leaves out coordinates, excavation fields, and detailed find
locations. It does not download image files. The current snapshot has 35,849
records: 21,232 ceramic vessels, 5,589 glass containers, 4,723 metal
implements and hardware records, 3,333 coins/medals/tokens, 594 buttons, and
378 stone implements. Counts are records with distinct Met Object IDs, not
counts of unique object types or archaeological finds.

## Image rights

The CSV does not contain image URLs. The catalog therefore stores a remote
image URL only for records marked public domain in both the CSV's `Is Public
Domain` field and the Met Object API's `isPublicDomain` response. The URL must
also use the Met image host over HTTPS. The current snapshot has 60 such
checked URLs; image bytes are not bundled. The application can show one of
these images after a person selects **Load reference photograph**. Other records remain searchable
without a seeded image URL.

An explicit photograph request can also query the museum's fixed Object API
for the selected source ID. It accepts an image only when the response confirms
the same object ID and `isPublicDomain=true`; image hosts are restricted to the
Met's HTTPS image service. The source ID is public museum metadata. Notes, town
selections and local photos are not included. Failed image access leaves the
local record readable.

CC0 covers the released metadata. It does not itself grant rights to every
artwork image; the per-record public-domain check controls whether an image
URL is stored. The source's own object page remains linked for review.

## Refresh and verify

The source snapshot is stored outside the tracked tree so builds can be
reproduced and reviewed by its hash. From the repository root, refresh it with
one bulk download and optionally check a small set of image URLs:

```powershell
& .\.venv\Scripts\python.exe -m tools.ingest_object_references --download --image-checks 60
```

The image option permits at most 240 detail requests and uses no more than four
concurrent requests with a 12-second timeout. It checks selected public-domain
rows only. Building from the saved CSV is offline by default:

```powershell
& .\.venv\Scripts\python.exe -m tools.ingest_object_references
```

The private source snapshot's SHA-256 and catalog counts are recorded in the
SQLite metadata table and in the private QA report for this build.
