"""Print lanyard_summary.json (study.py) as the markdown tables posted on vt350#218.  python3 tables.py <summary.json>"""
import json, sys
rows = json.load(open(sys.argv[1]))
def S(r, k, f=lambda v: v): return ", ".join(str(f(r["slots"][s][k])) for s in sorted(r["slots"]))
print("## Ceiling and sag, no lanyard\n")
print("| gantry | EI | tube cut (slots 1-5) | unsolved | ceiling contact % of positions (slots) | longest contact mm | lowest Z | tightest R | docked gaps |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    if r["case"] != "none": continue
    sl = r["slots"].values()
    print(f"| {r['raise_']} | {r['EI']:.0f} | {S(r,'L')} | {sum(x['unsolved'] for x in sl)} | {S(r,'ceiling_pct')} | {max(x['ceiling_max_mm'] for x in sl)} | "
          f"{min(x['lowest'] for x in sl)} | {min(x['minR'] for x in sl)} | {r['docked_gaps']} |")
print("\n## Lanyard cases\n")
print("| gantry | EI | case | unsolved | ceiling % (slots) | lowest Z | tightest R | docked head Fz N (slots; + = lift) | head force p50 / max N | touching a docked bundle % | cord mm min-max | worst cord angle | cord lowest Z | cord crosses docked % (slots) | cross Z |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    sl = list(r["slots"].values())
    cord = r["case"] != "none"
    zs = [x.get("cord_cross_z") for x in sl if x.get("cord_cross_z")]
    print(f"| {r['raise_']} | {r['EI']:.0f} | {r['case']} | {sum(x['unsolved'] for x in sl)} | {S(r,'ceiling_pct')} | {min(x['lowest'] for x in sl)} | "
          f"{min(x['minR'] for x in sl)} | {S(r,'docked_fz')} | {max(x['f_p50'] for x in sl)} / {max(x['f_max'] for x in sl)} | {S(r,'touch_docked_pct')} | "
          + (f"{min(x['cord_min'] for x in sl)}-{max(x['cord_max'] for x in sl)} | {min(x['cord_deg_min'] for x in sl)}° | {min(x['cord_lowest_z'] for x in sl)} | {S(r,'cord_cross_pct')} | "
             f"{(min(z[0] for z in zs), max(z[1] for z in zs)) if zs else '-'} |" if cord else "- | - | - | - | - |"))
