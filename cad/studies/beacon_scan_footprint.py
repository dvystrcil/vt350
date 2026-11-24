#!/usr/bin/env python3
"""Side view of the Beacon's scan footprint at the head's forward limit (vt350#291, #309). Plain python, read-only.

Where does the Beacon sense the bed when the head is as far forward as it can go? For three X positions (most of the
width, a gap between docks, the best spot) it takes the nozzle's forward limit (the worse of the two heads, lite-78
front: cad/data/front_reach_front17.json), puts the coil y_offset behind it, and draws the coil housing with a
trapezoid from the coil face down to the bed.

The trapezoid's flare is a STAND-IN. Beacon publishes no downward sensing cone. Its STEP (Beacon_RevH_Assm_Normal,
MIT) has the coil housing (17 mm across, 2.6 tall) and a metal keep-out cone ABOVE the board (17 -> 18.75 mm across
over 20 mm). The trapezoid uses that same flare downward, so at the scan height it is barely wider than the coil.

Run: python3 cad/studies/beacon_scan_footprint.py [--y-offset 27.4]  ->  cad/data/beacon_scan_footprint.svg
"""
import argparse, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
FRONT_REACH = os.path.join(CAD, "data", "front_reach_front17.json")
MAPPING = os.path.join(CAD, "klipper", "xy_mapping.json")
OUT = os.path.join(CAD, "data", "beacon_scan_footprint.svg")

PLATE_FRONT = -2.5        # printer Y of the plate's front edge (355 plate, 350 print square, centred; print_area.py)
PRINTABLE_FRONT = 2.5     # printer Y of the printable front edge (print_area.py)
MESH_MIN_Y = 5.48         # beacon.cfg mesh_min Y (coil fully on the plate)
SCAN_Z = 2.0              # nozzle height during the scan (beacon trigger_distance, cad/motion/beacon_scan.py)
COIL_ABOVE_TIP = 2.6      # coil face above the nozzle tip (lite24_beacon.py)
HOUSING_D, HOUSING_H = 17.0, 2.6                 # Beacon STEP: the coil housing under the board
FLARE = (18.75 - 17.0) / 2 / 20.0                # Beacon STEP keep-out cone: radius growth per mm (stand-in, see above)
SAMPLES = (("most of the width", 175.0), ("gap between docks", 50.0), ("best spot", 205.0))   # printer X


def nozzle_front(front, mapping):
    """printer X -> nozzle's forward limit, printer Y (worse head), at each sample of the front reach map."""
    (ox, oy), (gx, gy) = mapping["origin_model_xy"], mapping["sign_xy"]
    rows = {}
    for h, rs in front["heads"].items():
        for r in rs:
            x = round(gx * (r["x"] - ox), 2)
            rows.setdefault(x, []).append(round(gy * (r["clear"] - oy), 2))
    return {x: max(v) for x, v in rows.items() if len(v) == len(front["heads"])}


def footprints(front, mapping, dy):
    """One row per sample X: nozzle Y, coil centre Y, footprint front edge at the bed (printer and plate Y)."""
    nf = nozzle_front(front, mapping)
    half = HOUSING_D / 2 + FLARE * (SCAN_Z + COIL_ABOVE_TIP)
    out = []
    for name, x in SAMPLES:
        sx = min(nf, key=lambda a: abs(a - x))
        ny = nf[sx]; cy = ny + dy
        out.append(dict(name=name, x=sx, nozzle=ny, coil=round(cy, 2), front=round(cy - half, 2),
                        plate_coil=round(cy - PLATE_FRONT, 2), plate_front=round(cy - half - PLATE_FRONT, 2)))
    return out, round(half, 2)


def svg(rows, half, dy):
    """Three lanes (one per sample X), one Y scale, so the front edges line up for comparison."""
    sc = 14.0; y0, y1, zlo, zhi = -32.0, 42.0, -2.0, 9.0          # plate Y window; Z window per lane (mm)
    LH = (zhi - zlo) * sc + 30                                     # lane height px
    W, top0 = (y1 - y0) * sc, 50
    pl = lambda y: y - PLATE_FRONT                                 # printer -> plate Y
    cols = ("#1f5fbf", "#d08a00", "#2a9d4b")
    zf = SCAN_Z + COIL_ABOVE_TIP
    H = top0 + 3 * LH
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H + 120:.0f}" font-family="sans-serif" font-size="13">',
         '<rect width="100%" height="100%" fill="white"/>']
    X = lambda y: (y - y0) * sc
    for i, (yy, lab, col) in enumerate(((0.0, "plate front 0", "#444"), (pl(PRINTABLE_FRONT), f"printable {pl(PRINTABLE_FRONT):g}", "#444"),
                                         (pl(MESH_MIN_Y), f"mesh_min {pl(MESH_MIN_Y):g}", "#7a3fbf"))):
        s.append(f'<line x1="{X(yy):.1f}" y1="{top0 - 4 + (2 - i) * 0:.1f}" x2="{X(yy):.1f}" y2="{H:.1f}" stroke="{col}" stroke-dasharray="4 3"/>')
        s.append(f'<text x="{X(yy) + 3:.1f}" y="{14 + i * 15}" fill="{col}">{lab}</text>')
    for k, (r, col) in enumerate(zip(rows, cols)):
        base = top0 + k * LH
        Z = lambda z: base + (zhi - z) * sc
        s.append(f'<rect x="{X(0):.1f}" y="{Z(0):.1f}" width="{X(y1) - X(0):.1f}" height="{2 * sc:.1f}" fill="#999" fill-opacity="0.5"/>')
        c_ = pl(r["coil"]); h0 = HOUSING_D / 2
        pts = [(X(c_ - h0), Z(zf)), (X(c_ + h0), Z(zf)), (X(c_ + half), Z(0)), (X(c_ - half), Z(0))]
        s.append(f'<polygon points="{" ".join(f"{u:.1f},{v:.1f}" for u, v in pts)}" fill="{col}" fill-opacity="0.22" stroke="{col}" stroke-width="1.5"/>')
        s.append(f'<rect x="{X(c_ - h0):.1f}" y="{Z(zf + HOUSING_H):.1f}" width="{HOUSING_D * sc:.1f}" height="{HOUSING_H * sc:.1f}" '
                 f'fill="{col}" fill-opacity="0.6" stroke="{col}"/>')
        s.append(f'<line x1="{X(c_):.1f}" y1="{Z(0):.1f}" x2="{X(c_):.1f}" y2="{Z(zf + HOUSING_H):.1f}" stroke="#222" stroke-dasharray="2 2"/>')
        s.append(f'<text x="{X(c_):.1f}" y="{Z(zf + HOUSING_H) - 5:.1f}" text-anchor="middle" fill="{col}">coil centre {r["plate_coil"]:.2f}</text>')
        s.append(f'<text x="{X(c_ - half) - 4:.1f}" y="{Z(0) - 4:.1f}" text-anchor="end" fill="{col}" font-weight="bold">front edge {r["plate_front"]:.2f}</text>')
        u, v = X(pl(r["nozzle"])), Z(SCAN_Z)
        s.append(f'<polygon points="{u:.1f},{v:.1f} {u - 5:.1f},{v - 12:.1f} {u + 5:.1f},{v - 12:.1f}" fill="{col}"/>')
        s.append(f'<text x="{u:.1f}" y="{v - 16:.1f}" text-anchor="middle" fill="{col}">nozzle {pl(r["nozzle"]):.2f}</text>')
        s.append(f'<text x="8" y="{base + 14:.1f}" fill="{col}" font-weight="bold">X {r["x"]:g}: {r["name"]}</text>')
    yb = H + 22
    s.append(f'<text x="10" y="{yb}" font-weight="bold">Beacon at y_offset {dy:g}, head at its forward limit (worse head, lite-78 front). '
             f'Side view, front to the left, plate Y (printer Y = plate Y − 2.5). 1 mm = {sc:g} px.</text>')
    s.append(f'<text x="10" y="{yb + 22}">Triangle: nozzle tip at scan Z {SCAN_Z:g}. Box: coil housing (17 across, face {zf:g} above the bed). '
             f'Trapezoid: 17 → {2 * half:.2f} across at the bed.</text>')
    s.append(f'<text x="10" y="{yb + 42}">The flare is a stand-in (Beacon\'s keep-out cone above the board, mirrored down); Beacon publishes no downward '
             f'sensing cone.</text>')
    s.append(f'<text x="10" y="{yb + 62}">Bed mesh points are coil CENTRES: a straight front row can start no further forward than the X {rows[0]["x"]:g} lane.</text>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--y-offset", type=float, default=27.4)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    with open(FRONT_REACH, encoding="utf-8") as f, open(MAPPING, encoding="utf-8") as g:
        rows, half = footprints(json.load(f), json.load(g), a.y_offset)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(svg(rows, half, a.y_offset))
    for r in rows:
        print(f'X {r["x"]:g} ({r["name"]}): nozzle printer Y {r["nozzle"]}, coil centre plate Y {r["plate_coil"]}, '
              f'footprint front plate Y {r["plate_front"]}')
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
