# FreeCAD GUI script: export a working copy as meshes for Blender (cad/render/render.py).
#   VT350_MODEL = .FCStd to read (default: the current working copy), VT350_RENDER_OUT = output folder.
# Writes one binary STL per (material, colour) bucket in global coordinates (mm) and scene.json describing each
# bucket (colour, FreeCAD material card, labels), plus the camera / LED positions found in the model.
# Never saves the model.
import FreeCAD, Mesh, MeshPart, os, json, time, traceback, re
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-16.FCStd")
OUT = os.environ.get("VT350_RENDER_OUT", "/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad/render")
os.makedirs(OUT, exist_ok=True)
logf = open(os.path.join(OUT, "export.log"), "w"); t0 = time.time()
def log(*a): logf.write(f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); logf.flush()
try:
    doc = FreeCAD.openDocument(MODEL); log("opened", MODEL)
    leaves = {o.Name: o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids}
    buckets, scene = {}, {"model": os.path.basename(MODEL), "buckets": {}, "lights": [], "camera": None}
    hidden = 0
    for o in leaves.values():
        vo = o.ViewObject if FreeCAD.GuiUp else None
        if vo is not None and not vo.isVisible(): hidden += 1; continue
        if any(o2.isDerivedFrom('Part::Feature') and o2.Name in leaves for o2 in o.InList if o2.TypeId != 'App::Part'):
            continue    # consumed by a feature that is itself a leaf
        try:
            col = tuple(round(c, 2) for c in vo.ShapeAppearance[0].DiffuseColor[:3]) if vo else (0.7, 0.7, 0.7)
            tr = round(vo.Transparency / 100, 2) if vo else 0.0
        except Exception: col, tr = (0.7, 0.7, 0.7), 0.0
        mat = getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
        key = f"{re.sub('[^A-Za-z0-9]+', '_', mat)}__{int(col[0]*100):02d}_{int(col[1]*100):02d}_{int(col[2]*100):02d}_t{int(tr*100)}"
        if o.Label.startswith("LED channel"): key = "LED_emitter"
        b = buckets.setdefault(key, {"mesh": Mesh.Mesh(), "color": col, "material": mat, "transparency": tr, "labels": []})
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
        b["mesh"].addMesh(MeshPart.meshFromShape(Shape=s, LinearDeflection=0.08, AngularDeflection=0.35, Relative=False))
        b["labels"].append(o.Label)
        if o.Label.startswith("LED channel"):
            bb = s.BoundBox; scene["lights"].append({"label": o.Label, "bbox": [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]})
        if o.Label == "Nocturne lens":
            pl = o.getGlobalPlacement(); d = pl.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
            scene["camera"] = {"pos": [pl.Base.x, pl.Base.y, pl.Base.z], "dir": [d.x, d.y, d.z], "fov_diag_deg": 96.0, "aspect": 16 / 9}
    for k, b in buckets.items():
        b["mesh"].write(os.path.join(OUT, k + ".stl"))
        scene["buckets"][k] = {"color": b["color"], "material": b["material"], "transparency": b["transparency"],
                               "n": len(b["labels"]), "facets": b["mesh"].CountFacets, "labels": sorted(set(b["labels"]))[:40]}
        log(f"{k}: {len(b['labels'])} solids, {b['mesh'].CountFacets} facets")
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=1)
    log(f"done: {len(buckets)} buckets, {hidden} hidden solids skipped")
except Exception: log("FAILED\n" + traceback.format_exc())
finally: logf.close(); os._exit(0)
