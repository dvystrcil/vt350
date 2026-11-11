# FreeCAD GUI script: export a working copy as meshes for Blender (platform/render/render.py).
#   VT350_MODEL = .FCStd to read (default: the current working copy), VT350_RENDER_OUT = output folder,
#   VT350_EXTRA = more .FCStd files in the same global frame, ':'-separated (e.g. vt350-ebox.FCStd, lite-19),
#   VT350_COLOURS = colour map (default cad/render/colours.json; "none" = the model's own colours only).
#   VT350_GROUPS = a motion groups file (cad/motion/play.py's, vt350#135 AC4; platform/render/motion.py): each moving
#     group's parts go in buckets of their own, "<group>__<key>", with "group" in scene.json, so render.py --frames
#     can move them; "clip" parts are exported cut to their box, "hide" parts are left out. Unset: as before.
# Writes one binary STL per bucket in global coordinates (mm) and scene.json describing each bucket (colour,
# FreeCAD material card, labels, colour-map role), plus the camera / LED positions found in the model. A part the
# colour map gives a role goes in that role's bucket (#38). The rest bucket by (material, model colour) as before.
# Also writes each model's per-part box index beside it, <model>.parts.json (platform/freecad/part_index.py, #90),
# unless it is fresh; a failure there is logged as "index: FAILED" and does not fail the export.
# Never saves the model.
import FreeCAD, Part, Mesh, MeshPart, os, json, time, traceback, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # colours.py sits next to this script (laptop or a gpu-batch pod)
import colours
import logos                                       # Voron logos: orange, white inset (shared with export_exploded.py)
MODEL = os.environ.get("VT350_MODEL", "/home/dan/Documents/VT350/vt350-lite-16.FCStd")
OUT = os.environ.get("VT350_RENDER_OUT", "/tmp/claude-1000/-home-dan-Code/49170e9e-d71c-4cd7-8f69-23f113691ee5/scratchpad/render")
EXTRA = [p for p in os.environ.get("VT350_EXTRA", "").split(":") if p]
CMAP = None if os.environ.get("VT350_COLOURS") == "none" else colours.load(os.environ.get("VT350_COLOURS", colours.MAP_FILE))
class STATIC:                                      # no motion groups (as motion.Assign(None), without importing it:
    bucket = staticmethod(lambda name, key: (key, None))   # the batch lane's vt350-render chain stages no motion.py)
    hidden = staticmethod(lambda name: False); clip = staticmethod(lambda name: None)
GROUPS = STATIC
if os.environ.get("VT350_GROUPS"):                 # motion groups -> buckets (vt350#135 AC4)
    import motion
    GROUPS = motion.Assign(json.load(open(os.environ["VT350_GROUPS"])))
os.makedirs(OUT, exist_ok=True)
logf = open(os.path.join(OUT, "export.log"), "w"); t0 = time.time()
def log(*a): logf.write(f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); logf.flush()
try:
    buckets, scene = {}, {"model": os.path.basename(MODEL), "extra": [os.path.basename(p) for p in EXTRA], "buckets": {},
                          "lights": [], "camera": None, "roles": CMAP["roles"] if CMAP else {}}
    hidden = 0; uncoloured = {}; n_role = {}; n_motion = {"hide": 0, "clip": 0, "moving": 0}
    if os.environ.get("VT350_GROUPS"): scene["groups_file"] = os.environ["VT350_GROUPS"]
    for path_ in [MODEL] + EXTRA:
      doc = FreeCAD.openDocument(path_); log("opened", path_)
      G = GROUPS if path_ == MODEL else STATIC     # the groups name MODEL's objects; an extra file's may reuse a Name
      leaves = {o.Name: o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids}
      par = {}
      for g in doc.Objects:
          for k in (getattr(g, 'Group', []) or []): par.setdefault(k.Name, g)
      def gpath(o):
          r, p = [], par.get(o.Name)
          while p is not None: r.append(p.Label); p = par.get(p.Name)
          return " / ".join(reversed(r))
      for o in leaves.values():
        vo = o.ViewObject if FreeCAD.GuiUp else None
        if vo is not None and not vo.isVisible(): hidden += 1; continue
        if G.hidden(o.Name): n_motion["hide"] += 1; continue
        if EXTRA and o.Label.startswith(("Ebox envelope", "Filter envelope")): continue   # placeholders for vt350-ebox / vt350-filter merged in (lite-19, lite-27)
        if any(o2.isDerivedFrom('Part::Feature') and o2.Name in leaves for o2 in o.InList if o2.TypeId != 'App::Part'):
            continue    # consumed by a feature that is itself a leaf
        try:
            col = tuple(round(c, 2) for c in vo.ShapeAppearance[0].DiffuseColor[:3]) if vo else (0.7, 0.7, 0.7)
            tr = round(vo.Transparency / 100, 2) if vo else 0.0
        except Exception: col, tr = (0.7, 0.7, 0.7), 0.0
        mat = getattr(getattr(o, 'ShapeMaterial', None), 'Name', '') or 'Default'
        key = f"{re.sub('[^A-Za-z0-9]+', '_', mat)}__{int(col[0]*100):02d}_{int(col[1]*100):02d}_{int(col[2]*100):02d}_t{int(tr*100)}"
        role = None
        if o.Label.startswith("LED channel"): key = "LED_emitter"
        elif CMAP:
            role = colours.role_of(CMAP, o.Label, gpath(o), mat)
            if role: key = f"role_{role}_t{int(tr*100)}"; n_role[role] = n_role.get(role, 0) + 1
            elif mat == "Default" and tr == 0: uncoloured[o.Label] = gpath(o)
        key, grp = G.bucket(o.Name, key)
        if grp: n_motion["moving"] += 1
        b = buckets.setdefault(key, {"mesh": Mesh.Mesh(), "color": col, "material": mat, "transparency": tr, "labels": [],
                                     "role": role, "group": grp})
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
        cb = G.clip(o.Name)
        if cb:                                       # a belt loop: only the part that moves rigidly (player.py's clip)
            x0, y0, z0, x1, y1, z1 = cb; s = s.common(Part.makeBox(x1 - x0, y1 - y0, z1 - z0, FreeCAD.Vector(x0, y0, z0)))
            n_motion["clip"] += 1
        lg = logos.split(o.Label, s) if CMAP else None
        if lg:                                       # the inset goes to the printed (white) role's bucket
            ib = buckets.setdefault(G.bucket(o.Name, f"role_printed_t{int(tr*100)}")[0],
                                    {"mesh": Mesh.Mesh(), "color": col, "material": mat, "transparency": tr,
                                     "labels": [], "role": "printed", "group": grp})
            ib["mesh"].addMesh(MeshPart.meshFromShape(Shape=Part.Compound(lg[0]),
                               LinearDeflection=0.08, AngularDeflection=0.35, Relative=False))
            ib["labels"].append(o.Label + " (logo inset)"); s = Part.Compound(lg[1])
            log(f"logo {o.Label}: {len(lg[0])} inset faces white, {len(lg[1])} {role}")
        b["mesh"].addMesh(MeshPart.meshFromShape(Shape=s, LinearDeflection=0.08, AngularDeflection=0.35, Relative=False))
        b["labels"].append(o.Label)
        if o.Label.startswith("LED channel"):
            bb = s.BoundBox; scene["lights"].append({"label": o.Label, "bbox": [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]})
        if o.Label == "Nocturne lens":
            pl = o.getGlobalPlacement(); d = pl.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
            scene["camera"] = {"pos": [pl.Base.x, pl.Base.y, pl.Base.z], "dir": [d.x, d.y, d.z], "fov_diag_deg": 96.0, "aspect": 16 / 9}
    for k, b in buckets.items():
        b["mesh"].write(os.path.join(OUT, k + ".stl"))
        scene["buckets"][k] = {"color": b["color"], "material": b["material"], "transparency": b["transparency"], "role": b["role"],
                               **({"group": b["group"]} if b.get("group") else {}),
                               "n": len(b["labels"]), "facets": b["mesh"].CountFacets, "labels": sorted(set(b["labels"]))[:40]}
        log(f"{k}: {len(b['labels'])} solids, {b['mesh'].CountFacets} facets")
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=1)
    for path_ in [MODEL] + EXTRA:                  # per-part box index beside each model (#90); never fails the export
        try:
            up = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # platform/freecad, or a pod's scripts/
            sys.path[:0] = [os.path.join(up, "freecad"), os.path.join(up, "scripts")]
            import part_index
            doc = next(d for d in FreeCAD.listDocuments().values() if os.path.realpath(d.FileName) == os.path.realpath(path_))
            log(f"index: {part_index.refresh(doc, path_)} {part_index.sidecar(path_)}")
        except Exception as e: log(f"index: FAILED for {path_}: {type(e).__name__}: {e}")
    log(f"colour map: {n_role or 'off'}; {len(uncoloured)} solids with material Default kept the model's colour "
        "(printed parts among them need a rule in colours.json):")
    for lab, g in sorted(uncoloured.items(), key=lambda kv: (kv[1], kv[0])): log(f"   uncoloured  {lab}   [{g}]")
    if os.environ.get("VT350_GROUPS"):
        log(f"motion groups: {n_motion['moving']} moving solids, {n_motion['clip']} clipped, {n_motion['hide']} left out")
    log(f"done: {len(buckets)} buckets, {hidden} hidden solids skipped")
except Exception: log("FAILED\n" + traceback.format_exc())
finally: logf.close(); os._exit(0)
