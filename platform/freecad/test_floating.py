# SPDX-License-Identifier: GPL-3.0-or-later
"""platform/freecad/floating.py: plain python, no FreeCAD."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floating import floating_starts


def box(x0, y0, z0, x1, y1, z1, pts, tris):
    """append a closed box (outward normals) to pts/tris"""
    b = len(pts)
    pts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    for t in [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6),
              (3, 0, 4), (3, 4, 7)]:
        tris.append(tuple(b + i for i in t))


class FloatingTest(unittest.TestCase):
    def test_box_on_the_bed_is_not_floating(self):
        pts, tris = [], []
        box(0, 0, 0, 10, 10, 10, pts, tris)
        assert floating_starts(pts, tris) == []


    def test_box_in_the_air_floats(self):
        pts, tris = [], []
        box(0, 0, 0, 10, 10, 10, pts, tris)
        box(20, 0, 5, 30, 10, 8, pts, tris)
        got = floating_starts(pts, tris)
        assert len(got) == 1 and abs(got[0][0] - 5) < 1e-9 and got[0][1] == (20, 30, 0, 10), got


    def test_a_downward_point_floats_and_a_pit_does_not(self):
        # an upside-down pyramid (its tip at Z 3, pointing down) floats
        pts = [(0, 0, 3), (-5, -5, 8), (5, -5, 8), (5, 5, 8), (-5, 5, 8)]
        tris = [(0, 2, 1), (0, 3, 2), (0, 4, 3), (0, 1, 4), (1, 2, 3), (1, 3, 4)]
        got = floating_starts(pts, tris)
        assert len(got) == 1 and got[0][0] == 3 and got[0][2] == 1, got
        # the same faces turned inside out (a pit: the faces point up and in) do not
        assert floating_starts(pts, [(a, c, b) for a, b, c in tris]) == []


    def test_tessellation_repeats_are_merged(self):
        pts, tris = [], []
        box(20, 0, 5, 30, 10, 8, pts, tris)
        flat = [pts[i] for t in tris for i in t]          # every face with its own copy of each vertex, as in an STL
        got = floating_starts(flat, [(i, i + 1, i + 2) for i in range(0, len(flat), 3)])
        assert len(got) == 1 and got[0][2] == 4, got


if __name__ == "__main__":
    unittest.main()
