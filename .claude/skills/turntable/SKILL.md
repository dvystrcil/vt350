---
name: turntable
description: Make a drag-to-turn page of real Blender Cycles renders of the VT350 or a part of it (36 angles x 7 heights), preview it privately, and publish it on the public reference pages with its frames as a release asset. Use when asked for a turntable, a "draggable render", renders from all round a part, or to put one on the repo's pages; also to re-render one after a model or look change.
---

# Turntables of real renders

Everything runs through `cad/viewer/turntable.py` and one settings file per turntable,
`cad/viewer/turntables/<name>.json`. The commands are in `notes/scripts.md` ("A turntable of real renders"); this
skill is the order and the checks. Don't improvise steps the script already does: if something is missing, add it to
the script (generic parts in `platform/viewer/`, VT350 values in the settings file), in the same branch.

## 0. Rules that hold throughout

- Models are read-only: the export never saves, and nothing here writes a `.FCStd`.
- Don't edit `cad/render/colours.json`. The turntable look is opt-in render options in the settings file.
- A new turntable is a new settings file: copy `toolhead.json` or `printer.json`, change it, then
  `cad/viewer/turntable.py check all`.

## 1. Export, cameras, one test frame

```bash
cad/viewer/turntable.py export <name>      # prints RUN; the licence check runs here too
cad/viewer/turntable.py views  <name>
```

Before rendering all 252, render **three test views** and look at them yourself: a low rear one, a low front one, and
one from the side at 0° (`blender -b -P platform/render/render.py -- RUN/export RUN/test 24 --only
tt-e-40-a180,tt-e-40-a000,tt-e00-a090 --size 960x540 --look "AgX - Punchy" --plastic-specular 0.2`). Check that:
- the rear isn't dark (the key light must turn with the camera: views carry `light_turn_deg`);
- nothing the owner doesn't want to see is in the frame (the printer's base board is hidden with `"hide"`).

## 2. Render

- A part (the toolhead): render here, `cad/viewer/turntable.py render <name>` (about 30 min for 252 frames).
  Run it in the background.
- The whole printer: the batch lane, `render <name> --lane` (load the `batch-lane` skill). Then end the turn; the
  result is a comment on the issue. Afterwards: `collect <name>`.
- Never delete a lane job yourself (`kubectl delete` is blocked here). Give the owner the exact command with `! `.

## 3. Show the owner privately first

`cad/viewer/turntable.py stage <name>` writes `RUN/page/` (index.html, turntable.json, frames/). Publish that folder
as a **private artifact**: `file_path` = `RUN/page/index.html`, `root` = `RUN/page`, and every frame plus
`turntable.json` listed in `files`. Republish to the same file path to keep the link. Tell the owner what to look
for to know it's the new version (the strip says "252 Cycles renders" and lists the heights).

Changes the owner asks for go into the settings file, then rerun from the step they affect (`views` for cameras or
hidden parts, `render` for the look).

## 4. Publish on the public pages (only when the owner asks)

```bash
cad/viewer/turntable.py publish <name>     # refuses unless every part's licence is cleared
```

It uploads the frames zip to the release in the settings, records its sha256 in `notes/reference/assets.json`, writes
the page and its `turntable.json`, and adds the index entry. Then commit `notes/reference/` and the settings file on a
branch and open a **draft** PR. The `pages` workflow fetches and checks the zip on the PR. The site updates only when
the owner merges.

- A licence the rules don't cover: find the part's real licence and its source, add a rule to
  `cad/viewer/licences.json` with that source, and ask the owner when it isn't clear-cut. Never guess a licence.
- An old zip that nothing refers to any more can come off the release (`gh release delete-asset`), but only after the
  change that stops referring to it has merged, or the live site's build breaks.
