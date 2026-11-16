# Tests for profile_lib.py (vt350#195) on synthetic members built here. Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/platform/freecad/test_profile_lib_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI (no FreeCAD there).
#
# The fixture member stands in for an imported extrusion along Z: a 20 x 20 square with a Ø4.2 bore, 200 long, its
# bore opened to Ø5 for 15 mm at the bottom end (the tapped end the real end faces show), and one Ø5.5 cross-hole
# along Y at Z 100. The "messy" profile is the same square and bore drawn the way the imports are: B-spline edges, the
# loop's vertices up to 0.004 apart, and points up to 0.002 off the plane.
import os, sys, traceback, unittest, math

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
sys.path.insert(0, HERE)
import FreeCAD, Part
import profile_lib as PL

V = FreeCAD.Vector
BORE_R, TAP_R, TAP_D, HOLE_R, L = 2.1, 2.5, 15.0, 2.75, 200.0
AREA = 400 - math.pi * BORE_R ** 2


def member():
    s = Part.makeBox(20, 20, L, V(-10, -10, 0)).cut(Part.makeCylinder(BORE_R, L, V(0, 0, 0)))
    s = s.cut(Part.makeCylinder(TAP_R, TAP_D, V(0, 0, 0)))
    s = s.cut(Part.makeCylinder(HOLE_R, 30, V(0, -15, 100), V(0, 1, 0)))
    return s.removeSplitter()


def messy_wires(z=50.0):
    """The square and the bore as B-splines with gaps and noise, on (roughly) the plane Z = z."""
    def bs(pts):
        c = Part.BSplineCurve(); c.interpolate(pts); return c.toShape()
    corners = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    jit = [(0.003, -0.002, 0.001), (-0.004, 0.0, -0.002), (0.0, 0.003, 0.002), (0.002, 0.002, -0.001)]
    outer = []
    for k in range(4):
        (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 4]
        j0, j1 = jit[k], jit[(k + 1) % 4]
        # each edge's start jittered by its own corner's offset, its end by a slightly different one: gaps <= 0.004
        p0 = V(x0 + j0[0], y0 + j0[1], z + j0[2]); p1 = V(x1 + j1[1], y1 + j1[0], z - j1[2])
        outer.append(Part.LineSegment(p0, p1).toShape())
    ring = []
    for k in range(2):                                   # the bore as two spline halves, a 0.003 gap between them
        a0, a1 = math.pi * k, math.pi * (k + 1)
        pts = [V(BORE_R * math.cos(a0 + (a1 - a0) * i / 16), BORE_R * math.sin(a0 + (a1 - a0) * i / 16),
                 z + 0.002 * math.sin(3 * i)) for i in range(17)]
        pts[-1] = pts[-1] + V(0.003, 0, 0)
        ring.append(bs(pts))
    return [Part.Wire([e]) for e in outer + ring]       # loose edges, as a slice of a broken import returns them


class CleanWires(unittest.TestCase):
    def setUp(self):
        self.f, self.rep = PL.clean_wires(messy_wires(), 2, 50.0)

    def test_exact_plane(self):
        zs = [v.Point.z for v in self.f.Vertexes] + [self.f.valueAt(*uv).z for uv in ((0.1, 0.1), (0.5, 0.7))]
        self.assertTrue(all(abs(z - 50.0) < 1e-9 for z in zs), zs)
        self.assertTrue(self.f.isValid())

    def test_lines_and_arcs_only(self):
        self.assertEqual(self.rep["spline_kept"], 0, self.rep)
        self.assertEqual(self.rep["line"], 4)
        self.assertEqual(self.rep["spline_as_arc"], 2)
        self.assertEqual(self.rep["loops"], 2)

    def test_area(self):
        # each merged vertex keeps the first point seen, so the jittered corners (<= 0.005) move the square's sides:
        # at most 80 mm of perimeter x 0.005
        self.assertAlmostEqual(self.f.Area, AREA, delta=80 * 0.005)

    def test_prism_takes_booleans(self):
        p = self.f.extrude(V(0, 0, 100))
        c = p.cut(Part.makeBox(5, 30, 10, V(-2.5, -15, 120)))
        self.assertEqual(len(c.Solids), 1)
        self.assertAlmostEqual(c.Volume, p.Volume - p.common(Part.makeBox(5, 30, 10, V(-2.5, -15, 120))).Volume, delta=1e-6)

    def test_open_loop_raises(self):
        ws = messy_wires()
        with self.assertRaises(RuntimeError):
            PL.clean_wires(ws[:1] + ws[2:], 2, 50.0)


class Rebuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = member()
        cls.out, cls.rep = PL.rebuild(cls.s)

    def test_axis_and_length(self):
        self.assertEqual(self.rep["ax"], 2)
        self.assertEqual((self.rep["lo"], self.rep["hi"]), (0.0, L))

    def test_profile_from_the_middle_not_the_tapped_end(self):
        self.assertAlmostEqual(self.rep["area"], AREA, delta=1e-6)

    def test_cross_hole_kept(self):
        self.assertEqual(self.rep["holes_kept"], self.rep["holes"])
        self.assertGreaterEqual(self.rep["holes"], 1)
        self.assertFalse(self.out.isInside(V(0, -7, 100), 1e-6, True))      # in the hole, in the wall
        self.assertTrue(self.out.isInside(V(0, -7, 104), 1e-6, True))       # beside it

    def test_volume(self):
        tap = math.pi * (TAP_R ** 2 - BORE_R ** 2) * TAP_D                 # the tap is not rebuilt
        self.assertAlmostEqual(self.out.Volume, self.s.Volume + tap, delta=0.5)
        self.assertEqual(len(self.out.Solids), 1)
        self.assertTrue(self.out.isValid())

    def test_drop(self):
        out, rep = PL.rebuild(self.s, drop=lambda h: abs(h["line"][2] - 100) < 1)
        self.assertEqual(rep["holes_kept"], 0)
        self.assertTrue(out.isInside(V(0, -7, 100), 1e-6, True))

    def test_hole_stretches(self):
        # wider than the bore, the cross-hole's wall is one stretch; narrower, the bore splits it into two
        hs = PL.cross_holes(self.s, 2)
        self.assertEqual([(round(h["lo"], 3), round(h["hi"], 3)) for h in hs], [(-10.0, 10.0)])
        s = Part.makeBox(20, 20, L, V(-10, -10, 0)).cut(Part.makeCylinder(BORE_R, L, V(0, 0, 0)))
        s = s.cut(Part.makeCylinder(1.5, 30, V(0, -15, 100), V(0, 1, 0)))
        hs = PL.cross_holes(s, 2)
        self.assertEqual(sorted((round(h["lo"], 1), round(h["hi"], 1)) for h in hs), [(-10.0, -1.5), (1.5, 10.0)])

    def test_snapped_ends(self):
        s = self.s.translated(V(0, 0, 0.004))
        _, rep = PL.rebuild(s)
        self.assertEqual((rep["lo"], rep["hi"]), (0.0, L))

    def test_sample_diff_same(self):
        bad, inside = PL.sample_diff(self.s, self.s, 2, n=300)
        self.assertEqual(bad, 0); self.assertGreater(inside, 0)


class Votes(unittest.TestCase):
    def test_prefer_breaks_a_tie(self):
        # the first 100 of 200 have a Ø6 bore, as a piece extruded from an end face would: a 4-4 tie, which the
        # earlier slice wins unless `prefer` names the true profile
        s = Part.makeBox(20, 20, L, V(-10, -10, 0)).cut(Part.makeCylinder(BORE_R, L, V(0, 0, 0)))
        s = s.cut(Part.makeCylinder(3.0, 100, V(0, 0, 0)))
        f, rep = PL.mid_profile(s, 2)
        self.assertEqual(sorted(rep["votes"].values()), [4, 4], rep["votes"])
        self.assertAlmostEqual(f.Area, 400 - math.pi * 9, delta=1e-6)
        f, rep = PL.mid_profile(s, 2, prefer={round(AREA, 2)})
        self.assertAlmostEqual(f.Area, AREA, delta=1e-6)

    def test_extension_piece_outvoted(self):
        # 200 long; the first 60 have a Ø6 bore (a lite-46-style extension made from another profile): 2 slices of 8
        s = Part.makeBox(20, 20, L, V(-10, -10, 0)).cut(Part.makeCylinder(BORE_R, L, V(0, 0, 0)))
        s = s.cut(Part.makeCylinder(3.0, 60, V(0, 0, 0)))
        f, rep = PL.mid_profile(s, 2)
        self.assertAlmostEqual(f.Area, AREA, delta=1e-6)
        self.assertEqual(len(rep["votes"]), 2, rep["votes"])


if __name__ == "__main__" or True:
    try:
        r = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(
            unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (CleanWires, Rebuild, Votes)))
        code = 0 if r.wasSuccessful() else 1
    except Exception:
        traceback.print_exc(); code = 1
    sys.stdout.flush(); os._exit(code)
