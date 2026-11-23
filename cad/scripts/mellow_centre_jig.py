# freecadcmd script: the Mellow centre jig, a printed tool (vt350#291). Read-only for the models; writes
# cad/derived/mellow-centre-jig/mellow-centre-jig.{step,stl} and a JSON of its checks.
#    $APP freecadcmd $PWD/cad/scripts/mellow_centre_jig.py
#
# Owner, 2026-11-22: the Mellow MultiHead Zero goes on the plate centre to calibrate (by hand, tc_offsets.cfg
# MELLOW_CALIBRATE_START) and parks on the backbone otherwise; a printed jig puts it back on the same spot each time
# (plus a re-find each run). The plate stack (aluminium 10 + magnet sheet 1.4 + PEI 1.0) is flush at 355 x 355, so:
#  - an L that hooks over the plate's FRONT and LEFT edges (lips down the edge, clear of the corner's radius),
#  - a diagonal arm from the corner to a POCKET at the plate centre that fits the parked carrier's base (lite-78's
#    parked_zero(), the same code), +0.2 mm all round, the probe's axis on the centre.
# Use: lay the jig on the plate with both lips against the edges, drop the carrier (Zero on it) into the pocket, lift the
# jig straight up (the pocket is outside the Zero's whole outline). If the PEI sheet overhangs the aluminium, the lips
# register on the sheet's edge: the sheet must then be seated the same way each time.
# Print: upside down (the face that lies on the plate goes on the build plate, lips up): flat, no supports.
# Frame: printer coordinates, plate top Z 0, the plate's front-left corner at (-2.5, -2.5) (xy_mapping.json).
import FreeCAD, Part, Mesh, MeshPart, os, sys, json
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render"), os.path.join(_REPO, "cad/passes")]
os.environ["LITE78_AS_LIB"] = "1"
import lite78_front17 as L, printchamfer
V = FreeCAD.Vector
PLATE = (-2.5, 352.5)                 # the 355 plate, printer X and Y
CENTRE = (175.0, 175.0)
T = 3.0                               # the jig's thickness on the plate
W = 12.0                              # arm width
LIP_T, LIP_D = 3.0, 8.0               # lip thickness, how far down the plate's edge (the stack is 12.4)
LIP_FROM = 30.0                       # lips start this far from the corner (clear of its radius)
FIT, RIM = 0.2, 6.0                   # pocket clearance round the carrier's base, the rim round the pocket
OUT = os.path.join(_REPO, "cad/derived/mellow-centre-jig")


def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def main():
    res = {"checks": []}
    def check(ok, what): res["checks"].append(("ok" if ok else "FAIL", what)); print(("ok   " if ok else "FAIL ") + what)
    # the carrier with the Zero at the plate centre: build it with the module's own code, then move the probe's axis
    parts, _ = L.parked_zero(0.0, 0.0)
    probe_bb = parts["probe"][1].BoundBox
    ax = ((probe_bb.XMin + probe_bb.XMax) / 2, (probe_bb.YMin + probe_bb.YMax) / 2)
    mv = V(CENTRE[0] - ax[0], CENTRE[1] - ax[1], 0)
    zero = {k: s.copy() for k, (lab, s) in parts.items()}
    for s in zero.values(): s.translate(mv)
    cb = zero["carrier"].BoundBox
    x0, y0 = PLATE[0], PLATE[0]
    px0, px1, py0, py1 = cb.XMin - FIT, cb.XMax + FIT, cb.YMin - FIT, cb.YMax + FIT
    reach = px1 + RIM                                       # the arms run as far as the pocket's rim
    front = bx(x0, reach, y0, y0 + W, 0, T)
    left = bx(x0, x0 + W, y0, py1 + RIM, 0, T)
    lip_f = bx(x0 + LIP_FROM, reach - 10, y0 - LIP_T, y0, -LIP_D, T)
    lip_l = bx(x0 - LIP_T, x0, y0 + LIP_FROM, py1 + RIM - 10, -LIP_D, T)
    rim = bx(px0 - RIM, px1 + RIM, py0 - RIM, py1 + RIM, 0, T)
    # the diagonal arm: from the corner to the rim's front-left corner, W wide
    a, b = V(x0 + W / 2, y0 + W / 2, 0), V(px0 - RIM / 2, py0 - RIM / 2, 0)
    d = b - a; Ln = d.Length; d.normalize()
    arm = bx(0, Ln, -W / 2, W / 2, 0, T)
    arm.Placement = FreeCAD.Placement(a, FreeCAD.Rotation(V(1, 0, 0), d))
    # a second arm from the far ends of the L to the rim's sides makes it a stiff frame
    def bar(p, q):
        dd = q - p; l = dd.Length; dd.normalize()
        s = bx(0, l, -W / 2, W / 2, 0, T); s.Placement = FreeCAD.Placement(p, FreeCAD.Rotation(V(1, 0, 0), dd)); return s
    brace_f = bar(V(reach - W / 2, y0 + W / 2, 0), V(px1 + RIM / 2, py0 - RIM / 2, 0))
    brace_l = bar(V(x0 + W / 2, py1 + RIM - W / 2, 0), V(px0 - RIM / 2, py1 + RIM / 2, 0))
    jig = front.fuse([left, lip_f, lip_l, rim, arm, brace_f, brace_l]).removeSplitter()
    jig = jig.cut(bx(px0, px1, py0, py1, -1, T + 1)).removeSplitter()
    # printed upside down: "up" for the chamfers is -Z (the plate-side face is the first layer)
    prof = printchamfer.profile(os.path.join(_REPO, "cad/data/print-profile.json"))
    jc, info = printchamfer.chamfer(jig, V(0, 0, -1), **prof)
    left_e = printchamfer.unchamfered(jig, jc, V(0, 0, -1), **prof,
                                      skip={w for k, w, c in info["skipped"]} | {w for k, w in info.get("failed", [])})
    jb = jc.BoundBox
    check(jc.isValid() and len(jc.Solids) == 1, f"one valid solid, {jc.Volume:.0f} mm3 ({jc.Volume * 1.27e-3:.0f} g of ABS-ish)")
    check(jb.XLength <= 340 and jb.YLength <= 340, f"fits the bed: {jb.XLength:.1f} x {jb.YLength:.1f} x {jb.ZLength:.1f}")
    pc = ((px0 + px1) / 2, (py0 + py1) / 2)
    pb = zero["probe"].BoundBox
    check(abs((pb.XMin + pb.XMax) / 2 - CENTRE[0]) < 1e-6 and abs((pb.YMin + pb.YMax) / 2 - CENTRE[1]) < 1e-6,
          f"the probe's axis on the plate centre {CENTRE} (pocket centre {pc[0]:.2f}, {pc[1]:.2f}: the carrier's base "
          f"isn't centred on the probe)")
    for k, s in zero.items():
        v = s.common(jc).Volume
        check(v < 1e-3, f"the jig clears the {k} in the pocket ({v:.4f} mm3)")
    # lifts straight off: nothing of the jig in the column over the Zero's whole outline
    allz = FreeCAD.BoundBox()
    for s in zero.values(): allz.add(s.BoundBox)
    col = bx(allz.XMin, allz.XMax, allz.YMin, allz.YMax, -50, 200)
    check(col.common(jc).Volume < 1e-3, "lifts straight off: no jig over the Zero's outline")
    plate = bx(PLATE[0], PLATE[1], PLATE[0], PLATE[1], -12.4, 0)
    check(plate.common(jc).Volume < 1e-3, "nothing in the plate")
    for nm, face_x in (("front", None), ("left", None)):
        pass
    gap_f = jc.distToShape(bx(PLATE[0] + 40, PLATE[0] + 100, PLATE[0], PLATE[0] + 1, -LIP_D, -0.5))[0]
    gap_l = jc.distToShape(bx(PLATE[0], PLATE[0] + 1, PLATE[0] + 40, PLATE[0] + 100, -LIP_D, -0.5))[0]
    check(gap_f < 1e-6 and gap_l < 1e-6, f"both lips on the plate's edges (gaps {gap_f:.4f}, {gap_l:.4f})")
    check(not info.get("failed") and not left_e, f"chamfers: {info['bottom']} first-layer + {info['top']} top edges, "
                                                 f"{len(info['reduced'])} reduced, missed {left_e}")
    os.makedirs(OUT, exist_ok=True)
    jc.exportStep(os.path.join(OUT, "mellow-centre-jig.step"))
    up = jc.copy(); up.rotate(V(0, 0, 0), V(1, 0, 0), 180); up.translate(V(0, 0, -up.BoundBox.ZMin))   # print pose
    up.translate(V(-up.BoundBox.XMin, -up.BoundBox.YMin, 0))
    MeshPart.meshFromShape(Shape=up, LinearDeflection=0.01, AngularDeflection=0.1).write(os.path.join(OUT, "mellow-centre-jig.stl"))
    res.update(box=[round(v, 2) for v in (jb.XMin, jb.XMax, jb.YMin, jb.YMax, jb.ZMin, jb.ZMax)],
               pocket=[round(v, 2) for v in (px0, px1, py0, py1)], volume=round(jc.Volume, 1))
    json.dump(res, open(os.path.join(OUT, "mellow-centre-jig.json"), "w"), indent=1)
    pv = os.environ.get("JIG_PREVIEW")                    # review images: platform/render/render_parts.py
    if pv:
        os.makedirs(pv, exist_ok=True); idx = []
        roles = {"body": "brushed_aluminium", "probe": "brushed_steel", "switch": "black_plastic", "carrier": "printed"}
        items = [("jig", jc, "accent"), ("plate (PEI, 355)", plate, "Default")]
        items += [(k, s_, roles.get(k, "brushed_steel")) for k, s_ in zero.items()]
        for i, (lab, s_, role) in enumerate(items):
            fn = f"{i:02d}-{lab.split()[0]}.stl"
            MeshPart.meshFromShape(Shape=s_, LinearDeflection=0.05, AngularDeflection=0.2).write(os.path.join(pv, fn))
            idx.append(dict(file=fn, label=lab, role=role))
        json.dump(idx, open(os.path.join(pv, "parts.json"), "w"))
    fails = [c for c in res["checks"] if c[0] == "FAIL"]
    print(f"mellow_centre_jig: {len(fails)} problems"); return 1 if fails else 0


try:
    rc = main()
except Exception:
    import traceback; traceback.print_exc(); rc = 2
print("exit", rc)
