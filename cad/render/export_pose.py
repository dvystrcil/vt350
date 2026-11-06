# Headless export of one toolhead-sweep pose for Blender (render.py). Read-only: never saves the model.
#   VT350_POSE="Left:front-left, top" VT350_RENDER_OUT=<dir> \
#     $APP freecadcmd /home/dan/Code/vt350/cad/render/export_pose.py
# Uses sweep_toolhead.plan() for the groups and the pose, so the picture shows exactly what the sweep checked.
# Colours are by ROLE, not the model's own (headless has no GuiDocument colours): carried head, plate, the two
# plate-bracket variants, carriage, gantry, bed, frame, and the overlap volumes themselves in red.
# Left out so the cameras can see in: door, roof and side panels, insulation, camera housing, ebox envelope.
# scene.json gets "views" (close-ups on the clash), which render.py renders instead of its default views.
import FreeCAD, Mesh, MeshPart, os, sys, json, time, traceback, tempfile
sys.path.insert(0, "/home/dan/Code/vt350/cad/scripts")
V = FreeCAD.Vector
POSE = os.environ.get("VT350_POSE", "Left:front-left, top")
OUT = os.environ.get("VT350_RENDER_OUT", "/tmp/vt350-pose-render")
SKIP_PATHS = {"Door (1) (1)", "Insulation: carbon felt sealed in aluminium"}
SKIP_LABEL_PREFIX = ("Roof panel", "Right side panel", "Camera housing", "Nocturne", "Ebox envelope")
os.makedirs(OUT, exist_ok=True)
logf = open(os.path.join(OUT, "export.log"), "w"); t0 = time.time()
def log(*a): logf.write(f"[{time.time() - t0:7.1f}s] " + " ".join(str(x) for x in a) + "\n"); logf.flush()
try:
    import sweep_toolhead as sw
    head, pid = POSE.split(":", 1)
    pj = os.path.join(tempfile.mkdtemp(prefix="pose-"), "plan.json")
    sw.plan(pj); plan = json.load(open(pj))
    doc = FreeCAD.ActiveDocument
    tr = plan["poses"][head][pid]
    meta = plan["meta"][f"{head}:{pid}"]
    log("pose", POSE, meta["what"], "translations", tr)
    t = plan["tool"][head]
    role = {}                                        # name -> (bucket, colour, material, transparency, group)
    def put(names, bucket, col, mat="Default", trn=0.0, grp=None):
        for n in names: role[n] = (bucket, col, mat, trn, grp)
    for n in plan["bed"]: role[n] = ("bed", (0.25, 0.25, 0.27), "Default", 0.0, "bed")
    put(plan["gantry"], "gantry", (0.20, 0.40, 0.85), "Default", 0.0, "gantry")    # role colour, not metal
    put(plan["carriage"], "carriage", (0.18, 0.18, 0.2), "Default", 0.0, "carriage")
    put(t["head"], "head", (0.78, 0.78, 0.8), "Default", 0.0, "head")
    put(t["plate"], "plate", (0.55, 0.2, 0.7), "Default", 0.0, "head")
    put([x for x in t["std"]], "bracket_std", (1.0, 0.5, 0.05), "Default", 0.0, "head")
    put(t["alt"], "bracket_alt", (1.0, 0.9, 0.1), "Default", 0.6, "head")
    other = [h for h in plan["heads"] if h != head][0]
    put([n for n in plan["heads"][other]], "parked_head", (0.6, 0.6, 0.62), "Default", 0.0, None)
    excl = set(plan["exclude"]) | {plan["tubes"][head]}
    buckets, moved, n_skip = {}, {}, 0
    for o in doc.Objects:
        if not (o.isDerivedFrom('Part::Feature') and not o.Shape.isNull() and o.Shape.Solids): continue
        if o.Name in excl: continue
        path = {p.Label for p in o.InListRecursive}
        if path & SKIP_PATHS or o.Label.startswith(SKIP_LABEL_PREFIX): n_skip += 1; continue
        bucket, col, mat, trn, grp = role.get(o.Name, ("frame", (0.62, 0.63, 0.66), "Aluminum", 0.0, None))
        if o.Label.startswith("Bowden"): bucket, col, mat = "bowden", (0.92, 0.92, 0.85), "PTFE"
        s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
        if grp: s.translate(V(*tr.get(grp, (0, 0, 0))))
        moved[o.Name] = (s, grp, o.Label)
        b = buckets.setdefault(bucket, {"mesh": Mesh.Mesh(), "color": col, "material": mat, "transparency": trn, "labels": []})
        b["mesh"].addMesh(MeshPart.meshFromShape(Shape=s, LinearDeflection=0.08, AngularDeflection=0.35, Relative=False))
        b["labels"].append(o.Label)
    # overlap volumes: carried head + carriage against everything that isn't on the head/carriage
    clash = Mesh.Mesh(); found = []
    mov = [(n, v) for n, v in moved.items() if v[1] in ("head", "carriage")]
    rest = [(n, v) for n, v in moved.items() if v[1] not in ("head", "carriage")]
    for na, (sa, ga, la) in mov:
        ba = sa.BoundBox
        for nb, (sb, gb, lb) in rest:
            if not ba.intersect(sb.BoundBox): continue
            try: c = sa.common(sb)
            except Exception: continue
            if c.Volume > 0.01:
                found.append((c.Volume, la, lb)); clash.addMesh(MeshPart.meshFromShape(Shape=c, LinearDeflection=0.05, AngularDeflection=0.3, Relative=False))
    if found:
        buckets["clash"] = {"mesh": clash, "color": (0.95, 0.05, 0.05), "material": "Default", "transparency": 0.0, "labels": ["overlap volumes"]}
    for v, la, lb in sorted(found, reverse=True): log(f"   overlap {v:8.2f} mm3  {la} x {lb}")
    scene = {"model": f"vt350-lite-22-{head}-{pid.replace(', ', '-').replace(' ', '-')}.FCStd", "buckets": {}, "lights": [], "camera": None}
    for k, b in buckets.items():
        b["mesh"].write(os.path.join(OUT, k + ".stl"))
        scene["buckets"][k] = {"color": b["color"], "material": b["material"], "transparency": b["transparency"],
                               "n": len(b["labels"]), "facets": b["mesh"].CountFacets, "labels": sorted(set(b["labels"]))[:40]}
        log(f"{k}: {len(b['labels'])} solids, {b['mesh'].CountFacets} facets")
    # cameras aimed at the overlap centre
    if found:
        cc = clash.BoundBox; c = V((cc.XMin + cc.XMax) / 2, (cc.YMin + cc.YMax) / 2, (cc.ZMin + cc.ZMax) / 2)
    else:
        nz = meta["nozzle"]; c = V(nz[0], nz[1], nz[2] + 50)
    side = 1 if c.x > -245 else -1                    # look from the chamber side, toward the frame wall
    # close-ups look from OUTSIDE the joint (frame hidden), so the head doesn't hide its own bracket
    focus = dict(hide=["frame", "bed", "parked_head", "bowden"], alpha={"head": 0.12, "gantry": 0.4, "bracket_alt": 0.35})
    scene["views"] = [
        {"name": "closeup", "pos": [c.x + side * 170, c.y - 150, c.z + 70], "look": [c.x, c.y, c.z], "lens_mm": 45, **focus},
        {"name": "top", "pos": [c.x + side * 30, c.y - 40, c.z + 240], "look": [c.x, c.y, c.z], "lens_mm": 40, **focus},
        {"name": "context", "pos": [c.x - side * 420, c.y - 520, c.z + 330], "look": [c.x - side * 120, c.y + 60, c.z - 40], "lens_mm": 30},
    ]
    scene["pose"] = {"pose": POSE, "what": meta["what"], "translations": tr, "overlaps": [[round(v, 2), la, lb] for v, la, lb in sorted(found, reverse=True)]}
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), indent=1)
    log(f"done: {len(buckets)} buckets, {len(found)} overlaps, {n_skip} solids left out for the view; centre {c}")
except Exception: log("FAILED\n" + traceback.format_exc())
finally: logf.close(); os._exit(0)
