# Tests for dock_layout.py's analysis stage (plain python3, no FreeCAD, no numpy): extent fields built from boxes
# whose answers are known by hand. Runs anywhere, in CI too:
#   python3 cad/studies/test_dock_layout.py      # "Ran N tests" + "OK"
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dock_layout as dl


def box(lo, hi, h=1.0):
    """Extent fields of an axis-aligned box (lo, hi: (x, y, z) corners), as the FreeCAD stage writes them:
    'x' maps (y, z) cells to (xmin, xmax), 'y' maps (x, z) cells to (ymin, ymax)."""
    def cells(a, b): return range(int(a // h), int(-(-b // h)))
    fx = {(iy, iz): (lo[0], hi[0]) for iy in cells(lo[1], hi[1]) for iz in cells(lo[2], hi[2])}
    fy = {(ix, iz): (lo[1], hi[1]) for ix in cells(lo[0], hi[0]) for iz in cells(lo[2], hi[2])}
    return {"x": fx, "y": fy}


def union(*fs):
    out = {"x": {}, "y": {}}
    for f in fs:
        for ax in ("x", "y"):
            for k, (lo, hi) in f[ax].items():
                a, b = out[ax].get(k, (lo, hi)); out[ax][k] = (min(a, lo), max(b, hi))
    return out


class Sep(unittest.TestCase):
    def test_touching_offset_of_two_boxes(self):        # 10 wide box: B touches A when moved +10 in X
        a = box((0, 0, 0), (10, 5, 5))
        self.assertEqual(dl.sep(a["x"], a["x"]), 10.0)

    def test_no_shared_rows_is_none(self):              # B shifted 20 in Y never meets A along X
        a = box((0, 0, 0), (10, 5, 5))
        self.assertIsNone(dl.sep(a["x"], a["x"], du=20.0))

    def test_step_lets_b_come_closer_where_rows_differ(self):
        # A: a 10 wide base (y 0..5) with a 20 wide shelf behind it (y 5..10). B = the base alone, moved in Y.
        a = union(box((0, 0, 0), (10, 5, 5)), box((0, 5, 0), (20, 10, 5)))
        b = box((0, 0, 0), (10, 5, 5))
        self.assertEqual(dl.sep(a["x"], b["x"]), 10.0)          # level with the base
        self.assertEqual(dl.sep(a["x"], b["x"], du=5.0), 20.0)  # level with the shelf
        self.assertEqual(dl.sep(a["x"], b["x"], du=2.5), 20.0)  # half way: the part-shared cells count (safe side)

    def test_minus_side_by_flip(self):                  # A's shelf sticks out on +X only, so -X is just the base
        a = union(box((0, 0, 0), (10, 5, 5)), box((0, 5, 0), (20, 10, 5)))
        self.assertEqual(dl.sep(dl.flip(a["x"]), dl.flip(a["x"])), 20.0)
        self.assertEqual(dl.sep(a["x"], a["x"]), 20.0)


class Pitch(unittest.TestCase):
    """A dock row: every slot is the same parked tool; the carried tool and the empty shuttle move with MadMax's
    dock moves. Boxes: parked tool 50 wide (x 0..50) and 40 deep (y 0..40); the carried tool is the same box."""
    P = box((0, 0, 0), (50, 40, 30))

    def test_pitch_is_set_by_the_detach_move(self):
        r = dl.pitch(parked=self.P["x"], carried=self.P["x"], shuttle=box((20, 40, 0), (30, 60, 10))["x"],
                     detach=+5.0, attach=-6.0, toolhead_y=200.0, shuttle_y=36.0, clearance=2.0)
        self.assertEqual(r["parked"], 52.0)             # 50 wide + 2
        self.assertEqual(r["detach side"], 57.0)        # carried head 5 mm toward the neighbour: 50 + 5 + 2
        self.assertEqual(r["pitch"], 57.0)

    def test_minus_detach_mirrors(self):
        r = dl.pitch(parked=self.P["x"], carried=self.P["x"], shuttle=box((20, 40, 0), (30, 60, 10))["x"],
                     detach=-5.0, attach=-6.0, toolhead_y=200.0, shuttle_y=36.0, clearance=2.0)
        self.assertEqual(r["detach side"], 57.0)

    def test_wide_shuttle_sets_the_pitch(self):         # an empty carriage wider than the tool sets the pitch
        r = dl.pitch(parked=self.P["x"], carried=self.P["x"], shuttle=box((-20, 0, 0), (70, 60, 10))["x"],
                     detach=+5.0, attach=-6.0, toolhead_y=200.0, shuttle_y=36.0, clearance=2.0)
        self.assertEqual(r["shuttle"], 72.0)            # reaches 70 past the slot's own left edge, + 2
        self.assertEqual(r["pitch"], 72.0)


class Behind(unittest.TestCase):
    def test_y_needed_to_pass_behind_the_row(self):
        parked = box((0, 0, 0), (50, 40, 30))
        carried = box((0, -10, 0), (50, 30, 30))       # its front face is 10 in front of the parked front
        r = dl.behind(parked["y"], carried["y"], dx_range=(-100.0, 100.0), clearance=2.0)
        self.assertEqual(r["dy"], 52.0)                 # parked rear 40 - carried front -10 + 2
        self.assertIsNotNone(r["at_dx"])

    def test_tall_part_only_where_it_overlaps_in_z(self):
        # the carried part sits above the parked one (z 40..50): it never needs to go behind
        parked = box((0, 0, 0), (50, 40, 30))
        carried = box((0, -10, 40), (50, 30, 50))
        self.assertIsNone(dl.behind(parked["y"], carried["y"], dx_range=(-100.0, 100.0), clearance=2.0)["dy"])


class Tools(unittest.TestCase):
    def test_tool_count(self):
        # reach 342 wide, detach 5 inward of the outer slot: 337 for the slot centres
        self.assertEqual(dl.tool_count((-416.0, -74.0), pitch=78.4, detach=5.0), 5)
        self.assertEqual(dl.tool_count((-416.0, -74.0), pitch=84.25, detach=5.0), 5)      # 4 x 84.25 = 337
        self.assertEqual(dl.tool_count((-416.0, -74.0), pitch=84.26, detach=5.0), 4)


class Fields(unittest.TestCase):
    def test_round_trip_through_json_keys(self):
        f = box((0, 0, 0), (2, 2, 1))["x"]
        self.assertEqual(dl.load_field(dl.dump_field(f)), f)


def shifted(F, dx):
    return {k: (v[0] + dx, v[1] + dx) for k, v in F.items()}


class PairGap(unittest.TestCase):
    """pair_gap(): the nozzle distance between two neighbouring slots of any two templates. Two copies of one
    template must give pitch()'s answer, wherever the template sits in X."""
    P = box((0, 0, 0), (50, 40, 30))["x"]
    S = box((20, 40, 0), (30, 60, 10))["x"]
    K = dict(attach=-6.0, toolhead_y=200.0, shuttle_y=36.0, clearance=2.0)

    def slot(self, x, detach):
        return dict(x=25.0 + x, detach=detach, parked=shifted(self.P, x), carried=shifted(self.P, x), shuttle=shifted(self.S, x))

    def test_same_template_is_pitch(self):
        for d in (5.0, -5.0):
            p = dl.pitch(parked=self.P, carried=self.P, shuttle=self.S, detach=d, **self.K)["pitch"]
            self.assertEqual(dl.pair_gap(self.slot(0, d), self.slot(300, d), **self.K)["gap"], p)

    def test_both_detach_into_one_gap(self):          # only one head moves at a time: 5 + 50 + 2 either way
        self.assertEqual(dl.pair_gap(self.slot(0, 5.0), self.slot(-80, -5.0), **self.K)["gap"], 57.0)

    def test_both_detach_away(self):                  # nothing moves toward the gap: parked width + 2
        self.assertEqual(dl.pair_gap(self.slot(0, -5.0), self.slot(80, 5.0), **self.K)["gap"], 52.0)


class Layout(unittest.TestCase):
    def test_mixed_row_beats_a_uniform_one(self):
        # gaps: L|L 57, R|R 57, L|R 57 (both detach in), R|L 52 (both away); reach 0..215
        g = {("L", "L"): 57.0, ("R", "R"): 57.0, ("L", "R"): 57.0, ("R", "L"): 52.0}
        det = {"L": 5.0, "R": -5.0}
        rows = dl.layouts(g, det, (0.0, 215.0), 5)   # {tool count: best row or None}
        self.assertEqual(rows[4]["pattern"], "LRLR")   # L|R 57 + R|L 52 + L|R 57 = 166; neither end detaches outward
        self.assertAlmostEqual(rows[4]["needed"], 166.0)
        self.assertIsNone(rows[5])                     # best 5: 218 + a 5 mm detach pad > 215


if __name__ == "__main__":
    unittest.main()
