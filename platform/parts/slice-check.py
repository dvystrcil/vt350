#!/usr/bin/env python3
"""Headless slicer check of printed parts (#70): supports, time, filament, warnings, keep-out boxes, a preview.

  python3 platform/parts/slice-check.py <stl…> [--keepout parts/slice/keepout.json] [--out DIR] [--orca parts/slice/orca/orca.json]
  python3 platform/parts/slice-check.py --slicer prusa <stl…> [--profile INI]

The default slicer is OrcaSlicer (gpu-batch-docker#13); --slicer prusa is the original PrusaSlicer check, below.
Orca slices with the Neptune presets the user prints with (parts/slice/orca/: machine, process, filament,
exported from the GUI; orca.json names them). Orca places the part itself (arrange, no re-orienting); keep-out boxes
are mapped through the offset between the STL's centre and the model extrusions' centre. It adds real
estimates: time, grams and cost with the Neptune's own machine limits, speeds and filament density/cost, plus
per-layer time (<part>.layers.csv, slowest layer in the report) and per-feature time, weight and speeds. Orca's
CLI resolves a user preset's `inherits` only against <datadir>/system, which the GUI fills on first run by copying
resources/profiles/<Vendor>.opc and the CLI never does, and only for preset files inside <datadir>/user/default/
<type>/, so slice-check builds that datadir under DIR. The process gets orca.json's `support_check` overrides
(supports on, everywhere, 45°, like the PrusaSlicer profile): the user's own preset has supports off, per plate.
The slicer is ORCA_SLICER (default: the flatpak, com.orcaslicer.OrcaSlicer); system profiles come from
ORCA_PROFILES, else /app/share/OrcaSlicer/profiles (the gpu-batch-orcaslicer image), else the flatpak's.

With --slicer prusa, each STL is sliced by PrusaSlicer's command line (the flatpak, com.prusa3d.PrusaSlicer) with the pinned profile
parts/slice/petg-0.4-0.2.ini (PETG, 0.4 nozzle, 0.2 layers, automatic supports for overhangs flatter than 45°) and
an empty --datadir, so no GUI preset leaks in. The part is sliced in the STL's OWN orientation, so it must already
be print-oriented. PrusaSlicer centres it on the 355 bed (--center); Orca's Neptune bed is 235 square.

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
ORCA_MANIFEST = os.path.join(ROOT, "parts", "slice", "orca", "orca.json")
SLICER = os.environ.get("SLICER", "flatpak run --command=prusa-slicer com.prusa3d.PrusaSlicer").split()
ORCA_SLICER = os.environ.get("ORCA_SLICER", "flatpak run --command=orca-slicer com.orcaslicer.OrcaSlicer").split()
ORCA_FLATPAK = "com.orcaslicer.OrcaSlicer"
CENTRE = (177.5, 177.5)
FIL_AREA = math.pi * (1.75 / 2) ** 2           # mm2: filament mm -> mm3
SUPPORT_COLOUR = "#e0302a"
BOX_COLOUR = "#2a6fe0"


def is_support(t):
    """PrusaSlicer: Support material[ interface]; Orca: Support, Support interface, Support transition"""
    return t.startswith("Support")


def _speed_stats(fs):
    """{min, median, max} of length-weighted feed rates [(mm/s, mm)]"""
    fs = sorted(fs); total = sum(w for _, w in fs); acc = 0.0; med = fs[-1][0]
    for v, w in fs:
        acc += w
        if acc >= total / 2: med = v; break
    return {"min": fs[0][0], "median": med, "max": fs[-1][0]}


def parse_gcode(text):
    """{types: {type: filament mm}, support_mm, support, filament_mm, time, segments: [(type, x0, y0, x1, y1, z)],
    speeds: {type: {min, median, max} mm/s, length-weighted}}. Absolute (M82) or relative (M83) E; an arc (G2/G3)
    counts its filament, and its segment is the chord to its end point."""
    types, segs, feeds = {}, [], {}
    x = y = z = 0.0; e = 0.0; t = None; rel = False; f = 0.0
    filament_mm = None; time_ = None
    for ln in text.splitlines():
        if ln.startswith("M83"):
            rel = True; continue
        if ln.startswith("M82"):
            rel = False; continue
        if ln.startswith(";TYPE:"):
            t = ln[6:].strip(); continue
        if ln.startswith("; filament used [mm] ="):
            filament_mm = sum(float(v) for v in ln.split("=")[1].split(",")); continue   # Orca: one per filament
        if ln.startswith("; estimated printing time (normal mode) ="):
            time_ = ln.split("=", 1)[1].strip(); continue
        if ln.startswith("G92"):
            m = re.search(r"\bE(-?[\d.]+)", ln)
            if m: e = float(m.group(1))
            continue
        if not ln.startswith(("G1 ", "G0 ", "G2 ", "G3 ")):
            continue
        code = ln.split(";", 1)[0]
        v = {k: float(n) for k, n in re.findall(r"([XYZEF])(-?[\d.]+)", code)}
        if "F" in v: f = v["F"]
        nx, ny, nz = v.get("X", x), v.get("Y", y), v.get("Z", z)
        if "E" in v:
            if rel: de = v["E"]
            else: de = v["E"] - e; e = v["E"]
            if de > 0 and t is not None and ("X" in v or "Y" in v):
                types[t] = types.get(t, 0.0) + de
                segs.append((t, x, y, nx, ny, nz))
                feeds.setdefault(t, []).append((round(f / 60, 1), math.hypot(nx - x, ny - y)))
        x, y, z = nx, ny, nz
    sup = sum(v for k, v in types.items() if is_support(k))
    return dict(types=types, support_mm=sup, support=sup > 0, filament_mm=filament_mm, time=time_, segments=segs,
                speeds={k: _speed_stats(v) for k, v in feeds.items()})


def hms(sec):
    """seconds -> '1h 2m 5s'"""
    sec = int(sec); h, r = divmod(sec, 3600); m, s_ = divmod(r, 60)     # truncated, as Orca prints it (9730.5 s = 2h 42m 10s)
    return " ".join(p for p in (f"{h}h" if h else "", f"{m}m" if h or m else "", f"{s_}s") if p)


def orca_estimates(st):
    """estimates from Orca's --export-statistics JSON (plate_N.statistics.json)"""
    u = st.get("units", {})
    if (u.get("time"), u.get("length"), u.get("volume"), u.get("weight")) != ("s", "mm", "mm3", "g"):
        raise ValueError(f"unexpected statistics units {u}")
    s_ = st["summary"]
    layers = [(L["z"], L["time"]) for L in st.get("layers", [])]
    return dict(time=hms(s_["time"]), seconds=s_["time"], grams=s_["weight"], cost=s_.get("filament_cost"),
                filament_mm=sum(f_["length"] for f_ in s_.get("filaments", [])),
                filament_cm3=sum(f_["volume"] for f_ in s_.get("filaments", [])) / 1000,
                support_cm3=sum(o.get("support_volume", 0.0) for o in st.get("objects", [])) / 1000,
                layer_times=layers, slowest_layer=max(layers, key=lambda L: L[1]) if layers else None,
                features=s_.get("features", {}))


def orca_warnings(res):
    """Orca's result.json: the classed `warnings` and each plate's warning_message"""
    w = [f"{x.get('class', '?')}: {x.get('message', '')}".rstrip(": ") for x in res.get("warnings", [])]
    w += [p["warning_message"] for p in res.get("sliced_plates", []) if p.get("warning_message")]
    if res.get("return_code", 0) != 0: w.append(f"error: {res.get('error_string')}")
    return w


def stl_bbox(path):
    """((min x, y, z), (max x, y, z)) of an STL, binary or ASCII"""
    import struct
    data = open(path, "rb").read()
    pts = []
    n = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else -1
    if n >= 0 and len(data) == 84 + 50 * n:
        for i in range(n):
            v = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
            pts += [v[0:3], v[3:6], v[6:9]]
    else:
        pts = [tuple(float(c) for c in m) for m in
               re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


def offset_from_gcode(lo, hi, segs):
    """G-code = STL + offset, for a slicer that places the part itself (Orca arranges it): the XY centre of the
    model's extrusions (support, brim and skirt left out) against the STL's, and the drop to Z 0. Line widths
    and elephant-foot compensation are symmetric, so they cancel in the centre."""
    m = [s for s in segs if not is_support(s[0]) and s[0] not in ("Brim", "Skirt", "Prime tower", "Custom")]
    xs = [c for s in m for c in (s[1], s[3])]; ys = [c for s in m for c in (s[2], s[4])]
    return ((min(xs) + max(xs)) / 2 - (lo[0] + hi[0]) / 2, (min(ys) + max(ys)) / 2 - (lo[1] + hi[1]) / 2, -lo[2])


def orca_profiles_dir():
    if os.environ.get("ORCA_PROFILES"): return os.environ["ORCA_PROFILES"]
    if os.path.isdir("/app/share/OrcaSlicer/profiles"): return "/app/share/OrcaSlicer/profiles"
    loc = subprocess.run(["flatpak", "info", "--show-location", ORCA_FLATPAK], capture_output=True, text=True, check=True)
    return os.path.join(loc.stdout.strip(), "files", "share", "OrcaSlicer", "profiles")


def orca_datadir(dd, manifest, src, profiles):
    """a fresh Orca datadir: the vendors' system profiles in system/, as the GUI installs them, and the three
    presets in user/default/<type>/, the process with the support_check overrides. Returns {type: preset path}."""
    os.makedirs(os.path.join(dd, "system"), exist_ok=True)
    for v in manifest["vendors"]:
        opc = os.path.join(profiles, v + ".opc")
        if not os.path.isfile(opc): raise FileNotFoundError(f"no system profiles for vendor {v}: {opc}")
        shutil.copyfile(opc, os.path.join(dd, "system", v + ".opc"))
    out = {}
    for t in ("machine", "process", "filament"):
        d = os.path.join(dd, "user", "default", t); os.makedirs(d, exist_ok=True)
        cfg = json.load(open(os.path.join(src, manifest[t])))
        if t == "process":
            cfg.update(manifest.get("support_check", {}))
            cfg["name"] = cfg["name"] + " (slice-check)"
        out[t] = os.path.join(d, os.path.basename(manifest[t]))
        with open(out[t], "w") as f: json.dump(cfg, f, indent=4)
    return out


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


def report_md(rows, profile, slicer="prusa"):
    prof = os.path.relpath(profile, ROOT) if os.path.isabs(profile) else profile
    orca = slicer == "orca"
    out = [f"# slice-check report", "", f"Profile: `{prof}` "
           f"({'OrcaSlicer' if orca else 'PrusaSlicer'} CLI, part in its STL orientation). Support volume = support + interface extrusion.", ""]
    if orca:
        out += ["| Part | Support | Support cm³ | Time | Filament cm³ | Grams | Cost | Slowest layer | Slicer warnings | Keep-out | Preview |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
    else:
        out += ["| Part | Support | Support cm³ | Time | Filament cm³ | Slicer warnings | Keep-out | Preview |",
                "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ko = "—" if not r["keepout"] else "**FAIL** " + ", ".join(f"{h['box']} ({h['segments']} segments)" for h in r["keepout"])
        mid = ""
        if orca:
            sl = r.get("slowest_layer")
            mid = (f" {r['grams']:.2f} | {r['cost']:.2f} | "
                   f"{f'{sl[1]:.1f} s @ Z {sl[0]:.2f}' if sl else '—'} |")
        out.append(f"| {r['part']} | {'yes' if r['support'] else 'no'} | {r['support_cm3']:.2f} | {r['time']} | "
                   f"{r['filament_cm3']:.2f} |{mid} {'; '.join(r['warnings']) or '—'} | {ko} | {r['png']} |")
    if orca:
        for r in rows:
            out += ["", f"## {r['part']}", "", f"Per-layer time: `{r['layers_csv']}`. Speeds are the G-code's feed rates "
                    "while extruding, weighted by length.", "",
                    "| Feature | Time | Grams | Min mm/s | Median mm/s | Max mm/s |", "|---|---|---|---|---|---|"]
            for k, v in sorted(r["features"].items(), key=lambda kv: -kv[1].get("time", 0)):
                sp = r["speeds"].get(k)
                spd = " | ".join(f"{sp[q]:.0f}" for q in ("min", "median", "max")) if sp else "— | — | —"
                out.append(f"| {k} | {hms(v.get('time', 0))} | {v.get('weight', 0):.2f} | {spd} |")
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


def run_orca(args):
    r = subprocess.run(ORCA_SLICER + args, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def check_orca(stl, out, manifest_path, boxes):
    name = os.path.splitext(os.path.basename(stl))[0]
    manifest = json.load(open(manifest_path))
    dd = os.path.join(out, ".orca-datadir")
    if not os.path.isdir(os.path.join(dd, "system")):
        orca_datadir(dd, manifest, os.path.dirname(os.path.abspath(manifest_path)), orca_profiles_dir())
    p = {t: os.path.join(dd, "user", "default", t, os.path.basename(manifest[t])) for t in ("machine", "process", "filament")}
    od = os.path.join(out, ".orca-" + name)
    shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    # --orient 0: slice the part as the STL stands; Orca's arrange places it on the bed (offset_from_gcode).
    rc, sl_out = run_orca(["--datadir", dd, "--load-settings", f"{p['machine']};{p['process']}", "--load-filaments",
                           p["filament"], "--orient", "0", "--arrange", "1", "--slice", "0", "--export-statistics",
                           "--outputdir", od, os.path.abspath(stl)])
    with open(os.path.join(out, name + ".slicer.log"), "w") as f: f.write(sl_out)
    res_path = os.path.join(od, "result.json")
    res = json.load(open(res_path)) if os.path.isfile(res_path) else {}
    gsrc = os.path.join(od, "plate_1.gcode")
    if rc != 0 or not os.path.isfile(gsrc):
        raise RuntimeError(f"{stl}: slicing failed ({rc}): {res.get('error_string', '')} {sl_out[-400:]}")
    gcode = os.path.join(out, name + ".gcode")
    shutil.move(gsrc, gcode)
    shutil.move(os.path.join(od, "plate_1.statistics.json"), os.path.join(out, name + ".statistics.json"))
    shutil.move(res_path, os.path.join(out, name + ".result.json"))
    shutil.rmtree(od, ignore_errors=True)
    est = orca_estimates(json.load(open(os.path.join(out, name + ".statistics.json"))))
    g = parse_gcode(open(gcode, encoding="utf-8", errors="replace").read())
    lo, hi = stl_bbox(stl)
    off = offset_from_gcode(lo, hi, g["segments"])
    hits = keepout_hits(g["segments"], boxes, off)
    with open(os.path.join(out, name + ".layers.csv"), "w") as f:
        f.write("z_mm,time_s\n" + "".join(f"{z:.3f},{t:.3f}\n" for z, t in est["layer_times"]))
    with open(os.path.join(out, name + ".svg"), "w") as f:
        f.write(svg(g["segments"], boxes, off, title=f"{os.path.basename(stl)}: support {est['support_cm3']:.2f} cm3, "
                    f"{est['time']}, {est['grams']:.1f} g (OrcaSlicer)"))
    png = name + ".png"
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-o", os.path.join(out, png), os.path.join(out, name + ".svg")], check=True)
    else: png = name + ".svg"
    return dict(part=os.path.basename(stl), support=est["support_cm3"] > 0 or g["support"], support_cm3=est["support_cm3"],
                time=est["time"], filament_cm3=est["filament_cm3"], grams=est["grams"], cost=est["cost"] or 0.0,
                slowest_layer=est["slowest_layer"], features=est["features"], speeds=g["speeds"],
                layers_csv=name + ".layers.csv", warnings=orca_warnings(res), keepout=hits, png=png)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stl", nargs="+")
    ap.add_argument("--keepout", default=KEEPOUT)
    ap.add_argument("--profile", default=PROFILE)
    ap.add_argument("--slicer", choices=("orca", "prusa"), default="orca",
                    help="orca (default): the Neptune presets, real estimates; prusa: the pinned petg-0.4-0.2.ini")
    ap.add_argument("--orca", default=ORCA_MANIFEST, help="orca.json: the presets, vendors and support_check overrides")
    ap.add_argument("--out", default=os.path.expanduser(
        "~/Documents/VT350/slice/" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    a = ap.parse_args()
    ko = json.load(open(a.keepout)) if os.path.isfile(a.keepout) else {}
    validate_keepout(ko)
    os.makedirs(a.out, exist_ok=True)
    rows, fails = [], []
    for stl in a.stl:
        try:
            if a.slicer == "orca": r = check_orca(stl, a.out, os.path.abspath(a.orca), ko.get(os.path.basename(stl), []))
            else: r = check(stl, a.out, os.path.abspath(a.profile), ko.get(os.path.basename(stl), []))
        except RuntimeError as e:
            fails.append(str(e)); print(f"ERROR {e}"); continue
        rows.append(r)
        extra = f", {r['grams']:.2f} g, cost {r['cost']:.2f}" if a.slicer == "orca" else ""
        print(f"{r['part']}: support {'yes' if r['support'] else 'no'} ({r['support_cm3']:.2f} cm3), {r['time']}, "
              f"{r['filament_cm3']:.2f} cm3{extra}; warnings {r['warnings'] or 'none'}; keep-out {r['keepout'] or 'clear'}")
        if r["keepout"]: fails.append(f"{r['part']}: support inside keep-out {[h['box'] for h in r['keepout']]}")
    with open(os.path.join(a.out, "report.md"), "w") as f:
        f.write(report_md(rows, a.orca if a.slicer == "orca" else a.profile, slicer=a.slicer))
    print(f"report: {os.path.join(a.out, 'report.md')}")
    if fails:
        print("slice-check: FAILED: " + " | ".join(fails)); return 1
    print("slice-check: OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
