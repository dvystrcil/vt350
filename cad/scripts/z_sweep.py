# #82: the bed's Z travel, both ends, measured on the SAVED model. Headless, read-only, never saves:
#   VT350_MODEL=/home/dan/Documents/VT350/vt350-lite-29.FCStd $APP freecadcmd cad/scripts/z_sweep.py
# Log: $VT350_WORK/logs/z_sweep.log (+ z_sweep.json), ending "z_sweep: done (read-only, nothing saved)" when every
# check passed. Its z_lower_limit_mm= / z_upper_limit_mm= / print_height_mm= / klipper_position_max_mm= /
# z_negative_limit_mm= / z_travel_mm= lines are what refresh.py reports.
#
# Moving group: the bed, exactly as sweep_toolhead.py classifies it (its plan() runs here, on the same document).
# Everything else is fixed, plus the solids of every document an envelope names ("Filter envelope (contents in
# vt350-filter-3.FCStd)" -> that file, beside the model); the envelope boxes themselves are left out, as are
# sweep_toolhead's exclusions (the docks' carriage copies, the Z drag chain, whose links are posed for one bed height).
#
#  lower end: the bed moves down. Limit = the first contact with a fixed solid, or a Z block's bottom end reaching
#             its rail's bottom end, whichever comes first.
#  upper end: the bed moves up with each head carried over the print centre (sweep_toolhead's "centre, top" pose:
#             gantry, carriage and that head translated; its own bowden tube and the belts left out), against
#             everything. The first touch must be the magnet sheet on that head's nozzle; anything else is a FAIL.
#             With nothing over the bed (model pose, heads docked) the mechanical stop is logged as well.
#  full travel (AC6): the bed moves up with the toolhead parked at each dock (sweep_toolhead's "dock pickup, top":
#             gantry and carriage translated, both heads docked, belts left out). The mechanical top is the higher
#             parking's first touch, or a Z block's top end reaching its rail's, whichever comes first. In Klipper's
#             terms Z0 is the nozzle on the magnet sheet, so the lower stop is position_max and the top is negative Z.
#
# Contact = common() volume > contact.TOL, scanned every contact.STEP mm and bisected to contact.EPS (contact.py).
# Rail ends, the plate top and the magnet top come from vertical Part.makeLine ray probes (litelib._t_zspan).
# Bounding boxes only pick the pairs that can meet and bound each pair's search window (contact.window); no limit
# comes from a box. A pair already overlapping at the model pose (a nut on its lead screw) is listed, not a limit.
# The heavy work goes through litelib Pass.map (_t_contact, _t_zspan), so a parallel run is bit-identical to serial.
import html, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contact

MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-29.FCStd")
ENVELOPE = re.compile(r"^.+ envelope \(contents in ([^()]+\.FCStd)\)$")
PLATE, MAGNET, NOZZLE = "LDO 350 build plate", "Magnetic sheet", "E3D v6 HotEnd - Nozzle"
BLOCK_GROUP, BLOCK_PART, RAIL_GROUP = "MGN9H (", "MGN9H - Carriage", "MGN9 - 400mm"
RAY_GRID = 0.5          # mm between ray probes over a block or rail footprint
CARRIED_POSE = "centre, top"
PARKED_POSE = "dock pickup, top"   # sweep_toolhead's: gantry and carriage at a head's own dock, both heads docked (#82 AC6)


# ------------------------------------------------------------------------------------------- plain python (tested)
def envelope_docs(labels):
    """The document file names the envelope labels name, once each, in order."""
    out = []
    for l in labels:
        m = ENVELOPE.match(l)
        if not m: continue
        d = m.group(1)
        if os.path.basename(d) != d or d.startswith(".."): raise ValueError(f"envelope {l!r}: {d!r} is not a file name")
        if d not in out: out.append(d)
    return out


def envelope_docs_of(path):
    """envelope_docs() of a saved .FCStd, read from its Document.xml (no FreeCAD)."""
    with zipfile.ZipFile(path) as z:
        try: xml = z.read("Document.xml").decode("utf-8")
        except KeyError: raise ValueError(f"{path}: no Document.xml")
    labels = re.findall(r'<Property name="Label" type="App::PropertyString"[^>]*>\s*<String value="([^"]*)"/>', xml)
    return envelope_docs(html.unescape(l) for l in labels)


def envelope_paths(model):
    """The documents a model's envelopes name, beside the model: what the sweep opens (and the batch lane ships)."""
    return [os.path.join(os.path.dirname(model), d) for d in envelope_docs_of(model)]


def grid(x0, x1, y0, y1, step):
    """Ray probe points: the centre of each step x step cell over the box (a partial last cell: its own centre)."""
    def axis(lo, hi):
        out, i = [], 0
        while lo + i * step < hi:
            out.append(lo + step / 2 + i * step if lo + (i + 1) * step <= hi else (lo + i * step + hi) / 2)
            i += 1
        return out
    return [(x, y) for x in axis(x0, x1) for y in axis(y0, y1)]


def limits(plate_top, lower_contact, rails, uppers, top_contact, rails_up=()):
    """plate_top: LDO plate top Z at the model pose. lower_contact: (travel, (bed label, fixed label)) | None.
    rails: [(travel, block, rail)] to each Z block's bottom end reaching its rail's. uppers: {head: (travel, (bed
    label, other label)) | None}, the first touch with that head carried. top_contact: (travel, (bed label, other
    label)) | None, the first touch going up with the toolhead parked off the bed; rails_up: [(travel, block, rail)] to
    each Z block's top end reaching its rail's. -> {lower, upper, top, print_height, klipper, lines, problems}; lines
    are the log's limit lines (contact.line), problems the checks that fail. Klipper's Z0 is the nozzle on the magnet
    sheet, so the mechanical top is negative Z (#82 AC6)."""
    cands = [(lower_contact[0], f"{lower_contact[1][0]} lands on {lower_contact[1][1]}")] if lower_contact else []
    cands += [(d, f"the bottom end of {b} reaches the bottom end of {r}") for d, b, r in rails]
    if not cands: raise RuntimeError("no lower limit: no contact and no rail end")
    dl, why = min(cands, key=lambda c: c[0])
    lower = {"dz": -dl, "plate_top": plate_top - dl, "why": why}
    lines = [contact.line("z_lower_limit_mm", plate_top - dl, f"LDO plate top; bed dZ -{dl:.2f} from the model pose: {why}")]
    problems, heights, best = [], {}, None
    for h, u in uppers.items():
        if u is None:
            problems.append(f"{h} head carried over the centre: nothing touches the bed within the search"); continue
        d, (a, b) = u
        heights[h] = d + dl
        lines.append(f"{h} head carried over the centre: bed dZ +{d:.2f}, {a} touches {b}; print height {d + dl:.2f}")
        if not (a.startswith(MAGNET) and b.startswith(NOZZLE)):
            problems.append(f"{h} head carried over the centre: {a} touches {b} before the nozzle reaches the magnet sheet")
        if best is None or d < best[0]: best = (d, h, a, b)
    if best is None: raise RuntimeError("no upper limit: no head touches the bed")
    d, h, a, b = best
    upper = {"dz": d, "plate_top": plate_top + d, "head": h, "why": f"{a} touches {b}"}
    lines.append(contact.line("z_upper_limit_mm", plate_top + d,
                              f"LDO plate top; bed dZ +{d:.2f} from the model pose: {h} head carried, {a} touches {b}"))
    lines.append(contact.line("print_height_mm", d + dl, f"magnet-sheet top, from the lower stop to the {h} nozzle"))
    tops = [(top_contact[0], f"{top_contact[1][0]} touches {top_contact[1][1]}")] if top_contact else []
    tops += [(t, f"the top end of {b} reaches the top end of {r}") for t, b, r in rails_up]
    if not tops: raise RuntimeError("no mechanical top: no contact and no rail end with the toolhead parked")
    dt, twhy = min(tops, key=lambda c: c[0])
    top = {"dz": dt, "plate_top": plate_top + dt, "why": twhy}
    if dt < d:
        problems.append(f"the mechanical top (bed dZ +{dt:.2f}, {twhy}) is below the nozzle touch (+{d:.2f})")
    klipper = {"position_max": d + dl, "z_negative": d - dt, "travel": dt + dl}
    lines.append(contact.line("klipper_position_max_mm", d + dl, "Klipper Z at the lower stop; Z0 = the nozzle on the "
                              "magnet sheet (with a steel sheet, subtract its thickness)"))
    lines.append(contact.line("z_negative_limit_mm", d - dt, "Klipper Z at the mechanical top, toolhead parked off the "
                              f"bed: bed dZ +{dt:.2f}, {twhy}"))
    lines.append(contact.line("z_travel_mm", dt + dl, "the bed's full travel, lower stop to mechanical top"))
    return {"lower": lower, "upper": upper, "top": top, "print_height": heights, "klipper": klipper, "lines": lines,
            "problems": problems}


def parked_top(found):
    """found: {head: (travel, (bed label, other label)) | None}, the first touch going up with the carriage parked at
    that head's dock. The toolhead can park at either, so -> the higher touch, or None when some parking meets nothing
    within the search (the rail ends are then the top)."""
    if not found: raise RuntimeError("no parking searched")
    if any(v is None for v in found.values()): return None
    return max(found.values(), key=lambda v: v[0])


# ------------------------------------------------------------------------------------------------ FreeCAD (main)
def main(p):
    import json, tempfile
    import litelib, sweep_toolhead
    from litelib import _t_contact, _t_zspan, _Err
    p.log(f"model {MODEL} (read-only)")
    pr = p.open(MODEL)
    sweep_toolhead.MODEL = MODEL
    with tempfile.TemporaryDirectory(prefix="z-sweep-") as d:          # sweep_toolhead's groups, same document
        sweep_toolhead.plan(os.path.join(d, "plan.json"))
        plan = json.load(open(os.path.join(d, "plan.json")))
    par = {}
    for o in pr.doc.Objects:
        for k in (getattr(o, "Group", []) or []): par.setdefault(k.Name, o)
    def path(n):
        r, q = [], par.get(n)
        while q is not None: r.append(q.Label); q = par.get(q.Name)
        return r
    lab = {("printer", o.Name): o.Label for o in pr.leaves}
    env = [o.Name for o in pr.leaves if ENVELOPE.match(o.Label)]
    docs = {"printer": pr}
    for dp in envelope_paths(MODEL):
        if not os.path.isfile(dp): raise RuntimeError(f"an envelope names {dp}, which is missing")
        m = p.open(dp); docs[os.path.basename(dp)] = m
        lab.update({(os.path.basename(dp), o.Name): o.Label for o in m.leaves})
    bed = list(plan["bed"])
    skip = set(plan["exclude"]) | set(env)
    others = [("printer", n) for n in pr.shapes if n not in set(bed) and n not in skip] + \
             [(k, n) for k, m in docs.items() if k != "printer" for n in m.shapes]
    p.log(f"bed {len(bed)} solids moving; {len(others)} others: the printer's, less {len(env)} envelope(s) and "
          f"{len(plan['exclude'])} sweep_toolhead exclusions (docks' carriage copies, Z drag chain), plus "
          + ", ".join(f"{k} ({len(m.shapes)} solids)" for k, m in docs.items() if k != "printer"))
    box = {}
    for k, m in docs.items():
        for n, b in m.boxes.items(): box[(k, n)] = (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)
    shape = lambda key: docs[key[0]].shapes[key[1]]
    def moved(b, t): return (b[0] + t[0], b[1] + t[1], b[2] + t[2], b[3] + t[0], b[4] + t[1], b[5] + t[2])

    # --- ray probes: plate and magnet tops, Z blocks vs rails
    def span(key, pts, b):
        r = p.map(_t_zspan, [(shape(key), pts, b[2] - 5.0, b[5] + 5.0)])[0]
        if isinstance(r, _Err): raise RuntimeError(f"ray probe on {lab[key]} failed: {r.msg}")
        return r
    def one(prefix):
        c = [("printer", n) for n in bed if lab[("printer", n)].startswith(prefix)]
        if len(c) != 1: raise RuntimeError(f"{len(c)} bed solids labelled {prefix!r}...")
        return c[0]
    tops = {}
    for what in (PLATE, MAGNET):
        k = one(what); b = box[k]; cx, cy = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        s = span(k, grid(cx - 1.5, cx + 1.5, cy - 1.5, cy + 1.5, 1.0), b)
        if s is None: raise RuntimeError(f"no ray meets {lab[k]} at its centre")
        tops[what] = s[1]
        p.log(f"{lab[k]}: top Z {s[1]:.3f} at the model pose (ray probes at its centre)")
    blocks = {}
    for n in bed:
        g = [x for x in path(n) if x.startswith(BLOCK_GROUP)]
        if g and lab[("printer", n)].startswith(BLOCK_PART) and "screw" not in lab[("printer", n)].lower():
            blocks.setdefault(g[0], []).append(n)
    if not blocks: raise RuntimeError("no Z blocks found in the bed group")
    rails_lo, rails_hi = [], []
    for g, parts in sorted(blocks.items()):
        bz = [span(("printer", n), grid(*_xy(box[("printer", n)]), RAY_GRID), box[("printer", n)]) for n in parts]
        bz = [s for s in bz if s]
        blo, bhi = min(s[0] for s in bz), max(s[1] for s in bz)
        bb = _union([box[("printer", n)] for n in parts])
        rail = [k for k in others if k[0] == "printer" and any(x.startswith(RAIL_GROUP) for x in path(k[1]))
                and not lab[k].startswith("M") and _xy_overlap(box[k], bb)]
        if not rail: raise RuntimeError(f"{g}: no Z rail under its block")
        rail = max(rail, key=lambda k: box[k][5] - box[k][2])
        rs = span(rail, grid(*_xy(box[rail]), RAY_GRID), box[rail])
        rails_lo.append((blo - rs[0], g, f"{lab[rail]} ({[x for x in path(rail[1]) if x.startswith(RAIL_GROUP)][0]})"))
        rails_hi.append((rs[1] - bhi, g, lab[rail]))
        p.log(f"Z block {g} ({len(parts)} parts): Z {blo:.3f} .. {bhi:.3f}; rail {lab[rail]}: Z {rs[0]:.3f} .. {rs[1]:.3f}; "
              f"block end reaches the rail's bottom end at bed dZ -{blo - rs[0]:.2f}, its top end at +{rs[1] - bhi:.2f}")
    cap_lo = min(r[0] for r in rails_lo) + contact.REPORT
    cap_hi = min(r[0] for r in rails_hi) + contact.REPORT
    p.log(f"search caps (first rail end + {contact.REPORT:.0f} mm): down {cap_lo:.2f}, up {cap_hi:.2f}")

    # --- pruned boolean search
    def sweep(name, direction, cands, cap):
        """cands [(other key, translation)] -> search() over bed x cands, logged; best as (d, (bed label, label))"""
        pairs, tr, errors = [], {}, []
        for a in bed:
            for k, t in cands:
                w = contact.window(box[("printer", a)], moved(box[k], t), direction, cap=cap)
                if w: pairs.append((("printer", a), k) + w); tr[k] = t
        pairs = [((a, k), lo, hi) for a, k, lo, hi in pairs]
        def run(batch):
            res = p.map(_t_contact, [(shape(a), shape(k), direction, lo, hi, (0.0, 0.0, 0.0), tuple(tr[k]))
                                     for (a, k), lo, hi in batch])
            out = []
            for ((a, k), lo, _), r in zip(batch, res):
                if isinstance(r, _Err): errors.append((lo, a, k, r.msg)); r = {"kind": "clear", "d": None}
                out.append(r)
            return out
        r = contact.search(pairs, run, cap)
        p.log(f"== {name}: {len(pairs)} pairs can meet within {cap:.2f} mm, {r['runs']} searched, "
              f"{len(r['fits'])} already overlapping at the model pose, {len(errors)} boolean errors")
        for k, v in r["fits"]: p.log(f"   fit (not a limit): {lab[k[0]]} x {lab[k[1]]}: {v:.3f} mm3 at the model pose")
        for d, k in r["contacts"]: p.log(f"   contact at {d:8.3f}: {lab[k[0]]} x {lab[k[1]]} ({k[1][0]})")
        best = r["best"][0] if r["best"] else None
        for lo, a, k, msg in errors:
            p.check(best is not None and lo >= best + contact.REPORT,
                    f"{name}: boolean failed for {lab[a]} x {lab[k]} (window from {lo:.2f}): {msg}")
        return (r["best"][0], (lab[r["best"][1][0]], lab[r["best"][1][1]])) if r["best"] else None, r, errors

    zero = (0.0, 0.0, 0.0)
    low, rlow, elow = sweep("bed down", -1, [(k, zero) for k in others], cap_lo)
    ups, report = {}, {}
    belts = set(plan["belt"])
    for h in sweep_toolhead.HEADS:
        pose = plan["poses"][h][CARRIED_POSE]
        g = {**{n: pose["gantry"] for n in plan["gantry"]}, **{n: pose["carriage"] for n in plan["carriage"]},
             **{n: pose["head"] for n in plan["heads"][h]}}
        cands = [(k, tuple(g.get(k[1], zero)) if k[0] == "printer" else zero) for k in others
                 if not (k[0] == "printer" and (k[1] in belts or k[1] == plan["tubes"][h]))]
        m = plan["meta"][f"{h}:{CARRIED_POSE}"]
        p.log(f"{h} head carried, nozzle over ({m['nozzle'][0]:.2f}, {m['nozzle'][1]:.2f}), tip Z {m['nozzle'][2]:.2f} "
              f"by its box; belts and its own bowden tube left out")
        ups[h], report[h], _ = sweep(f"bed up, {h} head carried over the centre", +1, cands, cap_hi)
    docked, rdock, _ = sweep("bed up, both heads docked (model pose)", +1, [(k, zero) for k in others], cap_hi)
    parked, rpark = {}, {}
    for h in sweep_toolhead.HEADS:                                     # the full travel's top (#82 AC6)
        pose = plan["poses"][h][PARKED_POSE]
        g = {**{n: pose["gantry"] for n in plan["gantry"]}, **{n: pose["carriage"] for n in plan["carriage"]}}
        cands = [(k, tuple(g.get(k[1], zero)) if k[0] == "printer" else zero) for k in others
                 if not (k[0] == "printer" and k[1] in belts)]
        p.log(f"toolhead parked at the {h} dock pickup: gantry dY {pose['gantry'][1]:.2f}, carriage "
              f"({pose['carriage'][0]:.2f}, {pose['carriage'][1]:.2f}); both heads docked, belts left out")
        parked[h], rpark[h], _ = sweep(f"bed up, toolhead parked at the {h} dock", +1, cands, cap_hi)
    p.log("mechanical upper stop with nothing over the bed: " +
          (f"bed dZ +{docked[0]:.2f}, {docked[1][0]} touches {docked[1][1]}" if docked else "none within the cap") +
          "; rail top ends: " + "; ".join(f"{g} +{d:.2f}" for d, g, _ in rails_hi))
    L = limits(tops[PLATE], low, rails_lo, ups, parked_top(parked), rails_hi)
    for l in L["lines"]: p.log(l)
    p.log(f"magnet-sheet top at the model pose {tops[MAGNET]:.3f}: lower stop {tops[MAGNET] + L['lower']['dz']:.2f}, "
          f"upper stop {tops[MAGNET] + L['upper']['dz']:.2f} (no steel sheet modelled)")
    for x in L["problems"]: p.check(False, x)
    p.check(True, "every limit measured by boolean contact or ray probe")
    p.dump(dict(model=MODEL, plate_top=tops[PLATE], magnet_top=tops[MAGNET], lower=L["lower"], upper=L["upper"],
                print_height=L["print_height"], top=L["top"], klipper=L["klipper"],
                parked={h: v[0] if v else None for h, v in parked.items()}, rails_lower=rails_lo, rails_upper=rails_hi,
                docked_upper=docked[0] if docked else None, problems=L["problems"],
                contacts={"down": [(d, lab[k[0]], lab[k[1]]) for d, k in rlow["contacts"]],
                          **{f"up {h}": [(d, lab[k[0]], lab[k[1]]) for d, k in report[h]["contacts"]] for h in report},
                          **{f"parked {h}": [(d, lab[k[0]], lab[k[1]]) for d, k in rpark[h]["contacts"]] for h in rpark}}))
    p.finish([])                                                       # nothing to save, ever
    if not p.errs: p.log(contact.DONE)


def _xy(b):
    return b[0], b[3], b[1], b[4]


def _union(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), min(b[2] for b in bs),
            max(b[3] for b in bs), max(b[4] for b in bs), max(b[5] for b in bs))


def _xy_overlap(a, b):
    return a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4]


if __name__ in ("__main__", "z_sweep") and "FreeCAD" in sys.modules:     # freecadcmd runs it as "z_sweep"
    import litelib
    litelib.Pass("z_sweep").run(main)
