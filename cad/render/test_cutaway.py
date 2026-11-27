# SPDX-License-Identifier: GPL-3.0-or-later
"""cutaway.py: which parts the cutaway hides, cuts or keeps (plain python)."""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cutaway


def part(name, label, x0, x1):
    return {"name": name, "label": label, "bbox": {"xmin": x0, "xmax": x1, "ymin": 0, "ymax": 1, "zmin": 0, "zmax": 1}}


class OtherTool(unittest.TestCase):
    def test_other_tools_parts_hidden(self):
        for label in ("Bowden arm T2 (printed)", "Dancer sheave T0", "Arm hold T3: cable housing", "Bundle split clip T4: x",
                      "O2S USB cable slot 3 (x)", "Bowden slot 4"):
            self.assertTrue(cutaway.other_tool(label, 1), label)

    def test_own_and_shared_parts_kept(self):
        for label in ("Bowden arm T1 (printed)", "Arm hold T1: plunger", "O2S USB cable slot 2 (x)", "Bowden slot 2",
                      "Dancer stack X -324.2, section 2/3", "2040 (3)"):
            self.assertFalse(cutaway.other_tool(label, 1), label)


class Groups(unittest.TestCase):
    def test_cut_hide_keep(self):
        idx = {"parts": [part("a", "2040 long", -600, 100), part("b", "small left", -450, -420),
                         part("c", "small across", -400, -300), part("d", "right", -200, -100),
                         part("e", "Arm hold T0: wire", -440, -430)]}
        g = cutaway.groups(idx, -392.0, 1)
        self.assertEqual(set(g["clip"]), {"a"})
        self.assertEqual(set(g["hide"]), {"b", "e"})


if __name__ == "__main__":
    unittest.main()
