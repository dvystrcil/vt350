#!/usr/bin/env python3
"""Headless slicer check of printed parts (#70): supports, time, filament, warnings, keep-out boxes, a preview.

  python3 platform/parts/slice-check.py <stl…> [--keepout parts/slice/keepout.json] [--out DIR] [--profile INI]

Each STL is sliced by PrusaSlicer's command line (the flatpak, com.prusa3d.PrusaSlicer) with the pinned profile
parts/slice/petg-0.4-0.2.ini (PETG, 0.4 nozzle, 0.2 layers, automatic supports for overhangs flatter than 45°) and
an empty --datadir, so no GUI preset leaks in. The part is sliced in the STL's OWN orientation, so it must already
be print-oriented. It's centred on the 355 bed (--center).

Per part it reports:
  - support yes/no and its volume, from the G-code's ;TYPE:Support material / interface extrusions;
  - estimated time and filament, from the G-code footer;
  - the slicer's stability warnings, from its console output;
  - keep-out boxes: support G-code inside one is a FAIL.

Keep-out boxes are in the STL's own coordinates, in keepout.json: {"<stl file name>": [{"name", "min": [x,y,z],
"max": [x,y,z]}]}.

The preview is a PNG plot of the G-code (top, front and side views; support red, keep-out boxes blue). The
PrusaSlicer 2.9 CLI has no preview or PNG export: `--help` lists only --export-gcode/--info/… for FFF, and the
`thumbnails` setting renders the model without supports.

Output goes to DIR (default ~/Documents/VT350/slice/<UTC>/): report.md, <part>.gcode, <part>.png. The default is
under $HOME because the flatpak can't see /tmp. The last line is "slice-check: OK", or "slice-check: FAILED ..."
with exit 1 (slicer error or a keep-out hit). Stdlib only; the PNG needs `rsvg-convert` (librsvg), and without it
only the SVG is written.
"""
import argparse
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))      # the checkout: the profile + keep-outs are the printer's (vt350#122)
PROFILE = os.path.join(ROOT, "parts", "slice", "petg-0.4-0.2.ini")
KEEPOUT = os.path.join(ROOT, "parts", "slice", "keepout.json")
SLICER = os.environ.get("SLICER", "flatpak run --command=prusa-slicer com.prusa3d.PrusaSlicer").split()
CENTRE = (177.5, 177.5)
FIL_AREA = math.pi * (1.75 / 2) ** 2           # mm2: filament mm -> mm3
SUPPORT_COLOUR = "#e0302a"
BOX_COLOUR = "#2a6fe0"


def is_support(t):
    return t.startswith("Support material")


def parse_gcode(text):
    """{types: {type: filament mm}, support_mm, support, filament_mm, time, segments: [(type, x0, y0, x1, y1, z)]}"""
    types, segs = {}, []
    x = y = z = 0.0; e = 0.0; t = None
    filament_mm = None; time_ = None
    for ln in text.splitlines():
        if ln.startswith(";TYPE:"):
            t = ln[6:].strip(); continue
        if ln.startswith("; filament used [mm] ="):
            filament_mm = float(ln.split("=")[1]); continue
        if ln.startswith("; estimated printing time (normal mode) ="):
            time_ = ln.split("=", 1)[1].strip(); continue
        if ln.startswith("G92"):
            m = re.search(r"\bE(-?[\d.]+)", ln)
            if m: e = float(m.group(1))
            continue
        if not (ln.startswith("G1 ") or ln.startswith("G0 ")):
            continue
        code = ln.split(";", 1)[0]
        v = {k: float(n) for k, n in re.findall(r"([XYZE])(-?[\d.]+)", code)}
        nx, ny, nz = v.get("X", x), v.get("Y", y), v.get("Z", z)
        if "E" in v:
            de = v["E"] - e; e = v["E"]
            if de > 0 and t is not None and ("X" in v or "Y" in v):
                types[t] = types.get(t, 0.0) + de
                segs.append((t, x, y, nx, ny, nz))
        x, y, z = nx, ny, nz
    sup = sum(v for k, v in types.items() if is_support(k))
    return dict(types=types, support_mm=sup, support=sup > 0, filament_mm=filament_mm, time=time_, segments=segs)


def parse_info(out):
    i = {}
    for ln in out.splitlines():
        m = re.match(r"^(\w+) = (.*)$", ln.strip())
        if m:
            try: i[m.group(1)] = float(m.group(2))
            except ValueError: i[m.group(1)] = m.group(2)
    return i


def slicer_warnings(out):
    """PrusaSlicer prints 'Detected print stability issues:' then one issue per line until a blank or progress line"""
    w, lines = [], out.splitlines()
    for k, ln in enumerate(lines):
        if ln.strip().startswith("Detected print stability issues"):
            items = []
            for nxt in lines[k + 1:]:
                s = nxt.strip()
                if not s and items: break
                if re.match(r"^\d+ =>", s): break
                if s: items.append(s)
            w.append("Detected print stability issues: " + "; ".join(items))
        elif re.search(r"\b(warning|error)\b", ln, re.I) and "=>" not in ln and "export file name" not in ln:
            w.append(ln.strip())
    return w


def offset_for(info, centre=CENTRE):
    """G-code = STL + offset: the slicer centres the bounding box on the bed and drops the part to Z 0"""
    return (centre[0] - (info["min_x"] + info["max_x"]) / 2, centre[1] - (info["min_y"] + info["max_y"]) / 2,
            -info["min_z"])


def validate_keepout(k):
    for part, boxes in k.items():
        if part.startswith("_"): continue                       # notes
        for b in boxes:
            if not b.get("name") or len(b.get("min", [])) != 3 or len(b.get("max", [])) != 3:
                raise ValueError(f"{part}: each box needs name, min [x,y,z], max [x,y,z]: {b}")
            if any(lo >= hi for lo, hi in zip(b["min"], b["max"])):
                raise ValueError(f"{part}: box {b['name']}: min must be below max on every axis")


def keepout_hits(segs, boxes, offset, step=0.5):
    """support segments with any point (sampled every `step` mm) inside a box, boxes in STL coordinates"""
    out = []
    for b in boxes:
        lo = [b["min"][i] + offset[i] for i in range(3)]; hi = [b["max"][i] + offset[i] for i in range(3)]
        n = 0
        for t, x0, y0, x1, y1, z in segs:
            if not is_support(t) or not (lo[2] <= z <= hi[2]): continue
            k = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            if any(lo[0] <= x0 + (x1 - x0) * i / k <= hi[0] and lo[1] <= y0 + (y1 - y0) * i / k <= hi[1] for i in range(k + 1)):
                n += 1
        if n: out.append(dict(box=b["name"], segments=n))
    return out


def svg(segs, boxes, offset, title="", size=420):
    """three orthographic views of the extrusions: top (X,Y), front (X,Z), side (Y,Z); support red, model grey"""
    if not segs:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="60"><text x="10" y="30">{title}: no extrusions</text></svg>'
    xs = [c for s in segs for c in (s[1], s[3])]; ys = [c for s in segs for c in (s[2], s[4])]; zs = [s[5] for s in segs]
    rng = {"x": (min(xs), max(xs)), "y": (min(ys), max(ys)), "z": (0.0, max(zs))}
    span = max(max(h - l for l, h in rng.values()), 1.0); sc_ = (size - 40) / span
    views = [("top (X right, Y up)", "x", "y"), ("front (X right, Z up)", "x", "z"), ("side (Y right, Z up)", "y", "z")]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{3 * size}" height="{size + 50}" font-family="sans-serif" font-size="13">',
             f'<rect width="100%" height="100%" fill="white"/><text x="10" y="20" font-size="15">{title}</text>']
    def P(seg, a):
        _, x0, y0, x1, y1, z = seg
        return {"x": (x0, x1), "y": (y0, y1), "z": (z, z)}[a]
    for vi, (name, a, b) in enumerate(views):
        ox = vi * size + 20
        def tx(v, ax=a): return ox + (v - rng[ax][0]) * sc_
        def ty(v, ax=b): return size + 20 - (v - rng[ax][0]) * sc_
        parts.append(f'<g class="view"><text x="{ox}" y="40">{name}</text>')
        for sup in (False, True):
            d = []
            for s in segs:
                if is_support(s[0]) != sup: continue
                (a0, a1), (b0, b1) = P(s, a), P(s, b)
                d.append(f"M{tx(a0):.1f} {ty(b0):.1f}L{tx(a1):.1f} {ty(b1):.1f}")
            if d:
                col, w, op = (SUPPORT_COLOUR, 1.2, 0.9) if sup else ("#666", 0.6, 0.25)
                parts.append(f'<path d="{"".join(d)}" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}" fill="none"/>')
        for bx in boxes:
            idx = {"x": 0, "y": 1, "z": 2}
            lo = [bx["min"][i] + offset[i] for i in range(3)]; hi = [bx["max"][i] + offset[i] for i in range(3)]
            X0, X1 = tx(lo[idx[a]]), tx(hi[idx[a]]); Y0, Y1 = ty(hi[idx[b]]), ty(lo[idx[b]])
            parts.append(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1 - X0:.1f}" height="{Y1 - Y0:.1f}" fill="{BOX_COLOUR}" '
                         f'fill-opacity="0.15" stroke="{BOX_COLOUR}"/><text x="{X0:.1f}" y="{Y0 - 3:.1f}" fill="{BOX_COLOUR}">{bx["name"]}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts)


def report_md(rows, profile):
    out = [f"# slice-check report", "", f"Profile: `{os.path.relpath(profile, ROOT) if os.path.isabs(profile) else profile}` "
           "(PrusaSlicer CLI, part in its STL orientation). Support volume = support + interface extrusion.", "",
           "| Part | Support | Support cm³ | Time | Filament cm³ | Slicer warnings | Keep-out | Preview |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ko = "—" if not r["keepout"] else "**FAIL** " + ", ".join(f"{h['box']} ({h['segments']} segments)" for h in r["keepout"])
        out.append(f"| {r['part']} | {'yes' if r['support'] else 'no'} | {r['support_cm3']:.2f} | {r['time']} | "
                   f"{r['filament_cm3']:.2f} | {'; '.join(r['warnings']) or '—'} | {ko} | {r['png']} |")
    return "\n".join(out) + "\n"


def run_slicer(args):
    r = subprocess.run(SLICER + args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def check(stl, out, profile, boxes):
    name = os.path.splitext(os.path.basename(stl))[0]
    datadir = os.path.join(out, ".datadir"); os.makedirs(datadir, exist_ok=True)
    base = ["--datadir", datadir, "--load", profile]
    rc, info_out = run_slicer(base + ["--info", os.path.abspath(stl)])
    if rc != 0: raise RuntimeError(f"{stl}: --info failed ({rc}): {info_out[-400:]}")
    info = parse_info(info_out)
    gcode = os.path.join(out, name + ".gcode")
    rc, sl_out = run_slicer(base + ["--center", f"{CENTRE[0]},{CENTRE[1]}", "--export-gcode", "-o", gcode, os.path.abspath(stl)])
    with open(os.path.join(out, name + ".slicer.log"), "w") as f: f.write(sl_out)
    if rc != 0 or not os.path.isfile(gcode): raise RuntimeError(f"{stl}: slicing failed ({rc}): {sl_out[-400:]}")
    g = parse_gcode(open(gcode, encoding="utf-8", errors="replace").read())
    off = offset_for(info)
    hits = keepout_hits(g["segments"], boxes, off)
    with open(os.path.join(out, name + ".svg"), "w") as f:
        f.write(svg(g["segments"], boxes, off, title=f"{os.path.basename(stl)}: support {g['support_mm'] * FIL_AREA / 1000:.2f} cm3"))
    png = name + ".png"
    if shutil.which("rsvg-convert"):          # fast; ImageMagick's own SVG renderer takes minutes on a 6 MB plot
        subprocess.run(["rsvg-convert", "-o", os.path.join(out, png), os.path.join(out, name + ".svg")], check=True)
    else: png = name + ".svg"
    warn = slicer_warnings(sl_out)
    if info.get("manifold") == "no": warn.append("mesh not manifold")
    return dict(part=os.path.basename(stl), support=g["support"], support_cm3=g["support_mm"] * FIL_AREA / 1000,
                time=g["time"] or "?", filament_cm3=(g["filament_mm"] or 0) * FIL_AREA / 1000, warnings=warn,
                keepout=hits, png=png)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stl", nargs="+")
    ap.add_argument("--keepout", default=KEEPOUT)
    ap.add_argument("--profile", default=PROFILE)
    ap.add_argument("--out", default=os.path.expanduser(
        "~/Documents/VT350/slice/" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    a = ap.parse_args()
    ko = json.load(open(a.keepout)) if os.path.isfile(a.keepout) else {}
    validate_keepout(ko)
    os.makedirs(a.out, exist_ok=True)
    rows, fails = [], []
    for stl in a.stl:
        try:
            r = check(stl, a.out, os.path.abspath(a.profile), ko.get(os.path.basename(stl), []))
        except RuntimeError as e:
            fails.append(str(e)); print(f"ERROR {e}"); continue
        rows.append(r)
        print(f"{r['part']}: support {'yes' if r['support'] else 'no'} ({r['support_cm3']:.2f} cm3), {r['time']}, "
              f"{r['filament_cm3']:.2f} cm3; warnings {r['warnings'] or 'none'}; keep-out {r['keepout'] or 'clear'}")
        if r["keepout"]: fails.append(f"{r['part']}: support inside keep-out {[h['box'] for h in r['keepout']]}")
    with open(os.path.join(a.out, "report.md"), "w") as f: f.write(report_md(rows, a.profile))
    print(f"report: {os.path.join(a.out, 'report.md')}")
    if fails:
        print("slice-check: FAILED: " + " | ".join(fails)); return 1
    print("slice-check: OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
