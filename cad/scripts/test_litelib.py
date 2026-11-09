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
        self.p = litelib.Pass("t", work=self.work, dry=True)
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
        p = litelib.Pass("t2", work=self.work, dry=True, volumes=volumes)
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
        p = litelib.Pass("t3", work=self.work, dry=False)
        try:
            p.check(False, "broken"); out = os.path.join(self.work, "out.FCStd")
            p.finish([(self.m.doc, out)])
            self.assertFalse(os.path.exists(out))
        finally: p.close()
        lines = [l.split("] ", 1)[1].rstrip("\n") for l in open(p.log_path)]
        self.assertEqual(lines[-3:], ["verify: 1 problems", "  broken", "NOT SAVED"])

    def test_finish_saves_each_document_in_order_when_not_dry(self):
        p = litelib.Pass("t4", work=self.work, dry=False)
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
