# GUI pass: vt350-lite-58 -> vt350-lite-59   (headless = dry run, never saves)
# vt350#5. The e-box's faces (owner, 2026-11-16 22:30 PST, on the lite-58 renders): TOP and REAR = panels; BOTTOM =
# open, for air; FRONT = "the Voron grille treatment, like the large skirt" (lite-42's hex windows, mesh and badge).
#  - TOP: a 3 mm panel on the e-box's top members, X 30..160, Y -90..520, Z 690..693: the roof panel's plane and
#    front/rear edges, continued over the e-box (the roof panel stops at X 30).
#  - REAR: a 3 mm panel on the rear face, Y 520..523, X 30..146, Z -50..690 (full height, as the left side panel).
#    It stops 1 mm short of the e-box door's hinges, which wrap round the rear-right corner (X 147..176, Y 514..533).
#    The cable channel's two arms (lite-40, Y 520..533) cross this face: the panel is notched round them, 1 mm clear.
#  - Both are made as lite-38 made the printer's: a white core and a 0.2 mm `panel_paint` skin on the outward face
#    ("... paint, outside"); in the GUI they copy the roof panel's look.
#  - FRONT: a white printed grille, Y -93..-90 (flush with the printer door's frame line, as lite-42's skirt walls
#    are flush with the faces), X 30..160, Z -50..690, in lite-42 "tall"'s style: chamfered windows filled with
#    flat-top hexes (19 mm, 3 mm webs), an orange 2 mm mesh plate behind each (6 mm hexes), an orange badge inset in
#    a band. Three windows: two below, split by a rib, and one above the band. The band (Z 400..530) is where both
#    doors' latch hardware crosses the face (the printer door's handle and latch at X 24..51, the e-box door's at
#    X 131..201, Z 406..524): the grille is notched round each, 1 mm clear, and the badge sits between.
#    No corner blocks: both front corners are taken by the doors' latch hardware.
#  - The grille is 740 tall, more than the bed's 350, so it's three pieces split across the rib and under the band:
#    Z -50..195, 195..400, 400..690. Each mesh plate lies inside one piece.
# Checks (refuses to save on any): the e-box frame members where expected; every new part one valid solid; skin +
# core = the panel; nothing new overlaps a lite-58 part (envelopes excepted) or another new part; the notches only in
# the band (front) and round the arms (rear); each grille piece and mesh fits the print area flat; colour roles;
# solids = lite-58 + new parts.
import FreeCAD, Part, os, sys, math
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render")]
import litelib, colours
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-58.FCStd", f"{MODELS}/vt350-lite-59.FCStd"
EXTRAS = "Enclosure extras (lite-16)"
GROUP = "E-box panels and front grille (lite-59)"
ROOF, ROOF_PAINT = "Roof panel (3 mm)", "Roof panel (3 mm) paint, outside"
T, SKIN, CLR, TOL = 3.0, 0.2, 1.0, 1e-3
X0, X1, XI = 30.0, 160.0, 140.0               # e-box: printer's right face, outer members' outer and inner faces
YF, YR = -90.0, 520.0                         # front and rear faces
ZB, ZT = -50.0, 690.0
REAR_X1 = 146.0                               # 1 mm short of the e-box door's hinges (X 147.1)
# front grille, face-local: u = X, v = Z; the wall Y -93..-90, inward +Y
GY0, GY1 = YF - T, YF
WIN_U = (37.0, 133.0)                         # windows inside the opening X 30..140 less the mesh margin + 4
WINDOWS = [(-4.0, 183.0), (207.0, 390.0), (540.0, 640.0)]
SPLITS = [195.0, 400.0]
BAND = (400.0, 530.0)
HEX_F, WEB = 19.0, 3.0                        # lite-42 tall
MESH_F, MESH_WEB, MESH_T, MESH_M = 6.0, 1.6, 2.0, 3.0
BADGE_W, BADGE_H, BADGE_D = 50.0, 100.0, 1.5
LIC = "(printed ABS, vt350, GPL-3.0-or-later)"


def bx(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def prism(pts_uv, w0, w1):
    """A polygon in the front face (u = X, v = Z), extruded across Y from w0 to w1."""
    P = [V(u, w0, v) for u, v in pts_uv]
    return Part.Face(Part.makePolygon(P + [P[0]])).extrude(V(0, w1 - w0, 0))


def chamfered(u0, u1, v0, v1, c):
    return [(u0 + c, v0), (u1 - c, v0), (u1, v0 + c), (u1, v1 - c), (u1 - c, v1), (u0 + c, v1), (u0, v1 - c), (u0, v0 + c)]


def hexes(u0, u1, v0, v1, F, web):
    a = F / math.sqrt(3); du = (F + web) * math.cos(math.radians(30)); dv = F + web
    out, i, u = [], 0, u0 - du
    while u < u1 + du:
        v = v0 - dv + (dv / 2 if i % 2 else 0)
        while v < v1 + dv:
            out.append([(u + a * math.cos(math.radians(60 * k)), v + a * math.sin(math.radians(60 * k))) for k in range(6)])
            v += dv
        u += du; i += 1
    return out


def main(p):
    pr = p.open(SRC); doc = pr.doc
    cmap = colours.load(f"{_REPO}/cad/render/colours.json")
    n0 = len(pr.leaves)
    by = lambda pre: [o for o in pr.leaves if o.Label.startswith(pre)]
    # ---- the e-box frame, measured
    want = {"2020 e-box front outer upright": (XI, X1, YF, YF + 20, ZB, ZT),
            "2040 e-box rear outer upright": (XI, X1, YR - 40, YR, ZB, ZT),
            "2040 e-box outer side rail, top": (XI, X1, -70, 480, ZT - 40, ZT),
            "2040 (2) (new front)": (-520, XI, YF, YF + 20, ZB, -10),
            "4040 (2) one piece": (-520, XI, YR - 40, YR, ZB, -10)}
    for pre, bb in want.items():
        os_ = by(pre)
        b = pr.boxes[os_[0].Name] if len(os_) == 1 else None
        got = (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax) if b else ()
        p.check(len(os_) == 1 and all(abs(g - w) < 0.2 for g, w in zip(got, bb)),
                f"{pre}: {len(os_)} found, box {tuple(round(g, 1) for g in got)} (expected {bb})")
    roof = by(ROOF); roof_paint = [o for o in pr.leaves if o.Label == ROOF_PAINT]
    roof = [o for o in roof if o.Label == ROOF]
    p.check(len(roof) == 1 and len(roof_paint) == 1, f"roof panel core {len(roof)}, paint {len(roof_paint)}")
    rb = pr.boxes[roof_paint[0].Name]
    p.check(abs(rb.ZMax - (ZT + T)) < 0.05 and abs(rb.YMin - YF) < 0.05 and abs(rb.YMax - YR) < 0.05,
            f"roof panel Z ..{rb.ZMax:.2f}, Y {rb.YMin:.1f}..{rb.YMax:.1f}: the top panel continues it")
    env = {o.Name for o in pr.leaves if "envelope" in o.Label}

    def hits(shape, skip=()):
        """[(label, bbox)] of lite-58 parts that overlap shape (envelopes excepted)."""
        sb = shape.BoundBox; out = []
        for o in pr.leaves:
            if o.Name in env or o.Name in skip or not pr.boxes[o.Name].intersect(sb): continue
            try: v = shape.common(pr.shapes[o.Name]).Volume
            except Exception: v = 1.0
            if v > TOL: out.append((o.Label, pr.boxes[o.Name]))
        return out

    grp = doc.addObject("App::DocumentObjectGroup", "Ebox_panels"); grp.Label = GROUP
    next(o for o in doc.Objects if o.Label == EXTRAS).addObject(grp)
    made = []

    def add(name, label, shape, look=None):
        shape = shape.removeSplitter()
        if len(shape.Solids) > 1:
            big = max(shape.Solids, key=lambda s: s.Volume)
            crumbs = [s.Volume for s in shape.Solids if s is not big]
            p.check(sum(crumbs) < 1.0, f"{label[:40]}: crumbs {crumbs[:5]} mm3")
            shape = big
        p.check(shape.isValid() and len(shape.Solids) == 1, f"{label[:48]}: one valid solid ({len(shape.Solids)}), {shape.Volume:.0f} mm3")
        o = doc.addObject("Part::Feature", name); o.Shape = shape; o.Label = label; grp.addObject(o); made.append(o)
        if FreeCAD.GuiUp and look is not None:
            try: o.ViewObject.ShapeAppearance = look.ViewObject.ShapeAppearance
            except Exception: pass
        return o

    # ---- top and rear panels: core + 0.2 mm paint skin on the outward face (lite-38's method)
    def notches(slab, axes, ok_box):
        """Cut a box round every lite-58 part the slab hits, CLR clear in the face's two axes, through its depth.
        ok_box(bbox) must say the hit is one this pass expects to notch round."""
        hs = hits(slab); cuts = []
        sb = slab.BoundBox
        for lab, b in hs:
            p.check(ok_box(b), f"{lab[:50]}: crosses the panel at X {b.XMin:.1f}..{b.XMax:.1f} Y {b.YMin:.1f}..{b.YMax:.1f} "
                               f"Z {b.ZMin:.1f}..{b.ZMax:.1f}: an expected notch")
            lo = [sb.XMin - 1, sb.YMin - 1, sb.ZMin - 1]; hi = [sb.XMax + 1, sb.YMax + 1, sb.ZMax + 1]
            for a in axes:
                lo[a] = (b.XMin, b.YMin, b.ZMin)[a] - CLR; hi[a] = (b.XMax, b.YMax, b.ZMax)[a] + CLR
            cuts.append(bx(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
        return hs, (slab.cut(Part.makeCompound(cuts)) if cuts else slab)

    panels = {
        "top": dict(slab=bx(X0, X1, YF, YR, ZT, ZT + T), axes=(0, 1), inward=V(0, 0, -SKIN), ok=lambda b: False),
        "rear": dict(slab=bx(X0, REAR_X1, YR, YR + T, ZB, ZT), axes=(0, 2), inward=V(0, -SKIN, 0),
                     ok=lambda b: b.YMin >= YR - 0.01 and b.ZMax - b.ZMin < 20 and b.XMax < 120),
    }
    stats = {}
    for nm, d in panels.items():
        hs, P = notches(d["slab"], d["axes"], d["ok"])
        stats[nm] = {"notched_round": [h[0][:40] for h in hs]}
        inner = P.copy(); inner.translate(d["inward"])
        skin, core = P.cut(inner).removeSplitter(), P.common(inner).removeSplitter()
        p.check(skin.isValid() and core.isValid() and abs(skin.Volume + core.Volume - P.Volume) < TOL and skin.Volume < 0.1 * P.Volume,
                f"{nm} panel: skin {skin.Volume:.1f} + core {core.Volume:.1f} = {P.Volume:.1f} mm3")
        lab = f"E-box {nm} panel (3 mm)"
        add("Ebox_panel", lab, core, roof[0] if roof else None)
        add("Ebox_panel_paint", f"{lab} paint, outside", skin, roof_paint[0] if roof_paint else None)
        b = P.BoundBox; stats[nm]["box"] = [round(v, 1) for v in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)]

    # ---- front grille
    wall = bx(X0, X1, GY0, GY1, ZB, ZT)
    in_band = lambda b: b.ZMin >= BAND[0] and b.ZMax <= BAND[1]
    hs, wall = notches(wall, (0, 2), in_band)
    stats["front"] = {"notched_round": sorted({h[0][:40] for h in hs})}
    p.check(len(hs) >= 2, f"front: notched round {len(hs)} door latch parts (both doors')")
    wo, wi = GY0, GY1
    u0, u1 = WIN_U
    holes, meshes = [], []
    for k, (v0, v1) in enumerate(WINDOWS, 1):
        c = min(8.0, (v1 - v0) / 3)
        win = prism(chamfered(u0, u1, v0, v1, c), wo - 1, wi + 1)
        hx = Part.makeCompound([prism(h, wo - 1, wi + 1) for h in hexes(u0, u1, v0, v1, HEX_F, WEB)])
        holes.append(win.common(hx))
        mo = chamfered(u0 - MESH_M, u1 + MESH_M, v0 - MESH_M, v1 + MESH_M, c + MESH_M * 0.4)
        plate = prism(mo, wi, wi + MESH_T)
        inner = prism(chamfered(u0 - MESH_M + 2, u1 + MESH_M - 2, v0 - MESH_M + 2, v1 + MESH_M - 2, c), wi - 1, wi + MESH_T + 1)
        mh = Part.makeCompound([prism(h, wi - 1, wi + MESH_T + 1)
                                for h in hexes(u0 - MESH_M, u1 + MESH_M, v0 - MESH_M, v1 + MESH_M, MESH_F, MESH_WEB)])
        meshes.append((k, plate.cut(inner.common(mh))))
    um, vm = (u0 + u1) / 2, (BAND[0] + BAND[1]) / 2
    bw, bh = BADGE_W, BADGE_H                 # an elongated hexagon, upright: points at top and bottom
    badge = prism([(um, vm - bh / 2), (um + bw / 2, vm - bh / 2 + bw / 2), (um + bw / 2, vm + bh / 2 - bw / 2),
                   (um, vm + bh / 2), (um - bw / 2, vm + bh / 2 - bw / 2), (um - bw / 2, vm - bh / 2 + bw / 2)], wo, wo + BADGE_D)
    grille = wall.cut(Part.makeCompound(holes)).cut(badge)
    cuts = [ZB] + SPLITS + [ZT]
    pieces = []
    for i, (za, zb) in enumerate(zip(cuts, cuts[1:]), 1):
        piece = grille.common(bx(X0 - 1, X1 + 1, GY0 - 1, GY1 + 1, za, zb))
        pieces.append(add("Ebox_grille_panel", f"E-box grille panel {i} of {len(cuts) - 1}, Z {za:.0f}..{zb:.0f} {LIC}", piece))
    for k, m in meshes: add("Ebox_grille_mesh", f"E-box grille mesh {k} {LIC}", m)
    add("Ebox_grille_badge", f"E-box grille badge {LIC}", badge)
    stats["front"].update(windows=WINDOWS, window_u=WIN_U, splits=SPLITS, band=BAND)
    doc.recompute(); pr.refresh()
    mine = {o.Name for o in made}
    # ---- checks
    p.no_overlap([(o.Label, pr.shapes[o.Name]) for o in made], pr,
                 lambda r: f"no new part overlaps a lite-58 part: {len(r.hits)} {r.hits[:8]}", exclude=env | mine)
    for i, a in enumerate(made):
        for b in made[i + 1:]:
            if not pr.boxes[a.Name].intersect(pr.boxes[b.Name]): continue
            v = pr.shapes[a.Name].common(pr.shapes[b.Name]).Volume
            p.check(v < TOL, f"{a.Label[:30]} vs {b.Label[:30]}: {v:.4f} mm3")
    for o in made:
        if not o.Label.startswith("E-box grille"): continue
        flat = pr.shapes[o.Name].copy(); flat.rotate(V(0, 0, 0), V(1, 0, 0), 90)   # printed face down: Z up = Y
        r = p.fits_print_area(flat, f"{o.Label[:40]}: fits the bed flat")
        if "mesh" in o.Label:                   # every mesh lies inside one grille piece's Z span
            b = pr.boxes[o.Name]
            p.check(not any(b.ZMin < z < b.ZMax for z in SPLITS), f"{o.Label[:30]}: Z {b.ZMin:.1f}..{b.ZMax:.1f}, inside one piece")
    def gpath(o):
        r_, q = [], o.getParentGeoFeatureGroup()
        while q is not None: r_.append(q.Label); q = q.getParentGeoFeatureGroup()
        return " / ".join(reversed(r_))
    roles = {}
    for o in made:
        key = " ".join(o.Label.split()[:3]) + (" paint" if "paint, outside" in o.Label else "")
        roles.setdefault(key, set()).add(colours.role_of(cmap, o.Label, gpath(o), "Default"))
    roof_role = colours.role_of(cmap, ROOF, gpath(roof[0]), "Default") if roof else None
    p.check(roles == {"E-box top panel": {roof_role}, "E-box top panel paint": {"panel_paint"},
                      "E-box rear panel": {roof_role}, "E-box rear panel paint": {"panel_paint"},
                      "E-box grille panel": {"printed"}, "E-box grille mesh": {"accent"}, "E-box grille badge": {"accent"}},
            f"roles {roles} (panel cores as the roof's: {roof_role})")
    p.check(len(made) == 4 + 3 + 3 + 1 and len(pr.leaves) == n0 + len(made), f"lite-59 solids: {len(pr.leaves)} (lite-58 {n0} + {len(made)})")
    p.dump({"stats": stats, "volumes_mm3": {o.Label.split(" (")[0]: round(pr.shapes[o.Name].Volume) for o in made}})
    return p.finish([(doc, DST)])


litelib.Pass("lite59_ebox_panels").run(main)
