> **Public edition:** public Census town points are bundled as spatial context; archaeological/fossil locations are not. See the [README](../README.md). Other datasets described below are optional and are not bundled.

# Investigate a place inside Clovis

**A little curiosity, Dig deeper.**

Clovis connects sources to observations. Start with a public town, inspect a
map or exposed object, and save what you learned with its source and date.

## Choose a place

Select a state, click the town box and type a name. Choose a returned Census
place, then select **Explore this town** on the right. A name plus state, such
as `Santa Rosa, CA`, also works. For a rural location, use a nearby town.
**Change town** in the header or notes panel opens the same editable selector.
The opening **Try Cincinnati** example selects and explores a town for you.
No address, browser location or sign-in is needed.

## Read local evidence

The central **Local evidence** tab shows mapped rock units as selectable cards.
Open one for its material, interval, description and original source. Multiple
map units can overlap; they are separate map sources, not independent finds or
layers under your yard. Reviewed formation guides show fossil learning examples
only for matched named formations, with their own source and limits.

**Show regional geology overlay** is optional and off initially. It requires a
current successful online town report. Adjust its opacity to compare it with
the background map. Colours distinguish mapped units; a colour or blank tile
does not identify a specimen or prove absence. The overlay pauses in other
tools. Select a unit and use its investigation action to carry the source and
interval into written notes.

## Read a historical map

1. Open **Historical maps**, then **Find maps of this town**. Clovis queries the
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

In **Investigations**, choose one of three guided tasks:

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

## Return to your work

**My fieldbook** keeps town reports, guided investigations and object
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
