---
name: public-pages
description: Rebuild the VT350's public reference pages (the toolhead / printer turntable of real Cycles renders and the live 3D viewer with its GLB) from a new lite-N, preview them privately, and publish them with their big files as release assets. Use when a model pass changes parts those pages show, when the owner cuts a release or asks to "update the pages", or for a new turntable or viewer subject.
---

# The public toolhead / printer pages

Everything runs through `cad/viewer/pages.py` and one settings file per subject, `cad/viewer/pages/<name>.json`
(`toolhead`: turntable + viewer; `printer`: turntable). The commands are in `notes/scripts.md` ("The public toolhead /
printer pages"); this skill is the order and the checks. Don't improvise steps the script already does: if one is
missing, add it to the script (generic parts in `platform/viewer/` or `platform/pages/`, VT350 values in the
settings), in the same branch.

## When

- A lite-N pass changed parts a page shows (the toolhead, carriage, Beacon, ducts; for `printer`, anything visible):
  **offer** to refresh the pages once the pass is in. Don't refresh on your own: it uploads public files.
- The owner asks for it ("update the pages", a new release).

## 0. Rules

- Models are read-only: the export never saves.
- Don't edit `cad/render/colours.json`; the pages' look is in the settings (`render`).
- A new subject: copy a settings file, change it, `cad/viewer/pages.py check all`.

## 1. Build

```bash
cad/viewer/pages.py release toolhead --model N            # ~40 min here: run it in the background
cad/viewer/pages.py release printer  --model N --lane     # the lane; end the turn, wait for the issue comment
cad/viewer/pages.py collect printer && cad/viewer/pages.py stage printer
```

If the export fails on a new lite-N, the likely cause is the selection (`cad/viewer/toolhead.json`): a part was
renamed or the carriage moved. Fix the selection, not the model.

## 2. Look before showing

Open a few frames yourself: a low rear one (`tt-e-40-a180`), a low front one, a side one at 0°, and the compare
render. The rear must not be dark (the key light turns with each camera) and nothing the owner doesn't want to see
(the base board) may be in frame. The compare render and the 3D view must show the same parts.

## 3. Show the owner privately

`stage` wrote `RUN/page-turntable/` and `RUN/page-viewer/`. Publish each as a **private artifact**: `file_path` =
the folder's `index.html`, `root` = the folder, everything else in `files` (all frames + `turntable.json`; or
`viewer.json`, the `.gltf.json` and `render-compare.jpg`: artifacts don't serve `.glb`, so the preview uses the
embedded-JSON copy). Republish to the same file path to keep a link. Say what proves it's the new version (the model
label, lite-N, in the top strip).

Changes the owner asks for go into the settings file; rerun from the step they affect (`views`, `glb`, `render`).

## 4. Publish (only when the owner says so)

```bash
cad/viewer/pages.py publish toolhead
```

It refuses unless every part's licence is cleared. It uploads the frames zip and GLB to `viewer-assets-lite-<N>`
(created as a pre-release), rewrites the pages under `notes/reference/` and `assets.json`. Then commit those and the
settings on a branch, open a **draft** PR, and when the `pages` check is green (it fetches and checks the files) mark it
ready. The site updates when the owner merges; then load both pages to confirm.

- A licence the rules don't cover: find the part's real licence and its source, add a rule to
  `cad/viewer/licences.json` with that source, ask the owner when it isn't clear-cut. Never guess.
- Old releases stay: pages on main point at them until the new PR merges.
