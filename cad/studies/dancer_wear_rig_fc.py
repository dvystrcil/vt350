# vt350#312: a hand-cycled test rig for the dancer's axle wear (owner 2026-11-27: the axle is a dowel that slides up
# and down its slots, "it will cause flat spots"; we test it first: "the physical test will need to be by hand").
# Headless, builds from the lite-81 pass's own functions (no model file), never touches a model:
#
#   VT350_REPO=$PWD $APP freecadcmd $PWD/cad/studies/dancer_wear_rig_fc.py
#
# Out: STLs ready to slice in $VT350_RIG_OUT (default ~/Documents/VT350/prints/dancer-wear-rig/, not in git), each in
# its print orientation, + parts.json for platform/render/render_parts.py; cad/data/dancer_wear_rig.json (the
# numbers) and cad/data/logs/dancer_wear_rig.log. The procedure and the results log: notes/dancer-wear-test.md.
#
# The rig is a piece of the real stack, so the dowel slides on the surfaces it will slide on in the printer:
#   - stack_body() for T0 and T1's stack (its three plates and the post: the same plates, axle grooves, slot width,
#     windows and rungs), cut out of the middle section (Z 155..358, the windows' tops peaked at 45 degrees as the real stack's), printed standing as the real sections are; the
#     slots shortened to the travel the rig can give. The test wheel runs in the first channel (an outer plate on one
#     side, the shared plate on the other, as T0's); the second channel can take a second wheel later (another
#     material, another dowel);
#   - a base flange under it (4 thick, 4 holes for wood screws or a clamp to the bench);
#   - the fixed leg's anchor: a 4.2 teardrop hole through the plates' rung at Z 350, above the wheel's highest sweep: an M4
#     screw (or any 4 mm pin) through it, the cord tied round it between the plates. The grooves run out of the top
#     (as the real middle section's, owner 2026-11-27): the wheel drops in with the pin out, and the pin then stops
#     it riding up out of them;
#   - the wheel: the real two halves (sheave_halves(), print-chamfered), its 625 and dowel. Halves + 625 + dowel are
#     ~42 g, the 0.4 N the dancer study picked (W_PICK): no extra weight is needed.
# The cord (any 5 mm cord, or a spare length of the bundle) is tied at the anchor, runs down between the plates, under
# the wheel in its groove, and up the other side, where the owner pulls it up and lets it down by hand.
import json, math, os, sys, traceback

REPO = os.environ.get("VT350_REPO", os.getcwd())
OUT = os.environ.get("VT350_RIG_OUT", os.path.expanduser("~/Documents/VT350/prints/dancer-wear-rig"))
LOG = os.path.join(REPO, "cad/data/logs/dancer_wear_rig.log")
_log = open(LOG, "w")                              # freecadcmd loses print() under os._exit (LESSONS.md)


def log(*a):
    _log.write(" ".join(str(x) for x in a) + "\n"); _log.flush()


CUT = (155.0, 358.0)            # the piece of the stack (real Z): the middle section's bottom, to the rung 342..358's top
BASE_T, BASE_Y = 4.0, 35.0      # the base flange: thickness; half its depth in Y
ANCHOR_Z, ANCHOR_R = 350.0, 2.1  # the fixed leg's pin: in the rung 342..358; an M4 (or 4 mm pin) through it
CLEAR = 2.0                     # the wheel's sweep clear of the base and the pin


def main():
    os.environ["LITE81_AS_LIB"] = "1"
    sys.path.insert(0, os.path.join(REPO, "cad", "passes"))
    import FreeCAD, Part
    import lite81_arms_dancers as L
    import printchamfer
    V = FreeCAD.Vector
    os.makedirs(OUT, exist_ok=True)
    problems = []

    def check(ok, what):
        log(("ok  " if ok else "FAIL"), what)
        if not ok: problems.append(what)

    cx, y0 = -324.2, 0.0                           # T0's stack X (its post side), the sheave's plane at Y 0
    R, RP = L.SHEAVE_R, L.DANCER["RP"]
    ycs = [y0 - L.PITCH / 2, y0 + L.PITCH / 2, y0 + 3 * L.PITCH / 2]
    # the axle's travel: the wheel's bottom clear of the base, its top clear of the anchor pin
    axle = (CUT[0] + BASE_T + R + CLEAR, ANCHOR_Z - ANCHOR_R - R - CLEAR)
    slot = (axle[0] - L.SLOT_W / 2 - 1.0, CUT[1])  # open at the top, as the real stack's middle section: the wheel
                                                   # drops in with the pin out; the pin then stops it riding out
    body, rods, px = L.stack_body(cx, ycs, slot)
    piece = body.common(Part.makeBox(4000, 4000, CUT[1] - CUT[0], V(-2000, -2000, CUT[0]))).removeSplitter()
    bb = piece.BoundBox
    x0, x1 = min(bb.XMin, px - L.POST_W) - 6.0, cx + RP + 10.0
    base = Part.makeBox(x1 - x0, 2 * BASE_Y, BASE_T, V(x0, y0 + L.PITCH / 2 - BASE_Y, CUT[0]))
    for hx in (x0 + 7.0, x1 - 7.0):
        for hy in (y0 + L.PITCH / 2 - BASE_Y + 7.0, y0 + L.PITCH / 2 + BASE_Y - 7.0):
            base = base.cut(Part.makeCylinder(2.75, BASE_T + 2, V(hx, hy, CUT[0] - 1), V(0, 0, 1)))
    rig = piece.fuse(base).removeSplitter()
    # the pin's hole: a teardrop, its point up at 45 degrees, so it prints standing with no support (owner 2026-11-27)
    pin = Part.makeCylinder(ANCHOR_R, 200.0, V(cx - RP, y0 - 100.0, ANCHOR_Z), V(0, 1, 0))
    k = ANCHOR_R / math.sqrt(2)
    tip = Part.Face(Part.makePolygon([V(cx - RP - k, y0 - 100.0, ANCHOR_Z + k), V(cx - RP + k, y0 - 100.0, ANCHOR_Z + k),
                                      V(cx - RP, y0 - 100.0, ANCHOR_Z + ANCHOR_R * math.sqrt(2)),
                                      V(cx - RP - k, y0 - 100.0, ANCHOR_Z + k)])).extrude(V(0, 200.0, 0))
    rig = rig.cut(pin.fuse(tip)).removeSplitter()
    # the leg's path, from the pin down between the plates to the wheel's side at its lowest: nothing in the way
    leg = Part.makeCylinder(2.55, ANCHOR_Z - ANCHOR_R - axle[0], V(cx - RP, y0, axle[0]), V(0, 0, 1))
    check(rig.common(leg).Volume < 0.01, f"the fixed leg's path (X {cx - RP:.1f}, Z {axle[0]:.1f}..{ANCHOR_Z:g}) is clear "
          f"between the plates ({rig.common(leg).Volume:.2f} mm3 in the way)")
    check(rig.isValid() and len(rig.Solids) == 1, f"the rig is one valid solid ({len(rig.Solids)})")
    # the wheel at both ends of its travel, against the rig: only the axle's ends in their grooves
    a, b = L.sheave_halves(cx, y0, 0.0)
    for zc in axle:
        hit = rig.common(L.bearing(cx, y0, zc)).Volume
        for s in (a, b):                           # the halves are built at Z 0: move them up to this axle height
            s = s.copy(); s.translate(V(0, 0, zc)); hit += rig.common(s).Volume
        ends = L.axle(cx, y0, zc)
        check(hit < 0.01, f"the wheel at axle Z {zc:.1f} clear of the rig ({hit:.2f} mm3)")
        check(rig.common(ends).Volume < 0.01, f"the dowel at Z {zc:.1f} clear in its grooves")
    # the wheel can't ride out of the open grooves: with the pin in, its rim meets the pin before the dowel leaves them
    stop = ANCHOR_Z - ANCHOR_R - math.sqrt(max(R ** 2 - RP ** 2, 0.0))   # axle Z where the rim reaches the pin
    check(stop + L.BEARING[1] < CUT[1] - 2.0, f"the pin stops the wheel at axle Z {stop:.1f}, the dowel still "
          f"{CUT[1] - stop - L.BEARING[1]:.1f} below the grooves' open top")
    # the grooves' open mouths at the top stay sharp: the web between two grooves is 0.8, too thin for a chamfer
    mouth = lambda e: e.BoundBox.ZMin > CUT[1] - 0.01 and abs(e.BoundBox.Center.x - cx) <= L.SLOT_W / 2 + 0.01
    rig, info = printchamfer.chamfer(rig, V(0, 0, 1), leave=mouth, **L.CHAMFER)
    check(not info.get("failed"), f"the rig print-chamfered: {info['bottom']} bed, {info['top']} top, failed {info.get('failed')}")
    dims = rig.BoundBox
    check(max(dims.XLength, dims.YLength) <= L.PRINT_XY and dims.ZLength <= L.PRINT_Z,
          f"the rig prints standing: {dims.XLength:.0f} x {dims.YLength:.0f} x {dims.ZLength:.0f} tall")
    # weight: the wheel's printed halves at ~1.3 g/cm3 (PET-GF / ASA-ish) + the 625 (~4.4 g) + the dowel (~1.8 g)
    grams = (a.Volume + b.Volume) / 1000 * 1.3 + 4.4 + math.pi * 2.5 ** 2 * L.AXLE_L * 7.85e-3
    check(abs(grams * 9.81e-3 - L.W_PICK) < 0.15, f"the wheel weighs ~{grams:.0f} g = {grams * 9.81e-3:.2f} N "
          f"(the dancer study's pick {L.W_PICK} N): no extra weight")
    # export, each in its print orientation, set on Z 0
    def place(s, rot=None):
        s = s.copy()
        if rot: s.rotate(V(0, 0, 0), V(1, 0, 0), rot)
        s.translate(V(-s.BoundBox.Center.x, -s.BoundBox.Center.y, -s.BoundBox.ZMin)); return s
    files = [("rig.stl", place(rig), "Rig: a piece of T0's stack + base (print standing)", "printed"),
             ("half1.stl", place(a, 90), "Sheave half 1 (print plate face down)", "printed"),
             ("half2.stl", place(b, -90), "Sheave half 2 (print plate face down)", "accent")]
    for f, s, lab, role in files:
        s.exportStl(os.path.join(OUT, f)); log("wrote", os.path.join(OUT, f), f"({s.Volume / 1000:.1f} cm3)")
    json.dump([{"file": f, "label": lab, "role": r} for f, _, lab, r in files], open(os.path.join(OUT, "parts.json"), "w"))
    # the assembled rig at mid travel, for a render
    asm = os.path.join(OUT, "assembled"); os.makedirs(asm, exist_ok=True)
    zm = sum(axle) / 2
    shift = V(-cx, -y0, -CUT[0])
    items = [("rig", rig, "printed"), ("half1", a, "printed"), ("half2", b, "accent"),
             ("bearing", L.bearing(cx, y0, zm), "bearing"), ("dowel", L.axle(cx, y0, zm), "brushed_steel"),
             ("pin", Part.makeCylinder(2.0, 24.0, V(cx - RP, y0 - 12.0, ANCHOR_Z), V(0, 1, 0)), "hardware")]
    out = []
    for n, s, role in items:
        s = s.copy()
        if n.startswith("half"): s.translate(V(0, 0, zm))
        s.translate(shift); s.exportStl(os.path.join(asm, n + ".stl")); out.append({"file": n + ".stl", "label": n, "role": role})
    json.dump(out, open(os.path.join(asm, "parts.json"), "w"))
    data = {"cut_z": CUT, "axle_travel_z": [round(z, 1) for z in axle], "stroke": round(axle[1] - axle[0], 1),
            "slot_z": [round(z, 1) for z in slot], "slot_w": L.SLOT_W, "groove_d": L.GROOVE_D, "axle_l": L.AXLE_L,
            "anchor": [round(cx - RP, 1), ANCHOR_Z], "base": [round(x1 - x0, 1), 2 * BASE_Y, BASE_T],
            "rig_mm": [round(dims.XLength, 1), round(dims.YLength, 1), round(dims.ZLength, 1)],
            "wheel_g": round(grams, 1), "out": OUT, "problems": problems}
    json.dump(data, open(os.path.join(REPO, "cad/data/dancer_wear_rig.json"), "w"), indent=1)
    log(f"stroke {data['stroke']} mm (axle Z {data['axle_travel_z']}); rig {data['rig_mm']} mm")
    log("dancer wear rig:", "OK" if not problems else f"{len(problems)} PROBLEMS")


try:
    main()
except Exception:
    log(traceback.format_exc())
os._exit(0)
