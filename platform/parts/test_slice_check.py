#!/usr/bin/env python3
"""Tests for platform/parts/slice-check.py (#70): G-code parsing, keep-out boxes, report, preview. No slicer needed.

Run: python3 platform/parts/test_slice_check.py
"""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("slice_check", os.path.join(HERE, "slice-check.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

# two layers; absolute E with a G92 reset in the middle; support on layer 1 at X 10..20
GCODE = """\
M82 ; use absolute distances for extrusion
G92 E0
;LAYER_CHANGE
;Z:0.2
G1 Z0.2 F720
;TYPE:External perimeter
G1 X0 Y0
G1 X10 Y0 E1.0
G1 X10 Y10 E2.0
;TYPE:Support material
G1 X10 Y0
G1 X20 Y0 E2.5
G1 E2.0 F2100 ; retract (negative: not counted)
G92 E0
;LAYER_CHANGE
;Z:0.4
G1 Z0.4
;TYPE:Support material interface
G1 X20 Y5 E0.25
;TYPE:Perimeter
G1 X0 Y5 E1.25
; filament used [mm] = 3.75
; filament used [cm3] = 0.01
; estimated printing time (normal mode) = 1m 2s
"""


class Parse(unittest.TestCase):
    def setUp(self):
        self.g = sc.parse_gcode(GCODE)

    def test_filament_per_type_counts_only_extrusion(self):
        t = self.g["types"]
        self.assertAlmostEqual(t["External perimeter"], 2.0)
        self.assertAlmostEqual(t["Support material"], 0.5)          # the retract and G92 reset are not support
        self.assertAlmostEqual(t["Support material interface"], 0.25)
        self.assertAlmostEqual(t["Perimeter"], 1.0)

    def test_support_total_and_flag(self):
        self.assertAlmostEqual(self.g["support_mm"], 0.75)
        self.assertTrue(self.g["support"])

    def test_footer_stats(self):
        self.assertEqual(self.g["time"], "1m 2s")
        self.assertAlmostEqual(self.g["filament_mm"], 3.75)

    def test_segments_carry_type_and_z(self):
        sup = [s for s in self.g["segments"] if sc.is_support(s[0])]
        self.assertEqual(len(sup), 2)
        self.assertEqual(sup[0][1:], (10.0, 0.0, 20.0, 0.0, 0.2))
        self.assertEqual(sup[1][5], 0.4)

    def test_no_support(self):
        g = sc.parse_gcode(GCODE.replace(";TYPE:Support material interface", ";TYPE:Solid infill")
                           .replace(";TYPE:Support material", ";TYPE:Solid infill"))
        self.assertFalse(g["support"])
        self.assertEqual(g["support_mm"], 0.0)


class KeepOut(unittest.TestCase):
    def test_support_inside_a_box_is_reported_in_stl_coordinates(self):
        g = sc.parse_gcode(GCODE)
        # the STL sits at X 100.. in its own frame; the slicer centred it so gcode = stl + (-100, 0, 0)
        offset = (-100.0, 0.0, 0.0)
        hit = sc.keepout_hits(g["segments"], [{"name": "air channel", "min": [112, -1, 0], "max": [118, 1, 1]}], offset)
        self.assertEqual([h["box"] for h in hit], ["air channel"])
        self.assertEqual(hit[0]["segments"], 1)

    def test_model_extrusion_inside_a_box_is_fine(self):
        g = sc.parse_gcode(GCODE)
        hit = sc.keepout_hits(g["segments"], [{"name": "wall", "min": [99, -1, 0], "max": [111, 11, 1]}], (-100.0, 0, 0))
        # perimeters are inside, but only support counts; the support segment from X 110..120 crosses X 111? it starts at 110
        self.assertEqual([h["box"] for h in hit], ["wall"])          # support start point (110,0) is inside
        hit = sc.keepout_hits(g["segments"], [{"name": "wall", "min": [99, 1, 0], "max": [111, 11, 1]}], (-100.0, 0, 0))
        self.assertEqual(hit, [])

    def test_offset_from_slicer_info(self):
        info = {"min_x": 100.0, "max_x": 120.0, "min_y": -10.0, "max_y": 10.0, "min_z": 5.0}
        self.assertEqual(sc.offset_for(info, centre=(177.5, 177.5)), (67.5, 177.5, -5.0))

    def test_keepout_file_is_validated(self):
        with self.assertRaises(ValueError):
            sc.validate_keepout({"part.stl": [{"name": "x", "min": [0, 0], "max": [1, 1, 1]}]})
        with self.assertRaises(ValueError):
            sc.validate_keepout({"part.stl": [{"name": "x", "min": [2, 0, 0], "max": [1, 1, 1]}]})
        sc.validate_keepout({"part.stl": [{"name": "x", "min": [0, 0, 0], "max": [1, 1, 1]}]})
        sc.validate_keepout({"_doc": "a note", "part.stl": []})       # keys starting with _ are notes


class Info(unittest.TestCase):
    def test_parse_info(self):
        out = "[a.stl]\nsize_x = 57.1\nmin_x = 121.4\nmin_y = 125.4\nmin_z = 0.000000\nmax_x = 178.5\nmax_y = 174.5\nmanifold = yes\n"
        i = sc.parse_info(out)
        self.assertEqual(i["min_x"], 121.4)
        self.assertEqual(i["manifold"], "yes")

    def test_warnings_are_picked_from_slicer_output(self):
        out = "70 => Generating support material\nDetected print stability issues:\n\nFloating object part\nLow bed adhesion\n\n90 => Exporting G-code\n"
        self.assertEqual(sc.slicer_warnings(out), ["Detected print stability issues: Floating object part; Low bed adhesion"])
        self.assertEqual(sc.slicer_warnings("90 => Exporting G-code\n"), [])
        # PrusaSlicer's own complaint about a '[t]_' file name is not a print problem
        noise = "[2026-11-06 18:12:39.4] [0x7] [error]   Failed to apply the print statistics to the export file name: Parsing error\n"
        self.assertEqual(sc.slicer_warnings(noise), [])


class Preview(unittest.TestCase):
    def test_svg_has_three_views_support_in_red_and_the_box(self):
        g = sc.parse_gcode(GCODE)
        s = sc.svg(g["segments"], [{"name": "air", "min": [0, 0, 0], "max": [5, 5, 5]}], (0.0, 0.0, 0.0), title="t")
        self.assertTrue(s.startswith("<svg"))
        self.assertEqual(s.count('class="view"'), 3)
        self.assertIn(sc.SUPPORT_COLOUR, s)
        self.assertIn("air", s)


class Report(unittest.TestCase):
    def test_markdown_row_per_part(self):
        rows = [dict(part="a.stl", support=True, support_cm3=1.234, time="1h", filament_cm3=10.0, warnings=["w"],
                     keepout=[{"box": "air", "segments": 3}], png="a.png")]
        md = sc.report_md(rows, profile="p.ini")
        self.assertIn("| a.stl | yes | 1.23 |", md)
        self.assertIn("**FAIL** air (3 segments)", md)
        self.assertIn("p.ini", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
