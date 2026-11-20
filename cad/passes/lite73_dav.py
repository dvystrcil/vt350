# GUI pass: vt350-lite-72 -> vt350-lite-73   (headless = dry run, never saves)   vt350#263
# The Dragon ACE Volcano on every A4Tv2 head, on DW-Tas's hex DAV main body, with no spacer (owner, 2026-11-19).
#  1. Each head's main body `main-body_dragon-rapido-UHF_o2_xol` (lite-15) becomes `hex-main-body_DAV_o2_xol` from
#     https://github.com/DW-Tas/A4Tv2 (CC BY-NC-SA 4.0) at UPSTREAM_COMMIT, read from $VT350_A4TV2 (not in git).
#     DW-Tas's per-variant body STEPs share one frame (identical boxes; the UHF and DAV bodies differ only round the
#     hotend pocket), so the UHF body STEP is fitted to each head's body (dupes.fit, a rigid move checked vertex by
#     vertex) and that move puts the DAV body in its place. The hex variant's 11 inlay solids (the hexagons, printed in
#     a second colour) fill its recesses and are kept in the body as one compound; DW-Tas's print support is not.
#  2. The 3 mm `TL-dragon-ace-spacer` goes on every head: DW-Tas, "for use without spacer".
#  3. No Dragon ACE Volcano CAD exists, so the old hotend parts stay as a STAND-IN, each renamed "... (stand-in)":
#     the heat sink and everything held in it seat its top against the DAV body's hotend pocket ceiling (the body's
#     material straight above the heat sink), the heat block still seated on the heat break's flange: heat-sink top ->
#     block bottom = DAV_TO_BLOCK, the owner's measurement of the real DAV (45.5). The stand-in's nozzle and sock go; under
#     the block (kept: the Volcano heater is 20 tall) the Trianglelab MZE assembly hangs as its STEP assembles it (MZE,
#     brass V6 nozzle in it, silicone sock round it), the MZE's stud screwed up until it butts the heat break. The tip
#     lands where that puts it: 59.40, the owner's measurement with a 0.6 TC Undertaker (Phaetus's 60.6 superseded;
#     lite-72 51.0; nothing stretched).
#     The four M2.5 hotend screws seat their heads on the DAV body's counterbore floor.
#  4. The Beacon goes up BEACON_UP (0.30), to BEACON_DZ (2.80) above the carried tip (the tip is 0.10 higher than lite-72's,
#     which put the carriage-mounted Beacon 0.10 closer, at 2.50). The carriage's Beacon pocket ceiling (our remix,
#     cad/derived/madmax-andrewmcgr-carriage-beacon/) is cut 0.30 deeper over the board, on the carriage and its
#     mirrored dock copy, and its printable STL is written again (lite25_carriage_9mm.py's frame).
# Found on the way (logged, checked): in lite-15..72 the stand-in never touched the UHF body. The spacer's top sat
# UHF_GAP (8.5 mm) below the UHF body's pocket ceiling, so lite-72's nozzle tip was not where a seated hotend puts it.
# The DAV body's ceiling is the UHF body's minus the spacer's 3 mm (the 3 mm of plastic DW-Tas added there).
# Checks (refuses to save on any):
#  - the UHF body STEP fits every head's body (5 bodies: 1 part + 4 links), the DAV STEP has the UHF STEP's box, the
#    inlays fill the plain DAV body's recesses; the DAV ceiling = the UHF ceiling - 3.0 on every head;
#  - the same 18 hotend parts on every head (1 spacer, 4 screws, 9 held in the heat sink, 4 below it); the MZE STEP's
#    three parts;
#  - after: no spacer left; the DAV body on all 5 heads (its box where its fit puts it, links following the master);
#    heat-sink top on the ceiling and heat-sink top -> block bottom = 45.5 and -> tip = 59.40 +- 0.05, the MZE stud butting the heat break; nozzle tips' XY unchanged;
#    the MZE on the hotend axis; the Beacon BEACON_DZ above the
#    carried tip; screw heads on the counterbore floor; no new or worse overlap of any changed part with anything; every other
#    solid's box unchanged.
# Measures (the log + json): the stand-in heat block and nozzle (#263, the best figures we have for the Volcano's
# block), the tips' Z change, the Beacon face and the carriage underside above the carried tip, the 4010 ducts'
# lowest point above the tip, and the screws' thread engagement in the heat sink.
import FreeCAD, Part, Import, Mesh, MeshPart, math, os, re, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, dupes
from litelib import MODELS
V = FreeCAD.Vector
SRC = os.environ.get("VT350_SRC", f"{MODELS}/vt350-lite-72.FCStd")
DST = f"{MODELS}/vt350-lite-73.FCStd"
UPSTREAM_COMMIT = "888755a97da9e1bd3062c35c914538342ef7d6f2"
A4TV2 = os.environ.get("VT350_A4TV2", f"{MODELS}/downloads/upstream/a4tv2-{UPSTREAM_COMMIT[:7]}")
UHF_STEP, DAV_STEP, PLAIN_DAV_STEP = (f"{A4TV2}/{n}.step" for n in
                                      ("main-body_dragon-rapido-UHF_o2_xol", "hex-main-body_DAV_o2_xol", "main-body_DAV_o2_xol"))
OLD_BODY, NEW_BODY = "main-body_dragon-rapido-UHF_o2_xol", "hex-main-body_DAV_o2_xol"
SUPPORT = "Support_Main-body"                  # DW-Tas's print support in the hex STEP: not part of the body
SPACER, SCREW = "TL-dragon-ace-spacer", "Hex socket head cap screw M2.5"
HEATSINK = "TL-dragon-Íâ¿ò-°«"   # GBK read as Latin-1: TL-dragon-外框-矮 (the heat sink)
NOZZLE, BLOCK = "E3D v6 HotEnd - Nozzle", "Heat Block"
STANDIN = " (stand-in)"
VOLCANO_SPAN = 60.6          # Phaetus, Dragon ACE Volcano: heat-sink top to nozzle tip (#263): compared, no longer imposed
DAV_TO_BLOCK = 45.5          # owner, 2026-11-20, measured on the real DAV: "the height of the DAV without MZE and nozzle",
                             # read as heat-sink top -> heat-block bottom; the stand-in's (block seated on the heat break) is checked
DAV_TO_TIP = 59.40           # owner, 2026-11-20: heat-sink top -> tip with the MZE and a 0.6 TC Undertaker nozzle (West3D);
                             # 57.70 with a bimetal 0.2 (1.7 shorter). Supersedes Phaetus's 60.6 (their own nozzle, presumably)
SPACER_T = 3.0
OLD_SPAN = 51.0              # the stand-in's own top-to-tip in lite-72 (#263)
UHF_GAP = 8.5                # lite-72: spacer top 434.8, UHF pocket ceiling 443.3 (measured here, checked)
HOTEND_R = 12.0              # hotend parts lie within this of the heat sink's axis (XY box)
COUNTS = {"spacer": 1, "screw": 4, "upper": 9, "lower": 4}   # per head (lower includes the heat block's mesh stand-in)
CARRY_DZ = 0.315             # sweep_toolhead.log: a docked head sits 0.315 above where the carriage carries it
BEACON = "Beacon RevH"
CARRIAGE = "COMPOUND"        # the gantry carriage's label (lite-62; the dock copies are COMPOUND003/004)
DUCTS = "[a]_Duct-4010-"
TOL = 0.05
MZE_STEP = os.environ.get("VT350_MZE_STEP", os.path.join(_REPO, "cad/vendor/trianglelab-mze-robertsamples/Trianglelabs_MZE_v3.step"))
# "Trianglelab MZE w/sock" by Robert Samples (Printables 1391903, CC0-1.0), a remix of Bolado's "MZE DLC V6 Melt Zone
# Extender" (Printables 1263324, CC0-1.0): an assembly of the MZE, a brass V6 nozzle and the silicone sock. The owner's
# own DAV on the LH Stinger has an MZE of this shape (2026-11-20). Its sizes are the sellers' published ones, corrected
# "from measurement" by the remixer: still owner to measure (heat-sink top -> tip, the MZE's length and diameter).
MZE_PARTS = {"MZE": "TL-dragon-ace-MZE", "V6 nozzle": "TL-dragon-ace-MZE nozzle (brass V6)", "Sock": "TL-dragon-ace-MZE sock"}
MZE = MZE_PARTS["MZE"]; MZE_RE = re.escape(MZE) + r"\d*$"
HEATBREAK = r"Component\d*$"  # the stand-in's heat break (Component1 on the Left head; Component006 ... on the others) (M6 thread), held in the heat sink, screwed into the block
BEACON_DZ = 2.80             # Beacon coil face above the carried tip (Beacon's 2.6-3 zone; owner 2026-11-20: 2.80, so a
                             # hot-tighten's 0.1-0.2 still leaves >= 2.6)
BEACON_UP = 0.30             # the Beacon goes up this much; the carriage's Beacon pocket ceiling is cut as much deeper
ROOF_MIN = 1.2               # mm of carriage left above the deeper ceiling (about 3 perimeters at 0.4)
CAR_COPY = "COMPOUND004"     # the Right Dock's mirrored carriage copy (a Part); the Left Dock's COMPOUND003 links the carriage
CAR_STL = "madmax-andrewmcgr-carriage-beacon/MadMaxCarriage Beacon RevH pocket 9mm belts.stl"   # cad/derived and parts/printed/vt350
# The M2.5 hotend screws' overlaps after the pass, each capped. Seated on the DAV counterbore floor (Z 445.3), a
# screw's 2.5 mm head reaches 447.8, and the parts DW-Tas puts on top of the body start at 446.8 over every screw
# (in lite-72 too, over the UHF floor at 445.8: the screws then floated below the body, so nothing showed). Which
# screw (or head) the A4Tv2 means here is an open question on #263; the pass reports it, it doesn't guess.
SCREW_L = 10.0               # the hotend screws' length under the head: M2.5 x 10 SHCS (DIN 912), cut from longer OK
ENGAGE = 5.0                 # full thread engagement: 2 x the diameter, in the aluminium heat sink
BOTTOM_GAP = 0.5             # the screw's tip stays this far off the tapped hole's bottom
HEADS_RULE = "screw head under the extruder adapter / Crossbow (reported, #263)"
KNOWN = {HEADS_RULE: None,
         "screw in the stand-in heat sink's tapped hole (modelled at the minor diameter; 5.0 mm deep now, was 2.0)": (HEATSINK, 8.0),
         "screw through the DAV body's 0.2 mm print bridging layers": (NEW_BODY, 0.5)}
SOCK_RULE = "the silicone sock stretched over the MZE (as in the author's assembly: 1.33 mm3)"
KNOWN_HEADS = (("[a]_orbiter-crossbow-adapter_o2_xol", 10.0), ("Crossbow - Main Body", 10.0))


def load(path, p):
    d = FreeCAD.newDocument(); Import.insert(path, d.Name)
    objs = [o for o in d.Objects if o.TypeId == "Part::Feature" and o.Shape.Solids]
    p.log(f"read {os.path.basename(path)}: {[(o.Label, round(o.Shape.Volume, 2)) for o in objs]}")
    return d, objs


def above(shape, x, y, z0, z1=520.0):
    """Lowest Z of `shape`'s material on the vertical line at (x, y) above z0 (None if none)."""
    zs = [min(v.Point.z for v in e.Vertexes) for e in Part.makeLine(V(x, y, z0), V(x, y, z1)).common(shape).Edges]
    return min(zs) if zs else None


def ceiling(shape, cx, cy, z0, r=8.0):
    """The body's material straight above the hotend: lowest Z above z0 on 4 lines at radius r round the axis, along X
    and Y (the diagonals at r 8 are the hotend screws' holes)."""
    zs = [above(shape, cx + r * math.cos(a), cy + r * math.sin(a), z0) for a in [k * math.pi / 2 for k in range(4)]]
    return zs


def move_global(o, d):
    """Move o (a part, a link or a mesh) by the global vector d, through its own Placement."""
    C = linkgeo.gplace(o).multiply(o.Placement.inverse())
    o.Placement = C.inverse().multiply(FreeCAD.Placement(d, FreeCAD.Rotation())).multiply(C).multiply(o.Placement)


def tight(s):
    """The overlap of BoundBox and optimalBoundingBox: each can overshoot on B-splines, both contain the shape
    (LESSONS.md; the heat block's BoundBox is 0.75 mm too tall)."""
    a, b = s.BoundBox, litelib.obb(s)
    return FreeCAD.BoundBox(max(a.XMin, b.XMin), max(a.YMin, b.YMin), max(a.ZMin, b.ZMin),
                            min(a.XMax, b.XMax), min(a.YMax, b.YMax), min(a.ZMax, b.ZMax))


def gbox(o):
    return (linkgeo.gmesh(o) if linkgeo.is_mesh(o) else linkgeo.gshape(o)).BoundBox


def main(p):
    # ---- the upstream bodies
    du, uo = load(UHF_STEP, p); U = max((o.Shape for o in uo), key=lambda s: s.Volume)
    dp, po = load(PLAIN_DAV_STEP, p); PD = max((o.Shape for o in po), key=lambda s: s.Volume)
    dd, do = load(DAV_STEP, p)
    main_ = [o for o in do if o.Label == NEW_BODY]
    inlays = [o for o in do if o.Label != NEW_BODY and not o.Label.startswith(SUPPORT)]
    p.check(len(main_) == 1 and len(inlays) == 11, f"hex DAV STEP: the body + 11 inlays ({len(main_)}, {[o.Label for o in inlays]})")
    if p.errs: return p.finish([])
    HD = Part.makeCompound([main_[0].Shape.Solids[0]] + [s for o in inlays for s in o.Shape.Solids])
    ub, hb = U.BoundBox, HD.BoundBox
    p.check(all(abs(getattr(ub, k) - getattr(hb, k)) < 1e-4 for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax")),
            f"the DAV and UHF body STEPs share one frame (boxes {ub} / {hb})")
    p.check(abs(HD.Volume - PD.Volume) < 0.5, f"the inlays fill the hex body's recesses: body + inlays {HD.Volume:.2f} = "
                                             f"plain DAV body {PD.Volume:.2f} mm3")
    p.check(all(s.isValid() for s in HD.Solids), "the DAV body's solids are valid")
    for d in (du, dp, dd): FreeCAD.closeDocument(d.Name)
    # ---- the MZE assembly. In its STEP the MZE's shoulder face is at Z 0 with its M6 stud up (+Z, into the heat block's
    # bottom, where the nozzle was), the V6 nozzle screwed into its female end below and the sock round it: as fitted.
    dm = FreeCAD.newDocument(); Import.insert(MZE_STEP, dm.Name)
    mo = {o.Label: o.Shape.copy() for o in dm.Objects if o.TypeId == "Part::Feature" and o.Shape.Solids}
    FreeCAD.closeDocument(dm.Name)
    p.check(sorted(mo) == sorted(MZE_PARTS) and all(len(x.Solids) == 1 and x.isValid() for x in mo.values()),
            f"MZE STEP ({MZE_STEP}): one valid solid each for {sorted(MZE_PARTS)} ({sorted(mo)})")
    if p.errs: return p.finish([])
    mt, nt, kt = tight(mo["MZE"]), tight(mo["V6 nozzle"]), tight(mo["Sock"])
    shoulder = [f for f in mo["MZE"].Faces if f.Surface.__class__.__name__ == "Plane" and abs(f.BoundBox.ZMin) < 1e-6
                and abs(f.BoundBox.ZMax) < 1e-6 and f.Area > 10]
    MZE_L, MZE_STUD, MZE_TIP = -mt.ZMin, mt.ZMax, -nt.ZMin
    MZE_OD = min(mt.XLength, mt.YLength)
    p.check(len(shoulder) == 1 and abs(MZE_L - 8.0) < 0.05 and abs(MZE_STUD - 7.4) < 0.4 and abs(MZE_TIP - 13.5) < 0.05,
            f"MZE: {MZE_L:.2f} mm below its shoulder, stud {MZE_STUD:.2f}, nozzle tip {MZE_TIP:.2f} below the shoulder")
    inner = {f"{a} x {b}": round(mo[a].common(mo[b]).Volume, 3) for a, b in (("MZE", "Sock"), ("MZE", "V6 nozzle"), ("Sock", "V6 nozzle"))}
    p.log(f"MZE assembly: MZE {mt.XLength:.2f} x {mt.YLength:.2f} x {mt.ZLength:.2f} (hex 10 A/F; {MZE_L:.2f} below the shoulder, "
          f"stud {MZE_STUD:.2f}), nozzle tip {MZE_TIP:.2f} below the shoulder, sock bottom {-kt.ZMin:.2f}: tip {kt.ZMin - nt.ZMin:.2f} "
          f"below the sock; overlaps inside the STEP {inner}")
    # ---- the model
    pr = p.open(SRC); doc = pr.doc
    par = linkgeo.group_parents(doc.Objects)
    bodies = [o for o in pr.leaves if o.Label.startswith(OLD_BODY)]
    master = [o for o in bodies if o.TypeId == "Part::Feature"]
    p.check(len(bodies) == 5 and len(master) == 1 and all(linkgeo.link_target(o) is master[0] for o in bodies),
            f"5 UHF bodies, one part + links to it ({[(o.Name, o.TypeId) for o in bodies]})")
    if p.errs: return p.finish([])
    master = master[0]
    T, heads = {}, {}
    for b in bodies:
        r, t = dupes.fit(U, pr.shapes[b.Name])
        p.check(r == "moved", f"{b.Label}: the UHF body STEP fits it ({r}, {t})")
        if r == "moved": T[b.Name] = t
    if p.errs: return p.finish([])
    rot0 = T[master.Name].Rotation
    p.check(all(t.Rotation.isSame(rot0, 1e-9) for t in T.values()), "every head's body has the same orientation")
    meshes = [o for o in doc.Objects if linkgeo.is_mesh(o)]
    for b in bodies:
        box = {o.Name: gbox(o) for o in pr.leaves + meshes if par.get(o.Name) is par.get(b.Name) and o.Name != b.Name}
        hs = [o for o in pr.leaves if o.Name in box and o.Label.startswith(HEATSINK) and box[o.Name].XLength > 20]
        p.check(len(hs) == 1, f"{b.Label}: one heat sink ({[o.Label for o in hs]})")
        if p.errs: return p.finish([])
        hs = hs[0]; hb_ = box[hs.Name]; cx, cy = hb_.Center.x, hb_.Center.y
        parts = [doc.getObject(n) for n, bb in box.items() if abs(bb.XMin - cx) <= HOTEND_R and abs(bb.XMax - cx) <= HOTEND_R
                 and abs(bb.YMin - cy) <= HOTEND_R and abs(bb.YMax - cy) <= HOTEND_R and bb.ZMin > 370 and bb.ZMax < 445]
        g = {"spacer": [o for o in parts if o.Label.startswith(SPACER)],
             "screw": [o for o in parts if o.Label.startswith(SCREW)]}
        rest = [o for o in parts if o not in g["spacer"] + g["screw"]]
        g["lower"] = [o for o in rest if box[o.Name].ZMax < hb_.ZMin - 1e-6]
        g["upper"] = [o for o in rest if o not in g["lower"]]
        p.check({k: len(v) for k, v in g.items()} == COUNTS,
                f"{b.Label}: hotend parts {({k: len(v) for k, v in g.items()})}: lower {[o.Label for o in g['lower']]}, "
                f"upper {[o.Label for o in g['upper']]}")
        nz = [o for o in g["lower"] if o.Label.startswith(NOZZLE)]; bl = [o for o in g["lower"] if o.Label.startswith(BLOCK) and not linkgeo.is_mesh(o)]
        p.check(len(nz) == 1 and len(bl) == 1, f"{b.Label}: one nozzle, one heat block")
        if p.errs: return p.finish([])
        hb = [o for o in g["upper"] if re.match(HEATBREAK, o.Label) and box[o.Name].ZMin < hb_.ZMin]
        p.check(len(hb) == 1, f"{b.Label}: one heat break below the heat sink ({[o.Label for o in hb]})")
        if p.errs: return p.finish([])
        heads[b.Name] = dict(body=b, hs=hs, axis=(cx, cy), g=g, nozzle=nz[0], block=bl[0], hbreak=hb[0])
    # ---- where the hotend seats: the UHF and DAV bodies' material straight above the heat sink
    info = {}
    for n, h in heads.items():
        b = h["body"]; cx, cy = h["axis"]
        top = gbox(h["hs"]).ZMax; sp = gbox(h["g"]["spacer"][0])
        D = HD.copy(); D.transformShape(T[n].toMatrix(), True, False); h["D"] = D
        cu, cd = ceiling(pr.shapes[n], cx, cy, top), ceiling(D, cx, cy, top)
        ok = all(z is not None for z in cu + cd) and max(cu) - min(cu) < 1e-6 and max(cd) - min(cd) < 1e-6
        p.check(ok, f"{b.Label}: a flat pocket ceiling over the heat sink (UHF {cu}, DAV {cd})")
        if not ok: return p.finish([])
        h["seat"] = cd[0]
        p.check(abs(sp.ZMin - top) < 1e-6 and abs(sp.ZMax - top - SPACER_T) < 1e-6, f"{b.Label}: the spacer sits on the heat sink ({sp.ZMin:.3f}..{sp.ZMax:.3f})")
        p.check(abs(cu[0] - sp.ZMax - UHF_GAP) < 0.01, f"{b.Label}: lite-72's hotend floats {cu[0] - sp.ZMax:.3f} mm below the UHF "
                                                       f"body's pocket ceiling (Z {cu[0]:.3f}; spacer top {sp.ZMax:.3f})")
        p.check(abs(cu[0] - cd[0] - SPACER_T) < 1e-3, f"{b.Label}: the DAV ceiling (Z {cd[0]:.3f}) is the UHF's less the spacer's {SPACER_T} mm")
        tip = gbox(h["nozzle"]).ZMin
        p.check(abs(top - tip - OLD_SPAN) < TOL, f"{b.Label}: the stand-in's heat-sink top -> tip in lite-72 {top - tip:.3f} (expected {OLD_SPAN})")
        # the screws: head underside on the DAV counterbore floor. On a line 1.9 mm off each screw's axis (outside the
        # dia 2.75 hole, inside the dia 4.8 counterbore and the head) the body's first stretch above the heat sink runs
        # from the pocket ceiling to the counterbore floor; the screw's lowest point there is its head's underside.
        sc = h["g"]["screw"]; floors, unders = [], []
        for s_ in sc:
            sb = gbox(s_); x, y = sb.Center.x + 1.9, sb.Center.y
            es = sorted(((min(v.Point.z for v in e.Vertexes), max(v.Point.z for v in e.Vertexes))
                         for e in Part.makeLine(V(x, y, top), V(x, y, 520)).common(D).Edges))
            floors.append(es[0][1] if es and abs(es[0][0] - cd[0]) < 1e-6 else None)
            unders.append(above(linkgeo.gshape(s_), x, y, sb.ZMin - 1))
        ok = all(z is not None for z in floors + unders) and max(floors) - min(floors) < 1e-6 and max(unders) - min(unders) < 1e-6
        p.check(ok, f"{b.Label}: DAV counterbore floors {floors} (from the ceiling up); screw head undersides {unders}")
        if not ok: return p.finish([])
        floor = floors[0]
        # the heat sink's tapped holes: on each screw's axis the heat sink has no material from its top down to the
        # hole's bottom (the stand-in models the hole at the minor diameter, so the screw's own axis line is clear)
        HS = linkgeo.gshape(h["hs"]); depths = []
        for s_ in sc:
            sb = gbox(s_); x, y = sb.Center.x, sb.Center.y
            es = [max(v.Point.z for v in e.Vertexes) for e in Part.makeLine(V(x, y, top - 30), V(x, y, top + 1)).common(HS).Edges]
            depths.append(top - max((z for z in es if z < top - 0.01), default=top - 30))
        p.check(max(depths) - min(depths) < 1e-6 and min(depths) < 29, f"{b.Label}: the heat sink's 4 tapped holes, {depths} mm deep")
        h["hole_depth"] = min(depths)
        lsc = unders[0] - min(gbox(s_).ZMin for s_ in sc)
        p.check(abs(lsc - SCREW_L) < 1e-3, f"{b.Label}: the hotend screws are M2.5 x {lsc:.2f} under the head (expected {SCREW_L})")
        blk0 = tight(linkgeo.gshape(h["block"]))
        # the block stays seated on the stand-in heat break's flange, where lite-72 has it; the MZE's stud screws up the
        # block until it butts the heat break (a nozzle's or MZE's seal is against the heat break, hot-tightened), so its
        # shoulder sits on the block only if the stud is no longer than the block's free thread below the heat break
        HB0 = linkgeo.gshape(h["hbreak"]); hbz0 = tight(HB0).ZMin
        fl0 = above(HB0, cx + 4.0, cy, blk0.ZMax)
        free = hbz0 - blk0.ZMin; sgap = max(0.0, MZE_STUD - free)
        p.check(abs(top - blk0.ZMin - DAV_TO_BLOCK) < TOL and fl0 is not None and abs(fl0 - blk0.ZMax) < 1e-3,
                f"{b.Label}: the stand-in, block seated on the heat break's flange (gap {(fl0 or 0) - blk0.ZMax:.3f}), has heat-sink top -> "
                f"block bottom {top - blk0.ZMin:.3f} (owner's DAV: {DAV_TO_BLOCK} +- {TOL})")
        span = top - blk0.ZMin + sgap + MZE_TIP
        p.check(abs(span - DAV_TO_TIP) < TOL, f"{b.Label}: block bottom {top - blk0.ZMin:.3f} + MZE shoulder gap {sgap:.3f} + the "
                f"STEP's tip {MZE_TIP:.3f} = heat-sink top -> tip {span:.3f} (owner's DAV, 0.6 TC Undertaker: {DAV_TO_TIP} +- {TOL})")
        h.update(top=top, tip=tip, floor=floor, under=unders[0], dz_up=cd[0] - top, dz_low=cd[0] - top,
                 dz_screw=floor - unders[0], uhf_ceiling=cu[0], blk_rel=top - blk0.ZMin, free=free, sgap=sgap, span=span)
        p.log(f"{b.Label}: seat Z {cd[0]:.3f} (heat sink and block +{h['dz_up']:.3f}); the block's thread below the heat break "
              f"{free:.3f}, the MZE's stud {MZE_STUD:.3f}: shoulder {sgap:.3f} below the block; heat-sink top -> tip {span:.3f} "
              f"(Phaetus {VOLCANO_SPAN}, lite-72 {OLD_SPAN}); tip {tip:.3f} -> {cd[0] - span:.3f}; counterbore floor "
              f"{floor:.3f}, screws {h['dz_screw']:+.3f}")
    if p.errs: return p.finish([])
    # ---- the Beacon stays where lite-72 has it (on the carriage, not moved): the 59.40 tip is 0.10 higher than lite-72's,
    # so it ends BEACON_DZ above the carried tip, inside its 2.6-3 zone; raising it 0.10 to 2.60 would cut into the carriage
    bea = [o for o in pr.leaves if o.Label.startswith(BEACON)]
    car = [o for o in pr.leaves if o.Label == CARRIAGE]
    p.check(len(bea) == 1 and len(car) == 1, f"one Beacon part, one gantry carriage ({[o.Label for o in bea]})")
    if p.errs: return p.finish([])
    bea, car = bea[0], car[0]
    # the carriage's copies: the Left Dock's links the carriage (follows it); the Right Dock's is a mirrored Part
    cp = [o for o in pr.leaves if o.Label == CAR_COPY]
    lk = [o for o in pr.leaves if o.TypeId == "App::Link" and linkgeo.link_target(o) is car]
    p.check(len(cp) == 1 and cp[0].TypeId == "Part::Feature" and len(lk) == 1, f"the carriage's dock copies: {CAR_COPY} (a Part) and one "
            f"link ({[o.Label for o in lk]})")
    if p.errs: return p.finish([])
    cp = cp[0]
    # the cut: the Beacon board's footprint, from its top (0.010 under the pocket ceiling) up by BEACON_UP
    BS = pr.shapes[bea.Name]; board = max(BS.Solids, key=lambda x: x.BoundBox.XLength * x.BoundBox.YLength * (x.BoundBox.ZLength < 3))
    bt = tight(board)
    CUT = Part.makeBox(bt.XLength, bt.YLength, BEACON_UP + 0.02, V(bt.XMin, bt.YMin, bt.ZMax - 0.01))
    G = pr.shapes[car.Name]; cb = tight(G)
    d0 = BS.distToShape(G)[0]
    p.check(abs(d0 - 0.01) < 0.005, f"the Beacon's board top {bt.ZMax:.3f} sits {d0:.3f} under the carriage's pocket ceiling")
    zc = bt.ZMax + 0.01; zn = zc + BEACON_UP
    G2 = G.cut(CUT); rem = G.common(CUT).Volume
    p.check(G2.isValid() and len(G2.Solids) == len(G.Solids) and abs(G.Volume - G2.Volume - rem) < 0.05 and rem > 1,
            f"the carriage's pocket ceiling {BEACON_UP} deeper: {rem:.2f} mm3 removed ({G.Volume:.1f} -> {G2.Volume:.1f}), solids {len(G2.Solids)}")
    # Thickness maps over the board's two end ledges (the ceiling it bears on), before and after: carriage material from
    # the ceiling up on vertical lines, 0.2 x 0.5 mm. The ledges' outer edges already slope to nothing (a chamfer-like
    # edge in today's part); the cut shortens that slope. Owner 2026-11-20: fail only on a NEW thin feature (thinner than
    # ROOF_MIN where nothing near was thin before), and the flat ledge tops (1.8 today) keep >= 1.5.
    ends = sorted(G.common(CUT).Solids, key=lambda q: q.BoundBox.Center.x)
    p.check(len(ends) == 2, f"the board's two end ledges ({len(ends)} pieces of ceiling over it)")
    if p.errs: return p.finish([])
    def tmap(S, z0, qb):
        crop = S.common(Part.makeBox(qb.XLength + 1.2, qb.YLength + 1.2, 10.5, V(qb.XMin - 0.6, qb.YMin - 0.6, z0 - 0.5)))
        out = {}
        for i in range(int((qb.XLength + 1.2) / 0.2) + 1):
            for j in range(int((qb.YLength + 1.2) / 0.5) + 1):
                x, y = qb.XMin - 0.6 + i * 0.2, qb.YMin - 0.6 + j * 0.5
                es = sorted((min(v.Point.z for v in e.Vertexes), max(v.Point.z for v in e.Vertexes))
                            for e in Part.makeLine(V(x, y, z0 - 0.3), V(x, y, z0 + 10)).common(crop).Edges)
                out[(i, j)] = (x, y, es[0][1] - z0 if es and abs(es[0][0] - z0) < 0.02 else 0.0)
        return out
    newthin, flat, mins = [], [], []
    for q in ends:
        qb = q.BoundBox; m0, m1 = tmap(G, zc, qb), tmap(G2, zn, qb)
        inb = lambda v: bt.XMin + 0.05 <= v[0] <= bt.XMax - 0.05 and bt.YMin + 0.05 <= v[1] <= bt.YMax - 0.05   # under the board (cut)
        m0 = {k: v for k, v in m0.items() if inb(v)}; m1 = {k: v for k, v in m1.items() if inb(v)}
        thin0 = [k for k, v in m0.items() if 0 < v[2] < ROOF_MIN]; thin1 = [k for k, v in m1.items() if 0 < v[2] < ROOF_MIN]
        near = lambda k: any(abs(k[0] - a_) <= 3 and abs(k[1] - b_) <= 1 for a_, b_ in thin0)   # within 0.6 x 0.5 mm of an old thin spot
        newthin += [m1[k] for k in thin1 if not near(k)]
        flat += [m1[k][2] for k, v in m0.items() if v[2] >= 1.79]
        mins.append((min((v[2] for v in m0.values() if v[2] > 0), default=0), min((v[2] for v in m1.values() if v[2] > 0), default=0),
                     len(thin0), len(thin1)))
    p.log(f"end-ledge thickness maps (before / after: min over the material, lines thinner than {ROOF_MIN}): "
          f"{[(round(a_, 3), round(b_, 3), c_, d_) for a_, b_, c_, d_ in mins]}")
    p.check(not newthin, f"no new thin feature: after the cut, every spot thinner than {ROOF_MIN} is on today's sloped edges "
            f"({len(newthin)} not: {[(round(x_, 2), round(y_, 2), round(t_, 3)) for x_, y_, t_ in newthin[:4]]})")
    p.check(flat and min(flat) >= 1.5 - 1e-3, f"the ledges' flat tops (1.8 or more today) keep {min(flat) if flat else 0:.3f} mm above the "
            f"new ceiling over {len(flat)} lines (>= 1.5)")
    if p.errs: return p.finish([])
    # the Right Dock's copy: the carriage mirrored in X (checked), cut the same way
    G3 = pr.shapes[cp.Name]; c3 = tight(G3)
    Mx = FreeCAD.Matrix(); Mx.A11 = -1; Mx.A14, Mx.A24, Mx.A34 = c3.XMin + cb.XMax, c3.YMin - cb.YMin, c3.ZMin - cb.ZMin
    gm = tight(G.transformGeometry(Mx))
    dbox = max(abs(getattr(gm, k) - getattr(c3, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    p.check(abs(G.Volume - G3.Volume) < 0.5 and dbox < 0.01, f"{CAR_COPY} is the carriage mirrored in X ({G3.Volume:.1f} / {G.Volume:.1f} mm3; "
            f"boxes agree to {dbox:.4f} after the move)")
    if p.errs: return p.finish([])
    CUT3 = CUT.transformGeometry(Mx); G4 = G3.cut(CUT3); rem3 = G3.common(CUT3).Volume
    p.check(G4.isValid() and len(G4.Solids) == len(G3.Solids) and abs(rem3 - rem) < 0.05, f"{CAR_COPY}: {rem3:.2f} mm3 removed the same way")
    # the printable STL: the carriage back in the STL's own frame (lite25_carriage_9mm.py's map: X along X, STL Y down -Z
    # from the carriage top, STL Z +Y from its front face; checked here on the current STL)
    stl_d = os.path.join(_REPO, "cad/derived", CAR_STL)
    m0 = Mesh.Mesh(stl_d); sb = m0.BoundBox
    Ms = FreeCAD.Matrix(); (Ms.A11, Ms.A12, Ms.A13), (Ms.A21, Ms.A22, Ms.A23), (Ms.A31, Ms.A32, Ms.A33) = (1, 0, 0), (0, 0, 1), (0, -1, 0)
    Ms.A14, Ms.A24, Ms.A34 = cb.XMin, cb.YMin, cb.ZMax
    sbm = FreeCAD.BoundBox(); [sbm.add(Ms.multiply(V(q.x - sb.XMin, q.y - sb.YMin, q.z - sb.ZMin))) for q in m0.Points]
    dsb = max(abs(getattr(sbm, k) - getattr(cb, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    smp = [Ms.multiply(V(q.x - sb.XMin, q.y - sb.YMin, q.z - sb.ZMin)) for q in m0.Points[::max(1, m0.CountPoints // 12)]]
    # The committed STL is either today's carriage (before this pass's cut) or already the cut one: #265 merged the
    # re-exported STL before the owner's GUI run, so the run that saves sees the cut STL. Accept either; only re-export
    # when it's still the old one.
    dpt = max(G.distToShape(Part.Vertex(q))[0] for q in smp)
    dpt2 = max(G2.distToShape(Part.Vertex(q))[0] for q in smp)
    stl_cut = abs(m0.Volume - G2.Volume) < abs(m0.Volume - G.Volume)
    ref, dref = (G2, dpt2) if stl_cut else (G, dpt)
    p.check(dsb < 0.02 and abs(m0.Volume - ref.Volume) < 10.0 and dref < 0.05, f"the current carriage STL is the model's carriage "
            f"({'already cut' if stl_cut else 'before the cut'}) in lite25's frame (boxes agree to {dsb:.4f}; volumes "
            f"{m0.Volume:.1f} / {ref.Volume:.1f}, the STL's chords on round holes; {len(smp)} points within {dref:.4f})")
    if p.errs: return p.finish([])
    back = G2.copy(); back.transformShape(Ms.inverse(), True); back.translate(V(sb.XMin, sb.YMin, sb.ZMin))
    m1 = MeshPart.meshFromShape(Shape=back, LinearDeflection=0.01, AngularDeflection=0.1)
    mb1 = m1.BoundBox; dmb = max(abs(getattr(mb1, k) - getattr(sb, k)) for k in ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"))
    p.check(abs((m0.Volume - m1.Volume) - (0.0 if stl_cut else rem)) < 1.0 and dmb < 0.02 and m1.isSolid() >= m0.isSolid() and m1.hasNonManifolds() <= m0.hasNonManifolds(),
            f"printable carriage STL: {m1.CountFacets} facets, volume {m1.Volume:.1f} (was {m0.Volume:.1f}: the cut's {rem:.2f}), box as before to {dmb:.4f}; closed / non-manifold {m1.isSolid()} / {m1.hasNonManifolds()} (no worse than before: {m0.isSolid()} / {m0.hasNonManifolds()})")
    car_out = (m1, stl_d)
    if stl_cut: p.log("the committed carriage STL is already the cut one: not rewritten (its sha256 stays the manifest's)")
    # ---- before: overlaps of every part this pass touches
    for h in heads.values():                    # the stand-in's nozzle and sock make way for the MZE assembly's
        h["old"] = [h["nozzle"]] + [o for o in h["g"]["lower"] if o.Label.startswith("TL-dragon")]
        h["keep"] = [o for o in h["g"]["lower"] if o not in h["old"]]
    p.check(all(len(h["old"]) == 2 and len(h["keep"]) == 2 for h in heads.values()), "each head: the stand-in's nozzle and sock go, "
            "its heat block (+ mesh stand-in) stays")
    if p.errs: return p.finish([])
    removed = {o.Name for h in heads.values() for o in h["g"]["spacer"] + h["old"]}
    changed = ({n for n in heads} | {o.Name for h in heads.values() for k in ("screw", "upper", "lower") for o in h["g"][k]
                                     if not linkgeo.is_mesh(o)} | {bea.Name, car.Name, cp.Name, lk[0].Name}) - removed
    def pairs():
        out = set()
        for a in changed:
            for o in pr.leaves:
                if o.Name != a and o.Name not in removed and pr.shapes[a].BoundBox.intersect(pr.shapes[o.Name].BoundBox):
                    out.add(tuple(sorted((a, o.Name))))
        return sorted(out)
    P0 = pairs()
    before = dict(zip(P0, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in P0])))
    p.log(f"overlap pairs before: {len(P0)}, {sum(1 for v in before.values() if v > 1e-3)} overlapping")
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    tips0 = {n: gbox(h["nozzle"]) for n, h in heads.items()}
    # ---- write: the body (master shape; the links follow), the moves, the spacers
    gui = FreeCAD.GuiUp
    P_ = FreeCAD.Placement(master.Placement)
    ap = list(master.ViewObject.ShapeAppearance) if gui and hasattr(master.ViewObject, "ShapeAppearance") else None
    C = linkgeo.gplace(master).multiply(master.Placement.inverse())
    s = HD.copy(); s.transformShape(C.multiply(P_).inverse().multiply(T[master.Name]).toMatrix(), True, False); s.Placement = P_
    master.Shape = s
    if ap is not None: master.ViewObject.ShapeAppearance = ap
    p.check(master.Placement.isSame(P_, 1e-9), "the body keeps its placement")
    for b in bodies: b.Label = b.Label.replace(OLD_BODY, NEW_BODY)
    for n, h in heads.items():
        for o in h["g"]["upper"]: move_global(o, V(0, 0, h["dz_up"]))
        for o in h["keep"]: move_global(o, V(0, 0, h["dz_low"]))
        for o in h["g"]["screw"]: move_global(o, V(0, 0, h["dz_screw"]))
        for o in h["g"]["upper"] + h["keep"]:
            if not linkgeo.is_mesh(o) and not o.Label.endswith(STANDIN): o.Label += STANDIN
    # the MZE assembly on every head: the MZE's shoulder on the heat block's bottom, on the hotend axis; its parts
    # take the look of the parts they stand next to (MZE: the heat break; nozzle, sock: the stand-in's)
    looks = {}
    for k, src in (("MZE", heads[master.Name]["hbreak"]), ("V6 nozzle", heads[master.Name]["old"][0]), ("Sock", heads[master.Name]["old"][1])):
        t_ = linkgeo.link_target(src)
        looks[k] = (getattr(t_, "ShapeMaterial", None),
                    list(t_.ViewObject.ShapeAppearance) if gui and hasattr(t_.ViewObject, "ShapeAppearance") else None)
    new = {}
    for n, h in heads.items():
        cx, cy = h["axis"]; bot = tight(linkgeo.gshape(h["block"])).ZMin - h["sgap"]
        cont = h["body"].getParentGeoFeatureGroup(); Cc = linkgeo.gplace(cont)
        new[n] = {}
        for k, label in MZE_PARTS.items():
            g_ = mo[k].copy(); g_.translate(V(cx, cy, bot)); g_.transformShape(Cc.inverse().toMatrix(), True, False)
            o = doc.addObject("Part::Feature", "MZE"); cont.addObject(o); o.Shape = g_; o.Label = label
            mat, ap_ = looks[k]
            if mat is not None:
                try: o.ShapeMaterial = mat
                except Exception as e: p.log(f"  {label} material: {e}")
            if ap_ is not None: o.ViewObject.ShapeAppearance = ap_
            new[n][k] = o; changed.add(o.Name)
    sp = [o for h in heads.values() for o in h["g"]["spacer"] + h["old"]]
    for o in sorted(sp, key=lambda o: o.TypeId != "App::Link"): doc.removeObject(o.Name)       # links first
    for n, h in heads.items(): h["nozzle"] = new[n]["V6 nozzle"]
    # the Beacon up, the carriage's pocket ceiling and its mirrored dock copy cut to match (local frames kept)
    move_global(bea, V(0, 0, BEACON_UP))
    for o, sh in ((car, G2), (cp, G4)):
        P0 = FreeCAD.Placement(o.Placement); Cg = linkgeo.gplace(o).multiply(o.Placement.inverse())
        ap_ = list(o.ViewObject.ShapeAppearance) if gui and hasattr(o.ViewObject, "ShapeAppearance") else None
        g_ = sh.copy(); g_.transformShape(Cg.multiply(P0).inverse().toMatrix(), True, False); g_.Placement = P0; o.Shape = g_
        if ap_ is not None: o.ViewObject.ShapeAppearance = ap_
    doc.recompute(); pr.refresh()
    # ---- after
    p.check(not [o for o in doc.Objects if o.Label.startswith(SPACER)], "no spacer left")
    newb = [o for o in pr.leaves if o.Label.startswith(NEW_BODY)]
    p.check(len(newb) == 5 and not [o for o in pr.leaves if o.Label.startswith(OLD_BODY)], f"the DAV body on all 5 heads ({[o.Label for o in newb]})")
    res = {}
    for n, h in heads.items():
        b = h["body"]; G = pr.shapes[n]; want = h["D"].BoundBox; got = G.BoundBox
        p.check(abs(G.Volume - HD.Volume) < 0.05 and max(abs(getattr(want, k) - getattr(got, k)) for k in
                ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax")) < 1e-3, f"{b.Label}: where its fit puts it ({G.Volume:.2f} mm3, {got})")
        top = gbox(h["hs"]).ZMax; nb = tight(linkgeo.gshape(h["nozzle"])); tip = nb.ZMin
        p.check(abs(top - h["seat"]) < 1e-3, f"{b.Label}: heat-sink top {top:.3f} on the DAV ceiling {h['seat']:.3f}")
        p.check(abs(top - tip - h["span"]) < 1e-3, f"{b.Label}: heat-sink top -> tip {top - tip:.3f} (owner {DAV_TO_TIP}; Phaetus {VOLCANO_SPAN}, lite-72 {OLD_SPAN})")
        o0 = tips0[n]
        p.check(abs(nb.Center.x - o0.Center.x) < 1e-3 and abs(nb.Center.y - o0.Center.y) < 1e-3,
                f"{b.Label}: tip XY unchanged ({nb.Center.x:.3f}, {nb.Center.y:.3f})")
        Mz = linkgeo.gshape(new[n]["MZE"]); mzb = tight(Mz); Bk = linkgeo.gshape(h["block"]); tb_ = tight(Bk)
        HBk = linkgeo.gshape(h["hbreak"]); hx, hy = h["axis"]
        p.check(abs(top - tb_.ZMin - DAV_TO_BLOCK) < TOL, f"{b.Label}: heat-sink top -> block bottom {top - tb_.ZMin:.3f} ({DAV_TO_BLOCK} +- {TOL})")
        sh = mzb.ZMin + MZE_L
        p.check(Mz.isValid() and abs(mzb.Center.x - hx) < 1e-3 and abs(mzb.Center.y - hy) < 1e-3 and abs(tb_.ZMin - sh - h["sgap"]) < 1e-3,
                f"{b.Label}: the MZE on the hotend axis, its shoulder {tb_.ZMin - sh:.3f} below the heat block's bottom Z {tb_.ZMin:.3f}")
        hb_bot = tight(HBk).ZMin; stud_gap = hb_bot - mzb.ZMax
        flange = above(HBk, hx + 4.0, hy, tb_.ZMax)              # the heat break's flange (r 4.25) over the block
        h["stud_gap"], h["flange_gap"] = stud_gap, (flange - tb_.ZMax) if flange else None
        p.check(abs(stud_gap) < 1e-3 and h["flange_gap"] is not None and abs(h["flange_gap"]) < 1e-3,
                f"{b.Label}: the MZE's stud butts the heat break (gap {stud_gap:.3f}); the block seated on the heat break's flange "
                f"(gap {h['flange_gap'] or 0:.3f})")
        un = [above(linkgeo.gshape(s_), gbox(s_).Center.x + 1.9, gbox(s_).Center.y, gbox(s_).ZMin - 1) for s_ in h["g"]["screw"]]
        p.check(all(abs(u - h["floor"]) < 1e-3 for u in un), f"{b.Label}: screw heads on the counterbore floor {h['floor']:.3f} ({un})")
        eng = top - min(gbox(s_).ZMin for s_ in h["g"]["screw"]); spare = h["hole_depth"] - eng
        p.check(eng >= ENGAGE - 1e-6 and spare >= BOTTOM_GAP - 1e-6,
                f"{b.Label}: M2.5 x {SCREW_L:g} SHCS: {h['floor'] - top:.2f} mm through the body, {eng:.2f} mm into the heat sink "
                f"(full engagement >= {ENGAGE}), {spare:.2f} short of the {h['hole_depth']:.2f} mm hole's bottom (>= {BOTTOM_GAP})")
        blk = tight(linkgeo.gshape(h["block"]))
        sb = [gbox(s_) for s_ in h["g"]["screw"]]
        res[b.Label] = dict(tip_xyz=[round(nb.Center.x, 3), round(nb.Center.y, 3), round(tip, 3)], tip_dz=round(tip - o0.ZMin, 3),
                            heatsink_top=round(top, 3), uhf_ceiling=round(h["uhf_ceiling"], 3), dav_ceiling=round(h["seat"], 3),
                            heat_block_top=round(blk.ZMax, 3), heat_block_bottom=round(blk.ZMin, 3),
                            screw_tip=round(min(x.ZMin for x in sb), 3),
                            screw_engagement_in_heatsink=round(top - min(x.ZMin for x in sb), 3),
                            heatsink_hole_depth=round(h["hole_depth"], 3),
                            heatsink_top_to_block_bottom=round(top - tb_.ZMin, 3), heatsink_top_to_tip=round(top - tip, 3),
                            mze_shoulder_below_block=round(h["sgap"], 3), block_thread_below_heat_break=round(h["free"], 3), body_at_screws=round(h["floor"] - top, 3),
                            screw_length_range=[round(h["floor"] - top + ENGAGE, 2), round(h["floor"] - top + h["hole_depth"] - BOTTOM_GAP, 2)])
        p.log(f"{b.Label}: {res[b.Label]}")
    # the stand-in heat block, and the MZE assembly under it (the Left head's)
    L = heads[master.Name]
    B = linkgeo.gshape(L["block"]); bb = tight(B)
    nbb = tight(linkgeo.gshape(new[master.Name]["V6 nozzle"])); sk = tight(linkgeo.gshape(new[master.Name]["Sock"]))
    block = dict(width_x=round(bb.XLength, 2), depth_y=round(bb.YLength, 2), height_z=round(bb.ZLength, 2),
                 volume_mm3=round(B.Volume, 1), mze_length_below_block=round(MZE_L, 2), mze_stud=round(MZE_STUD, 2),
                 mze_od=round(MZE_OD, 2), nozzle_box=[round(nbb.XLength, 2), round(nbb.YLength, 2), round(nbb.ZLength, 2)],
                 nozzle_below_block=round(bb.ZMin - nbb.ZMin, 2),
                 sock_box=[round(sk.XLength, 2), round(sk.YLength, 2), round(sk.ZLength, 2)],
                 nozzle_below_sock=round(sk.ZMin - nbb.ZMin, 2))
    p.log(f"stand-in heat block + MZE assembly (#263): {block}")
    # tip clearances: Beacon face and carriage underside above the carried tip; the 4010 ducts above the tip
    tipL = res[master.Label]["tip_xyz"][2]; carried = tipL - CARRY_DZ
    ducts = [o for o in pr.leaves if o.Label.startswith(DUCTS) and par.get(o.Name) is par.get(master.Name)]
    clear = {}
    clear["beacon_face_above_carried_tip"] = round(pr.shapes[bea.Name].BoundBox.ZMin - carried, 3)
    BN, CN = pr.shapes[bea.Name], pr.shapes[car.Name]
    ov, dn = BN.common(CN).Volume, BN.distToShape(CN)[0]
    p.check(ov < 1e-3 and dn < 0.05, f"the raised Beacon touches or clears the deeper pocket ceiling (overlap {ov:.4f} mm3, gap {dn:.3f})")
    for o in lk + [cp]:
        p.check(abs(pr.shapes[o.Name].Volume - G2.Volume) < 0.5, f"{o.Label}: the same part as the carriage ({pr.shapes[o.Name].Volume:.1f} mm3)")
    clear["carriage_underside_above_carried_tip"] = round(pr.shapes[car.Name].BoundBox.ZMin - carried, 3)
    if ducts: clear["ducts_4010_lowest_above_tip"] = round(min(litelib.obb(pr.shapes[o.Name]).ZMin for o in ducts) - tipL, 3)
    p.check(len(clear) == 3, f"clearances measured: {clear} (lite-72: Beacon 2.60, carriage 3.0, ducts 2.41)")
    p.check(abs(clear["beacon_face_above_carried_tip"] - BEACON_DZ) < TOL and 2.6 - 1e-6 <= clear["beacon_face_above_carried_tip"] <= 3.0, f"the Beacon face is {clear['beacon_face_above_carried_tip']:.3f} above the carried tip ({BEACON_DZ} +- {TOL}, in its 2.6-3 zone)")
    p.check(clear["beacon_face_above_carried_tip"] < clear["carriage_underside_above_carried_tip"], "the Beacon is still the carriage's lowest part")
    # overlaps after
    removed_now = set(removed)
    P1 = [(a, b) for a, b in pairs() if doc.getObject(a) is not None and doc.getObject(b) is not None]
    after = dict(zip(P1, p.volumes([(pr.shapes[a], pr.shapes[b]) for a, b in P1])))
    lab = lambda n: doc.getObject(n).Label
    worse = sorted(((v, lab(a), lab(b), before.get((a, b), 0.0)) for (a, b), v in after.items() if v > before.get((a, b), 0.0) + 0.01), reverse=True)
    gone = sorted(((before[k], lab(k[0]), lab(k[1])) for k in before if before[k] > 0.01 and after.get(k, 0.0) < 0.01), reverse=True)
    p.log(f"overlaps gone ({len(gone)}): {[(round(v, 2), a, b) for v, a, b in gone[:20]]}")
    for v, a, b, w in worse: p.log(f"   new/worse overlap {v:8.2f} mm3 (was {w:.2f})  {a}  x  {b}")
    def known(a, b, v):
        """The screws' and the MZE's expected or reported overlaps (see KNOWN): (rule, cap) or None."""
        ab = sorted((a, b), key=lambda x: not re.match(MZE_RE, x))     # FreeCAD numbers repeated labels: MZE001 ...
        if re.match(MZE_RE, ab[0]) and ab[1].startswith(MZE_PARTS["Sock"]): return SOCK_RULE if v <= 1.5 else None
        if a.startswith(MZE) or b.startswith(MZE): return None
        if not (a.startswith(SCREW) or b.startswith(SCREW)): return None
        other = b if a.startswith(SCREW) else a
        for rule, pc in KNOWN.items():
            for prefix, cap in ([pc] if pc else KNOWN_HEADS):
                if other.startswith(prefix) and v <= cap: return rule
        return None
    left, kn, hit = [], {}, set()
    for v, a, b, w in worse:
        r = known(a, b, v)
        if r: kn.setdefault(r, []).append(round(v, 2))
        else: left.append((v, a, b, w))
        if r == HEADS_RULE: hit.add(a if a.startswith(SCREW) else b)
    for r, vs in kn.items(): p.log(f"known: {r}: {len(vs)} pairs, {min(vs)}..{max(vs)} mm3")
    p.check(len(hit) == 20, f"all 20 screw heads hit the adapter or the Crossbow body ({len(hit)}): the open question on #263")
    p.check(not left, f"no other new or worse overlap of a changed part ({len(left)}: "
                      f"{[(round(v, 2), a, b, round(w, 2)) for v, a, b, w in left[:12]]})")
    moved = [lab(k) for k, b in box0.items() if k not in changed and k not in removed_now
             and (k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox))]
    p.check(not moved, f"every other solid's box unchanged ({len(moved)}: {moved[:5]})")
    p.check(kn.get(SOCK_RULE, []) and len(kn[SOCK_RULE]) == 5, f"the sock over the MZE on all 5 heads ({kn.get(SOCK_RULE)})")
    p.dump({"mze": {"step": os.path.relpath(MZE_STEP, _REPO), "length_below_shoulder": round(MZE_L, 3), "stud": round(MZE_STUD, 3),
                    "od": round(MZE_OD, 3), "tip_below_shoulder": round(MZE_TIP, 3), "inside_step_overlaps": inner},
            "heads": res, "stand_in_heat_block": block, "clearances": clear, "upstream": UPSTREAM_COMMIT,
            "overlaps_gone": [(round(v, 2), a, b) for v, a, b in gone], "src": os.path.basename(SRC)})
    m1, stl_d = car_out
    for fn in ((stl_d, os.path.join(_REPO, "parts/printed/vt350", CAR_STL)) if not p.errs and not stl_cut else ()):
        m1.write(fn); p.log(f"wrote {os.path.relpath(fn, _REPO)} (a derived STL, written in a dry run too: it doesn't touch the model)")
    return p.finish([(doc, DST)])


if not os.environ.get("LITE73_AS_LIB"): litelib.Pass("lite73_dav").run(main)
