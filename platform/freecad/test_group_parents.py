# Tests for linkgeo.group_parents / group_path: the group path of a part, the same in export_meshes.py's scene.json
# and part_index.py's index (vt350#220). No FreeCAD: linkgeo's FreeCAD import is stubbed; the objects are fakes.
#   python3 platform/freecad/test_group_parents.py      # "Ran N tests" + "OK"
import os, sys, types, unittest

sys.modules.setdefault("FreeCAD", types.ModuleType("FreeCAD"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linkgeo


class Obj:
    def __init__(self, name, label=None, group=()):
        self.Name, self.Label, self.Group = name, label or name, list(group)


class GroupParents(unittest.TestCase):
    def test_a_group_inside_a_part_keeps_the_group(self):
        # the lite-72 case: "Front right" sits in "Monolith gantry" (a group) inside the frame's App::Part, and the
        # App::Part's Group lists it too (it comes FIRST in doc.Objects, so a first-found walk dropped the group)
        leaf = Obj("VT9", "VT9-FIB")
        corner = Obj("FR", "Front right: _Front_right", [leaf])
        gantry = Obj("G", "Monolith gantry (LDO milled, 2WD VT 9mm)", [corner])
        frame = Obj("P", "4040-350x350x250 Voron Trident v4 v33", [gantry, corner, leaf])
        par = linkgeo.group_parents([frame, gantry, corner, leaf])
        self.assertEqual(linkgeo.group_path(leaf, par),
                         ["4040-350x350x250 Voron Trident v4 v33", "Monolith gantry (LDO milled, 2WD VT 9mm)",
                          "Front right: _Front_right"])

    def test_order_of_objects_does_not_matter(self):
        leaf = Obj("L"); g = Obj("G", group=[leaf]); p = Obj("P", group=[g, leaf])
        for objs in ([p, g, leaf], [leaf, g, p], [g, p, leaf]):
            self.assertEqual(linkgeo.group_path(leaf, linkgeo.group_parents(objs)), ["P", "G"])

    def test_top_level_part_has_an_empty_path(self):
        leaf = Obj("L")
        self.assertEqual(linkgeo.group_path(leaf, linkgeo.group_parents([leaf])), [])

    def test_a_cycle_does_not_hang(self):
        a = Obj("A"); b = Obj("B", group=[a]); a.Group = [b]; leaf = Obj("L"); b.Group.append(leaf)
        par = linkgeo.group_parents([a, b, leaf])
        self.assertIn(par["L"].Name, ("B",))


if __name__ == "__main__":
    unittest.main()
