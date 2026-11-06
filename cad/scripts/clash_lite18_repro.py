# #45 AC1 + AC2: reproduce lite-18's clash findings from the SAVED vt350-lite-18.FCStd with clashlib, serial (1
# worker) and parallel (cores - 2), and compare pairs and volumes with the serial result in data/logs/lite18_plate.log.
# Plain python3 (the workers run freecadcmd themselves); read-only, never saves.
#   python3 /home/dan/Code/vt350/cad/scripts/clash_lite18_repro.py [n_parallel]
# lite-18's rule (lite18_plate.py, "clashes"): the 7 new parts x every leaf solid; pairs inside {plate, pad,
# hold-downs} skipped (contact by construction); the magnet sheet is checked against all of them; > 0.01 mm3 reported.
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clashlib

WORK = os.environ.get("VT350_WORK", "/home/dan/Code/vt350/cad/data")
MODEL = "/home/dan/Documents/VT350/vt350-lite-18.FCStd"
REF_LOG = WORK + "/logs/lite18_plate.log"
PLATE = ["LDO 350 build plate (real: 355 sq x 10, 3.4 + 6.5x4.9 cbore)",
         "Heater pad LDO-SHPAC-350-120-750 (1.5 mm, photo outline +-1 mm)"] + \
        [f"Heater pad hold-down {k} (pan head + washer envelope, 3.8 below plate)" for k in range(1, 5)]
MAGNET = ["Magnetic sheet (1.4 mm)"]
TOL = 0.01

log_f = open(WORK + "/logs/clashlib_lite18.log", "w"); t0 = time.time()
def log(*a):
    s = f"[{time.time()-t0:7.1f}s] " + " ".join(str(x) for x in a); print(s); log_f.write(s + "\n"); log_f.flush()

# serial reference: the CLASH lines of the FINDINGS block (FAIL lines would be listed under verify; there were 0)
ref = {}
for line in open(REF_LOG):
    m = re.search(r"\]\s+CLASH\s+([\d.]+) mm3  (.+) x (.+)$", line)
    if m: ref[frozenset((m.group(2), m.group(3)))] = float(m.group(1))
log(f"reference ({REF_LOG}): {len(ref)} clashes")
for k, v in ref.items(): log(f"   {v:8.2f} mm3  " + " x ".join(sorted(k)))

def compare(res, tag):
    got = {frozenset((r["la"], r["lb"])): r["volume"] for r in res["results"]}
    bad = []
    for k, v in ref.items():
        if k not in got: bad.append(f"missing: {' x '.join(sorted(k))}")
        elif abs(got[k] - v) > TOL + 0.005:   # the log prints 2 decimals: allow its rounding (0.005) on top of 0.01
            bad.append(f"volume {got[k]:.4f} vs {v:.2f}: {' x '.join(sorted(k))}")
    for k, v in got.items():
        if k not in ref: bad.append(f"extra: {v:.4f} mm3 {' x '.join(sorted(k))}")
    for r in res["results"]: log(f"   {tag}: {r['volume']:10.4f} mm3  {r['la']} x {r['lb']}")
    if res["errors"]: bad += [f"common() failed: {e['la']} x {e['lb']}: {e['error']}" for e in res["errors"]]
    log(f"{tag}: {len(got)} clashes, {len(bad)} mismatches vs lite-18" + "".join(f"\n      {b}" for b in bad))
    return not bad

n_par = int(sys.argv[1]) if len(sys.argv) > 1 else clashlib.default_n()
ok, times = True, {}
for n in (1, n_par):
    tag = f"n={n}"
    res = clashlib.run(MODEL, groups={"plate": PLATE, "magnet": MAGNET}, n=n, tol=TOL, log=log)
    s = res["stats"]; times[n] = s
    log(f"{tag}: wall {s['wall_s']}s; load {s['load_s']}s; clash stage (slowest worker) {s['check_s_max']}s, "
        f"sum over workers {s['check_s_sum']}s; {s['leaves']} leaves, {s['pairs_total']} pairs, {s['box_hits']} box hits")
    ok &= compare(res, tag)
s1, sn = times[1], times[n_par]
log(f"AC2: clash stage serial {s1['check_s_max']}s vs {n_par} workers {sn['check_s_max']}s "
    f"(x{s1['check_s_max'] / max(sn['check_s_max'], 0.1):.1f}); wall {s1['wall_s']}s vs {sn['wall_s']}s "
    f"(lite-18's own serial loop: ~480s, 80 -> ~560s in {os.path.basename(REF_LOG)})")
log("AC1: " + ("PASS, same pairs and volumes as lite-18" if ok else "FAIL"))
