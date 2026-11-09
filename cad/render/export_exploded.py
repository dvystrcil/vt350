# Headless export of an EXPLODED view of the filter holder (#74, lite-30) for Blender (render.py). Read-only.
#   1. dry-run the pass with VT350_EXPORT=<parts dir> so it writes its new parts (ring, seal halves, tray seal) as BREP;
#   2. VT350_PARTS=<parts dir> VT350_RENDER_OUT=<dir> $APP freecadcmd /home/dan/Code/vt350/cad/render/export_exploded.py
#   3. blender -b -P cad/render/render.py -- <dir> <out>      (or the GPU batch lane on node-03)
# Stacked bottom to top in assembly order, each pulled straight up by its OFFSET (mm): ring, tray seal, filter,
# cutout seal halves (also pulled apart in X), backbone (cropped to the cutout and a margin, so the camera sees in).
import FreeCAD, Part, Mesh, MeshPart, os, json, time, traceback
V = FreeCAD.Vector
MODELS = "/home/dan/Documents/VT350"
PRINTER = os.environ.get("VT350_PRINTER", f"{MODELS}/vt350-lite-29.FCStd")
FILTER = os.environ.get("VT350_FILTER", f"{MODELS}/vt350-filter-3.FCStd")
PARTS = os.environ.get("VT350_PARTS", "/tmp/vt350-lite30-parts")
OUT = os.environ.get("VT350_RENDER_OUT", "/tmp/vt350-exploded")
CROP = (-470.0, -20.0, 20.0, 450.0)            # backbone crop X0 X1 Y0 Y1: the cutout (X -420..-70, Y 70..400) + 50
ORANGE, TPU, GREY, STEEL = (0.89, 0.4, 0.16), (0.12, 0.12, 0.13), (0.72, 0.72, 0.74), (0.25, 0.25, 0.27)
# key: (offset Z, offset X, colour, material, transparency)
# The tray seal sits 77 mm down inside the tub (Z -80 vs the collar top -3): it needs > 90 to clear the ring at all.
LAYERS = {"ring": (0, 0, ORANGE, "PET-GF", 0.0), "tray_seal": (120, 0, TPU, "TPU", 0.0),
          "filter": (230, 0, GREY, "PETG", 0.0), "seal_left": (360, -25, TPU, "TPU", 0.0),
          "seal_right": (360, 25, TPU, "TPU", 0.0), "backbone": (430, 0, STEEL, "Steel-Generic", 0.35)}
os.makedirs(OUT, exist_ok=True)
logf = open(os.path.join(OUT, "export.log"), "w"); t0 = time.time()
def log(*a): logf.write(f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); logf.flush()
def gshape(o):
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement(); return s
def leaf(o):
    return o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and bool(o.Shape.Solids) and o.TypeId != 'App::Part'
try:
    shapes = {}
    for k in ("ring", "tray_seal", "seal_left", "seal_right"):
        s = Part.Shape(); s.importBrep(os.path.join(PARTS, k + ".brep")); shapes[k] = [s]
    fd = FreeCAD.openDocument(FILTER); log("opened", FILTER)
    shapes["filter"] = [gshape(o) for o in fd.Objects if leaf(o) and not o.Label.startswith("StealthMax cradle half")]
    pd = FreeCAD.openDocument(PRINTER); log("opened", PRINTER)
    bb = next(o for o in pd.Objects if leaf(o) and o.Label.startswith("backbone-350"))
    shapes["backbone"] = [gshape(bb).common(Part.makeBox(CROP[1] - CROP[0], CROP[3] - CROP[2], 40, V(CROP[0], CROP[2], -30)))]
    scene = {"model": "vt350-lite-30-exploded.FCStd", "buckets": {}, "lights": [], "camera": None}
    for k, (dz, dx, col, mat, tr) in LAYERS.items():
        m = Mesh.Mesh()
        for s in shapes[k]:
            s = s.copy(); s.translate(V(dx, 0, dz))
            m.addMesh(MeshPart.meshFromShape(Shape=s, LinearDeflection=0.1, AngularDeflection=0.35, Relative=False))
        m.write(os.path.join(OUT, k + ".stl"))
        scene["buckets"][k] = {"color": col, "material": mat, "transparency": tr, "n": len(shapes[k]),
                               "facets": m.CountFacets, "labels": [k]}
        log(f"{k}: {len(shapes[k])} solids, {m.CountFacets} facets, dZ {dz}, dX {dx}")
    c = V(-245, 235, 170)                         # centre of the stack
    scene["views"] = [
        {"name": "exploded_front", "pos": [c.x + 620, c.y - 980, c.z + 480], "look": [c.x, c.y, c.z], "lens_mm": 35},
        {"name": "exploded_side", "pos": [c.x - 1080, c.y - 140, c.z + 280], "look": [c.x, c.y, c.z], "lens_mm": 35},
        {"name": "exploded_under", "pos": [c.x + 540, c.y - 840, c.z - 480], "look": [c.x, c.y, c.z + 40], "lens_mm": 35},
    ]
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=1)
    log("done")
except Exception: log("FAILED\n" + traceback.format_exc())
finally: logf.close(); os._exit(0)
