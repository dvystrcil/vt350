# Tests for z_sweep.py's plain-python parts (#82): which documents the envelopes name, the ray-probe grid, and how
# the measured contacts become the log's limit lines. No FreeCAD (z_sweep imports it only in main), so CI runs them:
#   python3 cad/scripts/test_z_sweep.py      # "Ran N tests" + "OK"
import os, shutil, sys, tempfile, unittest, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contact, z_sweep

XML = """<?xml version='1.0' encoding='utf-8'?>
<Document>
  <Property name="Label" type="App::PropertyString" status="134217728">
      <String value="Ebox envelope (contents in vt350-ebox.FCStd)"/>
  </Property>
  <Property name="Label" type="App::PropertyString"><String value="2020 (1)"/></Property>
  <Property name="Label" type="App::PropertyString">
      <String value="Filter envelope (contents in vt350-filter-3.FCStd)"/>
  </Property>
  <Property name="Label" type="App::PropertyString"><String value="Filter envelope (contents in vt350-filter-3.FCStd)"/></Property>
  <Property name="Label" type="App::PropertyString"><String value="A &amp; B envelope (contents in a&amp;b.FCStd)"/></Property>
</Document>
"""


class Envelopes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="z-sweep-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def fcstd(self, xml, name="m.FCStd"):
        p = os.path.join(self.tmp, name)
        with zipfile.ZipFile(p, "w") as z:
            if xml is not None: z.writestr("Document.xml", xml)
            z.writestr("GuiDocument.xml", "<x/>")
        return p

    def test_labels_name_their_documents_once_in_order(self):
        labels = ["x", "Ebox envelope (contents in vt350-ebox.FCStd)", "Filter envelope (contents in vt350-filter-3.FCStd)",
                  "Ebox envelope (contents in vt350-ebox.FCStd)"]
        self.assertEqual(z_sweep.envelope_docs(labels), ["vt350-ebox.FCStd", "vt350-filter-3.FCStd"])

    def test_a_label_that_is_not_an_envelope_names_nothing(self):
        self.assertEqual(z_sweep.envelope_docs(["Filter envelope", "contents in x.FCStd", "envelope (contents in x.step)",
                                                "Filter envelope (contents in x.FCStd) old"]), [])

    def test_a_document_name_with_a_path_is_refused(self):
        for bad in ("../x.FCStd", "a/x.FCStd", "/x.FCStd"):
            with self.assertRaisesRegex(ValueError, "not a file name"):
                z_sweep.envelope_docs([f"Filter envelope (contents in {bad})"])

    def test_the_saved_file_is_read_without_freecad(self):
        self.assertEqual(z_sweep.envelope_docs_of(self.fcstd(XML)),
                         ["vt350-ebox.FCStd", "vt350-filter-3.FCStd", "a&b.FCStd"])

    def test_a_file_without_document_xml_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Document.xml"):
            z_sweep.envelope_docs_of(self.fcstd(None))

    def test_paths_are_beside_the_model(self):
        m = self.fcstd(XML, "vt350-lite-29.FCStd")
        self.assertEqual(z_sweep.envelope_paths(m), [os.path.join(self.tmp, d) for d in
                                                     ("vt350-ebox.FCStd", "vt350-filter-3.FCStd", "a&b.FCStd")])

    def test_no_envelopes(self):
        self.assertEqual(z_sweep.envelope_paths(self.fcstd("<Document/>")), [])


class Grid(unittest.TestCase):
    def test_cell_centres_cover_the_box(self):
        self.assertEqual(z_sweep.grid(0, 3, 10, 12, 1.0),
                         [(0.5, 10.5), (0.5, 11.5), (1.5, 10.5), (1.5, 11.5), (2.5, 10.5), (2.5, 11.5)])

    def test_a_box_narrower_than_a_cell_gets_its_centre_line(self):
        self.assertEqual(z_sweep.grid(0, 0.4, 0, 0.2, 1.0), [(0.2, 0.1)])
        self.assertEqual(z_sweep.grid(0, 3, 0, 0.2, 1.0), [(0.5, 0.1), (1.5, 0.1), (2.5, 0.1)])

    def test_steps_are_not_accumulated(self):
        pts = z_sweep.grid(0, 1, 0, 0.1, 0.1)
        self.assertEqual([x for x, _ in pts], [0.05 + i * 0.1 for i in range(10)])

    def test_a_partial_last_cell_is_covered(self):
        self.assertEqual(z_sweep.grid(0, 2.5, 0, 1, 1.0), [(0.5, 0.5), (1.5, 0.5), (2.25, 0.5)])   # its own centre


def hit(d, a, b):
    return (d, (a, b))


class Limits(unittest.TestCase):
    PLATE, NOZ, MAG = 285.76, "E3D v6 HotEnd - Nozzle", "Magnetic sheet (1.4 mm)"

    def up(self, d, a=None, b=None):
        return hit(d, a or self.MAG, b or self.NOZ)

    def test_the_lower_limit_is_the_first_contact(self):
        r = z_sweep.limits(self.PLATE, hit(241.98, "2020 (1)", "backbone-350 v2"),
                           [(242.1, "MGN9H (2)", "Z rail L")], {"Left": self.up(95.0)})
        self.assertEqual(r["lower"], {"dz": -241.98, "plate_top": 285.76 - 241.98,
                                      "why": "2020 (1) lands on backbone-350 v2"})
        self.assertIn(contact.line("z_lower_limit_mm", 285.76 - 241.98,
                                   "LDO plate top; bed dZ -241.98 from the model pose: 2020 (1) lands on backbone-350 v2"),
                      r["lines"])

    def test_a_rail_end_before_any_contact_is_the_lower_limit(self):
        r = z_sweep.limits(self.PLATE, hit(241.98, "2020 (1)", "backbone"),
                           [(250.0, "MGN9H (3)", "Z rail R"), (240.5, "MGN9H (2)", "Z rail L")], {"Left": self.up(95.0)})
        self.assertEqual(r["lower"]["dz"], -240.5)
        self.assertEqual(r["lower"]["why"], "the bottom end of MGN9H (2) reaches the bottom end of Z rail L")

    def test_a_tie_goes_to_the_contact(self):
        r = z_sweep.limits(self.PLATE, hit(240.5, "2020 (1)", "backbone"), [(240.5, "MGN9H (2)", "Z rail L")],
                           {"Left": self.up(95.0)})
        self.assertEqual(r["lower"]["why"], "2020 (1) lands on backbone")

    def test_rail_ends_alone_or_contact_alone(self):
        self.assertEqual(z_sweep.limits(self.PLATE, None, [(240.5, "b", "r")], {"L": self.up(9)})["lower"]["dz"], -240.5)
        self.assertEqual(z_sweep.limits(self.PLATE, hit(7, "a", "b"), [], {"L": self.up(9)})["lower"]["dz"], -7)

    def test_no_lower_limit_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "no lower limit"):
            z_sweep.limits(self.PLATE, None, [], {"L": self.up(9)})

    def test_upper_limit_and_print_height_take_the_lowest_head(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [], {"Left": self.up(95.0), "Right": self.up(94.5)})
        self.assertIn(contact.line("z_upper_limit_mm", 285.76 + 94.5,
                                   f"LDO plate top; bed dZ +94.50 from the model pose: Right head carried, "
                                   f"{self.MAG} touches {self.NOZ}"), r["lines"])
        self.assertIn(contact.line("print_height_mm", 94.5 + 240.0,
                                   "magnet-sheet top, from the lower stop to the Right nozzle"), r["lines"])
        self.assertEqual(r["upper"]["head"], "Right")
        self.assertEqual(r["print_height"], {"Left": 335.0, "Right": 334.5})
        self.assertEqual(r["problems"], [])

    def test_a_head_tie_keeps_the_first_head(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [], {"Left": self.up(95.0), "Right": self.up(95.0)})
        self.assertEqual(r["upper"]["head"], "Left")

    def test_each_head_gets_its_own_line(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [], {"Left": self.up(95.0), "Right": self.up(94.5)})
        self.assertIn("Left head carried over the centre: bed dZ +95.00, "
                      f"{self.MAG} touches {self.NOZ}; print height 335.00", r["lines"])

    def test_the_lines_parse_back(self):
        r = z_sweep.limits(self.PLATE, hit(241.98, "a", "b"), [], {"Left": self.up(95.0)})
        got = contact.parse("\n".join(r["lines"] + [contact.DONE]))
        self.assertEqual(got, {"z_lower_limit_mm": round(285.76 - 241.98, 2), "z_upper_limit_mm": round(285.76 + 95, 2),
                               "print_height_mm": 336.98})

    def test_something_touching_before_the_nozzle_is_a_problem(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [],
                           {"Left": self.up(90.0, b="Beacon RevH"), "Right": self.up(94.0, a="Heater pad")})
        self.assertEqual(len(r["problems"]), 2)
        self.assertIn("Left", r["problems"][0]); self.assertIn("Beacon RevH", r["problems"][0])
        self.assertIn("Heater pad", r["problems"][1])

    def test_a_head_that_never_touches_is_a_problem_and_has_no_height(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [], {"Left": None, "Right": self.up(94.0)})
        self.assertEqual(r["print_height"], {"Right": 334.0})
        self.assertEqual(r["upper"]["head"], "Right")
        self.assertTrue(any("Left" in p and "nothing" in p for p in r["problems"]))

    def test_no_head_touching_at_all_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "no upper limit"):
            z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [], {"Left": None})

    def test_label_prefixes_are_what_counts(self):
        r = z_sweep.limits(self.PLATE, hit(240.0, "a", "b"), [],
                           {"Left": self.up(90.0, a="Magnetic sheet (2 mm)", b="E3D v6 HotEnd - Nozzle001")})
        self.assertEqual(r["problems"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
