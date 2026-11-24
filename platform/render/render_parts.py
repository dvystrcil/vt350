# Blender (Cycles) review image of a handful of STL parts: a quick look at one region, not the full scene render.
#   blender -b -P platform/render/render_parts.py -- <parts dir> <out.png> [--view X,Y,Z] [--up 0,0,1] [--size WxH]
#       [--samples N] [--colours colours.json] [--ortho 1] [--fit 1.15] [--target X,Y,Z] [--radius R]
# <parts dir>: one STL per part, plus parts.json: [{"file", "label", "role"}], role = a colours.json role name, or the
# two review roles "before" (grey, see-through) and "after" (orange). --view is the direction the camera looks FROM
# (from the target), default 3/4 front-left-above. The camera frames every part's box (times --fit). Model mm -> m.
# Generic: any printer's colour map works (VT350's is cad/render/colours.json).
import bpy, json, math, os, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
OPTS = {}
while any(a.startswith("--") for a in argv):            # --key value, or --key=value (for a value starting with "-")
    i = next(i for i, a in enumerate(argv) if a.startswith("--"))
    if "=" in argv[i]: k, v = argv[i][2:].split("=", 1); OPTS[k] = v; del argv[i]
    else: OPTS[argv[i][2:]] = argv[i + 1]; del argv[i:i + 2]
SRC, OUT = argv[0], argv[1]
vec = lambda k, d: Vector([float(v) for v in OPTS.get(k, d).split(",")])
VIEW, UP = vec("view", "-1,-1.4,0.9").normalized(), vec("up", "0,0,1")
W, H = (int(v) for v in OPTS.get("size", "1600x1000").split("x"))
SAMPLES, FIT, ORTHO = int(OPTS.get("samples", "64")), float(OPTS.get("fit", "1.15")), OPTS.get("ortho", "0") == "1"
roles = json.load(open(OPTS["colours"]))["roles"] if "colours" in OPTS else {}
S = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ("OPTIX", "CUDA"):
        try: prefs.compute_device_type = t; prefs.get_devices(); break
        except Exception: continue
    for d in prefs.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.view_settings.view_transform = 'AgX'


def hexrgb(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c] + [1.0]


mats = {}
def material(role):
    if role in mats: return mats[role]
    m = bpy.data.materials.new(role); bsdf = m.node_tree.nodes["Principled BSDF"]
    if role == "before":
        bsdf.inputs["Base Color"].default_value = hexrgb("#9A9A9A"); bsdf.inputs["Alpha"].default_value = 0.35
    elif role == "after":
        bsdf.inputs["Base Color"].default_value = hexrgb("#E2662A"); bsdf.inputs["Roughness"].default_value = 0.5
    else:
        r = roles.get(role, {"hex": "#B8B8B8", "kind": "plastic", "roughness": 0.6})
        bsdf.inputs["Base Color"].default_value = hexrgb(r["hex"])
        bsdf.inputs["Roughness"].default_value = r.get("roughness", 0.6)
        if r.get("kind") == "metal": bsdf.inputs["Metallic"].default_value = 1.0
    mats[role] = m; return m


lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for p in json.load(open(os.path.join(SRC, "parts.json"))):
    bpy.ops.wm.stl_import(filepath=os.path.join(SRC, p["file"]))
    o = bpy.context.selected_objects[0]; o.scale = (S, S, S); o.name = p["label"][:60]
    o.data.materials.append(material(p.get("role") or "Default"))
    bpy.context.view_layer.update()
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
centre = (lo + hi) / 2 if "target" not in OPTS else vec("target", "0,0,0") * S
radius = (hi - lo).length / 2 * FIT if "radius" not in OPTS else float(OPTS["radius"]) * S   # --radius R (mm): same framing for a before/after pair
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam)
cam_d.clip_start, cam_d.clip_end = 0.001, 100
if ORTHO:
    cam_d.type = 'ORTHO'; cam_d.ortho_scale = 2 * radius * max(1.0, W / H)
    cam.location = centre + VIEW * radius * 4
else:
    cam_d.lens = 50; fov = 2 * math.atan(36 / 2 / 50) * min(1.0, H / W)
    cam.location = centre + VIEW * (radius / math.sin(fov / 2))
cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
for name, d, e in (("key", (-0.5, -1, 1.2), 4.0), ("fill", (1, -0.3, 0.6), 1.5), ("top", (0, 0.2, 1), 2.0)):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = e; lo_ = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo_)
    lo_.rotation_euler = Vector(d).normalized().to_track_quat('Z', 'Y').to_euler()
world = bpy.data.worlds.new("w"); sc.world = world
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.92, 0.94, 1); world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("render_parts: wrote", OUT)
