# #19 AC5 / #53 AC4: toolhead collision sweep on the SAVED vt350-lite-26.FCStd (#61: carriage on the MGN12H block). Headless, read-only: never saves.
#   python3 /home/dan/Code/vt350/cad/scripts/sweep_toolhead.py [n_workers]
# Two stages, both from this file:
#  1. plan (freecadcmd, env SWEEP_PLAN=<json>): classify the moving groups, find each head's carried offset, the
#     nozzle, the bed's Z travel, and write the poses.
#  2. check (plain python3): clashlib runs the poses on N workers, one job per carried head; then the report.
#
# The model has NO head on the MadMax carriage: both A4Tv2 heads sit at their docks (lite-15). A head is put on the
# carriage by transform: each dock carries a copy of the carriage at its pickup pose (lite-14), so
#   T_pick(head) = dock carriage copy - gantry carriage      (centre of mass of the same COMPOUND part)
# and with the carriage translated by Tc, the carried head moves Tc - T_pick (its own docked pose at pickup).
#
# Moving groups (translations only): bed (Z), gantry (Y), carriage (X+Y), head (X+Y, rigid on the carriage).
# The MadMax tool plate (Plate + Plate Back, filed under each dock) is bolted to the head and moves with it. Since
# lite-23 the dock screws are on bosses on the head's duct (no Dock/Alternate Bracket). The Beacon (lite-24) is under
# the carriage and moves with it.
# Belts (#53 AC4): the part of each belt inside the XY joints' Y band (the idler wraps and the runs out to the carriage
# clamps) rides rigidly with the gantry: it's its own group, clipped to BELT_CLIP, moved with the gantry, and not checked
# against the gantry or the carriage (it wraps the joints' idlers and is clamped in the carriage). Limitation: the
# drawn runs end at the carriage's model-pose X, so near the clamps they are approximate. The side (Y) runs are left out.
# Left out of every check, and said so in the report:
#  - the docks' carriage copies (they ARE the carriage at pickup; the moving carriage takes their place),
#  - the belts' side runs, outside BELT_CLIP (they change length with gantry Y),
#  - the Z drag chain (links posed for one bed height),
#  - the carried head's own bowden tube (a rigid route from its docked pose; the parked head's tube stays in, fixed).
# USB cables are not in the model.
# Poses per head: nozzle at the 4 corners of the 350 print square (plate inset 2.5 mm; rear clamped to the gantry's Y
# reach) + the centre, each with the bed at the top (magnet sheet at the nozzle tip: Z0, no steel sheet modelled) and
# at the bottom; plus the head's own dock pickup at both bed heights, at the parked position and at the keyslots'
# large opening (SLIDE forward: the attach move, #52); plus the saved model pose (baseline).
import json, os, subprocess, sys, time

WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-26.FCStd")   # refresh.py sets it (#69)
HERE = os.path.abspath(__file__)
Y_TRAVEL = (-277.19, 145.43)           # gantry dY limits, lite9_rails.log (joint/mount hard stops; Z moves since keep them)
PLATE_X0, PLATE_Y0, PLATE_W, PRINT_W = -422.5, 28.0, 355.0, 350.0
# Tool side of each dock: the MadMax plate + Plate Back (the brackets were removed in lite-23).
HEADS = {"Left": dict(group="Left Toolhead", dock="Left Dock", tube="Bowden Left", copy="COMPOUND003",
                      plate=["Plate", "Plate Back"]),
         "Right": dict(group="Right Toolhead", dock="Right Dock", tube="Bowden Right", copy="COMPOUND004",
                       plate=["Plate(Mirror)", "Plate Back(Mirror)"])}
SLIDE = 6.0                            # keyslot slide, parked -> large opening (#52, sliced)
BEAM = "Beacon RevH"                   # label prefix of the Beacon (lite-24); must be in the carriage group
BELTS = ("GT2 9mm belt, lower (Monolith 2WD)", "GT2 9mm belt, upper (Monolith 2WD)")
BELT_CLIP = (-480.0, 243.2, 400.0, -10.0, 294.5, 460.0)   # XY joints' Y band (VC9-J* plates), lite-23 probe
X_SCAN = 40.0, 1.0                     # nozzle X scanned inward from each side of the print square: span, step (mm)
CARRIAGE_PART = ("Carriage (1)", "COMPOUND")          # (group, label) of the gantry's MadMax carriage body
BED_PATHS = {"Bed frame", "Z_Bed_Left", "Z_Bed_Right", "Z_Bed_Rear", "Z_Carriage_Left", "Z_Carriage_Right",
             "Z_Carriage_Rear_2-hole (IGUS)", "Z_Carriage_Rear_3-Hole (Generic)", "MGN9H (2)", "MGN9H (3)",
             "MGN9H (4)", "kinematic bed mount v1"}
BED_LABEL_PREFIX = ("LDO 350 build plate", "Magnetic sheet", "Heater pad")
BED_LOOSE = ("M5x16-Screw001", "M5-Washer001")       # bed-frame bolt filed under the frame (lite-10 found it)
GANTRY_PATHS = {"XY left: _XY_left", "XY right: _XY_right", "Gantry assembly"}
GANTRY_LABELS = ("Carbonara CF X beam 20x20 430",)
CARRIAGE_PATHS = {"Carriage (1)"}
CARRIAGE_LABELS = ("MGN_12_H_CARRAGE v1",)
EXCLUDE_PATHS = {"10x11 Chain Z"}
NOZZLE = "E3D v6 HotEnd - Nozzle"


# ------------------------------------------------------------------------------------------------ stage 1: plan
def plan(out):
    import FreeCAD
    V = FreeCAD.Vector
    doc = FreeCAD.openDocument(MODEL)
    par = {}
    for o in doc.Objects:
        for k in (getattr(o, 'Group', []) or []): par.setdefault(k.Name, o)
    def path(o):
        r, p = [], par.get(o.Name)
        while p is not None: r.append(p.Label); p = par.get(p.Name)
        return r
    leaves = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids]
    P = {o.Name: set(path(o)) for o in leaves}
    def gshape(o):
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
    _bb = {}
    def bb(o):
        if o.Name not in _bb:
            s = gshape(o)
            try: _bb[o.Name] = s.optimalBoundingBox(True, False)
            except Exception: _bb[o.Name] = s.BoundBox
        return _bb[o.Name]
    def one(label, under=None):
        c = [o for o in leaves if o.Label == label and (under is None or under in P[o.Name])]
        if len(c) != 1: raise RuntimeError(f"{len(c)} leaves labelled {label!r} under {under!r}")
        return c[0]
    notes = []
    tubes = {h: one(d["tube"]) for h, d in HEADS.items()}
    copies = {h: one(d["copy"], d["dock"]) for h, d in HEADS.items()}
    belts = [one(l).Name for l in BELTS]
    exclude = [o.Name for o in leaves if P[o.Name] & EXCLUDE_PATHS] + \
              [c.Name for c in copies.values()]
    # the whole carriage copy in each dock: everything under the dock's "Carriage" sub-assembly
    for h, d in HEADS.items():
        exclude += [o.Name for o in leaves if d["dock"] in P[o.Name] and ("Carriage" in P[o.Name] or "Carriage(Mirror)" in P[o.Name])]
    exclude = sorted(set(exclude))
    bed = [o.Name for o in leaves if (P[o.Name] & BED_PATHS or o.Label.startswith(BED_LABEL_PREFIX) or o.Label in BED_LOOSE)]
    gantry = [o.Name for o in leaves if P[o.Name] & GANTRY_PATHS or o.Label in GANTRY_LABELS]
    carriage = [o.Name for o in leaves if P[o.Name] & CARRIAGE_PATHS or o.Label in CARRIAGE_LABELS]
    beacon = [o for o in leaves if o.Label.startswith(BEAM)]
    if len(beacon) != 1 or beacon[0].Name not in carriage: raise RuntimeError(f"Beacon: {len(beacon)} found / not in the carriage group")
    notes.append(f"Beacon {beacon[0].Label!r} rides with the carriage")
    heads, tool = {}, {}
    for h, d in HEADS.items():
        tool[h] = dict(head=[o.Name for o in leaves if d["group"] in P[o.Name] and o.Name not in (tubes["Left"].Name, tubes["Right"].Name)],
                       plate=[one(l, d["dock"]).Name for l in d["plate"]])
        heads[h] = tool[h]["head"] + tool[h]["plate"]
    allg = bed + gantry + carriage + heads["Left"] + heads["Right"] + belts
    if len(allg) != len(set(allg)): raise RuntimeError("a solid is in two moving groups")
    if set(allg) & set(exclude): raise RuntimeError(f"moving solids excluded: {set(allg) & set(exclude)}")
    lab = {o.Name: o.Label for o in leaves}
    notes.append(f"groups: bed {len(bed)}, gantry {len(gantry)}, carriage {len(carriage)}, "
                 f"Left head {len(heads['Left'])}, Right head {len(heads['Right'])} solids; excluded {len(exclude)}; "
                 f"{len(leaves)} leaves")
    # carried offset of each head: dock carriage copy vs the gantry carriage (same part)
    def com(s):                                   # compounds have no CenterOfMass: volume-weighted over the solids
        vs = [(x.Volume, x.CenterOfMass) for x in s.Solids]; tv = sum(v for v, _ in vs)
        return sum((c * (v / tv) for v, c in vs), V(0, 0, 0))
    real = one(CARRIAGE_PART[1], CARRIAGE_PART[0])
    sr = gshape(real); T = {}
    for h, c in copies.items():
        sc = gshape(c)
        t = com(sc) - com(sr)
        moved = sr.copy(); moved.translate(t)
        resid = max(abs(a - b) for a, b in zip(
            [moved.BoundBox.XMin, moved.BoundBox.YMin, moved.BoundBox.ZMin, moved.BoundBox.XMax, moved.BoundBox.YMax, moved.BoundBox.ZMax],
            [sc.BoundBox.XMin, sc.BoundBox.YMin, sc.BoundBox.ZMin, sc.BoundBox.XMax, sc.BoundBox.YMax, sc.BoundBox.ZMax]))
        dv = abs(sc.Volume - sr.Volume)
        notes.append(f"{h}: pickup carriage offset ({t.x:.3f}, {t.y:.3f}, {t.z:.3f}) from the gantry carriage; "
                     f"same part: volume diff {dv:.3f} mm3, box residual {resid:.3f} mm")
        if dv > 0.5 or resid > 0.05: raise RuntimeError(f"{h}: dock carriage copy isn't the gantry carriage part")
        if abs(t.z) > 0.01: notes.append(f"   NOTE {h}: the dock expects the carriage {t.z:+.3f} mm off the gantry carriage's Z")
        T[h] = (t.x, t.y, t.z)
    nozzles = {}
    for h, d in HEADS.items():
        nz = [o for o in leaves if o.Label.startswith(NOZZLE) and d["group"] in P[o.Name]]
        if len(nz) != 1: raise RuntimeError(f"{h}: {len(nz)} nozzles")
        b = bb(nz[0]); nozzles[h] = ((b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2, b.ZMin)
        notes.append(f"{h}: docked nozzle tip ({nozzles[h][0]:.2f}, {nozzles[h][1]:.2f}, {nozzles[h][2]:.2f})")
    # bed travel: top = magnet sheet at the nozzle tip; bottom = first bed solid to land on a fixed solid below it
    mag = bb(one("Magnetic sheet (1.4 mm)"))
    bedset, movset = set(bed), set(allg) | set(exclude)
    fixed = [o for o in leaves if o.Name not in movset]
    land = []
    def on_rail(o): return any(x.startswith("MGN9 - 400mm") for x in P[o.Name])
    for nb in bed:
        ob = doc.getObject(nb); b = bb(ob)
        for f in fixed:
            g = bb(f)
            if on_rail(f):
                # a Z block rides its rail (the rail's screws sit recessed under it): the limit is the block leaving
                # the rail's bottom end
                if any(x.startswith("MGN9H") for x in P[nb]) and ob.Label.startswith("MGN9H - Carriage") \
                        and min(b.XMax, g.XMax) - max(b.XMin, g.XMin) > 0.01 and min(b.YMax, g.YMax) - max(b.YMin, g.YMin) > 0.01 \
                        and g.ZMin < b.ZMin and not f.Label.startswith("M3"):
                    land.append((b.ZMin - g.ZMin, lab[nb], f.Label + " (block leaves the rail's bottom end)"))
                continue
            if g.ZMax > b.ZMin + 0.01: continue
            if min(b.XMax, g.XMax) - max(b.XMin, g.XMin) <= 0.01 or min(b.YMax, g.YMax) - max(b.YMin, g.YMin) <= 0.01: continue
            land.append((b.ZMin - g.ZMax, lab[nb], f.Label))
    land.sort()
    dz_bottom = -land[0][0]
    notes.append(f"bed bottom: dZ {dz_bottom:.2f} ({land[0][1]} lands on {land[0][2]}, bounding-box estimate); next: "
                 + "; ".join(f"{-g:.2f} {a} on {c}" for g, a, c in land[1:4]))
    # poses
    poses, meta = {}, {}
    x_lo, x_hi = PLATE_X0 + (PLATE_W - PRINT_W) / 2, PLATE_X0 + (PLATE_W + PRINT_W) / 2
    y_lo, y_hi = PLATE_Y0 + (PLATE_W - PRINT_W) / 2, PLATE_Y0 + (PLATE_W + PRINT_W) / 2
    for h in HEADS:
        nx, ny, nz = nozzles[h]; tx, ty, tz = T[h]
        tip_z = nz - tz                                    # nozzle tip when carried (head moves Tc - T_pick, Tc.z = 0)
        dz_top = tip_z - mag.ZMax
        y_reach = ny + Y_TRAVEL[1] - ty                    # nozzle Y with the gantry at its rear stop
        y_front = ny + Y_TRAVEL[0] - ty
        notes.append(f"{h} carried: nozzle tip Z {tip_z:.2f}; bed top dZ {dz_top:+.2f} (magnet top {mag.ZMax:.2f} -> "
                     f"{mag.ZMax + dz_top:.2f}); nozzle Y reach {y_front:.2f} .. {y_reach:.2f} (print square Y {y_lo:.1f} .. {y_hi:.1f})")
        poses[h] = {}
        def add(pid, nozzle_xy, dz, what, slide=0.0):
            if nozzle_xy is None:
                tc = (tx, ty - slide, 0.0)                 # pickup: head at its docked pose (or slid to the large opening)
            else:
                tc = (nozzle_xy[0] - nx + tx, nozzle_xy[1] - ny + ty, 0.0)
            th = (tc[0] - tx, tc[1] - ty, tc[2] - tz)
            if not (Y_TRAVEL[0] - 1e-6 <= tc[1] <= Y_TRAVEL[1] + 1e-6): raise RuntimeError(f"{pid}: gantry dY {tc[1]:.2f} out of travel")
            poses[h][pid] = {"bed": (0, 0, dz), "gantry": (0, tc[1], 0), "belt": (0, tc[1], 0), "carriage": tc, "head": th}
            meta[f"{h}:{pid}"] = dict(what=what, nozzle=(nx + th[0], ny + th[1], nz + th[2]), bed_dz=dz, carriage=tc)
        for zname, dz in (("bed top", dz_top), ("bed bottom", dz_bottom)):
            zt = "top" if zname == "bed top" else "bottom"
            for cname, (x, y) in (("front-left", (x_lo, y_lo)), ("front-right", (x_hi, y_lo)), ("rear-left", (x_lo, y_hi)),
                                  ("rear-right", (x_hi, y_hi)), ("centre", ((x_lo + x_hi) / 2, (y_lo + y_hi) / 2))):
                yc = min(y, y_reach)
                add(f"{cname}, {zt}", (x, yc), dz, f"{cname} corner{' (Y clamped to reach %.2f)' % yc if yc < y else ''}, {zname}")
            add(f"dock pickup, {zt}", None, dz, f"own dock pickup (parked), {zname}")
            add(f"dock pickup at the large opening, {zt}", None, dz,
                f"own dock pickup slid {SLIDE} mm forward to the keyslots' large opening, {zname}", slide=SLIDE)
        xs = {}
        span, step = X_SCAN
        for side, x0, sgn in (("left", x_lo, 1), ("right", x_hi, -1)):
            for i in range(int(span / step) + 1):
                x = x0 + sgn * i * step
                pid = f"X scan {side} {x:.1f}"
                tc = (x - nx + tx, (y_lo + y_hi) / 2 - ny + ty, 0.0)
                xs[pid] = {"gantry": (0, tc[1], 0), "belt": (0, tc[1], 0), "carriage": tc, "head": (tc[0] - tx, tc[1] - ty, tc[2] - tz)}
        poses[h + " X scan"] = xs
    json.dump(dict(bed=bed, gantry=gantry, belt=belts, carriage=carriage, heads=heads, tool=tool, exclude=exclude,
                   tubes={h: t.Name for h, t in tubes.items()}, poses=poses, meta=meta, notes=notes, labels=lab),
              open(out, "w"))


def plan_stage(freecadcmd):
    """Run stage 1 (freecadcmd) and return its plan. Its temp dir is removed on every path."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="sweep-") as d:
        pj = os.path.join(d, "plan.json")
        subprocess.run(freecadcmd + [HERE], env=dict(os.environ, SWEEP_PLAN=pj), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, cwd="/tmp")
        if not os.path.exists(pj): raise SystemExit("plan stage wrote nothing")
        plan_ = json.load(open(pj))
    if "fatal" in plan_: raise SystemExit("plan stage failed:\n" + plan_["fatal"])
    return plan_


# ------------------------------------------------------------------------------------------------ stage 2: check
def main():
    sys.path.insert(0, os.path.dirname(HERE)); import clashlib
    n = int(sys.argv[1]) if len(sys.argv) > 1 else clashlib.default_n()
    os.makedirs(WORK + "/logs", exist_ok=True)
    log_f = open(WORK + "/logs/sweep_toolhead.log", "w"); t0 = time.time()
    def log(*a):
        s = f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a); print(s, flush=True); log_f.write(s + "\n"); log_f.flush()
    plan_ = plan_stage(clashlib.FREECADCMD)
    log(f"model {MODEL} (read-only)")
    for s in plan_["notes"]: log(s)
    lab = plan_["labels"]
    log("excluded from every check: docks' carriage copies, the belts' side runs (outside the XY joints' Y band), the Z "
        "drag chain, the carried head's own bowden tube; the Beacon's USB cable is not in the model")
    log(f"belts: clipped to X {BELT_CLIP[0]}..{BELT_CLIP[3]}, Y {BELT_CLIP[1]}..{BELT_CLIP[4]} and moved with the gantry; "
        "not checked against the gantry or carriage")
    clip = {b: BELT_CLIP for b in plan_["belt"]}
    BSKIP = [("belt", "gantry"), ("belt", "carriage")]
    summary = {}
    for h in HEADS:
        other = [x for x in HEADS if x != h][0]
        groups = dict(bed=plan_["bed"], gantry=plan_["gantry"], belt=plan_["belt"], carriage=plan_["carriage"], head=plan_["heads"][h])
        poses = dict(plan_["poses"][h]); poses["model"] = {}
        res = clashlib.run(MODEL, groups=groups, poses=poses, exclude=plan_["exclude"] + [plan_["tubes"][h]], n=n,
                           tol=0.01, log=log, clip=clip, skip_group_pairs=BSKIP)
        log(f"=== {h} head on the carriage ({other} head parked in its dock): {len(res['results'])} overlaps, "
            f"{len(res['errors'])} common() errors")
        for e in res["errors"]: log(f"   ERROR {e['pose']}: {e['la']} x {e['lb']}: {e['error']}")
        base = {(r["a"], r["b"]): r["volume"] for r in res["results"] if r["pose"] == "model"}
        by_pair = {}
        for r in res["results"]: by_pair.setdefault((r["a"], r["b"]), []).append(r)
        order = list(poses)
        for pid in order:
            rows = [r for r in res["results"] if r["pose"] == pid]
            m = plan_["meta"].get(f"{h}:{pid}", dict(what="saved model pose (baseline: nothing moved, both heads docked)"))
            nz = f" nozzle ({m['nozzle'][0]:.1f}, {m['nozzle'][1]:.1f}, {m['nozzle'][2]:.2f}) bed dZ {m['bed_dz']:+.2f}" if "nozzle" in m else ""
            log(f"-- {h} / {pid}: {m['what']};{nz}: {len(rows)} overlaps")
            for r in rows:
                tag = ""
                if pid != "model":
                    if (r["a"], r["b"]) in base and abs(base[(r["a"], r["b"])] - r["volume"]) < 0.01: tag = "  [same in the saved model]"
                    elif len({round(x["volume"], 2) for x in by_pair[(r["a"], r["b"])]}) == 1 and len(by_pair[(r["a"], r["b"])]) == len(order) - 1:
                        tag = "  [same at every carried pose: fit on the carriage]"
                log(f"   {r['volume']:10.2f} mm3  {r['ga']}: {r['la']}  x  {r['gb'] or 'fixed'}: {r['lb']}{tag}")
        summary[h] = res["stats"]
        # X reach: carriage + this head scanned inward from each side of the print square (bed at its model pose)
        xres = clashlib.run(MODEL, groups=dict(gantry=plan_["gantry"], belt=plan_["belt"], carriage=plan_["carriage"], head=plan_["heads"][h]),
                            poses=plan_["poses"][h + " X scan"], exclude=plan_["exclude"] + [plan_["tubes"][h]],
                            n=n, tol=0.01, log=log, clip=clip, skip_group_pairs=BSKIP)
        const = {(r["a"], r["b"]) for r in res["results"] if r["pose"] == "model"}      # sliding fits already in the saved model
        for side in ("left", "right"):
            pids = [p for p in plan_["poses"][h + " X scan"] if f" {side} " in p]
            log(f"-- {h} X scan, {side} side (nozzle X, Y at the centre; overlaps not already in the saved model):")
            first_clear = None
            for pid in pids:
                rows = [r for r in xres["results"] if r["pose"] == pid and (r["a"], r["b"]) not in const
                        and not (r["la"].startswith("MGN12-400mm") or r["lb"].startswith("MGN12-400mm"))]
                parts = sorted({(r["la"] if r["ga"] in ("carriage", "head") else r["lb"]) for r in rows})
                log(f"   X {pid.split()[-1]:>7}: {len(rows):2} overlaps, {sum(r['volume'] for r in rows):8.2f} mm3"
                    + (f"; moving parts: {', '.join(parts)}" if parts else ""))
                if first_clear is None and not rows: first_clear = pid.split()[-1]
            log(f"   {h} head, {side} side: first nozzle X with no new overlap {first_clear} (print square edge {pids[0].split()[-1]})")
        summary[h + " X scan"] = xres["stats"]
        # tool-internal: the head against its plate (they move together, so this is pose-independent)
        t = plan_["tool"][h]
        ires = clashlib.run(MODEL, groups=dict(head=t["head"], plate=t["plate"]), fixed=[], n=min(n, 4), tol=0.01, log=log)
        log(f"-- {h} tool-internal (head vs MadMax Plate + Plate Back):")
        for r in ires["results"]: log(f"   {r['volume']:10.2f} mm3  {r['ga']}: {r['la']}  x  {r['gb']}: {r['lb']}")
    log("timing: " + "; ".join(f"{h}: wall {s['wall_s']}s, {s['pair_poses']} pair-poses, {s['box_hits']} box hits" for h, s in summary.items()))
    log("done (read-only, nothing saved)")


if os.environ.get("SWEEP_PLAN"):
    try:
        plan(os.environ["SWEEP_PLAN"])
    except Exception:
        import traceback; json.dump(dict(fatal=traceback.format_exc()), open(os.environ["SWEEP_PLAN"], "w"))
    finally:
        os._exit(0)
elif __name__ == "__main__":
    main()
