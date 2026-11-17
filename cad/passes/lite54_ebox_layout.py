# GUI pass: vt350-lite-53 + vt350-ebox.FCStd -> vt350-lite-54 + vt350-ebox-2.FCStd   (headless = dry run, never saves)
# vt350#5. The e-box layout, concept C (owner chose it 2026-11-15; https://claude.ai/artifact/FMrmmceihcvcKo52hcFaw3),
# on lite-53's inner 2020 frame. A layout study for the owner to approve or change (user, 2026-11-16: "lets see what
# you come up with and I will approve or ask for changes"): positions, not wiring.
#  - vt350-ebox-2.FCStd (from vt350-ebox.FCStd, which stays as it is): the real Octopus (with its DIN clips), Pi 5
#    assembly and SSR are kept and moved, each with its back on the rail face (their printed clips fit the old
#    vertical rails: to reprint for horizontal ones); the Meanwell LRS-200-24 and RS-25, the old vertical DIN rails, DIN mounts,
#    centre supports, WAGO mount and the old cabinet extrusion are removed (concept C: two BOSYTROs, 5 V from a buck,
#    rails on the inner frame). Everything else is a box at its size, labelled with where the size comes from.
#  - DIN rails (TS35 x 7.5) run along Y on the inner frame's face, X 65..72.5, front upright to rear. Five rails:
#    mains (Z 30), PSUs (190), DC fuses + buck (300), logic (400 and 490). Rail-mounted parts start at X 72.5.
#  - The two 600 W supplies lie flat on printed DIN clips (~10, assumed, as lite-46), terminal ends (113 x 50) facing
#    the centre duct between them: 60 V supply in front, 24 V behind.
#  - Ducts (40 x 40, printed white with orange covers in concept C): front and rear trunks, duct 1 above the mains
#    rail, the centre duct, and duct 3 at the top. They sit on the rails, X 72.5..112.5.
#  - DIN modules (breaker, fuse holders, K1) are taken as 90 / 81 tall and 62.5 deep from the rail face: standard
#    widths, depth assumed (to X 135, inside the outer members at X 140).
#  - lite-54: the "Ebox envelope" becomes the union box of vt350-ebox-2's parts and points at it. The Octopus board's
#    stand-in, "Octopus_Pro - beta v1 (simplified box)", lived in the printer model (the old e-box file has only the
#    board's clips and screws): it moves into vt350-ebox-2 with its clips.
# Checks (refuses to save on any): the kept assemblies found and moved by exactly the translation asked; every new
# part inside the e-box (X 65..140, Y -58..480, Z -30..670; the inlet and switch through the rear panel); no two
# layout units overlap; no layout part overlaps a lite-53 part (the envelope and the Octopus stand-in excepted);
# lite-54 = lite-53 - 1 solids.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-53.FCStd", f"{MODELS}/vt350-lite-54.FCStd"
EBOX, EBOX2 = f"{MODELS}/vt350-ebox.FCStd", f"{MODELS}/vt350-ebox-2.FCStd"
RX0, RX1 = 65.0, 72.5                      # DIN rail, X (on the inner frame's face, lite-53)
Y0, Y1 = -58.0, 480.0                      # inner frame, front upright's front face .. rear upright's rear face
STALE = "Octopus_Pro - beta v1 (simplified box)"
KEEP = {   # old e-box App::Part label -> target centre (Y, Z) of its box; X: its back on the rail face (X 72.5).
           # Their printed DIN clips were made for the old VERTICAL rails: to reprint for these horizontal ones.
    "Controllers": (222.5, 445.0),         # Octopus Pro H723, on the logic rails (concept C: Y 174..271)
    "Pi Assembly": (325.0, 390.5),         # Pi 5 + NVMe (C: Y 279..371, Z 362..419)
    "SSR": (92.0, 30.0)}                   # Omron G3NA + clamp heatsink, on the mains rail (C: Y 60..124)
DROP = ["Meanwell RS-25", "Meanwell LRS-200-24", "DIN_Mount", "DIN_Mount (1)", "DIN_Mount (2)", "DIN_Mount (3)",
        "DIN_Center_Support", "DIN_Center_Support001", "3x WAGO_221-415_mount", "Electronics Cabinet",
        "DIN3 Rail", "DIN3 Rail001"]
RAILS = {"mains": 30.0, "PSUs": 190.0, "DC fuses + buck": 300.0, "logic, lower": 400.0, "logic, upper": 490.0}
STEEL, SILVER, WHITE, GREY, DARK, BLUE, BLACK = (0.70, 0.71, 0.73), (0.80, 0.81, 0.83), (0.95, 0.95, 0.94), \
    (0.85, 0.86, 0.86), (0.18, 0.19, 0.21), (0.20, 0.36, 0.62), (0.08, 0.08, 0.09)
ORANGE = (0.91, 0.45, 0.17)
PSU_T, PSU_L, PSU_H, CLIP = 50.0, 215.0, 113.0, 10.0      # BOSYTRO 600 W, measured by the owner (#5): X, Y, Z
MOD_D = 62.5                                               # DIN module depth from the rail face (assumed)
# (label, (x0, x1, y0, y1, z0, z1), colour): global boxes. Sizes: [m] measured, [s] spec, [a] assumed, [c] concept C
def zc(zc_, h): return (zc_ - h / 2, zc_ + h / 2)
P_Z = zc(RAILS["PSUs"], PSU_H)
BLOCKS = [
    # supplies, flat on printed clips
    ("PSU 60 V: BOSYTRO 600 W 0-60 V, set to 48 V (X/Y drivers) [m 215 x 113 x 50]", (RX1 + CLIP, RX1 + CLIP + PSU_T, -32.0, -32.0 + PSU_L, *P_Z), SILVER),
    ("PSU 24 V: BOSYTRO 600 W 0-24 V [m 215 x 113 x 50]", (RX1 + CLIP, RX1 + CLIP + PSU_T, 227.0, 227.0 + PSU_L, *P_Z), SILVER),
    ("PSU clip, 60 V, front (printed) [a 10 deep]", (RX1, RX1 + CLIP, 0.0, 30.0, *zc(RAILS["PSUs"], 35)), WHITE),
    ("PSU clip, 60 V, rear (printed) [a 10 deep]", (RX1, RX1 + CLIP, 120.0, 150.0, *zc(RAILS["PSUs"], 35)), WHITE),
    ("PSU clip, 24 V, front (printed) [a 10 deep]", (RX1, RX1 + CLIP, 260.0, 290.0, *zc(RAILS["PSUs"], 35)), WHITE),
    ("PSU clip, 24 V, rear (printed) [a 10 deep]", (RX1, RX1 + CLIP, 380.0, 410.0, *zc(RAILS["PSUs"], 35)), WHITE),
    # ducts (concept C: printed, white, orange snap-on covers)
    ("Duct, front trunk: frame wiring [c 40 x 40]", (RX1, RX1 + 40, -58.0, -34.0, 85.0, 636.0), WHITE),
    ("Duct, rear trunk: toolhead USB [c 40 x 40]", (RX1, RX1 + 40, 446.0, 480.0, 85.0, 636.0), WHITE),
    ("Duct 1: mains below its divider, DC above [c 40 x 40]", (RX1, RX1 + 40, -34.0, 446.0, 85.0, 125.0), WHITE),
    ("Duct, centre: PSU terminals, clipped to the PSU rail [c 40 x 40]", (RX1, RX1 + 40, 185.0, 225.0, 125.0, 258.0), ORANGE),
    ("Duct 3: signal [c 40 x 40]", (RX1, RX1 + 40, -34.0, 446.0, 596.0, 636.0), WHITE),
    # mains rail (concept C order, front to rear: SSR, K1, F4, F2, F1, Q1, X1)
    ("K1: TBT7-C1 time relay, delays the 24 V supply [a 36 wide, 90 tall]", (RX1, RX1 + MOD_D, 132.0, 168.0, *zc(RAILS["mains"], 90)), GREY),
    ("F4: fuse holder, bed heater (SSR) [a 18 wide]", (RX1, RX1 + MOD_D, 176.0, 194.0, *zc(RAILS["mains"], 81)), GREY),
    ("F2: fuse holder, 24 V supply [a 18 wide]", (RX1, RX1 + MOD_D, 202.0, 220.0, *zc(RAILS["mains"], 81)), GREY),
    ("F1: fuse holder, 60 V supply [a 18 wide]", (RX1, RX1 + MOD_D, 228.0, 246.0, *zc(RAILS["mains"], 81)), GREY),
    ("Q1: 2-pole breaker [a 36 wide, 90 tall]", (RX1, RX1 + MOD_D, 254.0, 290.0, *zc(RAILS["mains"], 90)), GREY),
    ("X1: N and PE terminals [a 48 wide]", (RX1, RX1 + 45, 298.0, 346.0, *zc(RAILS["mains"], 50)), GREY),
    # DC fuse rail
    ("F5: fuse holder, 60 V -> TMC5160T Plus X and Y [a 18 wide]", (RX1, RX1 + MOD_D, 190.0, 208.0, *zc(RAILS["DC fuses + buck"], 81)), GREY),
    ("F6: fuse holder, 24 V -> Octopus [a 18 wide]", (RX1, RX1 + MOD_D, 208.0, 226.0, *zc(RAILS["DC fuses + buck"], 81)), GREY),
    ("F7: fuse holder, 24 V -> Nitehawk Hexa [a 18 wide]", (RX1, RX1 + MOD_D, 226.0, 244.0, *zc(RAILS["DC fuses + buck"], 81)), GREY),
    ("F8: fuse holder, 24 V -> buck [a 18 wide]", (RX1, RX1 + MOD_D, 244.0, 262.0, *zc(RAILS["DC fuses + buck"], 81)), GREY),
    ("Buck 24 -> 5 V, for the Pi (as the Neptune's EA60) [m 62 x 56, a 32 deep]", (RX1, RX1 + 32, 290.0, 352.0, *zc(RAILS["DC fuses + buck"], 56)), BLUE),
    # logic
    ("TMC5160T Plus, X, in its case [s 64 x 56 x 32.55]", (RX1, RX1 + 32.55, 110.0, 166.0, 362.0, 426.0), DARK),
    ("TMC5160T Plus, Y, in its case [s 64 x 56 x 32.55]", (RX1, RX1 + 32.55, 110.0, 166.0, 434.0, 498.0), DARK),
    ("Nitehawk Hexa on the owner's printed holder, upright [m 44 x 139, a 57 deep]", (RX1, RX1 + 57, 303.0, 347.0, 430.0, 569.0), BLACK),
    # rear panel
    ("Inlet: C14 with fuse and EMI filter, in the rear panel [a]", (85.0, 115.0, 490.0, 545.0, 0.0, 70.0), BLACK),
    ("Mains switch, in the rear panel [a]", (85.0, 115.0, 490.0, 545.0, 90.0, 120.0), BLACK),
]
for name, z in RAILS.items():
    BLOCKS.append((f"DIN rail TS35 x 7.5, {name}, Z {z:.0f}", (RX0, RX1, Y0, Y1, *zc(z, 35)), STEEL))
INSIDE = (RX0, 140.0, Y0, Y1, -30.0, 670.0)
REAR_PANEL = ("Inlet", "Mains switch")


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    stale = [o for o in pr.leaves if o.Label == STALE]
    p.check(len(stale) == 1, f"the Octopus board's stand-in in the printer model: {len(stale)} (1)")
    eb = p.open(EBOX); ed = eb.doc
    by = {o.Label: o for o in ed.Objects}
    def subtree(o):
        out = [o]
        for c in getattr(o, "Group", []) or []: out += subtree(c)
        return out
    # 1. drop what concept C replaces
    gone = 0
    for lab in DROP:
        o = by.get(lab)
        if not p.check(o is not None, f"old e-box part to remove: {lab}"): continue
        objs = subtree(o)
        if o.TypeId == "App::Part": objs += [x for x in o.OutList if x.TypeId.startswith("App::Origin") or x.TypeId in ("App::Line", "App::Plane", "App::Point")]
        gone += sum(1 for x in objs if linkgeo.is_leaf(x))
        for x in reversed(objs):
            try: ed.removeObject(x.Name)
            except Exception: pass
    ed.recompute(); eb.refresh()
    p.log(f"removed {gone} solids of the old layout; {len(eb.leaves)} left")
    # 2. move the kept assemblies: rail face X 57 -> 72.5, box centres to concept C's places
    moves = {}
    for lab, (yc, zc_) in KEEP.items():
        o = next((x for x in ed.Objects if x.Label == lab and x.TypeId == "App::Part"), None)
        if not p.check(o is not None, f"kept assembly found: {lab}"): continue
        leaves = [x for x in subtree(o) if linkgeo.is_leaf(x)]
        bb = FreeCAD.BoundBox()
        for x in leaves: bb.add(eb.boxes[x.Name])
        d = V(RX1 - bb.XMin, yc - (bb.YMin + bb.YMax) / 2, zc_ - (bb.ZMin + bb.ZMax) / 2)   # its back on the rail face
        gp = linkgeo.gplace(o); par = gp.multiply(o.Placement.inverse())
        o.Placement = par.inverse().multiply(FreeCAD.Placement(d, FreeCAD.Rotation()).multiply(gp))
        moves[lab] = (o, leaves, bb, d)
    ed.recompute(); eb.refresh()
    for lab, (o, leaves, bb, d) in moves.items():
        nb = FreeCAD.BoundBox()
        for x in leaves: nb.add(eb.boxes[x.Name])
        p.check(all(abs(a - b) < 0.05 for a, b in ((nb.XMin, bb.XMin + d.x), (nb.YMin, bb.YMin + d.y), (nb.ZMin, bb.ZMin + d.z),
                                                   (nb.XMax, bb.XMax + d.x), (nb.YMax, bb.YMax + d.y), (nb.ZMax, bb.ZMax + d.z))),
                f"{lab}: moved ({d.x:.1f}, {d.y:.1f}, {d.z:.1f}) -> X {nb.XMin:.1f}..{nb.XMax:.1f} Y {nb.YMin:.1f}..{nb.YMax:.1f} Z {nb.ZMin:.1f}..{nb.ZMax:.1f}")
    # 3. the new parts, in one App::Part in the global frame
    grp = ed.addObject("App::Part", "Layout"); grp.Label = "E-box layout, concept C on the inner frame (lite-54)"
    new = []
    for label, b, col in BLOCKS:
        new += p.add_solids(ed, grp, [("", box(*b))], "Block", label, col)
    # the Octopus board itself: its stand-in lived in the printer model (the old e-box file has only its clips and
    # screws); it moves into vt350-ebox-2 with the same translation as its clips
    if stale and "Controllers" in moves:
        sb = pr.shapes[stale[0].Name].translated(moves["Controllers"][3])
        new += p.add_solids(ed, grp, [("", sb)], "Block",
                            "Octopus Pro H723 board (simplified box, moved from the printer model) [m 100 x 162]", BLACK)
    ed.recompute(); eb.refresh()
    # checks: inside the e-box
    for o in new:
        b = eb.boxes[o.Name]
        if o.Label.startswith(REAR_PANEL):
            ok = b.XMin >= RX0 and b.XMax <= INSIDE[1] and b.ZMin >= INSIDE[4]
        else:
            ok = (b.XMin >= INSIDE[0] - 0.01 and b.XMax <= INSIDE[1] + 0.01 and b.YMin >= INSIDE[2] - 0.01 and
                  b.YMax <= INSIDE[3] + 0.01 and b.ZMin >= INSIDE[4] - 0.01 and b.ZMax <= INSIDE[5] + 0.01)
        p.check(ok, f"inside the e-box: {o.Label[:60]}: X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.1f}..{b.ZMax:.1f}")
    # checks: no two layout units overlap (a unit = a kept assembly, or one new block)
    # the Octopus board rests on its own DIN clips: board and clips are one unit
    board = [o for o in new if o.Label.startswith("Octopus Pro H723 board")]
    units = [(lab, Part.makeCompound([eb.shapes[x.Name] for x in leaves + (board if lab == "Controllers" else [])]))
             for lab, (o, leaves, bb, d) in moves.items()]
    units += [(o.Label, eb.shapes[o.Name]) for o in new if o not in board]
    pairs = [(a, b) for i, a in enumerate(units) for b in units[i + 1:] if a[1].BoundBox.intersect(b[1].BoundBox)]
    vols = p.volumes([(a[1], b[1]) for a, b in pairs])
    hits = [(a[0][:40], b[0][:40], round(v, 1)) for (a, b), v in zip(pairs, vols) if v > 1e-3]
    p.check(not hits, f"layout units overlap: {len(hits)} {hits[:10]}")
    # 4. lite-54: the printer model
    env = [o for o in pr.leaves if o.Label.startswith("Ebox envelope")]
    p.check(len(env) == 1, f"envelope {len(env)} (1)")
    excl = {o.Name for o in env + stale}
    items = [(x.Label, eb.shapes[x.Name]) for x in eb.leaves]
    p.no_overlap(items, pr, lambda r: f"no e-box part overlaps a lite-53 part: {len(r.hits)} {r.hits[:10]}", exclude=excl)
    n0 = len(pr.leaves)
    if stale: doc.removeObject(stale[0].Name)
    allbb = FreeCAD.BoundBox()
    for x in eb.leaves: allbb.add(eb.boxes[x.Name])
    if env: p.resize_envelope(pr, env[0], allbb, "Ebox envelope (contents in vt350-ebox-2.FCStd)")
    pr.refresh()
    p.check(len(pr.leaves) == n0 - 1, f"lite-54 solids: {len(pr.leaves)} (lite-53 - 1 = {n0 - 1})")
    p.dump({"ebox2_solids": len(eb.leaves), "removed": gone, "kept": {k: [round(v, 1) for v in m[3]] for k, m in moves.items()},
            "blocks": [[l, list(b)] for l, b, _ in BLOCKS], "envelope": [allbb.XMin, allbb.XMax, allbb.YMin, allbb.YMax, allbb.ZMin, allbb.ZMax]})
    return p.finish([(ed, EBOX2), (doc, DST)])


litelib.Pass("lite54_ebox_layout").run(main)
