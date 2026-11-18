# Blender: the meshes written by platform/render/export_meshes.py -> one GLB for a web viewer (vt350#220).
#   blender -b -P platform/viewer/glb.py -- <export dir> <out.glb> [--decimate RATIO] [--draco 1]
# One object per bucket, with the same PBR material render.py gives it (colour-map roles from colours.json via
# scene.json, else the bucket's own colour; metallic / roughness / alpha / transmission / emission), so the viewer
# shows the renders' colours (AC2). glTF keeps colour, metallic, roughness, alpha, transmission and emission; it has
# no Cycles lighting, so the page lights it.
# Units: model mm -> metres (x 0.001); the glTF exporter turns Blender's Z-up into glTF's Y-up.
# --decimate RATIO (0..1): collapse-decimate every mesh to that share of its triangles (a smaller file).
# --draco 1: Draco mesh compression (the page then needs three.js's DRACOLoader).
# --json 1: also write <out minus .glb>.gltf.json, the same glTF as one JSON file with its buffer embedded (base64,
#   ~1/3 bigger), for hosts that serve .json but not .glb (claude.ai artifacts). glbjson.py does the conversion.
# Prints "glb: <path> <bytes> bytes, <n> triangles, <k> objects" and "glb-export: OK" at the end.
import bpy, bmesh, json, math, os, sys
argv = sys.argv[sys.argv.index("--") + 1:]
OPTS = {}
while any(a.startswith("--") for a in argv):
    i = next(i for i, a in enumerate(argv) if a.startswith("--")); OPTS[argv[i][2:]] = argv[i + 1]; del argv[i:i + 2]
SRC, OUT = argv[0], argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "render")]   # colours.py: platform/render, or flat in a pod
import colours
S = 0.001
scene_j = json.load(open(os.path.join(SRC, "scene.json")))
bpy.ops.wm.read_factory_settings(use_empty=True)


# The material mapping is render.py's (material(), kind_of(), the role lookup), restricted to what glTF carries.
# Keep the two in step (render.py builds its materials inline, so they can't be shared without changing what the
# batch lane stages).
def kind_of(mat, label0):
    m = mat.lower()
    if "alumin" in m: return "aluminium"
    if "steel" in m: return "steel"
    if "brass" in m or "copper" in m: return "brass"
    if "ptfe" in m: return "ptfe"
    if "felt" in label0.lower(): return "felt"
    return "plastic"


def pbr(key, b, roles):
    """-> (base colour linear RGB, metallic, roughness, alpha, transmission, emission RGB or None) as render.py."""
    kind = "emitter" if key == "LED_emitter" else kind_of(b["material"], (b["labels"] or [""])[0])
    col = tuple(b["color"]); rough = None
    role = roles.get(b.get("role") or "")
    if role:
        col = colours.linear(role["hex"]); kind = role.get("kind", "plastic"); rough = role.get("roughness")
    elif kind in ("aluminium", "steel"):
        col = tuple(min(1, max(0.55, c)) for c in col)
    metal = 1.0 if kind in ("aluminium", "steel", "brass") else 0.0
    r = rough if rough is not None else {"aluminium": 0.35, "steel": 0.3, "brass": 0.3, "felt": 0.95, "ptfe": 0.4}.get(kind, 0.5)
    trans = 0.0
    if kind == "glass": trans = 1.0; r = rough if rough is not None else 0.03
    emis = (1.0, 0.8, 0.6) if kind == "emitter" else None
    return col, metal, r, 1 - b.get("transparency", 0), trans, emis


def material(key, b, roles):
    col, metal, rough, alpha, trans, emis = pbr(key, b, roles)
    m = bpy.data.materials.new(key); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Metallic"].default_value = metal; p.inputs["Roughness"].default_value = rough
    if trans:
        for n in ("Transmission Weight", "Transmission"):
            if n in p.inputs: p.inputs[n].default_value = trans; break
    if emis:
        p.inputs["Emission Color"].default_value = (*emis, 1); p.inputs["Emission Strength"].default_value = 3.0
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
        elif hasattr(m, "blend_method"): m.blend_method = 'BLEND'
    return m


try: ROLES = dict(scene_j.get("roles", {}), **colours.load()["roles"])   # the CURRENT colours.json, as render.py
except Exception as e: print("colours.json not loaded:", e); ROLES = scene_j.get("roles", {})
tris = 0
for key, b in scene_j["buckets"].items():
    path = os.path.join(SRC, key + ".stl")
    if not os.path.exists(path) or b.get("facets", 1) == 0: continue
    bpy.ops.wm.stl_import(filepath=path, global_scale=S)
    ob = bpy.context.selected_objects[0]; ob.name = key
    bm = bmesh.new(); bm.from_mesh(ob.data)               # STL triangles share no vertices: weld them (1 µm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(ob.data); bm.free()
    if "decimate" in OPTS:
        md = ob.modifiers.new("dec", 'DECIMATE'); md.ratio = float(OPTS["decimate"])
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="dec")
    ob.data.materials.append(material(key, b, ROLES))
    bpy.context.view_layer.objects.active = ob
    if hasattr(bpy.ops.object, "shade_smooth_by_angle"): bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    elif hasattr(bpy.ops.object, "shade_auto_smooth"): bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    ob["labels"] = ", ".join(b.get("labels", []))[:2000]   # glTF "extras": what the bucket holds
    tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
kw = dict(filepath=OUT, export_format='GLB', export_apply=True, export_extras=True, export_yup=True)
if OPTS.get("draco") == "1":
    kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7)
bpy.ops.export_scene.gltf(**kw)
n = len([o for o in bpy.data.objects if o.type == 'MESH'])
print(f"glb: {OUT} {os.path.getsize(OUT)} bytes, {tris} triangles, {n} objects")
if OPTS.get("json") == "1":
    import glbjson
    js = (OUT[:-4] if OUT.endswith(".glb") else OUT) + ".gltf.json"
    glbjson.write(OUT, js); print(f"glb: {js} {os.path.getsize(js)} bytes (embedded JSON)")
print("glb-export: OK")
