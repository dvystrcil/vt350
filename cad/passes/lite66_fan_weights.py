# GUI pass: vt350-lite-65 -> vt350-lite-66   (headless = dry run, never saves)   vt350#60
# The fans get a weight. They were FreeCAD's weightless Default: each head's two Vindr Berserker 4010B blowers and its
# 2510 hotend fan. Neither maker's weight is published, so the cards use a same-size, same-type fan's (owner,
# 2026-11-17): 15 g a blower, 6.8 g the 2510 (cad/materials/bought.json gives the sources). Each is one solid that
# every head links to (Blower_4010: 10 blowers; A4Tv035: 5 fans), so the card goes on those two solids. No geometry.
# The material cards are registered before the model opens (else every part reopens as Default; LESSONS.md).
# Checks (refuses to save on any):
#  - both cards found, with a density; one target per fan, a Part::Feature on Default, its volume bought.json's;
#  - 10 blowers and 5 fans link to them, one blower pair and one fan in each of the 5 heads;
#  - afterwards: each blower weighs 15 g and each fan 6.8 g; no other part's material changed; every solid's box,
#    the count and (GUI) each fan's colour unchanged.
import FreeCAD, json, os, re, sys
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-65.FCStd", f"{MODELS}/vt350-lite-66.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
BLOWER, FAN = "Bought Vindr Berserker 4010B blower", "Bought 2510 hotend fan"
LABELS = {BLOWER: re.compile(r"^Vindr Berserker 4010B blower [LR] "), FAN: re.compile(r"^2510 Fan\d*$")}
COUNT = {BLOWER: 10, FAN: 5}
VOL_TOL = 1e-3               # relative: the modelled volume against bought.json
MASS_TOL = 0.01              # g


def mat_name(o):
    sm = getattr(linkgeo.link_target(o), "ShapeMaterial", None)
    return sm.Name if sm is not None else None


def density(o):              # g/mm3, None for Default / none
    sm = getattr(linkgeo.link_target(o), "ShapeMaterial", None)
    if sm is None or sm.Name == "Default": return None
    m = re.match(r"([0-9.eE+-]+) kg/mm\^3", sm.PhysicalProperties.get("Density", ""))
    return float(m.group(1)) * 1000 if m else None


def appearance(o):           # what the GUI draws: the target's, unless the link overrides (LESSONS.md)
    vo = getattr(linkgeo.link_target(o), "ViewObject", None)
    if vo is None or not hasattr(vo, "ShapeAppearance"): return None
    return [(tuple(a.DiffuseColor), round(a.Transparency, 6)) for a in vo.ShapeAppearance]


def main(p):
    mm = matlib.use_dir(CARDS)
    bought = {b["name"]: b for b in json.load(open(os.path.join(CARDS, "bought.json")))["parts"]}
    cards = {}
    for n in (BLOWER, FAN):
        try: cards[n] = matlib.card(mm, n)
        except Exception as e: p.check(False, f"card {n!r}: {e}"); continue
        p.check(bool(cards[n].PhysicalProperties.get("Density")), f"card {n!r} has a density")
    pr = p.open(SRC); doc = pr.doc
    if p.errs: return p.finish([])
    P = {o.Name: [g.Label for g in o.InListRecursive] for o in pr.leaves}
    leaves, target = {}, {}
    for n in (BLOWER, FAN):
        leaves[n] = [o for o in pr.leaves if LABELS[n].match(o.Label)]
        tg = {linkgeo.link_target(o).Name for o in leaves[n]}
        p.check(len(leaves[n]) == COUNT[n] and len(tg) == 1,
                f"{n}: {COUNT[n]} parts, one target ({len(leaves[n])}, {sorted(tg)})")
        if len(tg) != 1: continue
        t = target[n] = doc.getObject(tg.pop())
        heads = sorted({g for o in leaves[n] for g in P[o.Name] if g in ("Left Toolhead", "Right Toolhead") or g.startswith("Toolhead slot")})
        p.check(len(heads) == 5, f"{n}: in all 5 heads ({heads})")
        p.check(t.TypeId == "Part::Feature" and mat_name(t) == "Default", f"{n}: {t.Name} is a Part::Feature on Default ({t.TypeId}, {mat_name(t)})")
        v, want = t.Shape.Volume, bought[n]["default_mm3"]
        p.check(abs(v - want) / want < VOL_TOL, f"{n}: volume {v:.1f} mm3 (bought.json {want})")
    if p.errs: return p.finish([])
    mat0 = {o.Name: mat_name(o) for o in pr.leaves}
    look0 = {o.Name: appearance(o) for o in pr.leaves}
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    n0 = len(pr.leaves)
    gui = FreeCAD.GuiUp
    for n, t in target.items():
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        t.ShapeMaterial = cards[n]
        if ap is not None: t.ViewObject.ShapeAppearance = ap          # keep the colour: the card's isn't applied
    doc.recompute(); pr.refresh()
    masses = {}
    for n in (BLOWER, FAN):
        for o in leaves[n]:
            g = pr.shapes[o.Name].Volume * (density(o) or 0)
            masses[o.Label] = round(g, 3)
            p.check(abs(g - bought[n]["mass_g"]) < MASS_TOL, f"{o.Label}: {g:.3f} g (want {bought[n]['mass_g']} g)")
    mine = {o.Name for n in leaves for o in leaves[n]}
    changed = [doc.getObject(k).Label for k, m in mat0.items() if k not in mine and mat_name(doc.getObject(k)) != m]
    p.check(not changed, f"no other part's material changed ({len(changed)}: {changed[:5]})")
    p.check(len(pr.leaves) == n0, f"solids {len(pr.leaves)} (was {n0})")
    moved = [doc.getObject(k).Label for k, b in box0.items()
             if k not in pr.shapes or not pr.shapes[k].BoundBox.isInside(b) or not b.isInside(pr.shapes[k].BoundBox)]
    p.check(not moved, f"every solid's box unchanged ({len(moved)}: {moved[:5]})")
    if gui:
        recol = [doc.getObject(k).Label for k in mine if appearance(doc.getObject(k)) != look0[k]]
        p.check(not recol, f"each fan's colour unchanged ({len(recol)}: {recol[:5]})")
    per_head = round(2 * bought[BLOWER]["mass_g"] + bought[FAN]["mass_g"], 3)
    p.log(f"per head: 2 blowers + 1 fan = {per_head} g")
    p.dump({"cards": {n: target[n].Name for n in target}, "per_head_g": per_head, "masses_g": masses})
    return p.finish([(doc, DST)])


litelib.Pass("lite66_fan_weights").run(main)
