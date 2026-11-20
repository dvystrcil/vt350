# cad/library/: every part's CAD, with its source and licence

**Draft for the owner's approval (vt350#268 AC1).** The questions at the end are open (the first is answered); nothing here is final until
the owner approves this page on the PR.

The library is the one place to rebuild the printer in CAD, or print a replacement part, without the FreeCAD model
(which lives outside git). Each part keeps a snapshot of the file as we used it, with where it came from and under
what licence, so we stay traceable if an author later changes the licence, updates the model or takes it down.

## Layout

The library is for finding a part, so it's sorted by part, not by author (owner, 2026-11-20). The author is a field
in `source.json`.

```
cad/library/
  README.md                       this page
  schema.json                     JSON Schema for source.json (it holds the list of categories)
  <category>/                     one of the categories below (electronics)
    <part>/                       the part (raspberry-pi-5)
      README.md                   which variant the model uses, and why
      <variant>/                  one source of that part: what it is, then whose (simplified-mandache, official-raspberry-pi)
        source.json               where it came from, its licence, the sha256 of each file as downloaded
        <file>.step               the file(s), unchanged from the download (renamed only to drop spaces)
        README.md                 optional: longer notes
```

- **Categories** (a fixed list; `schema.json` rejects any other, and an entry's `category` must be its folder):
  `electronics`, `hotend`, `motion`, `fasteners`, `frame`, `toolhead`, `enclosure`. Add one only with the owner.
- **Several variants of one part sit side by side** under `<part>/`, and the part's `README.md` says which one the
  model uses and why, linking any comparison.
- **One variant per folder**, files flat beside `source.json` (no sub-folders). A STEP for every part; an STL too only
  when the STL is what upstream publishes (see the questions: printed STLs stay in `parts/printed/` for now).
- **Files are never edited after they're committed.** The sha256 in `source.json` is of the download; a new upstream
  version is a new download with a new sha256 and date. A part we change is our remix, with its own variant (see
  [our own parts](#our-own-parts)).

Worked example: [`electronics/raspberry-pi-5/`](electronics/raspberry-pi-5/README.md), with the simplified model
by Eduard Mandache ([`simplified-mandache/`](electronics/raspberry-pi-5/simplified-mandache/source.json), a committed
STEP, CC BY-SA 4.0) and Raspberry Pi Ltd's own
([`official-raspberry-pi/`](electronics/raspberry-pi-5/official-raspberry-pi/source.json), a no-file entry: MIT, but
78 MB).

## source.json

[`schema.json`](schema.json) is the exact contract. The fields:

| Field | Required | What it holds |
|---|---|---|
| `category` | yes | One of the categories above; the entry's first folder |
| `title` | yes | The part's name as its source page gives it |
| `author` | yes | The person or company to credit |
| `handle` | no | Their user name on the site (`@EduardMandac_3771478`) |
| `source_url` | yes | The page it was downloaded from (`https://` only) |
| `licence` | yes | An SPDX id (`CC-BY-SA-4.0`, `MIT`), or a `LicenseRef-*` that `cad/credits.json` names (`LicenseRef-GrabCAD-NC-attribution`) |
| `licence_source` | yes | Where and when the licence was read: "owner's screenshot of the Printables page, 2026-11-20", "LICENSE.txt in the zip" |
| `downloaded` | yes | The download date, `YYYY-MM-DD` |
| `upstream_version` | no | The upstream version, commit, or the "updated" date on the page |
| `redistributable` | yes | Whether the licence lets this repo share the file |
| `committed` | no | Default: the same as `redistributable`. `false` keeps a shareable part out of git anyway (too large, not used) |
| `credit` | no | The project key in `cad/credits.json` that credits it in `CREDITS.md` |
| `archive` | no | `{name, sha256}` of the zip the files came out of |
| `files` | yes | `[{path, sha256, upstream_name?, size?}]`: every file, as downloaded |
| `notes` | no | Anything a rebuilder needs: "owner confirmed matches the real part", what a remix changed, why this part |

## Parts we can't share: the no-file entry

A part whose licence doesn't allow redistribution (GrabCAD's terms: show only, with credit; or an unknown licence)
gets a `source.json` with `"redistributable": false` and **no file**. It still records the URL, the licence and the
sha256 of what we downloaded, so anyone can download it themselves and check they have the same file. The check fails
if the file is ever committed. A shareable part we leave out (`"committed": false`) works the same way, with a note
saying why (the official Raspberry Pi 5 model: "redistributable but large; add if wanted").

## Our own parts

Our own parts (the frame, the remixes, the parts modelled from measurements) exist only inside the FreeCAD model. They
will be exported from the latest lite-N into `cad/library/<category>/<part>/vt350/` (variant
`vt350`) by a **read-only** FreeCAD run (AC3; not built yet):

- a platform script that opens lite-N, exports each listed part as STEP and **never saves the model**, run on the
  batch lane, from a printer-side list of parts (label or group prefix → part folder);
- each entry's `source.json` has `author` "Daniel Vystrcil", `source_url` this repository, `upstream_version`
  `lite-N`, and the licence of what it was made from (GPL-3.0-or-later for our own; a remix keeps its upstream's,
  as `REUSE.toml` already does for `cad/derived/`);
- a re-export from a newer lite-N replaces the file and its sha256 together (STEP files carry a timestamp, so the
  sha256 changes even when the shape doesn't).

## How it relates to what already records sources and licences

Each fact has one home; the check makes the others agree with it instead of copying it by hand.

| File | Is the source of truth for | Link to the library |
|---|---|---|
| `cad/library/*/*/*/source.json` | a part's provenance: URL, date, sha256 as downloaded, licence as read, notes | — |
| `REUSE.toml` | the licence label of every file in git (`reuse lint`, CI `reuse`) | `check_library.py --reuse` fails when a committed file's label differs from its `source.json` |
| `cad/credits.json` → `CREDITS.md` | one credit row per upstream project | an entry's `credit` names the project; `--projects` fails on an unknown key |
| `cad/viewer/licences.json` | which parts the public pages may show | none yet (it matches model labels, not files) |
| `parts/printed/manifest.csv` | the printed STLs: source repo, commit, sha256, licence | none yet: question 2 |
| `cad/vendor/` (#265) | the MZE STEP and its README | none yet: question 3 |

## Questions for the owner (AC1)

1. ~~**Folder names**~~ **Answered (owner, 2026-11-20):** by part, not by author:
   `<category>/<part>/<variant>/`, as above.
2. **Printed parts:** keep the STLs in `parts/printed/` with `manifest.csv` as their record (it already has the
   sha256, source, commit and licence), and give the library only their STEP, with a `printed` field pointing at the
   manifest rows? Or move the STLs into the library and retire the manifest's provenance columns?
3. **`cad/vendor/`:** once #265 merges, move `cad/vendor/trianglelab-mze-robertsamples/` into
   `cad/library/hotend/mze/trianglelab-robertsamples/` (its README becomes `source.json` + notes), so there's one folder
   for downloaded CAD? Or keep `cad/vendor/` for files the passes import, and the library for everything else?
4. **Hand-written or generated:** today each committed file's licence is written twice, in `source.json` and in
   `REUSE.toml`, and the check fails when they differ. Fine as is, or should a script write the `REUSE.toml`
   annotations (and the credit rows) from the `source.json` files?
5. **Big files:** the simplified Pi 5 STEP (24 MB) goes in git as it is. For the official one (78 MB) and anything
   that size: leave it a no-file entry, commit it anyway, or keep it as a release asset with its sha256 here (as the
   public pages do with their GLBs)?
6. **The MIT notice:** the simplified Pi 5 remixes Raspberry Pi Ltd's MIT model, so `REUSE.toml` lists both
   holders and the entry's notes quote "Copyright (c) 2026 Raspberry Pi Ltd". Enough, or also commit the official
   zip's `LICENSE.txt` beside it?
