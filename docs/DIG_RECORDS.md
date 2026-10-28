> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Local dig records

In **Fieldbook → Dig records**, start with a project code and title, or restore
a project backup. Existing projects appear in the project chooser. The recording
form and export action appear after you select a project.
Use the code required by your course or field team. Add units or trenches, contexts, finds, samples and source
documents. Record what you observed separately from interpretation and
uncertainty. An unknown context, count or measurement stays unknown.

## Sample measurements and processing

Create a **Sample**, open it and choose **Add measurement for this sample**.
A separate observation form opens with that sample linked. You can also choose
**Sample measurement / processing** in the record-type menu and select the
saved sample. Keep the project's observation code and name the portion or
fraction for each recorded quantity or processing observation. The sample reader
lists every linked measurement with pagination; a measurement opens its sample.
Changing the sample's code keeps the link to its stable ID.

Choose what the observation describes: collected, processed, analyzed, retained
unprocessed material, or a recovered result. Record the material/analysis target,
method, bag or container, recorder and observation/processing date. Mesh opening
and its original unit can be kept with the processing observation. Use the
description for retention reasons and recovery qualifications.

Quantities preserve the entered numeric precision and unit. For example,
`10.00 L` stays `10.00 L`; a separate `1200 cm³` entry stays in that unit. Values
must be finite nonnegative numeric text of up to 40 characters and at most
10^12. Mesh openings must be positive. Any recorded amount or mesh opening
requires its unit. A known unit may remain when its amount is unknown.
Choose **As recorded**, **Approximately**, **Less than** or **Greater than** to
qualify a recorded quantity. Put ranges or other unstructured qualifications
in the description.

Set the analysis status of the named material/portion explicitly. A processed
portion is not automatically marked analyzed. A zero seed count is recorded as
`0 items` for that result; an unexamined portion has an unknown quantity and
**Not analyzed** status. These observations do not establish that a whole sample
or context is empty. Clovis does not convert units, sum portions, infer recovery
rates or associate portions merely because their labels match.

For a teaching example, keep a collected volume, a processed volume, an analyzed
portion and a seed-count result as separately coded observations linked to the
same sample. Record the fraction actually examined and the method used. Review
the requirements of the real project when deciding what each quantity means.

Sample measurement corrections show their recorded fields in the revision
reader. Each observation has its own stable ID and complete backup history.
Existing sample/context snapshots are preserved when adding measurements.

## Contexts, finds and corrections

### Use Atlas evidence in a project

Open a result in **Atlas**, expand **Use in a dig project**, choose an existing
local project and enter its source-document code, such as `REF-01`. **Save and
open project source** opens that source in the project's recording workspace.
Create the project in **Fieldbook → Dig records** first if needed.

The source keeps the complete generated Atlas citation, including its source
attribution, reuse terms and qualifications. **Captured Atlas citation** shows
the original text and capture time. This snapshot is independent of the installed
collection: it remains readable after that collection is removed or replaced.
It contains the citation text, not a copy of the source database or attachments.
Project captures allow up to 2 MB of citation text, separately from browser
fieldbook readings, which allow 500 KB per reading and 20 MB of full reading
data in the local workspace. Browser notes and references remain bounded to
750 KB. An oversized citation is refused rather than shortened. Older builds
can reject larger citations; reopen these exports with the newer build.
The ordinary citation label, description and interpretation remain editable;
dated corrections preserve the captured text unchanged.

Saving the same cited content in that project opens its existing source, keeping
your annotations. Changed cited content needs a separate source code and record.
In another record, select the source under supporting source documents. **Read
source document** opens its saved citation. Published reference evidence does not
become an observed find or supply field coordinates.

A context can link to its recorded unit. Finds and samples can link to a
recorded context; bag identifiers remain separate from their record codes.
Add a source document, then select it as supporting evidence for another
record. Links are checked within the selected project. Clovis does not assign
the selected town or a reference specimen's identity to a field observation.

For a measured **depth below datum**, record the original numeric precision,
unit and named datum together. The datum must come from your project; a town
map supplies none. Values are not converted or compared across datums. This
form does not currently record survey coordinates or elevations.

Choose a saved record to correct it. The internal ID stays the same when its
human-readable code changes. Each correction keeps an earlier dated revision.
If another window changed the record, reopen it before saving; Clovis refuses
to overwrite a revision you have not read. The reader displays the latest 20
descriptions and interpretations; backups retain every field in every revision.

**Context relationships** records above, below and explicit same-as
correlations. Both contexts must belong to the project. Circular sequences,
including cycles introduced by a correlation, are rejected for review.
To correct a relationship, choose it, write the reason and void it. The
original relationship and dated correction remain in the backup. These checks
do not verify field observations, infer chronology or produce a Harris matrix.

## Storage and portable backups

Dig records are saved by the local app in
`~/Clovis Local/dig-records.sqlite`, outside the installed package and repository.
The folder is created when you first save a project. They remain available
after reloading the browser or restarting the app on this computer. Browser
fieldbook readings still have their own JSON backups and 50-entry limit.
Changing computer requires an explicit project backup and restore.

### Original photos

Open a record and choose **Add a photo**. Add a caption describing the side,
scale, visible features and uncertainty, then **Save record**. The original
JPEG, PNG or still WebP file is stored by the local app without re-encoding.
No identification or find coordinates are inferred from it. Each record can
have up to 12 photos, at most 5 MB and 40 million pixels each.

Captions belong to the saved record revision. Correcting a caption or removing
a photo from the current record creates another revision when saved; earlier
revisions retain their photos. **Download original** returns the original bytes,
including embedded metadata. Unattached uploads are retained locally; automatic
cleanup is not implemented. Keep complete backups before moving computers.

**Download project backup** creates a ZIP containing `dig-records.json`:
project metadata, stable IDs, current records, all revisions and relationships,
including voided ones. Attached original photos from current and earlier
revisions appear under `photos/`, once per distinct file checksum.
**Restore project backup** checks the entire archive
before merging in a transaction. Repeated restores keep matching records once.
Later revisions with an identical earlier history can advance a record;
divergent corrections cancel the restore without overwriting either copy.

Projects with a photo field in any current or earlier revision export
**version 4** backups. Projects containing captured Atlas citations export **version 3** backups,
including the complete text and all annotation revisions. Projects with sample
measurements and no captured citations export **version 2**; other projects keep
**version 1**. Current Clovis reads all four versions. Saving an original photo,
measurement or captured citation upgrades the database's format marker within
its transaction; original records and revisions are not rewritten. Older builds
refuse formats they cannot understand. Use the current build after adding these
records and retain your portable backups.

Each project supports up to 20,000 current records. Portable backups are
bounded to 32 MB of expanded project JSON plus 100 MB of original photos and
up to 1,024 distinct images, with ZIP overhead allowed. Large
citations and their revision history can be restored through **Restore project
backup** using the same file chooser as smaller projects. Transfer stays on this
computer. If a backup exceeds the project allowance, the saved database remains
intact; preserve that local file and organize subsequent work into another
project. The record list pages 24 at a time. Link pickers show up to 100 matching
codes; type a code to find records beyond the first page of suggestions.

The local database and backups contain your written information. Nothing is
published or sent to another person. Captured Swedish assignment citations
include their complete source geometry: **Show captured source geometry** and
**Download captured source record** remain available after restoring a project,
even when that source collection is not installed in the destination profile.
These are published source geometries with their original qualifications, not
new field observations or individual find locations.
The citation reader presents readable facts and qualifications; the complete
encoded source archive stays in the project and backup. Download the captured
source record to inspect its full original metadata and geometry.

Observed survey geometry, general attachments,
team accounts, synchronization and archive-repository submission are not
implemented. Use the recording requirements and supervision of your actual
project; this initial notebook does not claim professional archive compliance.

## Recording references

The design uses stable context/find/sample identifiers, checked cross-links and
retained corrections, informed by [CIfA's record-checking guidance](https://www.archaeologists.net/work/toolkits/ag2gp/strat-overview).
Project numbering conventions and the meaning of contexts still need written
documentation; see the [Archaeology Data Service project-documentation guide](https://guides.archaeologydataservice.ac.uk/guidesintro/projectdocu/).
Material-specific recording follows the project's requirements; [CIfA's finds
recording toolkit](https://archaeologists.net/work/toolkits/finds-recording/guidance)
provides a starting reference. These links do not establish certification or
endorsement of Clovis.

The sample fields also draw on [Historic England's environmental archaeology
guide, section 5.1](https://historicengland.org.uk/images-books/publications/environmental-archaeology-3rd/heag327a-environmental-archaeology/),
which discusses processing quantities, sample/context identifiers, mesh, dates
and retained material. Its environmental guidance is framed for England;
Clovis's fields are a recording aid, not a universal sampling protocol.
[CIfA's primary-record guidance](https://archaeologists.net/work/toolkits/finds-recording/primary-record)
supports keeping sample links and explicitly qualified quantities such as
estimated counts and weights. Apply the definitions and recording requirements
of your own project and repository.
