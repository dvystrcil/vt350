# GUI pass: vt350-lite-57 -> vt350-lite-58   (headless = dry run, never saves)
# vt350#4 / #5. The clear sheet goes INTO the door frame's slots, on both doors (owner, 2026-11-16: "it looks like
# its stuck on the outs of the door and not in the V channel of the frame of the door"; both doors; edged with a
# rubber glazing strip). Until now (since #4/#19) each sheet was screwed flat on the frame's outside on a foam gasket.
#  - Each door frame is four 2040s, 20 deep; the faces toward the opening carry one slot each, centred in that depth.
#    The sheet lies on that mid plane: the front door at Y -103, the e-box door at X 173 (lite-56).
#  - Sheet = the opening + INSERT into the slot on every side: front 479 x 669, e-box 539 x 669, 3 mm.
#  - Glazing strip: a rubber U on the sheet's edge, 6 across (fills the ~6.2 slot), its base 1 beyond the sheet's
#    edge, its lips back to the frame's face: INSERT + 1 = 5.5 mm into the slot. Modelled as 3 x 4 butted boxes.
#  - The old sheet and gasket objects are reshaped in place (Name, group, colour kept): the sheet keeps its label;
#    the gasket becomes the strip ("... gasket (rubber glazing strip, ...)", so the render's rubber rule still finds it).
# Checks (refuses to save on any): both doors' frames found and where expected; every new shape inside its frame's
# outline and depth; no sheet or strip overlaps any lite-57 part (the envelopes, and each other, excepted): this is
# what proves they sit in open slot, not in the profile; solids unchanged.
import FreeCAD, Part, os, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-57.FCStd", f"{MODELS}/vt350-lite-58.FCStd"
T, INSERT, LIP, BASE = 3.0, 4.5, 1.5, 1.0
# door: (sheet label prefix, gasket label prefix, depth axis, depth mid, width axis, opening along it, Z opening)
DOORS = {
    "front": ("Door window (3 mm", "Door window gasket", 1, -103.0, 0, (-480.0, -10.0), (-10.0, 650.0)),
    "e-box": ("E-box door window (", "E-box door window gasket", 0, 173.0, 1, (-50.0, 480.0), (-10.0, 650.0)),
}


def box3(lo, hi):
    return Part.makeBox(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], V(*lo))


def slab(dax, d0, d1, wax, w0, w1, z0, z1):
    lo, hi = [0, 0, 0], [0, 0, 0]
    lo[dax], hi[dax] = d0, d1; lo[wax], hi[wax] = w0, w1; lo[2], hi[2] = z0, z1
    return box3(lo, hi)


def ring(dax, d0, d1, wax, outer, inner):
    """A rectangular ring in the door plane, depth d0..d1: outer (w0, w1, z0, z1) minus inner, as 4 butted boxes."""
    (w0, w1, z0, z1), (i0, i1, j0, j1) = outer, inner
    return [slab(dax, d0, d1, wax, w0, w1, z0, j0), slab(dax, d0, d1, wax, w0, w1, j1, z1),
            slab(dax, d0, d1, wax, w0, i0, j0, j1), slab(dax, d0, d1, wax, i1, w1, j0, j1)]


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n0 = len(pr.leaves)
    made = []
    for door, (sl, gl, dax, mid, wax, (o0, o1), (z0, z1)) in DOORS.items():
        sheet = [o for o in pr.leaves if o.Label.startswith(sl)]
        gasket = [o for o in pr.leaves if o.Label.startswith(gl)]
        if not p.check(len(sheet) == 1 and len(gasket) == 1, f"{door} door: sheet {len(sheet)}, gasket {len(gasket)} (1 each)"):
            continue
        s_out = (o0 - INSERT, o1 + INSERT, z0 - INSERT, z1 + INSERT)
        e = INSERT + BASE
        st_out = (o0 - e, o1 + e, z0 - e, z1 + e)
        new_sheet = slab(dax, mid - T / 2, mid + T / 2, wax, *s_out)
        strip = (ring(dax, mid - T / 2 - LIP, mid - T / 2, wax, st_out, (o0, o1, z0, z1)) +      # lip, one side
                 ring(dax, mid + T / 2, mid + T / 2 + LIP, wax, st_out, (o0, o1, z0, z1)) +      # lip, other side
                 ring(dax, mid - T / 2, mid + T / 2, wax, st_out, s_out))                        # base, past the edge
        for o, s, lab in ((sheet[0], new_sheet, None),
                          (gasket[0], Part.makeCompound(strip),
                           f"{gl} (rubber glazing strip, U on the sheet's edge, in the frame slot; lite-58)")):
            par = linkgeo.gplace(o).multiply(o.Placement.inverse())
            loc = s.copy(); loc.Placement = par.inverse().multiply(loc.Placement)
            o.Shape = loc; o.Placement = loc.Placement
            if lab: o.Label = lab
            made.append((door, o))
        sheet[0].Label = sheet[0].Label.split(" [lite-58")[0] + f" [lite-58: in the frame slot, {s_out[1] - s_out[0]:.0f} x {s_out[3] - s_out[2]:.0f}]"
    doc.recompute(); pr.refresh()
    for door, o in made:
        _, _, dax, mid, wax, (o0, o1), (z0, z1) = DOORS[door]
        b = pr.boxes[o.Name]; lo = (b.XMin, b.YMin, b.ZMin); hi = (b.XMax, b.YMax, b.ZMax)
        ok = (lo[dax] >= mid - 10 - 1e-6 and hi[dax] <= mid + 10 + 1e-6 and lo[wax] >= o0 - 20 and hi[wax] <= o1 + 20
              and lo[2] >= z0 - 20 and hi[2] <= z1 + 20)
        p.check(ok, f"{door}: {o.Label[:50]}: X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} Z {b.ZMin:.1f}..{b.ZMax:.1f}")
    excl = {o.Name for o in pr.leaves if "envelope" in o.Label} | {o.Name for _, o in made}
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for _, o in made], pr,
                 lambda r: f"no sheet or strip overlaps a lite-57 part (so each sits in open slot): {len(r.hits)} {r.hits[:10]}",
                 exclude=excl)
    p.check(len(pr.leaves) == n0, f"lite-58 solids: {len(pr.leaves)} (= lite-57 {n0})")
    p.dump({"insert": INSERT, "sheet_t": T, "lip": LIP, "base": BASE, "doors": {k: [v[3]] for k, v in DOORS.items()}})
    return p.finish([(doc, DST)])


litelib.Pass("lite58_door_glazing").run(main)
