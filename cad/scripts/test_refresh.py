#!/usr/bin/env python3
"""Tests for cad/scripts/refresh.py (#69).

Run: python3 cad/scripts/test_refresh.py
"""
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("refresh", os.path.join(HERE, "refresh.py"))
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

HEADER = ("path,part,qty,stage,bom,source,repo,commit,upstream_path,sha256,license,variant,link,material,notes\n")


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Tree:
    """a tiny repo: cad/derived sources, parts/printed copies, a manifest"""

    def __init__(self, rows, files):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name
        for rel, data in files.items():
            p = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)
        self.manifest = os.path.join(self.root, "parts/printed/manifest.csv")
        os.makedirs(os.path.dirname(self.manifest), exist_ok=True)
        with open(self.manifest, "w", newline="") as f:
            f.write(HEADER + "".join(rows))

    def read(self, rel):
        with open(os.path.join(self.root, rel), "rb") as f:
            return f.read()

    def text(self):
        with open(self.manifest, newline="") as f:
            return f.read()


OLD, NEW = b"solid old\n", b"solid new\n"


def row(path, src, digest, repo="dvystrcil/vt350", extra='"a part, with a comma",1,12,X,vt350 remix'):
    return f'{path},{extra},{repo},abc123,{src},{digest},CC BY-NC-SA 4.0,,,PETG,"note, quoted"\n'


class Sync(unittest.TestCase):
    def tree(self, *a):
        t = Tree(*a); self.addCleanup(t.dir.cleanup); return t

    def test_changed_source_is_copied_and_only_its_sha_cell_changes(self):
        t = self.tree([row("vt350/d/a b.stl", "cad/derived/d/a b.stl", sha(OLD)),
                  row("vt350/d/c.stl", "cad/derived/d/c.stl", sha(OLD))],
                 {"cad/derived/d/a b.stl": NEW, "parts/printed/vt350/d/a b.stl": OLD,
                  "cad/derived/d/c.stl": OLD, "parts/printed/vt350/d/c.stl": OLD})
        before = t.text()
        changed = rf.sync_printed(t.root)
        self.assertEqual([c["path"] for c in changed], ["vt350/d/a b.stl"])
        self.assertEqual(changed[0]["old"], sha(OLD))
        self.assertEqual(changed[0]["new"], sha(NEW))
        self.assertEqual(t.read("parts/printed/vt350/d/a b.stl"), NEW)
        # byte-for-byte the same manifest except that one sha (quoting and order untouched)
        self.assertEqual(t.text(), before.replace(f"a b.stl,{sha(OLD)}", f"a b.stl,{sha(NEW)}", 1))

    def test_no_change_writes_nothing(self):
        t = self.tree([row("vt350/d/c.stl", "cad/derived/d/c.stl", sha(OLD))],
                 {"cad/derived/d/c.stl": OLD, "parts/printed/vt350/d/c.stl": OLD})
        m0 = os.stat(t.manifest).st_mtime_ns
        self.assertEqual(rf.sync_printed(t.root), [])
        self.assertEqual(os.stat(t.manifest).st_mtime_ns, m0)

    def test_upstream_rows_are_left_alone(self):
        t = self.tree([row("voron/z.stl", "STLs/z.stl", sha(OLD), repo="VoronDesign/Voron-Trident")],
                 {"parts/printed/voron/z.stl": OLD})
        self.assertEqual(rf.sync_printed(t.root), [])

    def test_missing_source_is_an_error(self):
        t = self.tree([row("vt350/d/c.stl", "cad/derived/d/gone.stl", sha(OLD))], {"parts/printed/vt350/d/c.stl": OLD})
        with self.assertRaises(rf.StepError):
            rf.sync_printed(t.root)

    def test_dry_run_reports_but_does_not_write(self):
        t = self.tree([row("vt350/d/c.stl", "cad/derived/d/c.stl", sha(OLD))],
                 {"cad/derived/d/c.stl": NEW, "parts/printed/vt350/d/c.stl": OLD})
        before = t.text()
        self.assertEqual(len(rf.sync_printed(t.root, write=False)), 1)
        self.assertEqual(t.read("parts/printed/vt350/d/c.stl"), OLD)
        self.assertEqual(t.text(), before)


class Steps(unittest.TestCase):
    def test_plan_order_and_model(self):
        names = [s.name for s in rf.plan(26, root="/r", app="/app")]
        self.assertEqual(names, ["derive_stls", "sync_printed", "check_printed", "sweep", "print_area", "test_print_area"])
        sweep = next(s for s in rf.plan(26, root="/r", app="/app") if s.name == "sweep")
        self.assertEqual(sweep.env["VT350_MODEL"], "/home/dan/Documents/VT350/vt350-lite-26.FCStd")

    def test_from_step_skips_earlier_steps(self):
        names = [s.name for s in rf.plan(26, root="/r", app="/app", start="sweep")]
        self.assertEqual(names, ["sweep", "print_area", "test_print_area"])

    def test_unknown_from_step_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.plan(26, root="/r", app="/app", start="nope")

    def test_runner_stops_at_the_first_failure_and_names_it(self):
        ran = []
        ok = rf.Step("one", cmd=[sys.executable, "-c", "pass"], log="one.log")
        bad = rf.Step("two", cmd=[sys.executable, "-c", "import sys; sys.exit(3)"], log="two.log")
        never = rf.Step("three", cmd=[sys.executable, "-c", "pass"], log="three.log")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rf.StepError) as e:
                rf.run([ok, bad, never], cwd=d, on_step=lambda s: ran.append(s.name))
        self.assertEqual(ran, ["one", "two"])
        self.assertIn("two", str(e.exception))
        self.assertIn("two.log", str(e.exception))

    def test_a_step_that_must_print_a_marker_fails_without_it(self):
        # a step can crash yet exit 0: require its completion marker in the log
        quiet = rf.Step("quiet", cmd=[sys.executable, "-c", "print('hi')"], log="q.log", marker="check-printed: OK")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rf.StepError) as e:
                rf.run([quiet], cwd=d)
        self.assertIn("marker", str(e.exception))


SWEEP = """\
[   53.0s] model /home/x/vt350-lite-26.FCStd (read-only)
[   53.0s] Left carried: nozzle tip Z 380.48; bed top dZ +93.32; nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[   53.0s] Right carried: nozzle tip Z 380.49; bed top dZ +93.32; nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[  344.3s]    Left head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  344.3s]    Left head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
[  656.3s]    Right head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  656.3s]    Right head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
"""


class Summary(unittest.TestCase):
    def test_reach_compared_with_the_previous_run(self):
        prev = SWEEP.replace("-416.0", "-418.0")
        s = rf.summary(changed=[], sweep_log=SWEEP, prev_sweep_log=prev)
        self.assertIn("0 STLs changed", s)
        self.assertIn("vt350-lite-26", s)
        self.assertIn("X -416.0 .. -74.0 (was -418.0 .. -74.0)", s)
        self.assertIn("Y -51.93 .. 370.69", s)

    def test_changed_stls_are_listed(self):
        s = rf.summary(changed=[dict(path="vt350/d/c.stl", old="a" * 64, new="b" * 64)], sweep_log=None, prev_sweep_log=None)
        self.assertIn("1 STL changed", s)
        self.assertIn("vt350/d/c.stl", s)
        self.assertIn("sweep not run", s)


class MarkersMatchTheRealTools(unittest.TestCase):
    """the markers in plan() against the output of the real scripts, not a transcription of it"""
    ROOT = os.path.dirname(os.path.dirname(HERE))

    def marker_of(self, name):
        return next(s for s in rf.plan(26, root=self.ROOT, app="/app") if s.name == name).marker

    def real_output(self, *argv):
        import subprocess
        r = subprocess.run([sys.executable, *argv], cwd=self.ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout + r.stderr

    def test_test_print_area_marker(self):
        out = self.real_output(os.path.join(HERE, "test_print_area.py"))
        self.assertRegex(out, self.marker_of("test_print_area"))

    def test_check_printed_marker(self):
        out = self.real_output(os.path.join(self.ROOT, "parts/check-printed.py"), "--root", self.ROOT)
        self.assertRegex(out, self.marker_of("check_printed"))

    def test_print_area_marker(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.real_output(os.path.join(HERE, "print_area.py"), "--out", os.path.join(d, "a.svg"))
        self.assertRegex(out, self.marker_of("print_area"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
