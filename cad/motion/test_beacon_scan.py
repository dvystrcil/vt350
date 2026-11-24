#!/usr/bin/env python3
"""Tests for beacon_scan.py (vt350#291). Run: python3 cad/motion/test_beacon_scan.py"""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beacon_scan as bs  # noqa: E402


class FromTheConfig(unittest.TestCase):
    """The video's values are beacon.cfg's and printer.cfg's (owner 2026-11-22: link the cfg to the rendering)."""

    def test_committed_values(self):
        s = bs.settings()
        self.assertEqual(s["offset"], (0.0, 15.0))   # lite-79 (#291); 27.4 before
        self.assertEqual(s["axis_min"], (4.0, -99.43)); self.assertEqual(s["axis_max"], (346.0, 340.19))
        self.assertEqual(len(s["tilt_points"]), 3)

    def test_a_changed_cfg_changes_the_path(self):
        with open(bs.BEACON_CFG) as f:
            text = f.read()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "beacon.cfg")
            with open(p, "w") as f:
                f.write(text.replace("mesh_min: 5.48, 5.48", "mesh_min: 20, 30").replace("probe_count: 15, 15", "probe_count: 7, 9"))
            s = bs.settings(beacon_cfg=p)
        self.assertEqual(s["mesh_min"], (20.0, 30.0)); self.assertEqual(s["probe_count"], (7, 9))
        path = bs.scan_path(s["mesh_min"], s["mesh_max"], s["probe_count"], s["offset"])
        self.assertAlmostEqual(path[0][0], 20.0); self.assertAlmostEqual(path[0][1], 30.0 - 15.0)

    def test_committed_gcode_is_what_the_cfg_gives(self):
        """Edit beacon.cfg, then: python3 cad/motion/beacon_scan.py > cad/motion/beacon_scan.gcode, and rerun Kalico
        for the timeline (cad/motion/README.md)."""
        with open(os.path.join(os.path.dirname(bs.__file__), "beacon_scan.gcode")) as f:
            self.assertEqual(f.read(), bs.gcode())

    def test_printer_cfg_does_not_include_beacon_cfg_yet(self):
        """Kalico batch mode can't load [beacon]; printer.cfg includes beacon.cfg when the Beacon is wired."""
        import pinmap
        self.assertNotIn(os.path.abspath(bs.BEACON_CFG), pinmap.load(bs.PRINTER_CFG).files)


class Overscan(unittest.TestCase):
    def test_vt350_rear_room_limits_it(self):
        # nozzle Y range 5.48-15 .. 344.52-15 = -9.52 .. 329.52; rooms 89.91 front, 10.67 rear; spacing+2 = 26.22
        # (at lite-78's 27.4 it was 23.07: the smaller offset brings the nozzle 12.4 nearer the rear limit)
        self.assertAlmostEqual(bs.overscan(), 340.19 - (344.52 - 15.0), places=6)

    def test_spacing_limits_it_with_room(self):
        self.assertAlmostEqual(bs.overscan((50, 50), (150, 150), (11, 11), (0, 0), (0, 0), (300, 300)), 12.0)


class Path(unittest.TestCase):
    def test_extent_is_the_mesh_less_the_offset_plus_the_overscan(self):
        p = bs.scan_path()
        o = bs.overscan()
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        self.assertAlmostEqual(min(xs), 5.48); self.assertAlmostEqual(max(xs), 344.52)
        self.assertAlmostEqual(min(ys), 5.48 - 15.0 - o, places=3)
        self.assertAlmostEqual(max(ys), 344.52 - 15.0 + o, places=3)

    def test_lines_run_along_y_serpentine(self):
        p = bs.scan_path()
        self.assertEqual(p[0], (5.48, 5.48 - 15.0)); self.assertEqual(p[1], (5.48, 344.52 - 15.0))
        self.assertAlmostEqual(p[-1][0], 344.52); self.assertAlmostEqual(p[-1][1], 344.52 - 15.0)   # 15 lines: ends at the back

    def test_steps_stay_inside_the_axis_limits(self):
        for x, y in bs.scan_path():
            self.assertTrue(bs.AXIS_MIN[0] <= x <= bs.AXIS_MAX[0] and bs.AXIS_MIN[1] - 1e-9 <= y <= bs.AXIS_MAX[1] + 1e-9)

    def test_order_is_coarse_home_pickup_tilt_tap_scan(self):
        """Owner 2026-11-22: coarse Z by proximity with no head, then T0, the tilt taps, the Z0 taps, the scan."""
        g = bs.gcode().splitlines()
        bc = bs.S["beacon"]
        tap = f"G1 Z0 F{bc['autocal_speed'] * 60:g}"
        dive = g.index(f"G1 Z{bs.TRIGGER_Z:g} F{bc['speed'] * 60:g}")
        t0 = g.index("T0")
        taps = [i for i, l in enumerate(g) if l == tap]
        scan_start = [i for i, l in enumerate(g) if l.startswith("; 5.")][0]
        self.assertLess(dive, t0)
        self.assertEqual(len(taps), len(bs.TILT_POINTS) + bc["autocal_sample_count"])
        self.assertLess(t0, taps[0]); self.assertLess(taps[-1], scan_start)

    def test_moves_use_the_cfg_speeds_and_heights(self):
        g = bs.gcode().splitlines()
        zt, bm = bs.S["z_tilt"], bs.S["bed_mesh"]
        for x, y in bs.TILT_POINTS:
            self.assertIn(f"G1 X{x:g} Y{y:g} F{zt['speed'] * 60:g}", g)
        self.assertIn(f"G1 Z{zt['horizontal_move_z']:g} F{bs.S['beacon']['autocal_retract_speed'] * 60:g}", g)
        scan = [l for l in g if l.endswith(f"F{bm['speed'] * 60:g}")]
        self.assertGreater(len(scan), 30)

if __name__ == "__main__":
    unittest.main(verbosity=2)
