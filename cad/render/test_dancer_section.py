# SPDX-License-Identifier: GPL-3.0-or-later
"""dancer_section.py: the section drawing from step 1's JSON (plain python; fixture = a real lite-81 export)."""
import json, os, re, sys, unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dancer_section as D

NS = "{http://www.w3.org/2000/svg}"
FIX = json.load(open(os.path.join(HERE, "testdata", "dancer_section.json")))


def views(root):
    """clip id -> the <path> elements drawn in that view"""
    out = {}
    for g in root.iter(NS + "g"):
        m = re.match(r"url\(#clip_(\w)\)", g.get("clip-path", ""))
        if m:
            out.setdefault(m.group(1), []).extend(g.iter(NS + "path"))
    return out


class Drawing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = D.drawing(FIX)
        cls.root = ET.fromstring(cls.svg)
        cls.views = views(cls.root)
        cls.texts = [t.text for t in cls.root.iter(NS + "text")]

    def test_three_views_and_titles(self):
        self.assertEqual(set(self.views), {"A", "B", "C"})
        for s in "ABC":
            self.assertIn(f"SECTION {s}-{s}", self.texts)

    def test_every_cut_part_drawn(self):
        for s, cuts in FIX["sections"].items():
            filled = [p for p in self.views[s] if p.get("stroke-width") == str(D.THICK)]
            self.assertGreaterEqual(len(filled), len(cuts), s)

    def test_axle_lengthwise_not_hatched(self):
        """A-A cuts the axle along its length: no hatch; C-C cuts it across: hatched"""
        fills = {s: [p.get("fill") for p in self.views[s]] for s in "AC"}
        self.assertIn("url(#h_axle)", fills["C"])
        self.assertNotIn("url(#h_axle)", fills["A"])

    def test_touching_parts_hatch_differently(self):
        self.assertNotEqual(D.hatch_of("stack")[1], D.hatch_of("sheave1")[1])
        self.assertNotEqual(D.hatch_of("sheave0")[1], D.hatch_of("sheave1")[1])
        self.assertLess(D.hatch_of("rod0")[1][1], D.hatch_of("stack")[1][1])      # steel denser

    def test_key_dimensions_from_the_pass(self):
        k = FIX["k"]
        for label in (f"Ø{2 * k['SHEAVE_R']:.1f}", f"pitch {k['PITCH']:.0f}", f"axle {k['AXLE_L']}",
                      f"groove {k['GROOVE_W']} × {k['GROOVE_D']} deep", f"gap {k['PLATE_GAP']}"):
            self.assertIn(label, self.texts)

    def test_text_on_the_sheet(self):
        for t in self.root.iter(NS + "text"):
            x, y = float(t.get("x")), float(t.get("y"))
            self.assertTrue(0 < x < D.SHEET_W and 0 < y < D.SHEET_H, t.text)

    def test_views_do_not_overlap(self):
        rects = [(float(r.get("x")), float(r.get("y")), float(r.get("width")), float(r.get("height")))
                 for c in self.root.iter(NS + "clipPath") for r in c.iter(NS + "rect")]
        for i, a in enumerate(rects):
            self.assertTrue(a[0] + a[2] < D.SHEET_W and a[1] + a[3] < D.SHEET_H)
            for b in rects[i + 1:]:
                self.assertFalse(a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


if __name__ == "__main__":
    unittest.main()
