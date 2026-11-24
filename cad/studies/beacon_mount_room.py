# freecadcmd study, read-only, never saves:   $APP freecadcmd $PWD/cad/studies/beacon_mount_room.py
# Where can the Beacon's two M3 screws go at a smaller y_offset? (vt350#291, lite-79)
#
# beacon_offset.py found y_offset 15 the smallest that keeps the Beacon BODY clear of both carried heads, and left the
# carriage out ("its pocket gets re-cut for whatever offset is chosen"). This checks what that skipped: the board hangs
# from the MadMax carriage on two M3 screws through its slots (lite-24: pilot holes at +-15.8 mm, 5.06 mm deep since
# lite-73). Moving the Beacon forward moves those holes forward. For each offset, at each hole, on a vertical line from
# the board's top up: how much carriage material is there (thread), and what's the first non-carriage part (the carried
# head's tool plate, ducts, screws). Also every head part over the board's footprint within 8 mm of its top.
#
# The pose: each dock's carriage copy (COMPOUND003 = the Left Dock's link, COMPOUND004 = the Right Dock's mirrored
# copy) is the carriage at that dock's pickup, with its head docked: the Beacon is taken there from the gantry carriage
# by the copy's offset. That puts the head 0.315 higher than when carried (CARRY_DZ, lite73_dav.py); the room numbers
# here are therefore up to 0.315 generous, which doesn't change the answer.
# Output: $VT350_WORK/logs/beacon_mount_room.log, $VT350_WORK/beacon_mount_room.json and beacon_mount_room.svg (a side
# section at the left hole's X: carriage, head parts, Beacon now and at 15).
import FreeCAD, Part, math, os, sys, json
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad")]
import litelib
V = FreeCAD.Vector
MODEL = os.environ.get("VT350_MODEL", os.path.join(litelib.MODELS, "vt350-lite-78.FCStd"))
WORK = os.environ.get("VT350_WORK", os.path.join(_REPO, "cad/data"))
NOW = 27.4
OFFSETS = (27.4, 25.0, 24.0, 23.0, 22.0, 20.0, 18.0, 15.0)
THREAD = 5.0                 # mm of carriage needed over the board for an M3 into a printed pilot hole (lite-73 left 5.06)
WALL = 1.6                   # the ring round the hole axis (the pilot hole is 2.52 across, so its axis is air) on which
                             # the carriage's material is measured: 8 points, the third-thinnest counts (the holes sit in
                             # narrow end ledges, so a point or two can fall off an edge; lite-73 measured 5.06 there)
OVER = 8.0                   # height over the board's top searched for head parts
HOLE_DX = 15.8               # Beacon RevH slots at +-15.8 (lite24_beacon.py)
COPIES = ("COMPOUND003", "COMPOUND004")
os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
logf = open(os.path.join(WORK, "logs", "beacon_mount_room.log"), "w")
def log(*a): logf.write(" ".join(str(x) for x in a) + "\n"); logf.flush()


def column(shape, x, y, z0, z1):
    """(lo, hi) intervals of shape's material on the vertical line x, y between z0 and z1, sorted."""
    es = Part.makeLine(V(x, y, z0), V(x, y, z1)).common(shape).Edges
    return sorted((min(v.Point.z for v in e.Vertexes), max(v.Point.z for v in e.Vertexes)) for e in es)


def thread_at(shape, x, y, z0):
    """Carriage material from the board top z0 straight up (0 if the line starts in air)."""
    iv = column(shape, x, y, z0 - 0.2, z0 + 20)
    return round(iv[0][1] - z0, 2) if iv and iv[0][0] <= z0 + 0.05 else 0.0


def main():
    doc = FreeCAD.openDocument(MODEL)
    m = litelib.Model(doc); S = m.shapes
    car = next(o for o in m.leaves if o.Label == "COMPOUND")
    bea = next(o for o in m.leaves if o.Label.startswith("Beacon RevH"))
    G, B = S[car.Name], S[bea.Name]
    board = max(B.Solids, key=lambda s: s.Volume)                     # the PCB (lite-24: solid 2, 1429 mm3)
    top = board.BoundBox.ZMax
    holes = [h for h in G.Faces if isinstance(h.Surface, Part.Cylinder) and abs(h.Surface.Radius - 1.26) < 0.05
             and h.BoundBox.ZMin < top + 0.1]
    log(f"model {os.path.basename(MODEL)} (read-only); Beacon board top Z {top:.3f}; carriage front face Y {G.BoundBox.YMin:.3f}")
    assert len(holes) == 2, f"two Beacon pilot holes in the carriage ({len(holes)})"
    hy = sum(h.Surface.Center.y for h in holes) / 2; hx = sorted(h.Surface.Center.x for h in holes)
    log(f"pilot holes X {hx[0]:.2f} / {hx[1]:.2f}, Y {hy:.3f} ({hy - G.BoundBox.YMin:.2f} behind the carriage front)")
    carfam = {o.Name for o in m.leaves if o.Label.startswith("COMPOUND")} | {bea.Name}
    out = dict(model=os.path.basename(MODEL), now=NOW, thread_needed=THREAD, docks={})
    sect = None
    for cn in COPIES:
        cp = next(o for o in m.leaves if o.Label == cn); C = S[cp.Name]
        d = V(C.BoundBox.Center.x - G.BoundBox.Center.x, C.BoundBox.YMin - G.BoundBox.YMin, C.BoundBox.ZMin - G.BoundBox.ZMin)
        near = [o for o in m.leaves if o.Name not in carfam and S[o.Name].BoundBox.intersect(
            FreeCAD.BoundBox(C.BoundBox.XMin - 5, C.BoundBox.YMin - 40, top + d.z - 1, C.BoundBox.XMax + 5, C.BoundBox.YMax + 20, top + d.z + 60))]
        log(f"-- {cn} (dock pickup pose, offset {d.x:.2f}, {d.y:.2f}, {d.z:.3f}): {len(near)} head/dock parts near")
        rows = []
        for off in OFFSETS:
            dy = -(NOW - off); z0 = top + d.z
            bb = board.BoundBox; R = Part.makeBox(bb.XLength, bb.YLength, OVER, V(bb.XMin + d.x, bb.YMin + d.y + dy, z0))
            over = []
            for o in near:
                s = S[o.Name]
                if not s.BoundBox.intersect(R.BoundBox): continue
                c = s.common(R)
                if c.Volume > 0.01: over.append((round(c.BoundBox.ZMin - z0, 2), o.Label))
            hr = []
            for x in hx:
                X, Y = x + d.x, hy + d.y + dy
                ring = sorted(thread_at(C, X + WALL * math.cos(k * math.pi / 4), Y + WALL * math.sin(k * math.pi / 4), z0)
                              for k in range(8))
                th = ring[2]
                first = sorted((round(iv[0][0] - z0, 2), o.Label) for o in near
                               for iv in [column(S[o.Name], X, Y, z0 - 0.2, z0 + 40)] if iv)
                hr.append(dict(x=round(X, 2), y=round(Y, 2), carriage_over_board=th, first_part=first[0] if first else None))
            ok = all(h["carriage_over_board"] >= THREAD and (h["first_part"] is None or h["first_part"][0] >= THREAD) for h in hr)
            rows.append(dict(offset=off, holes=hr, head_parts_over_board=sorted(over)[:8], mountable_today=ok))
            log(f"   y_offset {off:5.1f}: holes " + "; ".join(
                f"carriage {h['carriage_over_board']:.2f} over the board, first part {h['first_part']}" for h in hr)
                + " -> " + ("screws into today's carriage" if ok else "NO room for the screws"))
            if over: log(f"      head parts over the board (gap above its top, part): {sorted(over)[:6]}")
        out["docks"][cn] = rows
        if sect is None: sect = (cn, d, near, C)
    last = {cn: min([r["offset"] for r in rows if r["mountable_today"]], default=None) for cn, rows in out["docks"].items()}
    out["smallest_mountable_offset_tried"] = last
    log(f"smallest offset tried whose screws still go into today's carriage: {last}")
    svg(sect, B, hx[0], top, hy)
    json.dump(out, open(os.path.join(WORK, "beacon_mount_room.json"), "w"), indent=1)
    log("done (read-only, nothing saved)")


def svg(sect, B, x0, top, hy):
    """Side section (YZ plane) at the left hole's X, dock pose: carriage, head parts, the Beacon at 27.4 and at 15."""
    cn, d, near, C = sect
    X = x0 + d.x; z0 = top + d.z
    layers = [("carriage", "#888", [C])]
    layers.append(("head (plate, ducts, screws)", "#c66", [S for S in (litelib.gshape(o) for o in near)]))
    b0 = B.copy(); b0.translate(d); b1 = B.copy(); b1.translate(d + V(0, -(NOW - 15.0), 0))
    layers += [("Beacon at 27.4", "#36c", [b0]), ("Beacon at 15", "#d90", [b1])]
    ylo, yhi, zlo, zhi = hy + d.y - 40, hy + d.y + 20, z0 - 8, z0 + 22
    sc = 12.0; W, H = (yhi - ylo) * sc, (zhi - zlo) * sc
    px = lambda y, z: ((y - ylo) * sc, (zhi - z) * sc)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H + 60:.0f}" font-family="sans-serif" font-size="13">',
             f'<rect width="100%" height="100%" fill="white"/>']
    for name, col, shapes in layers:
        for s in shapes:
            bb = s.BoundBox
            if bb.XMin > X or bb.XMax < X or bb.YMax < ylo or bb.YMin > yhi or bb.ZMax < zlo or bb.ZMin > zhi: continue
            try: ws = s.slice(V(1, 0, 0), X)
            except Exception: continue
            for w in ws:
                pts = [px(p.y, p.z) for p in w.discretize(Deflection=0.05)]
                parts.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{col}" fill-opacity="0.45" stroke="{col}" stroke-width="1"/>')
    for i, (name, col, _) in enumerate(layers):
        parts.append(f'<rect x="{10 + i * 200}" y="{H + 15}" width="14" height="14" fill="{col}" fill-opacity="0.6"/><text x="{30 + i * 200}" y="{H + 27}">{name}</text>')
    parts.append(f'<text x="10" y="{H + 52}">Side section at the left Beacon screw (X {X:.1f}, {cn} pose). Front (-Y) to the left. 1 mm = {sc:g} px.</text>')
    parts.append("</svg>")
    open(os.path.join(WORK, "beacon_mount_room.svg"), "w").write("\n".join(parts))


try:
    main()
except Exception:
    import traceback; log("FATAL\n" + traceback.format_exc()); raise
