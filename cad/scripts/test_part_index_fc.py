# Tests for part_index.py's FreeCAD side (#90 AC5) on a small fixture document built here: the index's boxes are
# checked against FreeCAD's own optimal boxes and against the fixture's known geometry. Needs FreeCAD:
#
#   APP=/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage
#   $APP freecadcmd $PWD/cad/scripts/test_part_index_fc.py     # prints "Ran N tests" + "OK"/"FAILED", exit code 0/1
#
# Not in CI (no FreeCAD there); the plain-python3 side (schema, staleness, --check) is test_part_index.py, which is.
#
# Fixture (global mm). App::Part "Trident (fixture)" placed at (+100, 0, 0) and turned 90 deg about Z, so a local box
# is NOT where the index must put it. Inside it, a group "Filter (fixture)" holds:
#   lid     a box, global X 0..50 Y 0..20 Z -80..-60, material Steel-Generic
#   ring    a torus (plain BoundBox != optimal box), centre (200, 0, 0)
#   holed   Part::Cut of base (box) by tool (cylinder): base and tool are leaves too, marked consumed
# and, outside the App::Part, "loose": a box with no group (path []), XMin -5.123456 (rounds to -5.1235).
import hashlib, json, os, subprocess, sys, tempfile, traceback, unittest
import shutil

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "cad/scripts")
sys.path.insert(0, HERE)
import FreeCAD, Part, Materials
import litelib, part_index

V = FreeCAD.Vector
ROOT_PL = FreeCAD.Placement(V(100, 0, 0), FreeCAD.Rotation(V(0, 0, 1), 90))
STEEL = "90bbd8ef-8623-4d78-b3bf-e0bdb9b74dd3"
APP = os.environ.get("FREECAD_APPIMAGE", "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage")
EXPORT = os.path.join(os.path.dirname(HERE), "render", "export_meshes.py")
TOL = 1e-4                                      # the index rounds to 0.1 um


def build_fixture(path):
    doc = FreeCAD.newDocument("part_index_fixture")
    root = doc.addObject('App::Part', 'Root'); root.Label = "Trident (fixture)"; root.Placement = ROOT_PL
    grp = doc.addObject('App::DocumentObjectGroup', 'Grp'); grp.Label = "Filter (fixture)"; root.addObject(grp)

    def add(name, label, shape, into=grp):       # shape in GLOBAL coordinates, stored local to the root
        o = doc.addObject('Part::Feature', name); s = shape.copy()
        s.Placement = ROOT_PL.inverse().multiply(s.Placement)
        o.Shape = s; o.Label = label; into.addObject(o); return o

    lid = add("Lid", "lid (fixture)", litelib.box(0, 50, 0, 20, -80, -60))
    lid.ShapeMaterial = Materials.MaterialManager().getMaterial(STEEL)
    add("Ring", "ring (fixture)", Part.makeTorus(30, 5, V(200, 0, 0)))
    base = add("Base", "base (fixture)", litelib.box(-50, -10, 0, 40, 0, 10))
    tool = add("Tool", "tool (fixture)", Part.makeCylinder(5, 10, V(-30, 20, 0)))
    cut = doc.addObject('Part::Cut', 'Holed'); cut.Base = base; cut.Tool = tool; cut.Label = "holed (fixture)"
    grp.addObject(cut)
    loose = doc.addObject('Part::Feature', 'Loose'); loose.Shape = litelib.box(-5.123456, 5, -5, 5, 300, 310)
    loose.Label = "loose (fixture)"
    doc.recompute(); doc.saveAs(path); FreeCAD.closeDocument(doc.Name)


def sha(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()


def close_all():
    for d in list(FreeCAD.listDocuments()): FreeCAD.closeDocument(d)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="part-index-fc-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.master = os.path.join(cls.tmp, "fixture-master.FCStd")
        build_fixture(cls.master)

    def setUp(self):
        d = tempfile.mkdtemp(dir=self.tmp)
        self.fixture = os.path.join(d, "vt350-fixture.FCStd")
        open(self.fixture, "wb").write(open(self.master, "rb").read())
        self.work = tempfile.mkdtemp(dir=self.tmp)

    def tearDown(self): close_all()

    def index(self, p=None):
        doc = FreeCAD.openDocument(self.fixture)
        try: return part_index.index_doc(doc, self.fixture, p=p)
        finally: FreeCAD.closeDocument(doc.Name)

    def by_label(self, idx): return {p["label"]: p for p in idx["parts"]}


class IndexDoc(Base):
    def test_valid_headless_and_names_the_method_and_freecad(self):
        idx = self.index()
        self.assertEqual(part_index.validate(idx), [])
        self.assertEqual(idx["bbox"]["mode"], "headless")
        self.assertEqual(idx["bbox"]["method"], "optimalBoundingBox(True, False)")
        self.assertEqual(idx["bbox"]["freecad"], ".".join(FreeCAD.Version()[:3]))
        self.assertEqual(idx["model"], "vt350-fixture.FCStd")
        self.assertEqual(idx["source"], part_index.fingerprint(self.fixture))
        self.assertGreaterEqual(idx["seconds"], 0)

    def test_parts_are_litelibs_leaves(self):
        doc = FreeCAD.openDocument(self.fixture)
        want = sorted(o.Name for o in litelib.Model(doc).leaves)
        FreeCAD.closeDocument(doc.Name)
        self.assertEqual(sorted(p["name"] for p in self.index()["parts"]), want)
        self.assertEqual(want, ["Base", "Holed", "Lid", "Loose", "Ring", "Tool"])

    def test_boxes_match_freecads_own_optimal_boxes(self):
        idx = self.index()
        doc = FreeCAD.openDocument(self.fixture)
        for p in idx["parts"]:
            o = doc.getObject(p["name"])
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
            b = s.optimalBoundingBox(True, False)
            got = p["bbox"]
            for k, v in (("xmin", b.XMin), ("ymin", b.YMin), ("zmin", b.ZMin),
                         ("xmax", b.XMax), ("ymax", b.YMax), ("zmax", b.ZMax)):
                self.assertAlmostEqual(got[k], v, delta=TOL, msg=f"{p['label']} {k}")

    def test_boxes_are_global_not_local(self):
        lid = self.by_label(self.index())["lid (fixture)"]["bbox"]
        for k, v in dict(xmin=0, xmax=50, ymin=0, ymax=20, zmin=-80, zmax=-60).items():
            self.assertAlmostEqual(lid[k], v, delta=TOL, msg=k)

    def test_boxes_are_rounded_to_a_tenth_of_a_micron(self):
        self.assertEqual(self.by_label(self.index())["loose (fixture)"]["bbox"]["xmin"], -5.1235)

    def test_the_torus_gets_the_optimal_box_not_the_plain_one(self):
        r = self.by_label(self.index())["ring (fixture)"]["bbox"]
        for k, v in dict(xmin=165, xmax=235, ymin=-35, ymax=35, zmin=-5, zmax=5).items():
            self.assertAlmostEqual(r[k], v, delta=1e-3, msg=k)

    def test_group_path_from_the_root_down(self):
        bl = self.by_label(self.index())
        self.assertEqual(bl["lid (fixture)"]["path"], ["Trident (fixture)", "Filter (fixture)"])
        self.assertEqual(bl["loose (fixture)"]["path"], [])

    def test_material(self):
        bl = self.by_label(self.index())
        self.assertEqual(bl["lid (fixture)"]["material"], "Steel-Generic")
        self.assertEqual(bl["ring (fixture)"]["material"], "Default")

    def test_a_booleans_inputs_are_consumed_and_the_result_is_not(self):
        bl = self.by_label(self.index())
        self.assertEqual({k: v["consumed"] for k, v in bl.items()},
                         {"base (fixture)": True, "tool (fixture)": True, "holed (fixture)": False,
                          "lid (fixture)": False, "ring (fixture)": False, "loose (fixture)": False})

    def test_parts_are_sorted_by_name(self):
        names = [p["name"] for p in self.index()["parts"]]
        self.assertEqual(names, sorted(names))

    def test_parallel_workers_give_the_same_index(self):
        serial = self.index()
        p = litelib.Pass("pi", work=self.work, dry=True, workers=2)
        try: par = self.index(p=p)
        finally: p.close()
        self.assertEqual(serial["parts"], par["parts"])

    def test_gui_mode_is_recorded_and_ignores_headless_workers(self):
        class NoMap:                                 # a Pass whose workers would be headless: must not be used
            workers = 4
            def map(self, *a): raise AssertionError("GUI index used the worker pool")
        old = FreeCAD.GuiUp; FreeCAD.GuiUp = 1
        try: idx = self.index(p=NoMap())
        finally: FreeCAD.GuiUp = old
        self.assertEqual(idx["bbox"]["mode"], "gui")
        self.assertEqual(part_index.validate(idx), [])


class Refresh(Base):
    def test_writes_the_sidecar_then_skips_while_fresh(self):
        doc = FreeCAD.openDocument(self.fixture)
        self.assertEqual(part_index.refresh(doc, self.fixture), "written")
        self.assertEqual(part_index.status(self.fixture), "fresh")
        first = open(part_index.sidecar(self.fixture)).read()
        self.assertEqual(part_index.refresh(doc, self.fixture), "fresh")
        self.assertEqual(open(part_index.sidecar(self.fixture)).read(), first)
        self.assertEqual(part_index.refresh(doc, self.fixture, force=True), "written")

    def test_a_stale_sidecar_is_rewritten(self):
        doc = FreeCAD.openDocument(self.fixture)
        part_index.refresh(doc, self.fixture)
        idx = part_index.load(part_index.sidecar(self.fixture)); idx["source"]["sha256"] = "0" * 64
        json.dump(idx, open(part_index.sidecar(self.fixture), "w"))
        self.assertEqual(part_index.status(self.fixture), "stale")
        self.assertEqual(part_index.refresh(doc, self.fixture), "written")
        self.assertEqual(part_index.status(self.fixture), "fresh")

    def test_never_modifies_the_model(self):
        before = sha(self.fixture), os.stat(self.fixture).st_mtime_ns
        doc = FreeCAD.openDocument(self.fixture)
        part_index.refresh(doc, self.fixture, force=True)
        self.assertEqual((sha(self.fixture), os.stat(self.fixture).st_mtime_ns), before)


class Artifacts(Base):
    """The shipped entry points, run as the laptop runs them (a separate freecadcmd)."""
    def freecadcmd(self, script, **env):
        e = dict(os.environ, **env)
        return subprocess.run(APP.split() + ["freecadcmd", script], env=e, capture_output=True, text=True, timeout=600)

    def test_freecadcmd_entry_writes_each_models_index(self):
        second = os.path.join(os.path.dirname(self.fixture), "vt350-fixture-2.FCStd")
        open(second, "wb").write(open(self.fixture, "rb").read())
        before = sha(self.fixture)
        self.freecadcmd(os.path.join(HERE, "part_index.py"), VT350_INDEX_MODELS=f"{self.fixture}:{second}",
                        VT350_WORK=self.work, VT350_WORKERS="1")
        log = open(os.path.join(self.work, "logs", "part_index.log")).read()
        self.assertIn("part_index: done", log, log)
        self.assertNotIn("FAILED", log, log)
        for m in (self.fixture, second):
            self.assertEqual(part_index.status(m), "fresh", m)
            self.assertIn(f"written {part_index.sidecar(m)}", log)
        self.assertEqual(sha(self.fixture), before)
        self.assertEqual(self.by_label(part_index.load(part_index.sidecar(self.fixture))).keys(),
                         self.by_label(self.index()).keys())

    def test_freecadcmd_entry_skips_a_fresh_index(self):
        doc = FreeCAD.openDocument(self.fixture); part_index.refresh(doc, self.fixture); close_all()
        self.freecadcmd(os.path.join(HERE, "part_index.py"), VT350_INDEX_MODELS=self.fixture,
                        VT350_WORK=self.work, VT350_WORKERS="1")
        log = open(os.path.join(self.work, "logs", "part_index.log")).read()
        self.assertIn(f"fresh   {part_index.sidecar(self.fixture)}", log, log)
        self.assertIn("part_index: done", log, log)

    def test_freecadcmd_entry_logs_a_missing_model_as_failed(self):
        self.freecadcmd(os.path.join(HERE, "part_index.py"), VT350_INDEX_MODELS="/nonexistent/x.FCStd",
                        VT350_WORK=self.work, VT350_WORKERS="1")
        log = open(os.path.join(self.work, "logs", "part_index.log")).read()
        self.assertIn("FAILED", log); self.assertIn("no such model /nonexistent/x.FCStd", log)
        self.assertNotIn("part_index: done", log)

    def test_freecadcmd_entry_with_no_models_fails(self):
        self.freecadcmd(os.path.join(HERE, "part_index.py"), VT350_INDEX_MODELS="", VT350_WORK=self.work,
                        VT350_WORKERS="1")
        log = open(os.path.join(self.work, "logs", "part_index.log")).read()
        self.assertIn("FAILED", log); self.assertIn("no models", log); self.assertNotIn("part_index: done", log)

    def test_export_meshes_writes_the_index_beside_the_model(self):
        out = tempfile.mkdtemp(dir=self.tmp)
        self.freecadcmd(EXPORT, VT350_MODEL=self.fixture, VT350_RENDER_OUT=out, VT350_COLOURS="none")
        log = open(os.path.join(out, "export.log")).read()
        self.assertIn("] done: ", log, log)
        self.assertIn(f"index: written {part_index.sidecar(self.fixture)}", log, log)
        self.assertEqual(part_index.status(self.fixture), "fresh")
        got = part_index.load(part_index.sidecar(self.fixture))
        self.assertEqual(got["parts"], self.index()["parts"])

    def test_export_meshes_survives_an_unwritable_model_folder(self):
        d = os.path.dirname(self.fixture); out = tempfile.mkdtemp(dir=self.tmp)
        os.chmod(d, 0o555)
        try: self.freecadcmd(EXPORT, VT350_MODEL=self.fixture, VT350_RENDER_OUT=out, VT350_COLOURS="none")
        finally: os.chmod(d, 0o755)
        log = open(os.path.join(out, "export.log")).read()
        self.assertIn("] done: ", log, log)
        self.assertIn("index: FAILED", log, log)


if __name__ in ("__main__", "test_part_index_fc"):      # freecadcmd runs a script as module "test_part_index_fc"
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
