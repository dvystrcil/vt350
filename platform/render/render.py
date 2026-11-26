# Blender (Cycles) render of the meshes written by export_meshes.py.
#   blender -b -P platform/render/render.py -- <export dir> <output dir> [samples]
# Writes <model>-<view>.png (master) and <model>-<view>.jpg (quality 85: the README image, cad/renders/).
# Views: "obico"   = what the Nocturne camera sees, chamber lit only by the LED strips (room dim);
#        "outside" = 3/4 front view, studio light plus the LED strips;
#        "low_front", "low_side" = only for a model on its stand (a "Base board" part, lite-27): the feet, board and
#        the filter recessed under the backbone, seen from just above the board.
#        "dock_top", "dock_below" = only for a model with the front dock bar (lite-32, vt350#19): the tool row seen
#        straight down and straight up, orthographic (true scale, no perspective), to read the heads' clearances to
#        the bar and its brackets. Each camera's near clip plane cuts away what is in the way: the lid and top frame
#        above Z 560 for dock_top, the bed and everything below Z 380 (the nozzle tips) for dock_below. Both have the
#        printer's front at the bottom of the image; dock_below is seen from underneath, so it is mirrored left-right
#        against dock_top (the printer's left, slot 1, is on the image's right).
#        "ebox_side" = only for a model with the e-box's inner frame (lite-53, vt350#5): the e-box seen straight on from
#        its outer side, orthographic, front on the left.
#        "glamour", "glamour_ebox" = also only with the e-box: the whole machine, EMU included, 3/4 from the front;
#        glamour_ebox swung round to the right to look in through the e-box door.
#   blender -b -P render.py -- <export dir> <output dir> [samples] --only dock_top,dock_below   renders just those views
# Motion frames (vt350#135 AC4): an export made with VT350_GROUPS (each moving group's parts in buckets of their own)
#   blender -b -P render.py -- <export dir> <output dir> [samples] --frames <frames.json, relative: in the export dir>
#       [--view NAME] [--size WxH] [--first N] [--count N]
#   --size WxH also sets the size of ordinary view renders (default 1920x1080).
#   --look NAME: an AgX look, e.g. "AgX - Punchy" (richer colour, more contrast); default none, as before.
#   --plastic-specular F: the Principled "Specular IOR Level" of plastic and paint (default Blender's 0.5); 0.2 = less
#     sheen. Both opt-in (vt350#220, owner 2026-11-17: the turntable and viewer use Punchy + 0.2); colours.json's frame
#     hex was tuned under the default look, so README renders keep it.
# renders one PNG per frame, frame-NNNNN.png, from the scene's explicit view NAME (default its first), moving each
# group's objects by the frame's translation (platform/render/motion.py). Frames already in the output dir are skipped,
# so a run cut short resumes. --first/--count take a slice of the frames list (to split a long run).
# Units: model mm -> scene metres (x 0.001).
import bpy, json, math, os, sys
if bpy.app.version < (5, 0): sys.exit("needs Blender 5.0+, where new materials and worlds come with node trees (#247)")
argv = sys.argv[sys.argv.index("--") + 1:]
OPTS = {}
while any(a.startswith("--") for a in argv):
    i = next(i for i, a in enumerate(argv) if a.startswith("--")); OPTS[argv[i][2:]] = argv[i + 1]; del argv[i:i + 2]
SRC, OUT = argv[0], argv[1]; SAMPLES = int(argv[2]) if len(argv) > 2 else 128
# colours.py (and motion.py) sit next to this script; a single-script batch-lane job stages them in the export dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(SRC))
import colours                                       # #38: role colours from colours.json (via scene.json)
from mathutils import Vector
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
if "size" in OPTS:                                  # --size WxH: any render, not only motion frames (vt350#220 turntable)
    sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in OPTS["size"].lower().split("x"))
sc.view_settings.view_transform = 'AgX'
if "look" in OPTS: sc.view_settings.look = OPTS["look"]
PLASTIC_SPEC = float(OPTS["plastic-specular"]) if "plastic-specular" in OPTS else None
def kelvin_rgb(k):   # Tanner Helland's approximation, good enough for a strip colour
    t = k / 100
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(max(0, min(255, c)) / 255 for c in (r, g, b))
LED_K = 3800
def material(name, color, kind, transparency=0.0, roughness=None):
    m = bpy.data.materials.new(name)                 # 5.0+: new materials come with a Principled BSDF tree (#247)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    metal = kind in ("aluminium", "steel", "brass")
    p.inputs["Metallic"].default_value = 1.0 if metal else 0.0
    p.inputs["Roughness"].default_value = roughness if roughness is not None else \
        {"aluminium": 0.35, "steel": 0.3, "brass": 0.3, "felt": 0.95, "ptfe": 0.4}.get(kind, 0.5)
    if PLASTIC_SPEC is not None and kind in ("plastic", "paint") and "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = PLASTIC_SPEC
    if kind == "glass":                              # a clear sheet (the door window, lite-38): transmits, ~no tint
        for n in ("Transmission Weight", "Transmission"):   # Blender 4.x name, then 3.x
            if n in p.inputs: p.inputs[n].default_value = 1.0; break
        p.inputs["IOR"].default_value = 1.49
        p.inputs["Roughness"].default_value = roughness if roughness is not None else 0.03
    if kind == "glow":                               # overlap volumes in export_pose.py scenes: visible inside anything
        p.inputs["Emission Color"].default_value = (*color, 1); p.inputs["Emission Strength"].default_value = 8.0
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
# role colours: the CURRENT colours.json (so a colour-only edit re-renders from an old export), else the export's copy
try: ROLES = dict(scene_j.get("roles", {}), **colours.load()["roles"])
except Exception as e: print("colours.json not loaded:", e); ROLES = scene_j.get("roles", {})
OBJ = {}                                             # bucket -> its object (Blender cuts names at 63 bytes)
for key, b in scene_j["buckets"].items():
    path = os.path.join(SRC, key + ".stl")
    if not os.path.exists(path): continue
    bpy.ops.wm.stl_import(filepath=path, global_scale=S)
    ob = bpy.context.selected_objects[0]; ob.name = key; OBJ[key] = ob
    kind = "emitter" if key == "LED_emitter" else "glow" if key == "clash" else kind_of(b["material"], (b["labels"] or [""])[0])
    col = tuple(b["color"]); rough = None
    role = ROLES.get(b.get("role") or "")
    if role:                                         # colour map role (#38): sRGB hex -> linear, its own finish
        col = colours.linear(role["hex"]); kind = role.get("kind", "plastic"); rough = role.get("roughness")
    elif kind in ("aluminium", "steel"): col = tuple(min(1, max(0.55, c)) for c in col)
    ob.data.materials.append(material(key, col, kind, b.get("transparency", 0), rough))
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35)) if hasattr(bpy.ops.object, "shade_auto_smooth") else None
# LED strips: also a real area light under each channel, facing down, so the strip lights the chamber
for L in scene_j["lights"]:
    x0, x1, y0, y1, z0, z1 = L["bbox"]
    bpy.ops.object.light_add(type='AREA', location=((x0 + x1) / 2 * S, (y0 + y1) / 2 * S, (z0 - 0.5) * S))
    li = bpy.context.object; li.data.shape = 'RECTANGLE'; li.data.size = (x1 - x0) * S; li.data.size_y = (y1 - y0) * S
    li.data.energy = 6.0; li.data.color = kelvin_rgb(LED_K); li.rotation_euler = (math.pi, 0, 0)   # face -Z
    li.name = L["label"]
# world: dim grey room
w = bpy.data.worlds.new("room"); sc.world = w       # 5.0+: comes with a Background node tree (#247)
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
def add_ortho(name, centre, width, z, clip_z):
    """A camera looking straight down (z above clip_z) or straight up (z below), orthographic, `width` mm across,
    with the near clip plane at Z clip_z: what is between the camera and that plane is not drawn."""
    cd = bpy.data.cameras.new(name); co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    cd.type = 'ORTHO'; cd.ortho_scale = width * S; cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start = abs(z - clip_z) * S; cd.clip_end = 20
    co.location = Vector((centre[0], centre[1], z)) * S
    co.rotation_euler = (0, 0, 0) if z > clip_z else (math.pi, 0, math.pi)   # both: image up = printer rear (+Y)
    return co
def add_ortho_side(name, centre, width, x, clip_x):
    """A camera looking along -X from X `x` (beyond clip_x), orthographic, `width` mm across, image up = +Z and
    image right = +Y (the printer's rear); what is between the camera and the plane X clip_x is not drawn."""
    cd = bpy.data.cameras.new(name); co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    cd.type = 'ORTHO'; cd.ortho_scale = width * S; cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start = (x - clip_x) * S; cd.clip_end = 20
    co.location = Vector((x, centre[0], centre[1])) * S
    co.rotation_euler = (math.pi / 2, 0, math.pi / 2)   # the camera's -Z (its view) turned onto -X, its up onto +Z
    return co
DOCK_BAR = ("2020 dock bar", "Dock bar 2020")          # the front dock bar's labels (lite-31, lite-32)
EBOX_FRAME = ("2020 e-box inner upright",)            # the e-box's inner frame (lite-53, vt350#5)
EBOX_CLIP_X = float(OPTS.get("ebox-clip", "210"))     # ebox_side's near plane: beyond the e-box door (X 132..201), which colours.json hides
                                                     # for this view (owner 2026-11-26; 165 cut inside the door frame)
views = []
c = scene_j["camera"]
if scene_j.get("views"):                             # explicit cameras (export_pose.py): render only these, key-lit
    for v in scene_j["views"]:
        views.append((v["name"], add_cam(v["name"], v["pos"], v["look"], lens_mm=v.get("lens_mm", 35)), 1.0, v.get("ev", -0.5)))
elif c:
    pos = Vector(c["pos"]) + Vector(c["dir"]) * 1.0        # just in front of the lens
    views.append(("obico", add_cam("obico", pos, pos + Vector(c["dir"]) * 100, fov_diag=c["fov_diag_deg"]), 0.15, -1.6))
if not scene_j.get("views"):
    views.append(("outside", add_cam("outside", (480, -1500, 1150), (-245, 215, 300), lens_mm=35), 1.0, -1.0))
    # a model on its stand (lite-27: levelling feet + base board, #83) also gets two low views of the base and the
    # filter recessed under the backbone (#74), camera just above the board top (Z -100)
    if any(lab.startswith("Base board") for b in scene_j["buckets"].values() for lab in b.get("labels", [])):
        # framed on the base: board (Z -118..-100) in the lower third, frame bottom (Z -50) mid-frame, camera
        # 30 mm above the board so the filter shows between the feet under the bottom extrusions
        views.append(("low_front", add_cam("low_front", (105, -555, -70), (-245, 225, -15), lens_mm=35), 1.0, -0.6))
        views.append(("low_side", add_cam("low_side", (-1145, -25, -70), (-245, 225, 5), lens_mm=35), 1.0, 0.4))   # unlit side: +1 EV
    # the dock row (vt350#19): X -565..75 (the front verticals and a margin), Y -200..160 (bar front .. carriages)
    if any(lab.startswith(DOCK_BAR) for b in scene_j["buckets"].values() for lab in b.get("labels", [])):
        views.append(("dock_top", add_ortho("dock_top", (-245, -20), 640, 2000, 560), 1.0, -0.6))
        views.append(("dock_below", add_ortho("dock_below", (-245, -20), 640, -1500, 380), 1.0, 0.8))
    # the e-box (vt350#5): its whole outer side, Z -50..690 (1460 wide at 16:9 is 821 tall), seen from outside, ortho;
    # the clip plane at X 165 is just outside the e-box's outer members (X 140..160), so nothing outside it is drawn
    if any(lab.startswith(EBOX_FRAME) for b in scene_j["buckets"].values() for lab in b.get("labels", [])):
        views.append(("ebox_side", add_ortho_side("ebox_side", (215, 320), 1460, 1500, EBOX_CLIP_X), 1.0, 0.4))
        # two glamour shots of the whole machine (owner, 2026-11-16): the scene is X -554..201, Y -151..548,
        # Z -108..1040 with the EMU on the roof (its top is cut off in "outside"). "glamour": outside's direction, far
        # enough back for all 1150 mm of height; "glamour_ebox": the printer turned ~30 degrees to the left (the camera
        # swung round to the right), so the view goes in through the clear e-box door (its outer face, +X)
        views.append(("glamour", add_cam("glamour", (824, -2167, 1294), (-176, 200, 466), lens_mm=35), 1.0, -1.0))
        views.append(("glamour_ebox", add_cam("glamour_ebox", (1876, -1347, 1294), (-150, 200, 420), lens_mm=35), 1.0, -1.0))
if "only" in OPTS:
    keep = OPTS["only"].split(",")
    if not set(keep) <= {v[0] for v in views}: raise SystemExit(f"render: --only {keep}, but the views are {[v[0] for v in views]}")
    views = [v for v in views if v[0] in keep]
VIEWDEF = {v["name"]: v for v in scene_j.get("views", [])}
SHOW_ALL = OPTS.get("show-all", "") in ("1", "true", "yes")   # --show-all 1: ignore the visibility flags
def apply_view(name):                                # per-view "hide": [bucket], "alpha": {bucket: alpha}; plus the
    # visibility flags (colours.json, via scene.json): a bucket flagged "vis" is hidden in the views its rule names
    v = VIEWDEF.get(name, {})
    for key, b in scene_j["buckets"].items():
        ob = bpy.data.objects.get(key)
        if ob is None: continue
        ob.hide_render = key in v.get("hide", []) or (not SHOW_ALL and colours.hidden_in(scene_j, b.get("vis"), name))
        a = v.get("alpha", {}).get(key, 1 - b.get("transparency", 0))
        ob.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = a
# key light for the outside view only
bpy.ops.object.light_add(type='AREA', location=(0.6, -1.4, 1.6)); key = bpy.context.object
key.data.size = 1.2; key.data.energy = 500; key.rotation_euler = (math.radians(55), 0, math.radians(20))
bpy.context.view_layer.update(); KEY0 = key.matrix_world.copy()
def place_key(name):
    """A view with "light_turn_deg" (a turntable frame, vt350#220) gets the key light turned by that angle about the
    vertical line through its "look" point, so every frame is lit as the first: the camera and the light go round
    together, as if the model turned. "light_tilt_deg" first tilts it up (+) or down (-) about the line through "look"
    along X (the unturned view's left-right), so a camera below the model has the key below too. Any other view: the
    key where it always is."""
    v = VIEWDEF.get(name, {})
    if "light_turn_deg" not in v: key.matrix_world = KEY0; return
    from mathutils import Matrix
    c = Vector(v["look"]) * S
    tilt = Matrix.Rotation(-math.radians(v.get("light_tilt_deg", 0)), 4, 'X')   # +X rotation lowers a -Y point: negate
    key.matrix_world = Matrix.Translation(c) @ Matrix.Rotation(math.radians(v["light_turn_deg"]), 4, 'Z') @ tilt @ Matrix.Translation(-c) @ KEY0
if "frames" in OPTS:                                 # motion frames (vt350#135 AC4), then stop
    import motion
    fp = OPTS["frames"] if os.path.isabs(OPTS["frames"]) else os.path.join(SRC, OPTS["frames"])   # a lane job: in/
    ff = json.load(open(fp))
    motion.check_scene(ff, scene_j)
    pick = [v for v in views if v[0] == OPTS.get("view", views[0][0])]
    if not pick: raise SystemExit(f"render: no view {OPTS['view']!r} in scene.json (have {[v[0] for v in views]})")
    name, cam, room, ev = pick[0]
    sc.camera = cam; sc.view_settings.exposure = ev; bg.inputs["Strength"].default_value = 0.4 * room
    key.hide_render = name == "obico"
    apply_view(name); place_key(name)
    if "size" in OPTS: sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in OPTS["size"].lower().split("x"))
    sc.render.use_persistent_data = True             # only locations change between frames
    sc.render.image_settings.file_format = 'PNG'
    first = int(OPTS.get("first", 0)); frames = ff["frames"][first:first + int(OPTS.get("count", len(ff["frames"])))]
    todo = [f for f in frames if not os.path.exists(os.path.join(OUT, motion.frame_name(f["i"])))]
    print(f"frames: {len(frames)} in the slice, {len(frames) - len(todo)} already rendered, {len(todo)} to render")
    for f in todo:
        for k, d in motion.offsets(f, scene_j["buckets"]).items():
            if k in OBJ: OBJ[k].location = Vector(d) * S
        sc.render.filepath = os.path.join(OUT, motion.frame_name(f["i"]))
        bpy.ops.render.render(write_still=True); print("wrote", sc.render.filepath, flush=True)
    print(f"frames: done, {len(frames)} in {OUT}")
    raise SystemExit(0)
for name, cam, room, ev in views:
    sc.camera = cam; sc.view_settings.exposure = ev; bg.inputs["Strength"].default_value = 0.4 * room
    key.hide_render = name == "obico"
    apply_view(name); place_key(name)
    sc.render.filepath = os.path.join(OUT, f"{scene_j['model'].replace('.FCStd', '')}-{name}.png")
    bpy.ops.render.render(write_still=True); print("wrote", sc.render.filepath)
    # The README image (homelab#1961 AC8): the same render as a quality-85 JPEG, the format cad/renders/ holds,
    # so a render here or in the batch lane drops straight into the README. The PNG stays the lossless master.
    jpg, im = sc.render.filepath[:-len(".png")] + ".jpg", sc.render.image_settings
    im.file_format, im.quality = 'JPEG', 85
    bpy.data.images["Render Result"].save_render(jpg, scene=sc); print("wrote", jpg)
    im.file_format = 'PNG'
