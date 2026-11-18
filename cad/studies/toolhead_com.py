# SPDX-License-Identifier: GPL-3.0-or-later
# Mass and centre of mass of each carried toolhead and of the moving X assembly (vt350#60, AC2-AC4): read-only.
#
#   $APP freecadcmd $PWD/cad/studies/toolhead_com.py          # VT350_MODEL=<lite-N.FCStd> to pick the model
#
# Each head is placed on the gantry carriage as sweep_toolhead.py does (moved by -T_pick). Masses come from each
# solid's ShapeMaterial density. Many solids carry FreeCAD's "Default" material (1e-9 kg/mm3, i.e. weightless), so the
# masses and CoMs are given two ways, with every Default solid as printed plastic (DEFAULT_LO) and as aluminium
# (DEFAULT_HI), and the Default solids are listed with their volumes (AC2: the uncertainty made visible). Neither is
# a measurement: AC6 (weighing the real parts) is what settles it.
#
# Output: cad/data/logs/toolhead_com.log, flushed line by line. Ends with "toolhead_com: done".
import os, re, sys, time

WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-63.FCStd")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE] + [os.path.join(os.path.dirname(os.path.dirname(HERE)), d) for d in ("platform/freecad",)]
HEADS = {"Left": dict(group="Left Toolhead", dock="Left Dock", copy="COMPOUND003", tube="Bowden Left",
                      plate=["Plate", "Plate Back"]),
         "Right": dict(group="Right Toolhead", dock="Right Dock", copy="COMPOUND004", tube="Bowden Right",
                       plate=["Plate(Mirror)", "Plate Back(Mirror)"])}
TUBES = ("Bowden Left", "Bowden Right")
CARRIAGE_PART = ("Carriage (1)", "COMPOUND")
CARRIAGE_PATHS = {"Carriage (1)"}
CARRIAGE_LABELS = ("MGN_12_H_CARRAGE v1",)
BLOCK = "MGN_12_H_CARRAGE v1"
BELTS = ("GT2 9mm belt, lower (Monolith 2WD)", "GT2 9mm belt, upper (Monolith 2WD)")
BEAM = "Carbonara CF X beam 20x20 430"
NOZZLE = "E3D v6 HotEnd - Nozzle"
DEFAULT_LO, DEFAULT_HI = 1.27e-6, 2.7e-6        # kg/mm3: PETG (printed parts), aluminium 6061
LOG = os.path.join(WORK, "logs", "toolhead_com.log")
T0 = time.time()
_f = open(LOG, "w")


def log(s=""):
    _f.write(f"[{time.time() - T0:7.1f}s] {s}\n"); _f.flush()


def density(o, linkgeo):
    sm = getattr(linkgeo.link_target(o), "ShapeMaterial", None)
    if sm is None or sm.Name == "Default": return None, "Default"
    m = re.match(r"([0-9.eE+-]+) kg/mm\^3", sm.PhysicalProperties.get("Density", ""))
    return (float(m.group(1)), sm.Name) if m else (None, sm.Name)


def main():
    import FreeCAD, Part
    import linkgeo
    V = FreeCAD.Vector
    import matlib
    # a model stores only each material's UUID: register the repo's cards first, or every part with one of them
    # reopens as weightless Default with no warning (platform/freecad/LESSONS.md, "Materials")
    mm = matlib.use_dir(os.path.join(os.path.dirname(os.path.dirname(HERE)), "cad", "materials"))
    log(f"material cards: {sum(1 for _, m in mm.Materials.items() if m.LibraryName == 'Custom')} in the Custom library")
    doc = FreeCAD.openDocument(MODEL)
    log(f"opened {MODEL}")
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, p = [], par.get(o.Name)
        while p is not None: r.append(p.Label); p = par.get(p.Name)
        return r
    # a stand-in (StandInFor, vt350#195) is a cheap copy of a real part that is also in the model: count the real one
    leaves = [o for o in doc.Objects if linkgeo.is_leaf(o) and not getattr(o, "StandInFor", "")]
    P = {o.Name: set(path(o)) for o in leaves}
    def one(label, under=None):
        c = [o for o in leaves if o.Label == label and (under is None or under in P[o.Name])]
        if len(c) != 1: raise RuntimeError(f"{len(c)} leaves labelled {label!r} under {under!r}")
        return c[0]
    def vc(s):                                    # (volume, centroid) over the solids (a link's shape is a compound)
        vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
        return tv, sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
    _vc = {}
    def item(o, shift=None):
        if o.Name not in _vc: _vc[o.Name] = vc(linkgeo.gshape(o))
        v, c = _vc[o.Name]
        if shift is not None: c = c + shift
        d, mat = density(o, linkgeo)
        return dict(label=o.Label, vol=v, com=c, rho=d, mat=mat)
    def total(items, dflt):
        m = sum(i["vol"] * (i["rho"] if i["rho"] is not None else dflt) for i in items)
        c = sum((i["com"] * (i["vol"] * (i["rho"] if i["rho"] is not None else dflt) / m) for i in items), V(0, 0, 0))
        return m, c
    real = linkgeo.gshape(one(*CARRIAGE_PART[::-1]))
    carriage = [item(o) for o in leaves if P[o.Name] & CARRIAGE_PATHS or o.Label in CARRIAGE_LABELS]
    # references (AC4)
    bb = linkgeo.gshape(one(BLOCK)).BoundBox
    block = V(bb.Center.x, bb.Center.y, bb.Center.z)
    beam = linkgeo.gshape(one(BEAM)).BoundBox
    cx = block.x
    belts = []
    for lab in BELTS:
        s = linkgeo.gshape(one(lab))
        near = s.common(Part.makeBox(60, 4000, 4000, V(cx - 30, -2000, -2000)))   # the belt where it passes the carriage
        b = near.BoundBox if not near.isNull() and near.Solids else s.BoundBox
        belts.append((lab, b))
    log(f"X rail block centre ({block.x:.2f}, {block.y:.2f}, {block.z:.2f}); X beam centre line Y {beam.Center.y:.2f}, "
        f"Z {beam.Center.z:.2f}")
    for lab, b in belts:
        log(f"{lab}: near the carriage Y {b.YMin:.2f}..{b.YMax:.2f}, Z {b.ZMin:.2f}..{b.ZMax:.2f} (centre Z {b.Center.z:.2f})")
    def rel(c, tip):
        lines = [f"      vs the nozzle tip   dX {c.x - tip.x:+7.2f}  dY {c.y - tip.y:+7.2f}  dZ {c.z - tip.z:+7.2f}",
                 f"      vs the block centre dX {c.x - block.x:+7.2f}  dY {c.y - block.y:+7.2f}  dZ {c.z - block.z:+7.2f}",
                 f"      vs the X beam line           dY {c.y - beam.Center.y:+7.2f}  dZ {c.z - beam.Center.z:+7.2f}"]
        # the belts run along Y where they pass the carriage (they span Y 258..465 there): only their plane's Z means
        # anything for a CoM offset
        lines += [f"      vs the {lab.split(',')[1].split('(')[0].strip()} belt's plane                 dZ {c.z - b.Center.z:+7.2f}"
                  for lab, b in belts]
        return lines
    def report(name, items, tip):
        known = [i for i in items if i["rho"] is not None]
        unk = [i for i in items if i["rho"] is None]
        log(f"-- {name}: {len(items)} solids; {len(unk)} with Default material, {sum(i['vol'] for i in unk) / 1000:.1f} cm3 of "
            f"{sum(i['vol'] for i in items) / 1000:.1f} cm3")
        for tag, dflt in ((f"Default as PETG {DEFAULT_LO * 1e6:.2f} g/cm3", DEFAULT_LO), (f"Default as aluminium {DEFAULT_HI * 1e6:.2f} g/cm3", DEFAULT_HI)):
            m, c = total(items, dflt)
            log(f"   {tag}: mass {m * 1000:.0f} g, CoM ({c.x:.2f}, {c.y:.2f}, {c.z:.2f})")
            for l in rel(c, tip): log(l)
        mk = sum(i["vol"] * i["rho"] for i in known)
        log(f"   known materials only: {mk * 1000:.0f} g")
        return unk
    for h, d in HEADS.items():
        t_pick = vc(linkgeo.gshape(one(d["copy"], d["dock"])))[1] - vc(real)[1]
        sh = V(0, 0, 0) - t_pick
        nz = one(next(o.Label for o in leaves if o.Label.startswith(NOZZLE) and d["group"] in P[o.Name]), d["group"])
        nb = linkgeo.gshape(nz).BoundBox
        tip = V(nb.Center.x, nb.Center.y, nb.ZMin) + sh
        log("")
        log(f"===== {h} head carried (moved by -T_pick ({t_pick.x:.3f}, {t_pick.y:.3f}, {t_pick.z:.3f})); nozzle tip "
            f"({tip.x:.2f}, {tip.y:.2f}, {tip.z:.2f})")
        head = [item(o, sh) for o in leaves if d["group"] in P[o.Name] and o.Label not in TUBES]
        plate = [item(one(l, d["dock"]), sh) for l in d["plate"]]
        tube = [item(one(d["tube"]), sh)]   # the tube as modelled from the docked pose: a rigid route (sweep_toolhead)
        unk = report(f"{h} tool (head + Plate + Plate Back), no bowden (AC2)", head + plate, tip)
        report(f"{h} tool with its bowden tube (AC2; the tube as routed from the dock, moved rigidly)", head + plate + tube, tip)
        report(f"moving X assembly: carriage, Beacon, MGN12 block, clamps (AC3)", carriage, tip)
        unk += report(f"whole carried system with the {h} head, no bowden (AC3)", carriage + head + plate, tip)[:0]
        log(f"   Default-material solids in the {h} tool (AC2), largest first:")
        for i in sorted(unk, key=lambda i: -i["vol"]):
            log(f"      {i['vol'] / 1000:8.2f} cm3  {i['label'][:90]}")
    cu = [i for i in carriage if i["rho"] is None]
    log("")
    log("Default-material solids in the moving X assembly: " + ("; ".join(f"{i['label'][:50]} {i['vol'] / 1000:.2f} cm3" for i in cu) or "none"))
    log("")
    log("toolhead_com: done")


try:
    main()
except Exception:
    import traceback
    log(traceback.format_exc())
_f.close()
