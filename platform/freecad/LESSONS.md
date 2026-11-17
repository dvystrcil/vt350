# What we've learned about FreeCAD

Things that cost us time, measured on the VT350 model (FreeCAD 26.3rc2 AppImage, one laptop), but true of FreeCAD in general. Each entry says how
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
  | 6 SpeedClips | **90 MB** raw (29 MB in the zip) | only 2.9 s | big file, cheap to draw |

- How to measure: `cad/studies/open_time.py` (GUI open + first draw, appended to `cad/data/logs/open_time.log`).
  Run it several times, alternating the models: one run varies by ±10 s; medians of 5–6 runs agree within ~1 s.
  For a single part, put 5 copies in a small test document and time that; it predicted the lite-49 saving exactly.
- **Finding the expensive parts:** `platform/freecad/tess_cost.py` (headless) times `Shape.tessellate()` part by part
  at 0.5 % of each part's box diagonal and ranks families and parts. It's a **ranking proxy**, checked against GUI
  opens of six families (each within about 2×). Don't trust its absolute seconds, and confirm any fix with GUI opens.
  - **`MeshPart.meshFromShape` with the GUI's own Deviation and angular defaults is NOT a usable proxy.** On lite-48
    it gave 44 s in all and missed the springs and bowdens, the GUI's two worst families (measured 2026-11-16). So
    the GUI's cost on those swept B-spline surfaces isn't just meshing at its default settings; why is still open.
- **After lite-50 the cost is spread thin** (`tess_cost.py`, 2026-11-16): 72 s across 1,280 visible parts, the
  biggest family 4.2 s (53 M3×8 screws), then SpeedClips, hub housings and 2510 fans at ~3 s each. More stand-ins
  give less and less back from here.

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
  - `RENDER_STANDINS=1` is a quick preview: it draws each real part with its stand-in's geometry instead of meshing
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
- **lite-50:** mesh stand-ins for those five families (110 parts). Printer open, 3 alternating pairs: median
  120.7 → **83.6 s** (the test documents predicted ~40 s off; it was 37). The file grew 110 → 125 MB with the
  meshes stored. Since lite-47 the open went 133.5 → 83.6 s, and file size explained almost none of it.

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
- **Used from lite-51 (vt350#195):** 22 copies became links (SpeedClips, O2S boards, Smart Sensors and their mesh
  stand-ins, one carriage compound), found and made by `platform/freecad/dupes.py`. On a scratch copy of lite-50:
  file 124 → 67.7 MB, save 19.2 → 9.5 s, headless open 9.7 → 4.5 s, and the part index of all 1,395 parts identical.
  `dupes.py` finds 89 MB of copies in lite-50 in all; most of the rest are the ×5 toolhead parts.
- **What a link is to code that walks parts** (each found the hard way, 2026-11-16). `platform/freecad/linkgeo.py`
  handles all of it; walk parts through it:
  - A link is **not a Part::Feature**, so `isDerivedFrom('Part::Feature')` filters drop it silently.
  - A link has **no `getGlobalPlacement`**. Its global placement is its parents' times its own Placement
    (`linkgeo.gplace`). FreeCAD 26.3 deprecates `getGlobalPlacement` anyway (removed in 27.2, "does not handle Links").
  - A link **has `.Shape`** (and `.Mesh` for a link to a mesh): the target's raw geometry. Placed at `gplace(link)` it
    is exactly the copy it replaced. That Shape is a **Compound wrapper**: it has `.Solids` but no `.CenterOfMass`.
  - A link has **no `ShapeMaterial`**: it shows its target's. Read material and colour from
    `linkgeo.link_target(o)`.
  - **A link's view provider can carry a `ShapeAppearance` that isn't drawn.** The GUI draws the target's colours
    unless the link sets `OverrideMaterial` or `OverrideMaterialList`. lite-52's first GUI run read the link's own
    appearance and failed its colour check on all 1,001 links, which were in fact correct (2026-11-16). To check what
    a link shows: no override, then compare the target's appearance.
  - **A link shows its master's colour, so group copies by colour before linking** (`dupes.find(split=...)`). In
    lite-51, 32 copies were coloured unlike their master (some `Component21`s, the MR148ZZ shields, two extrusions).
  - **A fit within tolerance can still land microns off.** lite-51's zip ties fit their master but their links would
    have landed up to 3 µm away. `dupes.landing(group)` predicts each landing without changing the document; keep
    those copies real (`Group.drop`).
  - **Moving a master doesn't move its links**: each link places the target's raw shape by its own Placement
    (`test_links_fc.MovingMaster`). The motion player can move a head whose parts are masters of the other heads'.
    But editing a master's *shape* changes every link: unlink a copy before editing it alone.
  - A link appears in its target's **`InList`**: a check like "consumed by a leaf in its InList" must skip links.
  - **Names can be kept.** Remove the copy, then `addObject("App::Link", same_name)` gets that Name back, so motion
    groups and clash lists that name parts keep working.
- **Fitting a copy to its master** (`dupes.fit`), measured on lite-50:
  - Parts' raw geometry is often baked where it was imported (each SpeedClip's STL at its own spot, turned), so a
    copy is master × some rigid move, not master at the copy's Placement.
  - **FreeCAD's principal axes aren't always right-handed**: build the third from the cross product, or every
    candidate rotation comes out a reflection.
  - **A box-corner offset or principal-axes rotation is only near** (0.4 µm off on the SpeedClips). Refine with a
    least-squares fit on the matched vertices (Kabsch): the residual drops to ~1e-12 mm.
  - **An open mesh's `Volume` isn't stable**: lite-50's board stand-ins fit each other exactly, yet their volumes
    were 6431.0–6435.7 (areas within 3e-6). Group meshes by area and box size.
  - **A mesh's `BoundBox` includes its Placement** (a shape's raw copy doesn't): compare raw meshes.
  - **An L-shape is not a test of reflection**: it has a mirror plane, so its mirror image is a rotation of it. Use
    three unequal arms from a corner.

## File size: measure the zip, find the copies (measured 2026-11-16, lite-50)

- **An `.FCStd` is a zip; size it by the compressed entries** (`unzip -v`, column 3), not by raw `.brp` sizes. B-rep
  text compresses 3–7×: lite-50's SpeedClips are 90 MB raw but 29 MB of the 125 MB file. Of lite-50's 124 MB
  compressed, 106 MB is `.brp` shapes and 14.5 MB the lite-50 mesh stand-ins (`.bms`). It's a long tail:
  19 shapes over 1 MB hold 57 MB, and 440 between 10 kB and 1 MB hold 45 MB.
- **Each Part::Feature's shape is stored in full**, even when another object has the same shape. Equal zip CRCs
  find only byte-identical copies (23.7 MB in lite-50). A copy that has been moved differs in bytes. To find
  congruent copies, group solids by (volume, area, face count): in lite-50 that's 184 groups, and storing each
  once would save **80 MB**, 45 MB of it in the ×5 toolhead parts.
- **An STL turned into a solid is easy to spot:** every face is a planar triangle (the SpeedClips: 14,712 faces,
  all triangles, 4.9 MB compressed each). `removeSplitter()` doesn't rescue one: 14,712 → 10,085 faces, 30 s,
  and the result is **invalid**. Replace it with real geometry or a link.

## Gotchas

- **A GUI script named `build.py` never runs.** FreeCAD runs a `.py` argument by importing it by its module name,
  and another module called `build` is found first. The GUI just sits there. Give scripts distinctive names.
- **A crash-recovery dialog blocks scripted GUI runs.** A document left open when FreeCAD was killed leaves an
  autosave in `~/.cache/FreeCAD/v26-3/Cache/FreeCAD_Doc_*/fc_recovery_file.*`, and every GUI start offers it.
  A scripted run waits behind that dialog forever. Move the folder aside.
- **Neither box is always tight on B-spline surfaces.** `Shape.BoundBox` follows the control polygon: a spring's
  box was 7.65 mm across, the coil 6.905. `optimalBoundingBox` (`litelib.obb`) can overshoot instead: 1.4 mm on the
  heat blocks' threaded ends, where `BoundBox`, the mesh and points along every edge all agreed. Both contain the
  shape, so take their overlap (`tight()` in `cad/passes/lite50_mesh_standins.py`).
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
- **A handed copy needs a mirror, not a turn** (lite-56). Copying a door onto another face with its hinges on the
  other edge: `shape.mirror(base, normal)` (one mirror across x + y = 0 both turned the front door onto the side face
  and put its hinges at the rear). The copies are reflected, so they can't be App::Links (`dupes.py` reports them
  as reflected); handles and latches become mirrored prints.
- **A mesh becomes a solid in two calls** (lite-57): `sh = Part.Shape(); sh.makeShapeFromMesh(mesh.Topology, 0.05)`,
  then `Part.makeSolid(sh)`. Check `isValid()` and that its volume matches the mesh's: then the usual `common()`
  overlap checks work on it. A 2,200-facet printed part is cheap enough to keep as a solid.
- **An overlap check is how to prove a part sits in a slot** (lite-57 holder keys, lite-58 door sheets): put it where
  the slot should be and check it against the profile. 0 overlap means open slot, so the check guards the design,
  not just the pass.
- **Sweeping a round tube along a 3D spline** (emu3_bowdens, 2026-11-17, PTFE 4.12 OD, ~470 mm routes with arcs and
  straights): `Wire.makePipeShell([circle], True, True)` (Frenet) made a valid solid of only 57 % of pi r^2 L: the
  frame twists on the straights. `makePipeShell(.., True, False)` (corrected Frenet) failed in `MakeSolid`.
  `Wire.makePipe(face)` **segfaulted** freecadcmd. A loft through circles was 10 % short. What works:
  `ps = Part.BRepOffsetAPI.MakePipeShell(wire); ps.setBiNormalMode(V(1, 0, 0)); ps.add(circle); ps.build();
  ps.makeSolid()` with the binormal along the axis the route is (nearly) flat across: within 0.8 % of pi r^2 L.
  Check a sweep's volume against pi r^2 L: `isValid()` passed on the twisted one. A sweep can also come out inside
  out (negative volume); `shape.reverse()` fixes that.
- **A segfault in `freecadcmd` loses everything the script printed** (stdout is buffered): the run ends with no
  output at all. When a call might crash, write to a file of your own and flush before each risky call, so the log
  shows where it died. (A syntax error shows only as "Exception while processing file: ... [message]".)
- **Notch a panel round what the overlap check finds** (lite-59): build the plain slab, list the parts it overlaps
  (`common().Volume`), and cut each one's box + clearance through the panel. Then no part is missed or hard-coded,
  but gate every hit with a predicate ("only in the latch band", "only the cable arms"): an unexpected hit fails
  the pass instead of quietly becoming a hole.
