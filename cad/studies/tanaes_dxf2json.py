# Convert tanaes's Trident kinematic DXFs (whopping_Voron_mods/kinematic_bed/DXFs/Trident, GPL-3.0) to JSON that
# FreeCAD can read without ezdxf. Run with a Python that has ezdxf:
#   python -I tanaes_dxf2json.py <.../DXFs/Trident> $VT350_DL/tanaes_trident_parts.json
# Keys: A B C D E F G H I J. Entities: ["L", p0, p1] | ["A", c, r, start_deg, end_deg] | ["C", c, r]
#       | ["P", [[x, y, bulge], ...], closed]. Coordinates are the DXF's own (mm).
import ezdxf, sys, glob, os, json
out = {}
for f in sorted(glob.glob(sys.argv[1] + "/trident_*.dxf")) + [sys.argv[1] + "/J-spring.dxf"]:
    k = "J" if "J-spring" in f else os.path.basename(f)[len("trident_")]
    ents = []
    for e in ezdxf.readfile(f).modelspace():
        t = e.dxftype()
        if t == "LINE": ents.append(["L", list(e.dxf.start)[:2], list(e.dxf.end)[:2]])
        elif t == "ARC": ents.append(["A", list(e.dxf.center)[:2], e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle])
        elif t == "CIRCLE": ents.append(["C", list(e.dxf.center)[:2], e.dxf.radius])
        elif t == "LWPOLYLINE": ents.append(["P", [[float(v) for v in p] for p in e.get_points("xyb")], bool(e.closed)])
        else: raise SystemExit(f"{f}: unhandled {t}")
    out[k] = ents
json.dump(out, open(sys.argv[2], "w"))
print({k: len(v) for k, v in out.items()})
