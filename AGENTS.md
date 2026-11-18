# AGENTS.md: notes for AI coding tools working in this repo

Read by Claude Code (through `CLAUDE.md`), opencode, Cursor, Codex and others. Everything here also works by hand:
the owner must be able to run every tool without an AI (#122, the manual-run contract). This file points to the docs;
it doesn't repeat them, so they can't drift apart.

## What's where

- **Two kinds of code live here (#122).** `platform/` is the generic tooling: it would work unchanged for another
  printer, given that printer's data. Everything else is the VT350's own data, passes and documents. Put anything
  new deliberately on one side. Platform code reads printer data; it never imports printer code.
- **Platform inputs get neutral names** (`RENDER_STANDINS`, `FREECAD_APPIMAGE`), and the printer passes its values
  in. Don't add a `VT350_*` input to `platform/`. The 16 that remain are listed in `platform/README.md`.
- **Where to look first:**
  - `notes/scripts.md`: what to run, when, and how (the "what do I type" page).
  - `cad/README.md`: the model files and every `lite-N` pass, what it changed and what it found.
  - `platform/README.md`: the generic tools and how to run them by hand.
  - `platform/freecad/LESSONS.md`: what we've learned about FreeCAD. **Read it before FreeCAD work**, and add to it
    the day you learn something, in the same branch.
  - `notes/status.md`: the current state of the build.

## The model

- The FreeCAD models are **not in git** (100+ MB). They live in `~/Documents/VT350/`. The newest `vt350-lite-N.FCStd`
  is the working copy. `vt350-good.FCStd` is the untouched original: never save over it.
- **Every model change is a pass:** a script in `cad/passes/` that reads `lite-N` and saves a new `lite-(N+1)`,
  and **refuses to save** if any of its checks fails. Model it on the newest pass, using `platform/freecad/litelib.py`.
  - Run it headless first (`$APP freecadcmd <pass>`): that's a **dry run** and never saves.
  - Only a GUI run saves (`$APP <pass>`), because colours and visibility live in the GUI.
  - Back up before (`cad/backup-models.sh --verify`), and run `python3 cad/scripts/refresh.py N` after.
  - Add the pass's row to `cad/README.md`, and a sentence to `notes/status.md`.
- Show a design change to the owner (renders under `~/Documents/VT350/renders/`) before treating it as final.

## Working rules

- Branch, then open a **draft** PR. Mark it ready (`gh pr ready`) only when it's finished and every check is green.
  Never merge your own PR.
- Tests: the plain-python `test_*.py` files run in CI (`.github/workflows/`). The `*_fc.py` tests need FreeCAD:
  `$APP freecadcmd $PWD/<test>`.
- `result.json` at the repo root is a local slicer leftover: never commit it.
- Licensing is REUSE (`REUSE.toml`): our own work is GPL-3.0-or-later; third-party folders keep their own licences.
- Give FreeCAD scripts distinctive file names (a GUI script named `build.py` never runs; see `LESSONS.md`).

## Skills

Task recipes for Claude Code are in `.claude/skills/`. They point to the docs above; any tool or person can follow
them by reading the file.

- `freecad-standins`: make a FreeCAD model faster to open with stand-ins, and keep renders showing the real parts;
  make it smaller by turning copies into App::Links (`platform/freecad/dupes.py`).
- `turntable`: a drag-to-turn page of real Cycles renders (36 angles × 7 heights), previewed privately, then published
  on the reference pages with its frames as a release asset (`cad/viewer/turntable.py`).
