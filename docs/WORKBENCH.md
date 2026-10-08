> **Public edition:** public Census town points are bundled as spatial context; archaeological/fossil locations are not. See the [README](../README.md). Other datasets described below are optional and are not bundled.

# Investigate a place inside Clovis

Clovis connects sources to observations. Start with a public town, inspect a
map or exposed object, and save what you learned with its source and date.

## Choose a place

Select a state, click the town box and type a name. Choose a returned Census
place, then select **Explore this town** directly below the town box. A name plus state, such
as `Santa Rosa, CA`, also works. For a rural location, use a nearby town.
**Change town** in the header or notes panel opens the same editable selector.
The compact **Try an example** action randomly selects and explores one of
100 public-town research questions, two distinct towns per state. It avoids
the immediately previous example. No example or sample observations load on
startup. After you click, the question appears as a compact summary with its
instructions closed. Click the question to expand the instructions. Dismiss
the example to retain the current map and report, or change your town to close it. The
example resets land-use history to unknown and follows your online geology
choice. It preserves saved notes. Historical maps still require **Find maps
of this town**; the example does not assert a map, fossil or object exists.
No address, browser location or sign-in is needed.

The header has four destinations: **Explore**, **Inspect a find**, **Fieldbook**
and **Research**. Explore follows a simple path: choose a place, follow a clue,
keep a record. **Options & land-use context** reveals the optional history and
online setting. **Statewide background and sources** offers every state's
reviewed learning context. Result actions appear after you build current
evidence; changing inputs clears that current-result state. **Refresh town
evidence** reruns the lookup. Offline maps say **Not loaded**, never a false zero.

## Choose an appearance

Use **Dark / Light** in the header. The choice is kept locally in this browser
and applies after reload; it is separate from the fieldbook. Map tiles,
historical sheets, photographs and the logo retain their original colours.
Printed notes remain light. Keyboard and touch controls work in both themes.

## Read local evidence

The central **Rocks & fossils** tab gives the map room to explore. Below it,
open **Read rock evidence · materials, ages & sources** to read and select
mapped rock units. This drawer starts closed. Select a unit card to read its
material, interval, description and original source. Multiple
map units can overlap; they are separate map sources, not independent finds or
layers under your yard. Reviewed formation guides show fossil learning examples
only for matched named formations, with their own source and limits.

**Words in this source** explains the material and age vocabulary beside a
selected unit. Open a word for its meaning, an observation question and sources.
Age cards place periods or epochs in relative older-to-younger order; the
labels date the mapped unit, not a loose stone or historical object. Original
qualifiers and untranslated wording remain visible.

Open **Rock words & geological time · works offline** to search 28 material
concepts and 28 age labels even when rock maps are off or unavailable. Try
`loess`, `sedimentary`, `Ordovician` or `Lutetian`. Missing vocabulary is a
review gap. See the [reference sources](GEOLOGY_LEARNING_SOURCES.md).

Inside the rock evidence drawer, open **Map overlay & sources** for
**Show regional geology overlay**, which is
optional and off initially. It requires a
current successful online town report. Adjust its opacity to compare it with
the background map. Colours distinguish mapped units; a colour or blank tile
does not identify a specimen or prove absence. The overlay pauses in other
tools. Read the selected unit's source detail and any matched formation guide,
then use its investigation action to carry the source and interval into
written notes.

## Read a historical map

1. Open **Old maps**, then **Find maps of this town**. Clovis queries the
   Library of Congress maps collection for the selected town and state.
2. Select a record card. Check the title, date and visible map extent. Search
   relevance does not guarantee it covers your chosen place.
3. If the record has multiple sheets, select the sheet. Zoom, drag, rotate 90
   degrees or choose **Fit map**. Read street names, landmarks and the legend.
4. Write what you can actually see. Avoid treating an uncertain alignment as a
   property match. **Use this map in an investigation** opens guided review with
   source metadata; review it and save the written record to the fieldbook.

Up to 12 records and 60 viewable sheets per record are offered. Some towns have
no digitized matches; API or image access can also fail. The app shows that
status. Use **Open your own map image** for a JPEG, PNG or WebP under 12 MB when
you already have a suitable map. Add its title, date and source yourself.
Source-record links retain rights information: digitization does not establish
reuse rights or permission to collect.

## Turn evidence into an investigation

In **Investigation**, choose one of three guided tasks:

| Task | Useful result |
| --- | --- |
| Read the rocks | Map source and interval compared with visible grains, layers or imported fill. |
| Trace a place through time | Dated map source and visible streets, buildings or land-use clues. |
| Document an exposed object | Material, features, scale and questions for an expert. |

Tick only the steps you completed. Add observations and select **I cannot tell
yet**, **Some observed details match**, or **Observed details differ**. These
are your comparisons, not verified identities. A valid town and written
observation are required to save. Source text is limited to 1,000 characters,
date/interval to 120 and observations to 1,500.

**Inspect a find** has more detailed material comparisons and a browser-local
photo pad. Document what is already exposed; the workflow is not a dig plan.
Its comparison guide and feature-specific questions use the center. Select
**Read the questions for these features** to reach it directly, then **Edit
your observations** to return. Save and download actions are above the guide;
photo instructions expand when needed. Public town context is optional: check
**Include [town]** only when that town belongs with the observation. Changing
town clears the choice and preserves your written notes. The saved record
keeps the included town without exact coordinates or a claim about provenance.
Possible-bone guidance appears next to the material selector immediately.

## Return to your work

**Fieldbook** keeps town reports, guided investigations and object
observations together. Open a card, compare another record or add a dated
follow-up. The original remains intact. Print selected notes or export JSON to
back them up or move devices. Restore merges valid entries. Limits remain 50
entries and 750 KB. Older Clovis versions that do not know guided investigations
cannot read those new entries; use this version or newer to restore them.

## Privacy and evidence limits

- Town lookup is bundled. Online geology sends the public Census town point
  and normal network metadata to Macrostrat only when Explore is pressed.
- The geology overlay requests viewport tiles directly from Macrostrat;
  background maps also request tiles from their providers.
- Historical search sends the public town and state from the local app server
  to Library of Congress. Selected map images load from its image service in
  the browser. The app does not download an archive of those images.
- Local map images and find photos remain in the browser. They are not sent to
  Python, analyzed, saved in the fieldbook or included in exports. Local map
  mode sends only a mode flag and the public town code, not image bytes.
- Written notes and saved-book contents are processed by the local server for
  callbacks, but are not written to its database or disk. Browser storage is
  specific to this device and app origin. Keep sensitive details out of notes
  you intend to share.

The app does not calculate backyard discovery odds, verify property history,
identify an object or authorize excavation. Coverage gaps stay visible.

Provider interfaces: [Library of Congress API](https://www.loc.gov/apis/json-and-yaml/requests/endpoints/)
and [Macrostrat data services](https://dev.macrostrat.org/docs/data-services).
See [resident context](RESIDENT_CONTEXT.md), [observations](OBSERVATIONS.md)
and [setup](SETUP.md) for broader workflow and data details.
