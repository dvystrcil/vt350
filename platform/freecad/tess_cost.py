# Which parts make a model slow to open in the FreeCAD GUI (platform; LESSONS.md, "Why a model is slow to open").
# The GUI tessellates every visible solid when it opens a file, and that, not the file size, is most of the open
# time. This times Shape.tessellate() part by part, headless, at 0.5 % of each part's box diagonal, and prints the
# most expensive families and parts.
#   TESS_COST_MODEL=<model.FCStd> [TESS_COST_OUT=<file.json>] [TESS_COST_TOP=25] $APP freecadcmd $PWD/platform/freecad/tess_cost.py
# It is a RANKING PROXY, not the GUI's own meshing. Checked against GUI opens of 5 copies of each part (2026-11-16):
# it ranks the six measured families (springs, O2S boards, bowdens, bearings, heat blocks, sensors) the way the GUI
# does, within about 2x each. MeshPart.meshFromShape with the GUI's Deviation/angular defaults did NOT: it missed the
# springs and bowdens, the GUI's two worst. Use this to choose what to try; measure the real effect with GUI opens
# (cad/studies/open_time.py, or 5 copies of a part in a test document).
# Skips what the GUI skips: parts hidden by their own Visibility, and parts a stand-in shows instead (StandInFor).
# A family is the label without its copy suffixes ("Spring v1 (1)001" -> "Spring v1"). Read-only: never saves.
import FreeCAD, os, re, sys, time, json, collections

MODEL = os.environ.get("TESS_COST_MODEL")
OUT = os.environ.get("TESS_COST_OUT")
TOP = int(os.environ.get("TESS_COST_TOP", "25"))
DEVIATION = 0.005                                  # of the part's box diagonal (the proxy above)


def family(label):
    """The label without copy suffixes: trailing "001", " (1)", "(Mirror)" and the like."""
    s = label
    while True:
        t = re.sub(r"(\s*\(\d+\)|\d{3})$", "", s).rstrip()
        if t == s: return s
        s = t


def deflection(s):
    return max(s.BoundBox.DiagonalLength * DEVIATION, 1e-3)


def main():
    if not MODEL: raise SystemExit("set TESS_COST_MODEL to the .FCStd to measure")
    t0 = time.time(); doc = FreeCAD.openDocument(MODEL); t_open = time.time() - t0
    standin_for = {getattr(o, "StandInFor", "") for o in doc.Objects} - {""}
    leaves, skipped = [], collections.Counter()
    for o in doc.Objects:
        if not o.isDerivedFrom("Part::Feature") or o.Shape.isNull() or not o.Shape.Solids: continue
        if o.Name in standin_for: skipped["a stand-in shows it"] += 1; continue
        if not getattr(o, "Visibility", True): skipped["hidden"] += 1; continue
        leaves.append(o)
    rows = []
    for o in leaves:
        s = o.Shape.copy()                           # a fresh copy: no triangulation cached on it yet
        t = time.time()
        try: tri = len(s.tessellate(deflection(s))[1])
        except Exception: tri = -1                   # the time still counts: the GUI pays it too
        rows.append(dict(name=o.Name, label=o.Label, family=family(o.Label), secs=time.time() - t,
                         triangles=tri, faces=len(s.Faces)))
    total = sum(r["secs"] for r in rows)
    fam = collections.defaultdict(lambda: dict(secs=0.0, n=0, triangles=0))
    for r in rows:
        f = fam[r["family"]]; f["secs"] += r["secs"]; f["n"] += 1; f["triangles"] += r["triangles"]
    print(f"{os.path.basename(MODEL)}: opened in {t_open:.1f}s; {len(rows)} parts meshed in {total:.1f}s "
          f"({sum(r['triangles'] for r in rows)} triangles); skipped: {dict(skipped) or 'none'}")
    print("\nby family (secs, share, count, triangles):")
    for k, f in sorted(fam.items(), key=lambda kv: -kv[1]["secs"])[:TOP]:
        print(f"  {f['secs']:7.2f}s {100 * f['secs'] / total:5.1f}%  x{f['n']:<4d} {f['triangles']:>9d} tri  {k}")
    print(f"\ntop {TOP} parts:")
    for r in sorted(rows, key=lambda r: -r["secs"])[:TOP]:
        print(f"  {r['secs']:7.2f}s  faces {r['faces']:6d}  tri {r['triangles']:>8d}  {r['label']}")
    if OUT:
        json.dump(dict(model=os.path.basename(MODEL), open_secs=t_open, total_secs=total, skipped=dict(skipped),
                       parts=rows), open(OUT, "w"), indent=1)


try:
    main()
finally:
    sys.stdout.flush(); os._exit(0)                 # os._exit skips the flush; without it nothing prints
