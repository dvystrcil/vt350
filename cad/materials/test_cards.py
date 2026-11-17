#!/usr/bin/env python3
"""Every material card in cad/materials (vt350#60): plain python, no FreeCAD, in CI."""
import glob, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "platform", "freecad"))
import matlib  # noqa: E402


class Cards(unittest.TestCase):
    cards = {p: matlib.read_card(p) for p in sorted(glob.glob(os.path.join(HERE, "*.FCMat")))}

    def test_there_are_cards(self):
        self.assertTrue(self.cards)

    def test_each_card_names_itself_by_its_file(self):
        for p, c in self.cards.items():
            self.assertEqual(c.get("Name"), os.path.basename(p)[:-len(".FCMat")], p)

    def test_unique_uuids(self):
        u = [c.get("UUID") for c in self.cards.values()]
        self.assertTrue(all(re.fullmatch(r"[0-9a-f-]{36}", x or "") for x in u), u)
        self.assertEqual(len(u), len(set(u)))

    def test_density_and_source(self):
        for p, c in self.cards.items():
            m = re.fullmatch(r"([0-9.]+) kg/m\^3", c.get("Density", ""))
            self.assertTrue(m and 100 < float(m.group(1)) < 25000, f"{p}: Density {c.get('Density')!r}")
            self.assertTrue(c.get("SourceURL", "").startswith("http") and c.get("ReferenceSource"), f"{p}: no source")


if __name__ == "__main__":
    unittest.main()
