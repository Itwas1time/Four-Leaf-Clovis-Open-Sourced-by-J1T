> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Local dig records

In **Fieldbook → Dig records**, start with a project code and title, or restore
a project backup. Existing projects appear in the project chooser. The recording
form and export action appear after you select a project.
Use the code required by your course or field team. Add units or trenches, contexts, finds, samples and source
documents. Record what you observed separately from interpretation and
uncertainty. An unknown context, count or measurement stays unknown.

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

**Download project backup** creates a ZIP containing `dig-records.json`:
project metadata, stable IDs, current records, all revisions and relationships,
including voided ones. **Restore project backup** checks the entire archive
before merging in a transaction. Repeated restores keep matching records once.
Later revisions with an identical earlier history can advance a record;
divergent corrections cancel the restore without overwriting either copy.

Each project supports up to 20,000 current records. Portable backups are
bounded to 1.2 MB compressed and 32 MB expanded to fit the existing local
request limit. If a backup exceeds those bounds, the saved database remains
intact; preserve that local file and organize subsequent work into another
project. The record list pages 24 at a time. Link pickers show up to 100 matching
codes; type a code to find records beyond the first page of suggestions.

The local database and backups contain your written information. Nothing is
published or sent to another person. Photos, survey geometry, attachments,
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
