# Clovis — the past of any place, free and offline

<img src="atlas/gui/assets/clovis-bone-clover.svg" alt="Clovis four-leaf clover formed from bones" width="72" height="72">

**A little curiosity, Dig deeper.**

Pick a town and Clovis shows what is known about the ground there: who lived there before, old maps
of the place, nearby burial grounds and what the law asks of anyone digging. Found something in the
garden? Describe it and Clovis gives you dating clues and things to check, from published sources.
Want to go deeper? Read full archaeological studies and original data tables offline.

It runs on your own computer. No account, no subscription, no internet needed once installed.
Your notes and photos never leave your computer unless you export them.

![Clovis home screen: What is around me, I found something, Research a topic](https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T/releases/download/clovis-0.37.0/clovis-home.png)

## Download

- **Windows:** download [Clovis-0.37.0-windows-x64.zip](https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T/releases/download/clovis-0.37.0/Clovis-0.37.0-windows-x64.zip),
  extract it, and double-click **Start Clovis**. Nothing else to install.
- **macOS or Linux** (needs Python 3.11 or newer):
  ```sh
  python3 -m venv ~/clovis
  ~/clovis/bin/pip install https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T/releases/download/clovis-0.37.0/archaeo_scan-0.37.0-py3-none-any.whl
  ~/clovis/bin/python -m atlas.gui.app
  ```

Clovis opens in your web browser at `http://localhost:8050`. Updating keeps your notes: they live in
a `Clovis Local` folder in your home folder, not in the app.

## What you can do

**What is around me.** Choose any of 32,363 US towns and Census places, or press **Use my location**
(your spot stays on your computer). You get:
- *Your place through time*: lay old USGS topographic maps (as early as the 1880s) over your spot and
  slide between today and then. Each sheet is fetched once and then works offline;
- *Who lived here before you*, quoted from National Park Service histories (11 regions so far);
- *Known cemeteries* nearest your spot, from the USGS place-name index;
- *The law where you are*: permit, reporting and burial rules read from the official state code
  (verified for 11 states so far; other states link to their State Historic Preservation Office);
- 50,578 Sanborn fire-insurance atlas records, local rock and fossil context, and newspapers;
- a one-page summary to print or save as PDF.

**I found something.** Describe glass, pottery, metal, rock, a possible fossil or bone, or tick a
nail, button, clay pipe, marble or brick. Clovis shows dating clues that match what you saw (for
example, aqua bottle glass, cut versus wire nails, or the bore of a pipe stem), each with its source,
questions to check, and the law for your state. It explains; it never claims to identify your
object. Save it to your fieldbook with photos, export it, print it.

**Research a topic.** One search across museum objects, fossil specimens, radiocarbon dates,
excavation and survey records, minerals and full open-access studies with their original tables.
Large collections are optional downloads inside the app (Atlas > Manage offline collections); after
downloading they work offline.

**Fieldbook and dig records.** Keep observations, photos, contexts, samples and measurements with
every revision. Back up and restore the complete workspace as one file.

## What Clovis will not do

- Tell you what your find is. It gives the evidence to compare; the judgement is yours.
- Choose where to dig. Every list is about published, public places, not your yard.
- Replace legal advice. Rules are quoted from official sources with the date they were checked.
- Pretend coverage it does not have. Missing records never mean nothing is there.

## For developers

```sh
git clone https://github.com/Itwas1time/Four-Leaf-Clovis-Open-Sourced-by-J1T.git clovis
cd clovis
python -m venv .venv
.venv/Scripts/python -m pip install .     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m atlas.gui.app
```

On Windows, clone into a short folder near the top of the drive: Windows limits path length, and a
deeply nested folder makes `pip install` fail.
See [setup](docs/SETUP.md) and [security](SECURITY.md).

## Sources and publication status

Every record keeps its source, edition, license and the publisher's own wording about precision and
uncertainty. Source and rights notes for each collection are in [docs](docs/). This public edition
contains the application, user documentation, public Census town points and reviewed reference
catalogs. Credentials, personal details, private find locations and uncleared acquired data are
excluded; the edition uses a fresh Git history. Software is MIT licensed; data keeps its publishers'
terms.
