# lite-80 -> lite-81 (vt350#312): the bowden arms and the dancers, hardware first.
#
#   $APP freecadcmd $PWD/cad/passes/lite81_arms_dancers.py     dry run (never saves)
#   $APP $PWD/cad/passes/lite81_arms_dancers.py                GUI run: saves vt350-lite-81.FCStd if every check passes
#
# From the studies' own numbers (cad/data/bowden_arms_design.json, cad/data/bowden_arms_dancer.json, both on lite-80):
#   - five ARMS, one per tool, over their roof exits (X of each tool's exit), hinged on one 5 mm shaft under the rear
#     top 4040 (hinge Y 490, Z 640, the design "under the bar, arm 240"), each with its LOOP at the tip (raised: Y 251.01,
#     Z 662; lowered: Y 250, Z 640). All five are drawn raised (parked); the cam that lowers one isn't designed yet and
#     isn't modelled. Two printed hinge brackets hang the shaft from the 4040's underside.
#   - five DANCER SHEAVES: R 58.2 (the bundle's centreline R 53.6 + 4.6), 10 thick, axis along Y, in two stacks either
#     side of the rear-centre Z axis (T0 T1 at X -324.2, Y 446 / 459; T2 T3 T4 at X -167.0, Y 446 / 459 / 472), each at
#     its tool's parked height (dancer study, 41 g). A 625 bearing (5 x 16 x 5) in each hub on a 5 mm axle (owner,
#     2026-11-25: "less resistance").
#   - the LANE GUIDES (owner, 2026-11-25): per stack, vertical printed plates between and beside the sheaves, each with a
#     vertical slot the axle ends slide in, from below the lowest pulley height any studied weight or stiffness reaches
#     to the top of travel (Z 340); a tie across their tops above the highest sheave.
#   - the LEG GUIDES at Z 470 (the studies' Z_G): per stack and leg, a block with one rectangular hole per tool plane,
#     sized for the bundle (two tubes one above the other: 10.2 x 5.1), holding the legs where the channels begin.
#   - the BUNDLES on the studied route (dancer shapes at 41 g, every head docked as in the model's pose): from each old
#     run's crossing of the ceiling (Z 679) down the exit leg, round the sheave's groove (the cable inner, at the study's
#     R 51.05; the tube touching it outside), up the return leg, under the arm to its loop, the head span to the head.
#     The cable goes into its O2S lock (Z 560.11); the tube leaves the bundle 60 mm above the lock and runs to the
#     Orbiter's inlet (that branch is a PLACEHOLDER: how the PTFE gets from the bundle to the inlet isn't designed).
#     The old runs keep their pieces above the roof, outside the back panel and inside the head; the 20 zip ties of the
#     old route are removed. Each arm has the SLOT its own exit span passes down through (the study: "pulled down
#     through a slot in the arm"); T4's is a hook, open on +X, where the chamber camera's housing sits 0.2 mm away.
# Not in this pass: the cam and its stepper, the mounts of the guides and plates to the frame, the active (lowered)
# arm's route (every head is docked in the model's pose).
#
# Checks: every new part from the studies' numbers (positions, sizes); sheaves in their planes, slots cover the travel;
# axle ends inside their plates' slots, sheaves clear of the plates; each route ends at its head's lock; COLLISIONS:
# nothing new overlaps lite-80 (the old runs' and ties' overlaps are the baseline: none), and the new parts and runs
# don't overlap each other (a tool's own tube and cable may touch: they are bundled).
import FreeCAD, Part, os, sys, math, json, re, time
_REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
sys.path[:0] = [os.path.join(_REPO, "platform/freecad"), os.path.join(_REPO, "platform/render"),
                os.path.join(_REPO, "cad/passes")]
os.environ["LITE78_AS_LIB"] = "1"
import litelib, linkgeo
import lite78_front17 as l78
from litelib import MODELS
V = FreeCAD.Vector
SRC, DST = f"{MODELS}/vt350-lite-80.FCStd", f"{MODELS}/vt350-lite-81.FCStd"
# LITE81_PREVIEW=<path>: a GUI run saves there instead, a preview for renders (not a model version; the same checks
# must pass first). Used for the owner's cutaway before lite-80 is approved (2026-11-26).
DST = os.environ.get("LITE81_PREVIEW") or DST
DATA = os.path.join(_REPO, "cad", "data")
DESIGN = json.load(open(os.path.join(DATA, "bowden_arms_design.json")))["design"]
DANCER = json.load(open(os.path.join(DATA, "bowden_arms_dancer.json")))
W_PICK = 0.4                                  # N: the middle of the studied weights (41 g)
ARM_X = [-409.7, -324.54, -248.42, -156.42, -80.3]   # each tool's roof exit X (dancer shapes, the parked route's start)
ARM_W, ARM_T = 8.0, 8.0                        # the arm's section: across X, and across its length in YZ
LOOP_R, LOOP_r = 9.0, 2.5                     # the loop at the tip: a ring round the bundle's line (6.5 free inside)
ARM_LIFT = 7.0                                # the bar rides this far above the bundle's line: the return span
                                              # arrives under the arm, along its line, only at the loop
ARM_ROOT = 140.0                              # the bar's first 140 mm (to Y ~350) sit just under the hinge line:
                                              # each exit span crosses over it ~55 mm from the hinge (dry run 7)
ROOT_DROP = 2.0
SLOT_FRAME, SLOT_R = 21.0, 6.2                # the slot's frame width (X) and its clearance radius round the span
SLOT_HOOK = {4: -1}                           # T4: the frame only on -X, the slot open on +X (a hook): the chamber
                                              # camera's housing is 0.2 mm off the arm's +X face (dry run 8)
SHAFT_R = 2.5                                 # the hinge shaft, 5 mm
SHAFT_X = (-432.0, -58.0)
BRACKET_X = ((-432.0, -424.0), (-66.0, -58.0))
BAR_UNDERSIDE = 650.0                         # the rear top 4040 (Y 480..520, Z 650..690)
SHEAVE_R, SHEAVE_T = DANCER["RP"] + 4.6, 8.0   # 8 thick (was 10): room for grooved plates in the 13 mm pitch
GROOVE_W, GROOVE_IN = 5.6, DANCER["RP"] - 2.55 - 2.55 - 0.6   # groove bottom: the cable (inner, centre RP - 2.55) + 0.6
BEARING = (8.0, 2.5, 5.0)                     # 625: OD/2, ID/2, width
PITCH = 13.0                                  # the dancer study's plane pitch (Y 446 / 459 / 472)
GROOVE_D, PLATE_GAP = 1.6, 0.4                # the plates' blind axle grooves: depth; sheave face to plate face
# The axle: a 5 mm steel dowel pin pressed into the 625's inner race (owner 2026-11-26: "a steel dowel for the axle ...
# friction fit"). Its ends slide in BLIND grooves, one per axle end: dry run 10's shared through-slots let two
# neighbours' axle ends meet as one sheave passed the other (owner, from the cutaway).
AXLE_L = SHEAVE_T + 2 * (PLATE_GAP + GROOVE_D) - 0.2   # 11.8: 0.1 short of each groove's bottom
PLATE_T, PLATE_W = PITCH - SHEAVE_T - 2 * PLATE_GAP, 24.0   # the plates: 4.2 thick (Y), 24 wide (X); web 1.0 between grooves
SLOT_W = 5.4
Z_TOP, Z_G = DANCER["z_top"], 470.0
# The RAILS (owner 2026-11-26: "have the axle travel in a slotted rail held in place between the bottom and gantry
# extrusions"): every plate runs full height, from a FOOT on the backbone (it sits on the bottom rear 4040) to a CAP
# under the gantry's rear 2020 (X -415..-75, Y 480..500, Z 430..450). The two outer plates are the rails: flanged
# outward (a U) for stiffness. The leg guides at Z 470 sit on a BRIDGE between them, screwed to the 2020's front face.
FOOT_Z, CAP_Z = (-2.0, 8.0), (418.0, 430.0)   # the backbone's top is Z -2; the gantry 2020's underside Z 430
BELT_Y, BELT_Z0 = 466.5, 427.0                # the lower XY belt's rear run (Y 463.8..465.5, from Z 428.75: dry run 10):
                                              # the cap stays under Z BELT_Z0 in front of Y BELT_Y, full height behind it
FLANGE = (3.0, 8.0)                           # rail flange: X thickness, Y depth (outward)
GANTRY_2020 = dict(y=(480.0, 500.0), z=(430.0, 450.0), x=(-415.0, -75.0))
M5 = 2.75                                     # M5 clearance hole radius
LEG_BLOCK = (20.0, 6.0)                       # leg guide block: X width, Z height; holes 12 x 6.5
HOLE = (12.0, 6.5)
# PRINTING (owner 2026-11-26: "these lanes might be hard to print in one piece ... how to plate them for the neptune"):
# a plate is 410 tall; the Neptune 4 Pro takes 220 x 220 (cad/data/print-profile.json) and ~250 in Z. So each stack is
# one COMB printed standing in three SECTIONS: its plates widened in their own planes (no sheave runs there) out to a
# POST beyond the sheaves, the post tying them together; split at SPLIT_Z, outside the axle grooves (Z ~162..344), so
# no seam crosses a groove. Two M4 tie rods down the post clamp the sections from the foot to the cap.
# The post goes on one side only: the bed's rear kinematic mount and lead screw sweep X -263..-230 (Y 357..499) through
# all of Z, between the stacks (X -324.2 can't reach past -266, X -167 not past -225).
POST_SIDE = {-324.2: -1, -167.0: 1}
POST_DX, POST_W = 66.0, 10.0                  # post centre from the stack's X; width in X (2.8 clear of a sheave or leg)
ROD_R, ROD_HOLE, ROD_INSET, NUT_POCKET = 2.0, 2.2, 6.0, (4.4, 4.0)   # M4 rod; its hole; from the post's Y ends; nut
SPLIT_Z = (155.0, 350.0)
PRINT_XY, PRINT_Z = 220.0, 250.0              # the Neptune's bed with margin; its Z with margin
TOL = 1e-3


def stacks():
    """{cx: [(tool, plane y)]} from the dancer study's pulley table (tool keys are 1-based there)."""
    out = {}
    for k, (cx, y) in sorted(DANCER["pulley"].items(), key=lambda kv: int(kv[0])):
        out.setdefault(cx, []).append((int(k) - 1, y))
    return out


# The pulley's centre Z with every head docked (the model's pose), at W_PICK: cad/data/bowden_arms_dancer_shapes.json
# "T<n>|0.4" zc_parked (2.2 MB, on the arms branch feat/312-arms-lite80; the dancer study on lite-80).
PARKED_Z = {0: 284.99, 1: 320.53, 2: 340.0, 3: 317.13, 4: 285.24}   # after the locks rode +10 (PR #326)


def parked_z(tool):
    return PARKED_Z[tool]


def lowest(tools):
    """Lowest pulley centre any studied weight or stiffness reaches, over these tools."""
    return min(r["pulley_low"] for r in DANCER["rows"] if r["tool"] in tools)


def arm(x, hinge, loop):
    """The bar runs ARM_LIFT above the hinge-to-loop line (its root, under the 4040, on the line), the loop ring on
    the line at the tip, a boss on the hinge shaft."""
    hy, hz = hinge; ly, lz = loop
    dy, dz = ly - hy, lz - hz
    L = math.hypot(dy, dz)
    ang = math.degrees(math.atan2(dz, dy))     # (0,1,0) turned about +X by ang points along the arm
    up = ARM_LIFT + ARM_T / 2                  # the bar's centre, above the line in the WORLD
    # the turn about +X by ang takes local +Z to (0, -sin ang, cos ang): with the arm pointing forward (ang ~175 deg)
    # local +Z points down, so build the bar on local -Z (lite-81 dry run 5 found it under the line, in the bundle)
    sg = 1.0 if math.cos(math.radians(ang)) >= 0 else -1.0
    root = Part.makeBox(ARM_W, ARM_ROOT, ARM_T, V(-ARM_W / 2, 0, -sg * ROOT_DROP - ARM_T / 2))
    bar = Part.makeBox(ARM_W, L - ARM_ROOT + 5.0, ARM_T, V(-ARM_W / 2, ARM_ROOT - 5.0, sg * up - ARM_T / 2))
    wz = (-ROOT_DROP - ARM_T / 2, up + ARM_T / 2)
    web = Part.makeBox(ARM_W, 20.0, wz[1] - wz[0], V(-ARM_W / 2, ARM_ROOT - 10.0, wz[0] if sg > 0 else -wz[1]))
    boss = Part.makeCylinder(7.0, ARM_W, V(-ARM_W / 2, 0, 0), V(1, 0, 0))
    ring = Part.makeTorus(LOOP_R, LOOP_r, V(0, L, 0), V(0, 1, 0))
    tz = (LOOP_R - 0.5, up)
    tip = Part.makeBox(ARM_W, 2 * LOOP_r, tz[1] - tz[0], V(-ARM_W / 2, L - LOOP_r, tz[0] if sg > 0 else -tz[1]))
    s = root.fuse([bar, web, boss, ring, tip]).removeSplitter()
    s = s.cut(Part.makeCylinder(SHAFT_R + 0.1, ARM_W + 2, V(-ARM_W / 2 - 1, 0, 0), V(1, 0, 0)))
    s.rotate(V(0, 0, 0), V(1, 0, 0), ang)
    s.translate(V(x, hy, hz))
    return s, L


def sheave(cx, y, zc):
    disc = Part.makeCylinder(SHEAVE_R, SHEAVE_T, V(cx, y - SHEAVE_T / 2, zc), V(0, 1, 0))
    groove = Part.makeCylinder(SHEAVE_R + 1, GROOVE_W, V(cx, y - GROOVE_W / 2, zc), V(0, 1, 0)).cut(
        Part.makeCylinder(GROOVE_IN, GROOVE_W, V(cx, y - GROOVE_W / 2, zc), V(0, 1, 0)))
    hub = Part.makeCylinder(BEARING[0], SHEAVE_T + 2, V(cx, y - SHEAVE_T / 2 - 1, zc), V(0, 1, 0))
    return disc.cut(groove).cut(hub)


def bearing(cx, y, zc):
    o, i, w = BEARING
    return Part.makeCylinder(o, w, V(cx, y - w / 2, zc), V(0, 1, 0)).cut(
        Part.makeCylinder(i, w, V(cx, y - w / 2, zc), V(0, 1, 0)))


def axle(cx, y, zc):
    return Part.makeCylinder(BEARING[1], AXLE_L, V(cx, y - AXLE_L / 2, zc), V(0, 1, 0))


def plate(cx, yc, slot, side=0, faces=(-1, 1), xspan=None):
    """A full-height plate, foot to cap, with a blind axle groove GROOVE_D deep in each face that has a sheave
    (faces: -1 = its -Y face, +1 = its +Y face); side -1 / +1: an outer rail, flanged outward (toward -Y / +Y)."""
    z0, z1 = FOOT_Z[1], CAP_Z[0]
    xa, xb = xspan or (cx - PLATE_W / 2, cx + PLATE_W / 2)
    p = Part.makeBox(xb - xa, PLATE_T, z1 - z0, V(xa, yc - PLATE_T / 2, z0))
    if side:
        y0 = yc + PLATE_T / 2 if side > 0 else yc - PLATE_T / 2 - FLANGE[1]
        for x0 in (cx - PLATE_W / 2, cx + PLATE_W / 2 - FLANGE[0]):
            p = p.fuse(Part.makeBox(FLANGE[0], FLANGE[1], z1 - z0, V(x0, y0, z0)))
        p = p.removeSplitter()
    for f in faces:
        y0 = yc - PLATE_T / 2 - 1.0 if f < 0 else yc + PLATE_T / 2 - GROOVE_D
        p = p.cut(Part.makeBox(SLOT_W, GROOVE_D + 1.0, slot[1] - slot[0], V(cx - SLOT_W / 2, y0, slot[0])))
    return p


def stack_body(cx, ycs, slot):
    """One stack's plates (widened to the post) and its post, full height, with the tie-rod holes and nut pockets;
    -> (body, rods, post X)."""
    side = POST_SIDE[round(cx, 1)]
    px = cx + side * POST_DX
    xa, xb = sorted((cx - side * PLATE_W / 2, px + side * POST_W / 2))
    body = None
    for j, yc in enumerate(ycs):
        sd = -1 if j == 0 else (1 if j == len(ycs) - 1 else 0)
        faces = tuple(f for f in (-1, 1) if not (f < 0 and j == 0) and not (f > 0 and j == len(ycs) - 1))
        pl = plate(cx, yc, slot, sd, faces, (xa, xb))
        body = pl if body is None else body.fuse(pl)
    y0, y1 = ycs[0] - PLATE_T / 2, ycs[-1] + PLATE_T / 2
    z0, z1 = FOOT_Z[1], CAP_Z[0]
    body = body.fuse(Part.makeBox(POST_W, y1 - y0, z1 - z0, V(px - POST_W / 2, y0, z0))).removeSplitter()
    rods = []
    for y in (y0 + ROD_INSET, y1 - ROD_INSET):
        body = body.cut(Part.makeCylinder(ROD_HOLE, z1 - z0 + 2, V(px, y, z0 - 1)))
        for zb in (z0 - 1, z1 - NUT_POCKET[1]):
            body = body.cut(Part.makeCylinder(NUT_POCKET[0], NUT_POCKET[1] + 1, V(px, y, zb)))
        rods.append(Part.makeCylinder(ROD_R, z1 - z0 - 2 * NUT_POCKET[1] + 6, V(px, y, z0 + NUT_POCKET[1] - 3)))
    return body, rods, px


def sections(body):
    zs = [FOOT_Z[1], *SPLIT_Z, CAP_Z[0]]
    return [body.common(Part.makeBox(4000, 4000, b - a, V(-2000, -2000, a))).removeSplitter() for a, b in zip(zs, zs[1:])]


def rail_ends(cx, ycs):
    """The foot (on the backbone, two M5 through it) and the cap (one M5 up into the gantry 2020's bottom slot)."""
    yf, yb = ycs[0] - PLATE_T / 2 - FLANGE[1], ycs[-1] + PLATE_T / 2 + FLANGE[1]
    foot = Part.makeBox(PLATE_W, yb - yf, FOOT_Z[1] - FOOT_Z[0], V(cx - PLATE_W / 2, yf, FOOT_Z[0]))
    for y in (yf + 4.0, yb - 4.0):
        foot = foot.cut(Part.makeCylinder(M5, 20, V(cx, y, FOOT_Z[0] - 5)))
    ycap = sum(GANTRY_2020["y"]) / 2
    cap = Part.makeBox(PLATE_W, GANTRY_2020["y"][1] - yf, BELT_Z0 - CAP_Z[0], V(cx - PLATE_W / 2, yf, CAP_Z[0])).fuse(
        Part.makeBox(PLATE_W, GANTRY_2020["y"][1] - BELT_Y, CAP_Z[1] - CAP_Z[0], V(cx - PLATE_W / 2, BELT_Y, CAP_Z[0]))
    ).removeSplitter()
    cap = cap.cut(Part.makeCylinder(M5, 20, V(cx, ycap, CAP_Z[0] - 5)))
    return foot, cap


def leg_bridge(cx, ys):
    """The bar between a stack's two leg guides, and the tab that screws it to the gantry 2020's front face."""
    rp = DANCER["RP"]
    y0, y1 = min(ys) - 6.5, GANTRY_2020["y"][0]
    bar = Part.makeBox(2 * (rp - LEG_BLOCK[0] / 2), y1 - y0, LEG_BLOCK[1],
                       V(cx - rp + LEG_BLOCK[0] / 2, y0, Z_G - LEG_BLOCK[1] / 2))
    tab = Part.makeBox(PLATE_W, 4.0, Z_G + LEG_BLOCK[1] / 2 - (CAP_Z[1] + 2.0), V(cx - PLATE_W / 2, y1 - 4.0, CAP_Z[1] + 2.0))
    tab = tab.cut(Part.makeCylinder(M5, 10, V(cx, y1 - 6, sum(GANTRY_2020["z"]) / 2), V(0, 1, 0)))
    return bar.fuse(tab).removeSplitter()


def leg_block(x, ys):
    y0, y1 = min(ys) - 6.5, max(ys) + 6.5
    b = Part.makeBox(LEG_BLOCK[0], y1 - y0, LEG_BLOCK[1], V(x - LEG_BLOCK[0] / 2, y0, Z_G - LEG_BLOCK[1] / 2))
    for y in ys:
        b = b.cut(Part.makeBox(HOLE[0], HOLE[1], LEG_BLOCK[1] + 2, V(x - HOLE[0] / 2, y - HOLE[1] / 2, Z_G - LEG_BLOCK[1] / 2 - 1)))
    return b


# ---- the bundles (each tool's PTFE tube + O2S cable) on the studied route
SHAPES = json.load(open(os.path.join(DATA, "bowden_arms_dancer_shapes.json")))
TUBE_R, CABLE_R = 4.12 / 2, 5.1 / 2
CABLE_OFF, TUBE_OFF = -CABLE_R, TUBE_R + 0.05  # across the bundle (n: the sheave's outward radial): cable inner, centred
                                               # RP - 2.55 on the sheave (the study's inner tube), tube touching it
CEIL = 679.0                                   # the roof exit's lower end: the studied route starts here
LOCK_TOP = 560.11                              # lite-80's O2S locks' top: the cable enters straight down
INLET_Y = -50.14                               # the PTFE's entry into the Orbiter at Z LOCK_TOP (probe of lite-80)
BRANCH_R = 51.0                                # the PTFE's branch to the Orbiter inlet: no bend under R 51 (the cable's
                                               # limit, lite-40). The inlet is 41 mm in front of the lock, so the tube
                                               # leaves the bundle ~120 mm behind the lock (Z ~635), not just above it:
                                               # 20 mm above the lock gives R 9, 60 mm R 44 (owner 2026-11-26: "use your
                                               # recommendation")
CLIP_L, CLIP_WALL, CLIP_GAP, CLIP_BACK = 12.0, 1.6, 0.4, 14.0   # the printed clip at the split: length, wall, bore
                                               # clearance, its centre this far back along the bundle from the split
TUBES = ["Bowden Left", "Bowden slot 2", "Bowden slot 3", "Bowden slot 4", "Bowden Right"]
CABLES = [f"O2S USB cable slot {i} " for i in range(1, 6)]
TIES = [f"Zip tie, black (2.5 mm) slot {i} at " for i in range(1, 6)]


# ---- the ARM HOLD (owner 2026-11-26: "I do not see what is keeping the arm in its docked (not active head) position"):
# the dock lever (vt350#312, owner 2026-11-25: "a mechanical one set by which head is in use"; study
# cad/studies/dock_lever.py, moved to lite-80's docks). Per tool: a PLUNGER in a block under the front dock bar, which
# the parked head's hub housing pushes in; a sheathed pull cable from the block up the front, under the front top
# 2040, back along the ceiling in its own lane (LANE_DX from the arm) to a housing stop and a small pulley over a TAB
# on the arm, TAB_D in front of the hinge. Parked head: the wire holds the arm up. Head away: the arm drops.
LEVER = json.load(open(os.path.join(DATA, "dock_lever.json")))
LP = LEVER["params"]
ROD_TIP_GAP = 0.3                             # the plunger's tip, modelled just off the parked head's face
PLUNGER_R = 3.0
LEVER_PULLEY = (6.0 - 0.6 - 0.3, 5.0)          # the ceiling pulley: the wire's centre runs at R 6, so the rim is R 5.4, less 0.3 for the groove the wire sits in (smoothing pulls the wire ~0.2 in); width
TAB_W, TAB_H = 8.0, 10.0                      # the arm's tab: Y; Z (down from the wire's end)


def lever(t):
    """-> [(key, label, shape, role)] tool t's plunger, block, housing, wire, pulley and stop, and the tab (fused into
    the arm by build())."""
    r = LEVER["routes"][str(t + 1)]
    xp, pz = r["plunger"]
    bar_front, bar_back, bar_zlo = LP["BAR"]
    bx, by, bz = LP["BLOCK"]
    out = []
    block = Part.makeBox(bx, by, bz, V(xp - bx / 2, bar_back - by, bar_zlo - bz))
    block = block.cut(Part.makeCylinder(PLUNGER_R + 0.3, by + 2, V(xp, bar_back - by - 1, pz), V(0, 1, 0)))
    out.append((f"lever_block{t}", f"Arm hold T{t}: plunger block under the dock bar (printed; holds the plunger, its "
                f"spring and the housing's lower end) [lite-81, #312]", block, "printed"))
    y_tip = LP["HEAD_FRONT"] - ROD_TIP_GAP
    rod = Part.makeCylinder(PLUNGER_R, y_tip - (bar_back - by + 2.0), V(xp, bar_back - by + 2.0, pz), V(0, 1, 0))
    out.append((f"lever_plunger{t}", f"Arm hold T{t}: plunger, 6 mm steel, ball tip on the parked head's hub housing "
                f"(spring inside the block) [lite-81, #312]", rod, "brushed_steel"))
    H = [V(*q) for q in r["housing"]]
    hous, hl, how = sweep(H[1:], LP["HOUSING_R"], frenet_off=True)
    out.append((f"lever_housing{t}", f"Arm hold T{t}: cable housing, 5 mm PTFE-lined, ~{hl:.0f} mm (block -> ceiling "
                f"lane X {xp - LP['P_DX'] + LP['LANE_DX']:.1f}) [lite-81, #312]", hous, "rubber"))
    wire, wl, _ = sweep([V(*q) for q in r["wire_up"]], LP["WIRE_R"])
    out.append((f"lever_wire{t}", f"Arm hold T{t}: inner wire 1.2 mm, ceiling pulley to the arm's tab (arm up) "
                f"[lite-81, #312]", wire, "brushed_steel"))
    w0 = r["wire_up"][0]; xl = w0[0]
    pc = V(xl, w0[1] + 14.0, LP["Z_LANE"] - 6.0)
    pul = Part.makeCylinder(LEVER_PULLEY[0], LEVER_PULLEY[1], pc - V(LEVER_PULLEY[1] / 2, 0, 0), V(1, 0, 0))
    out.append((f"lever_pulley{t}", f"Arm hold T{t}: ceiling pulley (printed, on a 3 mm pin) [lite-81, #312]", pul, "printed"))
    end = r["wire_up"][-1]
    tab = Part.makeBox(abs(xl - ARM_X[t]) + TAB_W / 2, TAB_W, TAB_H,
                       V(min(xl, ARM_X[t]) - (TAB_W / 2 if xl < ARM_X[t] else 0), end[1] - TAB_W / 2, end[2] - LP['WIRE_R'] - TAB_H))
    return out, tab


def unit(v):
    return v * (1.0 / v.Length)


def centreline(t):
    """The bundle's parked centreline for tool t (W_PICK): roof exit -> exit leg -> round the sheave's bottom -> return
    leg -> under the raised arm to its loop -> the head span to the lock. -> ([V], index of the sheave's bottom)."""
    sh = SHAPES[f"T{t}|{W_PICK}"]
    cx, y = DANCER["pulley"][str(t + 1)]
    zc = PARKED_Z[t]
    key = min(sh["rear_up"], key=lambda k: abs(float(k) - zc))
    ex, rt = sh["rear_up"][key]
    ex = [list(p) for p in ex]; rt = [list(p) for p in rt]
    ex[-1][2] = zc; rt[0][2] = zc                  # the legs are vertical below Z_G: end them at this pulley height
    rp = DANCER["RP"]
    arc = [[cx - rp * math.cos(a), y, zc - rp * math.sin(a)] for a in [math.pi * i / 24 for i in range(1, 24)]]
    pts = ex + arc + rt[:-1] + sh["parked"]
    out = []
    for q in pts:
        v = V(*q)
        if not out or (v - out[-1]).Length > 0.5:
            out.append(v)
    mid = min(range(len(out)), key=lambda i: (out[i] - V(cx, y, zc - rp)).Length)
    return out, mid


def frames(pts, mid):
    """Unit normals along pts, carried along the path from the sheave's bottom (where n is the outward radial, -Z)
    by projection onto each tangent's normal plane (a parallel transport, good to the point spacing)."""
    tan = [unit(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]) for i in range(len(pts))]
    n = [None] * len(pts)
    n[mid] = unit(V(0, 0, -1) - tan[mid] * V(0, 0, -1).dot(tan[mid]))
    for rng in (range(mid + 1, len(pts)), range(mid - 1, -1, -1)):
        prev = mid
        for i in rng:
            v = n[prev] - tan[i] * n[prev].dot(tan[i])
            n[i] = unit(v); prev = i
    return tan, n


def chaikin(pts, n=2):
    """Corner-cutting smoothing; keeps both end points."""
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        out.append(pts[-1]); pts = out
    return pts


def resample(pts, step=6.0):
    out = [pts[0]]; acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = (b - a).Length
        if L < 1e-9: continue
        d = step - acc
        while d <= L:
            out.append(a + (b - a) * (d / L)); d += step
        acc = (acc + L) % step
    if (out[-1] - pts[-1]).Length > 0.5: out.append(pts[-1])
    return out


SPINES = {}                                   # a pipe's box key -> (its spine points, r): see near_spine()
SPINE_PAD = 0.2 + 3.0 + 0.5                   # the spline's tolerance + half the 6 mm sample step + a margin


def _bkey(s):
    b = s.BoundBox
    return tuple(round(v, 2) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))


def near_spine(s, box):
    """False only if solid s is a pipe from sweep() whose every spine point is farther than r + SPINE_PAD outside box,
    so the pipe can't reach it. A 695 mm diagonal housing's bounding box meets thousands of parts it never comes
    near, and one boolean each took hours (dry run 14, 2026-11-26)."""
    sp = SPINES.get(_bkey(s))
    if sp is None: return True
    pts, r = sp; m = r + SPINE_PAD
    x0, y0, z0, x1, y1, z1 = box.XMin - m, box.YMin - m, box.ZMin - m, box.XMax + m, box.YMax + m, box.ZMax + m
    return any(x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1 for x, y, z in pts)


def sweep(pts, r, t0=None, t1=None, frenet_off=False):
    """A round run of radius r along pts: a pipe along the smoothed points' spline; if OCC can't make that solid,
    a chain of cylinders and spheres along them. -> (shape, length, how)"""
    sm = resample(chaikin(pts))
    length = sum((b - a).Length for a, b in zip(sm[:-1], sm[1:]))
    spine = ([(q.x, q.y, q.z) for q in sm], r)
    for frenet in ((True, False) if frenet_off else (True,)):   # Frenet fails (MakeSolid) on the dock lever's long
        try:   # twisting housing; the plain mode makes it whole. ONLY there: on the runs a no-Frenet pipe overlapped the
               # clips, sheave grooves and arm loops sized round the chain (dry run 16, 8 overlaps; LESSONS.md, 2026-11-26)
            c = Part.BSplineCurve(); c.approximate(Points=sm, DegMin=3, DegMax=3, Tolerance=0.2)
            path = Part.Wire([c.toShape()])
            e0 = path.Edges[0]
            prof = Part.Wire([Part.makeCircle(r, e0.valueAt(e0.FirstParameter), e0.tangentAt(e0.FirstParameter))])
            s = path.makePipeShell([prof], True, frenet)   # never Wire.makePipe: it segfaults on these (LESSONS.md)
            if s.isValid() and s.Volume > 0.9 * math.pi * r * r * length:
                SPINES[_bkey(s)] = spine
                return s, length, "pipe" if frenet else "pipe (no Frenet)"
        except Exception:
            # lint-allow-silent: the next mode, then the chain below, is the fallback; the caller logs which ("how")
            pass
    segs = [Part.makeCylinder(r, (b - a).Length, a, unit(b - a)) for a, b in zip(sm[:-1], sm[1:]) if (b - a).Length > 1e-6]
    balls = [Part.makeSphere(r, q) for q in sm[1:-1]]
    return Part.makeCompound(segs + balls), length, "chain"


def branch(p0, d0, inlet, inlet_dir):
    """The gentlest cubic from p0 (leaving along d0) into the inlet (arriving along inlet_dir), never below the inlet.
    -> (min radius, [V] 40 points after p0) or (0, None)."""
    import numpy as np
    P0, D0 = np.array(p0), np.array(d0); P3, D3 = np.array(inlet), np.array(inlet_dir)
    u = np.linspace(0, 1, 160)[:, None]
    best = (0.0, None)
    for a in np.arange(10.0, 210.0, 10.0):
        for b in np.arange(10.0, 210.0, 10.0):
            P1, P2 = P0 + D0 * a, P3 - D3 * b
            B = (1 - u) ** 3 * P0 + 3 * (1 - u) ** 2 * u * P1 + 3 * (1 - u) * u ** 2 * P2 + u ** 3 * P3
            if B[:, 2].min() < P3[2] - 0.5: continue
            d1 = 3 * ((1 - u) ** 2 * (P1 - P0) + 2 * (1 - u) * u * (P2 - P1) + u ** 2 * (P3 - P2))
            d2 = 6 * ((1 - u) * (P2 - 2 * P1 + P0) + u * (P3 - 2 * P2 + P1))
            R = 1.0 / (np.linalg.norm(np.cross(d1, d2), axis=1) / np.linalg.norm(d1, axis=1) ** 3).max()
            if R > best[0]: best = (R, [V(*q) for q in B[4::4]])
    return best


def clip_at(ax, runs):
    """The split clip: one straight body round both runs (two cylinders fused, walls CLIP_WALL), then BOTH bores cut
    from it (CLIP_GAP over each run). Dry runs 10-11: each sleeve bored only for its own run left its wall inside the
    neighbour run (the tube and cable touch), 80-140 mm3; sleeves built along the curved runs failed in OCC."""
    body = bore = None
    for c, r in runs:
        o = Part.makeCylinder(r + CLIP_GAP + CLIP_WALL, CLIP_L, c - ax * (CLIP_L / 2), ax)
        b = Part.makeCylinder(r + CLIP_GAP, CLIP_L + 2.0, c - ax * (CLIP_L / 2 + 1.0), ax)
        body = o if body is None else body.fuse(o)
        bore = b if bore is None else bore.fuse(b)
    return body.cut(bore).removeSplitter()


def bundle(t, tube_top, cable_top, inlet, inlet_dir):
    """New in-chamber tube and cable for tool t: from the old runs' crossings of the ceiling (tube_top, cable_top) along
    the studied route; the cable into its lock; the tube leaves the bundle at the split nearest the head whose branch
    to the Orbiter inlet bends no tighter than BRANCH_R, with a printed clip holding the pair just behind the split.
    -> (cable, tube, clip, info)"""
    pts, mid = centreline(t)
    tan, n = frames(pts, mid)
    lock = pts[-1]
    cab = [cable_top] + [p + n[i] * CABLE_OFF for i, p in enumerate(pts)][2:-3] + [lock + V(0, 0, 8), lock]
    toff = [p + n[i] * TUBE_OFF for i, p in enumerate(pts)]
    split, R, tail = None, 0.0, None
    for i in range(len(pts) - 3, mid, -1):           # from the head back: the first split that bends gently enough
        if pts[i].z < lock.z + 15.0: continue
        R, tail = branch(toff[i], tan[i], inlet, inlet_dir)
        if R >= BRANCH_R: split = i; break
    if split is None: return None, None, None, dict(n_pts=len(pts))
    tub = [tube_top] + toff[2:split + 1] + tail
    acc, j = 0.0, split                              # the clip's centre: CLIP_BACK back along the bundle from the split
    while j > mid and acc < CLIP_BACK: acc += (pts[j] - pts[j - 1]).Length; j -= 1
    c, lc, hc = sweep(cab, CABLE_R)
    t_, lt, ht = sweep(tub, TUBE_R)
    clip = clip_at(tan[j], [(toff[j], TUBE_R), (pts[j] + n[j] * CABLE_OFF, CABLE_R)])
    return c, t_, clip, dict(split_z=round(pts[split].z, 1), split_y=round(pts[split].y, 1), branch_r=round(R, 1),
                             clip_at=tuple(round(x, 1) for x in pts[j]), n_pts=len(pts), cable_len=round(lc),
                             tube_len=round(lt), how=(hc, ht))


def slot_arm(s, t, x, hinge, loop):
    """The slot the tool's exit span passes down through (dancer study: "pulled down through a slot in the arm"):
    where the span comes nearest the arm's line, the arm widens to a frame SLOT_FRAME wide, and the span's path
    (radius SLOT_R: the bundle's 5.1 from its centreline + clearance) is cut out of it."""
    pts, mid = centreline(t)
    hy, hz = hinge; ly, lz = loop
    zline = lambda y: hz + (lz - hz) * (hy - y) / (hy - ly)
    ex = [q for q in pts[:mid] if q.z > zline(q.y) - 40 and q.y > ly + 20]
    c = min(ex, key=lambda q: abs(q.z - zline(q.y)))
    zc = zline(c.y)
    fx = (x - SLOT_FRAME / 2, x + SLOT_FRAME / 2)
    if SLOT_HOOK.get(t) == -1: fx = (x - SLOT_FRAME / 2, x + ARM_W / 2)
    if SLOT_HOOK.get(t) == +1: fx = (x - ARM_W / 2, x + SLOT_FRAME / 2)
    frame = litelib.box(fx[0], fx[1], c.y - 14.0, c.y + 14.0, zc - ROOT_DROP - ARM_T / 2 - 1.5,
                        zc - ROOT_DROP + ARM_T / 2 + 1.5)
    sm = resample(chaikin(ex), 3.0)
    clear = Part.makeCompound([Part.makeCylinder(SLOT_R, (b - a).Length, a, unit(b - a)) for a, b in zip(sm[:-1], sm[1:])]
                              + [Part.makeSphere(SLOT_R, q) for q in sm[1:-1]])
    out = s.fuse(frame).removeSplitter()
    for so in clear.Solids:
        if so.BoundBox.intersect(out.BoundBox):
            out = out.cut(so)
    return out, (round(c.x, 1), round(c.y, 1), round(c.z, 1))


def build():
    """-> [(key, label, shape, role)] every new part, in global coordinates, plus the numbers the checks use."""
    parts, info = [], {"sheaves": {}, "plates": {}, "slots": {}}
    hy, hz = DESIGN["hinge"]
    for t, x in enumerate(ARM_X):
        s, L = arm(x, (hy, hz), DESIGN["loop_up"])
        s, cross = slot_arm(s, t, x, (hy, hz), DESIGN["loop_up"])
        lev, tab = lever(t)
        s = s.fuse(tab).removeSplitter()
        info.setdefault("lever", []).extend(lev)
        info.setdefault("slot_at", []).append(cross)
        parts.append((f"arm{t}", f"Bowden arm T{t} (printed, raised; loop at the tip) [lite-81, #312]", s, "printed"))
        info.setdefault("arm_len", []).append(round(L, 2))
    parts.append(("shaft", "Bowden arm hinge shaft, 5 mm (steel) [lite-81, #312]",
                  Part.makeCylinder(SHAFT_R, SHAFT_X[1] - SHAFT_X[0], V(SHAFT_X[0], hy, hz), V(1, 0, 0)), "brushed_steel"))
    for i, (x0, x1) in enumerate(BRACKET_X):
        b = Part.makeBox(x1 - x0, 16.0, BAR_UNDERSIDE - (hz - 8.0), V(x0, hy - 8.0, hz - 8.0))
        b = b.cut(Part.makeCylinder(SHAFT_R + 0.1, x1 - x0 + 2, V(x0 - 1, hy, hz), V(1, 0, 0)))
        parts.append((f"bracket{i}", f"Bowden arm hinge bracket {'left' if i == 0 else 'right'} (printed; under the rear "
                      f"top 4040) [lite-81, #312]", b, "printed"))
    for cx, members in stacks().items():
        tools = [t for t, _ in members]
        ys = sorted(y for _, y in members)
        lo = lowest(tools)
        slot = (lo - SLOT_W / 2 - 5.0, Z_TOP + SLOT_W / 2 + 1.0)
        for t, y in members:
            zc = parked_z(t)
            info["sheaves"][t] = (cx, y, zc)
            parts.append((f"sheave{t}", f"Dancer sheave T{t} (printed, R {SHEAVE_R:.1f} x {SHEAVE_T:g}) [lite-81, #312]",
                          sheave(cx, y, zc), "printed"))
            parts.append((f"bearing{t}", f"Dancer bearing T{t}, 625-2RS (5 x 16 x 5) [lite-81, #312]", bearing(cx, y, zc), "bearing"))
            parts.append((f"axle{t}", f"Dancer axle T{t}, 5 mm steel dowel pin x {AXLE_L:g} (m6, pressed into the 625) [lite-81, #312]", axle(cx, y, zc), "brushed_steel"))
        ycs = [y - PITCH / 2 for y in ys] + [ys[-1] + PITCH / 2]
        info["plates"][cx] = ycs; info["slots"][cx] = slot
        body, rods, px = stack_body(cx, ycs, slot)
        foot, cap = rail_ends(cx, ycs)
        secs = sections(body)
        secs[0] = secs[0].fuse(foot).removeSplitter(); secs[-1] = secs[-1].fuse(cap).removeSplitter()
        zs = [FOOT_Z[0], *SPLIT_Z, CAP_Z[1]]
        info.setdefault("sections", {})[cx] = [(round(s_.BoundBox.XLength, 1), round(s_.BoundBox.YLength, 1),
                                                round(s_.BoundBox.ZLength, 1)) for s_ in secs]
        info.setdefault("post", {})[cx] = px
        what = ("with its foot (on the backbone, 2 x M5)", "the middle: the axle grooves", "with its cap (M5 up into the gantry's rear 2020)")
        for k, sec in enumerate(secs):
            parts.append((f"stack{cx:g}_{k}", f"Dancer stack X {cx:g}, section {k + 1}/3, {what[k]} (printed standing, "
                          f"Z {zs[k]:g}..{zs[k + 1]:g}; {len(ycs)} plates tied by a post at X {px:g}) [lite-81, #312]", sec, "printed"))
        for i, r in enumerate(rods):
            parts.append((f"rod{cx:g}_{i}", f"Dancer stack X {cx:g} tie rod {i + 1}, M4 threaded rod x "
                          f"{r.BoundBox.ZLength:.0f} (2 nuts in pockets) [lite-81, #312]", r, "brushed_steel"))
        parts.append((f"bridge{cx:g}", f"Dancer leg guide bridge X {cx:g} (printed; M5 into the gantry 2020's front face) "
                      f"[lite-81, #312]", leg_bridge(cx, ys), "printed"))
        for side, lx in (("exit", cx - DANCER["RP"]), ("return", cx + DANCER["RP"])):
            parts.append((f"leg{cx:g}{side}", f"Dancer leg guide X {lx:.1f}, {side} legs, Z {Z_G:g} (printed) [lite-81, #312]",
                          leg_block(lx, ys), "printed"))
    parts += info.pop("lever", [])
    return parts, info


def centre_at(shape, z, keep):
    """Centre of the shape's section at z, among the wires whose centre passes keep(V)."""
    cs = [w.BoundBox.Center for w in shape.slice(V(0, 0, 1), z)]
    cs = [c for c in cs if keep(c)]
    if len(cs) != 1:
        raise ValueError(f"section at Z {z}: {len(cs)} wires pass, want 1")
    return cs[0]


def keep_of(shape, zones):
    """The old run's pieces inside any of the boxes (x0, x1, y0, y1, z0, z1)."""
    pieces = [shape.common(litelib.box(*b)) for b in zones]
    pieces = [x for x in pieces if x.Volume > 1e-6]
    return pieces


FRAME_BAR = re.compile(r"^(2020|2040|4040)")              # the frame's extrusions (the e-box door's own frame is
FRAME_GROUP = "VT Frame"                                   # outside it: its own group, never aluminium since lite-56)
MATERIAL_TWIN = "4040 (1)"                                 # a frame bar that kept its material


def restore_frame_material(p, leaves):
    """lite-78's unlink() replaced five frame bars (App::Links) by solid copies with their label and colour but not their
    ShapeMaterial, so they turned 'Default': no frame colour in renders (owner 2026-11-26: "lower left and upper right
    look gray"), no density for the mass and FEM numbers. Copy the twin bar's material back; keep each bar's colour (a
    material can repaint it, lite12_materials.py)."""
    def in_frame(o):
        return FRAME_BAR.match(o.Label) and any(FRAME_GROUP in g.Label for g in o.InListRecursive)
    twin = [o for o in leaves if o.Label == MATERIAL_TWIN]
    p.check(len(twin) == 1 and "Alumin" in twin[0].ShapeMaterial.Name, f"the material twin {MATERIAL_TWIN!r} is aluminium")
    mat = twin[0].ShapeMaterial
    fixed = []
    for o in leaves:
        if not in_frame(o) or not hasattr(o, "ShapeMaterial") or "Alumin" in (o.ShapeMaterial.Name or ""): continue
        vo = getattr(o, "ViewObject", None)
        app = list(vo.ShapeAppearance) if vo is not None and hasattr(vo, "ShapeAppearance") else None
        o.ShapeMaterial = mat
        if app is not None: vo.ShapeAppearance = app
        fixed.append(o.Label)
    p.log(f"frame material restored on {len(fixed)} bars: {fixed}")
    left = [o.Label for o in leaves if in_frame(o) and hasattr(o, "ShapeMaterial") and "Alumin" not in (o.ShapeMaterial.Name or "")]
    p.check(not left, f"every frame extrusion is aluminium ({len(left)} not: {left})")
    return fixed


FLAT = 0.01                                   # mm: a common this thin is two faces touching; a gap this small is touching
SLOW = 20.0                                   # s: a pair slower than this is logged by name


def solid_overlaps(p, m, items, skip_of):
    """As lite78's overlaps (same result shape: ({(tag, leaf Label)}, pairs)), but solid by solid: a compound (a run
    of 2-5 pieces, a stack of sections) is split and each solid meets a leaf only where their boxes do. One boolean
    of a whole compound against a detailed part hung for 5 h in dry run 13 (2026-11-26) with no clue which pair; here
    each pair is named in <log>.progress before it starts, and any pair over SLOW s is logged. Pieces of one run may
    touch each other, so a sum can only over-count (a false hit, never a missed one)."""
    prog = p.log_path + ".progress"
    work, keys = [], set()                      # (tag, solid, leaf): only where the solid can reach the leaf
    for tag, s, n in items:
        solids = s.Solids or [s]
        for o in m.leaves:
            if o.Name in skip_of(n) or not m.boxes[o.Name].intersect(s.BoundBox): continue
            ob = m.boxes[o.Name]
            for x in solids:
                if x.BoundBox.intersect(ob) and near_spine(x, ob):
                    work.append((tag, x, o)); keys.add((tag, o.Name))
    vol, slow = {}, []
    t0 = time.time()
    for i, (tag, x, o) in enumerate(work):
        with open(prog, "w") as f:
            f.write(f"{i + 1}/{len(work)} {tag} vs {o.Label} ({time.time() - t0:.0f} s in)\n")
        t1 = time.time()
        b = m.shapes[o.Name]
        try:
            c = x.common(b); v = c.Volume
            cb = c.BoundBox
            if v > TOL and min(cb.XLength, cb.YLength, cb.ZLength) < FLAT: v = 0.0   # a face in contact, not volume
        except Exception as e:
            try:                                 # OCC can't intersect them (e.g. "Null shape"): are they apart?
                d = x.distToShape(b)[0]
            except Exception:
                # lint-allow-silent: no distance either; d = 0 counts it as an overlap below, logged
                d = 0.0
            p.log(f"  boolean failed: {tag} vs {o.Label}: {e}; {d:.2f} mm apart" + (" (clear)" if d > FLAT else ""))
            v = 0.0 if d > FLAT else float("inf")
        dt = time.time() - t1
        if dt > SLOW: slow.append((tag, o.Label, round(dt))); p.log(f"  slow pair ({dt:.0f} s): {tag} vs {o.Label}")
        vol[(tag, o.Label)] = vol.get((tag, o.Label), 0.0) + v
    p.log(f"  {len(keys)} part pairs, {len(work)} solid booleans in {time.time() - t0:.0f} s; {len(slow)} over {SLOW:g} s")
    return {k for k, v in vol.items() if v > TOL}, len(keys)


def main(p):
    m = p.open(SRC); doc = m.doc
    parts, info = build()
    p.log(f"{len(parts)} new parts; arms {info['arm_len']} long; sheaves {info['sheaves']}")
    restore_frame_material(p, m.leaves)
    by = {o.Label: o for o in m.leaves}
    def one(prefix):
        hit = [o for o in m.leaves if o.Label.startswith(prefix)]
        if len(hit) != 1:
            raise ValueError(f"{prefix!r}: {len(hit)} parts")
        return hit[0]
    tubes = [by[l] for l in TUBES]; cables = [one(c) for c in CABLES]
    ties = [o for o in m.leaves if any(o.Label.startswith(t) for t in TIES)]
    p.check(len(ties) == 20, f"the old route's 20 zip ties found ({len(ties)})")
    # ---- checks on the numbers
    p.check(all(abs(L - DESIGN["arm"]) < 0.5 for L in info["arm_len"]), f"arms {DESIGN['arm']:g} long, hinge to loop ({info['arm_len']})")
    for t, (cx, y, zc) in info["sheaves"].items():
        p.check(zc <= Z_TOP + TOL and zc - SHEAVE_R >= DANCER["floor"] - TOL,
                f"T{t} sheave Z {zc:.1f}: below the top of travel {Z_TOP:g}, its bottom above the floor {DANCER['floor']:g}")
    for cx, ycs in info["plates"].items():
        sl = info["slots"][cx]
        members = [(t, s) for t, s in info["sheaves"].items() if abs(s[0] - cx) < 1e-6]
        for t, (_, y, zc) in members:
            p.check(sl[0] + BEARING[1] <= zc <= sl[1] - BEARING[1], f"T{t} axle inside its slot (Z {zc:.1f} in {sl[0]:.1f}..{sl[1]:.1f})")
            gaps = [abs(yc - y) - PLATE_T / 2 - SHEAVE_T / 2 for yc in ycs]
            p.check(min(gaps) >= PLATE_GAP - TOL, f"T{t} sheave clear of the plates (closest {min(gaps):.2f})")
            ends = [y - AXLE_L / 2, y + AXLE_L / 2]
            # each end in its own groove: past the plate's face, short of the groove's bottom
            depth = [min(abs(e - yc) for yc in ycs) for e in ends]
            p.check(all(PLATE_T / 2 - GROOVE_D < d < PLATE_T / 2 for d in depth),
                    f"T{t} axle ends each in their own groove (end to plate centre {[round(d, 2) for d in depth]}, "
                    f"groove {PLATE_T / 2 - GROOVE_D:.1f}..{PLATE_T / 2:.1f})")
        p.check(PLATE_T - 2 * GROOVE_D >= 0.8, f"X {cx:g}: the web between two grooves {PLATE_T - 2 * GROOVE_D:.1f} mm (>= 0.8)")
        low = lowest([t for t, _ in members])
        p.check(sl[0] + BEARING[1] <= low, f"X {cx:g}: the slots reach the lowest studied pulley height ({low:.1f})")
    for cx, dims in info["sections"].items():
        sl = info["slots"][cx]
        p.check(all(max(x, y) <= PRINT_XY and z <= PRINT_Z for x, y, z in dims),
                f"X {cx:g}: each section prints standing on the Neptune ({dims}; <= {PRINT_XY:g} square, {PRINT_Z:g} tall)")
        p.check(SPLIT_Z[0] < sl[0] and sl[1] < SPLIT_Z[1],
                f"X {cx:g}: the axle grooves (Z {sl[0]:.1f}..{sl[1]:.1f}) inside the middle section ({SPLIT_Z}): no seam in a groove")
        px = info["post"][cx]
        p.check(abs(px - cx) - POST_W / 2 - max(SHEAVE_R, DANCER["RP"] + 4.6) >= 2.0,
                f"X {cx:g}: the post (X {px:g}) clear of the sheaves and the legs ({abs(px - cx) - POST_W / 2 - SHEAVE_R:.1f} >= 2)")
    p.check(all(s.isValid() and s.Volume > 0 for _, _, s, _ in parts), "every new part a valid solid")
    # ---- the bundles: new runs from the ceiling to the head, the old pieces above the roof / outside / in the head kept
    runs, routes = {}, {}
    for t in range(5):
        ot, oc = m.shapes[tubes[t].Name], m.shapes[cables[t].Name]
        tube_top = centre_at(ot, CEIL, lambda c: c.y > 300)
        cable_top = centre_at(oc, CEIL, lambda c: c.y > 300 and c.x < 0)
        inlet = centre_at(ot, LOCK_TOP, lambda c: c.y < 0)
        above = centre_at(ot, LOCK_TOP + 10.0, lambda c: c.y < 0)
        inlet_dir = unit(inlet - above)
        lock = centre_at(oc, LOCK_TOP, lambda c: c.y < 0 and c.x < 0)
        new_c, new_t, clip, r = bundle(t, tube_top, cable_top, inlet, inlet_dir)
        p.check(new_c is not None and new_t is not None, f"T{t}: the new tube and cable sweep to valid solids, the "
                f"tube's branch to the inlet no tighter than R {BRANCH_R:g} ({r.get('branch_r')})")
        if new_c is None or new_t is None: continue
        parts.append((f"clip{t}", f"Bundle split clip T{t}: the PTFE leaves the O2S cable here for the Orbiter inlet "
                      f"(printed) [lite-81, #312]", clip, "printed"))
        pts, _ = centreline(t)
        p.check((pts[-1] - lock).Length < 0.5, f"T{t}: the studied route ends at this head's lock ({(pts[-1] - lock).Length:.2f} off)")
        big = 2000.0
        kt = keep_of(ot, [(-big, big, -big, big, CEIL, big), (-big, big, -big, -20.0, -big, LOCK_TOP)])
        kc = keep_of(oc, [(-big, big, -big, big, CEIL, big), (-big, big, 505.0, big, -big, big),
                          (-big, big, -big, 0.0, -big, LOCK_TOP)])
        runs[t] = (Part.makeCompound(kt + [new_t]), Part.makeCompound(kc + [new_c]))
        routes[t] = dict(r, tube_top=tuple(round(x, 2) for x in tube_top), cable_top=tuple(round(x, 2) for x in cable_top),
                         )
        p.log(f"   T{t}: route {r['n_pts']} points, tube splits at Y {r['split_y']} Z {r['split_z']}, branch R {r['branch_r']}, clip at {r['clip_at']} ({r['how']}); new in-chamber tube ~{routes[t]['tube_len']:.0f}"
              f" mm, cable ~{routes[t]['cable_len']:.0f} mm; kept {len(kt)} tube / {len(kc)} cable pieces")
    if p.errs: return p.finish([])
    # ---- COLLISIONS: lite-80's overlaps of the old runs and ties, then the new parts and runs, against everything else
    env = {o.Name for o in m.leaves if "envelope" in o.Label.lower()}
    mine = {o.Name for o in tubes + cables + ties}
    old_items = [(o.Label, m.shapes[o.Name], o.Name) for o in tubes + cables + ties]
    base, nb = l78.overlaps(p, m, old_items, lambda n: env | mine)
    p.log(f"collision baseline (lite-80): {nb} pairs, {len(base)} overlaps of the old runs: {sorted(base)[:10]}")
    base_others = {b for _, b in base}
    items = [(lab, s, None) for _, lab, s, _ in parts]
    for t, (ts, cs) in runs.items():
        items += [(tubes[t].Label, ts, tubes[t].Name), (cables[t].Label, cs, cables[t].Name)]
    hits, nc = solid_overlaps(p, m, items, lambda n: env | mine)
    new_hits = sorted(h for h in hits if not (h[0] in {o.Label for o in tubes + cables} and (h[0], h[1]) in base))
    p.log(f"collision check: {nc} pairs, {len(hits)} overlaps, {len(new_hits)} new")
    shp = {lab: sh for lab, sh, _ in items}
    for h in new_hits:
        other = next(o for o in m.leaves if o.Label == h[1])
        try:
            c = shp[h[0]].common(m.shapes[other.Name])
            p.log("  overlap:", h, f"vol {c.Volume:.2f} at {c.BoundBox}")
        except Exception as e:
            p.log("  overlap:", h, e)
    p.check(not new_hits, f"COLLISIONS: nothing new overlaps lite-80 ({len(new_hits)}: {new_hits[:8]})")
    # within the new: parts with each other, runs with the parts, runs with each other (a tube touches its own cable)
    news = [(k, s) for k, _, s, _ in parts] + [(f"tube{t}", r[0]) for t, r in runs.items()] + [(f"cable{t}", r[1]) for t, r in runs.items()]
    bundled = lambda ka, kb: ka[:4] in ("tube", "cabl") and kb[:4] in ("tube", "cabl") and ka[-1] == kb[-1]
    work = []                                    # (ka, kb, x, y): solid pairs that can meet; a tool's own tube and
    for a in range(len(news)):                   # cable are bundled (they touch), so never computed
        for b in range(a + 1, len(news)):
            (ka, sa), (kb, sb) = news[a], news[b]
            if bundled(ka, kb) or not sa.BoundBox.intersect(sb.BoundBox): continue
            work += [(ka, kb, x, y) for x in (sa.Solids or [sa]) for y in (sb.Solids or [sb])
                     if x.BoundBox.intersect(y.BoundBox) and near_spine(x, y.BoundBox) and near_spine(y, x.BoundBox)]
    vol, prog, t0 = {}, p.log_path + ".progress", time.time()
    for i, (ka, kb, x, y) in enumerate(work):
        with open(prog, "w") as f:
            f.write(f"inner {i + 1}/{len(work)} {ka} vs {kb} ({time.time() - t0:.0f} s in)\n")
        t1 = time.time()
        try:
            v = x.common(y).Volume
        except Exception as e:
            p.log("  inner check failed:", ka, kb, e); v = 0.0
        if time.time() - t1 > SLOW: p.log(f"  slow inner pair ({time.time() - t1:.0f} s): {ka} vs {kb}")
        vol[(ka, kb)] = vol.get((ka, kb), 0.0) + v
    p.log(f"  inner: {len(work)} solid booleans in {time.time() - t0:.0f} s")
    inner = [(ka, kb, round(v, 1)) for (ka, kb), v in vol.items() if v > 0.5]
    for x in inner: p.log("  inner overlap:", x)
    p.check(not inner, f"the new parts and runs don't overlap each other ({len(inner)}: {inner[:8]})")
    if p.errs: return p.finish([])
    # ---- write
    root = m.root("4040-350x350x250 Voron Trident")
    grp = doc.addObject("App::Part", "ArmsDancers81"); grp.Label = "Bowden arms + dancers (lite-81, #312)"
    root.addObject(grp)
    for k, label, sh, role in parts:
        o = doc.addObject("Part::Feature", "AD81_" + k); grp.addObject(o)
        o.Placement = FreeCAD.Placement(); o.Shape = l78.to_local(o, sh); o.Label = label
    for t, (ts, cs) in runs.items():
        tubes[t].Shape = l78.to_local(tubes[t], ts); cables[t].Shape = l78.to_local(cables[t], cs)
    for o in ties: doc.removeObject(o.Name)
    doc.recompute(); m.refresh()
    bad = [o.Label for o in tubes + cables if abs(linkgeo.gshape(o).Volume - runs[(tubes + cables).index(o) % 5][0 if o in tubes else 1].Volume) > 1e-3]
    p.check(not bad, f"the new runs in place, in their parts' frames ({bad[:4]})")
    p.dump(dict(parts=[(k, lab, role) for k, lab, _, role in parts], routes={str(k): v for k, v in routes.items()},
                sheaves={str(t): v for t, v in info["sheaves"].items()}, collisions=dict(base=len(base), now=len(hits))))
    return p.finish([(doc, DST)])


if not os.environ.get("LITE81_AS_LIB"): litelib.Pass("lite81_arms_dancers").run(main)
