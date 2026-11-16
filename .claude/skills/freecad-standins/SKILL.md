---
name: freecad-standins
description: Make a FreeCAD model faster to open in the GUI by giving its most expensive parts cheap stand-ins (a fitted shape or a coarse mesh) while the real parts stay in the model, hidden, and renders keep drawing the real ones; and make it smaller by turning repeated parts into App::Links (dupes.py). Use when a model is slow to open or "not responding" on load, when asked which parts make it slow or what makes the file big, or before adding a stand-in or a link for a part.
---

# Stand-ins for a slow FreeCAD model

The knowledge is in `platform/freecad/LESSONS.md`. Read its first three sections before starting ("Why the printer
is slow to open", "Hidden parts are not tessellated", "Stand-ins"). This skill is the order to do things in.
**Add every new finding to `LESSONS.md` the day you learn it, in the same branch.**

## 1. Measure the open, the way the owner feels it

`$APP` (the FreeCAD AppImage) and `$NV` (the GPU prefix for GUI runs) are set at the top of `notes/scripts.md`.

```bash
VT350_MODEL=<model.FCStd> $NV $APP $PWD/cad/studies/open_time.py    # appends to cad/data/logs/open_time.log
```

One run varies by about ±10 s. Run 3 or more, alternating with the model you compare against, and compare medians.
File size does not predict open time (`LESSONS.md`), so don't use it as the measure.

## 2. Find what costs the time

```bash
TESS_COST_MODEL=<model.FCStd> $APP freecadcmd $PWD/platform/freecad/tess_cost.py
```

It ranks families and parts. It's a proxy: trust the order, not the seconds. Then **measure the candidates for
real**: 5 copies of the part in a small test document, opened in the GUI with `open_time.py`, against 5 copies of
each candidate stand-in. That's what predicted the lite-49 and lite-50 savings within a few seconds.

## 3. Choose the stand-in

- **A coarse mesh** (`Mesh::Feature`, 0.1 mm / 0.5 rad) suits almost any part: nothing to tessellate, and it still
  looks like the part. Pattern: `cad/passes/lite50_mesh_standins.py`.
- **A fitted shape** when the part has a simple envelope, such as a coil spring as a tube
  (`platform/freecad/standins.py`). Pattern: `cad/passes/lite49_spring_standins.py`.
- Things that **don't** help, and why: a hidden parent assembly, and App::Links over a hidden original
  (`LESSONS.md`).

## 4. Write the pass

A new pass in `cad/passes/`, modelled on the two above (see `AGENTS.md`, "The model"). For each real part:
- add the stand-in beside it, in the same App::Part, at the part's placement, in its colour;
- give the stand-in a `StandInFor` property holding the real part's Name;
- hide the real part with its **own** Visibility, not its parent's.

Checks the pass must make before it saves: the expected parts by label and face count; each part plain and directly
in an App::Part; the stand-in on its part (sampled points, and the box against the overlap of `BoundBox` and
`optimalBoundingBox`, since each overshoots on some B-splines); in the document, where it was built; the real part
hidden and unmoved. Dry run headless, then save from the GUI.

## 5. Prove it after the save

- **Open time:** step 1, alternating with the previous model.
- **Nothing else changed:** the part index (`<model>.parts.json`, written by the export) differs from the previous
  model only by any Part-shaped stand-ins. Mesh stand-ins don't appear in it at all.
- **Renders unchanged:** export with `platform/render/export_meshes.py`. Its log must say
  `stand-ins: N, drawing the real parts`. Then export again with `RENDER_STANDINS=1` (the quick preview): it must
  give the same buckets with the same part counts, and each bucket's box within a few hundredths of a mm.
- Row in `cad/README.md`, sentence in `notes/status.md`, findings in `LESSONS.md`.

## Copies: links, not stand-ins

When the same part appears several times (one per toolhead, one per dock), a link beats a stand-in for each copy:
the file stores the shape once, and the GUI tessellates it once for all its links (`LESSONS.md`, "Linked objects").

```bash
DUPES_MODEL=<model.FCStd> $APP freecadcmd $PWD/platform/freecad/dupes.py    # groups of copies, what linking saves
```

It prices each group from the zip (compressed bytes, the real file cost) and flags reflections (a link can't reflect)
and STL-made solids. A pass then calls `dupes.find(doc, dupes.object_bytes(src), names)` and `dupes.link_copies`
on an explicit list (model it on `cad/passes/lite51_links.py`), checking that each link lands where its copy was and
every part keeps its global box. Every walker reads links through `platform/freecad/linkgeo.py`; new code that walks
parts must too (`is_leaf`, `gshape`, `gplace`, never `isDerivedFrom('Part::Feature')` or `getGlobalPlacement`).
