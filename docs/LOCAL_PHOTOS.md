> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# Personal photos and portable notebooks

In **Inspect a find**, choose **Add a photo**, describe the already exposed
object and add captions. Keep uncertain material and identity unknown. Photos
are a visual aid; Clovis does not identify an object or infer its find location.
**Save observation** keeps the photo references and captions with the dated note.
Zoom and rotation affect the viewer; the original files stay unchanged.

Saved readings remain in this browser. The local Clovis app stores the original
photo files in its notebook database on this computer. A browser reload retains
the notes, but changing browser origin or computer requires a complete backup.

In **Fieldbook → Saved readings**, select a saved observation to see its photos.
A follow-up makes another dated entry and retains its original photos and
captions. Prepared expert questions and separately attributed responses also
retain those attachments. **Download question packet** produces readable
Markdown alone, or a ZIP with that Markdown and its original photos. Nothing
is sent to another person.

**Download this fieldbook** creates `clovis-fieldbook.json` for notes alone, or
`clovis-fieldbook.zip` when photos are attached. The ZIP contains
`fieldbook.json` and original image files under `photos/`. Each distinct file
appears once, even when several notes reference it. **Restore a fieldbook**
accepts either format, checks the notes and files, and merges matching notes.
Conflicting content under an existing note ID is refused. JSON field order can
change during transport; note values, filenames, captions and original image
bytes are preserved.

**Read full notes**, **Download note text** and **Download observation text**
show or export the written note. Use the complete fieldbook backup to include
photos. The printable text view is not a photo-inclusive archive.

In **Fieldbook → Dig records**, attach and caption photos before **Save record**.
Corrections and removals preserve earlier revisions and their original images.
**Download project backup** includes all of them; restoration checks photos and
project histories before committing them together. See [dig records](DIG_RECORDS.md).

Supported files are still JPEG, PNG and WebP, up to 5 MB and 40 million pixels
each, with up to 12 photos per observation or record. A portable archive allows
100 MB of originals and 1,024 distinct images. The existing fieldbook limits
remain 50 notes and 750 KB of note metadata; project metadata has its separate
32 MB limit. These are bounded local notebook formats, not a media repository.

Original files retain embedded metadata. They are not re-encoded, geocoded or
uploaded to an external service. Unattached uploads remain in the local database;
automatic cleanup, image editing, general attachments and cloud synchronization
are not implemented.

Notes with photos use fieldbook format 2. Saving original photos upgrades the
local notebook database to format 4; project exports with a photo field in any
revision use format 4. Current Clovis also reads the older notes-only and project
formats. Use the current application with photo-inclusive notebooks; older
builds refuse database formats they do not understand. Retain complete backups.
