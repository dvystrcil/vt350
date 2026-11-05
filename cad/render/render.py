# Blender (Cycles) render of the meshes written by export_meshes.py.
#   blender -b -P cad/render/render.py -- <export dir> <output dir> [samples]
# Views: "obico"   = what the Nocturne camera sees, chamber lit only by the LED strips (room dim);
#        "outside" = 3/4 front view, studio light plus the LED strips.
# Units: model mm -> scene metres (x 0.001).
import bpy, json, math, os, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]; SAMPLES = int(argv[2]) if len(argv) > 2 else 128
os.makedirs(OUT, exist_ok=True)
scene_j = json.load(open(os.path.join(SRC, "scene.json")))
S = 0.001
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t; prefs.get_devices()
            if any(d.type == t for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == t
                sc.cycles.device = 'GPU'; print("GPU:", t); break
        except Exception: pass
except Exception as e: print("no GPU prefs", e)
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = 'AgX'
def kelvin_rgb(k):   # Tanner Helland's approximation, good enough for a strip colour
    t = k / 100
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0, min(255, c)) / 255 for c in (r, g, b))
LED_K = 3800
def material(name, color, kind, transparency=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    metal = kind in ("aluminium", "steel", "brass")
    p.inputs["Metallic"].default_value = 1.0 if metal else 0.0
    p.inputs["Roughness"].default_value = {"aluminium": 0.35, "steel": 0.3, "brass": 0.3, "felt": 0.95, "ptfe": 0.4}.get(kind, 0.5)
    if kind == "emitter":
        p.inputs["Emission Color"].default_value = (*kelvin_rgb(LED_K), 1); p.inputs["Emission Strength"].default_value = 60.0
    if transparency > 0:
        p.inputs["Alpha"].default_value = 1 - transparency
    return m
def kind_of(mat, label0):
    m = mat.lower()
    if "alumin" in m: return "aluminium"
    if "steel" in m: return "steel"
    if "brass" in m or "copper" in m: return "brass"
    if "ptfe" in m: return "ptfe"
    if "felt" in label0.lower(): return "felt"
    return "plastic"
for key, b in scene_j["buckets"].items():
    path = os.path.join(SRC, key + ".stl")
    if not os.path.exists(path): continue
    bpy.ops.wm.stl_import(filepath=path, global_scale=S)
    ob = bpy.context.selected_objects[0]; ob.name = key
    kind = "emitter" if key == "LED_emitter" else kind_of(b["material"], (b["labels"] or [""])[0])
    col = tuple(b["color"])
    if kind in ("aluminium", "steel"): col = tuple(min(1, max(0.55, c)) for c in col)
    ob.data.materials.append(material(key, col, kind, b.get("transparency", 0)))
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35)) if hasattr(bpy.ops.object, "shade_auto_smooth") else None
# LED strips: also a real area light under each channel, facing down, so the strip lights the chamber
for L in scene_j["lights"]:
    x0, x1, y0, y1, z0, z1 = L["bbox"]
    bpy.ops.object.light_add(type='AREA', location=((x0 + x1) / 2 * S, (y0 + y1) / 2 * S, (z0 - 0.5) * S))
    li = bpy.context.object; li.data.shape = 'RECTANGLE'; li.data.size = (x1 - x0) * S; li.data.size_y = (y1 - y0) * S
    li.data.energy = 6.0; li.data.color = kelvin_rgb(LED_K); li.rotation_euler = (math.pi, 0, 0)   # face -Z
    li.name = L["label"]
# world: dim grey room
w = bpy.data.worlds.new("room"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1); bg.inputs["Strength"].default_value = 0.4
def add_cam(name, pos, look, fov_diag=None, lens_mm=None, sensor=36.0):
    cd = bpy.data.cameras.new(name); co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    co.location = Vector(pos) * S
    d = (Vector(look) - Vector(pos)); co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.clip_start = 0.002; cd.clip_end = 20
    if fov_diag:
        ar = 16 / 9; k = math.tan(math.radians(fov_diag) / 2) / math.hypot(ar, 1)
        cd.sensor_fit = 'HORIZONTAL'; cd.angle = 2 * math.atan(k * ar)
    if lens_mm: cd.lens = lens_mm; cd.sensor_width = sensor
    return co
views = []
c = scene_j["camera"]
if c:
    pos = Vector(c["pos"]) + Vector(c["dir"]) * 1.0        # just in front of the lens
    views.append(("obico", add_cam("obico", pos, pos + Vector(c["dir"]) * 100, fov_diag=c["fov_diag_deg"]), 0.15, -1.6))
views.append(("outside", add_cam("outside", (480, -1500, 1150), (-245, 215, 300), lens_mm=35), 1.0, -1.0))
# key light for the outside view only
bpy.ops.object.light_add(type='AREA', location=(0.6, -1.4, 1.6)); key = bpy.context.object
key.data.size = 1.2; key.data.energy = 500; key.rotation_euler = (math.radians(55), 0, math.radians(20))
for name, cam, room, ev in views:
    sc.camera = cam; sc.view_settings.exposure = ev; bg.inputs["Strength"].default_value = 0.4 * room
    key.hide_render = name == "obico"
    sc.render.filepath = os.path.join(OUT, f"{scene_j['model'].replace('.FCStd', '')}-{name}.png")
    bpy.ops.render.render(write_still=True); print("wrote", sc.render.filepath)
