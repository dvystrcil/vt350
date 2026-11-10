# GUI pass: vt350-lite-6.FCStd -> vt350-lite-7.FCStd   (headless = dry run, never saves)
# Re-draw both XY belts on the LDO Monolith milled 2WD path. lite-6 still had lite-5's belts: drawn for the printed
# AWD joints (2.2-2.8 mm off the milled ones) and ~58 mm short of the front idlers.
#  - Each belt is its GT2 pitch line through the pulleys/idlers in Monolith 2WD order: straight tangents + wraps,
#    from one carriage belt clip to the other. Pitch line = pulley OD + 0.254 mm on the tooth side, idler OD +
#    1.126 mm where the belt's back rides the idler (GT2: 1.38 mm thick, tooth tips 0.254 mm inside the pitch line).
#  - The solid is the 1.38 x 9 mm belt section swept along that line, so it touches every pulley and idler.
#  - The pitch length (what belts are sold by) is stored on each belt and logged; each end stops at the OUTER edge
#    of its carriage belt clip (running to the clip centre cuts into the carriage), so add the tuck-in when cutting.
# Checks: every pulley centre is found in the model; belts are valid single solids; no overlap > 0.5 mm3 with any
# part except the two carriage belt clips the ends sit in; everything else unchanged. Refuses to save otherwise.
import FreeCAD, Part, sys, os, time, math, traceback
sys.path.insert(0, "/home/dan/.local/share/FreeCAD/v26-3/Mod/fasteners")
import FastenersCmd  # noqa: F401
V = FreeCAD.Vector
WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
SRC = "/home/dan/Documents/VT350/vt350-lite-6.FCStd"
DST = "/home/dan/Documents/VT350/vt350-lite-7.FCStd"
DRY = not FreeCAD.GuiUp
OLD_BELTS = ["_9mm_2WD_belt_FT_FT", "_9mm_2WD_belt_FT_FT001"]
# The printed Y endstop (from the printed gantry lite-6 replaced) sits in the lower belt's rear cross-run (155 mm3) and its
# T-nut shares a slot with the milled rear mount's. Removed with its hardware; the Y endstop is to be chosen again.
REMOVE_GROUPS = ["_1_Y_endstop_FT v1"]
CLIPS = {"R": "Clip (1)", "L": "Clip (1)001"}          # carriage belt clips (x -222.38 / -267.62)
T_BACK, T_TOOTH, H = 1.126, 0.254, 9.0                # GT2: pitch line -> back face, pitch line -> tooth tips; width
R_TOOTHED, R_IDLER = 6.11, 6.5                        # GT2 20T outer radius; 695 bearing outer radius
# (label, centre x, y, outer radius, wrap: +1 = counter-clockwise seen from +Z, -1 = clockwise)
# Wrap directions follow the Monolith 2WD path; the teeth face the toothed pulleys, so each belt's tooth side is fixed
# by its motor's wrap and every other element is a tooth-side or back-side contact accordingly.
BELTS = {
    "lower": dict(z=373.25, start="R", end="L", teeth=+1, path=[
        ("XY right idler",          -36.75, 251.76, R_IDLER,   -1),
        ("front right pulley",      -23.51, -75.60, R_TOOTHED, +1),
        ("front right idler",       -19.26, -59.60, R_IDLER,   -1),
        ("rear right MOTOR",        -32.50, 479.00, R_TOOTHED, +1),
        ("rear right idler",        -46.50, 471.50, R_IDLER,   -1),
        ("rear left toothed idler", -457.50, 458.26, R_TOOTHED, +1),
        ("XY left pulley",          -457.50, 265.00, R_TOOTHED, +1)]),
    "upper": dict(z=386.75, start="L", end="R", teeth=-1, path=[
        ("XY left idler",           -453.25, 251.76, R_IDLER,   +1),
        ("front left pulley",       -466.49, -75.60, R_TOOTHED, -1),
        ("front left idler",        -470.74, -59.60, R_IDLER,   +1),
        ("rear left MOTOR",         -457.50, 479.00, R_TOOTHED, -1),
        ("rear left idler",         -443.50, 471.50, R_IDLER,   +1),
        ("rear right toothed idler", -32.50, 458.26, R_TOOTHED, -1),
        ("XY right pulley",          -32.50, 265.00, R_TOOTHED, -1)]),
}
os.makedirs(WORK + "/logs", exist_ok=True)
log_f = open(WORK + "/logs/lite7_belts.log", "w"); t0 = time.time()
def log(*a):
    log_f.write(f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); log_f.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def gbox(o):
    s = gshape(o)
    try: return s.optimalBoundingBox(True, False)
    except Exception: return s.BoundBox
def parent_of(o):
    return next((x for x in o.InList if (x.isDerivedFrom('App::Part') or x.isDerivedFrom('App::DocumentObjectGroup'))
                 and o in getattr(x, 'Group', [])), None)
def container_global(o):
    p = parent_of(o)
    while p is not None:
        if p.isDerivedFrom('App::Part'): return p.getGlobalPlacement()
        p = parent_of(p)
    return FreeCAD.Placement()
def close(a, b, tol=1e-3):
    return all(abs(x - y) <= tol for x, y in zip((a.XMin, a.YMin, a.ZMin, a.XMax, a.YMax, a.ZMax),
                                                    (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
def lnorm(u): return V(-u.y, u.x, 0)                 # left normal of a direction in the XY plane

def tangent(c1, r1, c2, r2):
    """directed tangent from circle 1 to circle 2; r = signed radius (+ = centre on the left of travel).
    Returns (p1, p2, u)."""
    D = c2 - c1; L = D.Length
    if abs(r2 - r1) >= L: raise RuntimeError(f"no tangent: |{r2:.2f}-{r1:.2f}| >= {L:.2f}")
    phi = math.atan2(D.y, D.x); th = phi - math.asin((r2 - r1) / L)
    u = V(math.cos(th), math.sin(th), 0); n = lnorm(u)
    return c1 - n * r1, c2 - n * r2, u

def belt_path(spec, clip_pts):
    z = spec['z']; teeth = spec['teeth']
    circ = []
    for lab, x, y, R, s in spec['path']:
        contact = 'tooth' if s == teeth else 'back'
        rp = R + (T_TOOTH if contact == 'tooth' else T_BACK)
        if R == R_TOOTHED and contact != 'tooth': raise RuntimeError(f"{lab}: toothed pulley on the belt's back")
        circ.append((lab, V(x, y, z), rp * s, contact))
    P0 = clip_pts[spec['start']]; P1 = clip_pts[spec['end']]
    edges, length, wraps = [], 0.0, []
    # clip -> first circle (point = zero-radius circle)
    a, b, u = tangent(P0, 0.0, circ[0][1], circ[0][2]); edges.append(Part.LineSegment(P0, b).toShape()); length += (b - P0).Length
    arrive = b
    for i, (lab, c, rs, contact) in enumerate(circ):
        if i + 1 < len(circ): p1, p2, _ = tangent(c, rs, circ[i + 1][1], circ[i + 1][2])
        else: p1, p2, _ = tangent(c, rs, P1, 0.0)
        # arc on this circle from `arrive` to `p1`, in the wrap direction
        r = abs(rs); s = 1 if rs > 0 else -1
        a0 = math.atan2(arrive.y - c.y, arrive.x - c.x); a1 = math.atan2(p1.y - c.y, p1.x - c.x)
        sweep = (a1 - a0) % (2 * math.pi) if s > 0 else -((a0 - a1) % (2 * math.pi))
        if abs(sweep) > 1e-6:
            mid = a0 + sweep / 2
            pm = c + V(math.cos(mid), math.sin(mid), 0) * r
            edges.append(Part.Arc(arrive, pm, p1).toShape()); length += r * abs(sweep)
        wraps.append((lab, contact, r, math.degrees(abs(sweep))))
        edges.append(Part.LineSegment(p1, p2).toShape()); length += (p2 - p1).Length
        arrive = p2
    return Part.Wire(edges), length, wraps

def sweep_belt(wire, teeth):
    e0 = wire.Edges[0]; p = e0.valueAt(e0.FirstParameter); u = e0.tangentAt(e0.FirstParameter); n = lnorm(u)
    # tooth side: +n if the belt's teeth are on its left (teeth=+1), else -n
    nt = n * teeth
    lo, hi = -T_BACK, T_TOOTH                          # across the belt, measured toward the tooth side
    q = [p + nt * lo + V(0, 0, -H / 2), p + nt * hi + V(0, 0, -H / 2), p + nt * hi + V(0, 0, H / 2), p + nt * lo + V(0, 0, H / 2)]
    prof = Part.makePolygon(q + [q[0]])
    ps = Part.BRepOffsetAPI.MakePipeShell(wire)
    ps.setBiNormalMode(V(0, 0, 1))
    ps.add(prof, False, False)
    ps.build(); ps.makeSolid()
    return ps.shape()

try:
    errs = []
    doc = FreeCAD.openDocument(SRC)
    log("opened", SRC, len(doc.Objects))
    leaves = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids]
    before = {o.Name: gbox(o) for o in leaves}
    # every path element must exist in the model: a toothed core or 695 bearing centred there
    rot = [(o, gbox(o)) for o in leaves if ('toothed' in o.Label or '695' in o.Label)]
    for nm, spec in BELTS.items():
        for lab, x, y, R, s in spec['path']:
            hit = [o for o, b in rot if abs((b.XMin + b.XMax) / 2 - x) < 0.05 and abs((b.YMin + b.YMax) / 2 - y) < 0.05
                   and b.ZMin - 0.5 < spec['z'] < b.ZMax + 0.5]
            if not hit: errs.append(f"{nm}: no pulley/idler in the model at {lab} ({x}, {y}) spanning z {spec['z']}")
    clips = {k: doc.getObjectsByLabel(v) for k, v in CLIPS.items()}
    if any(len(v) != 1 for v in clips.values()): raise RuntimeError(f"belt clips: {[(k, len(v)) for k, v in clips.items()]}")
    clipbox = {k: gbox(v[0]) for k, v in clips.items()}
    old = []
    for lab in OLD_BELTS:
        c = doc.getObjectsByLabel(lab)
        if len(c) != 1: raise RuntimeError(f"{len(c)} objects labelled {lab!r}")
        old.append(c[0])
    grp = parent_of(old[0]); Cg = container_global(old[0])
    new = []
    for nm, spec in BELTS.items():
        z = spec['z']
        # the run into each clip is horizontal at the adjacent XY-joint pulley/idler's pitch line: end at the clip centre
        clip_pts = {}
        for k in ('R', 'L'):
            cb = clipbox[k]; cx = cb.XMax if k == 'R' else cb.XMin   # belts arrive from outboard of each clip
            el = spec['path'][0] if k == spec['start'] else spec['path'][-1]
            lab, x, y, R, s = el
            contact = 'tooth' if s == spec['teeth'] else 'back'
            rp = R + (T_TOOTH if contact == 'tooth' else T_BACK)
            yrun = y + rp if (y + rp) < (cb.YMax) and abs(y + rp - (cb.YMin + cb.YMax) / 2) < abs(y - rp - (cb.YMin + cb.YMax) / 2) else y - rp
            clip_pts[k] = V(cx, yrun, z)
        wire, L, wraps = belt_path(spec, clip_pts)
        solid = sweep_belt(wire, spec['teeth'])
        log(f"{nm} belt (z {z - H/2:.2f}..{z + H/2:.2f}): pitch length {L:.1f} mm outer clip edge to outer clip edge; "
            f"solid valid {solid.isValid()}, solids {len(solid.Solids)}, volume {solid.Volume:.0f} mm3 (expected ~{L * 1.38 * H:.0f})")
        for lab, contact, r, deg in wraps: log(f"     {lab:26} {contact:5} pitch R {r:5.2f}  wrap {deg:6.1f} deg")
        if not solid.isValid() or len(solid.Solids) != 1 or abs(solid.Volume - L * 1.38 * H) > 0.02 * L * 1.38 * H:
            errs.append(f"{nm}: belt solid failed checks")
        new.append((nm, solid, L))
    # remove the printed Y endstop group with everything in it
    removed = set()
    for gl in REMOVE_GROUPS:
        g = doc.getObjectsByLabel(gl)
        if len(g) != 1: raise RuntimeError(f"{len(g)} objects labelled {gl!r}")
        todo, seen = [g[0]], []
        while todo:
            x = todo.pop(); seen.append(x); todo += [c for c in getattr(x, 'Group', []) if c not in seen]
        n_solid = sum(1 for x in seen if x.Name in before)
        log(f"removing {gl}: {len(seen)} objects ({n_solid} solids): {sorted(x.Label for x in seen if x.Name in before)}")
        removed |= {x.Name for x in seen}
        for x in reversed(seen):
            try: doc.removeObject(x.Name)
            except Exception: pass
    # replace
    old_names = {o.Name for o in old} | removed
    for o in old: doc.removeObject(o.Name)
    made = []
    for nm, solid, L in new:
        s = solid.copy(); s.Placement = Cg.inverse().multiply(s.Placement)
        o = doc.addObject('Part::Feature', 'Belt'); o.Shape = s
        if grp is not None: grp.addObject(o)
        o.Label = f"GT2 9mm belt, {nm} (Monolith 2WD)"
        o.addProperty('App::PropertyLength', 'PitchLength', 'Belt', 'pitch length, outer clip edge to outer clip edge (add the clamp tuck-in)')
        o.PitchLength = L
        if o.ViewObject is not None:
            try: o.ViewObject.ShapeAppearance = (FreeCAD.Material(DiffuseColor=(0.1, 0.1, 0.1)),)
            except Exception: pass
        made.append(o)
    doc.recompute()
    # overlaps with anything except the clips
    others = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids
              and o not in made]
    for o in made:
        so = gshape(o); bo = so.BoundBox
        for b in others:
            if not bo.intersect(gbox(b)): continue
            try: v = so.common(gshape(b)).Volume
            except Exception: continue
            if v > 0.5:
                if b.Label in CLIPS.values(): log(f"   {o.Label} x {b.Label}: {v:.1f} mm3 (belt end in its clip: expected)")
                else: errs.append(f"{o.Label} overlaps {b.Label} [{parent_of(b).Label if parent_of(b) else ''}] by {v:.1f} mm3")
    # untouched
    now = {o.Name: o for o in doc.Objects}
    for n, b in before.items():
        if n in old_names: continue
        if n not in now: errs.append(f"lost {n}"); continue
        if not close(gbox(now[n]), b): errs.append(f"changed: {now[n].Label}")
    log(f"verify: {len(errs)} problems"); [log("  " + e) for e in errs]
    if errs: log("NOT SAVED")
    elif DRY: log("DRY RUN (headless): all checks passed, not saved")
    else: doc.saveAs(DST); log("SAVED", DST, os.path.getsize(DST))
except Exception:
    log("FAILED\n" + traceback.format_exc())
finally:
    log_f.close(); os._exit(0)
