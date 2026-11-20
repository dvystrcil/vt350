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
#     material straight above the heat sink). The stand-in's nozzle and sock go; in their place, under the stand-in
#     heat block (kept: the Volcano heater is 20 tall), goes the Trianglelab MZE assembly (MZE_STEP: the MZE screwed
#     into the block's bottom, a brass V6 nozzle in it, the silicone sock round it). The block goes down until
#     heat-sink top -> nozzle tip = Phaetus's VOLCANO_SPAN (60.6 mm; the stand-in was 51.0), sliding down the stand-in
#     heat break's thread (a gap opens under the heat break's flange: the stand-in heat break is v6-length).
#     The four M2.5 hotend screws seat their heads on the DAV body's counterbore floor.
#  4. The Beacon goes down with the carried tip, back to BEACON_DZ above it (it hangs from the carriage only).
# Found on the way (logged, checked): in lite-15..72 the stand-in never touched the UHF body. The spacer's top sat
# UHF_GAP (8.5 mm) below the UHF body's pocket ceiling, so lite-72's nozzle tip was not where a seated hotend puts it.
# The DAV body's ceiling is the UHF body's minus the spacer's 3 mm (the 3 mm of plastic DW-Tas added there).
# Checks (refuses to save on any):
#  - the UHF body STEP fits every head's body (5 bodies: 1 part + 4 links), the DAV STEP has the UHF STEP's box, the
#    inlays fill the plain DAV body's recesses; the DAV ceiling = the UHF ceiling - 3.0 on every head;
#  - the same 18 hotend parts on every head (1 spacer, 4 screws, 9 held in the heat sink, 4 below it); the MZE STEP's
#    three parts;
#  - after: no spacer left; the DAV body on all 5 heads (its box where its fit puts it, links following the master);
#    heat-sink top on the ceiling and heat-sink top -> tip = 60.6 +- 0.05 on each head; nozzle tips' XY unchanged;
#    the MZE's shoulder on the block's bottom, its stud clear of the heat break; the Beacon face BEACON_DZ above the
#    carried tip; screw heads on the counterbore floor; no new or worse overlap of any changed part with anything; every other
#    solid's box unchanged.
# Measures (the log + json): the stand-in heat block and nozzle (#263, the best figures we have for the Volcano's
# block), the tips' Z change, the Beacon face and the carriage underside above the carried tip, the 4010 ducts'
# lowest point above the tip, and the screws' thread engagement in the heat sink.
import FreeCAD, Part, Import, math, os, re, sys
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
VOLCANO_SPAN = 60.6          # Phaetus, Dragon ACE Volcano: heat-sink top to nozzle tip (#263, owner's screenshot)
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
BEACON_DZ = 2.60             # Beacon coil face above the carried tip (lite-24; Beacon's 2.6-3 zone; owner 2026-11-20)
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
        h.update(top=top, tip=tip, floor=floor, under=unders[0], dz_up=cd[0] - top, dz_low=cd[0] - VOLCANO_SPAN + MZE_TIP - blk0.ZMin,
                 dz_screw=floor - unders[0], uhf_ceiling=cu[0], blk_rel=top - blk0.ZMin)
        p.log(f"{b.Label}: seat Z {cd[0]:.3f} (heat sink +{h['dz_up']:.3f}); tip {tip:.3f} -> {cd[0] - VOLCANO_SPAN:.3f}; heat block "
              f"{h['dz_low']:+.3f} (so {h['dz_up'] - h['dz_low']:.3f} further from the heat sink than in lite-72); counterbore floor "
              f"{floor:.3f}, screws {h['dz_screw']:+.3f}")
    if p.errs: return p.finish([])
    # ---- the Beacon: held only by the carriage (its board top on the pocket ceiling, two M3s, not modelled, into it);
    # nothing else is mounted to it. It goes down by as much as the carried tip, back to BEACON_DZ above it.
    bea = [o for o in pr.leaves if o.Label.startswith(BEACON)]
    car = [o for o in pr.leaves if o.Label == CARRIAGE]
    p.check(len(bea) == 1 and bea[0].TypeId == "Part::Feature" and len(car) == 1, f"one Beacon part, one gantry carriage ({[o.Label for o in bea]})")
    if p.errs: return p.finish([])
    bea, car = bea[0], car[0]
    on = [o.Label for o in pr.leaves if o.Name != bea.Name and linkgeo.link_target(o).Name == bea.Name]
    BS = pr.shapes[bea.Name]
    near = [o.Label for o in pr.leaves if o.Name not in (bea.Name, car.Name) and BS.BoundBox.intersect(pr.shapes[o.Name].BoundBox)
            and BS.distToShape(pr.shapes[o.Name])[0] < 0.05]
    d_car0 = BS.distToShape(pr.shapes[car.Name])[0]
    p.check(not on and not near, f"nothing links to the Beacon or touches it but the carriage (links {on}, touching {near}; "
                                 f"carriage {d_car0:.3f} away)")
    hL = heads[master.Name]; tip_new = hL["seat"] - VOLCANO_SPAN
    bz0 = pr.shapes[bea.Name].BoundBox.ZMin
    dz_b = (tip_new - CARRY_DZ + BEACON_DZ) - bz0
    btop = pr.shapes[bea.Name].BoundBox
    ceil = [above(pr.shapes[car.Name], btop.Center.x + dx, btop.Center.y + dy, btop.ZMax - 0.5) for dx in (-8, 0, 8) for dy in (-4, 4)]
    p.log(f"Beacon: face Z {bz0:.3f} -> {bz0 + dz_b:.3f} ({dz_b:+.3f}); top Z {btop.ZMax:.3f}, {d_car0:.3f} from the carriage; the "
          f"carriage's material above it at 6 points {[round(z, 3) if z else None for z in ceil]}; lowered, its mount gets "
          f"{-dz_b:.2f} mm longer (a shim or longer M3s)")
    # ---- before: overlaps of every part this pass touches
    for h in heads.values():                    # the stand-in's nozzle and sock make way for the MZE assembly's
        h["old"] = [h["nozzle"]] + [o for o in h["g"]["lower"] if o.Label.startswith("TL-dragon")]
        h["keep"] = [o for o in h["g"]["lower"] if o not in h["old"]]
    p.check(all(len(h["old"]) == 2 and len(h["keep"]) == 2 for h in heads.values()), "each head: the stand-in's nozzle and sock go, "
            "its heat block (+ mesh stand-in) stays")
    if p.errs: return p.finish([])
    removed = {o.Name for h in heads.values() for o in h["g"]["spacer"] + h["old"]}
    changed = ({n for n in heads} | {o.Name for h in heads.values() for k in ("screw", "upper", "lower") for o in h["g"][k]
                                     if not linkgeo.is_mesh(o)} | {bea.Name}) - removed
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
        cx, cy = h["axis"]; bot = tight(linkgeo.gshape(h["block"])).ZMin
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
    move_global(bea, V(0, 0, dz_b))
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
        p.check(abs(top - tip - VOLCANO_SPAN) < TOL, f"{b.Label}: heat-sink top -> tip {top - tip:.3f} (Volcano {VOLCANO_SPAN} +- {TOL})")
        o0 = tips0[n]
        p.check(abs(nb.Center.x - o0.Center.x) < 1e-3 and abs(nb.Center.y - o0.Center.y) < 1e-3,
                f"{b.Label}: tip XY unchanged ({nb.Center.x:.3f}, {nb.Center.y:.3f})")
        Mz = linkgeo.gshape(new[n]["MZE"]); mzb = tight(Mz); Bk = linkgeo.gshape(h["block"]); tb_ = tight(Bk)
        HBk = linkgeo.gshape(h["hbreak"]); hx, hy = h["axis"]
        d_blk = Mz.distToShape(Bk)[0]
        p.check(Mz.isValid() and abs(mzb.Center.x - hx) < 1e-3 and abs(mzb.Center.y - hy) < 1e-3 and d_blk < 1e-3
                and abs(mzb.ZMin + MZE_L - tb_.ZMin) < 1e-3,
                f"{b.Label}: the MZE on the hotend axis, its shoulder on the heat block's bottom Z {tb_.ZMin:.3f} (distance {d_blk:.4f})")
        hb_bot = tight(HBk).ZMin; stud_gap = hb_bot - mzb.ZMax
        flange = above(HBk, hx + 4.0, hy, tb_.ZMax)              # the heat break's flange (r 4.25) over the block
        h["stud_gap"], h["flange_gap"] = stud_gap, (flange - tb_.ZMax) if flange else None
        p.check(stud_gap >= -1e-3 and h["flange_gap"] is not None and h["flange_gap"] >= -1e-3,
                f"{b.Label}: the MZE's stud stops {stud_gap:.3f} below the heat break; the block hangs {h['flange_gap'] or 0:.3f} "
                f"below the heat break's flange (lite-72: 0; the block slides down the heat break's thread to reach {VOLCANO_SPAN})")
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
                            mze_stud_below_heat_break=round(h["stud_gap"], 3), block_below_heat_break_flange=round(h["flange_gap"], 3), body_at_screws=round(h["floor"] - top, 3),
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
    clear["carriage_underside_above_carried_tip"] = round(pr.shapes[car.Name].BoundBox.ZMin - carried, 3)
    clear["beacon_gap_under_its_seat"] = round(-dz_b, 3)
    if ducts: clear["ducts_4010_lowest_above_tip"] = round(min(litelib.obb(pr.shapes[o.Name]).ZMin for o in ducts) - tipL, 3)
    p.check(len(clear) == 4, f"clearances measured: {clear} (lite-72: Beacon 2.60, carriage 3.0, ducts 2.41)")
    p.check(abs(clear["beacon_face_above_carried_tip"] - BEACON_DZ) < TOL, f"the Beacon face is {clear['beacon_face_above_carried_tip']:.3f} above the carried tip ({BEACON_DZ} +- {TOL})")
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
            "beacon_dz": round(dz_b, 3), "heads": res, "stand_in_heat_block": block, "clearances": clear, "upstream": UPSTREAM_COMMIT,
            "overlaps_gone": [(round(v, 2), a, b) for v, a, b in gone], "src": os.path.basename(SRC)})
    return p.finish([(doc, DST)])


if not os.environ.get("LITE73_AS_LIB"): litelib.Pass("lite73_dav").run(main)
