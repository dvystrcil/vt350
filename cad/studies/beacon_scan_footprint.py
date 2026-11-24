#!/usr/bin/env python3
"""Side view: where the Beacon's scan footprint lands on the plate with the head parked at its safe front Y (vt350#291,
#309). Plain python, read-only.

The head sits at ONE Y: the furthest-forward nozzle Y that is clear at every X of the mesh, for both heads (the
lite-78 front: cad/data/front_reach_front17.json; the worst X sets it). That's where a straight front scan line can
run. With the nozzle there at scan height, the Beacon is y_offset behind it; the picture shows the coil housing and a
trapezoid from the coil face down to the plate, for today's offset (27.4) and the planned one (15).

The trapezoid's flare is a STAND-IN. Beacon publishes no downward sensing cone. Its STEP (Beacon_RevH_Assm_Normal,
MIT) has the coil housing (17 mm across, 2.6 tall) and a metal keep-out cone ABOVE the board (17 -> 18.75 mm across
over 20 mm). The trapezoid uses that same flare downward, so at the scan height it is barely wider than the coil.

Run: python3 cad/studies/beacon_scan_footprint.py  ->  cad/data/beacon_scan_footprint.svg
"""
import argparse, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
FRONT_REACH = os.path.join(CAD, "data", "front_reach_front17.json")
MAPPING = os.path.join(CAD, "klipper", "xy_mapping.json")
OUT = os.path.join(CAD, "data", "beacon_scan_footprint.svg")

PLATE_FRONT = -2.5        # printer Y of the plate's front edge (355 plate, 350 print square, centred; print_area.py)
PRINTABLE_FRONT = 2.5     # printer Y of the printable front edge (print_area.py)
MESH_X = (5.48, 344.52)   # beacon.cfg mesh_min / mesh_max X (the scan's X range)
MESH_MIN_Y = 5.48         # beacon.cfg mesh_min Y
SCAN_Z = 2.0              # nozzle height during the scan (beacon trigger_distance, cad/motion/beacon_scan.py)
COIL_ABOVE_TIP = 2.6      # coil face above the nozzle tip (lite24_beacon.py)
HOUSING_D, HOUSING_H = 17.0, 2.6                 # Beacon STEP: the coil housing under the board
BOARD_FRONT, BOARD_REAR, BOARD_TOP = 8.5, 19.0, 4.21   # board ends from the coil axis, board top above the coil face
FLARE = (18.75 - 17.0) / 2 / 20.0                # Beacon STEP keep-out cone: radius growth per mm (stand-in, see above)
OFFSETS = (("today, option 3", 27.4, "#1f5fbf"), ("planned", 15.0, "#c62828"))


def safe_nozzle_y(front, mapping, xr=MESH_X):
    """The furthest-forward nozzle printer Y that's clear for both heads at every sampled X in the mesh's X range
    (one front reach sample of slack each side, so the end samples count)."""
    (ox, oy), (gx, gy) = mapping["origin_model_xy"], mapping["sign_xy"]
    pts = [(gx * (r["x"] - ox), gy * (r["clear"] - oy)) for rs in front["heads"].values() for r in rs]
    xs = sorted({x for x, _ in pts})
    step = max(b - a for a, b in zip(xs, xs[1:]))
    return round(max(y for x, y in pts if xr[0] - step <= x <= xr[1] + step), 2)


def footprint(nozzle_y, dy):
    """Coil centre and the footprint's front / rear edge on the plate, printer and plate Y."""
    half = HOUSING_D / 2 + FLARE * (SCAN_Z + COIL_ABOVE_TIP)
    c = nozzle_y + dy
    pl = lambda y: round(y - PLATE_FRONT, 2)
    return dict(dy=dy, coil=round(c, 2), front=round(c - half, 2), rear=round(c + half, 2), half=round(half, 2),
                plate_nozzle=pl(nozzle_y), plate_coil=pl(c), plate_front=pl(c - half), plate_rear=pl(c + half))


def svg(ny, fps):
    """One lane per offset, the same head Y and one Y scale in both, so the footprints line up for comparison."""
    sc = 16.0; y0, y1, zlo, zhi = -22.0, 52.0, -3.0, 13.0         # plate Y window, Z window per lane (mm)
    LH, top = (zhi - zlo) * sc + 24, 48
    W = (y1 - y0) * sc
    X = lambda y: (y - y0) * sc
    pl = lambda y: y - PLATE_FRONT
    zf = SCAN_Z + COIL_ABOVE_TIP
    n = pl(ny)
    H = top + len(fps) * LH
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H + 120:.0f}" font-family="sans-serif" font-size="13">',
         '<rect width="100%" height="100%" fill="white"/>']
    for i, (yy, lab, col) in enumerate(((0.0, "plate front 0", "#444"), (pl(PRINTABLE_FRONT), f"printable {pl(PRINTABLE_FRONT):g}", "#444"),
                                         (pl(MESH_MIN_Y), f"mesh_min {pl(MESH_MIN_Y):g}", "#7a3fbf"))):
        s.append(f'<line x1="{X(yy):.1f}" y1="{top - 6:.1f}" x2="{X(yy):.1f}" y2="{H:.1f}" stroke="{col}" stroke-dasharray="4 3"/>')
        s.append(f'<text x="{X(yy) + 3:.1f}" y="{12 + i * 14}" fill="{col}" font-size="12">{lab}</text>')
    s.append(f'<line x1="{X(n):.1f}" y1="{top - 6:.1f}" x2="{X(n):.1f}" y2="{H:.1f}" stroke="#222" stroke-dasharray="1 3"/>')
    s.append(f'<text x="{X(n) - 4:.1f}" y="{top - 10:.1f}" text-anchor="end" font-weight="bold">head parked: nozzle {n:.2f}</text>')
    for k, fp in enumerate(fps):
        name, dy, col = next(o for o in OFFSETS if o[1] == fp["dy"])
        base = top + k * LH
        Z = lambda z: base + (zhi - z) * sc
        c, h0 = fp["plate_coil"], HOUSING_D / 2
        s.append(f'<rect x="{X(0):.1f}" y="{Z(0):.1f}" width="{X(y1) - X(0):.1f}" height="{2.5 * sc:.1f}" fill="#999" fill-opacity="0.5"/>')
        s.append(f'<text x="8" y="{base + 14:.1f}" fill="{col}" font-weight="bold">y_offset {dy:g} ({name})</text>')
        # the head, schematic: the nozzle and a rigid bar to the Beacon (the carriage it hangs from)
        s.append(f'<polygon points="{X(n - 3):.1f},{Z(zhi - 3):.1f} {X(n + 3):.1f},{Z(zhi - 3):.1f} {X(n + 1.2):.1f},{Z(SCAN_Z + 2.5):.1f} '
                 f'{X(n):.1f},{Z(SCAN_Z):.1f} {X(n - 1.2):.1f},{Z(SCAN_Z + 2.5):.1f}" fill="#555" fill-opacity="0.7"/>')
        s.append(f'<rect x="{X(n - 3):.1f}" y="{Z(zhi - 1.5):.1f}" width="{(c + BOARD_REAR - n + 3) * sc:.1f}" height="{1.5 * sc:.1f}" fill="#555" fill-opacity="0.45"/>')
        s.append(f'<line x1="{X(c):.1f}" y1="{Z(zhi - 1.5):.1f}" x2="{X(c):.1f}" y2="{Z(zf + BOARD_TOP):.1f}" stroke="#555" stroke-width="3"/>')
        s.append(f'<line x1="{X(n):.1f}" y1="{Z(zhi - 3.6):.1f}" x2="{X(c):.1f}" y2="{Z(zhi - 3.6):.1f}" stroke="{col}" marker-end="url(#a)"/>')
        s.append(f'<text x="{(X(n) + X(c)) / 2:.1f}" y="{Z(zhi - 3.6) - 4:.1f}" text-anchor="middle" fill="{col}">{dy:g}</text>')
        s.append(f'<rect x="{X(c - BOARD_FRONT):.1f}" y="{Z(zf + BOARD_TOP):.1f}" width="{(BOARD_FRONT + BOARD_REAR) * sc:.1f}" '
                 f'height="{(BOARD_TOP - HOUSING_H) * sc:.1f}" fill="{col}" fill-opacity="0.35" stroke="{col}"/>')
        s.append(f'<rect x="{X(c - h0):.1f}" y="{Z(zf + HOUSING_H):.1f}" width="{HOUSING_D * sc:.1f}" height="{HOUSING_H * sc:.1f}" '
                 f'fill="{col}" fill-opacity="0.8" stroke="{col}"/>')
        pts = [(X(c - h0), Z(zf)), (X(c + h0), Z(zf)), (X(c + fp["half"]), Z(0)), (X(c - fp["half"]), Z(0))]
        s.append(f'<polygon points="{" ".join(f"{u:.1f},{v:.1f}" for u, v in pts)}" fill="{col}" fill-opacity="0.35" stroke="{col}" stroke-width="2"/>')
        s.append(f'<line x1="{X(c):.1f}" y1="{Z(0):.1f}" x2="{X(c):.1f}" y2="{Z(zf):.1f}" stroke="#222" stroke-dasharray="2 2"/>')
        s.append(f'<text x="{X(c):.1f}" y="{Z(-1.6) + 5:.1f}" text-anchor="middle" fill="#222">centre {c:.2f}</text>')
        s.append(f'<text x="{X(c - fp["half"]) - 5:.1f}" y="{Z(1) :.1f}" text-anchor="end" fill="{col}" font-weight="bold">{fp["plate_front"]:.2f}</text>')
        s.append(f'<text x="{X(c + fp["half"]) + 5:.1f}" y="{Z(1):.1f}" fill="{col}" font-weight="bold">{fp["plate_rear"]:.2f}</text>')
    yb = H + 22
    s.append(f'<text x="10" y="{yb}" font-weight="bold">Head parked at the safe front Y: nozzle plate Y {n:.2f} (printer {ny:.2f}), the furthest forward '
             f'that is clear at every mesh X for both heads (lite-78 front). Scan Z {SCAN_Z:g}.</text>')
    s.append(f'<text x="10" y="{yb + 20}">Trapezoid: where the coil senses the plate, 17 across at the coil face ({zf:g} above the plate) → '
             f'{2 * fps[0]["half"]:.2f} at the plate. Bold numbers: its front and rear edge.</text>')
    s.append(f'<text x="10" y="{yb + 40}">Side view, front to the left, plate Y (0 = the plate\'s front edge; printer Y = plate Y − 2.5). Head drawn schematically. '
             f'1 mm = {sc:g} px.</text>')
    s.append(f'<text x="10" y="{yb + 60}">The flare is a stand-in (Beacon\'s keep-out cone above the board, mirrored down); Beacon publishes no downward '
             f'sensing cone.</text>')
    s.insert(2, '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    with open(FRONT_REACH, encoding="utf-8") as f, open(MAPPING, encoding="utf-8") as g:
        ny = safe_nozzle_y(json.load(f), json.load(g))
    fps = [footprint(ny, dy) for _, dy, _ in OFFSETS]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(svg(ny, fps))
    print(f"safe front nozzle Y: printer {ny}, plate {ny - PLATE_FRONT:.2f}")
    for fp in fps:
        print(f'y_offset {fp["dy"]:g}: coil centre plate Y {fp["plate_coil"]}, footprint plate Y {fp["plate_front"]} .. {fp["plate_rear"]}')
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
