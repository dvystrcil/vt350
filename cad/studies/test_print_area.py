#!/usr/bin/env python3
"""Tests for cad/studies/print_area.py (#67).

Run: python3 cad/studies/test_print_area.py
"""
import importlib.util
import json, os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "print_area.py")
CAD = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location("print_area", SCRIPT)
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)

LOG = """\
[   53.0s] model /home/x/vt350-lite-99.FCStd (read-only)
[   53.0s] Left carried: nozzle tip Z 380.48; bed top dZ +93.32 (magnet top 287.16 -> 380.48); nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[   53.0s] Right carried: nozzle tip Z 380.49; bed top dZ +93.32 (magnet top 287.16 -> 380.49); nozzle Y reach -51.93 .. 372.00 (print square Y 30.5 .. 380.5)
[  344.3s]    Left head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  344.3s]    Left head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
[  656.3s]    Right head, left side: first nozzle X with no new overlap -418.0 (print square edge -420.0)
[  656.3s]    Right head, right side: first nozzle X with no new overlap -75.0 (print square edge -70.0)
"""
SRC = "PLATE_X0, PLATE_Y0, PLATE_W, PRINT_W = -422.5, 28.0, 355.0, 350.0   # comment\n"


class Parse(unittest.TestCase):
    def test_plate_constants_from_sweep_source(self):
        self.assertEqual(pa.parse_plate(SRC), (-422.5, 28.0, 355.0, 350.0))

    def test_reach_is_the_tightest_head_per_side(self):
        r = pa.parse_reach(LOG)
        self.assertEqual(r["model"], "vt350-lite-99")
        # X: left side the larger (inner) value, right side the smaller; Y rear the smaller; front the larger
        self.assertEqual((r["x_min"], r["x_max"]), (-416.0, -75.0))
        self.assertEqual((r["y_min"], r["y_max"]), (-51.93, 370.69))

    def test_missing_head_line_fails(self):
        with self.assertRaises(ValueError):
            pa.parse_reach("\n".join(LOG.splitlines()[:-1]))

    def test_area_clamped_to_print_square(self):
        a = pa.printable(pa.parse_reach(LOG), pa.parse_plate(SRC))
        # plate coords, front-left plate corner = 0,0; square inset 2.5
        self.assertEqual(a["square"], (2.5, 2.5, 352.5, 352.5))
        self.assertEqual(a["area"], (6.5, 2.5, 347.5, 342.69))   # front reach -51.93 clamps to the square edge
        self.assertAlmostEqual(a["width"], 341.0)
        self.assertAlmostEqual(a["depth"], 340.19)


class Svg(unittest.TestCase):
    def test_svg_labels_the_three_outlines(self):
        a = pa.printable(pa.parse_reach(LOG), pa.parse_plate(SRC))
        svg = pa.svg(a)
        self.assertTrue(svg.startswith("<svg"))
        for text in ("355 × 355 plate", "350 × 350 print square", "341.0 × 340.19", "vt350-lite-99", "FRONT"):
            self.assertIn(text, svg)

    def test_committed_svg_matches_the_committed_log(self):
        """The drawing in the repo is what the script makes from the repo's sweep log (regenerate after a sweep)."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "print-area.svg")
            subprocess.run([sys.executable, SCRIPT, "--out", out], check=True, capture_output=True)
            with open(out, encoding="utf-8") as f, open(os.path.join(CAD, "data", "print-area.svg"), encoding="utf-8") as g:
                self.assertEqual(f.read(), g.read(), "cad/data/print-area.svg is stale: run python3 cad/studies/print_area.py")


class Beacon(unittest.TestCase):
    """vt350#291: the coil's reach (both heads, the planned y_offset) and beacon.cfg's mesh, drawn on the same page."""
    def committed(self):
        reach = pa.parse_reach(open(os.path.join(CAD, "data", "logs", "sweep_toolhead.log")).read())
        plate = pa.parse_plate(open(os.path.join(HERE, "sweep_toolhead.py")).read())
        b = pa.beacon_area(reach, plate, pa.parse_beacon(open(pa.BEACON_CFG).read()), json.load(open(pa.FRONT_REACH)),
                           json.load(open(pa.MAPPING)))
        return reach, plate, b

    def test_front_margin_is_the_what_if_s(self):
        # cad/data/front_reach_front17.json: worst nozzle printer Y -11.67, coil 3.33 at y_offset 15, mesh front 5.48
        _, _, b = self.committed()
        self.assertEqual(b["dy"], 15.0)
        self.assertEqual(b["margin"]["front"], 2.15)
        self.assertTrue(all(v >= 0 for v in b["margin"].values()), b["margin"])

    def test_the_coil_offset_moves_the_front_edge(self):
        reach, plate, _ = self.committed()
        args = (pa.parse_beacon(open(pa.BEACON_CFG).read()), json.load(open(pa.FRONT_REACH)), json.load(open(pa.MAPPING)))
        far = pa.beacon_area(reach, plate, *args, dy=27.4)
        self.assertAlmostEqual(far["margin"]["front"], 2.15 - 12.4, places=2)     # 12.4 further back: mesh not reached

    def test_svg_draws_and_labels_it(self):
        reach, plate, b = self.committed()
        svg = pa.svg(pa.printable(reach, plate), b)
        self.assertIn("<polygon", svg)
        self.assertIn("planned y_offset 15", svg)
        self.assertIn("front 2.15", svg)
        self.assertNotIn("NOT REACHED", svg)

    def test_parse_beacon(self):
        c = pa.parse_beacon("[beacon]\nx_offset: 0\ny_offset: 27.4\n[bed_mesh]\nmesh_min: 5.48, 5.48\nmesh_max: 344.52, 344.52\n")
        self.assertEqual(c, {"dx": 0.0, "dy": 27.4, "mesh_min": (5.48, 5.48), "mesh_max": (344.52, 344.52)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
