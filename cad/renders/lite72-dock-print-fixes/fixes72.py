# lite-72 (vt350#59) before/after renders of the dock print fixes, from the printable STLs.
#   blender -b -P fixes72.py -- <in> <out>      <in> holds before/<part>.stl and after/<part>.stl (same frame)
# For each part, the regions that changed are found by distance (before vertices > TOL from every after vertex, and the
# other way round), grouped, and each group is rendered from above and below with the SAME camera before and after.
# Changed faces are tinted orange in both images; the rest is grey. Workbench shading: geometry, not materials.
import bpy, bmesh, sys, os, math
from mathutils import Vector, kdtree

a = sys.argv[sys.argv.index("--") + 1:]
IN, OUT = a[0], a[1]
os.makedirs(OUT, exist_ok=True)
PARTS = ["cowl-left", "cowl-right", "plate-left", "plate-right"]
TOL = 0.08            # mm: farther than this from the other mesh's vertices counts as changed
GROUP = 12.0          # mm: changed vertices this close together are one region
GREY, HIT = (0.72, 0.72, 0.74, 1), (0.95, 0.45, 0.10, 1)


def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)


def load(path):
    try: bpy.ops.wm.stl_import(filepath=path)
    except AttributeError: bpy.ops.import_mesh.stl(filepath=path)
    o = bpy.context.selected_objects[0]; return o


def verts(o): return [o.matrix_world @ v.co for v in o.data.vertices]


def tree(vs):
    t = kdtree.KDTree(len(vs))
    for i, v in enumerate(vs): t.insert(v, i)
    t.balance(); return t


def far(vs, t): return [i for i, v in enumerate(vs) if t.find(v)[2] > TOL]


def groups(points):
    out = []
    for p in points:
        for g in out:
            if (g["c"] - p).length < GROUP: g["p"].append(p); g["c"] = sum(g["p"], Vector()) / len(g["p"]); break
        else: out.append({"p": [p], "c": p.copy()})
    return [g for g in out if len(g["p"]) >= 3]


def tint(o, idx):
    """Colour the faces touching the changed vertices (face corner colours read by Workbench 'attribute')."""
    me = o.data; hit = set(idx)
    col = me.color_attributes.new("chg", "BYTE_COLOR", "CORNER")
    for poly in me.polygons:
        c = HIT if any(v in hit for v in poly.vertices) else GREY
        for li in poly.loop_indices: col.data[li].color = c
    me.color_attributes.active_color = col


def scene_setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "VERTEX"; sh.show_cavity = True; sh.cavity_type = "BOTH"
    sh.show_shadows = True; sh.shadow_intensity = 0.35; sh.show_object_outline = True
    sh.background_type = "VIEWPORT"; sh.background_color = (1, 1, 1)
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    sc.render.image_settings.file_format = "PNG"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.clip_start = 0.1; cam.data.clip_end = 2000
    return sc, cam


def aim(cam, centre, d, scale):
    d = Vector(d).normalized()
    cam.location = centre + d * 300
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale


VIEWS = {"above": (0.55, -0.75, 1.0), "below": (0.55, -0.75, -1.0)}
report = []
for part in PARTS:
    clear()
    b = load(f"{IN}/before/{part}.stl"); vb = verts(b)
    f = load(f"{IN}/after/{part}.stl"); vf = verts(f)
    gone = far(vb, tree(vf)); new = far(vf, tree(vb))
    regs = groups([vb[i] for i in gone] + [vf[i] for i in new])
    report.append(f"{part}: {len(gone)} before-only and {len(new)} after-only vertices, {len(regs)} region(s): "
                  + ", ".join(f"({g['c'].x:.1f}, {g['c'].y:.1f}, {g['c'].z:.1f}) n={len(g['p'])}" for g in regs))
    tint(b, gone); tint(f, new)
    sc, cam = scene_setup()
    for k, g in enumerate(regs, 1):
        ext = max(max(abs((p - g["c"])[j]) for p in g["p"]) for j in range(3))
        for vname, d in VIEWS.items():
            aim(cam, g["c"], d, max(28.0, 4.0 * ext))
            for obj, tag in ((b, "before"), (f, "after")):
                b.hide_render = obj is not b; f.hide_render = obj is not f
                sc.render.filepath = f"{OUT}/{part}-r{k}-{vname}-{tag}.png"
                bpy.ops.render.render(write_still=True)
open(f"{OUT}/regions.txt", "w").write("\n".join(report) + "\n")
print("\n".join(report))
