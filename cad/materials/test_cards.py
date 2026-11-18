#!/usr/bin/env python3
"""Every material card in cad/materials (vt350#60): plain python, no FreeCAD, in CI.
FreeCAD's own check that it loads them: test_cards_fc.py."""
import glob, json, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "platform", "freecad"))
sys.path.insert(0, HERE)
import matlib, build_cards  # noqa: E402


class Cards(unittest.TestCase):
    paths = sorted(glob.glob(os.path.join(HERE, "**", "*.FCMat"), recursive=True))
    cards = {p: matlib.read_card(p) for p in paths}
    data = json.load(open(os.path.join(HERE, "ambrosia.json")))

    def test_cards_are_the_generated_ones(self):
        """The Ambrosia cards are exactly what build_cards.py writes from ambrosia.json: no hand edits, no strays."""
        want = build_cards.cards()
        have = {os.path.relpath(p, build_cards.OUT): open(p, encoding="utf-8").read()
                for p in self.paths if p.startswith(build_cards.OUT + os.sep)}
        self.assertEqual(sorted(have), sorted(want), "run python3 cad/materials/build_cards.py")
        for rel in want: self.assertEqual(have[rel], want[rel], f"{rel}: run build_cards.py")

    def test_bought_cards_are_the_generated_ones(self):
        want = build_cards.bought_cards()
        have = {os.path.relpath(p, build_cards.OUT_BOUGHT): open(p, encoding="utf-8").read()
                for p in self.paths if p.startswith(build_cards.OUT_BOUGHT + os.sep)}
        self.assertEqual(sorted(have), sorted(want), "run python3 cad/materials/build_cards.py")
        for rel in want: self.assertEqual(have[rel], want[rel], f"{rel}: run build_cards.py")

    def test_no_card_outside_the_generated_folders(self):
        for p in self.paths:
            self.assertTrue(p.startswith((build_cards.OUT + os.sep, build_cards.OUT_BOUGHT + os.sep)), p)

    def test_each_card_names_itself_by_its_file(self):
        for p, c in self.cards.items():
            self.assertEqual(c.get("Name"), os.path.basename(p)[:-len(".FCMat")], p)

    def test_unique_uuids(self):
        u = [c.get("UUID") for c in self.cards.values()]
        self.assertTrue(all(re.fullmatch(r"[0-9a-f-]{36}", x or "") for x in u), u)
        self.assertEqual(len(u), len(set(u)))

    def test_density_and_source(self):
        no_density = {f"Ambrosia {g['grade']}" for g in self.data["grades"] if g["density_kg_m3"] is None}
        for p, c in self.cards.items():
            self.assertTrue(c.get("SourceURL", "").startswith("http") and c.get("ReferenceSource"), f"{p}: no source")
            if any(c["Name"] == n or c["Name"].startswith(n + " ") for n in no_density):
                self.assertNotIn("Density", c, p); self.assertIn("not published", c["ReferenceSource"]); continue
            m = re.fullmatch(r"([0-9.]+) kg/m\^3", c.get("Density", ""))
            self.assertTrue(m and 100 < float(m.group(1)) < 25000, f"{p}: Density {c.get('Density')!r}")

    def test_bought_density_gives_the_published_mass(self):
        # the Default solids at the card's density, plus the part's solids already in other materials
        for p in json.load(open(build_cards.BOUGHT))["parts"]:
            c = matlib.read_card(os.path.join(build_cards.OUT_BOUGHT, p["name"] + ".FCMat"))
            rho = float(re.fullmatch(r"([0-9.]+) kg/m\^3", c["Density"]).group(1))
            self.assertAlmostEqual(p["default_mm3"] * rho * 1e-6 + p["known_g"], p["mass_g"], delta=0.01, msg=p["name"])
            self.assertTrue(p["source_url"].startswith("https://") and "read 20" in p["source"], p["name"])
            self.assertIn("NOT A REAL MATERIAL", c["Description"])

    def test_every_colour_has_a_value_and_says_where_from(self):
        used = {c["colour"] for g in self.data["grades"] for c in g["colours"]}
        for n in used:
            p = self.data["palette"][n]
            self.assertRegex(p.get("rgb") or "", r"^#[0-9a-f]{6}$", n)
            self.assertTrue(p.get("basis"), n)


if __name__ == "__main__":
    unittest.main()
