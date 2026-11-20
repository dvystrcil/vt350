# cad/library/: every part's CAD, with its source and licence

**Draft for the owner's approval (vt350#268 AC1).** The owner answered the open questions on 2026-11-20
([decisions](#decisions-owner-2026-11-20)); his approval of this page on the PR closes AC1.

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
  when the STL is what upstream publishes. Printed STLs stay in `parts/printed/` ([printed parts](#printed-parts)).
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
| `files` | yes, unless `printed` | `[{path, sha256, upstream_name?, size?, committed?}]`: every file, as downloaded. A file's own `committed: true` keeps it in git in a no-file entry (upstream's `LICENSE.txt`) |
| `printed` | no | A printed part's rows in `parts/printed/manifest.csv` (its `path` column), instead of copies of the STLs |
| `notes` | no | Anything a rebuilder needs: "owner confirmed matches the real part", what a remix changed, why this part |

## Parts we can't share: the no-file entry

A part whose licence doesn't allow redistribution (GrabCAD's terms: show only, with credit; or an unknown licence)
gets a `source.json` with `"redistributable": false` and **no file**. It still records the URL, the licence and the
sha256 of what we downloaded, so anyone can download it themselves and check they have the same file. The check fails
if the file is ever committed. A shareable part we leave out (`"committed": false`) works the same way, with a note
saying why (the official Raspberry Pi 5 model: "redistributable but large; add if wanted"). Upstream's licence file
is small, so it is committed even in a no-file entry (the official Pi 5's `LICENSE.txt`: the MIT notice and the
"guidance only" disclaimer), marked `"committed": true` on that file and labelled in `REUSE.toml`.

## Big files

- **By default a part is a no-file entry**: URL, licence and sha256, no file.
- **Commit the file when the model uses the part** (the simplified Pi 5, 24 MB), so the printer can be rebuilt from
  the repo.
- **A huge file** (near GitHub's 100 MB limit per file) goes up as a release asset instead; the entry stays no-file,
  with a note naming the release and asset (as the public pages do with their GLBs).

## Printed parts

Printed STLs stay in `parts/printed/`, and `parts/printed/manifest.csv` stays their record (source repo, commit,
sha256, licence; `check-printed.py` checks them). The library points at them instead of copying them: a printed
part's entry lists its manifest rows and no files (or only its STEP, when upstream publishes one):

```json
{"category": "motion", "title": "Z carriage", "author": "Voron Design",
 "source_url": "https://github.com/VoronDesign/Voron-Trident", "licence": "GPL-3.0-only",
 "licence_source": "LICENSE in the repo", "downloaded": "2026-11-20", "redistributable": true,
 "printed": ["voron-trident/z_carriage_left.stl", "voron-trident/z_carriage_right.stl"]}
```

`check_library.py --manifest parts/printed/manifest.csv` fails when a listed row is no longer in the manifest.

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
| `parts/printed/manifest.csv` | the printed STLs: source repo, commit, sha256, licence | a printed part's entry lists its rows (`printed`); `--manifest` fails on a missing row |
| `cad/vendor/` (#265, not merged) | the MZE STEP and its README | moves into the library (decision 3) |

## Decisions (owner, 2026-11-20)

1. **Folder names:** by part, not by author: `<category>/<part>/<variant>/`, as above.
2. **Printed parts:** the STLs stay in `parts/printed/`, with `manifest.csv` as their record; the library points at
   the manifest rows ([printed parts](#printed-parts)).
3. **`cad/vendor/` moves into the library.** It exists only on #265's branch (the Trianglelab MZE). Whichever of #265
   and #274 merges second moves `cad/vendor/trianglelab-mze-robertsamples/` to
   `cad/library/hotend/trianglelab-mze/<variant>/`, with a `source.json` made from its README.
4. **Each licence stays in both `source.json` and `REUSE.toml`**, and `check_library.py --reuse` keeps them equal.
5. **Big files:** no-file by default; commit when the model uses the part; a release asset if it's huge
   ([big files](#big-files)).
6. **The MIT notice:** Raspberry Pi Ltd's `LICENSE.txt` is committed beside the official entry's `source.json`.
