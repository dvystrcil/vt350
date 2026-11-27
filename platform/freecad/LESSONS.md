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

## Materials: a model stores the UUID, the card lives outside (measured 2026-11-17)

- **A part's `ShapeMaterial` is saved as the material's UUID only** (`<Material uuid="..."/>` in `Document.xml`).
  Opened where no registered library has that card, the part silently comes back as `Default` (1e-9 kg/mm³): no
  error, no warning. Measured on FreeCAD 26.3 and the Flatpak 1.1.4.
- **A material made in a script and never saved to a library doesn't survive a reopen**, for the same reason.
  Make it as the editor's "Inherit New" does: `Materials.Material()`, `addPhysicalModel()` for each of the parent's
  models (else `setPhysicalValue("Density", ...)` raises "Property not found"), then
  `MaterialManager().save(library, material, "<Name>.FCMat", True)`.
- **Register the card folder before opening a model**: Preferences > Material > "Use materials from user defined
  directory", or `matlib.use_dir(path)` in a script (sets `Mod/Material/Resources/CustomMaterialsDir` and calls
  `refresh()`). The library then shows as "Custom". The setting is saved in `user.cfg` on exit, per install: the
  AppImage (`~/.config/FreeCAD/v26-3`) and the Flatpak (`~/.var/app/org.freecad.FreeCAD/config/FreeCAD/v1-1`)
  each need it.
- **The Flatpak has its own private `/tmp`**: a script under `/tmp` on the host isn't there. Pass it inline (`-c`).

## Gotchas

- **An object can sit in two Groups: walk up from the innermost one** (found 2026-11-19, lite-72, vt350#220). A part
  inside a group inside an `App::Part` is listed in the group's `Group` **and** the App::Part's. A walk that takes the
  first container it meets in `doc.Objects` (`par.setdefault(child, container)`) often gets the App::Part, and the
  path loses the groups in between: `export_meshes.py` wrote `Voron Trident v4 / Front right` where the part index had
  `Voron Trident v4 / Monolith gantry (…) / Front right`, so 510 parts' paths differed and the licence rules written on
  the index's paths missed 267 of them. Use `linkgeo.group_parents()` + `group_path()` (the innermost container),
  which both now share; tested in `test_group_parents.py`. Renders didn't change (no colour or selection rule names
  the dropped groups), only the paths.
- **Changing a linked part's shape: keep its Placement.** An `App::Link` applies its own placement to its target's
  geometry under the target's Placement. Setting `o.Shape` to a global-frame result (the usual `loc.Placement =
  container.inverse() * loc.Placement`) also rewrites `o.Placement`. The target still looks right, but every link to
  it moves: lite-62's first save shifted a dock's carriage copy (a link) 4.78 mm in Y. `transformShape(m)` with the
  default `copy=False` doesn't help: for a rigid `m` it only sets the shape's location, and the object's Placement
  replaces that. What works: rebuild the shape as a compound of its solids, each moved into the object's own frame
  (`solid.Placement = (container * P0).inverse() * solid.Placement`), with `P0` on top; or, simpler (measured
  2026-11-17, lite-67), with `copy=True`, which bakes the transform into the geometry and keeps cylinders and planes
  analytic (`transformGeometry` turns every face into a B-spline): `s.transformShape(P0.inverse().toMatrix(), True,
  False); s.Placement = P0; o.Shape = s`. That moved the target and its link 0.000 mm; `copy=False`, and "set
  `Placement`, then reset it", both put them 425 mm out. Then check every link's global shape (centroid and box), not
  just its volume (`cad/passes/lite62_trim_beacon_pads.py`, `cad/passes/lite67_dock_spacer.py`).
- **…but `copy=True` breaks a solid with offset-curve edges** (measured 2026-11-18, lite-68). `face.makeOffset2D(r)`
  gives `OffsetCurve` edges. A solid built from that face is valid, and so is a fuse with it, but after
  `transformShape(m, True, False)` it isn't (`isValid()` False). Changing only the location keeps it valid, but that
  doesn't survive the write (above). Fix: `face.makeOffset2D(r).toNurbs()` before extruding, so the edges are
  B-splines. `shape.fix(1e-7, 1e-7, 1e-7)` after the transform also repairs it. Check `isValid()` after the write,
  not only before it (`cad/passes/lite68_dock_pads.py`).
- **A model can hold more copies of a part than its main assembly shows** (lite-68). The dock keyslot plate had five
  copies: the Left / Right docks' own, two Part::Feature copies in the slot docks, and one App::Link. A pass that
  changes a part must find every copy by its target and shape (`linkgeo.link_target`, matching placement), not only
  by the label under the group it's working on. The "every other solid's box unchanged" check is what found the link.
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
- **`BSplineCurve.interpolate(..., FinalTangent=t)` can curl at the end** (emu4_lower, 2026-11-18). Interpolating the
  roof-to-EMU bowden routes (~480 mm, points every 3 mm, the last 25 mm a straight run) with a unit `FinalTangent` left
  a cusp in the last ~3 mm (radius ~0). emu-3's pass checked curvature at 2,000 samples and stepped over it; 4,000
  found it on every route. Dropping `FinalTangent` (the straight points already set the end direction) gave radius
  >= 83.6 mm and an end angle of 0.00 deg. Sample curvature densely, and check a fit near its ends.
- **Booleans on swept tubes can't be trusted for overlap checks** (emu4_lower, 2026-11-18). emu-3's five roof-exit
  bowdens cut 1.25 mm into their roof clamp caps (the first arc began inside the clamp's bore), yet
  `tube.common(cap).Volume` was 0; a re-routed tube gave 24.8 mm3 with a result box reaching 20 mm outside the cap.
  `distToShape` between the solids just says 0 (touching or inside). What works: the distance from the tube's
  **centre line** (the sweep's spine edge) to each part near it, against the tube's radius.
- **A segfault in `freecadcmd` loses everything the script printed** (stdout is buffered): the run ends with no
  output at all. When a call might crash, write to a file of your own and flush before each risky call, so the log
  shows where it died. (A syntax error shows only as "Exception while processing file: ... [message]".)
- **Notch a panel round what the overlap check finds** (lite-59): build the plain slab, list the parts it overlaps
  (`common().Volume`), and cut each one's box + clearance through the panel. Then no part is missed or hard-coded,
  but gate every hit with a predicate ("only in the latch band", "only the cable arms"): an unexpected hit fails
  the pass instead of quietly becoming a hole.
- **A big chamfer can quietly leave edges out** (lite70_roof_exit_low, 2026-11-18). A `Part::Chamfer` with ~70 edges
  on the cable channel came back valid, one solid, smaller in volume, and dozens of its edges were still sharp
  (whole 350 mm rims among them). No error, no warning. Check the result against the input: an edge that was due a
  chamfer and still has an edge lying on its line afterwards was missed (`printchamfer.unchamfered`). Then chamfer
  the missed ones one at a time on the result (`shape.makeChamfer(d, [edge])`). That's what `printchamfer.chamfer`
  does. Re-find each edge by geometry each time: a neighbour's chamfer trims its ends, so test "on the same line"
  rather than "same midpoint and length".
- **Bed and top faces: compare with a tolerance of ~0.01 mm, not 1e-3**: a face's `CenterOfMass` along a tilted
  print direction (a cap printed on its 45 deg split face) came out 0.001 above the lowest vertex.
- **Matching parts across two STEP files by size: a part's box is in world axes** (vt350#220, 2026-11-19). After
  `Import.insert`, `Shape.BoundBox` includes the part's placement, so a part turned by anything but 90° (a T-nut
  on a slanted clip) gets a bigger box than the same part upright in the other file, and a name + size match
  misses it. Compare sorted box sizes, and also measure each STEP product in its own frame: walk the STEP text from
  `PRODUCT` to its shape representation and take the box of its `VERTEX_POINT`s (plain python, no FreeCAD). That
  box is short on curved faces (it holds no arc bulge), so accept a match when either measure agrees.
- **A flat face after a boolean isn't always a `Plane`** (lite-72, 2026-11-19): lite-68's pad faces, made by
  extruding, cutting and `removeSplitter()`, include flat faces whose `Surface` is not `Part.Plane`, so a filter on
  `f.Surface.__class__.__name__ == "Plane"` found no top face on a 0.16 mm pad and `max()` raised. The STL showed the
  face at once. To find a face at a height, test its vertices' heights (every vertex within ~1e-4 of it), not its
  surface type.
- **A designer's variant STEPs often share one frame: fit the variant you have, place the one you want** (lite-73,
  vt350#263, 2026-11-19). DW-Tas's `main-body_<hotend>_*.step` files all have the same box and differ only round the
  hotend pocket, so `dupes.fit(uhf_step_shape, model_body)` (a rigid move, checked vertex by vertex) gives the move that
  puts `hex-main-body_DAV_*.step` exactly where the UHF body was, with no hole matching. Check the shared frame first
  (equal boxes, the faces that differ all in one region).
- **An assembly's parts can look mounted and not touch** (lite-73). lite-15 took the Dragon ACE stand-in, spacer and
  screws from DW-Tas's `A4Tv2_assembly.step` as placed there; the spacer's top was 8.5 mm below the UHF body's pocket
  ceiling, and every nozzle figure since was measured off a floating hotend. Box overlaps can't show a gap. Probe it:
  vertical lines (`Part.makeLine(...).common(shape).Edges`) round the axis give each part's material along Z, so
  "what is directly above the heat sink" is one number per line. Keep the lines off holes (at radius 8 on the
  diagonals they ran down the screw holes and found nothing).

## A pass that writes a derived file must accept that file in its post-merge state (2026-11-20, lite-73)

A pass that re-exports a printed STL writes it even in a dry run, and the PR commits it. The owner's GUI save runs
*after* the merge, so it sees the new STL, not the one the pass was written against. lite-73's precheck ("the
committed carriage STL is today's carriage") passed in every dry run and failed the real save: NOT SAVED. Make such
checks accept both states (before and already-done), and don't rewrite a derived file that's already current, so its
sha256 keeps matching the manifest and the print projects. Also: passes read `VT350_REPO`, default `~/Code/vt350`. A
dry run from a worktree reads and writes the **main checkout** unless you set `VT350_REPO=$PWD`.

## A mirror by `transformGeometry` makes B-splines, and BoundBox lies about them (2026-11-20, lite-73 → lite-74)

lite-73 cut the carriage's Beacon pocket deeper, then cut the Right Dock's copy of the carriage (`COMPOUND004`) with
the same cut tool mirrored in X by `shape.transformGeometry(matrix)`. The cut landed in the right place, but
`transformGeometry` turns planes into **B-spline faces**, and `BoundBox` overshoots on B-splines: the copy's box grew
7.8 mm in Y with its volume unchanged. `sweep_toolhead.py` compares boxes, so it refused lite-73 ("dock carriage copy
isn't the gantry carriage part"). `optimalBoundingBox` (`litelib.obb`) still agreed to 0.014. Four more things this
fix taught us:

- **Move rigidly with `transformShape`, `translate`, `rotate` or `mirror`, never `transformGeometry`**, which is for
  scaling. `Shape.mirror(base, normal)` keeps exact planes; a mirror through `transformGeometry` also made each
  `distToShape` take minutes.
- **`Shape.translate` only changes `Shape.Placement`** (and `linkgeo.gshape` puts the global placement there too). Code
  that then sets the shape's Placement, as every pass's "write in the object's own frame" step does, silently drops the
  move. Bake first: `pl = s.Placement; s.Placement = FreeCAD.Placement(); s.transformShape(pl.toMatrix(), True, False)`.
- **Booleans between near-coincident copies are useless** (`lite72_carriage.cut(lite73_carriage)` gave 16,600 mm³ for
  a 25 mm³ cut). Compare such shapes by sample vertices and `distToShape` instead.
- **A box check can't tell a mirror from a translation** of a part that's symmetric in X, as this carriage is. lite-74
  checks the copy point by point against the carriage moved by the pickup offset.

## A standoff's "top" depends on where you probe it: measure a ring (2026-11-21, lite-75)

Placing the Pi 5 on its bracket, the first probe took the standoff top 1.3 mm from each pilot hole's axis: X 108.05.
That point is on the chamfer round the hole. The flat top is X 108.100, from r 1.5 to 2.0, and the edge rounds off
again at r 2.5 (107.7). Placed on 108.05, the board overlapped all four standoffs (1.98 mm³). Before seating a part on a
boss, probe lines at several radii and angles round it (lite75_pi5.py: r 1.0..2.5, every 30°). Check that the radii you
seat on are one plane on every boss, and that nothing is higher. The same probe showed the GrabCAD board it replaces sat
0.75 mm inside those standoffs.

## A STEP's colours: ImportGui keeps them, Import drops them, and the render takes one per object (2026-11-21, lite-75)

- `Import.insert` (App only) imports a STEP's shapes without colours. In a GUI run, `ImportGui.insert` gives the part a
  per-face `ShapeAppearance` (12,882 entries for the simplified Pi 5).
- The render export (`platform/render/export_meshes.py`) colours each object by its first `ShapeAppearance` entry. One
  25-solid feature rendered all one colour, so give each solid its own Part::Feature.
- A solid's first face is not its colour: every first face of the Pi 5 was the STEP's light grey. Use the solid's most
  common face colour.
- Set the appearance **after** `doc.recompute()` and `Gui.updateGui()`. Before that, the new feature's first redraw
  resets it to the default grey.
- FreeCAD reads this STEP's PCB as grey and blue, not the green the file names (`COLOUR_RGB('Opaque(0,140,73)')`). A
  `colours.json` role (by label, "PCB") is the dependable way to colour it.

## Assigning `o.Shape` also sets `o.Placement` from the shape (2026-11-21, lite-76)

`feature.Shape = g` copies `g.Placement` into `feature.Placement`. A shape moved into the object's frame (for example
with `transformShape(gplace(o).inverse())`) has an identity Placement, so assigning it wipes the feature's own
Placement. lite-76's first dry run put the A/B stepper 50 mm low that way. The Z motor came out right only because its
Placement happened to be identity. Set `g.Placement = o.Placement` before assigning, with the geometry expressed in
the frame of `o.Placement`.

## Memory, not cores, sets a sweep's speed (2026-11-22, lite-77)

The batch lane's refresh sweep took 1 h 58 min – 2 h 01 min for lite-75, 76 and 77 on a 32-thread server that was
about 1% busy. Its log said `clashlib: 5 workers`. The pool sizes itself as
`min(CPUs − 2, (free MB − reserve) ÷ MB per worker)`, and each worker opens its own copy of the model (2.8 GB budgeted
per worker, 1 GB reserve), so the job's 16 GiB memory limit allowed 5 workers, half the CPU cap of 10. Adding CPUs
would have changed nothing. The fix is memory: 30 GiB fits 10 (dvystrcil/gpu-batch#55). The laptop is the same:
32 GB runs 4 workers on 12 threads.

- When a long run feels slow, read the `N workers` line before anything else, and compare it with the cores.
- In a container the limit that counts is the cgroup's (`memory.max`), not the host's `/proc/meminfo`.
- Run times and recommended hardware for outside users: [`../HARDWARE.md`](../HARDWARE.md).

## `import FreeCAD` works only in the AppImage's own Python (2026-11-22)

`python3 platform/freecad/test_litelib.py` fails with `ModuleNotFoundError: No module named 'FreeCAD'` even with
FreeCAD installed: the module lives inside the AppImage. Run any test that imports FreeCAD as
`$APP freecadcmd $PWD/<test>` (test_litelib: 68 tests, test_logos: 10, both OK). A plain-python test that imports
numpy/scipy (`cad/studies/flap_guide/test_rod.py`) is the opposite case: it needs the system's `python3-numpy` and
`python3-scipy`, and under `freecadcmd` it exits 0 without running anything, because `unittest.main()` sits behind
`if __name__ == "__main__"`. Don't read either failure as "needs an environment we don't have" until it has been
tried in the right interpreter.


## A swept tube's own Volume can be several % off; check a splice against its cut pieces

vt350-lite-78 (vt350#291) lengthened lite-36's Bowden tubes (a B-spline sweep plus a short cylinder end, one closed
shell, `isValid()` True) by cutting them across and filling the gap. The check "new volume = old volume + section x 17"
failed by ~300 mm3 on an 8458 mm3 tube: `Shape.Volume` of the original was ~4 % high. The two cut pieces
(`common()` with a box on each side of the cut) summed to 8137, and the result to that plus the fill, give or take
~0.3 % (B-spline volume integration; a compound of the same pieces gave yet another figure, 8395).

- Check a splice of a swept part against the sum of the pieces it was cut into, not against its original `Volume`,
  and allow ~0.5 %.
- Exact-volume checks (1e-5) still hold for prism-like parts (extrusions, boxes, panels): keep them there.

## Rebuilding a part from the pass that made it loses every later retrofit (2026-11-23, lite-78)

vt350-lite-78 (vt350#291) moved the nozzle-offset probe bracket by deleting it and rebuilding it with lite-61's code.
That brought back lite-61's shape, which needs supports. lite-71 had already fixed it at the owner's request: the arm
was carried down so the part prints on one flat face. The owner caught it in the preview STL.

- Before rebuilding a part from its original pass, search the later passes for its label (`grep -l "<label>"
  cad/passes/*.py`), and carry their changes into the rebuild. Better still, move the model's current part when the
  change is a plain move.
- Keep the later pass's check in the rebuild too (here: lite-71's "no face hangs" test), so the fix can't be lost again.

## Rounding a printed part: build order, and the first-layer chamfer as a taper (2026-11-23, lite-78)

The Mellow bracket (two plates and an arm, vt350#291) in the cast style (`parts/printed/README.md`): rounded, blended,
mating faces flat, a 0.5 chamfer on the bed. What OCC (FreeCAD 26.3) would and wouldn't do:

- **Order matters.** Fillet the arm's joins with the plates while the plates are still sharp prisms (with their outline
  corners drawn in the 2D profile). Once a plate's rim is rounded, the same join fillets fail at every radius.
- **A plate's rim as one tangent chain** (both sides, the R4 corner arcs and the top) rounds cleanly in one `makeFillet`.
  Rounding the outline by intersecting rounded extrusions (side view x plan x front view) gives a crease at each
  corner instead.
- **The first-layer chamfer can't be an edge chamfer where a rim round runs down to the bed:** `makeChamfer` on those
  bottom edges fails (4 of 24 per edge), and chamfering first makes the rim fillet invalid. Instead cut the bottom
  0.5 mm off and fuse back the footprint face extruded 0.5 down with `Part::Extrusion` `TaperAngle = -45`: same result,
  no edge operations.
- **`Shape.BoundBox` is loose on fillet (B-spline) surfaces:** a "stays inside the box" test on it fails for nothing.
  Use `optimalBoundingBox()`.
- Pick edges by plane and position, never by index: every fillet renumbers them.

## A pass's new group name must reach every list that sorts parts by group (2026-11-23, lite-78)

lite-78 rebuilt the Mellow Zero and its bracket in a new group, "Nozzle offset probe, low on the bed edge (lite-78,
#291)". The pass's own "bed-side" check used litelib's Z band and passed, but `sweep_toolhead.py` picks what rides
with the bed from an exact set of group names, which still named lite-61's group. So the Z sweep took the Zero for a
fixed part: the heater pad "landed" on it 8 mm down and print height fell from 334 to 100 mm. Found only at the
refresh. Now the bed set also matches the prefix "Nozzle offset probe" (and so does `cad/viewer/licences.json`).
Now there's one rule, `sweep_toolhead.rides_with_bed()`, and lite-78's pass checks its new parts with it, so the dry
run catches this in minutes. A pass that adds bed parts should do the same. When a pass renames or regroups a part, grep the repo for the old group's label (`grep -rn "<old label>" --include=*.py
--include=*.json`) and update each list in the same pass.

## A GUI pass with no window, and a fair "before" render (2026-11-24, lite-79)

- **A pass that needs the GUI (colours) can run without a window:** `PASS_GUI_NOTICE=none xvfb-run -a $APP <pass>.py`.
  `xvfb-run` gives FreeCAD a virtual display, so `ViewObject` exists and colours are set and checked; `PASS_GUI_NOTICE=none`
  skips the message box nobody would see to click (the outcome is still in the log). The process exits by itself.
- **A render takes its colours from the checkout it runs in** (`VT350_REPO`: its `cad/render/colours.json`), not from the
  model. Rendering the "before" model from the branch that changes `colours.json` shows the new colours on the old model.
  For a fair before, export the old lite-N from main. lite-79's first "before" showed both parts already orange that way.
- A part's colour in the FreeCAD file and in the renders can differ: the renders go by `colours.json` roles. lite-79's
  camera housing was dark grey in the file and white in the renders.

## A pass that reshapes a part it has already moved must carry the move into the new shape (2026-11-25, lite-80)

lite-80 moved the front uprights −3 in Y (by Placement), then re-drilled their gantry-joint holes from the shape it
had read at the start, and assigned it back with `o.Shape = ...`. Assigning a shape sets the Placement from it (see
"Assigning `o.Shape` also sets `o.Placement`"), so the uprights went back to their old Y and the dry run found 28
new collisions with the gantry bars. Its box check passed because it compared against the *old* box. Fix: when a
part is reshaped after a step has moved it, build the new shape from the moved one (or translate it by the move), and
check its box against the box the plan expects, never "unchanged".

## `Wire.makePipe` can segfault; sweep with `makePipeShell` (2026-11-25, lite-81)

Sweeping a circle along a long approximated B-spline (a bowden route, ~400 points smoothed and fitted) with
`path.makePipe(face)` crashed FreeCAD with SIGSEGV inside `BRepFill_Pipe::MakeShape`: the process dies, no exception,
and a pass's `try` can't catch it (the log just stops after the last check). `path.makePipeShell([profile], True, True)`
on the same path raises `Part.OCCError` instead, which a pass can catch and fall back from (lite-81 falls back to a
chain of cylinders and spheres along the resampled points). If a headless run's log stops with no `FAILED` line, run
it again with stdout kept: the crash trace names the OCC call.

## A clip round two touching runs: fuse the bodies first, then cut every bore (2026-11-26, lite-81)

- **Bore each sleeve for its own run, fuse the sleeves, and the walls sit inside the neighbour.** The PTFE tube and the
  O2S cable touch, so the tube sleeve's 1.6 mm wall ran through the cable. Dry run 10 found 80–140 mm³ per clip.
  Build it this way instead: fuse the outer cylinders into one body, fuse the bores, then `body.cut(bores)` once.
- **Cutting the swept runs out of the clip fails silently.** `clip.cut(run_solid)` on the chain-of-cylinders runs left
  two of the five clips unchanged, and dry run 11 still found the overlaps. Don't rely on a boolean with a sweep for a
  part's shape.
- **Many small spheres and cylinders fused into one part make OCC fail:** `multiFuse` then `cut` returned a Null shape
  or an invalid solid on 3 of 5 tools. A straight 12 mm clip on a run with R > 50 sags only ~0.2 mm, so it needs no
  curve. Keep a part's solid simple.
- **Check one part fast before the full pass.** A probe that imports the pass (`LITE81_AS_LIB=1`), builds one bundle
  and reports `common` volumes takes 45 s. A dry run takes ~40 min.

## Replacing a Link by a solid copy: carry ShapeMaterial over too (2026-11-26, lite-81)

lite-78's `unlink()` swapped five frame bars (App::Links made by `dupes.py`) for `Part::Feature` copies so they could be
spliced longer. It copied the label and the colour (`ShapeAppearance`) but not `ShapeMaterial`, so the copies came out
`Default`. Nothing failed: the pass's checks were all geometry. Three lites later the owner saw two frame bars render
grey (the render's frame rule wants an aluminium material), and their density was gone from the mass numbers too.

- When a pass replaces an object, copy everything that isn't geometry: `Label`, `ShapeMaterial`, the view's
  `ShapeAppearance`/`Transparency`/`Visibility`, and its group.
- Setting `ShapeMaterial` can repaint the part: save `ShapeAppearance` first and put it back (as `lite12_materials.py`).
- A cheap guard: compare `part_index`'s `material` column before and after a pass (no label should turn `Default`).
  lite-81 checks that every frame extrusion is aluminium.

## makePipeShell: try Frenet off before giving up on a pipe (2026-11-26, lite-81)

The dock lever's cable housing (#312) is a 700-point route that climbs and turns about 600 mm in 3D. On it,
`Wire.makePipeShell([profile], True, True)` (Frenet on) throws `BRepOffsetAPI_MakePipeShell::MakeSolid`, and the
pass fell back to a chain of 231 cylinders and spheres per housing. The same call with Frenet **off**
(`makePipeShell([profile], True, False)`) makes one valid solid with the right volume. The pass's `sweep()` tries
Frenet first and then, **for the housing only** (`frenet_off=True`), without it, before the chain.

Not everywhere: with Frenet off for every run, the tubes and cables whose Frenet pipe failed became no-Frenet pipes
instead of chains. Dry run 16 then found 8 overlaps (0.7-70 mm³) with the split clips, a sheave groove, an arm loop and a
leg guide, all sized round the chain with 0.4-0.6 mm of clearance. Every overlap involved a no-Frenet pipe, and the tool
whose runs were both chains had none. A fallback that changes a shape changes what the checks see: re-run every
check, not only the one the fallback was for.

Don't fuse the chain instead: `multiFuse` of those 231 pieces returned one valid solid of 4743 mm³ where the pipe is
about 12300. It reported success and quietly lost most of the volume. Always check a fused result's volume against
what it should be.

## A long diagonal sweep's bounding box meets everything: filter on its spine (2026-11-26, lite-81)

Dry run 13 of the lite-81 pass sat 5.5 h in its collision check with no output, and the parent process was at 10 cores. The
dock lever's cable housings are 695 mm pipes running diagonally up and back, so each one's bounding box met thousands
of parts it never comes near: 9346 pairs, each a full `common()`, some taking 60 s. Two fixes, both in the pass's
`solid_overlaps()`:

- Keep each pipe's spine (its points and radius) and skip a part whose box no spine point comes within r plus a margin
  of (the spline's tolerance + half the sample step). That's conservative, and it cut 9346 pairs to 780.
- Name each pair in `<log>.progress` before it starts, and log any pair over 20 s. A silent hour then becomes one line
  naming the pair.

Two more traps from the same runs: a common that is a zero-thickness sheet (a block screwed flush under a bar) can
report a small non-zero volume, so treat a result under 0.01 mm thick as touching. And `common()` can throw "Null
shape" on a pair that's 16 mm apart: fall back to `distToShape()` before calling it an overlap.
