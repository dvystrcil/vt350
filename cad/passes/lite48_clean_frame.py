# GUI pass: vt350-lite-47 -> vt350-lite-48   (headless = dry run, never saves)
# vt350#195: every frame extrusion (the 30 2020/2040/4040s: frame, door frame, gantry, e-box) rebuilt from a clean
# profile. The imported members are heavy and broken for OCC (the 2040s ~20 MB of BRep each, 94-pole B-spline edges,
# 0.0046 mm gaps, a profile 0.002 out of flat), so every boolean on them fails; lite-46/47 had to work around that.
# Each member becomes an exact prism (platform/freecad/profile_lib.py):
#  - the profile is a slice from the MIDDLE of the member, as exact lines and arcs on an exact plane. Not the end face:
#    the ends carry the tapped bore (the 2040s model the thread as 25 rings), which the end-face extrusions of lite-46/47
#    copied along the whole length. Of 8 slices the area most agree on wins, so a slice through a cross-hole, or through
#    a lite-46 extension piece made from an end face, is outvoted. The tapped ends become the plain bore; screws in end
#    bores already overlapped the modelled thread, so their overlap with the bore is not new.
#  - the length is the member's own, its ends snapped to the 0.1 mm grid when within 0.01 (lite-46 left rails ending at
#    Y 480.0023 and X -520.0009, microns into their neighbours).
#  - every cross-hole is cut back, one cylinder per hole face at that face's own extent, so joints, counterbores and the
#    lite-45/46/47 holes come back exactly. Except: the 8 joint holes at Z 380 in the 4 printer uprights, orphaned since
#    lite-10 raised the gantry 50 mm (user, 2026-11-16: "there seems to be some orphanded holes here").
#  - lite-46's three-piece compound rails become one solid.
# The orphaned holes move up with the gantry: the 8 screws they were for went up 50 mm with it in lite-10 and have run
# through solid upright since (lite-47 overlaps of 184 mm3 each). Each hole comes back exactly as the original designer
# made it, 50 mm higher, at Z 430, the gantry rails' end bores: in the rear 4040 uprights a D5 hole and a D10 counterbore
# for the M5x50 that runs through into the rail's end; in the front 2040 uprights the D5 hex-key access holes for the
# M5x16 whose head sits in the upright's slot. No hardware is added.
# Checks (refuses to save on any): 30 members, each a plain Part::Feature nothing else is built from; each rebuilt as one
# valid solid whose box matches the old one; each kept hole is open, each orphan filled, each moved hole open; the 8
# gantry joint screws (and washers) clear their upright; no new or grown overlaps against lite-47 except screws in the
# end bores (thread engagement: the clean D4.2 bore replaces the modelled thread); the same number of solids.
import FreeCAD, Part, os, sys, time, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
import profile_lib as PL
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-47.FCStd", f"{MODELS}/vt350-lite-48.FCStd"
N_MEMBERS = 30
UPRIGHTS = {"4040 upright Z -10..650 (lite-46)": "rear", "4040(Mirror) upright Z -10..650 (lite-46)": "rear",
            "2040 upright Z -10..650 (lite-46)": "front", "2040(Mirror) upright Z -10..650 (lite-46)": "front"}
ORPHAN_Z = 380.0
GANTRY = ["2040 (3)", "2040 (3)001"]
VOL_TOL = 0.03                                     # rebuilt vs old volume (taps, threads, extension pieces)


def is_member(o):
    return o.Label.startswith(("2020", "2040", "4040"))


def main(p):
    pr = p.open(SRC); doc = pr.doc
    n_before = len(pr.leaves)
    old = {o.Name: pr.shapes[o.Name] for o in pr.leaves}
    members = [o for o in pr.leaves if is_member(o)]
    p.check(len(members) == N_MEMBERS, f"{N_MEMBERS} frame members: {len(members)}")
    for o in members:
        users = [x.Label for x in o.InList if o not in getattr(x, "Group", [])]
        p.check(o.TypeId == "Part::Feature" and not users, f"{o.Label}: a plain Part::Feature ({o.TypeId}), built into nothing {users}")
    by = {o.Label: o for o in members}

    def put(o, s):
        """o's shape := s (global). The shape goes in local to o's parents and o.Placement follows it (a Part::Feature's
        Placement IS its shape's). lite-46/47's put also set o.Placement to identity afterwards, which drops the shape's
        placement again: right only under an identity parent (the VT Frame), 78 mm off under the Door Frame's."""
        par = o.getGlobalPlacement().multiply(o.Placement.inverse())
        col = o.ViewObject.ShapeColor if FreeCAD.GuiUp else None
        s = s.copy(); s.Placement = par.inverse().multiply(s.Placement)
        o.Shape = s
        if col is not None: o.ViewObject.ShapeColor = col

    # 1. the gantry joints: the orphaned holes, moved to the gantry rails' end-bore height
    zs = [(pr.boxes[by[g].Name].ZMin + pr.boxes[by[g].Name].ZMax) / 2 for g in GANTRY if g in by]
    p.check(len(zs) == 2 and all(abs(z - zs[0]) < 0.01 for z in zs), f"gantry rails at one height: Z {zs}")
    DZ = round(zs[0] - ORPHAN_Z, 2) if zs else 0.0
    p.check(DZ == 50.0, f"gantry rails' bores at Z {ORPHAN_Z + DZ:.1f}: the orphaned holes move {DZ:+.1f} (lite-10 raised the gantry 50)")

    def joint_tools(lab):
        if lab not in UPRIGHTS: return []
        ax, _ = PL.axis_of(old[by[lab].Name])
        return [PL.hole_solid(h, 0.01).translated(V(0, 0, DZ)) for h in PL.cross_holes(old[by[lab].Name], ax)
                if h["dir"] != 2 and abs(h["line"][2] - ORPHAN_Z) < 1.0]

    # 2. rebuild every member
    rows, new_shape = [], {}
    t_all = time.time()
    def orphan_of(o):
        return (lambda h: h["dir"] != 2 and abs(h["line"][2] - ORPHAN_Z) < 1.0) if o.Label in UPRIGHTS else (lambda h: False)

    def family(o):      # the profile's outer size, e.g. (40, 40)
        b = pr.boxes[o.Name]; d = sorted((b.XLength, b.YLength, b.ZLength))
        return (round(d[0]), round(d[1]))

    built = {}
    for o in members:
        t = time.time()
        try:
            built[o.Name] = PL.rebuild(old[o.Name], drop=orphan_of(o), extra_holes=joint_tools(o.Label)) + (time.time() - t,)
        except Exception as e:
            p.check(False, f"{o.Label}: rebuild failed: {e!r}")
    # a member whose slices disagree takes the profile its size's self-consistent members have, if it has it among its
    # slices (lite-46's 4040 (2) rail: 4 slices of the true 4040 profile, 4 of an extension piece extruded from an end face)
    agreed = {}
    for o in members:
        if o.Name in built and len(built[o.Name][1]["votes"]) == 1:
            agreed.setdefault(family(o), {}).setdefault(round(built[o.Name][1]["area"], 2), 0)
            agreed[family(o)][round(built[o.Name][1]["area"], 2)] += 1
    for o in members:
        if o.Name not in built or len(built[o.Name][1]["votes"]) == 1: continue
        rep = built[o.Name][1]; fam = agreed.get(family(o), {})
        pick = [a for a in rep["votes"] if a in fam]
        if pick and round(rep["area"], 2) not in pick:
            prefer = {max(pick, key=lambda a: fam[a])}
            p.log(f"  {o.Label}: slices split {rep['votes']}; taking {prefer} (the {family(o)} profile of {fam})")
            t = time.time()
            built[o.Name] = PL.rebuild(old[o.Name], drop=orphan_of(o), extra_holes=joint_tools(o.Label), prefer=prefer) + (time.time() - t,)
    for o in members:
        if o.Name not in built: continue
        s = old[o.Name]; n, rep, secs = built[o.Name]; orphan = orphan_of(o); t = time.time() - secs
        ob_old, ob_new = s.optimalBoundingBox(), n.optimalBoundingBox()
        dev = max(abs(a - b) for a, b in zip((ob_old.XMin, ob_old.YMin, ob_old.ZMin, ob_old.XMax, ob_old.YMax, ob_old.ZMax),
                                             (ob_new.XMin, ob_new.YMin, ob_new.ZMin, ob_new.XMax, ob_new.YMax, ob_new.ZMax)))
        dv = (n.Volume - s.Volume) / s.Volume
        kb_old, kb_new = len(s.exportBrepToString()) / 1e3, len(n.exportBrepToString()) / 1e3
        p.check(len(n.Solids) == 1 and n.isValid(), f"{o.Label}: one valid solid ({len(n.Solids)}, valid {n.isValid()})")
        p.check(dev <= 0.011, f"{o.Label}: box as before within 0.011 ({dev:.4f})")
        p.check(abs(dv) <= VOL_TOL, f"{o.Label}: volume {s.Volume:.0f} -> {n.Volume:.0f} mm3 ({100 * dv:+.2f}%), within {100 * VOL_TOL:.0f}%")
        # every hole the old member had, probed on rings of 8 points 0.3 inside its radius at 5 places along it (the axis
        # itself can fall in a slot or a bore): kept, none of them is material; dropped, some are (the wall it was in)
        for h in PL.cross_holes(s, rep["ax"]):
            hit, c = probe_hole(n, h)
            at = tuple(round(x, 1) for x in c)
            if orphan(h): p.check(hit > 0, f"{o.Label}: orphaned hole r {h['r']:.2f} at {at} filled ({hit} of 40 probe points material)")
            else: p.check(hit == 0, f"{o.Label}: hole r {h['r']:.2f} at {at} kept ({hit} of 40 probe points material)")
        rows.append(dict(label=o.Label, ax=rep["ax"], length=round(rep["hi"] - rep["lo"], 3), kb_old=round(kb_old), kb_new=round(kb_new),
                         area=round(rep["area"], 3), votes=rep["votes"], edges={k: rep[k] for k in ("line", "arc", "spline_as_arc", "spline_kept")},
                         holes=rep["holes"], holes_kept=rep["holes_kept"], holes_dropped=rep["holes_dropped"], dropped=rep["dropped"],
                         joint_holes=rep["extra_holes"], split_kept=rep["split_faces_kept"], cut=rep["cut_method"], vol_old=round(s.Volume, 1), vol_new=round(n.Volume, 1), box_dev=round(dev, 4),
                         secs=round(time.time() - t, 1)))
        p.log(f"  {o.Label[:52]:52} {kb_old:8.0f} -> {kb_new:4.0f} KB  area {rep['area']:.2f} {rep['votes']}  holes {rep['holes_kept']}/{rep['holes']}"
              f"{' +' + str(rep['extra_holes']) + ' joint' if rep['extra_holes'] else ''}  vol {100 * dv:+.2f}%  {time.time() - t:.1f}s")
        new_shape[o.Name] = n
    tot_old, tot_new = sum(r["kb_old"] for r in rows), sum(r["kb_new"] for r in rows)
    p.log(f"rebuilt {len(rows)} members: {tot_old / 1e3:.1f} MB -> {tot_new / 1e3:.2f} MB of BRep in {time.time() - t_all:.0f}s")
    p.check(len(rows) == len(members), f"all members rebuilt: {len(rows)} of {len(members)}")
    p.check(sum(r["holes_dropped"] for r in rows if r["label"] in UPRIGHTS) >= 8 and
            all(r["joint_holes"] == r["holes_dropped"] for r in rows) and
            all(r["holes_dropped"] == 0 for r in rows if r["label"] not in UPRIGHTS),
            f"orphaned holes dropped only in the 4 uprights: {[(r['label'][:12], r['holes_dropped']) for r in rows if r['holes_dropped']]}")
    # 3. each moved hole open at Z 430 (ring check as above)
    for o in members:
        if o.Label not in UPRIGHTS or o.Name not in new_shape: continue
        n = new_shape[o.Name]
        for h in PL.cross_holes(old[o.Name], 2):
            if not (h["dir"] != 2 and abs(h["line"][2] - ORPHAN_Z) < 1.0): continue
            hit, c = probe_hole(n, h, DZ)
            p.check(hit == 0, f"{o.Label}: moved hole r {h['r']:.2f} at {tuple(round(x, 1) for x in c)} open ({hit} of 40 probe points material)")
    for o in members:
        if o.Name in new_shape: put(o, new_shape[o.Name])
    # 4. the right-hand gantry joint hardware sits 1 mm +Y of its left-hand mirror (about X -245): the rear M5x50s 1 mm
    #    proud of the upright, the front washers 20 mm3 into the upright's slot lips (lite-47). Moved to match the left.
    zj = ORPHAN_Z + DZ
    def bc(o, i):
        b = pr.boxes[o.Name]; return ((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, (b.ZMin + b.ZMax) / 2)[i]
    hw = [o for o in pr.leaves if o.Label.startswith(("M5x50-Screw", "M5x16-Screw", "M5-Washer")) and abs(bc(o, 2) - zj) < 1.0
          and (bc(o, 1) < -40 or bc(o, 1) > 460) and (-30 < bc(o, 0) < 40 or -530 < bc(o, 0) < -460)]
    kind = lambda o: o.Label.split("-")[0] + o.Label.split("-")[1][:5]
    moved = []
    for r in [o for o in hw if bc(o, 0) > -245]:
        mate = [l for l in hw if bc(l, 0) < -245 and kind(l) == kind(r) and abs((-490 - bc(r, 0)) - bc(l, 0)) < 0.1
                and (bc(l, 1) > 0) == (bc(r, 1) > 0)]
        p.check(len(mate) == 1, f"{r.Label}: its left-hand mirror found once: {[l.Label for l in mate]}")
        if len(mate) != 1: continue
        rb, lb = pr.boxes[r.Name], pr.boxes[mate[0].Name]
        dy = round(lb.YMin - rb.YMin, 3)
        p.check(abs(rb.YLength - lb.YLength) < 0.05 and abs(dy + 1.0) < 0.05,
                f"{r.Label}: Y {rb.YMin:.2f}..{rb.YMax:.2f}, its mirror {mate[0].Label} {lb.YMin:.2f}..{lb.YMax:.2f}: moves {dy:+.2f}")
        # a Fasteners-workbench object (Part::FeaturePython) rebuilds its shape from its Placement: move the Placement
        par = r.getGlobalPlacement().multiply(r.Placement.inverse())
        r.Placement = par.inverse().multiply(FreeCAD.Placement(V(0, dy, 0), FreeCAD.Rotation()).multiply(r.getGlobalPlacement()))
        moved.append(r)
    p.check(len(moved) == 8, f"8 right-hand gantry joint parts moved to mirror the left: {[o.Label for o in moved]}")
    doc.recompute(); pr.refresh()
    new = moved
    # every member where its rebuilt shape is, every moved part 1 mm along Y and nowhere else, read back from the document
    for o in members:
        if o.Name not in new_shape: continue
        a, b = pr.boxes[o.Name], new_shape[o.Name].optimalBoundingBox()
        dev = max(abs(x - y) for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax), (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
        p.check(dev <= 0.01, f"{o.Label}: in the document where it was built ({dev:.4f})")
    for o in moved:
        a, b = pr.boxes[o.Name], old[o.Name].optimalBoundingBox()
        d = (a.XMin - b.XMin, a.YMin - b.YMin, a.ZMin - b.ZMin, a.XMax - b.XMax, a.YMax - b.YMax, a.ZMax - b.ZMax)
        p.check(all(abs(x) < 0.01 for i, x in enumerate(d) if i % 3 != 1) and all(abs(x + 1.0) < 0.01 for i, x in enumerate(d) if i % 3 == 1),
                f"{o.Label}: in the document 1 mm toward -Y, nothing else ({tuple(round(x, 3) for x in d)})")
    # 4. overlaps against lite-47
    def in_end_bore(m, f):
        """the overlap of member m and fastener f is a screw's thread in m's end bore: within 1 of an end, at most 40
        along m, at most the screw's 5.2 across"""
        ax, ob = PL.axis_of(pr.shapes[m.Name])
        c = pr.shapes[m.Name].common(pr.shapes[f.Name])
        if not c.Solids: return False
        cb = c.BoundBox; lo, hi = (ob.XMin, ob.YMin, ob.ZMin)[ax], (ob.XMax, ob.YMax, ob.ZMax)[ax]
        c0, c1 = (cb.XMin, cb.YMin, cb.ZMin)[ax], (cb.XMax, cb.YMax, cb.ZMax)[ax]
        across = [(cb.XLength, cb.YLength, cb.ZLength)[i] for i in range(3) if i != ax]
        return min(c0 - lo, hi - c1) <= 1.0 and c1 - c0 <= 40 and max(across) <= 5.2

    is_screw = lambda o: "Screw" in o.Label or "SHCS" in o.Label
    mem = members + new
    names = {o.Name for o in mem}
    env = {o.Name for o in pr.leaves if o.Label.startswith("Ebox envelope")}
    cand = [(m, o) for m in mem for o in pr.leaves if o.Name != m.Name and o.Name not in env
            and (o.Name not in names or m.Name < o.Name) and pr.boxes[o.Name].intersect(pr.boxes[m.Name])]
    p.log(f"overlap candidates: {len(cand)} pairs")
    vnew = p.volumes([(pr.shapes[m.Name], pr.shapes[o.Name]) for m, o in cand])
    vold = p.volumes([(old[m.Name], old[o.Name]) if m.Name in old and o.Name in old else (Part.Shape(), Part.Shape())
                      for m, o in cand])
    fresh, grown, kept, thread, unverified, gone = [], [], [], [], [], []
    for (m, o), a, b in zip(cand, vnew, vold):
        both_old = m.Name in old and o.Name in old
        pair = (m.Label[:44], o.Label[:40], round(a, 2), round(b, 2) if b != float("inf") else "failed")
        if a == float("inf"): fresh.append(pair + ("new boolean failed",)); continue
        mm, ff = (m, o) if is_member(m) else (o, m)
        if a > 1e-2 and is_member(mm) and is_screw(ff) and (b == float("inf") or a > b + 1e-2) and in_end_bore(mm, ff):
            thread.append(pair); continue
        if not both_old: b = 0.0
        if b == float("inf"):
            if a > 1e-2: unverified.append(pair)
            continue
        if a > 1e-2 and b <= 1e-2: fresh.append(pair)
        elif a > b + max(1.0, 0.05 * b): grown.append(pair)
        elif b > 1e-2 and a > 1e-2: kept.append(pair)
        elif b > 1e-2: gone.append(pair)
    p.log(f"info screws threaded into end bores, overlap new or grown (the clean bore replaces the modelled thread): {len(thread)} {thread}")
    p.log(f"info overlaps lite-47 already has, not grown: {len(kept)} {kept}")
    p.log(f"info overlaps lite-47 had that are gone: {len(gone)} {gone}")
    p.log(f"info overlaps where lite-47's boolean failed (can't compare; volumes now): {len(unverified)} {unverified}")
    p.check(not fresh, f"new overlaps (pairs that didn't overlap in lite-47): {len(fresh)} {fresh[:12]}")
    p.check(not grown, f"grown overlaps (> 5% and > 1 mm3 more than lite-47): {len(grown)} {grown[:12]}")
    # the 8 gantry joint screws and their washers: clear of the uprights now
    up = {by[l].Name for l in UPRIGHTS if l in by}
    jf = [(u, f, a, b) for (m, o), a, b in zip(cand, vnew, vold) for u, f in ((m, o), (o, m))
          if u.Name in up and f.Label.startswith(("M5x50-Screw", "M5x16-Screw", "M5-Washer"))
          and abs((pr.boxes[f.Name].ZMin + pr.boxes[f.Name].ZMax) / 2 - (ORPHAN_Z + DZ)) < 1.0]
    p.check(sum(1 for _, o, _, _ in jf if "Screw" in o.Label) == 8 and all(a <= 1e-2 for _, _, a, _ in jf),
            f"the 8 gantry joint screws and their washers clear their upright: {[(o.Label, round(b, 1) if b != float('inf') else 'failed', round(a, 3)) for _, o, a, b in jf]}")
    p.check(len(pr.leaves) == n_before, f"solids: {len(pr.leaves)} (as lite-47: {n_before})")
    p.log(f"info faces left split where merging them broke the solid: {[r['label'] for r in rows if r['split_kept']]}")
    p.log(f"info holes cut one at a time (the one cut was invalid): {[r['label'] for r in rows if r['cut'] == 'hole by hole']}")
    p.dump({"members": rows, "brep_mb": [round(tot_old / 1e3, 1), round(tot_new / 1e3, 2)],
            "orphan_z": ORPHAN_Z, "moved_to_z": ORPHAN_Z + DZ, "hardware_moved_y": [o.Label for o in moved],
            "overlaps": dict(thread=len(thread), kept=len(kept), gone=len(gone), unverified=unverified)})
    return p.finish([(doc, DST)])


def probe_hole(n, h, dz=0.0):
    """-> (how many of 40 points inside hole h, raised dz, are material of n; the hole's mid point): rings of 8 at 0.3
    inside its radius, at 10, 30, 50, 70 and 90% of its extent"""
    hit = 0
    for k in (0.1, 0.3, 0.5, 0.7, 0.9):
        c = list(h["line"]); c[h["dir"]] = h["lo"] + (h["hi"] - h["lo"]) * k; c[2] += dz
        hit += sum(n.isInside(q, 1e-3, True) for q in ring(c, h["dir"], h["r"] - 0.3))
    c = list(h["line"]); c[h["dir"]] = (h["lo"] + h["hi"]) / 2; c[2] += dz
    return hit, c


def ring(c, d, r, n=8):
    """n points at radius r around the axis along coordinate d through c."""
    a, b = [i for i in range(3) if i != d]
    out = []
    for k in range(n):
        q = list(c); q[a] += r * math.cos(2 * math.pi * k / n); q[b] += r * math.sin(2 * math.pi * k / n); out.append(V(*q))
    return out


litelib.Pass("lite48_clean_frame").run(main)
