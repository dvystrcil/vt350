# clashlib: parallel, read-only clash checks with N headless freecadcmd workers (#45).
#
# The parent (plain python3, or a FreeCAD script) calls run(); it never needs the model loaded. Each worker opens the
# SAVED model itself, works out the same leaf list, checks its share of the pairs, writes JSON and exits. Workers never
# save. Model-writing passes stay single GUI runs (colours need GUI mode); only the checks fan out.
#
#   import sys; sys.path.insert(0, "/home/dan/Code/vt350/cad/scripts"); import clashlib
#   res = clashlib.run(model, groups={"bed": [names...], "head": [...]}, poses={"p1": {"bed": (0, 0, 50)}}, n=10)
#
# groups   {group: [object Name or Label]}: the parts that move together. Pairs inside one group are never checked
#          (they don't move relative to each other).
# fixed    leaves that stay put: default every leaf solid in the model not in a group, minus `exclude`.
#          Fixed x fixed pairs are never checked.
# poses    {pose_id: {group: (dx, dy, dz)}}: global translations; a group with no entry stays at its model pose.
#          Default: one pose "model" with nothing moved. Only translations (that's all a Cartesian printer needs).
# skip_group_pairs  [(g1, g2)]: group pairs never checked against each other (e.g. a carriage and the head it carries).
# tol      overlaps <= tol mm3 are not reported (lite-18 used 0.01).
#
# Pairs are split by the non-moving member's index (round-robin), so each fixed solid's bounding box is computed by
# one worker only. Prefilter: optimalBoundingBox (triangulation) enlarged by BOX_MARGIN, so a chord-short box can't
# drop a real overlap; then Shape.common().Volume. A common() that throws is reported as an error, not skipped.
import json, os, shutil, subprocess, sys, tempfile, time

APP = os.environ.get("FREECAD_APPIMAGE", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
FREECADCMD = os.environ.get("FREECADCMD", f"{APP} freecadcmd").split()
BOX_MARGIN = 0.1          # mm added to every bounding box before the intersect test
HERE = os.path.abspath(__file__)


def default_n():
    """VT350_WORKERS, else the CPUs this process may use (cgroup quota + affinity, not os.cpu_count()) - 2."""
    sys.path.insert(0, os.path.dirname(HERE))
    import litepool
    return litepool.worker_count()


def run(model, groups, poses=None, fixed=None, exclude=(), skip_group_pairs=(), n=None, tol=0.01, log=print,
        keep_dir=None, timeout=7200, clip=None):
    """Run the check on n workers; returns dict(results=[...], errors=[...], stats={...}).
    clip: {ref: (xmin, ymin, zmin, xmax, ymax, zmax)}: that solid is cut down to the box (global, at the model pose)
    before anything else, e.g. the part of a belt that rides rigidly with the gantry."""
    n = n or default_n()
    poses = poses or {"model": {}}
    job = dict(model=os.path.abspath(model), groups={g: list(v) for g, v in groups.items()},
               poses={p: {g: list(map(float, t)) for g, t in d.items()} for p, d in poses.items()},
               fixed=None if fixed is None else list(fixed), exclude=list(exclude),
               skip_group_pairs=[list(x) for x in skip_group_pairs], n=n, tol=tol,
               clip={r: list(map(float, b)) for r, b in (clip or {}).items()})
    for p, d in job["poses"].items():
        bad = set(d) - set(groups)
        if bad: raise ValueError(f"pose {p}: unknown groups {sorted(bad)}")
    tmp = keep_dir or tempfile.mkdtemp(prefix="clashlib-")
    os.makedirs(tmp, exist_ok=True)
    procs = []
    try:                                       # the job dir goes on every exit path, unless keep_dir asked for it
        return _run(job, tmp, n, tol, log, timeout, procs)
    finally:
        for p in procs:
            if p.poll() is None: p.kill(); p.wait()
        if not keep_dir: shutil.rmtree(tmp, ignore_errors=True)


def _run(job, tmp, n, tol, log, timeout, procs):
    jpath = os.path.join(tmp, "job.json")
    json.dump(job, open(jpath, "w"))
    t0 = time.time()
    for k in range(n):
        env = dict(os.environ, CLASHLIB_JOB=jpath, CLASHLIB_K=str(k), CLASHLIB_OUT=os.path.join(tmp, f"w{k}.json"))
        procs.append(subprocess.Popen(FREECADCMD + [HERE], env=env, stdout=subprocess.DEVNULL,
                                      stderr=open(os.path.join(tmp, f"w{k}.err"), "w"), cwd="/tmp"))
    log(f"clashlib: {n} workers on {os.path.basename(job['model'])}, {len(job['poses'])} poses, job dir {tmp}")
    for p in procs: p.wait(timeout=timeout)
    wall = time.time() - t0
    results, errors, wstats = [], [], []
    for k in range(n):
        out = os.path.join(tmp, f"w{k}.json")
        if not os.path.exists(out):
            err = open(os.path.join(tmp, f"w{k}.err")).read()[-2000:]
            raise RuntimeError(f"clashlib worker {k} wrote no result (stderr tail: {err!r})")
        w = json.load(open(out))
        if w.get("fatal"): raise RuntimeError(f"clashlib worker {k} failed:\n{w['fatal']}")
        results += w["results"]; errors += w["errors"]; wstats.append(w["stats"])
    results.sort(key=lambda r: (r["pose"], -r["volume"], r["la"], r["lb"]))
    # every worker computes the same leaf list from the same file; disagreement means the inputs differ
    if len({(s["leaves"], s["pairs_total"]) for s in wstats}) != 1:
        raise RuntimeError(f"clashlib workers disagree on the model: {[(s['leaves'], s['pairs_total']) for s in wstats]}")
    stats = dict(n=n, wall_s=round(wall, 1), leaves=wstats[0]["leaves"], pairs_total=wstats[0]["pairs_total"],
                 pair_poses=sum(s["pair_poses"] for s in wstats), box_hits=sum(s["box_hits"] for s in wstats),
                 load_s=max(s["load_s"] for s in wstats), check_s_max=max(s["check_s"] for s in wstats),
                 check_s_sum=round(sum(s["check_s"] for s in wstats), 1), workers=wstats)
    log(f"clashlib: done in {wall:.1f}s (load <= {stats['load_s']:.1f}s, check <= {stats['check_s_max']:.1f}s); "
        f"{stats['pair_poses']} pair-poses, {stats['box_hits']} box hits, {len(results)} overlaps > {tol} mm3, "
        f"{len(errors)} errors")
    return dict(results=results, errors=errors, stats=stats)


# ----------------------------------------------------------------------------------------------------- worker side
def _worker():
    import FreeCAD
    job = json.load(open(os.environ["CLASHLIB_JOB"]))
    k, out = int(os.environ["CLASHLIB_K"]), os.environ["CLASHLIB_OUT"]
    n, tol = job["n"], job["tol"]
    V = FreeCAD.Vector
    t0 = time.time()
    doc = FreeCAD.openDocument(job["model"])
    load_s = time.time() - t0

    def is_leaf(o):
        return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and bool(o.Shape.Solids)

    leaves = [o for o in doc.Objects if is_leaf(o)]
    by_name = {o.Name: o for o in leaves}
    by_label = {}
    for o in leaves: by_label.setdefault(o.Label, []).append(o)

    def resolve(ref):
        if ref in by_name: return by_name[ref]
        c = by_label.get(ref, [])
        if len(c) != 1: raise RuntimeError(f"{len(c)} leaf solids named or labelled {ref!r}")
        return c[0]

    gof, gorder = {}, list(job["groups"])
    for g in gorder:
        for ref in job["groups"][g]:
            o = resolve(ref)
            if o.Name in gof and gof[o.Name] != g: raise RuntimeError(f"{o.Label} is in groups {gof[o.Name]} and {g}")
            gof[o.Name] = g
    excl = {resolve(r).Name for r in job["exclude"]}
    clipb = {resolve(r).Name: b for r, b in job.get("clip", {}).items()}
    if job["fixed"] is None: fixed = [o for o in leaves if o.Name not in gof and o.Name not in excl]
    else: fixed = [resolve(r) for r in job["fixed"]]
    idx = {o.Name: i for i, o in enumerate(leaves)}
    skip = {frozenset(x) for x in job["skip_group_pairs"]}
    members = {g: sorted((by_name[nm] for nm, gg in gof.items() if gg == g), key=lambda o: idx[o.Name]) for g in gorder}

    # pairs: (a in a group) x (b fixed, or b in a later group); owner of a pair = index of b, round-robin.
    # Kept per b: [(gb or None, b, [ga, ...])], so a whole group is rejected with one box test.
    pairs_total, mine = 0, []
    owners = [(None, b) for b in fixed] + [(g, o) for g in gorder for o in members[g]]
    for gb, b in owners:
        gas = [ga for ga in (gorder if gb is None else gorder[:gorder.index(gb)])
               if gb is None or frozenset((ga, gb)) not in skip]
        np_ = sum(len(members[ga]) for ga in gas)
        pairs_total += np_
        if np_ and idx[b.Name] % n == k: mine.append((gb, b, gas))

    shape, box = {}, {}

    def gs(o):
        if o.Name not in shape:
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
            if o.Name in clipb:
                import Part
                x0, y0, z0, x1, y1, z1 = clipb[o.Name]
                s = s.common(Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0)))
            shape[o.Name] = s
            try: bb = s.optimalBoundingBox(True, False)
            except Exception: bb = s.BoundBox
            bb = FreeCAD.BoundBox(bb); bb.enlarge(BOX_MARGIN); box[o.Name] = bb
        return shape[o.Name]

    def moved_box(o, t):
        gs(o)
        if t == zero: return box[o.Name]
        b = FreeCAD.BoundBox(box[o.Name]); b.move(V(*t)); return b

    def _shifted(s, v):                     # copy that shares the geometry, with the placement moved by v
        c = s.copy(False); c.Placement = FreeCAD.Placement(v, FreeCAD.Rotation()).multiply(s.Placement); return c

    zero = (0.0, 0.0, 0.0)
    t1 = time.time()                        # the clash stage = bounding boxes + box tests + common()
    for _, b, _ in mine: gs(b)
    results, errors = [], []
    pair_poses = box_hits = 0
    for pid, tr in job["poses"].items():
        tr = {g: tuple(t) for g, t in tr.items()}
        mbox = {g: [(o, moved_box(o, tr.get(g, zero))) for o in members[g]] for g in gorder}
        gbox = {}
        for g in gorder:
            bb = FreeCAD.BoundBox()
            for _, x in mbox[g]: bb.add(x)
            gbox[g] = bb
        for gb, b, gas in mine:
            tb = tr.get(gb, zero) if gb else zero
            bb = moved_box(b, tb)
            for ga in gas:
                pair_poses += len(members[ga])
                if not gbox[ga].intersect(bb): continue
                ta = tr.get(ga, zero)
                for a, ab in mbox[ga]:
                    if not ab.intersect(bb): continue
                    box_hits += 1
                    sa, sb = gs(a), gs(b)
                    if ta != zero: sa = _shifted(sa, V(*ta))
                    if tb != zero: sb = _shifted(sb, V(*tb))
                    try: v = sa.common(sb).Volume
                    except Exception as e:
                        errors.append(dict(pose=pid, a=a.Name, b=b.Name, la=a.Label, lb=b.Label, error=repr(e))); continue
                    if v > tol:
                        results.append(dict(pose=pid, ga=ga, gb=gb, a=a.Name, b=b.Name, la=a.Label, lb=b.Label, volume=v))
    stats = dict(k=k, leaves=len(leaves), pairs_total=pairs_total, mine=len(mine), pair_poses=pair_poses,
                 box_hits=box_hits, load_s=round(load_s, 1), check_s=round(time.time() - t1, 1))
    json.dump(dict(results=results, errors=errors, stats=stats), open(out, "w"))


if os.environ.get("CLASHLIB_JOB"):
    try:
        _worker()
    except Exception:
        import traceback
        json.dump(dict(fatal=traceback.format_exc()), open(os.environ["CLASHLIB_OUT"], "w"))
    finally:
        sys.stdout.flush(); os._exit(0)
