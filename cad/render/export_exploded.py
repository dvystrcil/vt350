# Headless export of an EXPLODED view of the filter holder (#74, lite-30) for Blender (render.py). Read-only.
#   1. dry-run the pass with VT350_EXPORT=<parts dir> so it writes its new parts (ring, seal halves, tray seal) as BREP;
#   2. VT350_PARTS=<parts dir> VT350_RENDER_OUT=<dir> $APP freecadcmd /home/dan/Code/vt350/cad/render/export_exploded.py
#   3. blender -b -P platform/render/render.py -- <dir> <out>      (or the GPU batch lane on node-03)
# Stacked bottom to top in assembly order, each pulled straight up by its OFFSET (mm): backbone (cropped to the
# cutout and a margin), cutout seal halves (also pulled apart in X), cradle, tray seal, filter.
import FreeCAD, Part, Mesh, MeshPart, os, sys, json, time, traceback
_HERE = os.path.dirname(os.path.abspath(__file__))   # then the checkout's code folders (vt350#122); a gpu-batch pod stages all flat in _HERE
sys.path[:0] = [_HERE] + [p for p in (os.path.join(os.path.dirname(os.path.dirname(_HERE)), d) for d in ('platform/render',)) if os.path.isdir(p)]
import colours                                   # #38 role colours: the filter's accents, the black backbone
import logos                                     # Voron logos: orange, white inset (shared with export_meshes.py)
V = FreeCAD.Vector
MODELS = "/home/dan/Documents/VT350"
PRINTER = os.environ.get("VT350_PRINTER", f"{MODELS}/vt350-lite-29.FCStd")
FILTER = os.environ.get("VT350_FILTER", f"{MODELS}/vt350-filter-3.FCStd")
PARTS = os.environ.get("VT350_PARTS", "/tmp/vt350-lite30-parts")
OUT = os.environ.get("VT350_RENDER_OUT", "/tmp/vt350-exploded")
CROP = (-470.0, -20.0, 20.0, 450.0)            # backbone crop X0 X1 Y0 Y1: the cutout (X -420..-70, Y 70..400) + 50
ORANGE, TPU, GREY, STEEL = (0.89, 0.4, 0.16), (0.12, 0.12, 0.13), (0.72, 0.72, 0.74), (0.25, 0.25, 0.27)
# key: (offset Z, offset X, colour, material, transparency)
# Assembly order, bottom to top (user, 2026-11-09): backbone, cutout seal halves (laid on the backbone), cradle
# (the ring, dropped in so its lips land on the seal), tray seal (laid in the tub), filter. Gaps ~35-40 mm: the
# cradle hangs 89 mm below its own lips and the tray seal sits 77 mm down in the tub, hence the big jumps.
LAYERS = {"backbone": (0, 0, STEEL, "Steel-Generic", 0.35), "seal_left": (40, -25, TPU, "TPU", 0.0),
          "seal_right": (40, 25, TPU, "TPU", 0.0), "ring": (170, 0, ORANGE, "PET-GF", 0.0),
          "tray_seal": (300, 0, TPU, "TPU", 0.0), "filter": (340, 0, GREY, "PETG", 0.0)}
# Colour roles from colours.json (the same map as the full renders): the backbone and cradle by label; the filter
# split per role (StealthMax latches, hinges, logo cap = accent; bodies = printed). A filter part no rule names
# is "other": the acrylic panel is see-through, the rest (fan, HEPA, hub, sponge cord) dark.
ROLE_OF = {"backbone": "backbone", "ring": "accent"}
CLEAR, DARK = (0.85, 0.9, 0.95), (0.18, 0.18, 0.19)
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
    CMAP = colours.load()
    fobjs = [o for o in fd.Objects if leaf(o) and not o.Label.startswith("StealthMax cradle half")]
    froles = {}
    for o in fobjs:
        mat = getattr(getattr(o, "ShapeMaterial", None), "Name", "") or ""
        r = colours.role_of(CMAP, o.Label, "", mat) or ("clear" if "Acrylic" in o.Label else "other")
        froles.setdefault(r, []).append(o)
    for r, os_ in froles.items(): log(f"filter {r}: {sorted(o.Label for o in os_)}")
    shapes["filter"] = [gshape(o) for o in fobjs]
    split = {}                                     # logo label -> (inset faces, rest faces)
    for o in fobjs:
        r = logos.split(o.Label, gshape(o))
        if r:
            inset, rest = r; split[o.Label] = r
            log(f"logo {o.Label}: {len(inset)} inset faces ({sum(f.Area for f in inset):.0f} mm2) white, {len(rest)} orange")
    pd = FreeCAD.openDocument(PRINTER); log("opened", PRINTER)
    bb = next(o for o in pd.Objects if leaf(o) and o.Label.startswith("backbone-350"))
    shapes["backbone"] = [gshape(bb).common(Part.makeBox(CROP[1] - CROP[0], CROP[3] - CROP[2], 40, V(CROP[0], CROP[2], -30)))]
    scene = {"model": "vt350-lite-30-exploded.FCStd", "buckets": {}, "lights": [], "camera": None, "roles": CMAP["roles"]}
    layers = {}
    for k, v in LAYERS.items():
        if k != "filter": layers[k] = (v, ROLE_OF.get(k), shapes[k]); continue
        for r, os_ in froles.items():            # one bucket per role, so each gets its own material
            vv = {"clear": (v[0], v[1], CLEAR, v[3], 0.6), "other": (v[0], v[1], DARK, v[3], 0.0)}.get(r, v)
            shs = [Part.Compound(split[o.Label][1]) if o.Label in split else gshape(o) for o in os_]
            layers[f"filter_{r}"] = (vv, None if r in ("clear", "other") else r, shs)
        layers["filter_logo_inset"] = (v, "printed", [Part.Compound(i) for i, _ in split.values()])
    for k, ((dz, dx, col, mat, tr), role, shs) in layers.items():
        m = Mesh.Mesh()
        for s in shs:
            s = s.copy(); s.translate(V(dx, 0, dz))
            m.addMesh(MeshPart.meshFromShape(Shape=s, LinearDeflection=0.1, AngularDeflection=0.35, Relative=False))
        m.write(os.path.join(OUT, k + ".stl"))
        scene["buckets"][k] = {"color": col, "material": mat, "transparency": tr, "n": len(shs), "role": role,
                               "facets": m.CountFacets, "labels": [k]}
        log(f"{k} ({role}): {len(shs)} solids, {m.CountFacets} facets, dZ {dz}, dX {dx}")
    c = V(-245, 235, 165)                         # centre of the stack
    scene["views"] = [
        {"name": "exploded_front", "pos": [c.x + 620, c.y - 980, c.z + 480], "look": [c.x, c.y, c.z], "lens_mm": 35},
        {"name": "exploded_side", "pos": [c.x - 1080, c.y - 140, c.z + 280], "look": [c.x, c.y, c.z], "lens_mm": 35},
        # logo close-ups (filter lifted 340): the front hinge hexagon, and the cap on top
        {"name": "logo_front", "pos": [-245 + 70, 86 - 260, -26 + 340 + 70], "look": [-245, 86, -26 + 340], "lens_mm": 50,
         "hide": ["backbone", "seal_left", "seal_right"]},
        {"name": "logo_top", "pos": [-245 + 40, 235 - 120, -11 + 340 + 260], "look": [-245, 235, -11 + 340], "lens_mm": 50,
         "hide": ["filter_clear"], "ev": -1.6},     # the cap sits under the acrylic panel; white parts over-expose
        {"name": "exploded_under", "pos": [c.x + 540, c.y - 840, c.z - 480], "look": [c.x, c.y, c.z + 40], "lens_mm": 35},
    ]
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=1)
    log("done")
except Exception: log("FAILED\n" + traceback.format_exc())
finally: logf.close(); os._exit(0)
