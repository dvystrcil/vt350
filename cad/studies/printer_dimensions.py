#!/usr/bin/env python3
"""The printer's outside dimensions, print area, print height and print volume, as a reference page (vt350#323).

  python3 cad/studies/printer_dimensions.py <lite-N> [--renders DIR] [--no-images]

The first reference page written by a chain link from its own data (owner, 2026-11-25: links that produce data also
write an md or html page). Plain Python, read-only on every input:
  ~/Documents/VT350/vt350-lite-<N>.parts.json   the part index (platform/freecad/part_index.py, refresh step part_index):
                                                 the outside boxes, the nozzle height, the EMU envelope
  cad/data/logs/sweep_toolhead.log + cad/studies/sweep_toolhead.py   the printable area (print_area.printable)
  cad/data/logs/z_sweep.log                      print height and Klipper position_max (refresh step z_sweep)
  ~/Documents/VT350/renders/vt350-lite-<N>-*/out the newest full render of lite-N (cad/render/render_full.sh)
Writes notes/reference/printer-dimensions.html, its images in notes/reference/printer-dimensions/, and
cad/data/printer_dimensions.json. A sweep log from an older lite-N than the part index is used, and the page says so
in a warning box (the refresh replaces it). Prints "printer-dimensions: OK" last.
"""
import argparse
import glob
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import print_area  # noqa: E402

MODELS = os.environ.get("VT350_MODELS_DIR", os.path.expanduser("~/Documents/VT350"))
SWEEP_LOG = os.path.join(REPO, "cad", "data", "logs", "sweep_toolhead.log")
SWEEP_SRC = os.path.join(HERE, "sweep_toolhead.py")
Z_LOG = os.path.join(REPO, "cad", "data", "logs", "z_sweep.log")
OUT = os.path.join(REPO, "notes", "reference", "printer-dimensions.html")
IMG_DIR = os.path.join(REPO, "notes", "reference", "printer-dimensions")
JSON_OUT = os.path.join(REPO, "cad", "data", "printer_dimensions.json")
RENDERS = [("glamour", "The whole printer, EMU on the roof"), ("outside", "Three-quarter front, as you'd walk up to it"),
           ("low_front", "Low front: the doors, the bed and the gantry"), ("ebox_side", "The e-box side, its door taken off for this view")]
FRAME_GROUP = "VT Frame"        # the frame's group label contains this (4040-350 VT Frame v12)
FRAME_BAR = re.compile(r"^(4040|2040|2020)")   # its extrusions (the group also holds the back panel and fasteners)
INCH = 25.4


# ---------- data ----------

def box_of(parts):
    b = [p["bbox"] for p in parts]
    return {k: (min if k.endswith("min") else max)(x[k] for x in b)
            for k in ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")}


def size(b):
    return (round(b["xmax"] - b["xmin"], 1), round(b["ymax"] - b["ymin"], 1), round(b["zmax"] - b["zmin"], 1))


def outside(index):
    """-> {frame, body, emu, with_emu} boxes, the nozzle tip Z and the parts drawn. Envelopes (a stand-in box for a
    separate document) are left out of the body; the EMU's envelope is its outline on the roof."""
    parts = [p for p in index["parts"] if not p["consumed"]]
    env = [p for p in parts if "envelope" in p["label"].lower()]
    body = [p for p in parts if p not in env]
    frame = [p for p in body if len(p["path"]) > 1 and FRAME_GROUP in p["path"][1] and FRAME_BAR.match(p["label"])]
    emu = [p for p in env if p["label"].startswith("EMU")]
    noz = [p["bbox"]["zmin"] for p in body
           if re.search(r"\bnozzle\b", p["label"], re.I) and any("Toolhead" in g for g in p["path"])]
    if not (frame and noz):
        raise SystemExit(f"printer_dimensions: no frame group ({FRAME_GROUP!r}) or no toolhead nozzle in the index")
    out = {"frame": box_of(frame), "body": box_of(body), "nozzle_z": round(min(noz), 2), "parts": body, "frame_parts": frame}
    if emu:
        out["emu"] = box_of(emu)
        out["with_emu"] = box_of(body + emu)
    return out


def lite_of(text):
    m = re.search(r"vt350-lite-(\d+)", text)
    return int(m.group(1)) if m else None


def z_numbers(text):
    def num(key):
        m = re.search(rf"\b{key}=([\d.]+)", text)
        if not m:
            raise SystemExit(f"printer_dimensions: z_sweep.log has no {key}=")
        return float(m.group(1))
    return {"print_height": num("print_height_mm"), "position_max": num("klipper_position_max_mm"),
            "z_travel": num("z_travel_mm")}


def newest_renders(n):
    runs = sorted(glob.glob(os.path.join(MODELS, "renders", f"vt350-lite-{n}-*", "out")))
    runs = [r for r in runs if glob.glob(os.path.join(r, "*glamour.jpg"))]
    return runs[-1] if runs else None


# ---------- drawing ----------

def fmt(mm):
    return f"{mm:.1f} mm ({mm / INCH:.1f} in)"


def svg_view(parts, frame_parts, h, v, flip_v, body, vol, title, dims, emu=None):
    """One orthographic view: every part's box projected, the frame darker, the print volume in orange, and the dims
    as dimension lines. h/v: the axes ('x','y','z') across and up; flip_v draws v downward (top view: rear up)."""
    def rng(b, a):
        return b[a + "min"], b[a + "max"]
    full = dict(body)
    if emu:
        full = {k: (min if k.endswith("min") else max)(body[k], emu[k]) for k in body}
    h0, h1 = rng(full, h)
    v0, v1 = rng(full, v)
    pad_l, pad_r, pad_t, pad_b = 40, 210, 50, 130
    W = h1 - h0 + pad_l + pad_r
    H = v1 - v0 + pad_t + pad_b
    X = lambda a: a - h0 + pad_l
    Y = (lambda a: a - v0 + pad_t) if flip_v else (lambda a: v1 - a + pad_t)

    def rect(b, cls, minarea=0):
        a0, a1 = rng(b, h)
        b0, b1 = rng(b, v)
        if (a1 - a0) * (b1 - b0) < minarea:
            return ""
        y0, y1 = sorted((Y(b0), Y(b1)))
        return f'<rect class="{cls}" x="{X(a0):.0f}" y="{y0:.0f}" width="{max(a1 - a0, 1):.0f}" height="{max(y1 - y0, 1):.0f}"/>'

    frame_ids = {id(p) for p in frame_parts}
    out = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{html.escape(title)}">']
    out += [rect(p["bbox"], "pt", 150) for p in parts if id(p) not in frame_ids]
    out += [rect(p["bbox"], "fr") for p in frame_parts]
    if emu:
        out.append(rect(emu, "emu"))
    out.append(rect(vol, "vol"))

    def hdim(a0, a1, y, label, cls=""):
        x0, x1 = X(a0), X(a1)
        return (f'<g class="dim {cls}"><line x1="{x0:.0f}" y1="{y:.0f}" x2="{x1:.0f}" y2="{y:.0f}"/>'
                f'<line x1="{x0:.0f}" y1="{y - 10:.0f}" x2="{x0:.0f}" y2="{y + 10:.0f}"/>'
                f'<line x1="{x1:.0f}" y1="{y - 10:.0f}" x2="{x1:.0f}" y2="{y + 10:.0f}"/>'
                f'<text x="{(x0 + x1) / 2:.0f}" y="{y + 34:.0f}" text-anchor="middle">{label}</text></g>')

    def vdim(b0, b1, x, label, cls=""):
        y0, y1 = sorted((Y(b0), Y(b1)))
        return (f'<g class="dim {cls}"><line x1="{x:.0f}" y1="{y0:.0f}" x2="{x:.0f}" y2="{y1:.0f}"/>'
                f'<line x1="{x - 10:.0f}" y1="{y0:.0f}" x2="{x + 10:.0f}" y2="{y0:.0f}"/>'
                f'<line x1="{x - 10:.0f}" y1="{y1:.0f}" x2="{x + 10:.0f}" y2="{y1:.0f}"/>'
                f'<text x="{x + 16:.0f}" y="{(y0 + y1) / 2 + 8:.0f}">{label}</text></g>')

    base = max(Y(v0), Y(v1))
    for kind, (a0, a1), label in dims:
        if kind == "h":
            out.append(hdim(a0, a1, base + 40, label))
        elif kind == "hv":
            out.append(hdim(a0, a1, base + 95, label, "v"))
        elif kind == "v":
            out.append(vdim(a0, a1, X(h1) + 30, label))
        elif kind == "v2":
            out.append(vdim(a0, a1, X(h1) + 120, label))
        elif kind == "vv":
            out.append(vdim(a0, a1, X(rng(vol, h)[1]) + 16, label, "v"))
    out.append("</svg>")
    return "\n".join(x for x in out if x)


# ---------- page ----------

CSS = """
/* Layout: a drawing sheet. The headline numbers, three orthographic views to scale, the renders, then the sources. */
:root {
  --bg: #F3F4F1; --panel: #FFFFFF; --fg: #1D211B; --muted: #5C6457; --line: #D5D9D0;
  --accent: #4E6B3D; --frame: #6E8C5B; --part: #B9BFB2; --vol: #E0701F; --warn: #9A5B00; --warnbg: #FFF4E0;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #121411; --panel: #1A1D18; --fg: #E6E9E2; --muted: #9AA294; --line: #2E332B; --accent: #A6C28F;
  --frame: #7FA06A; --part: #4A5145; --vol: #F08A3C; --warn: #F0B45A; --warnbg: #2A2112; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #121411; --panel: #1A1D18; --fg: #E6E9E2; --muted: #9AA294; --line: #2E332B; --accent: #A6C28F;
  --frame: #7FA06A; --part: #4A5145; --vol: #F08A3C; --warn: #F0B45A; --warnbg: #2A2112; color-scheme: dark }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 15px; line-height: 1.5; }
.wrap { max-width: 1400px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }
header { display: grid; gap: 8px; }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
h1 { margin: 0; font-size: clamp(24px, 3.2vw, 34px); font-weight: 600; text-wrap: balance; }
h2 { margin: 0; font-size: 18px; font-weight: 600; text-wrap: balance; }
p { margin: 0; max-width: 72ch; color: var(--muted); }
p strong { color: var(--fg); font-weight: 600; }
a { color: var(--accent); }
code { font-family: var(--mono); font-size: .92em; }
.hero { margin: 0; display: grid; gap: 6px; }
.hero img { width: 100%; max-width: 100%; height: auto; display: block; border-radius: 6px; background: #111; }
.figs { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr)); gap: 12px; }
figure { margin: 0; display: grid; gap: 4px; min-width: 0; }
figure img { width: 100%; height: auto; display: block; border-radius: 4px; background: #111; }
figcaption { font-family: var(--mono); font-size: 12px; color: var(--muted); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); gap: 12px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; display: grid; gap: 2px; min-width: 0; }
.stat b { font-family: var(--mono); font-size: 22px; font-weight: 500; font-variant-numeric: tabular-nums; }
.stat small { color: var(--muted); font-size: 12.5px; }
.stat.vol { border-left: 4px solid var(--vol); }
.stat.out { border-left: 4px solid var(--frame); }
.warn { background: var(--warnbg); border: 1px solid var(--line); border-left: 4px solid var(--warn); border-radius: 6px; padding: 12px 16px; display: grid; gap: 6px; }
.warn p { color: var(--fg); }
.note { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; display: grid; gap: 8px; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 18px 6px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
th { font-weight: 500; color: var(--muted); }
td.n { font-family: var(--mono); }
.views { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 16px; }
.view { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 12px; display: grid; gap: 8px; min-width: 0; }
.view h3 { margin: 0; font-size: 14px; font-weight: 600; }
.view svg { width: 100%; max-width: 100%; height: auto; display: block; }
.pt { fill: var(--part); opacity: .35; }
.fr { fill: var(--frame); opacity: .8; }
.emu { fill: none; stroke: var(--muted); stroke-width: 3; stroke-dasharray: 12 8; }
.vol { fill: var(--vol); fill-opacity: .28; stroke: var(--vol); stroke-width: 3; }
.dim line { stroke: var(--fg); stroke-width: 2; }
.dim text { fill: var(--fg); font-family: var(--mono); font-size: 24px; }
.dim.v line { stroke: var(--vol); }
.dim.v text { fill: var(--vol); }
.key { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; color: var(--muted); }
.key i { display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: -1px; margin-right: 6px; }
ul { margin: 0; padding-left: 20px; color: var(--muted); max-width: 80ch; display: grid; gap: 4px; }
footer { color: var(--muted); font-size: 12.5px; display: grid; gap: 6px; }
"""


def page(d, imgs):
    n, o, pr = d["model"], d["outside"], d["print"]
    W, D, H = o["printer"]
    fw, fd, fh = o["frame"]
    e = lambda s: html.escape(str(s))
    rows = [("Frame (the extrusions alone)", o["frame"]), ("Printer (feet to the roof cable channel; doors, e-box, base board)", o["printer"])]
    if o.get("with_emu"):
        rows.append(("Printer with the EMU on the roof", o["with_emu"]))
    trs = "\n".join(f"<tr><td>{e(k)}</td><td class=n>{fmt(v[0])}</td><td class=n>{fmt(v[1])}</td><td class=n>{fmt(v[2])}</td></tr>"
                    for k, v in rows)
    stale = ""
    if d["stale"]:
        stale = ('<div class="warn"><p><strong>Print numbers from an older model.</strong> ' + e(d["stale"]) +
                 " The outside dimensions and the drawings are lite-" + e(n) + "'s. The lite-" + e(n) +
                 " refresh rewrites this page with its own numbers.</p></div>")
    hero = figs = ""
    if imgs:
        first, rest = imgs[0], imgs[1:]
        hero = (f'<figure class="hero"><img src="printer-dimensions/{e(first[0])}" alt="{e(first[1])}" '
                f'width="1920" height="1080"><figcaption>{e(first[1])} (lite-{e(n)}, Cycles)</figcaption></figure>')
        figs = "<div class=figs>" + "".join(
            f'<figure><img src="printer-dimensions/{e(f)}" alt="{e(c)}" loading="lazy" width="1920" height="1080">'
            f'<figcaption>{e(c)}</figcaption></figure>' for f, c in rest) + "</div>"
    vol_l = pr["volume_l"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>VT350 Dimensions</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Reference · vt350-lite-{e(n)} · generated {e(d["generated"])}</div>
  <h1>VT350 dimensions</h1>
  <p>The printer as modelled in <strong>lite-{e(n)}</strong>: how much room it takes, and how much it prints.
  This page is written by <code>cad/studies/printer_dimensions.py</code> from the model's part index and the refresh
  sweeps, and rewritten on every refresh, so its numbers are the model's.</p>
</header>
{stale}
<div class="stats">
  <div class="stat out"><small>Outside, W × D × H</small><b>{W:.0f} × {D:.0f} × {H:.0f} mm</b><small>{W / INCH:.1f} × {D / INCH:.1f} × {H / INCH:.1f} in, without the EMU</small></div>
  <div class="stat vol"><small>Print area, W × D</small><b>{pr["width"]:.1f} × {pr["depth"]:.1f} mm</b><small>{pr["width"] / INCH:.2f} × {pr["depth"] / INCH:.2f} in, every head reaches it</small></div>
  <div class="stat vol"><small>Print height</small><b>{pr["height"]:.1f} mm</b><small>{pr["height"] / INCH:.2f} in · Klipper position_max {pr["position_max"]:.2f}</small></div>
  <div class="stat vol"><small>Print volume</small><b>{vol_l:.1f} L</b><small>{vol_l * 61.0237:.0f} in³ · {vol_l / 28.3168:.2f} ft³</small></div>
</div>
{hero}
<section class="note">
  <h2>Outside dimensions</h2>
  <div class="tablewrap"><table>
    <tr><th></th><th>Width (X)</th><th>Depth (Y)</th><th>Height (Z)</th></tr>
    {trs}
  </table></div>
  <ul>
    <li>Width runs left to right as you face the doors; the e-box hangs on the right side. Depth runs front to back,
    door to rear cable channel. Height runs from the floor under the levelling feet.</li>
    <li>Boxes of every modelled part. Door handles and the doors' swing aren't included: allow
    {d["door_swing_note"]} in front for the doors to open.</li>
    <li><strong>Not modelled yet:</strong> the bowden arms and dancers behind the gantry (vt350#312, #244). They sit
    inside the frame's outline, so these outside numbers shouldn't change; the EMU's bowdens above the roof may.</li>
  </ul>
</section>
<section class="note">
  <h2>Drawn to scale</h2>
  <div class="key"><span><i style="background:var(--frame)"></i>frame extrusions</span><span><i style="background:var(--part);opacity:.6"></i>every other part</span><span><i style="background:var(--vol);opacity:.5"></i>print volume</span>{'<span><i style="border:2px dashed var(--muted)"></i>EMU on the roof (the side view’s outer height includes it)</span>' if o.get("with_emu") else ""}</div>
  <div class="views">
    <div class="view"><h3>Front</h3>{d["svg"]["front"]}</div>
    <div class="view"><h3>Right side</h3>{d["svg"]["side"]}</div>
    <div class="view"><h3>Top</h3>{d["svg"]["top"]}</div>
  </div>
</section>
<section class="note">
  <h2>Print volume</h2>
  <div class="tablewrap"><table>
    <tr><th></th><th>mm</th><th>in</th><th>From</th></tr>
    <tr><td>Print area, width (X)</td><td class=n>{pr["width"]:.2f}</td><td class=n>{pr["width"] / INCH:.2f}</td><td>{e(d["src"]["sweep"])}</td></tr>
    <tr><td>Print area, depth (Y)</td><td class=n>{pr["depth"]:.2f}</td><td class=n>{pr["depth"] / INCH:.2f}</td><td>{e(d["src"]["sweep"])}</td></tr>
    <tr><td>Print height (Z)</td><td class=n>{pr["height"]:.2f}</td><td class=n>{pr["height"] / INCH:.2f}</td><td>{e(d["src"]["z"])}</td></tr>
    <tr><td>Bed travel, end to end</td><td class=n>{pr["z_travel"]:.2f}</td><td class=n>{pr["z_travel"] / INCH:.2f}</td><td>{e(d["src"]["z"])}</td></tr>
    <tr><td>Nozzle tips (model Z)</td><td class=n>{d["nozzle_z"]:.2f}</td><td class=n>{d["nozzle_z"] / INCH:.2f}</td><td>part index</td></tr>
  </table></div>
  <ul>
    <li>The print area is where <em>every</em> head reaches, the tightest head on each side, clamped to the 350 plate's
    square (<code>print_area.py</code>). Loss against the full square: {e(", ".join(f"{k} {v}" for k, v in pr["loss"].items()))} mm.</li>
    <li>Print height runs from the print surface at the bed's lowest stop up to the nozzle (<code>z_sweep.py</code>,
    by boolean contact).</li>
  </ul>
</section>
{figs}
<footer>
  <div>Sources: <code>{e(d["src"]["index"])}</code> ({e(d["parts_count"])} parts); {e(d["src"]["sweep"])}; {e(d["src"]["z"])}; renders {e(d["src"]["renders"] or "none")}.</div>
  <div>Regenerate: <code>python3 cad/studies/printer_dimensions.py {e(n)}</code>. Tracked in
  <a href="https://github.com/dvystrcil/vt350/issues/323">vt350#323</a>.</div>
</footer>
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("n", type=int, help="lite-N")
    ap.add_argument("--renders", help="a render run's out/ dir (default: the newest of lite-N)")
    ap.add_argument("--no-images", action="store_true", help="leave the render images out")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    idx_path = os.path.join(MODELS, f"vt350-lite-{a.n}.parts.json")
    index = json.load(open(idx_path, encoding="utf-8"))
    o = outside(index)
    sweep_txt, z_txt = open(SWEEP_LOG, encoding="utf-8").read(), open(Z_LOG, encoding="utf-8").read()
    reach, plate = print_area.parse_reach(sweep_txt), print_area.parse_plate(open(SWEEP_SRC, encoding="utf-8").read())
    pa = print_area.printable(reach, plate)
    z = z_numbers(z_txt)
    sweep_n, z_n = lite_of(sweep_txt), lite_of(z_txt)
    olds = sorted({m for m in (sweep_n, z_n) if m != a.n})
    stale = (f"The print area and height come from lite-{' and lite-'.join(map(str, olds))}'s sweeps." if olds else "")
    x0, y0 = pa["origin"]
    ar = pa["area"]
    vol = {"xmin": x0 + ar[0], "xmax": x0 + ar[2], "ymin": y0 + ar[1], "ymax": y0 + ar[3],
           "zmin": o["nozzle_z"] - z["print_height"], "zmax": o["nozzle_z"]}
    pr = {"width": pa["width"], "depth": pa["depth"], "height": z["print_height"], "position_max": z["position_max"],
          "z_travel": z["z_travel"], "loss": pa["loss"],
          "volume_l": round(pa["width"] * pa["depth"] * z["print_height"] / 1e6, 2)}
    body, frame = o["body"], o["frame"]
    emu = o.get("emu")
    top_z = (o["with_emu"] if emu else body)
    svg = {
        "front": svg_view(o["parts"], o["frame_parts"], "x", "z", False, body, vol, "Front view", [
            ("h", (body["xmin"], body["xmax"]), f"{body['xmax'] - body['xmin']:.0f}"),
            ("hv", (vol["xmin"], vol["xmax"]), f"{pr['width']:.0f}"),
            ("v", (body["zmin"], body["zmax"]), f"{body['zmax'] - body['zmin']:.0f}"),
            ("vv", (vol["zmin"], vol["zmax"]), f"{pr['height']:.0f}")], emu),
        "side": svg_view(o["parts"], o["frame_parts"], "y", "z", False, body, vol, "Right side view", [
            ("h", (body["ymin"], body["ymax"]), f"{body['ymax'] - body['ymin']:.0f}"),
            ("hv", (vol["ymin"], vol["ymax"]), f"{pr['depth']:.0f}"),
            ("v", (body["zmin"], body["zmax"]), f"{body['zmax'] - body['zmin']:.0f}"),
            ("vv", (vol["zmin"], vol["zmax"]), f"{pr['height']:.0f}")]
            + ([("v2", (body["zmin"], top_z["zmax"]), f"{top_z['zmax'] - body['zmin']:.0f}")] if emu else []), emu),
        "top": svg_view(o["parts"], o["frame_parts"], "x", "y", False, body, vol, "Top view", [
            ("h", (body["xmin"], body["xmax"]), f"{body['xmax'] - body['xmin']:.0f}"),
            ("v", (body["ymin"], body["ymax"]), f"{body['ymax'] - body['ymin']:.0f}")]),
    }
    imgs, rdir = [], None
    if not a.no_images:
        rdir = a.renders or newest_renders(a.n)
        if rdir:
            os.makedirs(IMG_DIR, exist_ok=True)
            for old in glob.glob(os.path.join(IMG_DIR, "*.jpg")):
                os.remove(old)
            for view, cap in RENDERS:
                src = glob.glob(os.path.join(rdir, f"*-{view}.jpg"))
                if src:
                    dst = f"lite-{a.n}-{view}.jpg"
                    shutil.copyfile(src[0], os.path.join(IMG_DIR, dst))
                    imgs.append((dst, cap))
    d = {"model": a.n, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
         "outside": {"frame": size(frame), "printer": size(body), "with_emu": size(o["with_emu"]) if emu else None},
         "boxes": {"frame": frame, "printer": body, "emu": emu, "print_volume": vol},
         "print": pr, "nozzle_z": o["nozzle_z"], "parts_count": len(o["parts"]), "stale": stale,
         "door_swing_note": "about the door's width",
         "src": {"index": os.path.basename(idx_path), "sweep": f"sweep_toolhead.log (lite-{sweep_n})",
                 "z": f"z_sweep.log (lite-{z_n})", "renders": os.path.basename(os.path.dirname(rdir)) if rdir else None}}
    d["svg"] = svg
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page(d, imgs))
    js = {k: v for k, v in d.items() if k != "svg"}
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(js, f, indent=1)
        f.write("\n")
    W, D, H = d["outside"]["printer"]
    print(f"lite-{a.n}: outside {W} x {D} x {H} mm; print {pr['width']} x {pr['depth']} x {pr['height']} mm = "
          f"{pr['volume_l']} L{' (' + stale + ')' if stale else ''} -> {os.path.relpath(a.out, REPO)}")
    print("printer-dimensions: OK")


if __name__ == "__main__":
    main()
