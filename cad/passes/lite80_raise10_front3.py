# GUI pass: vt350-lite-79 -> vt350-lite-80   (headless = dry run, never saves)   vt350#243
# The gantry 10 mm higher, and the frame front 3 mm forward (owner, 2026-11-25). The frame lengths are then frozen.
#  - Why +10: #243, more print height (~334.4 -> ~344.4) in the same frame; 10.0, not 10.3, so the Z posts and the
#    rear vertical are a clean 440 (owner). Overtravel left for a shorter future head: ~11.2 mm.
#  - Why -3 in Y: the Y bars become 570 (567 since lite-78) and the e-box door rails 550, round lengths a friend can
#    cut (owner). At the FRONT, not the rear: the backbone bolts to the rear 4040's top slot at Y 490, so the rear can't
#    move (owner: "it depends on the backbone").
# STEP 1, front -3 (lite78_front17.py's rules, reused): FRONT set (box ends in front of Y -5, or a head or dock group)
#   moves -3; every other leaf reaching in front of Y -5 is spliced 3 longer; belts, Bowden tubes and O2S cables
#   spliced on their Y runs. The 490 Y rails aren't spliced: they move -1.5, centred between their mounts again.
# STEP 2, gantry +10: everything on the gantry moves +10 in Z: the frame's Gantry bars (2 x 2040 sides, rear 2020),
#   the Monolith group (mounts, motors, XY joints, X beam), the X rail, the carriage (and Beacon), the belts, the Y
#   rails, every head and dock, the dock bar and its end brackets, and the frame screws at those joints. The Z posts and
#   the rear 2020 vertical are spliced 10 longer at their tops (they end under the gantry). The Bowden tubes and O2S
#   cables lose 10 mm of their rise: cut out of a straight vertical stretch, the head end moved up.
# Checks (refuses to save on any): every leaf moved by exactly its step, spliced as planned, or unchanged; spliced
# parts valid with their solid count and volume; the Z posts and rear vertical 440 long and touching the gantry bars;
# rails 490, centred between the mounts; nozzle tips +10; nothing attached that would undo a move;
# COLLISIONS vs lite-79: no overlap that lite-79 didn't have.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render"),
                os.path.join(_REPO, "cad/passes")]
os.environ["LITE78_AS_LIB"] = "1"
import litelib, linkgeo
import lite78_front17 as l78
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-79.FCStd", f"{MODELS}/vt350-lite-80.FCStd"
DY, DZ = 3.0, 10.0
FRONT_Y = -5.0
FRONT_GROUPS = ("Toolhead", "Dock")
STAY = ("2040 Z post (R)", "2040(Mirror) Z post (L)", "backbone-350", "EMU envelope")
STAY_EXACT = ("2040 (2)",)                              # the bottom front 2040 at Y 0: the backbone's front holes
RAILS = ("MGN9 Y rail (",)                             # the lite-78 490s
FRONT_MOUNT, REAR_MOUNT = "VT9-FI", "VT9-R"
BELTS = ("GT2 9mm belt, lower", "GT2 9mm belt, upper")
TUBES, CABLES = ("Bowden ",), ("O2S USB cable slot ",)
TUBE_D, CABLE_D = 4.12, 5.1
RUN_GROUP = "O2S cables + channel"
SPLICE_Y = tuple(float(y) for y in range(30, 400, 5))
BELT_Y = tuple(float(y) for y in range(100, 170))
TUBE_Y = tuple(float(y) for y in range(100, 301))
# gantry riders (group names on the part's path, or labels)
RAISE_GROUPS = ("Monolith gantry", "Gantry assembly", "Carriage (1)", "_11_9mm_2WD_belts", "Toolhead", "Dock")
RAISE_FRAME_SUB = "Gantry"                              # the frame's sub-group: 2 x 2040 (3) + rear 2020
RAISE_LABELS = ("2020 dock bar", "Dock bar end bracket", "MGN9 Y rail (", "MGN_12_H_CARRAGE v1")   # + the X carriage block (root)
FASTENERS = "Fasteners"                                 # frame screws (M5, in the frame group): those at the gantry or
FRAME = "4040-350 VT Frame"                             # dock-bar joints ride
GANTRY_Z = (420.0, 440.0)
DOCKBAR_ZONE = FreeCAD.BoundBox(-525, -115, 465, 35, -65, 512)
POSTS = ("2040 Z post (R)", "2040(Mirror) Z post (L)")
REAR_VERTICAL = "2020 (3)"                              # Verticals: the rear 2020 under the gantry, Z -10..420
TUBE_Z = tuple(500.0 + 0.5 * i for i in range(200))    # where to look for a vertical stretch of each tube / cable
HEAD_Y = 0.0                                            # ... in its head end: the part in front of Y 0 (lite-79: tubes
                                                        # straight up at Y -50 over Z 520..550, cables at Y -6 over 560..590)
VERTICALS = "Verticals"                                 # frame uprights the riding joint screws pass through: re-drilled
TOL = 1e-3


def splice_z(s, zs_candidates, dz, probe=7.0):
    """A bar along Z: cut at a clean Z (section area the same `probe` higher), move the top part +dz, fill the gap
    with the section extruded (lite6.py's splice, turned to Z). (new, zs, area)"""
    bb = s.BoundBox; big = 5000
    def sec(z):
        low = s.common(Part.makeBox(big, big, z - bb.ZMin + 1, V(-big / 2, -big / 2, bb.ZMin - 1)))
        fs = [f for f in low.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).z) - 1) < 1e-6
              and abs(f.CenterOfMass.z - z) < 1e-6]
        return low, fs
    for zs in zs_candidates:
        if not (bb.ZMin + probe + 1 < zs < bb.ZMax - probe - 1): continue
        low, fs = sec(zs); _, fs2 = sec(zs + probe)
        a1, a2 = sum(f.Area for f in fs), sum(f.Area for f in fs2)
        if not fs or abs(a1 - a2) > 1e-3: continue
        top = s.common(Part.makeBox(big, big, bb.ZMax - zs + 1, V(-big / 2, -big / 2, zs)))
        top.translate(V(0, 0, dz))
        return low.fuse([top] + [f.extrude(V(0, 0, dz)) for f in fs]).removeSplitter(), zs, a1
    return None, None, None


def loop_at_z(s, z):
    """The section of s at Z = z: (perimeter, centre) of its one loop, or None."""
    big = 5000
    sec = s.section(Part.makePlane(big, big, V(-big / 2, -big / 2, z), V(0, 0, 1)))
    loops = Part.sortEdges(sec.Edges) if sec.Edges else []
    if len(loops) != 1: return None
    w = Part.Wire(loops[0])
    return w.Length, w.BoundBox.Center


def shorten_tube_z(s, zs_candidates, dz, d):
    """A tube or cable with a vertical stretch: find zs where the sections at zs and zs + dz are each one loop of
    perimeter ~pi d with the same centre (the run is straight up there), cut out zs..zs+dz and move the part below up
    by dz. (new, zs, err, removed volume estimate)"""
    big = 5000; best = None
    head = s.common(Part.makeBox(big, HEAD_Y + big / 2, big, V(-big / 2, -big / 2, -big / 2)))
    rest = s.cut(Part.makeBox(big, HEAD_Y + big / 2, big, V(-big / 2, -big / 2, -big / 2)))
    for zs in zs_candidates:
        a, b = loop_at_z(head, zs), loop_at_z(head, zs + dz)
        if a is None or b is None: continue
        err = max(abs(a[0] - math.pi * d), abs(b[0] - math.pi * d)) / (math.pi * d)
        off = math.hypot(a[1].x - b[1].x, a[1].y - b[1].y)
        score = err + off / d
        if best is None or score < best[0]: best = (score, zs, err, off)
    if best is None: return None, None, None, None
    _, zs, err, off = best
    bb = head.BoundBox
    low = head.common(Part.makeBox(big, big, zs - bb.ZMin + 1, V(-big / 2, -big / 2, bb.ZMin - 1)))
    up = head.common(Part.makeBox(big, big, bb.ZMax - zs - dz + 1, V(-big / 2, -big / 2, zs + dz)))
    low.translate(V(0, 0, dz))
    new = rest.fuse([low, up]).removeSplitter()
    return new, zs, (err, off), low.Volume + up.Volume + rest.Volume


def redrill(s, zlo, zhi, dz):
    """Holes in a bar along Z, within zlo..zhi, moved +dz: the band is rebuilt from the bar's plain section (taken
    just below the band, the same just above it) with the band's voids cut back in dz higher. (new, n voids, area)"""
    big = 5000; bb = s.BoundBox
    def sec(z):
        low = s.common(Part.makeBox(big, big, z - bb.ZMin + 1, V(-big / 2, -big / 2, bb.ZMin - 1)))
        return [f for f in low.Faces if isinstance(f.Surface, Part.Plane) and abs(abs(f.normalAt(0, 0).z) - 1) < 1e-6
                and abs(f.CenterOfMass.z - z) < 1e-6]
    fa, fb = sec(zlo - 2.0), sec(zhi + 2.0)
    if not fa or abs(sum(f.Area for f in fa) - sum(f.Area for f in fb)) > 1e-3: return None, 0, 0.0
    prof = [f.copy() for f in fa]
    for f in prof: f.translate(V(0, 0, zlo - (zlo - 2.0)))
    plain = Part.makeCompound([f.extrude(V(0, 0, zhi - zlo)) for f in prof])
    plain = plain.fuse([]).removeSplitter() if len(prof) > 1 else prof[0].extrude(V(0, 0, zhi - zlo))
    bandbox = Part.makeBox(big, big, zhi - zlo, V(-big / 2, -big / 2, zlo))
    band = s.common(bandbox)
    voids = [v for v in plain.cut(band).Solids if v.Volume > 0.01]
    if not voids: return s, 0, sum(f.Area for f in fa)
    moved = [v.translated(V(0, 0, dz)) for v in voids]
    if any(v.BoundBox.ZMax > zhi - 1e-6 for v in moved): return None, len(voids), 0.0
    new = s.cut(bandbox).fuse(plain.cut(moved)).removeSplitter()
    return new, len(voids), sum(f.Area for f in fa)


def move_z(o, dz):
    par = o.getParentGeoFeatureGroup()
    pg = linkgeo.gplace(par) if par is not None else FreeCAD.Placement()
    o.Placement = pg.inverse().multiply(FreeCAD.Placement(V(0, 0, dz), FreeCAD.Rotation())).multiply(pg).multiply(o.Placement)


def main(p):
    m = p.open(SRC); doc = m.doc
    par = linkgeo.group_parents(doc.Objects)
    path = {o.Name: linkgeo.group_path(o, par) for o in m.leaves}
    top = {n: (pp + ["", ""])[1] for n, pp in path.items()}
    gp = {n: " / ".join(pp) for n, pp in path.items()}
    box = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    lab = {o.Name: o.Label for o in m.leaves}
    stay = {n for n, l in lab.items() if l.startswith(STAY) or l in STAY_EXACT}
    rails = {n for n, l in lab.items() if l.startswith(RAILS)}
    tubes = {n for n, l in lab.items() if l.startswith(TUBES)}
    cables = {n for n, l in lab.items() if l.startswith(CABLES)}
    belts = {n for n, l in lab.items() if l.startswith(BELTS)}
    special = tubes | cables | rails
    # ---- STEP 1 sets (lite-78's)
    front = {n for n in lab if n not in stay | special
             and (box[n].YMax <= FRONT_Y or any(k in top[n] for k in FRONT_GROUPS))}
    cross = {n for n in lab if n not in front | stay | belts | special and box[n].YMin < FRONT_Y}
    # ---- STEP 2 sets
    def rides(n):
        if n in tubes | cables: return False
        pp = path[n]
        if any(any(g in x for g in RAISE_GROUPS) for x in pp[1:]): return True
        if RAISE_FRAME_SUB in pp[1:]: return True
        if lab[n].startswith(RAISE_LABELS): return True
        if any(FASTENERS in x for x in pp[1:]) and any(FRAME in x for x in pp) and lab[n].startswith("M5"):
            b = box[n]
            return (b.ZMin >= GANTRY_Z[0] - 6 and b.ZMax <= GANTRY_Z[1] + 6) or DOCKBAR_ZONE.isInside(b)
        return False
    raise_ = {n for n in lab if rides(n)}
    posts = {n for n, l in lab.items() if l in POSTS}
    rearv = {n for n, l in lab.items() if l == REAR_VERTICAL and "Verticals" in gp[n] and abs(box[n].ZMax - GANTRY_Z[0]) < TOL}
    zbars = posts | rearv
    jscrews = [n for n in raise_ if any(FASTENERS in x for x in path[n][1:]) and lab[n].startswith("M5x")]
    redr = {}
    for n in lab:
        if VERTICALS not in gp[n] or n in zbars: continue
        hit = [k for k in jscrews if box[n].intersect(box[k])]
        if hit: redr[n] = (min(box[k].ZMin for k in hit) - 8.0, max(box[k].ZMax for k in hit) + DZ + 8.0)
    p.log(f"   uprights the riding joint screws pass through, re-drilled +{DZ:g}: "
          f"{ {lab[n]: (round(a, 1), round(b, 1)) for n, (a, b) in redr.items()} }")
    p.log(f"{len(m.leaves)} leaves. STEP 1 (front -{DY:g}): {len(front)} move, {len(cross)} spliced, {len(belts)} belts, "
          f"{len(rails)} rails move -{DY / 2:g}, {len(tubes)} tubes + {len(cables)} cables spliced; stay by name "
          f"{sorted(lab[n] for n in stay)}")
    for n in sorted(cross, key=lambda n: lab[n]): p.log(f"   splice Y: {lab[n]} [{top[n]}] Y {box[n].YMin:.1f}..{box[n].YMax:.1f}")
    p.log(f"STEP 2 (gantry +{DZ:g}): {len(raise_)} ride; Z bars spliced: {sorted(lab[n] for n in zbars)}")
    groups = {}
    for n in raise_: groups.setdefault(top[n] if top[n] else "(root)", []).append(n)
    for g, ns in sorted(groups.items()): p.log(f"   rides: {len(ns):4d} in {g}")
    fz = sorted(lab[n] for n in raise_ if any(FASTENERS in x for x in path[n][1:]))
    p.log(f"   frame screws that ride ({len(fz)}): {fz}")
    # what stays in the gantry's band over the chamber: printed for review
    band = sorted((round(box[n].ZMin, 1), lab[n][:50], top[n][:30]) for n in lab
                  if n not in raise_ | special | zbars and box[n].ZMax > 405 and box[n].ZMin < 560
                  and box[n].XMax > -480 and box[n].XMin < -10 and box[n].YMax > -90 and box[n].YMin < 480)
    p.log(f"   in the gantry's Z band over the chamber but staying ({len(band)}): {band[:60]}")
    p.check(len(rails) == 2, f"two 490 Y rails ({sorted(lab[n] for n in rails)})")
    p.check(len(belts) == 2, f"two belts ({len(belts)})")
    p.check(len(tubes) == 5 and len(cables) == 5, f"five tubes and five cables ({len(tubes)}, {len(cables)})")
    p.check(len(posts) == 2 and len(rearv) == 1, f"2 Z posts and the rear vertical ({sorted(lab[n] for n in zbars)})")
    p.check(not (zbars & (front | cross)), "the Z bars aren't touched by step 1")
    nose = [lab[n] for n in raise_ if n in cross and not lab[n].startswith("2040 (3)")]
    p.log(f"   riders also spliced in Y: {sorted(lab[n] for n in raise_ & cross)} (unexpected: {nose})")
    p.check(not nose, f"only the gantry side bars are both spliced and raised ({nose})")
    allmoved = front | cross | belts | special | raise_ | zbars | set(redr)
    att = [lab[n] for n in allmoved if getattr(doc.getObject(n), "MapMode", "Deactivated") not in ("Deactivated", None)]
    p.check(not att, f"no moved or spliced leaf is attached: {att[:5]}")
    links = [o for o in m.leaves if o.TypeId == "App::Link"]
    tgt_of = {o.Name: linkgeo.link_target(o).Name for o in links}
    reshaped = cross | belts | tubes | cables | zbars | set(redr)
    keep = sorted(l for l, t in tgt_of.items() if t in reshaped and l not in reshaped)
    p.log(f"   {len(keep)} unchanged links share a reshaped shape, get their own copy first: {sorted(lab[l] for l in keep)}")
    if p.errs: return p.finish([])
    # ---- collision baseline: everything this pass touches against the rest (lite-79)
    env = {n for n, l in lab.items() if "envelope" in l}
    watched = allmoved - env
    # parts that move together can't change against each other: riders vs non-riders, front vs non-front
    def skip_of(n, front_set, raise_set):
        s = set(env) | {n}
        if n in raise_set: s |= raise_set
        elif n in front_set: s |= front_set
        return s
    base_hits, nc = l78.overlaps(p, m, [(lab[n], m.shapes[n], n) for n in watched],
                                 lambda n: skip_of(n, front - raise_, raise_))
    p.log(f"collision baseline (lite-79): {nc} pairs, {len(base_hits)} overlaps")
    mounts = {k: [o for o in m.leaves if o.Label.startswith(k)] for k in (FRONT_MOUNT, REAR_MOUNT)}
    fm0 = min(m.shapes[o.Name].BoundBox.YMax for o in mounts[FRONT_MOUNT])
    rm0 = min(m.shapes[o.Name].BoundBox.YMin for o in mounts[REAR_MOUNT])
    rail_gaps0 = {lab[n]: (box[n].YMin - fm0, rm0 - box[n].YMax) for n in rails}
    p.log(f"rails before: gaps to the front / rear mounts {rail_gaps0}")
    vols0 = {n: m.shapes[n].Volume for n in reshaped}
    renamed = {}
    for l in keep: renamed[l] = l78.unlink(doc, doc.getObject(l), m.shapes[l]).Name
    cur = lambda n: doc.getObject(renamed.get(n, n))
    def set_shape(n, new):
        o = cur(n)
        if o.TypeId == "App::Link": renamed[n] = l78.unlink(doc, o, new).Name
        else: o.Shape = l78.to_local(o, new)
    # ==== STEP 1: front -3
    for n in front: l78.move_global(cur(n), -DY)
    for n in rails: l78.move_global(cur(n), -DY / 2)
    spliced = {}
    shapes1 = {}
    for n in sorted(cross, key=lambda n: lab[n]):
        new, ys, area = l78.splice_multi(m.shapes[n], SPLICE_Y, DY)
        if new is None: p.check(False, f"splice {lab[n]}: no clean section"); continue
        spliced[n] = (ys, area, len(m.shapes[n].Solids)); set_shape(n, new)
    for n in sorted(belts, key=lambda n: lab[n]):
        new, cuts = l78.splice_belt(m.shapes[n], BELT_Y, DY, l78.BELT_COPY)
        if new is None: p.check(False, f"belt {lab[n]}: no clean cut"); continue
        p.log(f"   belt {lab[n]}: strands spliced at Y {cuts}"); set_shape(n, new); shapes1[n] = new
    tube_y = {}
    for n in sorted(tubes | cables, key=lambda n: lab[n]):
        r = l78.splice_tube(m.shapes[n], TUBE_Y, DY, TUBE_D if n in tubes else CABLE_D)
        new, ys, area, err = r[:4]
        if new is None: p.check(False, f"splice {lab[n]}: no single round section on its Y run"); continue
        tube_y[n] = (ys, area, err, r[4]); shapes1[n] = new
    cut_lo = min(v[0] for v in tube_y.values()) if tube_y else 0.0
    ties = {n for n in lab if RUN_GROUP in gp[n] and n not in tubes | cables | front and box[n].YMax <= cut_lo}
    p.log(f"   {len(ties)} parts on the tube + cable runs in front of Y {cut_lo:g} move -{DY:g} with them")
    for n in ties: l78.move_global(cur(n), -DY)
    # ==== STEP 2: gantry +10
    for n in raise_: move_z(cur(n), DZ)
    zties = set()
    zspl = {}
    for n in sorted(zbars, key=lambda n: lab[n]):
        new, zs, area = splice_z(m.shapes[n], tuple(float(z) for z in range(100, 400, 5)), DZ)
        if new is None: p.check(False, f"Z splice {lab[n]}: no clean section"); continue
        zspl[n] = (zs, area, len(m.shapes[n].Solids)); set_shape(n, new)
    redone = {}
    for n, (zlo, zhi) in sorted(redr.items(), key=lambda kv: lab[kv[0]]):
        new, nv, area = redrill(m.shapes[n], zlo, zhi, DZ)
        if new is None: p.check(False, f"re-drill {lab[n]}: no clean section round Z {zlo:.1f}..{zhi:.1f}"); continue
        if n in front: new = new.translated(V(0, -DY, 0))     # a front upright already moved -3 in step 1
        redone[n] = (nv, zlo, zhi, len(m.shapes[n].Solids)); set_shape(n, new)
    tube_z = {}
    for n in sorted(tube_y, key=lambda n: lab[n]):
        d = TUBE_D if n in tubes else CABLE_D
        new, zs, err, vol = shorten_tube_z(shapes1[n], TUBE_Z, DZ, d)
        if new is None: p.check(False, f"{lab[n]}: no vertical stretch to shorten"); continue
        tube_z[n] = (zs, err, vol); set_shape(n, new)
    # zip ties on the tubes' and cables' rise, below the cut, go up with the head end
    zcut = min((v[0] for v in tube_z.values()), default=0.0)
    zties = {n for n in lab if RUN_GROUP in gp[n] and lab[n].startswith("Zip tie") and n not in raise_
             and box[n].ZMax <= zcut}
    p.log(f"   {len(zties)} zip ties below the tubes' Z cut (Z {zcut:g}) move +{DZ:g}: {sorted(lab[n] for n in zties)}")
    for n in zties: move_z(cur(n), DZ)
    doc.recompute()
    m.refresh()
    # ---- after
    now = {o.Name: m.shapes[o.Name].BoundBox for o in m.leaves}
    for old, new in renamed.items(): now[old] = now[new]; m.shapes[old] = m.shapes[new]
    def same(a, b, dy=0.0, dz=0.0):
        return all(abs(x - y) <= TOL for x, y in zip((a.XMin, a.YMin + dy, a.ZMin + dz, a.XMax, a.YMax + dy, a.ZMax + dz),
                                                      (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)))
    exp = {}
    for n in lab:
        dy = -DY if n in front | ties else (-DY / 2 if n in rails else 0.0)
        dz = DZ if n in raise_ | zties else 0.0
        exp[n] = (dy, dz)
    plain = [n for n in lab if n not in reshaped]
    bad = [f"{lab[n]} {exp[n]}" for n in plain if n not in now or not same(box[n], now[n], *exp[n])]
    p.check(not bad, f"{len(plain)} leaves moved exactly as planned (front -{DY:g}, rails -{DY / 2:g}, riders +{DZ:g}, "
                     f"the rest unchanged): {len(bad)} not: {bad[:6]}")
    for n, (ys, area, nsol) in spliced.items():
        s = m.shapes[n]; b = s.BoundBox; want = vols0[n] + area * DY; dz = exp[n][1]
        ok = (s.isValid() and len(s.Solids) == nsol and abs(b.YMin - (box[n].YMin - DY)) < TOL
              and abs(b.YMax - box[n].YMax) < TOL and abs(b.ZMin - box[n].ZMin - dz) < TOL
              and abs(s.Volume - want) <= max(1.0, 1e-5 * want))
        p.check(ok, f"spliced {lab[n]} at Y {ys:g}: Y {b.YMin:.2f}..{b.YMax:.2f} (was {box[n].YMin:.2f}..{box[n].YMax:.2f}), "
                    f"Z +{b.ZMin - box[n].ZMin:.2f}, solids {len(s.Solids)}/{nsol}, vol {s.Volume:.0f} (want {want:.0f})")
    for n in belts:
        s = m.shapes[n]
        p.check(s.isValid() and abs(s.BoundBox.YMin - (box[n].YMin - DY)) < TOL and abs(s.BoundBox.ZMin - box[n].ZMin - DZ) < TOL,
                f"belt {lab[n]}: valid {s.isValid()}, Y {s.BoundBox.YMin:.2f}..{s.BoundBox.YMax:.2f}, Z +{s.BoundBox.ZMin - box[n].ZMin:.2f}")
    for n, (zs, area, nsol) in zspl.items():
        s = m.shapes[n]; b = s.BoundBox; want = vols0[n] + area * DZ
        ok = (s.isValid() and len(s.Solids) == nsol and abs(b.ZMin - box[n].ZMin) < TOL and abs(b.ZMax - box[n].ZMax - DZ) < TOL
              and abs(s.Volume - want) <= max(1.0, 1e-5 * want))
        p.check(ok, f"Z bar {lab[n]} spliced at Z {zs:g}: Z {b.ZMin:.2f}..{b.ZMax:.2f}, {b.ZLength:.2f} long "
                    f"(want 440), solids {len(s.Solids)}/{nsol}, vol {s.Volume:.0f} (want {want:.0f})")
        p.check(abs(b.ZLength - 440.0) < TOL, f"{lab[n]}: 440 long ({b.ZLength:.2f})")
    for n, (nv, zlo, zhi, nsol) in redone.items():
        s_ = m.shapes[n]
        p.check(s_.isValid() and len(s_.Solids) == nsol and same(box[n], now[n], -DY if n in front else 0.0)
                and abs(s_.Volume - vols0[n]) <= max(0.5, 1e-6 * vols0[n]),
                f"re-drilled {lab[n]}: {nv} hole(s) in Z {zlo:.1f}..{zhi:.1f} moved +{DZ:g}; valid {s_.isValid()}, "
                f"box moved as planned {same(box[n], now[n], -DY if n in front else 0.0)}, vol {vols0[n]:.1f} -> {s_.Volume:.1f}")
    gbars = [n for n in raise_ if RAISE_FRAME_SUB in path[n][1:]]
    for n in zbars:
        d = min(m.shapes[n].distToShape(m.shapes[g])[0] for g in gbars)
        p.check(d < TOL, f"{lab[n]}: its top meets a gantry bar (gap {d:.4f})")
    for n, (ys, area, err, pieces) in tube_y.items():
        zs, (zerr, off), zvol = tube_z.get(n, (None, (9, 9), 0))
        s = m.shapes[n]; b = s.BoundBox
        want = pieces + area * DY
        # Y splice: + section x 3; Z cut: the 10 mm removed is (pieces after the Y splice) - (pieces kept)
        p.check(s.isValid() and len(s.Solids) == 1 and err < 0.01 and zerr < 0.02 and off < 0.2,
                f"{lab[n][:32]}: Y cut at {ys:g} ({100 * err:.2f} % off pi d); Z cut {zs}..+{DZ:g} "
                f"({100 * zerr:.2f} % off pi d, centres {off:.3f} apart); Y {b.YMin:.2f}..{b.YMax:.2f} "
                f"(was {box[n].YMin:.2f}..{box[n].YMax:.2f}), Z {b.ZMin:.2f}..{b.ZMax:.2f} (was {box[n].ZMin:.2f}..{box[n].ZMax:.2f}); "
                f"vol {s.Volume:.0f} (Y-spliced {want:.0f}, after the Z cut {zvol:.0f})")
        p.check(abs(b.YMax - box[n].YMax) < TOL and abs(b.ZMax - box[n].ZMax) < TOL,
                f"{lab[n][:32]}: the roof end stays (Y max {b.YMax:.2f}, Z max {b.ZMax:.2f})")
    fm1 = min(m.shapes[o.Name].BoundBox.YMax for o in mounts[FRONT_MOUNT])
    rm1 = min(m.shapes[o.Name].BoundBox.YMin for o in mounts[REAR_MOUNT])
    for n in rails:
        b = m.shapes[n].BoundBox; g = (b.YMin - fm1, rm1 - b.YMax)
        p.check(abs(b.YLength - 490.0) < TOL and abs(g[0] - g[1]) < TOL and min(g) > 0,
                f"rail {lab[n][:16]}: Y {b.YMin:.2f}..{b.YMax:.2f}, {g[0]:.2f} from the front mount and {g[1]:.2f} from the rear")
    noz = [o for o in m.leaves if o.Label.startswith("TL-dragon-ace-MZE nozzle")]
    tips = sorted({round(m.shapes[o.Name].BoundBox.ZMin, 2) for o in noz})
    tips0 = sorted({round(box[o.Name].ZMin, 2) for o in noz})
    p.check(len(noz) == 5 and len(tips) == 1 and abs(tips[0] - tips0[0] - DZ) < 0.01, f"5 nozzles, one tip Z: {tips0} -> {tips}")
    # COLLISIONS vs lite-79
    raise_now = {renamed.get(n, n) for n in raise_}; front_now = {renamed.get(n, n) for n in front - raise_}
    names = [renamed.get(n, n) for n in watched]
    hits1, nc1 = l78.overlaps(p, m, [(lab[n], m.shapes[renamed.get(n, n)], renamed.get(n, n)) for n in watched],
                              lambda n: skip_of(n, front_now, raise_now))
    new_hits = sorted(hits1 - base_hits - {(b, a) for a, b in base_hits})
    gone_hits = sorted(base_hits - hits1)
    p.log(f"collision check: {nc1} pairs, {len(hits1)} overlaps now, {len(base_hits)} in lite-79; gone {gone_hits[:8]}")
    p.check(not new_hits, f"COLLISIONS: no overlap lite-79 didn't have ({len(new_hits)} new: {new_hits[:10]})")
    p.dump(dict(dy=DY, dz=DZ, front=len(front), raised=len(raise_), spliced_y={lab[n]: v[0] for n, v in spliced.items()},
                spliced_z={lab[n]: v[0] for n, v in zspl.items()},
                tubes={lab[n]: dict(y_cut=tube_y[n][0], z_cut=tube_z.get(n, (None,))[0]) for n in tube_y},
                nozzle_tip_z=tips, rails={lab[n]: [m.shapes[n].BoundBox.YMin, m.shapes[n].BoundBox.YMax] for n in rails},
                collisions=dict(now=len(hits1), lite79=len(base_hits), new=new_hits, gone=gone_hits)))
    return p.finish([(doc, DST)])


if not os.environ.get("LITE80_AS_LIB"): litelib.Pass("lite80_raise10_front3").run(main)
