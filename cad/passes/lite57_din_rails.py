# GUI pass: vt350-lite-56 + vt350-ebox-2.FCStd -> vt350-lite-57 + vt350-ebox-3.FCStd   (headless = dry run, never saves)
# vt350#5. Real DIN rails on the owner's holders (owner, 2026-11-16: "the din rails need to added and I think you can
# find the holders for them in my neptune ebox cad"; the holder is "DIN_frame_mount_x4_square" in
# ~/Documents/3D Files/ebox/ebox.FCStd, and it is shareable).
#  - The holder is a 60 x 14 x 11 printed spacer with a 0.8 mm key along its length: it stands up an inner upright,
#    its key in the upright's X 65 face slot, and the rail crosses it. One at each end of each rail: 10. Taken from
#    the Neptune file's mesh, made a solid; placed so its key is centred on the slot.
#  - The rails become TS35 x 7.5 (EN 60715) in section, drawn here (1 mm steel: a 27 mm back web, the walls, the
#    lips to 35): back X 76 (on the holders), face X 83.5, Y -58..480 (front upright to rear upright, 538 long).
#    No slots drawn.
#  - The rail face moves out 72.5 -> 83.5: every rail-mounted part (and the ducts, PSU clips, kept assemblies) moves
#    +11 in X. The mains rail goes up 30 -> 36 with its parts, so the 90-tall modules (now reaching X 146) stay
#    above the e-box's bottom outer rail (Z -10).
#  - vt350-ebox-3.FCStd is written from vt350-ebox-2.FCStd (which stays as it is); lite-57's envelope points at it.
# Checks (refuses to save on any): the holder mesh found and made a closed solid; every moved part moved by exactly
# what was asked; every part inside the e-box (X 64..160: the door frame starts at X 163); no two layout units
# overlap; no e-box part overlaps a lite-56 part (the envelopes excepted); lite-57 solids = lite-56.
import FreeCAD, Part, Mesh, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-56.FCStd", f"{MODELS}/vt350-lite-57.FCStd"
EBOX2, EBOX3 = f"{MODELS}/vt350-ebox-2.FCStd", f"{MODELS}/vt350-ebox-3.FCStd"
NEPTUNE = os.path.expanduser("~/Documents/3D Files/ebox/ebox.FCStd")
HOLDER = "DIN_frame_mount_x4_square"
FACE0 = 65.0                                  # the inner uprights' outer face (lite-53)
RB, RF = 76.0, 83.5                           # rail back (on the holders), rail face
DX = RF - 72.5                                # every rail-mounted part moves out by this
MAINS_DZ = 6.0                                # the mains rail and its parts go up by this
Y0, Y1 = -58.0, 480.0
UPRIGHT_Y = (-48.0, 470.0)                    # centres of the front and rear inner uprights (lite-53)
RAILS = {"mains": 36.0, "PSUs": 190.0, "DC fuses + buck": 300.0, "logic, lower": 400.0, "logic, upper": 490.0}
MAINS = ("SSR", "K1:", "F4:", "F2:", "F1:", "Q1:", "X1:")
STAY = ("Inlet", "Mains switch", "DIN rail")   # through the rear panel / rebuilt
INSIDE = (64.0, 160.0, -58.0, 480.0, -30.0, 670.0)
STEEL, WHITE = (0.70, 0.71, 0.73), (0.95, 0.95, 0.94)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rail(zc):
    """TS35 x 7.5 in section (1 mm): back web 27 wide at X RB..RB+1, walls, lips out to 35 at the face."""
    t = 1.0
    parts = [box(RB, RB + t, Y0, Y1, zc - 13.5, zc + 13.5)]
    for s in (1, -1):
        parts.append(box(RB + t, RF, Y0, Y1, *sorted((zc + s * 12.5, zc + s * 13.5))))
        parts.append(box(RF - t, RF, Y0, Y1, *sorted((zc + s * 13.5, zc + s * 17.5))))
    return Part.makeCompound(parts)


def main(p):
    # the holder, from the owner's Neptune e-box
    nd = FreeCAD.openDocument(NEPTUNE)
    hm = next((o for o in nd.Objects if o.Label == HOLDER), None)
    if not p.check(hm is not None, f"holder mesh {HOLDER} in {NEPTUNE}"): return p.finish([])
    m = hm.Mesh.copy(); m.Placement = FreeCAD.Placement()
    sh = Part.Shape(); sh.makeShapeFromMesh(m.Topology, 0.05)
    hs = Part.makeSolid(sh)
    p.check(hs.isValid() and hs.Volume > 0.9 * m.Volume, f"holder solid valid, volume {hs.Volume:.0f} (mesh {m.Volume:.0f})")
    key = [v for v in m.Points if v.z > 11.05]
    kx = (min(v.x for v in key) + max(v.x for v in key)) / 2 if key else 0.0
    hb = hs.BoundBox
    p.log(f"holder {hb.XLength:.1f} x {hb.YLength:.1f} x {hb.ZLength:.1f}, key at local x {kx:.2f}, top z {hb.ZMax:.2f}")
    FreeCAD.closeDocument(nd.Name)
    # local (x, y, z) -> global (RB - z, -x + yc, y + zc): z (thickness) out of the upright, y (60) up it, key to -X
    def holder_at(yc, zc):
        mat = FreeCAD.Matrix(0, 0, -1, RB, -1, 0, 0, yc + kx, 0, 1, 0, zc, 0, 0, 0, 1)   # body z 0..11 -> X 76..65; key into the slot
        s = hs.copy(); s.transformShape(mat); return s

    eb = p.open(EBOX2); ed = eb.doc
    lay = next(o for o in ed.Objects if o.TypeId == "App::Part" and o.Label.startswith("E-box layout"))
    tops = [o for o in ed.Objects if o.TypeId == "App::Part" and o.Label in ("Controllers", "Pi Assembly", "SSR")]
    before = {o.Name: eb.boxes[o.Name] for o in eb.leaves}
    def subtree(o):
        out = []
        for c in getattr(o, "Group", []) or []: out += [c] + subtree(c)
        return out
    owner = {}
    for t in tops:
        for x in subtree(t): owner[x.Name] = t.Label
    # 1. old rail strips out
    old = [o for o in lay.Group if o.Label.startswith("DIN rail")]
    p.check(len(old) == 5, f"old rail strips: {len(old)} (5)")
    for o in old: ed.removeObject(o.Name)
    # 2. move: assemblies by Placement; layout blocks by Placement
    want = {}
    def move(o, d):
        gp = linkgeo.gplace(o); par = gp.multiply(o.Placement.inverse())
        o.Placement = par.inverse().multiply(FreeCAD.Placement(d, FreeCAD.Rotation()).multiply(gp))
    for t in tops:
        d = V(DX, 0, MAINS_DZ if t.Label == "SSR" else 0); move(t, d)
        for x in subtree(t):
            if x.Name in before: want[x.Name] = d
    for o in list(lay.Group):
        if o.Label.startswith(STAY) or o.Name not in before: continue
        d = V(DX, 0, MAINS_DZ if o.Label.startswith(MAINS) else 0); move(o, d); want[o.Name] = d
    # 3. new rails and holders
    new = []
    for name, zc in RAILS.items():
        new += p.add_solids(ed, lay, [("", rail(zc))], "DinRail", f"DIN rail TS35 x 7.5 (EN 60715), {name}, Z {zc:.0f}, 538 long", STEEL)
        for yc, end in zip(UPRIGHT_Y, ("front", "rear")):
            new += p.add_solids(ed, lay, [("", holder_at(yc, zc))], "DinHolder",
                                f"DIN rail holder (owner's Neptune DIN_frame_mount), {name} rail, {end} upright", WHITE)
    ed.recompute(); eb.refresh()
    # checks: moves
    bad = []
    for n, d in want.items():
        a, b = before[n], eb.boxes[n]
        if max(abs(b.XMin - a.XMin - d.x), abs(b.XMax - a.XMax - d.x), abs(b.YMin - a.YMin), abs(b.ZMin - a.ZMin - d.z),
               abs(b.ZMax - a.ZMax - d.z)) > 0.05: bad.append(ed.getObject(n).Label[:40])
    p.check(not bad, f"{len(want)} parts moved by (+{DX}, 0, 0) (+{MAINS_DZ} Z on the mains rail): {len(bad)} off {bad[:6]}")
    for o in new:
        b = eb.boxes[o.Name]
        p.check(b.XMin >= INSIDE[0] and b.XMax <= INSIDE[1] + 0.01 and b.YMin >= INSIDE[2] - 0.01 and b.YMax <= INSIDE[3] + 0.01,
                f"{o.Label[:62]}: X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.1f}..{b.ZMax:.1f}")
    out = [o.Label[:40] for o in eb.leaves if not o.Label.startswith(STAY[:2])
           and not (eb.boxes[o.Name].XMax <= INSIDE[1] + 0.01 and eb.boxes[o.Name].XMin >= INSIDE[0] - 0.01)]
    p.check(not out, f"every e-box part within X {INSIDE[0]}..{INSIDE[1]}: {len(out)} out {out[:6]}")
    # units: a kept assembly (the Octopus board with its clips), or one layout part
    units = {}
    for o in eb.leaves:
        k = owner.get(o.Name) or ("Controllers" if o.Label.startswith("Octopus Pro H723 board") else o.Name)
        units.setdefault(k, []).append(eb.shapes[o.Name])
    ul = [(k if k in ("Controllers", "Pi Assembly", "SSR") else ed.getObject(k).Label, Part.makeCompound(v)) for k, v in units.items()]
    pairs = [(a, b) for i, a in enumerate(ul) for b in ul[i + 1:] if a[1].BoundBox.intersect(b[1].BoundBox)]
    vols = p.volumes([(a[1], b[1]) for a, b in pairs])
    hits = [(a[0][:36], b[0][:36], round(v, 1)) for (a, b), v in zip(pairs, vols) if v > 1e-3]
    p.check(not hits, f"layout units overlap: {len(hits)} {hits[:10]}")
    # the printer
    pr = p.open(SRC); doc = pr.doc
    env = [o for o in pr.leaves if o.Label.startswith("Ebox envelope")]
    p.check(len(env) == 1, f"e-box envelope {len(env)} (1)")
    excl = {o.Name for o in pr.leaves if "envelope" in o.Label}
    p.no_overlap([(o.Label, eb.shapes[o.Name]) for o in eb.leaves], pr,
                 lambda r: f"no e-box part overlaps a lite-56 part: {len(r.hits)} {r.hits[:10]}", exclude=excl)
    n0 = len(pr.leaves)
    allbb = FreeCAD.BoundBox()
    for o in eb.leaves: allbb.add(eb.boxes[o.Name])
    if env: p.resize_envelope(pr, env[0], allbb, "Ebox envelope (contents in vt350-ebox-3.FCStd)")
    pr.refresh()
    p.check(len(pr.leaves) == n0, f"lite-57 solids: {len(pr.leaves)} (= lite-56)")
    p.dump({"rail_back_face": [RB, RF], "dx": DX, "mains_dz": MAINS_DZ, "rails": RAILS, "holders": 2 * len(RAILS),
            "envelope": [allbb.XMin, allbb.XMax, allbb.YMin, allbb.YMax, allbb.ZMin, allbb.ZMax]})
    return p.finish([(ed, EBOX3), (doc, DST)])


litelib.Pass("lite57_din_rails").run(main)
