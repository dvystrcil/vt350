# A cutaway of the printer for renders (vt350#312, owner 2026-11-26: "a slice away of the printer which shows one complete
# system"): everything left of a cut plane X = CUT is left out, a part the plane crosses is exported cut to it, and the
# other tools' bowden arms, bundles, sheaves and clips are hidden so one tool's system reads alone.
#
#   python3 cad/render/cutaway.py groups <model.parts.json> <groups.json> [--cut X] [--tool T]
#       -> a VT350_GROUPS file for platform/render/export_meshes.py ({"clip": {Name: box}, "hide": [Name]})
#   python3 cad/render/cutaway.py views <export dir> [--tool T]
#       -> writes the cutaway's cameras into <export dir>/scene.json ("views"), for platform/render/render.py
#
# The whole run (no window: xvfb-run; heavy jobs one at a time: heavy-run.sh):
#   M=~/Documents/VT350/preview/vt350-lite-81-preview.FCStd; E=<run>/export
#   VT350_INDEX_MODELS=$M VT350_WORKERS=1 $APP freecadcmd $PWD/platform/freecad/part_index.py
#   python3 cad/render/cutaway.py groups ${M%.FCStd}.parts.json /tmp/cut.json
#   VT350_MODEL=$M VT350_EXTRA= VT350_RENDER_OUT=$E VT350_GROUPS=/tmp/cut.json VT350_COLOURS=cad/render/colours.json \
#       xvfb-run -a $APP platform/render/export_meshes.py
#   python3 cad/render/cutaway.py views $E
#   blender -b -P platform/render/render.py -- $E <run>/out 128
#
# Default: T1 (slot 2), whose arm (X -324.5) and sheave stack (X -324.2) line up, cut at X -392 (left of its sheave's
# exit leg, X -377.8, and its head). Plain python3; no FreeCAD.
import json, re, sys

BIG = 5000.0
SMALL = 150.0                                  # mm in X: smaller parts aren't cut (no slivers of the next head)
TUBES = ["Bowden Left", "Bowden slot 2", "Bowden slot 3", "Bowden slot 4", "Bowden Right"]


def other_tool(label, tool):
    """Is this part one of the other tools' arm / dancer / bundle parts?"""
    m = re.match(r"(Bowden arm|Dancer sheave|Dancer bearing|Dancer axle|Bundle split clip|Arm hold) T(\d)\b", label)
    if m:
        return int(m.group(2)) != tool
    m = re.match(r"O2S USB cable slot (\d) ", label)
    if m:
        return int(m.group(1)) - 1 != tool
    return label in TUBES and TUBES.index(label) != tool


def groups(index, cut, tool):
    clip, hide = {}, []
    for p in index["parts"]:
        b, n = p["bbox"], p["name"]
        small = b["xmax"] - b["xmin"] < SMALL           # a small part the plane crosses goes whole, to its side
        if other_tool(p["label"], tool) or b["xmax"] <= cut or (small and (b["xmin"] + b["xmax"]) / 2 < cut):
            hide.append(n)
        elif b["xmin"] < cut and not small:
            clip[n] = [cut, -BIG, -BIG, BIG, BIG, BIG]
    return {"groups": {}, "clip": clip, "hide": hide}


VIEWS = [  # name, camera position, look-at (model mm), lens, exposure
    ("cut_side", (-2050, 190, 330), (-324, 190, 330), 35, -0.6),     # straight at the cut face (the sheave is edge-on)
    ("cut_3q", (-1500, -1000, 1150), (-300, 230, 330), 35, -0.6),    # 3/4 from the front-left, above
    ("system_front", (-1250, -420, 880), (-330, 240, 440), 40, -0.3),  # T1's whole run: head, span, arm, rear, sheave
    ("system_rear", (-1250, 1000, 760), (-320, 320, 420), 35, 0.0),  # from behind-left: rails, sheave, arm, mounts
    ("head_close", (-640, -260, 760), (-330, 40, 600), 50, -0.6),    # the head, the lock, the split clip, the inlet
    ("rear_mounts", (-900, 120, 330), (-245, 470, 220), 30, 0.8),    # into the back: the stack sections, post, leg guides
    ("arm_hold", (-700, -300, 820), (-330, 120, 600), 35, -0.3),     # the dock lever: plunger, housing up and back, tab
    ("sheave_close", (-190, 170, 400), (-324, 459, 320), 45, 0.0),   # T1's spoked take-up wheel in its open-frame stack
    ("belt_sleeves", (-430, 250, 540), (-290, 465, 440), 45, 0.0),  # the leg guides' sleeves past the XY belts
    ("hold_top", (-560, 290, 560), (-345, 455, 658), 70, 0.3),       # its top end: housing stop, pulley, wire, arm's tab
    ("hold_dock", (-480, -260, 390), (-329, -85, 474), 70, 0.0),     # its bottom end: block, plunger on the head's hub
]


def views(exp):
    p = f"{exp}/scene.json"
    sc = json.load(open(p))
    sc["views"] = [{"name": n, "pos": list(pos), "look": list(look), "lens_mm": lens, "ev": ev} for n, pos, look, lens, ev in VIEWS]
    json.dump(sc, open(p, "w"))
    return [v[0] for v in VIEWS]


def main(argv):
    opt = {"--cut": -392.0, "--tool": 1}
    args = []
    while argv:
        a = argv.pop(0)
        if a in opt: opt[a] = type(opt[a])(argv.pop(0))
        else: args.append(a)
    if args[:1] == ["groups"] and len(args) == 3:
        g = groups(json.load(open(args[1])), opt["--cut"], opt["--tool"])
        json.dump(g, open(args[2], "w"))
        print(f"cutaway: X > {opt['--cut']:g}, T{opt['--tool']}: {len(g['clip'])} cut, {len(g['hide'])} left out")
        return 0
    if args[:1] == ["views"] and len(args) == 2:
        print("cutaway: views", views(args[1]))
        return 0
    print(__doc__ or "usage: see the header", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
