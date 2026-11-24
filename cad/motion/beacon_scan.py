#!/usr/bin/env python3
"""G-code for one Beacon start-of-print on the VT350, for the motion video (vt350#291). The owner's order (2026-11-22):
  1. home with no head on the carriage: X, Y, then a coarse Z by Beacon proximity (the Beacon is on the carriage, so
     it needs no head; there is no nozzle to tap yet);
  2. pick up T0;
  3. Z_TILT_ADJUST by nozzle taps, one near each of the three Z leadscrews;
  4. a nozzle tap at the home position: the true Z0 (contact homing);
  5. the Beacon's bed-mesh scan path.
The bed mesh is always the LAST measurement (owner, 2026-11-24): after the Z tilt, the Z0 and the tool pickup, because
each of those changes what the mesh is measured against. Nothing after it may tap, home, tilt or change tools; only
the purge line and the print follow. Any old mesh is cleared (BED_MESH_CLEAR) before the tilt. The shape follows the
owner's Neptune PRINT_START (G28, SKEW_PROFILE LOAD, BED_MESH_CLEAR, BED_MESH_CALIBRATE, CLEAR_PAUSE, LINE_PURGE),
with the toolchanger's steps added.

    python3 cad/motion/beacon_scan.py > cad/motion/beacon_scan.gcode      # then run it through Kalico batch mode

The scan path is Beacon's own (beacon3d/beacon_klipper@3ccd2e6 beacon.py, GPL-3.0: BeaconMeshHelper._generate_path,
_handle_connect's auto overscan, arc_points), reimplemented here:
  - lines run along mesh_main_direction (default y), one per probe_count in the other axis, serpentine;
  - the nozzle path is the mesh (coil positions) less the Beacon's offset;
  - at each line end the head runs past the mesh by the overscan, turning on two arcs. With mesh_overscan unset
    (-1) it is min(room before the mesh's start, room after its end, line spacing + 2), the rooms measured from the
    nozzle range to the axis limits.
  - the scan flies at Z = trigger_distance (2) at bed_mesh speed.

Every value comes from the config, so the video shows what the printer would do (owner, 2026-11-22):
cad/klipper/beacon.cfg ([beacon], [bed_mesh], [z_tilt]; not included by printer.cfg yet) and the X/Y axis limits from
printer.cfg and its includes (cad_values.cfg). Plain python3, standard library only. VT350-specific.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "platform", "klipper")]
import pinmap  # noqa: E402

BEACON_CFG = os.path.join(ROOT, "cad", "klipper", "beacon.cfg")
PRINTER_CFG = os.path.join(ROOT, "cad", "klipper", "printer.cfg")
# Beacon's defaults for options beacon.cfg leaves unset (beacon3d/beacon_klipper@3ccd2e6 beacon.py)
BEACON_DEFAULTS = dict(trigger_distance=2.0, speed=5.0, home_z_hop=0.0, home_z_hop_speed=15.0, home_xy_move_speed=50.0,
                       autocal_speed=3.0, autocal_retract_dist=2.0, autocal_retract_speed=10.0, autocal_sample_count=3)
# Klipper's defaults for [z_tilt] and [bed_mesh] (Config_Reference)
Z_TILT_DEFAULTS = dict(speed=50.0, horizontal_move_z=5.0)
BED_MESH_DEFAULTS = dict(speed=50.0, horizontal_move_z=5.0)


def _xy(v):
    a, b = (float(t) for t in v.split(","))
    return (a, b)


def _xy_list(v):
    return tuple(_xy(line) for line in v.strip().splitlines() if line.strip())


def settings(beacon_cfg=BEACON_CFG, printer_cfg=PRINTER_CFG):
    """The values the video uses, from the config files."""
    b = pinmap.load(beacon_cfg).sections
    p = pinmap.load(printer_cfg).sections
    pc = [int(t) for t in b["bed_mesh"]["probe_count"].split(",")]
    get = lambda sec, d: {k: type(v)(b[sec].get(k, v)) for k, v in d.items()}
    return dict(beacon=get("beacon", BEACON_DEFAULTS), z_tilt=get("z_tilt", Z_TILT_DEFAULTS),
                bed_mesh=get("bed_mesh", BED_MESH_DEFAULTS),
        offset=(float(b["beacon"].get("x_offset", 0)), float(b["beacon"].get("y_offset", 0))),
        home_xy=_xy(b["beacon"]["home_xy_position"]),
        direction=b["beacon"].get("mesh_main_direction", "y").lower(),
        mesh_min=_xy(b["bed_mesh"]["mesh_min"]), mesh_max=_xy(b["bed_mesh"]["mesh_max"]),
        probe_count=(pc[0], pc[-1]), speed=float(b["bed_mesh"]["speed"]),
        tilt_points=_xy_list(b["z_tilt"]["points"]),
        axis_min=(float(p["stepper_x"]["position_min"]), float(p["stepper_y"]["position_min"])),
        axis_max=(float(p["stepper_x"]["position_max"]), float(p["stepper_y"]["position_max"])))


S = settings()
BEACON_XY, HOME_XY, TILT_POINTS = S["offset"], S["home_xy"], S["tilt_points"]
MESH_MIN, MESH_MAX, PROBE_COUNT = S["mesh_min"], S["mesh_max"], S["probe_count"]
AXIS_MIN, AXIS_MAX, SCAN_SPEED, DIRECTION = S["axis_min"], S["axis_max"], S["speed"], S["direction"]
TRIGGER_Z = S["beacon"]["trigger_distance"]       # the scan height


def arc_points(cx, cy, r, start_deg, span_deg):
    """beacon.py arc_points: points on an arc no more than 0.1 mm off it."""
    a0, span = math.radians(start_deg), math.radians(span_deg)
    d = math.acos(1 - 0.1 / r)
    n = int(math.ceil(abs(span) / d))
    return [(cx + math.cos(a0 + span * i / n) * r, cy + math.sin(a0 + span * i / n) * r) for i in range(n + 1)]


def overscan(mesh_min=MESH_MIN, mesh_max=MESH_MAX, count=PROBE_COUNT, offset=BEACON_XY, axis_min=AXIS_MIN,
             axis_max=AXIS_MAX, direction=DIRECTION):
    """_handle_connect's auto overscan (mesh_overscan unset)."""
    a, p = (1, 0) if direction == "y" else (0, 1)          # along the lines, across them
    lo, hi = mesh_min[a] - offset[a], mesh_max[a] - offset[a]
    space = (mesh_max[p] - mesh_min[p]) / (count[p] - 1)
    return min(max(0.0, lo - axis_min[a]), max(0.0, axis_max[a] - hi), space + 2.0)


def scan_path(mesh_min=MESH_MIN, mesh_max=MESH_MAX, count=PROBE_COUNT, offset=BEACON_XY, over=None, direction=DIRECTION):
    """Nozzle XY points of the scan, in order (_generate_path)."""
    if over is None:
        over = overscan(mesh_min, mesh_max, count, offset, direction=direction)
    a, p = (1, 0) if direction == "y" else (0, 1)
    begin_a, end_a = mesh_min[a] - offset[a], mesh_max[a] - offset[a]
    begin_p, end_p = mesh_min[p] - offset[p], mesh_max[p] - offset[p]
    n = count[p]
    step = (end_p - begin_p) / (n - 1)
    r = min(step / 2, over)
    pts = []
    for i in range(n):
        pos_p = begin_p + step * i
        even = i % 2 == 0
        line = ((begin_a, pos_p), (end_a, pos_p)) if even else ((end_a, pos_p), (begin_a, pos_p))
        if pts and r > 0:
            if even:
                c = begin_a - over + r
                pts += arc_points(c, pos_p - step + r, r, -90, -90) + arc_points(c, pos_p - r, r, -180, -90)
            else:
                c = end_a + over - r
                pts += arc_points(c, pos_p - step + r, r, -90, 90) + arc_points(c, pos_p - r, r, 0, 90)
        pts += list(line)
    return [(q, pa) for pa, q in pts] if direction == "y" else pts


def gcode(s=None):
    """The start of print as G-code. Batch mode has no probe, so each probing step is written as the moves it makes,
    at beacon.cfg's heights and speeds (Beacon's and Klipper's defaults where it sets none): a dive or tap goes all the
    way to its target (the real one stops on the trigger, at about the same place)."""
    s = s or S
    bc, zt, bm = s["beacon"], s["z_tilt"], s["bed_mesh"]
    f = lambda v: f"{v:.3f}".rstrip("0").rstrip(".")
    F = lambda mm_s: f"F{f(mm_s * 60)}"
    hx, hy = s["home_xy"]
    hop = bc["home_z_hop"]
    path = scan_path(s["mesh_min"], s["mesh_max"], s["probe_count"], s["offset"], direction=s["direction"])

    def tap(n=1):
        """A contact tap: down at autocal_speed, back up autocal_retract_dist; n samples."""
        out = []
        for _ in range(n):
            out += [f"G1 Z0 {F(bc['autocal_speed'])}", f"G1 Z{f(bc['autocal_retract_dist'])} {F(bc['autocal_retract_speed'])}"]
        return out

    out = [
        "; VT350 start of print with the Beacon (vt350#291), for the motion video. Generated by cad/motion/beacon_scan.py",
        "; from cad/klipper/beacon.cfg; don't edit. Batch mode has no probe: G28 is instant (set_position), and each",
        "; probing step below is written as the moves it makes.",
        "G28", "G90", "INITIALIZE_TOOLCHANGER",
        "; BED_MESH_CLEAR: no old mesh under the tilt and Z0 taps (not run here: batch mode has no [bed_mesh])",
        "; 1. coarse Z, no head on the carriage (G28 Z METHOD=PROXIMITY): to home_xy_position at home_z_hop, then the",
        ";    carriage dives at [beacon] speed until the coil is at trigger_distance, and hops back",
        f"G1 Z{f(max(hop, zt['horizontal_move_z']))} {F(bc['home_z_hop_speed'])}",
        f"G1 X{f(hx)} Y{f(hy)} {F(bc['home_xy_move_speed'])}",
        f"G1 Z{f(TRIGGER_Z)} {F(bc['speed'])}", f"G1 Z{f(max(hop, TRIGGER_Z))} {F(bc['home_z_hop_speed'])}",
        "; 2. pick up T0 (left)", "T0",
        "; 3. Z_TILT_ADJUST PROBE_METHOD=CONTACT: [z_tilt] points at its speed and horizontal_move_z, a tap at each",
        ";    (one pass shown; the real command repeats until within retry_tolerance)",
    ]
    for x, y in s["tilt_points"]:
        out += [f"G1 Z{f(zt['horizontal_move_z'])} {F(bc['autocal_retract_speed'])}",
                f"G1 X{f(x)} Y{f(y)} {F(zt['speed'])}", *tap()]
    out += [f"G1 Z{f(zt['horizontal_move_z'])} {F(bc['autocal_retract_speed'])}",
            f"; 4. the true Z0 (G28 Z METHOD=CONTACT CALIBRATE=1): to home_xy_position, then autocal_sample_count taps",
            f"G1 X{f(hx)} Y{f(hy)} {F(bc['home_xy_move_speed'])}", *tap(bc["autocal_sample_count"]),
            f"G1 Z{f(max(hop, bm['horizontal_move_z']))} {F(bc['home_z_hop_speed'])}",
            f"; 5. the Beacon scan (BED_MESH_CALIBRATE): coil mesh {s['mesh_min']} .. {s['mesh_max']}, "
            f"{s['probe_count'][0]} lines along {s['direction'].upper()}, overscan "
            f"{overscan(s['mesh_min'], s['mesh_max'], s['probe_count'], s['offset'], s['axis_min'], s['axis_max'], s['direction']):.2f} mm,"
            f" at Z {f(TRIGGER_Z)} and {f(bm['speed'])} mm/s",
            f"G1 X{f(path[0][0])} Y{f(path[0][1])} {F(bm['speed'])}", f"G1 Z{f(TRIGGER_Z)} {F(bc['speed'])}"]
    out += [f"G1 X{f(x)} Y{f(y)} {F(bm['speed'])}" for x, y in path[1:]]
    out += [f"G1 Z{f(bm['horizontal_move_z'])} {F(bc['speed'])}"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.write(gcode())
