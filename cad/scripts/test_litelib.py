# Unit tests for litelib.py (#93), on a small fixture document built here from boxes. Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/cad/scripts/test_litelib.py      # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI: the workflows run plain python3 on ubuntu-latest, with no FreeCAD.
#
# Fixture (global mm), inside an App::Part "4040 ... Voron Trident" placed at (+100, 0, 0) so global placement matters:
#   backbone  X 0..100 Y 0..100 Z -10..-2, with a 4 mm wide through-slot at X 48..52 (Y 0..100)
#   bed       X 0..100 Y 0..100 Z 250..260 (inside the bed band 230..300)
#   envelope  a 1 mm cube far away, the part every no_overlap test excludes
#   post      X 90..100 Y 0..10 Z 240..600: its base is in the bed band but it reaches above it, so it is not bed
import os, sys, math, tempfile, traceback, unittest

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "cad/scripts")
sys.path.insert(0, HERE)
import FreeCAD, Part
import litelib

V = FreeCAD.Vector
OFF = V(100, 0, 0)            # the root App::Part's placement


def build_fixture(path):
    doc = FreeCAD.newDocument("litelib_fixture")
    root = doc.addObject('App::Part', 'Root'); root.Label = "4040-350x350x250 Voron Trident (fixture)"
    root.Placement = FreeCAD.Placement(OFF, FreeCAD.Rotation())

    def add(name, label, shape):           # shape given in GLOBAL coordinates, stored local to the root
        o = doc.addObject('Part::Feature', name); s = shape.copy()
        s.Placement = FreeCAD.Placement(-OFF, FreeCAD.Rotation()).multiply(s.Placement)
        o.Shape = s; o.Label = label; root.addObject(o); return o

    bb = litelib.box(0, 100, 0, 100, -10, -2).cut(litelib.box(48, 52, 0, 100, -10, -2))
    add("Backbone", "backbone-350 (fixture)", bb)
    add("Bed", "bed plate (fixture)", litelib.box(0, 100, 0, 100, 250, 260))
    add("Env", "Filter envelope (fixture)", litelib.box(500, 501, 500, 501, 500, 501))
    add("Post", "z post (fixture)", litelib.box(90, 100, 0, 10, 240, 600))   # starts in the bed band, is not bed
    doc.recompute(); doc.saveAs(path); FreeCAD.closeDocument(doc.Name)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="litelib-test-")
        cls.fixture = os.path.join(cls.tmp, "fixture.FCStd")
        build_fixture(cls.fixture)

    def setUp(self):
        self.work = tempfile.mkdtemp(dir=self.tmp)
        self.p = litelib.Pass("t", work=self.work, dry=True, workers=1)
        self.m = self.p.open(self.fixture)

    def tearDown(self):
        self.p.close()
        for d in list(FreeCAD.listDocuments()):
            FreeCAD.closeDocument(d)

    def lines(self):
        self.p.log_f.flush()
        return [l.split("] ", 1)[1].rstrip("\n") for l in open(self.p.log_path)]


class Helpers(Base):
    def test_log_lines_carry_a_timestamp_and_the_text(self):
        self.p.log("hello", 1, 2.5)
        raw = open(self.p.log_path).read().splitlines()
        self.assertRegex(raw[-1], r"^\[ *\d+\.\ds\] hello 1 2.5$")

    def test_check_logs_ok_and_fail_and_collects_failures(self):
        self.assertTrue(self.p.check(True, "good"))
        self.assertFalse(self.p.check(False, "bad"))
        self.assertEqual(self.lines()[-2:], ["ok   good", "FAIL bad"])
        self.assertEqual(self.p.errs, ["bad"])

    def test_open_logs_the_path_and_finds_leaf_solids_only(self):
        self.assertIn(f"opened {self.fixture}", self.lines())
        self.assertEqual(sorted(o.Name for o in self.m.leaves), ["Backbone", "Bed", "Env", "Post"])   # not the App::Part

    def test_shapes_are_global(self):
        b = self.m.boxes[self.m.leaf("bed plate").Name]
        self.assertAlmostEqual(b.XMin, 0.0, places=3); self.assertAlmostEqual(b.ZMin, 250.0, places=3)
        self.assertAlmostEqual(self.m.shapes["Bed"].BoundBox.XMax, 100.0, places=6)

    def test_root_and_leaf_lookup_by_label_prefix(self):
        self.assertEqual(self.m.root("4040-350x350x250 Voron Trident").Name, "Root")
        self.assertEqual(self.m.leaf("backbone-350").Name, "Backbone")
        with self.assertRaises(StopIteration): self.m.leaf("no such part")

    def test_by_label_is_global_shapes_keyed_by_label(self):
        bl = self.m.by_label()
        self.assertEqual(set(bl), {"backbone-350 (fixture)", "bed plate (fixture)", "Filter envelope (fixture)", "z post (fixture)"})
        self.assertAlmostEqual(bl["bed plate (fixture)"].BoundBox.XMin, 0.0, places=6)

    def test_vol_is_the_common_volume_and_inf_when_the_boolean_throws(self):
        self.assertAlmostEqual(self.p.vol(litelib.box(0, 2, 0, 2, 0, 2), litelib.box(1, 3, 1, 3, 1, 3)), 1.0, places=6)
        self.assertEqual(self.p.vol(litelib.box(0, 1, 0, 1, 0, 1), None), float("inf"))
        self.assertTrue(any(l.startswith("  boolean failed:") for l in self.lines()))

    def test_box_spans_the_given_ranges(self):
        b = litelib.box(1, 4, 2, 7, -3, 0).BoundBox
        self.assertEqual((b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax), (1, 4, 2, 7, -3, 0))

    def test_obb_falls_back_to_the_plain_box(self):
        class S:                                     # a shape whose optimalBoundingBox throws
            BoundBox = FreeCAD.BoundBox(0, 0, 0, 1, 1, 1)
            def optimalBoundingBox(self, *a): raise RuntimeError("no mesh")
        self.assertEqual(litelib.obb(S()).XMax, 1.0)


class OnFace(Base):
    def test_a_bottom_face_on_the_plane_passes(self):
        lip = litelib.box(10, 40, 10, 90, -2, 2)
        self.assertTrue(self.p.on_face(lip, -2.0, "lip on top", top=2.0))

    def test_wrong_height_or_wrong_top_fails(self):
        self.assertFalse(self.p.on_face(litelib.box(10, 40, 10, 90, -1.5, 2), -2.0, "floating"))
        self.assertFalse(self.p.on_face(litelib.box(10, 40, 10, 90, -2, 3), -2.0, "too thick", top=2.0))

    def test_a_top_face_on_the_plane_is_not_a_bottom_face(self):
        self.assertFalse(self.p.on_face(litelib.box(10, 40, 10, 90, -6, -2), -2.0, "hangs below"))

    def test_small_faces_do_not_count(self):
        self.assertFalse(self.p.on_face(litelib.box(10, 15, 10, 15, -2, 2), -2.0, "tiny", min_area=100))


class OverMaterial(Base):
    def test_fraction_of_the_footprint_over_material(self):
        bb = self.m.shapes["Backbone"]
        foot = litelib.box(10, 30, 10, 90, -2.5, -2)                       # all on material
        r = self.p.over_material(foot, bb, lambda r: f"full {r.frac:.0%}", min_frac=0.9)
        self.assertTrue(r); self.assertAlmostEqual(r.frac, 1.0, places=6)
        foot = litelib.box(40, 60, 10, 90, -2.5, -2)                       # 4 of 20 mm over the slot
        r = self.p.over_material(foot, bb, lambda r: f"slot {r.frac:.0%}", min_frac=0.9)
        self.assertFalse(r); self.assertAlmostEqual(r.frac, 0.8, places=6)
        self.assertEqual(self.lines()[-2:], ["ok   full 100%", "FAIL slot 80%"])


class ClearOfBedTravel(Base):
    def test_gap_to_the_bed_moved_down_by_dz(self):
        lip = litelib.box(10, 40, 10, 90, -2, 2)
        r = self.p.clear_of_bed_travel([("left", lip)], self.m, lambda r: f"gap {r.gap:.2f} ({r.who})",
                                       dz=-240.0, min_gap=5.0)
        self.assertTrue(r); self.assertAlmostEqual(r.gap, 8.0, places=3)        # 250 - 240 - 2
        self.assertEqual(r.who, "left vs bed plate (fixture)")
        r = self.p.clear_of_bed_travel([("left", lip)], self.m, "x", dz=-245.0, min_gap=5.0)
        self.assertFalse(r); self.assertAlmostEqual(r.gap, 3.0, places=3)

    def test_a_part_reaching_above_the_bed_band_is_not_bed(self):
        under_post = litelib.box(92, 95, 2, 5, -2, 2)                       # under the post AND under the bed plate
        r = self.p.clear_of_bed_travel([("u", under_post)], self.m, "x", dz=-240.0)
        self.assertAlmostEqual(r.gap, 8.0, places=3); self.assertEqual(r.who, "u vs bed plate (fixture)")

    def test_parts_outside_the_bed_footprint_are_ignored(self):
        far = litelib.box(200, 210, 10, 90, -2, 2)
        r = self.p.clear_of_bed_travel([("far", far)], self.m, "x", dz=-260.0)
        self.assertTrue(r); self.assertEqual((r.gap, r.who), (999, ""))

    def test_only_the_bed_band_moves(self):                                  # the backbone (Z -10) is not bed
        r = self.p.clear_of_bed_travel([("x", litelib.box(10, 40, 10, 90, -2, 2))], self.m, "x", dz=-240.0,
                                       bed_z=(-20, 0))
        self.assertTrue(r.gap < 0)


class NoOverlap(Base):
    def test_hits_name_the_item_and_the_printer_part(self):
        inside = litelib.box(10, 20, 10, 20, -6, 0)                         # into the backbone
        clear = litelib.box(10, 20, 10, 20, 0, 5)
        r = self.p.no_overlap([("a", inside), ("b", clear)], self.m, lambda r: f"hits {r.hits}", exclude=("Env",))
        self.assertFalse(r); self.assertEqual(r.hits, [("a", "backbone-350 (fixture)")])
        self.assertEqual(self.lines()[-1], "FAIL hits [('a', 'backbone-350 (fixture)')]")

    def test_excluded_parts_and_touching_faces_do_not_count(self):
        env = litelib.box(500, 501, 500, 501, 500, 501)
        touching = litelib.box(10, 20, 10, 20, -2, 3)                       # sits on the backbone top
        r = self.p.no_overlap([("e", env), ("t", touching)], self.m, "x", exclude=("Env",))
        self.assertTrue(r); self.assertEqual(r.hits, [])

    def test_the_volume_step_is_pluggable_for_a_parallel_runner(self):      # #45 slots in here
        seen = []
        def volumes(pairs):
            seen.extend(pairs); return [0.0 for _ in pairs]
        p = litelib.Pass("t2", work=self.work, dry=True, volumes=volumes, workers=1)
        try:
            r = p.no_overlap([("a", litelib.box(10, 20, 10, 20, -6, 0))], self.m, "x", exclude=("Env",))
        finally: p.close()
        self.assertTrue(r); self.assertEqual(len(seen), 1)                   # box prefilter left one pair


class MinDistance(Base):
    def test_lists_parts_closer_than_the_limit(self):
        s = litelib.box(0, 10, 0, 10, 0, 10)
        others = {"far": litelib.box(20, 30, 0, 10, 0, 10), "near": litelib.box(10.3, 20, 0, 10, 0, 10),
                  "skipped": litelib.box(5, 15, 0, 10, 0, 10)}
        r = self.p.min_distance(s, others, lambda r: f"{r.near} min {r.d:.2f}", min_d=0.5, skip=("skipped",))
        self.assertFalse(r); self.assertEqual(r.near, [("near", 0.3)]); self.assertAlmostEqual(r.d, 0.3, places=6)
        r = self.p.min_distance(s, {"far": others["far"]}, "x", min_d=0.5)
        self.assertTrue(r); self.assertAlmostEqual(r.d, 10.0, places=6)


class LiftOutClear(Base):
    def test_nothing_in_the_column_above_each_part(self):
        boxes = {"tray": FreeCAD.BoundBox(0, 0, 0, 10, 10, 5)}
        r = self.p.lift_out_clear(litelib.box(20, 30, 0, 10, 0, 50), boxes, lambda r: f"blocked {r.blocked}")
        self.assertTrue(r)
        r = self.p.lift_out_clear(litelib.box(5, 15, 0, 10, 40, 50), boxes, lambda r: f"blocked {r.blocked}")
        self.assertFalse(r); self.assertEqual(r.blocked, [("tray", 500.0)])

    def test_a_column_can_start_higher(self):                               # a ledge under the part is allowed
        boxes = {"tray": FreeCAD.BoundBox(0, 0, 0, 10, 10, 5)}
        ledge = litelib.box(0, 10, 0, 10, -4, 0.0)
        self.assertFalse(self.p.lift_out_clear(ledge.fuse(litelib.box(0, 10, 0, 10, 0, 0.5)), boxes, "x"))
        self.assertTrue(self.p.lift_out_clear(ledge.fuse(litelib.box(0, 10, 0, 10, 0, 0.5)), boxes, "x",
                                              start_z={"tray": 0.51}))


class FitsPrintArea(Base):
    def test_print_area_comes_from_the_sweep_log(self):
        w, d = litelib.print_area()
        self.assertTrue(300 < w <= 350 and 300 < d <= 350, (w, d))   # inside the 350 print square

    def test_flat_part_fits_either_way_round(self):
        area = (342.0, 340.19)
        r = self.p.fits_print_area(litelib.box(0, 341, 0, 100, 0, 3), lambda r: f"fits {r.size}", area=area)
        self.assertTrue(r); self.assertFalse(r.rotated)
        r = self.p.fits_print_area(litelib.box(0, 100, 0, 341, 0, 3), "x", area=(341.5, 120.0))   # needs turning
        self.assertTrue(r); self.assertTrue(r.rotated)
        r = self.p.fits_print_area(litelib.box(0, 100, 0, 100, 0, 3), "x", area=area)               # fits both ways
        self.assertTrue(r); self.assertFalse(r.rotated)

    def test_too_big_fails_and_margin_counts(self):
        self.assertFalse(self.p.fits_print_area(litelib.box(0, 343, 0, 100, 0, 3), "x", area=(342.0, 340.19)))
        self.assertFalse(self.p.fits_print_area(litelib.box(0, 340, 0, 100, 0, 3), "x", area=(342.0, 340.19), margin=2.5))
        self.assertTrue(self.p.fits_print_area(litelib.box(0, 336, 0, 100, 0, 3), "x", area=(342.0, 340.19), margin=2.5))


class LiftOutExact(Base):
    # an L-shaped part: its bounding box covers X/Y 0..10, but its material only the two arms 0..3
    L = staticmethod(lambda: litelib.box(0, 10, 0, 3, 0, 5).fuse(litelib.box(0, 3, 0, 10, 0, 5)).removeSplitter())

    def test_beside_the_material_but_inside_its_box_is_clear_with_parts(self):
        part = self.L(); boxes = {"L": part.BoundBox}
        block = litelib.box(6, 9, 6, 9, 10, 12)                              # over the L's empty corner
        self.assertFalse(self.p.lift_out_clear(block, boxes, "box only"))      # the box test flags it
        r = self.p.lift_out_clear(block, boxes, lambda r: f"exact {r.blocked}", parts={"L": part})
        self.assertTrue(r); self.assertEqual(r.blocked, [])

    def test_over_the_material_is_still_blocked_with_parts(self):
        part = self.L(); boxes = {"L": part.BoundBox}
        block = litelib.box(0.5, 2.5, 6, 9, 10, 12)                          # over the arm along Y
        r = self.p.lift_out_clear(block, boxes, "x", parts={"L": part})
        self.assertFalse(r); self.assertEqual([k for k, _ in r.blocked], ["L"])

    def test_under_an_overhang_does_not_block(self):                         # in the column, but below the material
        part = litelib.box(0, 10, 0, 3, 0, 8).fuse(litelib.box(0, 3, 0, 10, 5, 8)).removeSplitter()
        block = litelib.box(0.5, 2.5, 6, 9, 1, 3)                            # under the arm that floats at Z 5..8
        self.assertFalse(self.p.lift_out_clear(block, {"P": part.BoundBox}, "box only"))
        self.assertTrue(self.p.lift_out_clear(block, {"P": part.BoundBox}, "x", parts={"P": part}))

    def test_material_below_the_part_does_not_block(self):                   # a ledge UNDER the part is fine
        part = self.L(); boxes = {"L": part.BoundBox}
        ledge = litelib.box(0, 3, 0, 10, -4, 0)
        self.assertTrue(self.p.lift_out_clear(ledge, boxes, "x", parts={"L": part}))


class WriteAndFinish(Base):
    def test_add_solids_puts_shapes_in_the_group(self):
        doc = self.m.doc; g = doc.addObject('App::DocumentObjectGroup', 'G')
        objs = self.p.add_solids(doc, g, [("left", litelib.box(0, 1, 0, 1, 0, 1))], "Hanger", "hanger, {}")
        self.assertEqual([o.Label for o in objs], ["hanger, left"]); self.assertIn(objs[0], g.Group)

    def test_envelope_resize_is_global_through_the_root_placement(self):
        env = self.m.leaf("Filter envelope")
        nb = FreeCAD.BoundBox(10, 20, 30, 40, 50, 60)
        self.p.resize_envelope(self.m, env, nb, "Filter envelope (resized)")
        g = litelib.gshape(env).BoundBox
        self.assertEqual([round(x, 6) for x in (g.XMin, g.YMin, g.ZMin, g.XMax, g.YMax, g.ZMax)], [10, 20, 30, 40, 50, 60])
        self.assertEqual(env.Label, "Filter envelope (resized)")
        self.assertTrue(self.lines()[-1].startswith("envelope: BoundBox (10, 20, 30, 40, 50, 60)"))

    def test_finish_dry_run_never_saves(self):
        out = os.path.join(self.work, "out.FCStd")
        self.p.finish([(self.m.doc, out)])
        self.assertFalse(os.path.exists(out))
        self.assertEqual(self.lines()[-2:], ["verify: 0 problems", "DRY RUN (headless): all checks passed, not saved"])

    def test_finish_with_a_failure_never_saves_even_in_gui_mode(self):
        p = litelib.Pass("t3", work=self.work, dry=False, workers=1)
        try:
            p.check(False, "broken"); out = os.path.join(self.work, "out.FCStd")
            p.finish([(self.m.doc, out)])
            self.assertFalse(os.path.exists(out))
        finally: p.close()
        lines = [l.split("] ", 1)[1].rstrip("\n") for l in open(p.log_path)]
        self.assertEqual(lines[-3:], ["verify: 1 problems", "  broken", "NOT SAVED"])

    def test_finish_saves_each_document_in_order_when_not_dry(self):
        p = litelib.Pass("t4", work=self.work, dry=False, workers=1)
        out = os.path.join(self.work, "saved.FCStd")
        try: p.finish([(self.m.doc, out)])
        finally: p.close()
        self.assertTrue(os.path.exists(out))
        self.assertTrue(open(p.log_path).read().splitlines()[-1].split("] ", 1)[1].startswith(f"SAVED {out} "))

    def test_dump_writes_the_pass_json(self):
        self.p.dump({"a": 1})
        self.assertEqual(open(os.path.join(self.work, "logs", "t.json")).read(), '{\n "a": 1\n}')

    def test_run_logs_a_traceback_and_does_not_raise(self):
        def body(p): raise ValueError("boom")
        self.p.run(body, exit=False)
        txt = open(self.p.log_path).read()
        self.assertIn("FAILED\nTraceback", txt); self.assertIn("ValueError: boom", txt)


# ---- #45: every named check's heavy work goes through Pass.map(fn, tasks), which runs on workers when workers > 1
def L_shape():                                   # the LiftOutExact fixture's L
    return litelib.box(0, 10, 0, 3, 0, 5).fuse(litelib.box(0, 3, 0, 10, 0, 5)).removeSplitter()


class Routing(Base):
    """A spy on Pass.map: each check must hand its work to map (by op name), and use what map returns."""
    def spy(self, fake=None):
        p = litelib.Pass("spy", work=self.work, dry=True, workers=1)
        self.addCleanup(p.close)
        calls, real = [], p.map
        def m(fn, tasks):
            tasks = list(tasks)
            if tasks: calls.append((fn.__name__, len(tasks)))
            return fake(fn, tasks) if fake and fn.__name__ in fake.ops else real(fn, tasks)
        p.map = m
        return p, p.open(self.fixture), calls

    @staticmethod
    def faking(ops, f):
        f.ops = ops; return f

    def test_model_boxes_come_from_map(self):
        p, m, calls = self.spy()
        m.boxes
        self.assertEqual(calls, [("_t_obb", 4)])

    def test_clear_of_bed_travel_uses_the_mapped_boxes(self):
        lip = litelib.box(10, 40, 10, 90, -2, 2)
        fake = self.faking({"_t_obb"}, lambda fn, tasks: [(0, 0, 250, 100, 100, 251) for _ in tasks])
        p, m, calls = self.spy(fake)
        r = p.clear_of_bed_travel([("left", lip)], m, "x", dz=-240.0)
        self.assertEqual(calls, [("_t_obb", 4)])
        self.assertAlmostEqual(r.gap, 8.0, places=6)          # every leaf now looks like bed at Z 250
        self.assertEqual(len([o for o in m.leaves if m.boxes[o.Name].ZMin == 250]), 4)

    def test_no_overlap_volumes_go_through_map(self):
        fake = self.faking({"_t_vol"}, lambda fn, tasks: [5.0 for _ in tasks])
        p, m, calls = self.spy(fake)
        r = p.no_overlap([("c", litelib.box(10, 20, 10, 20, -2, 3))], m, "x", exclude=("Env",))  # touching only
        self.assertEqual(calls, [("_t_obb", 4), ("_t_vol", 1)])
        self.assertEqual(r.hits, [("c", "backbone-350 (fixture)")])        # the faked volume decided it

    def test_min_distance_goes_through_map(self):
        s = litelib.box(0, 10, 0, 10, 0, 10)
        others = {"far": litelib.box(20, 30, 0, 10, 0, 10), "skip": litelib.box(5, 6, 0, 1, 0, 1),
                  "far2": litelib.box(40, 50, 0, 10, 0, 10)}
        fake = self.faking({"_t_dist"}, lambda fn, tasks: [0.25 for _ in tasks])
        p, m, calls = self.spy(fake)
        r = p.min_distance(s, others, "x", min_d=0.5, skip=("skip",))
        self.assertEqual(calls, [("_t_dist", 2)])
        self.assertFalse(r); self.assertEqual(r.near, [("far", 0.25), ("far2", 0.25)]); self.assertEqual(r.d, 0.25)

    def test_lift_out_clear_box_stage_goes_through_map(self):
        boxes = {"tray": FreeCAD.BoundBox(0, 0, 0, 10, 10, 5), "cup": FreeCAD.BoundBox(50, 50, 0, 60, 60, 5)}
        fake = self.faking({"_t_col"}, lambda fn, tasks: [7.0 for _ in tasks])
        p, m, calls = self.spy(fake)
        r = p.lift_out_clear(litelib.box(500, 501, 500, 501, 500, 501), boxes, "x")
        self.assertEqual(calls, [("_t_col", 2)])
        self.assertEqual(r.blocked, [("tray", 7.0), ("cup", 7.0)])

    def test_lift_out_clear_exact_stage_goes_through_map(self):
        part = L_shape(); boxes = {"L": part.BoundBox}
        block = litelib.box(6, 9, 6, 9, 10, 12)                              # over the L's empty corner: clear
        fake = self.faking({"_t_above"}, lambda fn, tasks: [True for _ in tasks])
        p, m, calls = self.spy(fake)
        r = p.lift_out_clear(block, boxes, "x", parts={"L": part})
        self.assertEqual(calls, [("_t_col", 1), ("_t_above", 1)])
        self.assertFalse(r)                                                  # the faked exact stage decided it

    def test_a_failed_boolean_in_map_is_logged_and_counts_as_overlap(self):
        p, m, calls = self.spy()
        self.assertEqual(p.volumes([(litelib.box(0, 1, 0, 1, 0, 1), None)]), [float("inf")])
        self.assertTrue(self.lines_of(p)[-1].startswith("  boolean failed: "))

    def lines_of(self, p):
        p.log_f.flush()
        return [l.split("] ", 1)[1].rstrip("\n") for l in open(p.log_path)]


class Strips(Base):
    """The exact lift-out stage split into interleaved strips of grid columns gives the same answer for any split."""
    def test_any_split_matches_the_whole(self):
        part = L_shape()
        for block, want in ((litelib.box(6, 9, 6, 9, 10, 12), False), (litelib.box(0.5, 2.5, 6, 9, 10, 12), True),
                            (litelib.box(0.5, 9.5, 0.5, 9.5, 10, 12), True)):
            col = (0.0, 10.0, 0.0, 10.0, 0.0, 200.0)
            piece = block.common(litelib.box(*col))
            self.assertEqual(litelib.above_material(piece, part, 0.0, 1.0), want)
            for n in (2, 3, 7):
                got = [litelib.above_material(piece, part, 0.0, 1.0, s, n) for s in range(n)]
                self.assertEqual(any(got), want, (n, got))
                if block.BoundBox.XMax < 3 and n == 7: self.assertFalse(all(got))   # a strip is a PART of the grid

    def test_the_piece_cache_is_per_column(self):
        part = L_shape()
        blk = litelib.box(0.5, 9.5, 6, 9, 10, 12)                            # over the Y arm AND the empty corner
        self.assertTrue(litelib._t_above(blk, (0.0, 3.0, 0.0, 10.0, 0.0, 200.0), part, 0.0, 1.0))
        self.assertFalse(litelib._t_above(blk, (4.0, 10.0, 4.0, 10.0, 0.0, 200.0), part, 0.0, 1.0))

    def test_strips_cover_every_column_once(self):
        cols = []
        for n in (1, 3):
            seen = []
            for s in range(n): seen += litelib.grid_columns(0.0, 10.0, 1.0, s, n)
            cols.append(sorted(seen))
        self.assertEqual(cols[0], cols[1]); self.assertEqual(len(cols[0]), 10)


class Parallel(Base):
    """workers=2: the same checks on the same saved fixture give bit-identical results and log lines to serial."""
    def par(self, name="par"):
        p = litelib.Pass(name, work=self.work, dry=True, workers=2)
        self.addCleanup(p.close)
        return p, p.open(self.fixture)

    @staticmethod
    def lines_of(p):
        p.log_f.flush()
        return [l.split("] ", 1)[1].rstrip("\n") for l in open(p.log_path)]

    def run_checks(self, p, m):
        part = L_shape()
        out = [sorted((n, tuple((b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))) for n, b in m.boxes.items())]
        items = [("a", litelib.box(10, 20, 10, 20, -6, 0)), ("b", litelib.box(10, 20, 10, 20, 0, 5)),
                 ("c", litelib.box(91, 99, 1, 9, 255, 300))]
        out.append(p.no_overlap(items, m, lambda r: f"hits {r.hits}", exclude=("Env",)).__dict__)
        out.append(p.volumes([(s, m.shapes["Backbone"]) for _, s in items] + [(items[0][1], None)]))
        others = dict(m.by_label()); others["near"] = litelib.box(10.3, 20, 0, 10, 0, 10)
        others["near2"] = litelib.box(-5, -0.2, 0, 10, 0, 10)          # 2 pass-made shapes: a mixed map
        out.append(p.min_distance(litelib.box(0, 10, 0, 10, 0, 10), others, lambda r: f"{r.near} {r.d!r}", min_d=0.5,
                                  skip=("Filter envelope (fixture)",)).__dict__)
        out.append(p.clear_of_bed_travel(items, m, lambda r: f"gap {r.gap!r} {r.who}", dz=-240.0).__dict__)
        boxes = {"L": part.BoundBox, "tray": FreeCAD.BoundBox(20, 20, 0, 30, 30, 5)}
        for blk in (litelib.box(6, 9, 6, 9, 10, 12), litelib.box(0.5, 2.5, 6, 9, 10, 12), litelib.box(0.5, 29, 0.5, 29, 10, 12)):
            out.append(p.lift_out_clear(blk, boxes, lambda r: f"blocked {r.blocked}", parts={"L": part}).__dict__)
        return out

    def test_results_and_log_lines_are_identical_to_serial(self):
        p2, m2 = self.par()
        a, b = self.run_checks(self.p, self.m), self.run_checks(p2, m2)
        self.assertEqual(a, b)
        la, lb = self.lines(), self.lines_of(p2)
        self.assertEqual(la, lb)
        self.assertIsNotNone(p2._pool)                                       # it really ran on workers
        self.assertTrue(any(l.startswith("  boolean failed: ") for l in lb))
        self.assertEqual(p2.stale, 0)

    def test_a_shape_changed_in_memory_is_redone_in_the_parent(self):
        p2, m2 = self.par()
        self.assertIs(m2.doc, self.m.doc)                                    # openDocument: one doc per path
        bed = self.m.doc.getObject("Bed"); pl = bed.Placement; pl.Base.z += 3.0; bed.Placement = pl
        self.m.refresh(); m2.refresh()
        a, b = self.run_checks(self.p, self.m), self.run_checks(p2, m2)
        self.assertEqual(a, b)
        self.assertGreater(p2.stale, 0)                                      # the workers saw the saved file: stale

    def test_the_exact_stage_is_split_into_two_strips_per_worker(self):
        p2, m2 = self.par()
        seen, real = [], p2.map
        p2.map = lambda fn, tasks: (seen.append((fn.__name__, [t[5:] for t in tasks])), real(fn, tasks))[1]
        part = L_shape()
        r = p2.lift_out_clear(litelib.box(0.5, 2.5, 6, 9, 10, 12), {"L": part.BoundBox}, "x", parts={"L": part})
        self.assertFalse(r)
        self.assertEqual(seen[-1], ("_t_above", [(j, 4) for j in range(4)]))

    def test_shapes_of_a_big_document_stay_in_the_parent(self):        # #45: workers don't open the printer
        p2 = litelib.Pass("big", work=self.work, dry=True, workers=2, worker_doc_mb=0)
        self.addCleanup(p2.close)
        m2 = p2.open(self.fixture)                                          # any saved document is "big" at 0 MB
        self.assertEqual({n: tuple(b.XMin for _ in [0]) for n, b in m2.boxes.items()},
                         {n: tuple(b.XMin for _ in [0]) for n, b in self.m.boxes.items()})
        self.assertIsNone(p2._pool)                                         # nothing went to a worker
        part = L_shape()
        r = p2.lift_out_clear(litelib.box(0.5, 2.5, 6, 9, 10, 12), {"L": part.BoundBox}, "x", parts={"L": part})
        self.assertFalse(r); self.assertIsNotNone(p2._pool)                 # pass-made shapes still go out

    def test_mixed_big_document_and_worker_tasks_match_serial(self):
        p2 = litelib.Pass("mix", work=self.work, dry=True, workers=2, worker_doc_mb=0)
        self.addCleanup(p2.close)
        m2 = p2.open(self.fixture)
        self.assertEqual(self.run_checks(self.p, self.m), self.run_checks(p2, m2))
        self.assertEqual(self.lines(), self.lines_of(p2))

    def test_a_distance_to_a_many_faced_shape_stays_in_the_parent(self):   # #45: 10 GB for the carbon basket
        p2 = litelib.Pass("heavy", work=self.work, dry=True, workers=2, heavy_faces=6)
        self.addCleanup(p2.close)
        m2 = p2.open(self.fixture)
        s = litelib.box(0, 10, 0, 10, 0, 10)
        many = litelib.box(20, 30, 0, 10, 0, 10).fuse(litelib.box(25, 26, 2, 3, 10, 11))    # 11 faces > 6
        others = {"many": many, "box1": litelib.box(40, 50, 0, 10, 0, 10), "box2": litelib.box(60, 70, 0, 10, 0, 10)}
        r = p2.min_distance(s, others, lambda r: f"{r.near} {r.d!r}", min_d=0.5)
        self.assertEqual(r.__dict__, self.p.min_distance(s, others, lambda r: f"{r.near} {r.d!r}", min_d=0.5).__dict__)
        self.assertEqual(p2.parent_tasks, 1)                                # just the many-faced one
        p3 = litelib.Pass("heavy3", work=self.work, dry=True, workers=2, heavy_faces=6)
        self.addCleanup(p3.close)
        p3.lift_out_clear(many, {"a": FreeCAD.BoundBox(20, 0, 0, 30, 10, 5), "b": FreeCAD.BoundBox(40, 0, 0, 50, 10, 5)}, "x")
        self.assertEqual(p3.parent_tasks, 0); self.assertIsNotNone(p3._pool)  # only distances count as heavy

    def test_heavy_faces_defaults_from_env(self):
        old = os.environ.get("VT350_HEAVY_FACES")
        os.environ["VT350_HEAVY_FACES"] = "123"
        try: p = litelib.Pass("w", work=self.work, dry=True, workers=1); p.close()
        finally:
            if old is None: del os.environ["VT350_HEAVY_FACES"]
            else: os.environ["VT350_HEAVY_FACES"] = old
        self.assertEqual(p.heavy_faces, 123)
        p = litelib.Pass("w2", work=self.work, dry=True, workers=1); p.close()
        self.assertEqual(p.heavy_faces, litelib.HEAVY_FACES)

    def test_the_big_document_limit_defaults_from_env(self):
        old = os.environ.get("VT350_WORKER_DOC_MB")
        os.environ["VT350_WORKER_DOC_MB"] = "7"
        try: p = litelib.Pass("w", work=self.work, dry=True, workers=1); p.close()
        finally:
            if old is None: del os.environ["VT350_WORKER_DOC_MB"]
            else: os.environ["VT350_WORKER_DOC_MB"] = old
        self.assertEqual(p.worker_doc_mb, 7.0)
        p = litelib.Pass("w2", work=self.work, dry=True, workers=1); p.close()
        self.assertEqual(p.worker_doc_mb, litelib.WORKER_DOC_MB)

    def test_one_task_runs_in_the_parent_without_starting_workers(self):
        p2, m2 = self.par()
        p2.min_distance(litelib.box(0, 1, 0, 1, 0, 1), {"x": litelib.box(5, 6, 0, 1, 0, 1)}, "x", min_d=0.5)
        self.assertIsNone(p2._pool)

    def test_close_ends_the_workers(self):
        p2, m2 = self.par()
        p2.volumes([(litelib.box(0, 1, 0, 1, 0, 1), litelib.box(0, 2, 0, 2, 0, 2))] * 2)
        procs = list(p2._pool.procs); p2.close()
        self.assertTrue(all(pr.poll() is not None for pr in procs))
        self.assertIsNone(p2._pool)

    def test_worker_count_defaults_to_the_env_pin(self):
        old = os.environ.get("VT350_WORKERS")
        os.environ["VT350_WORKERS"] = "3"
        try:
            p = litelib.Pass("w", work=self.work, dry=True); p.close()
        finally:
            if old is None: del os.environ["VT350_WORKERS"]
            else: os.environ["VT350_WORKERS"] = old
        self.assertEqual(p.workers, 3)


if __name__ in ("__main__", "test_litelib"):        # freecadcmd runs a script as module "test_litelib"
    ok = False
    try:
        cases = [c for c in list(globals().values())
                 if isinstance(c, type) and issubclass(c, Base) and c is not Base]
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in cases)
        ok = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite).wasSuccessful()
    except Exception:
        traceback.print_exc()
    finally:
        sys.stdout.flush(); sys.stderr.flush()
        os._exit(0 if ok else 1)
