# What we've learned about FreeCAD

Things that cost us time, measured on this model (FreeCAD 26.3rc2 AppImage, this laptop). Each entry says how
we know it. **Keep this current while working:** add a finding the day it's measured, not in a later docs pass.

## Why the printer is slow to open: tessellation, not file size

- When the GUI opens a file it turns every visible solid into triangles (tessellation) before it can draw it.
  That, not reading the file, is most of the open time. Headless (no view) lite-48 opens in 8.5 s; the GUI takes ~125 s.
- **File size doesn't predict the cost.** lite-48 halved the file (214 → 110 MB, the frame extrusions rebuilt) and
  the GUI open only went 133 → 123 s. Timing each of the 1390 parts (131 s of tessellation in all):

  | Part | Each | Tessellation (all of them) | Why |
  |---|---|---|---|
  | 5 "Spring v1" | 0.1 MB, 3 faces | 19 s | one helical B-spline surface, ~144k triangles |
  | 5 bowden tubes | 0.02 MB, 4 faces | ~9 s | a 520 mm swept B-spline tube |
  | 5 O2S toolboards | 14.5 MB, 11,584 faces | 10.5 s | a populated PCB, 224 solids |
  | 90 `_MR` bearing parts | small | 8.6 s | toroidal raceways and balls |
  | 6 SpeedClips | **90 MB** in all | only 2.9 s | big file, cheap to draw |

- How to measure: `cad/studies/open_time.py` (GUI open + first draw, appended to `cad/data/logs/open_time.log`).
  Run it several times, alternating the models: one run varies by ±10 s; medians of 5–6 runs agree within ~1 s.
  For a single part, put 5 copies in a small test document and time that; it predicted the lite-49 saving exactly.

## Hidden parts are not tessellated (measured 2026-11-16)

Test documents with the 5 real springs, GUI open:

| The springs | Open |
|---|---|
| visible | 14.1 / 14.7 s |
| **hidden** (each spring's own Visibility off) | **0.3 / 0.2 s** |
| visible, but each inside a hidden App::Part | 15.5 / 14.8 s |
| hidden, then shown after the open | 0.6 s, then 14.7 s+ when shown |

- A hidden part's geometry is loaded, but its triangles aren't built until it's shown.
- **It's the part's own visibility that counts.** Hiding a parent assembly hides its children on screen, but they
  are still tessellated. Hiding a whole toolhead from the top of the tree saves nothing.
- The cost isn't gone, only deferred: showing the part later pays it then.

## Stand-ins: cheap in the GUI, the real part in renders

A stand-in is a cheap shape shown in place of an expensive part. The real part stays in the model, **hidden**, so it
costs nothing on open (above) and is there for renders.

- **How it's wired:** the stand-in sits beside the real part in the same App::Part, at its placement, in its colour,
  with a `StandInFor` property naming the real part.
  - The stand-in can be a shape (`Part::Feature`, the springs' tubes) or a coarse mesh (`Mesh::Feature`).
  - The render export (`platform/render/export_meshes.py`, rule `colours.standin_skip`) always walks the real part,
    though hidden, so it keeps its own bucket, colour role and motion group. It never exports the stand-in.
  - `VT350_STANDINS=1` is a quick preview: it draws each real part with its stand-in's geometry instead of meshing
    the real shape (`colours.standin_source`).
  - A `Mesh::Feature` isn't a `Part::Feature`, so the passes, clash checks and part index, which walk
    Part::Features, don't see mesh stand-ins at all.
- **To see a real part in the GUI:** select it in the tree and press Space. That pays its tessellation then.
- **Springs (lite-49):** a plain tube fitted to the coil (`platform/freecad/standins.py`). Printer open: median 125.6 → 111.5 s.
- **Choosing a stand-in shape** (5 copies each, GUI open; the real parts as they are vs two generic stand-ins):

  | Part ×5 | Real | Coarse mesh (0.1 mm) | One box per solid |
  |---|---|---|---|
  | Spring | 14.4 s | – | tube 0.2 s, ring stack 2.3 s |
  | Bowden tube | 13.0–13.5 s | 0.3–0.6 s | – |
  | O2S toolboard | 12.6–13.1 s | 0.9–1.0 s | 0.9–1.0 s |
  | Smart Sensor | 8.0–9.4 s | 0.7 s | 0.5–0.6 s |
  | Heat block | 5.4 s | 0.3 s | – |
  | Bearing (18 parts) | 4.2–4.4 s | 0.3 s | 0.2 s |

  A coarse **mesh** (`Mesh::Feature`, already triangles, so nothing to tessellate) is about as fast as boxes and
  still looks like the part, so it works as one generic stand-in for any part.

## Linked objects (App::Link): tessellated once (measured 2026-11-16)

Five copies of a part as separate Part::Features vs one part plus `App::Link`s to it, GUI open (two runs each):

| 5 copies of | Separate copies | 1 part + links (part visible) | 1 part hidden + 5 links |
|---|---|---|---|
| O2S toolboard | 14.5 / 13.2 s, 16 MB | 3.1 / 3.1 s, 3 MB | 3.0 / 3.1 s |
| Bowden tube | 14.7 / 13.7 s | 3.2 / 3.1 s | 3.3 / 3.1 s |

- **Links share the original's triangles:** five links cost about what one copy does, and the file stores the
  shape once.
- **A hidden original is still tessellated if a visible link shows it.** Hiding saves nothing then: the links
  need its triangles. So stand-ins and links don't combine. To skip a linked part's cost, hide the links too.
- **Not used in this model (yet).** The 5 toolheads are separate copies (each its own Part::Features). Making them
  links to one toolhead would cut every toolhead part's open cost to a fifth. But the motion groups, clash sweeps,
  part index, passes and render export all walk Part::Features by name, so that would be a restructure, not a pass.

## Gotchas

- **A GUI script named `build.py` never runs.** FreeCAD runs a `.py` argument by importing it by its module name,
  and another module called `build` is found first. The GUI just sits there. Give scripts distinctive names.
- **A crash-recovery dialog blocks scripted GUI runs.** A document left open when FreeCAD was killed leaves an
  autosave in `~/.cache/FreeCAD/v26-3/Cache/FreeCAD_Doc_*/fc_recovery_file.*`, and every GUI start offers it.
  A scripted run waits behind that dialog forever. Move the folder aside.
- **`Shape.BoundBox` is loose on B-spline surfaces:** it follows the control polygon. Use the tight box,
  `optimalBoundingBox` (`litelib.obb`). A spring's loose box was 7.65 mm across; the coil is 6.905.
- **`distToShape` is slow on a big multi-solid shape.** 60 points against the 224-solid O2S board took ~5 minutes.
  Check a point only against the faces whose box (enlarged by the tolerance) contains it.
- **A trimmed face's parameter range is the rectangle round it.** Sampling a grid over `ParameterRange` lands
  points off the face, for example on a plane face round a circular wire end. Sample edges instead, or check `isInside`.
- **`removeSplitter()` changes the shape it's called on.** If the result is invalid, the original is broken too.
  Call it on a copy.
- **A Part::Feature's `Placement` *is* its shape's placement.** Setting `o.Shape` (in the parent's frame) and then
  resetting `o.Placement` throws the offset away. It's only right under an identity parent; the door frame landed
  78 mm out. Check each part's position in the document after a pass, and diff the post-save part index.
- **Fasteners-workbench screws are `Part::FeaturePython`:** they regenerate from their properties. Move them by
  `Placement` only.
- **Imported extrusions break booleans** (94-pole B-spline edges, 0.005 mm gaps, a profile 0.002 out of flat), and
  their end faces carry the tapped bore. To rebuild one, take the profile from a slice in the middle
  (`platform/freecad/profile_lib.py`).
- **Headless `freecadcmd` has no `ViewObject`**, so no colours (an object's own `Visibility` property does exist).
  Our passes dry-run headless and save only from a GUI run.
