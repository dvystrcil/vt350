# GUI pass: vt350-lite-62 -> vt350-lite-63   (headless = dry run, never saves)   vt350#60
# Real materials from cad/materials (registered as the Custom library before the model opens). Owner, 2026-11-17:
#  - PET-GF (Ambrosia): the printed parts on each A4Tv2 head, the MadMax tool plates (Plate + Plate Back), and the
#    MadMax carriage (the gantry one and both docks' copies);
#  - PETG Clear (Ambrosia): clear parts, the A4Tv2 "[t]_" (transparent) parts;
#  - ASA (Ambrosia): every other printed part now in ABS (the owner can't print ABS), the "[o]_" LED filter included;
#  - bought parts with a published mass: the Orbiter (each head, ~135 g) and the Beacon (3.5 g), with the effective
#    density cards in cad/materials/Bought (bought.json says how they're made);
#  - NdFeB N52 (datasheet density): every magnet already in the model (the A4Tv2's 6x1.5, the doors' 6x3). The
#    MadMax carriage, plate and dock magnets aren't modelled yet: lite-64 adds them.
# And one colour (owner, 2026-11-17): the Beacon is white. Otherwise no geometry and no colour changes (the cards' own
# appearance is not applied; colours.json roles keep working). A link has no material of its own: its target's is set.
# Checks (refuses to save on any):
#  - every card found in the Custom library, with its density;
#  - each bought part's Default volume and known mass equal bought.json's (its card's density depends on them);
#  - no part is given two cards (a link and its target agree);
#  - afterwards: no ABS left; each head's Orbiter weighs 135 g and the Beacon 3.5 g; each part has its card;
#  - every solid's box unchanged, solid count unchanged; in the GUI, every part's colour and transparency unchanged.
import FreeCAD, os, re, sys, json
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib, linkgeo, matlib
from litelib import MODELS
SRC, DST = f"{MODELS}/vt350-lite-62.FCStd", f"{MODELS}/vt350-lite-63.FCStd"
CARDS = os.path.join(_REPO, "cad/materials")
BOUGHT = json.load(open(os.path.join(CARDS, "bought.json")))["parts"]
PETGF, PETG_CLEAR, ASA = "Ambrosia PET-GF", "Ambrosia PETG Clear", "Ambrosia ASA"
ORBITER, BEACON = "Bought LDO Orbiter v2.5 with motor", "Bought Beacon RevH Normal"
NDFEB = "NdFeB N52 magnet"
BEACON_WHITE = (0.949, 0.949, 0.941)        # #F2F2F0, the white the Ambrosia White card uses (an estimate)
ABS = "ABS-Generic"
HEADS = ("Left Toolhead", "Right Toolhead")   # the two carried heads: their Orbiters are weighed
# every toolhead: the two carried heads and the docked ones ("Toolhead slot 2 (L)" ...), whose parts link to the
# Left head's (lite-52), so a printed part is a toolhead part wherever it appears
ORBITER_GROUP = "Orbiter V2.0 Mockup"
TUBES = ("Bowden Left", "Bowden Right")
PLATE = re.compile(r"^Plate( Back)?(\(Mirror\))?\d*$")      # the MadMax tool plates, in every dock
CARRIAGE = re.compile(r"^COMPOUND\d*$")                         # under a MadMaxCarriage group: the gantry one, the dock copies
BEACON_LABEL = "Beacon RevH Normal"
VOL_TOL = 1e-3               # relative: the bought volumes against bought.json


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
    cards = {}
    for n in (PETGF, PETG_CLEAR, ASA, ORBITER, BEACON, NDFEB):
        try: cards[n] = matlib.card(mm, n)
        except Exception as e: p.check(False, f"card {n!r}: {e}"); continue
        p.check(bool(cards[n].PhysicalProperties.get("Density")), f"card {n!r} has a density")
    if p.errs: return p.finish([])
    pr = p.open(SRC); doc = pr.doc
    n0 = len(pr.leaves)
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, q = set(), par.get(o.Name)
        while q is not None: r.add(q.Label); q = par.get(q.Name)
        return r
    P = {o.Name: path(o) for o in pr.leaves}
    standin = {o.Name for o in pr.leaves if getattr(o, "StandInFor", "")}
    def head(o): return next((h for h in HEADS if h in P[o.Name]), None)
    def any_head(o): return any(g in HEADS or g.startswith("Toolhead slot") for g in P[o.Name])
    def carriage(o): return bool(CARRIAGE.match(o.Label)) and any(g.startswith("MadMaxCarriage") for g in P[o.Name])
    def in_orbiter(o): return any(ORBITER_GROUP in g for g in P[o.Name])
    def card_for(o):
        m, lab = mat_name(o), o.Label
        if lab.startswith(BEACON_LABEL): return BEACON
        tube = lab.startswith(TUBES) or linkgeo.link_target(o).Label.startswith(TUBES)     # the docked heads' links too
        if any_head(o) and in_orbiter(o) and not tube and o.Name not in standin and m == "Default": return ORBITER
        if PLATE.match(lab) or carriage(o): return PETGF
        if "agnet" in lab and not lab.startswith("Magnetic sheet"): return NDFEB
        if m != ABS: return None
        if lab.startswith("[t]_"): return PETG_CLEAR
        if any_head(o) and not lab.startswith("[o]_"): return PETGF
        return ASA
    # what each target gets
    plan, why = {}, {}
    for o in pr.leaves:
        c = card_for(o)
        if c is None: continue
        t = linkgeo.link_target(o)
        if t.Name in plan and plan[t.Name] != c:
            p.check(False, f"{t.Label} ({t.Name}) would get {plan[t.Name]!r} via {why[t.Name]} and {c!r} via {o.Label} ({o.Name})")
        plan[t.Name], why[t.Name] = c, f"{o.Label} ({o.Name})"
    cars = [o for o in pr.leaves if carriage(o)]
    p.check(any("Carriage (1)" in P[o.Name] for o in cars) and len(cars) >= 3,
            f"the carriages: {len(cars)} ({', '.join(f'{o.Label} in {sorted(P[o.Name])[0]}' for o in cars)})")
    plates = [o for o in pr.leaves if PLATE.match(o.Label)]
    p.check(len(plates) >= 4, f"the tool plates: {len(plates)} ({', '.join(sorted(o.Label for o in plates))})")
    count = {}
    for c in plan.values(): count[c] = count.get(c, 0) + 1
    for c, n in sorted(count.items()): p.log(f"{c}: {n} part(s) (targets; links follow)")
    # the bought parts' measured volumes against bought.json
    spec = {b["name"]: b for b in BOUGHT}
    def bought_items(name, h=None):
        return [o for o in pr.leaves if card_for(o) == name and (h is None or head(o) == h)]
    groups = [(ORBITER, h) for h in HEADS] + [(BEACON, None)]
    items0 = {(name, h): [o.Name for o in bought_items(name, h)] for name, h in groups}   # before: card_for reads Default
    for name, h in groups:
        items = bought_items(name, h)
        b = spec[name]
        dv = sum(pr.shapes[o.Name].Volume for o in items)
        known = 0.0
        if name == ORBITER:
            known = sum(pr.shapes[o.Name].Volume * (density(o) or 0) for o in pr.leaves
                        if head(o) == h and in_orbiter(o) and o.Label not in TUBES and o.Name not in standin and mat_name(o) != "Default")
        p.check(len(items) == b["default_solids"] and abs(dv - b["default_mm3"]) <= VOL_TOL * b["default_mm3"]
                and abs(known - b["known_g"]) < 0.01,
                f"{name} {h or ''}: {len(items)} Default solids, {dv:.2f} mm3, {known:.3f} g known "
                f"(bought.json: {b['default_solids']}, {b['default_mm3']}, {b['known_g']})")
    p.check(not any(mat_name(o) == ABS and card_for(o) is None for o in pr.leaves), "every ABS part has a card")
    if p.errs: return p.finish([])
    # apply
    look0 = {o.Name: appearance(o) for o in pr.leaves}
    box0 = {n: s.BoundBox for n, s in pr.shapes.items()}
    gui = FreeCAD.GuiUp
    for tn, c in plan.items():
        t = doc.getObject(tn)
        ap = list(t.ViewObject.ShapeAppearance) if gui and hasattr(t.ViewObject, "ShapeAppearance") else None
        t.ShapeMaterial = cards[c]
        if ap is not None:                                             # keep the colour: the card's isn't applied
            if c == BEACON:                                            # ... except the Beacon: white (owner)
                for a in ap: a.DiffuseColor = BEACON_WHITE + (1.0,) if len(a.DiffuseColor) == 4 else BEACON_WHITE
            t.ViewObject.ShapeAppearance = ap
    doc.recompute(); pr.refresh()
    # after
    p.check(len(pr.leaves) == n0, f"solids {len(pr.leaves)} (was {n0})")
    moved = [n for n, s in pr.shapes.items() if not s.BoundBox.isInside(box0[n].Center) or
             max(abs(a - b) for a, b in zip((s.BoundBox.XMin, s.BoundBox.YMin, s.BoundBox.ZMin, s.BoundBox.XMax, s.BoundBox.YMax, s.BoundBox.ZMax),
                                             (box0[n].XMin, box0[n].YMin, box0[n].ZMin, box0[n].XMax, box0[n].YMax, box0[n].ZMax))) > 1e-9]
    p.check(not moved, f"every solid's box unchanged ({len(moved)} changed: {moved[:5]})")
    left = [o.Label for o in pr.leaves if mat_name(o) == ABS]
    p.check(not left, f"no ABS left ({len(left)}: {left[:5]})")
    wrong = [f"{o.Label}: {mat_name(o)}" for o in pr.leaves if linkgeo.link_target(o).Name in plan
             and mat_name(o) != plan[linkgeo.link_target(o).Name]]
    p.check(not wrong, f"each part has its card ({len(wrong)} not: {wrong[:5]})")
    # a bought card belongs only on that part's own solids: a link elsewhere to one of them would weigh it twice
    mine = {n for v in items0.values() for n in v}
    stray = [f"{o.Label} ({o.Name}, {o.TypeId}, in {sorted(P[o.Name])[:2]})" for o in pr.leaves
             if mat_name(o) in (ORBITER, BEACON) and o.Name not in mine and not any(g.startswith("Toolhead slot") for g in P[o.Name])]
    p.check(not stray, f"no other part on the carried heads or the carriage has a bought card ({len(stray)}: {stray[:6]})")
    masses = {}
    for name, h in groups:
        b = spec[name]
        g = sum(pr.shapes[n].Volume * density(doc.getObject(n)) for n in items0[(name, h)])
        if name == ORBITER: g += b["known_g"]
        masses[f"{name} {h or ''}".strip()] = round(g, 3)
        p.check(abs(g - b["mass_g"]) < 0.05, f"{name} {h or ''}: {g:.3f} g (published {b['mass_g']} g)")
    if gui:
        bea = [o for o in pr.leaves if o.Label.startswith(BEACON_LABEL)]
        changed = [o.Label for o in pr.leaves if appearance(o) != look0[o.Name] and o not in bea]
        p.check(not changed, f"every other part's colour unchanged ({len(changed)} changed: {changed[:5]})")
        white = all(max(abs(x - y) for x, y in zip(c[:3], BEACON_WHITE)) < 2e-3 for o in bea for c, _ in appearance(o))
        p.check(bool(bea) and white, f"the Beacon is white: {[appearance(o) for o in bea]}")
    else:
        p.log("colours: not checked headless (no view objects); the GUI run checks them")
    p.dump({"cards": count, "bought_g": masses})
    return p.finish([(doc, DST)])


litelib.Pass("lite63_materials").run(main)
