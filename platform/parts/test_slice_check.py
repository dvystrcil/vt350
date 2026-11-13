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


# Orca-style G-code: relative E (M83), Orca's own support type names, an arc move, feed rates per feature
ORCA_GCODE = """\
M83 ; use relative distances for extrusion
;LAYER_CHANGE
;Z:0.2
G1 Z0.2 F720
;TYPE:Outer wall
G1 X0 Y0 F12000
G1 X10 Y0 E1.0 F12000
G1 X10 Y10 E1.0
;TYPE:Support
G1 X10 Y0 F9000
G1 X20 Y0 E0.5 F6000
G1 E-0.8 F2100 ; retract (negative: not counted)
;LAYER_CHANGE
;Z:0.4
G1 Z0.4
;TYPE:Support interface
G3 X20 Y5 I0 J2.5 E0.25 F3000
;TYPE:Inner wall
G1 X0 Y5 E1.0 F30000
; filament used [mm] = 3.75
; estimated printing time (normal mode) = 1m 2s
"""

STATS = {
    "version": 1, "generator": "OrcaSlicer 2.5.0", "units": {"time": "s", "length": "mm", "volume": "mm3", "weight": "g"},
    "summary": {"time": 3725.5, "layer_count": 3, "weight": 12.5, "filament_cost": 0.18,
                "filaments": [{"id": 1, "length": 4200.0, "volume": 9690.0, "weight": 12.5, "cost": 0.18,
                               "support": {"volume": 120.0, "weight": 0.15}}],
                "features": {"Outer wall": {"time": 600.0, "volume": 1000.0, "weight": 1.29},
                             "Support": {"time": 100.0, "volume": 120.0, "weight": 0.15}}},
    "layers": [{"z": 0.2, "time": 9.5}, {"z": 0.4, "time": 31.0}, {"z": 0.6, "time": 12.0}],
    "objects": [{"name": "a.stl", "support_volume": 120.0, "support_weight": 0.15}],
}


class Orca(unittest.TestCase):
    def setUp(self):
        self.g = sc.parse_gcode(ORCA_GCODE)

    def test_relative_e_counts_each_move(self):
        t = self.g["types"]
        self.assertAlmostEqual(t["Outer wall"], 2.0)
        self.assertAlmostEqual(t["Support"], 0.5)                     # the -0.8 retract is not support
        self.assertAlmostEqual(t["Support interface"], 0.25)          # an arc (G3) extrudes too
        self.assertAlmostEqual(t["Inner wall"], 1.0)

    def test_orca_support_names_are_support(self):
        self.assertTrue(sc.is_support("Support"))
        self.assertTrue(sc.is_support("Support interface"))
        self.assertTrue(sc.is_support("Support transition"))
        self.assertTrue(sc.is_support("Support material interface"))   # PrusaSlicer's names still are
        self.assertFalse(sc.is_support("Outer wall"))
        self.assertAlmostEqual(self.g["support_mm"], 0.75)

    def test_multi_filament_footer_is_summed(self):
        # a 4-slot (MMU) machine preset: Orca lists one length per filament
        g = sc.parse_gcode(ORCA_GCODE.replace("; filament used [mm] = 3.75", "; filament used [mm] = 0.00, 56262.59, 0.00, 0.00"))
        self.assertAlmostEqual(g["filament_mm"], 56262.59)

    def test_arc_segment_ends_at_its_target(self):
        arc = [s for s in self.g["segments"] if s[0] == "Support interface"]
        self.assertEqual(arc[0][1:], (20.0, 0.0, 20.0, 5.0, 0.4))

    def test_feature_speeds_in_mm_per_s(self):
        sp = self.g["speeds"]
        self.assertEqual(sp["Outer wall"], {"min": 200.0, "max": 200.0, "median": 200.0})   # F carries over
        self.assertEqual(sp["Support"]["max"], 100.0)
        self.assertEqual(sp["Inner wall"]["median"], 500.0)

    def test_estimates_from_statistics(self):
        e = sc.orca_estimates(STATS)
        self.assertEqual(e["time"], "1h 2m 5s")
        self.assertAlmostEqual(e["grams"], 12.5)
        self.assertAlmostEqual(e["cost"], 0.18)
        self.assertAlmostEqual(e["filament_mm"], 4200.0)
        self.assertAlmostEqual(e["support_cm3"], 0.12)
        self.assertEqual(e["layer_times"], [(0.2, 9.5), (0.4, 31.0), (0.6, 12.0)])
        self.assertEqual(e["slowest_layer"], (0.4, 31.0))
        self.assertEqual(e["features"]["Outer wall"]["time"], 600.0)

    def test_statistics_units_are_checked(self):
        bad = json.loads(json.dumps(STATS)); bad["units"]["time"] = "min"
        with self.assertRaises(ValueError):
            sc.orca_estimates(bad)

    def test_warnings_from_result_json(self):
        res = {"return_code": 0, "error_string": "Success.", "warnings": [{"class": "support_needed", "message": "Floating cantilever"}],
               "sliced_plates": [{"id": 1, "warning_message": "Low adhesion"}]}
        self.assertEqual(sc.orca_warnings(res), ["support_needed: Floating cantilever", "Low adhesion"])
        self.assertEqual(sc.orca_warnings({"return_code": 0, "warnings": [], "sliced_plates": [{"warning_message": ""}]}), [])

    def test_offset_from_stl_and_gcode_centres(self):
        # STL box X 100..120, Y -10..10, Z 5..25; model extrusions centred at (117.5, 117.5) -> offset
        segs = [("Outer wall", 107.5, 107.5, 127.5, 107.5, 0.2), ("Outer wall", 127.5, 107.5, 127.5, 127.5, 0.2),
                ("Support", 0.0, 0.0, 1.0, 0.0, 0.2)]                    # support/brim don't move the centre
        off = sc.offset_from_gcode((100.0, -10.0, 5.0), (120.0, 10.0, 25.0), segs)
        self.assertEqual(off, (7.5, 117.5, -5.0))

    def test_stl_bbox_binary_and_ascii(self):
        import struct
        with tempfile.TemporaryDirectory() as d:
            b = os.path.join(d, "b.stl")
            with open(b, "wb") as f:
                f.write(b"\0" * 80 + struct.pack("<I", 1))
                f.write(struct.pack("<12fH", 0, 0, 1, 1, 2, 3, -4, 5, 6, 7, 8, -9, 0))
            self.assertEqual(sc.stl_bbox(b), ((-4.0, 2.0, -9.0), (7.0, 8.0, 6.0)))
            a = os.path.join(d, "a.stl")
            with open(a, "w") as f:
                f.write("solid x\nfacet normal 0 0 1\nouter loop\nvertex 1 2 3\nvertex -1 0 0\nvertex 4 5 -6\n"
                        "endloop\nendfacet\nendsolid x\n")
            self.assertEqual(sc.stl_bbox(a), ((-1.0, 0.0, -6.0), (4.0, 5.0, 3.0)))

    def test_datadir_installs_vendors_and_the_support_check_process(self):
        with tempfile.TemporaryDirectory() as d:
            prof = os.path.join(d, "profiles"); os.makedirs(prof)
            for v in ("Elegoo", "OrcaFilamentLibrary", "Other"):
                open(os.path.join(prof, v + ".opc"), "wb").write(b"opc")
            src = os.path.join(d, "orca")
            for t, name in (("machine", "M  x"), ("process", "P"), ("filament", "F")):
                os.makedirs(os.path.join(src, t))
                json.dump({"name": name, "inherits": "parent", "enable_support": "0"}, open(os.path.join(src, t, name + ".json"), "w"))
            manifest = {"vendors": ["Elegoo", "OrcaFilamentLibrary"], "machine": "machine/M  x.json",
                        "process": "process/P.json", "filament": "filament/F.json",
                        "support_check": {"enable_support": "1", "support_threshold_angle": "45"}}
            dd = os.path.join(d, "dd")
            p = sc.orca_datadir(dd, manifest, src, prof)
            self.assertEqual(sorted(os.listdir(os.path.join(dd, "system"))), ["Elegoo.opc", "OrcaFilamentLibrary.opc"])
            # every preset sits in <datadir>/user/default/<type>/: Orca resolves `inherits` only for those
            for t in ("machine", "process", "filament"):
                self.assertEqual(os.path.dirname(p[t]), os.path.join(dd, "user", "default", t))
            self.assertEqual(os.path.basename(p["machine"]), "M  x.json")        # the two spaces survive
            proc = json.load(open(p["process"]))
            self.assertEqual(proc["enable_support"], "1")
            self.assertEqual(proc["support_threshold_angle"], "45")
            self.assertNotEqual(proc["name"], "P")                               # not the user's preset any more
            self.assertEqual(proc["inherits"], "parent")
            self.assertEqual(json.load(open(p["filament"]))["enable_support"], "0")   # only the process is changed
            with self.assertRaises(FileNotFoundError):
                sc.orca_datadir(os.path.join(d, "dd2"), dict(manifest, vendors=["Missing"]), src, prof)

    def test_shipped_manifest_names_real_files(self):
        m = json.load(open(sc.ORCA_MANIFEST))
        for t in ("machine", "process", "filament"):
            f = os.path.join(os.path.dirname(sc.ORCA_MANIFEST), m[t])
            self.assertTrue(os.path.isfile(f), f)
            self.assertIn("inherits", json.load(open(f)))
        self.assertIn("Elegoo", m["vendors"])
        self.assertEqual(m["support_check"]["enable_support"], "1")


class OrcaReport(unittest.TestCase):
    def test_orca_columns_and_feature_table(self):
        rows = [dict(part="a.stl", support=True, support_cm3=0.12, time="1h 2m 5s", filament_cm3=9.69, warnings=[],
                     keepout=[], png="a.png", grams=12.5, cost=0.18, slowest_layer=(0.4, 31.0),
                     features={"Outer wall": {"time": 600.0, "weight": 1.29}}, speeds={"Outer wall": {"min": 200.0, "median": 200.0, "max": 200.0}},
                     layers_csv="a.layers.csv")]
        md = sc.report_md(rows, profile="parts/slice/orca/orca.json", slicer="orca")
        self.assertIn("| Grams | Cost |", md)
        self.assertIn("| a.stl | yes | 0.12 | 1h 2m 5s | 9.69 | 12.50 | 0.18 |", md)
        self.assertIn("31.0 s @ Z 0.40", md)
        self.assertIn("| Outer wall | 10m 0s | 1.29 | 200 | 200 | 200 |", md)
        self.assertIn("OrcaSlicer", md)
        self.assertIn("a.layers.csv", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
