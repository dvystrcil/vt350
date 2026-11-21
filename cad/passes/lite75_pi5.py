# GUI pass: vt350-lite-74 + vt350-ebox-3.FCStd -> vt350-lite-75 + vt350-ebox-4.FCStd   (headless = dry run, never saves)
# vt350#268, #5. The e-box's Raspberry Pi 5 becomes Eduard Mandache's simplified model (owner, 2026-11-20, after the
# study https://dvystrcil.github.io/vt350/pi5-models.html: it matches Raspberry Pi Ltd's official STEP to 0.1 mm over
# all its surface, 25 solids, CC BY-SA 4.0), from cad/library/electronics/raspberry-pi-5/simplified-mandache/.
#  - Out: the GrabCAD Pi 5 (Mateusz Zelek; show-only terms), the App::Part `RASPBERRY_PI_5_1 v1` and everything in it.
#    It sat 0.735 mm inside the bracket's standoffs, its holes 0.12-0.14 mm off the screws.
#  - In: a new App::Part `Raspberry Pi 5 (simplified, Mandache)` in `Pi Assembly`, holding the STEP's 25 solids as 25 parts,
#    each with its STEP colour, the PCB labelled `Raspberry Pi 5 PCB` (its own group, so cad/viewer/licences.json
#    can credit it). Placed by the real mount, not by the old board:
#    its 4 mounting holes (Ø2.7, 58 x 49) on the bracket's 4 pilot-hole axes, its PCB's back face on the bracket's
#    standoff tops. Orientation as the old board: components face +X, the USB/Ethernet end at +Y, Ethernet at low Z
#    (STEP x -> +Y, y -> +Z, z -> +X).
#  - The 4 M2 x 10 self-tapping screws slide along their axes so their heads seat on the new PCB's front face.
#  - lite-75 = lite-74 with the e-box envelope's label pointing at vt350-ebox-4.FCStd (its box checked unchanged).
# Checks (refuses to save on any): the STEP's sha256 is source.json's; 25 solids, one PCB with 4 Ø2.7 holes 58 x 49;
# in ebox-3, one GrabCAD Pi, the bracket's 4 pilot holes 58 x 49 with the 4 screws on their axes and a flat standoff top
# at each; after: the board's holes on the pilot axes (< 0.01), its PCB back on the standoff tops (< 0.01), the screw
# heads on its PCB front (< 0.01); no overlap of the new board or the moved screws with any e-box part beyond what the
# screws had before (the self-tapping shank in the bracket's pilot hole); the board inside the e-box; every other e-box
# solid's box unchanged, and so the e-box's overall box; lite-75's solids = lite-74's, the envelope's box unchanged.
import FreeCAD, Part, Import, hashlib, json, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-74.FCStd", f"{MODELS}/vt350-lite-75.FCStd"
EBOX3, EBOX4 = f"{MODELS}/vt350-ebox-3.FCStd", f"{MODELS}/vt350-ebox-4.FCStd"
LIB = os.path.join(_REPO, "cad/library/electronics/raspberry-pi-5/simplified-mandache")
STEP = os.path.join(LIB, "raspberry_pi_5.step")
OLD = "RASPBERRY_PI_5_1 v1"                    # the GrabCAD Pi's App::Part (cad/viewer/licences.json)
ASSY, BRACKET = "Pi Assembly", "Raspberry_Bracket"
SCREWS = [f"M2x10 Selftapping screw00{i}" for i in (6, 7, 8, 9)]   # the board's 4 screws (Fasteners055)
NEW_PART, NEW_BOARD = "Raspberry Pi 5 (simplified, Mandache)", "Raspberry Pi 5 (simplified)"
ENV = "Ebox envelope"
HOLE_D, PILOT_D = 2.7, 1.9
PITCH = (58.0, 49.0)
TOL = 0.01
INSIDE = (64.0, 160.0, -58.0, 480.0, -30.0, 670.0)   # lite57_din_rails.py: the e-box's inside


def cyl_faces(s, d, axis):
    """Cylindrical faces of diameter d (0.05) whose axis is parallel to `axis`: [(centre of the face's box), ...]."""
    out = []
    for f in s.Faces:
        su = f.Surface
        if su.__class__.__name__ == "Cylinder" and abs(2 * su.Radius - d) < 0.05 and abs(su.Axis.dot(axis)) > 0.999:
            out.append(f.BoundBox.Center)
    uniq = []
    for c in out:
        if all((c - u).Length > 0.05 for u in uniq): uniq.append(c)
    return uniq


def grid(pts, a, b):
    """4 points on a rectangle in coordinates a, b (attribute names) with PITCH sides, sorted (a, b)."""
    if len(pts) != 4: return None
    pts = sorted(pts, key=lambda q: (round(getattr(q, a), 2), round(getattr(q, b), 2)))
    A = sorted({round(getattr(q, a), 3) for q in pts}); B = sorted({round(getattr(q, b), 3) for q in pts})
    if len(A) != 2 or len(B) != 2: return None
    return pts if abs(A[1] - A[0] - PITCH[0]) < 0.02 and abs(B[1] - B[0] - PITCH[1]) < 0.02 else None


def along(shape, y, z, x0=90.0, x1=130.0):
    """The material of `shape` on the line parallel to X at (y, z): [(xmin, xmax), ...]."""
    return sorted((min(v.Point.x for v in e.Vertexes), max(v.Point.x for v in e.Vertexes))
                  for e in Part.makeLine(V(x0, y, z), V(x1, y, z)).common(shape).Edges)


def descendants(o):
    out = []
    for c in getattr(o, "Group", []) or []:
        out += descendants(c) + [c]
    return out


def main(p):
    # ---- the chosen STEP
    src = json.load(open(os.path.join(LIB, "source.json")))
    sha = hashlib.sha256(open(STEP, "rb").read()).hexdigest()
    p.check(sha == src["files"][0]["sha256"], f"{os.path.relpath(STEP, _REPO)} is the library's file (sha256 {sha[:12]})")
    sd = FreeCAD.newDocument("pi5step")
    if FreeCAD.GuiUp:                            # ImportGui keeps the STEP's per-face colours; Import.insert drops them
        import ImportGui; ImportGui.insert(STEP, sd.Name); FreeCAD.Gui.updateGui()
    else: Import.insert(STEP, sd.Name)
    so = [o for o in sd.Objects if o.TypeId == "Part::Feature" and o.Shape.Solids]
    p.check(len(so) == 1 and len(so[0].Shape.Solids) == 25, f"the STEP: one part of 25 solids ({[(o.Label, len(o.Shape.Solids)) for o in so]})")
    if p.errs: return p.finish([])
    P = so[0].Shape.copy()
    pcb = [s for s in P.Solids if s.BoundBox.XLength > 80 and s.BoundBox.YLength > 50 and s.BoundBox.ZLength < 2.5]
    p.check(len(pcb) == 1, f"one PCB solid ({len(pcb)})")
    if p.errs: return p.finish([])
    pcb = pcb[0]
    zb = [f for f in pcb.Faces if f.Surface.__class__.__name__ == "Plane" and abs(f.Surface.Axis.z) > 0.999]
    zlo, zhi = min(f.BoundBox.ZMin for f in zb), max(f.BoundBox.ZMax for f in zb)
    sh = grid(cyl_faces(pcb, HOLE_D, V(0, 0, 1)), "x", "y")
    p.check(sh is not None, f"the PCB's 4 mounting holes, Ø{HOLE_D}, {PITCH[0]} x {PITCH[1]} ({sh and [(round(q.x, 3), round(q.y, 3)) for q in sh]}); "
                            f"PCB Z {zlo:.3f}..{zhi:.3f} ({zhi - zlo:.3f} thick)")
    if p.errs: return p.finish([])
    # ---- ebox-3: the old board, the bracket's pilot holes and standoffs, the screws
    eb = p.open(EBOX3); ed = eb.doc
    old = [o for o in ed.Objects if o.Label == OLD and o.TypeId == "App::Part"]
    assy = [o for o in ed.Objects if o.Label == ASSY and o.TypeId == "App::Part"]
    br = [o for o in eb.leaves if o.Label == BRACKET]
    sc = [o for o in eb.leaves if o.Label in SCREWS]
    p.check(len(old) == 1 and len(assy) == 1 and len(br) == 1 and len(sc) == 4,
            f"ebox-3: the GrabCAD Pi ({len(old)}), {ASSY} ({len(assy)}), the bracket ({len(br)}), its 4 screws ({len(sc)})")
    if p.errs: return p.finish([])
    old, assy, br = old[0], assy[0], br[0]
    gone = [o for o in descendants(old)]
    gone_leaf = {o.Name for o in gone if o.Name in eb.shapes}
    oldbox = FreeCAD.BoundBox(); [oldbox.add(eb.shapes[n].BoundBox) for n in gone_leaf]
    p.log(f"the GrabCAD Pi: {len(gone)} objects, {len(gone_leaf)} solids-bearing, box {oldbox}")
    B = eb.shapes[br.Name]
    ph = grid(cyl_faces(B, PILOT_D, V(1, 0, 0)), "y", "z")
    p.check(ph is not None, f"the bracket's 4 pilot holes, Ø{PILOT_D}, {PITCH[0]} x {PITCH[1]} along X "
                            f"({ph and [(round(q.y, 3), round(q.z, 3)) for q in ph]})")
    if p.errs: return p.finish([])
    # the standoffs' tops: the bracket's highest X on lines along X round each pilot hole, every 30 degrees. Each
    # standoff has a chamfer at its hole (r 1.0), a flat top (r 1.5 .. 2.0) and a rounded edge (r 2.5): the PCB's back
    # goes on the flat top, which must be one plane on all four.
    import math
    ring = {}
    for q in ph:
        for r in (1.0, 1.5, 1.75, 2.0, 2.5):
            for k in range(12):
                a = k * math.pi / 6; t = max((b for _, b in along(B, q.y + r * math.cos(a), q.z + r * math.sin(a))), default=None)
                if t is not None: ring.setdefault(r, []).append(round(t, 4))
    p.log(f"the bracket's top round the pilot holes (r: X min..max over 4 holes x 12 angles): "
          f"{ {r: (min(v), max(v), len(v)) for r, v in ring.items()} }")
    flat = ring.get(1.5, []) + ring.get(1.75, []) + ring.get(2.0, [])
    p.check(len(flat) == 144 and max(flat) - min(flat) < 1e-3 and max(t for v in ring.values() for t in v) <= max(flat) + 1e-3,
            f"a flat standoff top round every pilot hole, r 1.5..2.0, nothing higher: X {min(flat) if flat else 0:.4f}..{max(flat) if flat else 0:.4f}")
    if p.errs: return p.finish([])
    xs = max(flat)
    screw_axis = {}
    for s in sc:
        S = eb.shapes[s.Name]; c = cyl_faces(S, 2.2, V(1, 0, 0))
        near = [q for q in ph if c and abs(c[0].y - q.y) < TOL and abs(c[0].z - q.z) < TOL]
        p.check(len(c) == 1 and len(near) == 1, f"{s.Label}: on a pilot hole's axis ({c and (round(c[0].y, 3), round(c[0].z, 3))})")
        pl = sorted(f.BoundBox.XMin for f in S.Faces if f.Surface.__class__.__name__ == "Plane" and abs(f.Surface.Axis.x) > 0.999)
        screw_axis[s.Name] = pl                   # [tip, head underside, head top]
    p.check(all(len(v) == 3 for v in screw_axis.values()) and len({round(v[1], 4) for v in screw_axis.values()}) == 1,
            f"the screws' tip / head-underside / head-top planes {sorted({tuple(round(x, 3) for x in v) for v in screw_axis.values()})}")
    if p.errs: return p.finish([])
    under = list(screw_axis.values())[0][1]
    # ---- the board's placement: STEP x -> +Y, y -> +Z, z -> +X; hole (min x, min y) on the pilot (min Y, min Z),
    # the PCB's back (z = zlo) on the standoff tops
    R = FreeCAD.Rotation(FreeCAD.Matrix(0, 0, 1, 0,
                                        1, 0, 0, 0,
                                        0, 1, 0, 0,
                                        0, 0, 0, 1))
    h0, q0 = sh[0], ph[0]
    T = FreeCAD.Placement(V(xs, q0.y, q0.z) - R.multVec(V(h0.x, h0.y, zlo)), R)
    G = P.copy(); G.Placement = FreeCAD.Placement(); G.transformShape(T.toMatrix(), True, False)
    gh = cyl_faces(Part.makeCompound([s for s in G.Solids if s.BoundBox.YLength > 80 and s.BoundBox.ZLength > 50]), HOLE_D, V(1, 0, 0))
    dev = max(min(((g.y - q.y) ** 2 + (g.z - q.z) ** 2) ** 0.5 for g in gh) for q in ph) if len(gh) == 4 else 99
    p.check(dev < TOL, f"the board's 4 holes on the pilot axes (worst {dev:.4f} mm)")
    GP = [s for s in G.Solids if s.BoundBox.YLength > 80 and s.BoundBox.ZLength > 50][0]
    back, front = GP.BoundBox.XMin, GP.BoundBox.XMax
    p.check(abs(back - xs) < TOL, f"the PCB's back on the standoff tops (X {back:.4f} / {xs:.4f})")
    sdx = front - under
    p.log(f"the screws: head undersides X {under:.4f}, the PCB's front {front:.4f}: moved {sdx:+.4f} along their axes")
    ob = old and FreeCAD.BoundBox(oldbox)
    p.log(f"new board box {G.BoundBox}; the GrabCAD board's {ob}")
    in_ = INSIDE; gb = G.BoundBox
    p.check(in_[0] <= gb.XMin and gb.XMax <= in_[1] and in_[2] <= gb.YMin and gb.YMax <= in_[3] and in_[4] <= gb.ZMin and gb.ZMax <= in_[5],
            f"the board inside the e-box ({gb})")
    if p.errs: return p.finish([])
    # ---- before: the screws' overlaps (with the old board gone)
    screws = {s.Name for s in sc}
    def pairs(names, shapes, skip):
        """Every pair (a in names, n) whose boxes meet, each pair once (a board-screw pair counts)."""
        out = set()
        for a in names:
            for n, s in shapes.items():
                if n != a and n not in skip and shapes[a].BoundBox.intersect(s.BoundBox): out.add(tuple(sorted((a, n))))
        return sorted(out)
    P0 = pairs(screws, eb.shapes, gone_leaf)
    before = dict(zip(P0, p.volumes([(eb.shapes[a], eb.shapes[b]) for a, b in P0])))
    box0 = {n: s.BoundBox for n, s in eb.shapes.items() if n not in gone_leaf}
    all0 = FreeCAD.BoundBox(); [all0.add(s.BoundBox) for s in eb.shapes.values()]
    # ---- write the e-box
    # one Part::Feature per STEP solid, each with its own STEP colour (the render export takes one colour per object,
    # its first appearance entry: one 25-solid feature rendered all one colour). The PCB's label has "PCB" in it, so
    # cad/render/colours.json's electronics rule colours it like the e-box's other boards.
    PS, GS = P.Solids, G.Solids
    i_pcb = next(i for i, x in enumerate(PS) if x.isSame(pcb))
    PF = P.Faces; hs = {}                         # each solid's faces, by their index in the whole shape's faces
    for k, f in enumerate(PF): hs.setdefault(f.hashCode(), []).append(k)
    faces_of = [[next(k for k in hs.get(f.hashCode(), []) if PF[k].isSame(f)) for f in x.Faces] for x in PS]
    p.log(f"the STEP: {len(PF)} faces, each found in its solid")
    looks = None
    if FreeCAD.GuiUp:
        try: looks = list(so[0].ViewObject.ShapeAppearance)
        except Exception as e: p.log(f"  STEP appearance not read: {e}")
    for o in sorted(gone + [old], key=lambda o: o.TypeId == "App::Part"):   # leaves first, then the groups
        ed.removeObject(o.Name)
    npart = ed.addObject("App::Part", "Pi5Simplified"); npart.Label = NEW_PART; assy.addObject(npart)
    C = linkgeo.gplace(npart)                    # a new feature in npart has an identity Placement
    board = []
    for i, x in enumerate(GS):
        f = ed.addObject("Part::Feature", f"Pi5Solid{i:02d}"); npart.addObject(f)
        bb = PS[i].BoundBox
        f.Label = "Raspberry Pi 5 PCB" if i == i_pcb else \
            f"Raspberry Pi 5 part {i:02d} ({bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f})"
        g_ = x.copy(); g_.transformShape(C.inverse().toMatrix(), True, False); f.Shape = g_
        board.append(f)
    if looks:
        p.log("colours: " + ", ".join(f"{f.Label.split(' (')[0]} {tuple(round(c, 2) for c in f.ViewObject.ShapeAppearance[0].DiffuseColor[:3])}"
                                      for f in board))
    for s in sc:                                 # slide along X (their axis); Part::Features: through the Placement
        Cs = linkgeo.gplace(s).multiply(s.Placement.inverse())
        s.Placement = Cs.inverse().multiply(FreeCAD.Placement(V(sdx, 0, 0), FreeCAD.Rotation())).multiply(Cs).multiply(s.Placement)
    ed.recompute()
    want = {}
    if looks:                                    # after the recompute: a new feature's first redraw sets its default colour
        FreeCAD.Gui.updateGui()
        from collections import Counter
        key = lambda m: tuple(round(c, 3) for c in m.DiffuseColor[:3])
        p.log(f"the STEP's face colours: {Counter(key(m) for m in looks).most_common()}")
        for i, f in enumerate(board):            # the solid's most common face colour (a body, not its first face)
            top = Counter(key(looks[k]) for k in faces_of[i]).most_common(1)[0][0]
            m = next(looks[k] for k in faces_of[i] if key(looks[k]) == top); want[f.Name] = tuple(round(c, 2) for c in top)
            try: f.ViewObject.ShapeAppearance = [m]
            except Exception as e: p.log(f"  appearance not set on {f.Label}: {e}")
        p.log("wanted: " + ", ".join(sorted({str(tuple(round(c, 2) for c in f.ViewObject.ShapeAppearance[0].DiffuseColor[:3])) for f in board})))
    FreeCAD.closeDocument(sd.Name)
    eb.refresh()
    # ---- after (e-box)
    NB = Part.makeCompound([eb.shapes[f.Name] for f in board])
    dbx = max(abs(getattr(NB.BoundBox, k) - getattr(gb, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    p.check(abs(NB.Volume - P.Volume) < 0.05 and len(board) == 25 and all(len(eb.shapes[f.Name].Solids) == 1 for f in board) and dbx < TOL,
            f"{NEW_PART}: 25 one-solid parts where the fit puts them ({NB.Volume:.1f} mm3; box within {dbx:.5f})")
    if FreeCAD.GuiUp:
        got = {f.Name: tuple(round(c, 2) for c in f.ViewObject.ShapeAppearance[0].DiffuseColor[:3]) for f in board}
        p.check(len(looks or []) == len(P.Faces) and len(want) == 25 and got == want,
                f"each part shows its STEP solid's most common face colour ({len(looks or [])} face colours read; "
                f"{len(set(got.values()))} colours on the parts; the PCB's green comes from colours.json's electronics role)")
    for s in sc:
        pl = sorted(f.BoundBox.XMin for f in eb.shapes[s.Name].Faces if f.Surface.__class__.__name__ == "Plane" and abs(f.Surface.Axis.x) > 0.999)
        p.check(abs(pl[1] - front) < TOL, f"{s.Label}: head on the PCB's front ({pl[1]:.4f} / {front:.4f})")
    bnames = {f.Name for f in board}
    new = bnames | screws
    P1 = pairs(new, eb.shapes, set())
    after = dict(zip(P1, p.volumes([(eb.shapes[a], eb.shapes[b]) for a, b in P1])))
    lab = lambda n: ed.getObject(n).Label
    hits = sorted(((round(v, 3), lab(a), lab(b), round(before.get((a, b), 0.0), 3)) for (a, b), v in after.items()
                   if v > 1e-3 and v > before.get((a, b), 0.0) + 0.01 and not (a in bnames and b in bnames)), reverse=True)
    p.log(f"overlaps of the new board and the screws now (the board's own parts with each other not checked): "
          f"{sorted(((round(v, 3), lab(a), lab(b)) for (a, b), v in after.items() if v > 1e-3 and not (a in bnames and b in bnames)), reverse=True)}")
    for v, a, b, w in hits:                    # where: the overlap's box, per solid of the board
        A = eb.shapes[next(n for n in new | set(eb.shapes) if lab(n) == a)]; Bs = eb.shapes[next(n for n in eb.shapes if lab(n) == b)]
        for sa in (A.Solids if len(A.Solids) > 1 else [A]):
            for sb in (Bs.Solids if len(Bs.Solids) > 1 else [Bs]):
                if sa.BoundBox.intersect(sb.BoundBox):
                    c = sa.common(sb)
                    if c.Volume > 1e-3: p.log(f"   {a} x {b}: {c.Volume:.3f} mm3 at {c.BoundBox}")
    p.check(not hits, f"no new or worse overlap of the board or the screws with any e-box part ({hits[:8]})")
    moved = [lab(n) for n, b in box0.items() if n not in screws and (n not in eb.shapes or not eb.shapes[n].BoundBox.isInside(b)
             or not b.isInside(eb.shapes[n].BoundBox))]
    all1 = FreeCAD.BoundBox(); [all1.add(s_.BoundBox) for s_ in eb.shapes.values()]
    da = max(abs(getattr(all1, k) - getattr(all0, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    p.check(da < TOL, f"the e-box's overall box unchanged (within {da:.5f}): the envelope that lite-57 sized from it still fits")
    p.check(not moved, f"every other e-box solid's box unchanged ({len(moved)}: {moved[:5]})")
    # ---- lite-75: the envelope's label
    pr = p.open(SRC); doc = pr.doc
    env = [o for o in pr.leaves if o.Label.startswith(ENV)]
    p.check(len(env) == 1 and "vt350-ebox-3.FCStd" in env[0].Label, f"lite-74's e-box envelope ({[o.Label for o in env]})")
    if p.errs: return p.finish([])
    eb0 = pr.shapes[env[0].Name].BoundBox
    n0 = len(pr.leaves)
    env[0].Label = env[0].Label.replace("vt350-ebox-3.FCStd", "vt350-ebox-4.FCStd")
    doc.recompute(); pr.refresh()
    e1 = pr.shapes[env[0].Name].BoundBox
    de = max(abs(getattr(e1, k) - getattr(eb0, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    p.log(f"the envelope's box {eb0}; the e-box's contents before {all0}, after {all1}")
    p.check(len(pr.leaves) == n0 and de < 1e-6, f"lite-75: {n0} solids as lite-74, the envelope's box unchanged ('{env[0].Label}')")
    p.dump({"step_sha256": sha, "pcb_thickness": round(zhi - zlo, 4), "standoff_top_x": round(xs, 4),
            "pilot_holes_yz": [[round(q.y, 3), round(q.z, 3)] for q in ph], "hole_deviation": round(dev, 5),
            "screw_dx": round(sdx, 4), "new_board_box": [round(getattr(gb, k), 3) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax")],
            "old_board_box": [round(getattr(ob, k), 3) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax")],
            "removed_objects": len(gone) + 1, "src": [os.path.basename(SRC), os.path.basename(EBOX3)]})
    return p.finish([(ed, EBOX4), (doc, DST)])


if not os.environ.get("LITE75_AS_LIB"): litelib.Pass("lite75_pi5").run(main)
