# GUI pass: vt350-lite-38 -> vt350-lite-39   (headless = dry run, never saves)
# vt350#19 (user, 2026-11-14, on lite-38's render): "I see a problem with the obico camera placement. the toolheads are
# interfering with the view. can we install it on the right side?" Earlier (same day): "the camera has to be mounted to
# the frame".
# THE CAMERA moves from the top front centre (lite-16) to the REAR-RIGHT corner of the chamber, by the rear-right 4040
# upright (lens at X -50, Y 440, Z 620: just inboard of the right LED channel), aimed to frame the plate at both ends of the bed's travel. A probe (rays from the lens to a 7 x 7
# grid on the magnet sheet at the top of travel and at the floor stop, the bed's own solids moved with it; every
# other solid as a mesh) ranked 20 spots on the right side. Worst-height plate points seen, of 49:
#   top front centre (now) 23 | rear-right corner Z 620: 40 (47 at the bottom; refined to X -50 Y 440: 41) | right wall mid Y 120 Z 620: 40
#   (but no frame to mount on mid-wall) | right wall Y 240 Z 620: 31 | the front half of the right wall: 0 (the
#   parked heads' MadMax carriage fills the view).
# The 4 camera solids (housing front + back, board, lens) move rigidly: new pose * old pose^-1, the old pose read from
# the lens's placement (lite-16 built them as lens-at-origin, looking +Z, no roll). The render's obico view follows,
# since export_meshes.py reads it from the lens. The bracket to the upright is not modelled.
# Also: the Crossbow (each head's CNC aluminium Crossbow) renders brushed aluminium (colours.json, user 2026-11-14).
# Checks (refuses to save on any): the lens lands on the chosen pose, looking along the chosen direction, no roll;
# the 4 solids keep their shapes (volume) and moved as one; they hit nothing; worst-height plate points seen
# >= 40 of 49 and more than the old spot gives (measured here, same method); the housing is within reach of the
# upright for a bracket; roles; solid count unchanged.
import FreeCAD, Part, MeshPart, os, sys, math
sys.path.insert(0, os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad"))
import litelib
from litelib import is_leaf, MODELS, BED_FLOOR_DZ, BED_Z
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path.insert(0, f"{REPO}/platform/render")
import colours
SRC, DST = f"{MODELS}/vt350-lite-38.FCStd", f"{MODELS}/vt350-lite-39.FCStd"
V = FreeCAD.Vector
CAM = ("Camera housing front", "Camera housing back", "Nocturne USB camera board", "Nocturne lens")
LENS = "Nocturne lens"
NEW_C, NEW_AIM = V(-50.0, 440.0, 620.0), V(-302.0, 28.0, 30.0)   # a finer probe round the corner: the coarse pick
# (-30, 455, 620) puts the housing into the right LED channel (Z 642..650, X -26..-10, to Y 470); lowered to 595 the
# belts block it (33/49). Moving 20 mm inboard and 15 back keeps Z 620 and clears the channel: 41 top / 46 bottom.
UPRIGHT = "4040"                         # the rear-right upright (X -10..30, Y 480..520)
STACK = ("LDO 350 build plate", "Magnetic sheet", "Heater pad")
TOP_DZ = 109.6                           # the bed's top of travel from the model pose (lite-16: 380.6 vs 271)
FOV, AR, N = 96.0, 16 / 9, 7
MIN_SEEN = 40
TOL = 1e-3


def rot_to(c, t):
    z = t - c; z.normalize(); x = z.cross(V(0, 0, 1)); x.normalize(); y = z.cross(x)
    return FreeCAD.Rotation(x, y, z, "ZXY")


def main(p):
    pr = p.open(SRC); doc = pr.doc
    obj = lambda lab: next(o for o in doc.Objects if o.Label == lab)
    cmap = colours.load(f"{REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    cam = [o for o in pr.leaves if o.Label.startswith(CAM)]
    p.check(len(cam) == 4, f"the 4 camera solids: {[o.Label for o in cam]}")
    lens = obj(LENS)
    old = lens.getGlobalPlacement()
    d_old = old.Rotation.multVec(V(0, 0, 1))
    x_old = old.Rotation.multVec(V(1, 0, 0))
    p.check(abs(x_old.z) < 1e-6, f"the lens's old pose has no roll (local X horizontal: z {x_old.z:+.2e}); at "
            f"({old.Base.x:.1f}, {old.Base.y:.1f}, {old.Base.z:.1f}) looking ({d_old.x:+.3f}, {d_old.y:+.3f}, {d_old.z:+.3f})")
    new = FreeCAD.Placement(NEW_C, rot_to(NEW_C, NEW_AIM))
    T = new.multiply(old.inverse())
    vol0 = {o.Name: pr.shapes[o.Name].Volume for o in cam}
    com0 = {o.Name: pr.shapes[o.Name].CenterOfMass for o in cam}
    for o in cam:
        g = T.multiply(o.getGlobalPlacement())
        par = o.getParentGeoFeatureGroup()
        o.Placement = par.getGlobalPlacement().inverse().multiply(g) if par else g
    doc.recompute(); pr.refresh()
    now = lens.getGlobalPlacement(); d_new = now.Rotation.multVec(V(0, 0, 1)); want = NEW_AIM - NEW_C; want.normalize()
    p.check((now.Base - NEW_C).Length < TOL and (d_new - want).Length < 1e-6 and abs(now.Rotation.multVec(V(1, 0, 0)).z) < 1e-6,
            f"the lens is at ({now.Base.x:.2f}, {now.Base.y:.2f}, {now.Base.z:.2f}) looking ({d_new.x:+.3f}, {d_new.y:+.3f}, "
            f"{d_new.z:+.3f}), no roll")
    for o in cam:
        s = pr.shapes[o.Name]; moved = T.multVec(com0[o.Name])
        p.check(abs(s.Volume - vol0[o.Name]) < TOL and (s.CenterOfMass - moved).Length < 0.01,
                f"{o.Label}: same solid ({s.Volume:.1f} mm3), moved with the lens (centre off by {(s.CenterOfMass - moved).Length:.4f})")
    names = {o.Name for o in cam}
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in cam], pr, lambda r: f"the camera vs everything: {r.hits[:6]}", exclude=names)
    up = obj(UPRIGHT); ub = pr.shapes[up.Name].BoundBox
    p.check(abs(ub.XMin + 10) < 0.5 and abs(ub.YMin - 480) < 0.5, f"{UPRIGHT} is the rear-right upright: X {ub.XMin:.1f}..{ub.XMax:.1f}, Y {ub.YMin:.1f}..{ub.YMax:.1f}")
    house = Part.Compound([pr.shapes[o.Name] for o in cam])
    gap = house.distToShape(pr.shapes[up.Name])[0]
    p.check(gap < 40.0, f"the housing is {gap:.1f} mm from the upright: a bracket's reach (not modelled)")
    # ---- what the camera sees (the probe's method, measured on the saved geometry)
    stack = [o for o in pr.leaves if o.Label.startswith(STACK)]
    sb = pr.shapes[stack[0].Name].BoundBox
    for o in stack[1:]: sb.add(pr.shapes[o.Name].BoundBox)
    pl = next(o for o in pr.leaves if o.Label.startswith(STACK[0])); pb = pr.shapes[pl.Name].BoundBox
    ZS = sb.ZMax; DZ = {"top": TOP_DZ, "bottom": BED_FLOOR_DZ}
    bed = {o.Name for o in pr.leaves if BED_Z[0] <= pr.boxes[o.Name].ZMin <= BED_Z[1] and pr.boxes[o.Name].ZMax <= BED_Z[1]}
    skipn = names | {o.Name for o in stack} | {o.Name for o in pr.leaves if o.Label.startswith("Door window")}
    mesh = {o.Name: MeshPart.meshFromShape(Shape=pr.shapes[o.Name], LinearDeflection=1.0, AngularDeflection=0.5)
            for o in pr.leaves if o.Name not in skipn}
    boxes = {n: pr.shapes[n].BoundBox for n in mesh}
    grp = {o.Name: (o.getParentGeoFeatureGroup().Label if o.getParentGeoFeatureGroup() else o.Label) for o in pr.leaves}
    k = math.tan(math.radians(FOV / 2)) / math.hypot(AR, 1)
    def seen(c, r, dz):
        inv = r.inverted(); vis = inside = 0; by = {}
        for i in range(N):
            for j in range(N):
                q_ = V(pb.XMin + (pb.XMax - pb.XMin) * i / (N - 1), pb.YMin + (pb.YMax - pb.YMin) * j / (N - 1), ZS + dz + 0.05)
                q = inv.multVec(q_ - c)
                if q.z <= 0 or abs(q.x / q.z) > k * AR or abs(q.y / q.z) > k: continue
                inside += 1; d = q_ - c; L = d.Length; d.normalize(); hit = None
                for n, m in mesh.items():
                    s_ = dz if n in bed else 0.0
                    o2 = c - V(0, 0, s_)
                    if not boxes[n].intersect(FreeCAD.BoundBox(o2, q_ - V(0, 0, s_))): continue
                    h = m.nearestFacetOnRay((o2.x, o2.y, o2.z), (d.x, d.y, d.z))
                    if h and any((V(*hp) - o2).Length < L - 0.5 for hp in h.values()): hit = n; break
                if hit is None: vis += 1
                else: by[grp[hit]] = by.get(grp[hit], 0) + 1
        return inside, vis, by
    res = {}
    for tag, pose in (("old", old), ("new", now)):
        c = pose.Base + pose.Rotation.multVec(V(0, 0, 1)) * 0.5
        res[tag] = {h: seen(c, pose.Rotation, DZ[h]) for h in DZ}
        for h, (i, v, by) in res[tag].items():
            p.log(f"{tag} spot, bed at its {h} (sheet Z {ZS + DZ[h]:.0f}): {i}/{N * N} framed, {v} seen; blocked by "
                  f"{dict(sorted(by.items(), key=lambda kv: -kv[1])[:4])}")
    worst = {t: min(v for _, v, _ in res[t].values()) for t in res}
    p.check(worst["new"] >= MIN_SEEN and worst["new"] > worst["old"],
            f"plate points seen at the worst bed height: {worst['new']}/49 here, {worst['old']}/49 from the old spot")
    # ---- roles
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    xb = [o for o in pr.leaves if o.Label.startswith("Crossbow - ")]
    roles = {colours.role_of(cmap, o.Label, gpath(o), getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default') for o in xb}
    p.check(len(xb) == 20 and roles == {"brushed_aluminium"}, f"the Crossbow parts ({len(xb)}, 4 per head) -> {roles}")
    p.check(len(pr.leaves) == n_before, f"solids unchanged: {n_before} -> {len(pr.leaves)}")
    p.dump({"camera_lens_old": [round(c, 2) for c in old.Base], "camera_lens_new": [round(c, 2) for c in now.Base],
            "camera_dir_new": [round(c, 4) for c in d_new], "housing_to_upright_mm": round(gap, 1),
            "plate_points_seen_of_49": {t: {h: v for h, (_, v, _) in r.items()} for t, r in res.items()}})
    p.finish([(doc, DST)])


litelib.Pass("lite39_camera_right").run(main)
