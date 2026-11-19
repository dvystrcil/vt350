# GUI pass: vt350-lite-70 -> vt350-lite-71   (headless = dry run, never saves)   vt350#3
# The cable channel gets real fixings, prints in segments, and the older parts we designed get chamfered.
# Owner, 2026-11-18: "how is that cable channel attached?" (it wasn't: lite-40 only named the screws, and its post arms
# stopped edge-on at the channel's front wall, carrying nothing); "not tape"; segments for a 220 x 220 bed; and the
# chamfer retrofit "in their own pass", only for parts we designed ("the models that DW-Tas has created are production
# models and should not need alteration").
#
#  - POSTS (4, rebuilt): a 14 wide column on the roof panel's rear edge, an arm under the channel's floor (24 wide, to
#    the channel's back edge) that carries it, and a lip that hangs down the rear top 4040's back face (owner,
#    2026-11-19: "I expected there to be a lip hanging down so I can anchor it to the 4040"). Each post: 1 x M5x10 SHCS
#    through the 6 mm lip into a drop-in T-nut in the 4040's upper back slot (Z 680); the roof panel isn't drilled.
#    Printed upside down, the arm's top face on the bed (owner: "the top surface laying on the print bed"): every wall
#    then rises straight from it, no overhangs. The channel screws down into the arm: M3x6 countersunk (ISO 10642) through the floor, from inside the
#    channel before the cover goes on, into a heat-set insert in the arm; two (one per segment) where a joint sits on
#    the post, one elsewhere. The countersinks are the one bore the chamfer rule allows: the head sits flush under the
#    lowest lane.
#  - ARMS (2, rebuilt) on the drop: lite-40's ran through the e-box rear panel (X 30..146, Y 520..523). Now a foot on the
#    rear-right upright's back face (X -6..29.8, Y 520..) with 1 x M5x16 into a T-nut in its slot at X 20, bridging
#    over the e-box rear panel (Y 523.4..) to the channel's front wall, M3x6 countersunk through the front wall from
#    inside into inserts in the bridge's face. Moved to the drop's joint and below it (ARM_Z).
#  - SEGMENTS: the channel body and cover split at the joints (0.2 mm gap) into 5 each, every piece within the bed
#    (BED from cad/data/print-profile.json, 5 mm margin) as printed (front wall / cover face down), every joint over a
#    post or arm, every piece held by >= 2 screws.
#  - COVER CLIPS: on the straight runs, tabs from the cover over the walls' outer faces with a barb into a 0.8 mm
#    groove in the wall (0.2 mm clearance all round, 0.1 at the barb); away from the posts' arms, joints and windows.
#  - CHAMFERS (printchamfer, cad/data/print-profile.json): every new piece; and the retrofit of the older parts we
#    designed: the nozzle-offset probe bracket, the 3 e-box grille panels, the grille badge (the hex meshes are left:
#    2 mm bars, too narrow for the first-layer size anyway). Grille parts print outside face down. The probe bracket
#    (two parallel plates on a web) had no side that prints without supports: its section is carried down to its lowest
#    edge so all of it stands on one flat side (owner, 2026-11-19), its holes kept open through the new material.
# Hardware (listed, not modelled): see p.dump "fasteners".
# Checks (refuses to save on any): the parts found, ours only (label "vt350, GPL-3.0-or-later" or "printed, vt350"
# for every part changed); M5s on the slots; segments in the bed, one valid solid each, joint sections whole (no window
# cut by a joint), >= 2 screws each, joints supported, spans <= 200; posts clear of cables and clamps by >= 1 mm;
# clips: >= 2 per cover piece, grooves in solid wall; chamfers: none missed (printchamfer.unchamfered); retrofit
# parts lose only chamfer material (box unchanged, < 5 % volume); the posts print upside down with no overhang;
# no overlap: posts, arms, cover pieces vs the printer and the cables; body pieces vs the printer (they only lose
# material, so vs the cables nothing new); pieces vs each other; the side pack's stand-in envelope counted only up to
# the e-box rear panel's outer face (Y 523; it's a box that runs past the panel); roles as before; solids +8.
import FreeCAD, Part, os, re, sys, math, json
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "cad/scripts"), os.path.join(_REPO, "platform/render")]
import litelib, linkgeo, colours, printchamfer
from litelib import MODELS

V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-70.FCStd", f"{MODELS}/vt350-lite-71.FCStd"
TOL = 1e-3
PROFILE = os.path.join(_REPO, "cad/data/print-profile.json")
CHAMFER = printchamfer.profile(PROFILE)
BED = json.load(open(PROFILE))["bed_mm"]
BED_MARGIN = 5.0
OURS = ("vt350, GPL-3.0-or-later", "printed, vt350")

PANEL_TOP = 693.0                 # roof panel + paint top (lite-70)
SLOT_Y, BAR_TOP = 510.0, 690.0    # rear top 4040 (X -520..140, Y 480..520, Z 650..690): its rear top slot
UPR_FACE_Y, UPR_SLOT_X = 520.0, 20.0     # the rear-right 4040 upright (X -10..30): back face, slot
EBOX_REAR_Y1 = 523.0              # e-box rear panel + paint outer face (X 30..146)
M3, M3_INS, M5, M5_CB = 1.7, 2.0, 2.75, 4.75
INS_DEPTH, CLAMP_T = 6.5, 8.0
BAR_BACK_Y, LIP_Y1, LIP_Z0, BACK_SLOT_Z = 520.0, 526.0, 668.0, 680.0   # the post's lip on the 4040's back face; its upper back slot
CSK_R = 3.15                      # M3 countersunk head radius (Ø6.3), 90 deg
COL_W, COL_Y0, COL_Y1 = 14.0, 503.0, 517.0
ARM_W, ARM_T = 24.0, 12.0
JOINT_DX = 6.0                    # a joint's two screws, one each side
GAP = 0.2                         # between neighbouring segments
X_START, X_A, Z_END = -470.0, 40.0, 380.0
POST_TARGETS = [-457.0, -380.0, -186.0, 10.0]       # the first holds the end; the other three carry joints (the floor whole there)
                                                      # (lite-70's U is whole only at X -468..-386, -312..-308, -256..-216, -168..-138, -88..-50, 0..38)
JOINT_Z = 560.0                   # the drop's joint, on arm 2
ARM_Z = [440.0, JOINT_Z]
ARM_H = {440.0: 16.0, JOINT_Z: 24.0}
CLIP_W, CLIP_T, CLIP_GAP, BARB, GROOVE_D = 10.0, 1.2, 0.2, 0.7, 0.8
CLIP_PITCH, CLIP_END = 50.0, 12.0

CHAN = {"body": "Cable channel body, roof to side pack (printed, vt350, GPL-3.0-or-later)",
        "cover": "Cable channel cover, roof to side pack (printed, vt350, GPL-3.0-or-later)"}
POSTS = "Cable channel post {i} (printed, M5 to the rear 4040)"
ARMS = "Cable channel arm {i} (printed, M5 to the rear-right upright)"
SEG = "Cable channel {what} segment {k} of {n}, {where} (printed, vt350, GPL-3.0-or-later)"
PROBE_CUT, PROBE_Z0 = 251.0, 240.0      # the probe bracket's section through both plates and the web; its lowest edge (lite-70)
RETRO = ["Nozzle offset probe bracket", "E-box grille panel 1 of 3", "E-box grille panel 2 of 3", "E-box grille panel 3 of 3",
         "E-box grille badge"]
UP = {"body": V(0, 1, 0), "cover": V(0, -1, 0), "post": V(0, 0, -1), "arm": V(0, 0, 1)}   # post: upside down


def box(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def zcyl(x, y, z0, z1, r): return Part.makeCylinder(r, z1 - z0, V(x, y, z0))
def ycyl(x, z, y0, y1, r): return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def csk_down(x, y, ztop, r=M3, rh=CSK_R):
    """a countersunk M3 hole whose head sits flush in a face at Z ztop, the screw pointing -Z"""
    h = rh - r
    return zcyl(x, y, ztop - 20, ztop + 1, r).fuse(Part.makeCone(r, rh, h, V(x, y, ztop - h))).fuse(zcyl(x, y, ztop, ztop + 1, rh))


def csk_front(x, z, yface, r=M3, rh=CSK_R):
    """the same, head flush in a face at Y yface facing +Y (the front wall's inside), the screw pointing -Y"""
    h = rh - r
    return ycyl(x, z, yface - 20, yface + 1, r).fuse(Part.makeCone(r, rh, h, V(x, yface - h, z), V(0, 1, 0))).fuse(
        ycyl(x, z, yface, yface + 1, rh))


def gplace(o):
    par = o.getParentGeoFeatureGroup()
    return par.getGlobalPlacement() if par else FreeCAD.Placement()


def set_shape_keep_placement(o, g):
    P0 = FreeCAD.Placement(o.Placement)
    loc = g.copy(); loc.transformShape(gplace(o).multiply(P0).inverse().toMatrix(), True)
    loc.Placement = P0; o.Shape = loc


def bed_up(s, centre):
    """print on the largest flat face (ties: the one facing away from the printer's middle): up = minus its normal"""
    fl = [f for f in s.Faces if isinstance(f.Surface, Part.Plane)]
    amax = max(f.Area for f in fl)
    cands = [f for f in fl if f.Area > 0.99 * amax]
    def outward(f):
        n = FreeCAD.Vector(f.Surface.Axis)
        if f.Orientation == "Reversed": n = -n
        return n, (f.CenterOfMass - centre).dot(n)
    f = max(cands, key=lambda f: outward(f)[1])
    n = outward(f)[0]
    return V(-n.x, -n.y, -n.z), f.Area


def main(p):
    pr = p.open(SRC); doc = pr.doc
    by = {o.Label: o for o in doc.Objects}
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n_before = len(pr.leaves)
    def find(prefix):
        c = [o for o in pr.leaves if o.Label.startswith(prefix)]
        p.check(len(c) == 1, f"one part labelled {prefix!r} ({len(c)})"); return c[0] if len(c) == 1 else None
    old = {("chan", "body"): by.get(CHAN["body"]), ("chan", "cover"): by.get(CHAN["cover"])}
    for i in range(1, 5): old[("post", i)] = by.get(POSTS.format(i=i))
    for i in range(1, 3): old[("arm", i)] = by.get(ARMS.format(i=i))
    p.check(all(old.values()), f"the 8 channel parts to replace: missing {[k for k, v in old.items() if not v]}")
    retro = {lab: find(lab) for lab in RETRO}
    rp = [o for o in pr.leaves if o.Label == "Roof panel (3 mm)"]; pp = [o for o in pr.leaves if o.Label == "Roof panel (3 mm) paint, outside"]
    p.check(len(rp) == 1 and len(pp) == 1, f"the roof panel and its paint ({len(rp)}, {len(pp)})")
    if p.errs: return p.finish([])
    roof, paint = rp[0], pp[0]
    changed = list(old.values()) + list(retro.values())
    p.check(all(any(t in o.Label for t in OURS) or o.Label.startswith("Cable channel") for o in changed),
            f"only parts we designed are changed: {[o.Label for o in changed if not any(t in o.Label for t in OURS)][:4]}")
    p.check(all(o.TypeId == "Part::Feature" for o in list(retro.values()) + [roof, paint]),
            f"retrofit parts and the roof panel are plain Part::Features: {[(o.Label[:30], o.TypeId) for o in list(retro.values()) + [roof, paint] if o.TypeId != 'Part::Feature']}")
    names = {o.Name for o in old.values()}
    users = sorted({u.Label for o in old.values() for u in o.InList if u.Name not in names and u.TypeId != "App::DocumentObjectGroup"
                    and not u.TypeId.startswith("App::Part")})
    p.check(not users, f"nothing else uses the replaced parts: {users[:6]}")
    bars = [o for o in pr.leaves if o.Label.startswith("4040 (1)004 one piece")]
    upr = [o for o in pr.leaves if o.Label.startswith("4040 upright Z -10..650")]
    p.check(len(bars) == 1 and len(upr) == 1, f"the rear top 4040 and the rear-right upright ({len(bars)}, {len(upr)})")
    if p.errs: return p.finish([])
    bb_bar, bb_upr = pr.boxes[bars[0].Name], pr.boxes[upr[0].Name]
    p.check(abs(bb_bar.YMax - 520) < TOL and abs(bb_bar.YMin - 480) < TOL and abs(bb_bar.ZMax - BAR_TOP) < TOL,
            f"rear top 4040 at Y 480..520, top Z 690: the slot at Y {SLOT_Y} ({bb_bar.YMin:.1f}..{bb_bar.YMax:.1f}, {bb_bar.ZMax:.1f})")
    p.check(abs(bb_upr.YMax - UPR_FACE_Y) < TOL and abs(bb_upr.XMin + 10) < TOL and abs(bb_upr.XMax - 30) < TOL,
            f"rear-right upright X -10..30, back face Y 520: its slot at X {UPR_SLOT_X}")
    keep = {k: dict(group=next((g for g in o.InList if g.TypeId == "App::DocumentObjectGroup"), None) or o.getParentGeoFeatureGroup(),
                    label=o.Label, mat=getattr(o, "ShapeMaterial", None),
                    app=o.ViewObject.ShapeAppearance if FreeCAD.GuiUp else None) for k, o in old.items()}
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    role = {k: colours.role_of(cmap, o.Label, gpath(o), "Default") for k, o in old.items()}
    envs = [o for o in pr.leaves if o.Label.startswith("Ebox envelope")]
    p.check(len(envs) == 1, "the side pack's stand-in envelope")
    if p.errs: return p.finish([])
    env = envs[0]
    eb = pr.boxes[env.Name]
    env_real = pr.shapes[env.Name].common(box(eb.XMin - 1, eb.XMax + 1, eb.YMin - 1, EBOX_REAR_Y1, eb.ZMin - 1, eb.ZMax + 1))
    def env_vol(s): return s.common(env_real).Volume if s.BoundBox.intersect(env_real.BoundBox) else 0.0
    env_before = sum(env_vol(pr.shapes[o.Name]) for o in old.values())

    body0, cover0 = pr.shapes[old[("chan", "body")].Name], pr.shapes[old[("chan", "cover")].Name]
    bc_before = body0.common(cover0).Volume
    # ---------------- the channel's section, measured
    hz_part = body0.common(box(-1000, 0, 0, 1000, 0, 2000)).BoundBox
    zb, zt = hz_part.ZMin, hz_part.ZMax
    v_part = body0.common(box(0, 1000, 0, 1000, 0, 650)).BoundBox
    xv0, xv1 = v_part.XMin, v_part.XMax
    yf0, yin1 = body0.BoundBox.YMin, body0.BoundBox.YMax
    WALL = 2.0
    yin0, ymid = yf0 + WALL, (yf0 + WALL + yin1) / 2
    p.log(f"channel: horizontal run Z {zb:.2f}..{zt:.2f}, drop X {xv0:.2f}..{xv1:.2f}, front wall Y {yf0:.2f}..{yin0:.2f}, back edge Y {yin1:.2f}")
    p.check(abs(yin1 - cover0.BoundBox.YMin) < 0.01, f"the cover sits on the back edge (Y {cover0.BoundBox.YMin:.2f})")
    zc_top = (zb + zt) / 2 - 60.0                        # the drop's straight part ends where the corner (R 60) starts
    cables = [o for o in pr.leaves if o.Label.startswith("O2S USB cable slot")]
    clamps = [o for o in pr.leaves if o.Label.startswith("Roof exit clamp")]
    blockers = [pr.shapes[o.Name] for o in cables + clamps]

    # ---------------- posts
    def post_at(x, j=None):
        """column at x over the slot; the arm under the floor reaches to the joint at j (None: one screw at x)"""
        col = box(x - COL_W / 2, x + COL_W / 2, COL_Y0, LIP_Y1, PANEL_TOP, zb)
        lip = box(x - COL_W / 2, x + COL_W / 2, BAR_BACK_Y, LIP_Y1, LIP_Z0, PANEL_TOP)
        a0, a1 = (x - ARM_W / 2, x + ARM_W / 2) if j is None else (min(x - COL_W / 2, j - ARM_W / 2), max(x + COL_W / 2, j + ARM_W / 2))
        arm = box(a0, a1, COL_Y0, yin1, zb - ARM_T, zb)
        s = col.fuse(arm).fuse(lip).removeSplitter()
        s = s.cut(ycyl(x, BACK_SLOT_Z, BAR_BACK_Y - 1, LIP_Y1 + 1, M5))
        for sx in ((x,) if j is None else (j - JOINT_DX, j + JOINT_DX)):
            s = s.cut(zcyl(sx, ymid, zb - INS_DEPTH, zb + 1, M3_INS))
        return s
    def clear(ps):
        bb = ps.BoundBox; bb.enlarge(1.0)
        return not any(c.BoundBox.intersect(bb) and c.distToShape(ps)[0] < 1.0 for c in blockers)
    def sec_area(x):
        w = body0.slice(V(1, 0, 0), x)
        return sum(Part.Face(q).Area for q in w) if w else 0.0
    a_ref = max(sec_area(x) for x in (-465.0, -400.0, -200.0))
    free = []
    for x in range(int(X_START) + 15, int(X_A) - 5):
        if clear(post_at(float(x))): free.append(float(x))
    def runs(xs):
        out = []
        for x in xs:
            if out and x - out[-1][1] <= 1.0: out[-1][1] = x
            else: out.append([x, x])
        return [tuple(r) for r in out]
    def floor_vol(j):
        return body0.common(box(j - JOINT_DX - CSK_R - 1, j + JOINT_DX + CSK_R + 1, yin0, yin1, zb, zb + WALL)).Volume
    fl_full = floor_vol(-430.0)                            # where the U is whole (lite-70's chamfers included)
    def floor_ok(j):            # the floor whole round both of a joint's screws (a window opens only the front wall)
        return abs(floor_vol(j) - fl_full) < 0.01 * fl_full
    jfree = [x for x in free if floor_ok(x) and clear(post_at(x, x))]
    chosen = [min(free, key=lambda x: abs(x - POST_TARGETS[0])) if free else None]
    chosen += [min(jfree, key=lambda x: abs(x - t)) if jfree else None for t in POST_TARGETS[1:]]
    jx = chosen[1:]
    p.log(f"a post fits at X {runs(free)}; a joint post (floor whole round both screws) at X {runs(jfree)}")
    p.check(None not in chosen and len(set(chosen)) == 4, f"posts at X {chosen}, joints on posts 2-4 (targets {POST_TARGETS}) clear of cables and clamps by >= 1 mm")
    if p.errs: return p.finish([])
    sup = [X_START, chosen[0]] + jx + [X_A]
    gaps = [b - a for a, b in zip(sup, sup[1:])]
    p.check(max(gaps) <= 200.0 and jx == sorted(jx), f"spans between supports {[round(g) for g in gaps]} (<= 200)")
    if p.errs: return p.finish([])

    # ---------------- arms on the drop
    def arm_at(z, joint):
        h = ARM_H[z]
        foot = box(-6.0, 29.8, UPR_FACE_Y, yf0, z - h / 2, z + h / 2)
        bridge = box(29.0, xv0 + 16.0, EBOX_REAR_Y1 + 0.4, yf0, z - h / 2, z + h / 2)
        s = foot.fuse(bridge).removeSplitter()
        s = s.cut(ycyl(UPR_SLOT_X, z, UPR_FACE_Y - 1, yf0 + 1, M5)).cut(ycyl(UPR_SLOT_X, z, UPR_FACE_Y + CLAMP_T, yf0 + 1, M5_CB))
        for dz in ((-JOINT_DX, JOINT_DX) if joint else (0.0,)):
            s = s.cut(ycyl(xv0 + 8.0, z + dz, yf0 - INS_DEPTH, yf0 + 1, M3_INS))
        return s
    arms = {z: arm_at(z, z == JOINT_Z) for z in ARM_Z}

    # ---------------- the body: screws, then segments
    body = body0
    screws = []                                          # (where, point on the channel)
    for sx in [chosen[0]] + [j + d for j in jx for d in (-JOINT_DX, JOINT_DX)]:
        body = body.cut(csk_down(sx, ymid, zb + WALL)); screws.append(V(sx, ymid, zb + WALL))
    for z in ARM_Z:
        for dz in ((-JOINT_DX, JOINT_DX) if z == JOINT_Z else (0.0,)):
            body = body.cut(csk_front(xv0 + 8.0, z + dz, yin0)); screws.append(V(xv0 + 8.0, yin0, z + dz))
    p.check(body.isValid() and len(body.Solids) == 1, f"body with {len(screws)} countersunk M3 holes: one valid solid")
    # joint sections whole: the U's section at a joint has the area of a plain one
    for x in jx:
        p.check(floor_ok(x), f"joint X {x}: the floor whole round both screws; the section there {sec_area(x):.1f} mm2 (plain {a_ref:.1f}; a cable window opens the front wall)")
    zs = body0.slice(V(0, 0, 1), JOINT_Z)
    a_z = sum(Part.Face(w).Area for w in zs)
    a_zr = sum(Part.Face(w).Area for w in body0.slice(V(0, 0, 1), 500.0))
    p.check(abs(a_z - a_zr) < 0.5, f"joint Z {JOINT_Z}: the U is whole there ({a_z:.1f} mm2, plain {a_zr:.1f})")
    g = GAP / 2
    regions = [("roof run, left end", box(-2000, jx[0] - g, -2000, 2000, -2000, 2000)),
               ("roof run", box(jx[0] + g, jx[1] - g, -2000, 2000, -2000, 2000)),
               ("roof run, right", box(jx[1] + g, jx[2] - g, -2000, 2000, -2000, 2000)),
               ("the corner", box(jx[2] + g, 2000, -2000, 2000, JOINT_Z + g, 2000)),
               ("the drop", box(jx[2] + g, 2000, -2000, 2000, -2000, JOINT_Z - g))]
    def split(s, what):
        out = []
        for k, (where, r) in enumerate(regions, 1):
            q = s.common(r).removeSplitter()
            ok = q.isValid() and len(q.Solids) == 1
            bbq = q.BoundBox
            fx, fz = bbq.XLength, bbq.ZLength
            fits = max(fx, fz) <= max(BED) - BED_MARGIN and min(fx, fz) <= min(BED) - BED_MARGIN
            p.check(ok and fits, f"{what} segment {k} ({where}): one valid solid ({len(q.Solids)}), printed footprint "
                    f"{fx:.1f} x {fz:.1f} (bed {BED[0]} x {BED[1]}, margin {BED_MARGIN})")
            out.append((where, q))
        return out

    # ---------------- the cover: clips on the straight runs, then segments
    cover = cover0
    ybk = yin1 + 2.0                                    # the cover's outer face
    clip_n = 0
    arm_spans = [(min(x - COL_W / 2, (j if j is not None else x) - ARM_W / 2), max(x + COL_W / 2, (j if j is not None else x) + ARM_W / 2))
                 for x, j in zip(chosen, [None] + jx)]
    def clip_ok_x(c, side):
        if side < 0 and any(a - CLIP_W / 2 - 4 < c < b + CLIP_W / 2 + 4 for a, b in arm_spans): return False   # under the floor: the arms
        if any(abs(c - x) < CLIP_W / 2 + CLIP_END for x in jx): return False
        return X_START + CLIP_END <= c <= X_A - CLIP_W - 5
    def clip_ok_z(c):
        if any(abs(c - z) < ARM_H[z] / 2 + CLIP_W / 2 + 2 for z in ARM_Z): return False
        if abs(c - JOINT_Z) < CLIP_W / 2 + CLIP_END: return False
        return Z_END + CLIP_END <= c <= zc_top - CLIP_W - 25   # the whole tab on the straight, well short of the corner (lite-71 dry run: one at Z 680 cut the inner wall)
    yb0, yb1 = yin1 - 8.0, yin1 - 6.4                  # the groove / barb, 6.4..8 mm in from the back edge
    for side in (+1, -1):                                # the roof run: top wall (+Z) and floor (-Z)
        zw = zt if side > 0 else zb
        c = X_START + CLIP_END + CLIP_W / 2
        while c <= X_A:
            if clip_ok_x(c, side):
                groove = box(c - CLIP_W / 2 - CLIP_GAP, c + CLIP_W / 2 + CLIP_GAP, yb0 - 0.1, yb1 + 0.1,
                             *(sorted((zw, zw - side * GROOVE_D))))
                if abs(body.common(groove).Volume - groove.Volume) < 0.01:        # solid wall there (no window)
                    zo = zw + side * CLIP_GAP
                    tab = box(c - CLIP_W / 2, c + CLIP_W / 2, yb0, ybk, *sorted((zo, zo + side * CLIP_T)))
                    link = box(c - CLIP_W / 2, c + CLIP_W / 2, yin1 + CLIP_GAP, ybk, *sorted((zw, zo + side * CLIP_T)))
                    barb = box(c - CLIP_W / 2, c + CLIP_W / 2, yb0, yb1, *sorted((zw - side * (GROOVE_D - 0.1), zo)))
                    body = body.cut(groove); cover = cover.fuse(tab).fuse(link).fuse(barb); clip_n += 1
                    c += CLIP_PITCH; continue
            c += 2.0
    for side in (+1, -1):                                # the drop: its +X and -X walls
        xw = xv1 if side > 0 else xv0
        c = Z_END + CLIP_END + CLIP_W / 2
        while c <= zc_top:
            if clip_ok_z(c):
                groove = box(*sorted((xw, xw - side * GROOVE_D)), yb0 - 0.1, yb1 + 0.1, c - CLIP_W / 2 - CLIP_GAP, c + CLIP_W / 2 + CLIP_GAP)
                if abs(body.common(groove).Volume - groove.Volume) < 0.01:
                    xo = xw + side * CLIP_GAP
                    tab = box(*sorted((xo, xo + side * CLIP_T)), yb0, ybk, c - CLIP_W / 2, c + CLIP_W / 2)
                    link = box(*sorted((xw, xo + side * CLIP_T)), yin1 + CLIP_GAP, ybk, c - CLIP_W / 2, c + CLIP_W / 2)
                    barb = box(*sorted((xw - side * (GROOVE_D - 0.1), xo)), yb0, yb1, c - CLIP_W / 2, c + CLIP_W / 2)
                    body = body.cut(groove); cover = cover.fuse(tab).fuse(link).fuse(barb); clip_n += 1
                    c += CLIP_PITCH; continue
            c += 2.0
    cover = cover.removeSplitter()
    p.check(cover.isValid() and len(cover.Solids) == 1, f"cover with {clip_n} clips: one valid solid")
    body_segs = split(body, "body")
    for k, (where, q) in enumerate(body_segs, 1):
        bq = FreeCAD.BoundBox(q.BoundBox); bq.enlarge(0.5)
        n_sc = sum(1 for s in screws if bq.isInside(s) and q.distToShape(Part.Vertex(s))[0] < CSK_R + 0.5)
        p.check(n_sc >= 2, f"body segment {k} ({where}): held by {n_sc} screws (>= 2)")
    cover_segs = split(cover, "cover")
    for k, (where, q) in enumerate(cover_segs, 1):
        tabs = q.common(box(-2000, 2000, -2000, yin1 - 0.01, -2000, 2000))
        n_cl = len(tabs.Solids) if not tabs.isNull() else 0
        p.check(n_cl >= 2, f"cover segment {k} ({where}): {n_cl} clip barbs (>= 2)")

    # ---------------- chamfers
    made, chamf_log = {}, []
    def chamf(key, shape, up, what):
        s, info = printchamfer.chamfer(shape, up, **CHAMFER)
        skip = {w for k, w, c in info["skipped"]} | {w for k, w in info["failed"]}
        left = printchamfer.unchamfered(shape, s, up, **CHAMFER, skip=skip)
        p.check(s.isValid() and len(s.Solids) == 1 and not left,
                f"{what}: chamfered (up {tuple(round(c, 3) for c in up)}): {info['bottom']} first-layer, {info['top']} top, "
                f"{len(info['reduced'])} reduced, {len(info['skipped'])} skipped, {len(info['failed'])} OCC couldn't build; "
                f"-{info['removed_mm3']:.0f} mm3; missed: {left[:4]}")
        made[key] = s; return s
    for k, (where, q) in enumerate(body_segs, 1): chamf(("body", k), q, UP["body"], f"body segment {k} ({where})")
    for k, (where, q) in enumerate(cover_segs, 1): chamf(("cover", k), q, UP["cover"], f"cover segment {k} ({where})")
    for i, (x, j) in enumerate(zip(chosen, [None] + jx), 1):
        ps = post_at(x, j); top = ps.BoundBox.ZMax
        down = [f for f in ps.Faces if isinstance(f.Surface, Part.Plane) and f.normalAt(0, 0).z > 0.7 and f.BoundBox.ZMax < top - 0.05]
        small = [f for f in down if max(f.BoundBox.XLength, f.BoundBox.YLength) <= 2 * M3_INS + 0.01]   # an insert hole's floor: a 4 mm bridge
        hang = sum(f.Area for f in down if f not in small)
        p.check(hang < 1.0, f"post {i} printed upside down (arm's top on the bed): faces that would hang {hang:.1f} mm2 "
                            f"(+ {len(small)} insert-hole floors, bridges of {2 * M3_INS:.0f} mm)")
    for i, (x, j) in enumerate(zip(chosen, [None] + jx), 1): chamf(("post", i), post_at(x, j), UP["post"], f"post {i} at X {x}" + (f", carrying the joint at X {j}" if j is not None else ""))
    for i, z in enumerate(ARM_Z, 1): chamf(("arm", i), arms[z], UP["arm"], f"arm {i} at Z {z}")
    centre = V(-245, 215, 300)
    def probe_flat(s0):
        """owner 2026-11-19: the bracket (two parallel plates on a web, an H) had no side that prints without supports.
        Its section at Z PROBE_CUT (through both plates and the web) is carried down to the lowest edge, Z PROBE_Z0,
        so all three stand on one flat face; the original holes are kept open through the new material (and nowhere else)."""
        bb = s0.BoundBox
        ws = s0.slice(V(0, 0, 1), PROBE_CUT)
        face = Part.Face(ws[0]) if len(ws) == 1 else None
        faces = [Part.Face(w) for w in ws]
        prof = faces[0]
        for f in faces[1:]: prof = prof.fuse(f)
        prof = prof.removeSplitter()                     # filled outline (inner wires, i.e. holes crossing the cut, filled)
        prof.translate(V(0, 0, PROBE_Z0 - PROBE_CUT))
        slab = prof.extrude(V(0, 0, PROBE_CUT - PROBE_Z0))
        holes = []
        for f in s0.Faces:
            if not isinstance(f.Surface, Part.Cylinder): continue
            u0, u1, v0, v1 = f.ParameterRange; q = f.valueAt((u0 + u1) / 2, (v0 + v1) / 2); n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            ax, c = V(f.Surface.Axis), V(f.Surface.Center); r = q - c; r = r - ax * r.dot(ax)
            if n.dot(r) < 0:                             # concave: a hole
                cyl = Part.makeCylinder(f.Surface.Radius, 200, c - ax * 100, ax)
                holes.append((round(f.Surface.Radius, 2), tuple(round(x, 1) for x in c), tuple(round(x, 2) for x in ax), cyl.common(slab).Volume > 1e-3, cyl))
        for *_, cyl in holes: slab = slab.cut(cyl)       # the holes kept open through the new material only
        s1 = s0.fuse(slab).removeSplitter()
        new_holes = s0.cut(s1).Volume                    # the bracket's old material is all still there: nothing drilled anew
        up = V(0, 0, 1)
        z0 = s1.BoundBox.ZMin
        flat = sum(f.Area for f in s1.Faces if isinstance(f.Surface, Part.Plane) and f.BoundBox.ZMax < z0 + 1e-3)
        hang = sum(f.Area for f in s1.Faces if isinstance(f.Surface, Part.Plane) and f.normalAt(0, 0).z < -0.7 and f.BoundBox.ZMax > z0 + 0.05)
        b1 = s1.BoundBox
        same = all(abs(x - y) < 1e-3 for x, y in zip((bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax), (b1.XMin, b1.XMax, b1.YMin, b1.YMax, b1.ZMin, b1.ZMax)))
        p.check(s1.isValid() and len(s1.Solids) == 1 and hang < 1.0 and same and abs(z0 - PROBE_Z0) < 1e-3 and new_holes < 1e-3,
                f"probe bracket: section at Z {PROBE_CUT} carried down to Z {PROBE_Z0} (+{s1.Volume - s0.Volume:.0f} mm3); flat face on the bed "
                f"{flat:.0f} mm2 (lite-70's largest {bed_up(s0, centre)[1]:.0f}); faces that would hang {hang:.1f} mm2; box unchanged {same}; "
                f"old material removed {new_holes:.3f} mm3; holes kept open {[(h[0], h[1], h[2], 'through the new part' if h[3] else '') for h in holes]}")
        p.no_overlap([("probe bracket, flat side", s1)], pr, lambda r: f"probe bracket's new material vs the printer: {r.hits[:6]}",
                     exclude={o_.Name for o_ in pr.leaves if o_.Label.startswith("Nozzle offset probe bracket")})
        return s1, up, flat
    retro_new = {}
    for lab, o in retro.items():
        s0 = pr.shapes[o.Name]
        if lab.startswith("Nozzle offset probe bracket"):
            s0, up, area = probe_flat(s0)
        else:
            up, area = (V(0, 1, 0), None) if lab.startswith("E-box grille") else bed_up(s0, centre)   # grille: outside face (-Y) down
        s, info = printchamfer.chamfer(s0, up, **CHAMFER)
        skip = {w for k, w, c in info["skipped"]} | {w for k, w in info["failed"]}
        left = printchamfer.unchamfered(s0, s, up, **CHAMFER, skip=skip)
        b0, b1 = s0.BoundBox, s.BoundBox
        same = all(abs(a - b) < 1e-3 for a, b in zip((b0.XMin, b0.XMax, b0.YMin, b0.YMax, b0.ZMin, b0.ZMax),
                                                        (b1.XMin, b1.XMax, b1.YMin, b1.YMax, b1.ZMin, b1.ZMax)))
        lost = (s0.Volume - s.Volume) / s0.Volume
        p.check(s.isValid() and len(s.Solids) == len(s0.Solids) and not left and same and 0 < lost < 0.05,
                f"retrofit {lab}: printed on {'its outside face' if area is None else f'its largest face ({area:.0f} mm2)'} (up {tuple(round(c, 2) for c in up)}): "
                f"{info['bottom']} first-layer, {info['top']} top, {len(info['reduced'])} reduced, {len(info['skipped'])} skipped, "
                f"{len(info['failed'])} OCC couldn't build; -{lost * 100:.2f} %; box unchanged {same}; missed {left[:3]}")
        retro_new[lab] = s
    if p.errs: return p.finish([])

    # ---------------- into the document
    for o in old.values(): doc.removeObject(o.Name)
    newo = {}
    def add(key, s, label, kp):
        o = doc.addObject("Part::Feature", re.sub(r"\W", "_", label.split(" (")[0])[:40])
        if kp["group"] is not None: kp["group"].addObject(o)
        loc = s.copy(); loc.Placement = gplace(o).inverse().multiply(loc.Placement); o.Shape = loc
        o.Label = label
        if kp["mat"] is not None and hasattr(o, "ShapeMaterial"): o.ShapeMaterial = kp["mat"]
        if kp["app"] is not None: o.ViewObject.ShapeAppearance = kp["app"]
        newo[key] = o
    for k, (where, _) in enumerate(body_segs, 1):
        add(("body", k), made[("body", k)], SEG.format(what="body", k=k, n=5, where=where), keep[("chan", "body")])
    for k, (where, _) in enumerate(cover_segs, 1):
        add(("cover", k), made[("cover", k)], SEG.format(what="cover", k=k, n=5, where=where), keep[("chan", "cover")])
    for i in range(1, 5): add(("post", i), made[("post", i)], POSTS.format(i=i), keep[("post", i)])
    for i in range(1, 3): add(("arm", i), made[("arm", i)], ARMS.format(i=i), keep[("arm", i)])
    for lab, o in retro.items(): set_shape_keep_placement(o, retro_new[lab])
    doc.recompute(); pr.refresh()
    for key, o in newo.items():
        g_ = pr.shapes[o.Name]
        p.check(abs(g_.Volume - made[key].Volume) < 1e-3, f"{o.Label[:50]}: in the model as made")
    # ---------------- overlaps
    mine = {o.Name for o in newo.values()}
    cab = {o.Name for o in cables}
    body_n = {newo[("body", k)].Name for k in range(1, 6)}
    rigid = [(o.Label, pr.shapes[o.Name]) for o in newo.values()]
    p.no_overlap(rigid, pr, lambda r: f"new channel parts vs the printer: {r.hits[:6]}", exclude=mine | cab | {env.Name})
    p.no_overlap([x for x in rigid if pr.doc.getObjectsByLabel(x[0])[0].Name not in body_n], pr,
                 lambda r: f"posts, arms, cover vs the cables: {r.hits[:6]}", exclude={o.Name for o in pr.leaves} - cab)
    items = list(newo.values())
    cover_n = {newo[("cover", k)].Name for k in range(1, 6)}
    bc = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            sa, sb = pr.shapes[a.Name], pr.shapes[b.Name]
            if not sa.BoundBox.intersect(sb.BoundBox): continue
            v = sa.common(sb).Volume
            if {a.Name, b.Name} & body_n and {a.Name, b.Name} & cover_n: bc.append((a.Label[:36], b.Label[:36], v, sa.common(sb).BoundBox))
            elif v >= TOL: p.check(False, f"{a.Label[:40]} vs {b.Label[:40]}: {v:.3f} mm3")
    bc_new = sum(v for *_, v, _ in bc)
    p.check(bc_new <= bc_before + TOL, f"body vs cover, all segments: {bc_new:.3f} mm3 (lite-70's body vs cover: {bc_before:.3f}, never checked there) "
            f"{[(x, y, round(v, 3), tuple(round(c, 1) for c in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))) for x, y, v, bb in bc if v >= TOL]}")
    env_after = sum(env_vol(pr.shapes[o.Name]) for o in newo.values())
    p.check(env_after <= env_before + 1.0, f"in the side pack (its envelope up to the rear panel, Y {EBOX_REAR_Y1}): {env_after:.0f} mm3 (lite-70: {env_before:.0f})")
    # ---------------- roles, count
    for key, o in newo.items():
        k0 = ("chan", key[0]) if key[0] in ("body", "cover") else key
        r_ = colours.role_of(cmap, o.Label, gpath(o), "Default")
        p.check(r_ == role[k0], f"{o.Label[:50]}: role {r_} (lite-70: {role[k0]})")
    p.check(len(pr.leaves) == n_before + 8, f"solids: {n_before} -> {len(pr.leaves)} (body and cover 1 -> 5 each)")
    p.dump({"posts_x": chosen, "joints_x": jx, "post_arms_x": [[round(a, 1), round(b, 1)] for a, b in arm_spans], "joint_z": JOINT_Z, "arms_z": ARM_Z, "clips": clip_n, "bed_mm": BED,
            "segments": {w: [round(q.BoundBox.XLength, 1), round(q.BoundBox.ZLength, 1)] for w, q in body_segs},
            "fasteners": {"M5x10 SHCS (ISO 4762) + M5 drop-in T-nut, post lips into the rear top 4040's upper back slot (Z 680)": 4,
                          "M5x16 SHCS (ISO 4762) + M5 drop-in T-nut, drop arms into the rear-right upright's back slot (X 20)": 2,
                          "M3x6 countersunk (ISO 10642), channel into the posts and arms": len(screws),
                          "M3 heat-set insert (Ø4.0 hole, <= 6 mm long)": len(screws)},
            "retrofit": RETRO, "retrofit_print": "grille panels and badge: outside face down; probe bracket: its largest flat face down"})
    p.finish([(doc, DST)])


litelib.Pass("lite71_channel_fixings").run(main)
