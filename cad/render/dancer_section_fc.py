# The dancer's section drawing, step 1 of 2 (owner 2026-11-27: "a cutaway of the wheel in the channel", like a
# mechanical drawing): build one dancer stack from the lite-81 pass's own functions (no model needed) and cut it with
# three planes through one tool's sheave; write each part's cut outline as 2D polylines to a JSON file.
#
#   VT350_REPO=$PWD SECTION_OUT=<out.json> [SECTION_TOOL=1] $APP freecadcmd $PWD/cad/render/dancer_section_fc.py
#   python3 cad/render/dancer_section.py <out.json> <out.svg>          # step 2: the drawing (plain python3)
#
# The sections (2D axes in brackets):
#   A  X = the stack's X, through every axle         (Y, Z)  the sheaves side by side in their channels
#   B  Z = the tool's axle height                    (X, Y)  the rails, post and tie rods seen from above
#   C  Y = the tool's sheave mid-plane               (X, Z)  the spokes, hub, 625 and axle; the cable's path
import json, os, sys, traceback

OUT = os.environ.get("SECTION_OUT", "dancer_section.json")
_log = open(OUT + ".log", "w")                    # freecadcmd loses print() under os._exit (LESSONS.md)


def log(*a):
    _log.write(" ".join(str(x) for x in a) + "\n"); _log.flush()


def poly(wire, m):
    """A cut wire as a closed 2D polyline, through m (3D point -> (u, v))."""
    pts = wire.discretize(Deflection=0.02)
    return [[round(c, 3) for c in m(p)] for p in pts]


def main():
    repo = os.environ.get("VT350_REPO", os.getcwd())
    os.environ["LITE81_AS_LIB"] = "1"
    sys.path.insert(0, os.path.join(repo, "cad", "passes"))
    import FreeCAD
    import lite81_arms_dancers as L
    V = FreeCAD.Vector
    tool = int(os.environ.get("SECTION_TOOL", "1"))
    cx, members = next((cx, m) for cx, m in L.stacks().items() if tool in [t for t, _ in m])
    ys = sorted(y for _, y in members)
    ycs = [y - L.PITCH / 2 for y in ys] + [ys[-1] + L.PITCH / 2]
    slot = (L.lowest([t for t, _ in members]) - L.SLOT_W / 2 - 5.0, L.Z_TOP + L.SLOT_W / 2 + 1.0)
    body, rods, px = L.stack_body(cx, ycs, slot)
    parts = [("stack", "printed", body)] + [(f"rod{i}", "steel", r) for i, r in enumerate(rods)]
    sheaves = {}
    for t, y in members:
        zc = L.parked_z(t)
        sheaves[t] = (y, zc)
        parts += [(f"sheave{t}", "printed", L.sheave(cx, y, zc)), (f"bearing{t}", "bearing", L.bearing(cx, y, zc)),
                  (f"axle{t}", "shaft", L.axle(cx, y, zc))]
    y1, z1 = sheaves[tool]
    planes = {"A": (V(1, 0, 0), cx, lambda p: (p.y, p.z)),
              "B": (V(0, 0, 1), z1, lambda p: (p.x, p.y)),
              "C": (V(0, 1, 0), y1, lambda p: (p.x, p.z))}
    out = {"tool": tool, "cx": cx, "post_x": px, "plates": ycs, "slot": slot, "sheaves": {str(t): v for t, v in sheaves.items()},
           "k": {k: getattr(L, k) for k in ("SHEAVE_R", "SHEAVE_T", "GROOVE_W", "GROOVE_IN", "BEARING", "PITCH", "GROOVE_D",
                                            "PLATE_GAP", "AXLE_L", "PLATE_T", "PLATE_W", "SLOT_W", "FLANGE", "HUB_R",
                                            "RIM_WALL", "SPOKES", "SPOKE_T", "SPOKE_W", "POST_W", "ROD_R", "ROD_HOLE")},
           "RP": L.DANCER["RP"], "sections": {}}
    for name, (n, d, m) in planes.items():
        cut = []
        for key, kind, s in parts:
            try:
                wires = s.slice(n, d)
            except Exception as e:                    # a plane that misses the part
                log(name, key, "no cut:", e); wires = []
            if wires:
                cut.append({"part": key, "kind": kind, "loops": [poly(w, m) for w in wires]})
        out["sections"][name] = cut
        log(name, "plane at", round(d, 2), ":", [c["part"] for c in cut])
    json.dump(out, open(OUT, "w"))
    log("wrote", OUT)


try:
    main()
except Exception:
    log(traceback.format_exc())
os._exit(0)
