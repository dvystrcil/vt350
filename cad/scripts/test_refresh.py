#!/usr/bin/env python3
"""Tests for cad/scripts/refresh.py (#69).

Run: python3 cad/scripts/test_refresh.py
"""
import hashlib
import shutil
import importlib.util
import os
import re
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
        self.assertEqual(names, ["part_index", "derive_stls", "sync_printed", "check_printed", "orca_projects", "sweep", "z_sweep",
                                 "print_area", "test_print_area"])
        sweep = next(s for s in rf.plan(26, root="/r", app="/app") if s.name == "sweep")
        self.assertEqual(sweep.env["VT350_MODEL"], "/home/dan/Documents/VT350/vt350-lite-26.FCStd")

    def test_part_index_step_indexes_the_model_headless_into_the_repo_log(self):
        pi = next(s for s in rf.plan(26, root="/r", app="/app") if s.name == "part_index")
        self.assertEqual(pi.cmd, ["/app", "freecadcmd", "/r/platform/freecad/part_index.py"])
        self.assertEqual(pi.env["VT350_INDEX_MODELS"].split(":")[0], "/home/dan/Documents/VT350/vt350-lite-26.FCStd")
        self.assertEqual(pi.env["VT350_WORK"], "/r/cad/data")
        self.assertEqual(pi.marker_in, "/r/cad/data/logs/part_index.log")

    def test_part_index_step_also_indexes_the_companions(self):
        with tempfile.TemporaryDirectory() as d:
            t = 1_800_000_000
            for name, dt in (("vt350-lite-29", 0), ("vt350-filter-3", -40)):
                open(os.path.join(d, name + ".FCStd"), "wb").write(b"x"); os.utime(os.path.join(d, name + ".FCStd"), (t + dt, t + dt))
            pi = next(s for s in rf.plan(29, root="/r", app="/app", models=d) if s.name == "part_index")
        self.assertEqual(pi.env["VT350_INDEX_MODELS"], f"{d}/vt350-lite-29.FCStd:{d}/vt350-filter-3.FCStd")

    def test_order_is_the_plan_and_from_derive_stls_skips_the_index(self):
        self.assertEqual(rf.ORDER, [s.name for s in rf.plan(26, root="/r", app="/app")])
        self.assertEqual([s.name for s in rf.plan(26, root="/r", app="/app", start="derive_stls")][:2],
                         ["derive_stls", "sync_printed"])

    def test_from_step_skips_earlier_steps(self):
        names = [s.name for s in rf.plan(26, root="/r", app="/app", start="sweep")]
        self.assertEqual(names, ["sweep", "z_sweep", "print_area", "test_print_area"])

    def test_z_sweep_step_runs_headless_on_the_model_into_the_repo_log(self):        # #82
        z = next(s for s in rf.plan(26, root="/r", app="/app") if s.name == "z_sweep")
        self.assertEqual(z.cmd, ["/app", "freecadcmd", "/r/cad/studies/z_sweep.py"])
        self.assertEqual(z.env["VT350_MODEL"], "/home/dan/Documents/VT350/vt350-lite-26.FCStd")
        self.assertEqual(z.env["VT350_WORK"], "/r/cad/data")
        self.assertEqual(z.env["FREECADCMD"], "/app freecadcmd")
        self.assertEqual(z.marker_in, "/r/cad/data/logs/z_sweep.log")
        self.assertEqual(z.log, "/r/cad/data/logs/refresh_z_sweep.out")

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

    def test_a_marker_in_a_log_left_from_an_earlier_run_does_not_count(self):
        # the step crashed before rewriting its log: the old log still has the marker
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, "old.log"); open(old, "w").write("part_index: done (1 models)\n")
            os.utime(old, (1_000_000_000, 1_000_000_000))
            st = rf.Step("crashed", cmd=[sys.executable, "-c", "pass"], log="c.out", marker="part_index: done", marker_in=old)
            with self.assertRaises(rf.StepError) as e:
                rf.run([st], cwd=d)
            self.assertIn("not written by this run", str(e.exception))
            fresh = rf.Step("ok", cmd=[sys.executable, "-c", f"open({old!r}, 'w').write('part_index: done (1 models)')"],
                            log="o.out", marker="part_index: done", marker_in=old)
            rf.run([fresh], cwd=d)                                             # rewritten by the step: passes

    def test_a_step_that_must_print_a_marker_fails_without_it(self):
        # a step can crash yet exit 0: require its completion marker in the log
        quiet = rf.Step("quiet", cmd=[sys.executable, "-c", "print('hi')"], log="q.log", marker="check-printed: OK")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(rf.StepError) as e:
                rf.run([quiet], cwd=d)
        self.assertIn("marker", str(e.exception))


class Companions(unittest.TestCase):
    """the other models a lite-N pass saved with it (lite-28 -> vt350-filter-2, lite-19 -> vt350-ebox): saved within
    COMPANION_S of the lite-N, never another lite-N"""
    T = 1_800_000_000

    def folder(self, files):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        for name, dt in files.items():
            p = os.path.join(d, name); open(p, "wb").write(b"x"); os.utime(p, (self.T + dt, self.T + dt))
        return d

    def test_files_saved_with_the_model_are_companions(self):
        d = self.folder({"vt350-lite-29.FCStd": 0, "vt350-filter-3.FCStd": -40, "vt350-ebox.FCStd": 120,
                         "vt350-lite-28.FCStd": 30, "vt350-filter-2.FCStd": -3 * 3600, "vt350-good.FCStd": 86400,
                         "vt350-lite-29.parts.json": 1, "vt350-filter-3.parts.json": 2})
        self.assertEqual(rf.companions(os.path.join(d, "vt350-lite-29.FCStd")),
                         [os.path.join(d, "vt350-ebox.FCStd"), os.path.join(d, "vt350-filter-3.FCStd")])

    def test_the_window_edge(self):
        d = self.folder({"vt350-lite-29.FCStd": 0, "a.FCStd": rf.COMPANION_S, "b.FCStd": -rf.COMPANION_S - 1})
        self.assertEqual(rf.companions(os.path.join(d, "vt350-lite-29.FCStd")), [os.path.join(d, "a.FCStd")])

    def test_a_missing_model_has_none(self):
        self.assertEqual(rf.companions("/nonexistent/vt350-lite-1.FCStd"), [])


SWEEP = """\
[   53.0s] model /home/x/vt350-lite-26.FCStd (read-only)
[   53.0s] Left carried: nozzle tip Z 380.48; bed top dZ +93.32; nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[   53.0s] Right carried: nozzle tip Z 380.49; bed top dZ +93.32; nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[  344.3s]    Left head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  344.3s]    Left head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
[  656.3s]    Right head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  656.3s]    Right head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
"""


ZLOG = """\
[   80.2s] z_lower_limit_mm=43.78 (LDO plate top; bed dZ -241.98 from the model pose: 2020 (1) lands on backbone-350 v2)
[   99.0s] z_upper_limit_mm=379.10 (LDO plate top; bed dZ +93.34 from the model pose: Left head carried, x touches y)
[   99.1s] print_height_mm=335.32 (magnet-sheet top, from the lower stop to the Left nozzle)
[  120.0s] klipper_position_max_mm=335.32 (Klipper Z at the lower stop)
[  120.0s] z_negative_limit_mm=-17.15 (Klipper Z at the mechanical top)
[  120.0s] z_travel_mm=352.47 (the bed's full travel)
[  120.1s] z_sweep: done (read-only, nothing saved)
"""


class EnvelopeDocs(unittest.TestCase):
    def test_the_documents_the_envelopes_name_beside_the_model(self):       # #82: homelab ships these
        import zipfile
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        m = os.path.join(d, "vt350-lite-29.FCStd")
        with zipfile.ZipFile(m, "w") as z:
            z.writestr("Document.xml", '<Property name="Label" type="App::PropertyString">'
                                       '<String value="Ebox envelope (contents in vt350-ebox.FCStd)"/></Property>')
        self.assertEqual(rf.envelope_docs(m), [os.path.join(d, "vt350-ebox.FCStd")])


class Summary(unittest.TestCase):
    def test_z_travel_compared_with_the_previous_run(self):                   # #82
        prev = ZLOG.replace("43.78", "33.00").replace("335.32", "347.80")
        s = rf.summary([], None, None, z_log=ZLOG, prev_z_log=prev)
        self.assertIn("Z travel: plate top 43.78 .. 379.10, print height 335.32, full travel 352.47 "
                      "(Klipper Z 335.32 .. -17.15) (was 33.00 .. 379.10, 347.80, full travel 352.47)", s)

    def test_z_travel_against_a_log_from_before_the_full_travel(self):    # the committed log before #82 AC6
        old = "\n".join(l for l in ZLOG.splitlines() if not l.split("] ")[1].startswith(("klipper", "z_neg", "z_trav")))
        s = rf.summary([], None, None, z_log=ZLOG, prev_z_log=old.replace("43.78", "43.76"))
        self.assertIn("(Klipper Z 335.32 .. -17.15) (was 43.76 .. 379.10, 335.32)", s)

    def test_z_travel_without_a_usable_previous_log(self):
        s = rf.summary([], None, None, z_log=ZLOG, prev_z_log="")
        self.assertIn("Z travel: plate top 43.78 .. 379.10, print height 335.32, full travel 352.47 "
                      "(Klipper Z 335.32 .. -17.15)", s)
        self.assertNotIn("was", s.split("Z travel")[1])

    def test_z_sweep_not_run(self):
        self.assertIn("z sweep not run", rf.summary([], None, None))

    def test_reach_compared_with_the_previous_run(self):
        prev = SWEEP.replace("-416.0", "-418.0")
        s = rf.summary(changed=[], sweep_log=SWEEP, prev_sweep_log=prev)
        self.assertIn("0 STLs changed", s)
        self.assertIn("vt350-lite-26", s)
        self.assertIn("X -416.0 .. -74.0 (was -418.0 .. -74.0)", s)
        self.assertIn("Y -51.93 .. 370.69", s)

    def test_index_status_of_each_model_is_listed(self):
        s = rf.summary([], None, None, index=[("/d/vt350-lite-29.FCStd", "fresh"), ("/d/vt350-filter-3.FCStd", "stale")])
        self.assertIn("part index: vt350-lite-29 fresh, vt350-filter-3 stale", s)

    def test_changed_stls_are_listed(self):
        s = rf.summary(changed=[dict(path="vt350/d/c.stl", old="a" * 64, new="b" * 64)], sweep_log=None, prev_sweep_log=None)
        self.assertIn("1 STL changed", s)
        self.assertIn("vt350/d/c.stl", s)
        self.assertIn("sweep not run", s)


# homelab bin/gpu-batch-submit.py's output, verbatim in shape (its first line is pinned by homelab
# test_first_line_names_the_chain_id_for_vt350_refresh_py, homelab#2257)
SUBMIT_OUT = """\
started chain vt350-refresh vt350-lite-35-20261114t170000-ab12
  derive  /mnt/nfs/media/gpu-batch/vt350-lite-35-20261114t170000-ab12-derive  (status.json there is that step's record)
  sweep   /mnt/nfs/media/gpu-batch/vt350-lite-35-20261114t170000-ab12-sweep  (status.json there is that step's record)
  area    /mnt/nfs/media/gpu-batch/vt350-lite-35-20261114t170000-ab12-area  (status.json there is that step's record)
"""
CID = "vt350-lite-35-20261114t170000-ab12"


class Lane(unittest.TestCase):
    """homelab#2257: the model-reading steps (part_index, sweep, z_sweep, print_area) run on the vt350-refresh
    batch-lane chain; the laptop keeps the steps whose output is committed (derive_stls's STLs: the lane's
    tessellation differs, homelab#1961) and submits the chain first so both run at once"""

    def test_lane_plan_passes_the_guard_and_reuse_flags(self):
        plain = rf.lane_plan(35, root="/r", app="/app", models="/m")[0].cmd
        self.assertNotIn("--z-change-ok", plain); self.assertNotIn("--fresh", plain)
        both = rf.lane_plan(35, root="/r", app="/app", models="/m", z_change_ok=True, fresh=True)[0].cmd
        self.assertIn("--z-change-ok", both); self.assertIn("--fresh", both)

    def test_lane_plan_submits_then_runs_only_the_repo_writing_steps(self):
        names = [s.name for s in rf.lane_plan(35, root="/r", app="/app", models="/m", notify="dvystrcil/homelab#2257")]
        self.assertEqual(names, ["submit", "derive_stls", "sync_printed", "check_printed", "orca_projects"])

    def test_submit_step_is_the_homelab_chain_on_this_checkout_and_model(self):
        s = rf.lane_plan(35, root="/r", app="/app", models="/m", notify="dvystrcil/homelab#2257",
                         submit="/h/bin/gpu-batch-submit.py")[0]
        self.assertEqual(s.cmd, [sys.executable, "/h/bin/gpu-batch-submit.py", "chain", "vt350-refresh",
                                 "--model", "/m/vt350-lite-35.FCStd", "--models-dir", "/m", "--vt350", "/r",
                                 "--sweep-deadline", str(rf.SWEEP_DEADLINE_S), "--notify", "dvystrcil/homelab#2257"])
        self.assertEqual(s.log, "/r/cad/data/logs/refresh_submit.out")
        self.assertRegex(SUBMIT_OUT, s.marker)

    def test_without_notify_there_is_no_notify_flag(self):
        s = rf.lane_plan(35, root="/r", app="/app", models="/m", notify=None)[0]
        self.assertNotIn("--notify", s.cmd)

    def test_the_sweep_job_has_room_for_sweep_index_and_z_sweep(self):
        # lite-32 on the laptop: sweep 1114 s + z_sweep 3219 s; the sweep job runs both plus the index
        self.assertGreaterEqual(rf.SWEEP_DEADLINE_S, 7200)

    def test_chain_id_is_read_from_the_submit_output(self):
        self.assertEqual(rf.chain_id(SUBMIT_OUT), CID)
        with self.assertRaises(rf.StepError):
            rf.chain_id("chain webhook answered 500\n")


class Collect(unittest.TestCase):
    """refresh.py N --collect <chain-id>: after the chain's comment, the chain's outputs into the repo"""

    def setUp(self):
        self.work = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.work, True)
        self.root = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.root, True)
        os.makedirs(os.path.join(self.root, "cad/data/logs"))
        model = f"/work/{CID}-sweep/in/vt350-lite-35.FCStd"
        self.outputs = {
            "sweep": {"out/logs/sweep_toolhead.log": SWEEP.replace("/home/x/vt350-lite-26.FCStd", model)
                      + "[  700.0s] done (read-only, nothing saved)\n",
                      "out/logs/z_sweep.log": f"[    0.0s] model {model} (read-only)\n" + ZLOG,
                      "out/logs/z_sweep.json": '{"model": "%s"}\n' % model,
                      "out/logs/part_index.log": "[   45.2s] part_index: done (1 models)\n",
                      "out/index/vt350-lite-35.parts.json": "{}\n"},
            "area": {"out/print-area.svg": '<svg><text>Printable area on vt350-lite-35 (both heads: Left, Right)</text></svg>\n',
                     "out/refresh-summary.json": '{"printable": [342.0, 340.19], "print_area_svg_unchanged": false}\n'},
        }
        for job in ("derive", "sweep", "area"):
            self.job(job, "succeeded", "ok")
            for rel, text in self.outputs.get(job, {}).items():
                self.write(job, rel, text)

    def job(self, job, state, reason):
        d = os.path.join(self.work, f"{CID}-{job}"); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "status.json"), "w") as f:
            f.write('{"state": "%s", "reason": "%s"}' % (state, reason))

    def write(self, job, rel, text):
        p = os.path.join(self.work, f"{CID}-{job}", rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(text)

    def collect(self, n=35, cid=CID):
        return rf.collect(n, cid, root=self.root, work_root=self.work)

    def repo(self, rel):
        p = os.path.join(self.root, rel)
        return open(p).read() if os.path.isfile(p) else None

    def assert_nothing_written(self):
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "cad/data/logs"))), [])
        self.assertIsNone(self.repo("cad/data/print-area.svg"))

    def test_logs_and_svg_land_where_the_local_steps_wrote_them(self):
        got = self.collect()
        for job, rel, dest in (("sweep", "out/logs/sweep_toolhead.log", rf.SWEEP_LOG), ("sweep", "out/logs/z_sweep.log", rf.Z_LOG),
                               ("sweep", "out/logs/z_sweep.json", "cad/data/logs/z_sweep.json"),
                               ("sweep", "out/logs/part_index.log", "cad/data/logs/part_index.log"),
                               ("area", "out/print-area.svg", "cad/data/print-area.svg")):
            self.assertEqual(self.repo(dest), self.outputs[job][rel], dest)
        self.assertEqual(got["index"], [os.path.join(self.work, f"{CID}-sweep/out/index/vt350-lite-35.parts.json")])
        self.assertEqual(got["printable"], [342.0, 340.19])

    def test_a_failed_job_is_named_with_its_reason_and_nothing_is_written(self):
        self.job("sweep", "failed", "step z-sweep: exit 1")
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn(f"{CID}-sweep", str(e.exception)); self.assertIn("step z-sweep: exit 1", str(e.exception))
        self.assert_nothing_written()

    def test_a_chain_still_running_is_not_finished(self):
        os.remove(os.path.join(self.work, f"{CID}-area", "status.json"))
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn("not finished", str(e.exception))
        self.assert_nothing_written()

    def test_a_log_without_its_completion_marker_is_refused(self):
        # the runner's own checks passed, but a log copied here must still end the way the local step's must
        self.write("sweep", "out/logs/z_sweep.log", ZLOG.replace("z_sweep: done", "z_sweep: FAILED"))
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn("z_sweep.log", str(e.exception))
        self.assert_nothing_written()

    def test_a_missing_output_is_refused(self):
        os.remove(os.path.join(self.work, f"{CID}-sweep", "out/logs/z_sweep.json"))
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn("z_sweep.json", str(e.exception))
        self.assert_nothing_written()

    def test_a_chain_without_a_part_index_is_refused(self):
        os.remove(os.path.join(self.work, f"{CID}-sweep", "out/index/vt350-lite-35.parts.json"))
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn("no part index", str(e.exception))
        self.assert_nothing_written()

    def test_a_chain_of_another_model_is_refused(self):
        with self.assertRaises(rf.StepError) as e:
            self.collect(n=34)
        self.assertIn(f"{CID} is not a chain of vt350-lite-34", str(e.exception))
        self.assert_nothing_written()

    def test_a_sweep_of_another_model_is_refused_even_under_the_right_id(self):
        self.write("sweep", "out/logs/sweep_toolhead.log",
                   self.outputs["sweep"]["out/logs/sweep_toolhead.log"].replace("vt350-lite-35.FCStd", "vt350-lite-34.FCStd"))
        with self.assertRaises(rf.StepError) as e:
            self.collect()
        self.assertIn("sweep_toolhead.log", str(e.exception))
        self.assert_nothing_written()

    def test_the_last_submitted_chain_is_the_default(self):
        with open(os.path.join(self.root, "cad/data/logs/refresh_submit.out"), "w") as f:
            f.write(SUBMIT_OUT)
        self.assertEqual(rf.last_chain_id(self.root), CID)
        os.remove(os.path.join(self.root, "cad/data/logs/refresh_submit.out"))
        with self.assertRaises(rf.StepError):
            rf.last_chain_id(self.root)

    def test_collect_plan_adopts_the_index_and_tests_the_print_area_locally(self):
        steps = rf.collect_plan(["/w/x.parts.json"], root="/r", models="/m")
        self.assertEqual([s.name for s in steps], ["adopt_index", "test_print_area"])
        self.assertEqual(steps[0].cmd, [sys.executable, "/r/platform/freecad/part_index.py", "--adopt", "--models", "/m",
                                        "/w/x.parts.json"])


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        import subprocess
        return subprocess.run([sys.executable, os.path.join(HERE, "refresh.py"), *argv], capture_output=True, text=True)

    # parse_args only: a red run of the old main() with these argv would start the real steps (a FreeCAD sweep)
    def parse_error(self, *argv):
        import contextlib, io
        err = io.StringIO()
        with self.assertRaises(SystemExit) as e, contextlib.redirect_stderr(err):
            rf.parse_args(list(argv))
        self.assertEqual(e.exception.code, 2)
        return err.getvalue()

    def test_from_needs_local(self):
        # --from picks among the all-local steps; the lane run has its own fixed four
        self.assertIn("--local", self.parse_error("35", "--from", "sweep"))
        self.assertEqual(rf.parse_args(["35", "--local", "--from", "sweep"]).start, "sweep")

    def test_collect_and_local_are_exclusive(self):
        self.parse_error("35", "--local", "--collect", CID)

    def test_collect_without_an_id_means_the_last_submitted(self):
        self.assertEqual(rf.parse_args(["35", "--collect"]).collect, "")
        self.assertIsNone(rf.parse_args(["35"]).collect)

    def test_lane_dry_run_lists_the_submit_and_the_local_steps(self):
        r = self.run_cli("35", "--dry-run", "--notify", "dvystrcil/homelab#2257")
        self.assertEqual(r.returncode, 0, r.stderr)
        names = [l.split()[0] for l in r.stdout.splitlines() if l and not l.startswith("would")]
        self.assertEqual(names, ["submit", "derive_stls", "sync_printed", "check_printed", "orca_projects"])
        self.assertIn("chain vt350-refresh", r.stdout)


class ToolModules(unittest.TestCase):
    """main() loads part_index for the summary from where TOOLS says it lives (it moved to platform/ in #132 and the
    summary kept the old path: lite-31's refresh ran every step, then died on FileNotFoundError)"""
    def test_part_index_loads_for_the_summary(self):
        pi = rf.load_tool("part_index")
        self.assertTrue(callable(pi.status))

    def test_every_tool_path_exists(self):
        root = os.path.dirname(os.path.dirname(HERE))
        for name, path in rf.TOOLS.items():
            self.assertTrue(os.path.isfile(os.path.join(root, path)), (name, path))


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
        out = self.real_output(os.path.join(self.ROOT, "cad/studies/test_print_area.py"))
        self.assertRegex(out, self.marker_of("test_print_area"))

    def test_check_printed_marker(self):
        out = self.real_output(os.path.join(self.ROOT, "platform/parts/check-printed.py"), "--root", self.ROOT)
        self.assertRegex(out, self.marker_of("check_printed"))

    def test_orca_projects_marker(self):
        # --check prints the same last line as a generating run, without needing Orca
        out = self.real_output(os.path.join(self.ROOT, "platform/parts/orca_projects.py"),
                               os.path.join(self.ROOT, "parts/slice/sets.json"), "--check")
        self.assertRegex(out, self.marker_of("orca_projects"))

    def test_part_index_marker(self):
        # needs FreeCAD to produce, so: the committed log of a real run (cad/data/logs/part_index.log, 2026-11-09)
        log = open(os.path.join(self.ROOT, "cad/data/logs/part_index.log")).read()
        self.assertRegex(log, self.marker_of("part_index"))
        self.assertNotRegex("[  1.0s] FAILED\nTraceback ... platform/freecad/part_index.py, in run\n", self.marker_of("part_index"))

    def test_z_sweep_marker(self):
        # z_sweep needs FreeCAD; its last line is contact.DONE, logged by a litelib Pass (timestamp prefix)
        sys.path.insert(0, os.path.join(self.ROOT, "platform/freecad")); import contact
        self.assertRegex(f"[  99.2s] {contact.DONE}\n", self.marker_of("z_sweep"))
        self.assertNotRegex("[  9.0s] FAILED\nTraceback ...\n", self.marker_of("z_sweep"))
        self.assertNotRegex(f"[  9.0s] {contact.DONE} or not\n", self.marker_of("z_sweep"))
        # and the committed log of a real run (batch lane, lite-29, 2026-11-09) passes it and parses
        log = open(os.path.join(self.ROOT, "cad/data/logs/z_sweep.log")).read()
        self.assertRegex(log, self.marker_of("z_sweep"))
        z = contact.parse(log)
        # the config carries the configured floor the committed log measured (user 2026-11-09); it is in the generated
        # cad/klipper/cad_values.cfg since vt350#294
        cfg = open(os.path.join(self.ROOT, "cad/klipper/cad_values.cfg")).read()
        pm = re.search(r"(?ms)^\[stepper_z\]\n.*?^position_max:\s*([0-9.]+)", cfg)  # [stepper_z]'s, not the first
        want = re.findall(r"klipper_position_max_configured_mm=([0-9.]+)", log)
        self.assertTrue(pm and want, (pm, want))
        self.assertEqual(float(pm.group(1)), float(want[-1]))
        self.assertEqual((z["z_lower_limit_mm"], z["klipper_position_max_mm"], z["z_negative_limit_mm"], z["z_travel_mm"]),
                         (43.76, 334.43, -21.17, 355.6))   # lite-77: Z0 on the 1.0 mm PEI sheet

    def test_print_area_marker(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.real_output(os.path.join(self.ROOT, "cad/studies/print_area.py"), "--out", os.path.join(d, "a.svg"))
        self.assertRegex(out, self.marker_of("print_area"))



class SkipUnchanged(unittest.TestCase):
    """#324: a link whose inputs match its last successful run is reused; --fresh forces a link and its downstream."""

    def setUp(self):
        import json
        self.json = json
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root = self.tmp.name
        self.models = os.path.join(self.root, "models"); os.makedirs(self.models)
        for rel in ("cad/studies/sweep_toolhead.py", "cad/studies/z_sweep.py", "cad/studies/print_area.py"):
            p = os.path.join(self.root, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write("# v1\n")
        self.record = os.path.join(self.root, "cad/data/logs/refresh_inputs.json")

    def index(self, n, x=0.0):
        parts = [{"name": "a", "label": "2040 (1)", "material": "Aluminum",
                  "bbox": {"xmin": x, "xmax": x + 40, "ymin": 0, "ymax": 20, "zmin": 0, "zmax": 500}}]
        self.json.dump({"parts": parts}, open(os.path.join(self.models, f"vt350-lite-{n}.parts.json"), "w"))

    def gate(self, n, fresh=None):
        return rf.Gate(n, root=self.root, models=self.models, fresh=fresh, record=self.record)

    def ran(self, g, names):
        for name in names:
            s = rf.Step(name)
            if not g(s): g.done(s)
        return {k: v[0] for k, v in g.verdicts.items()}

    def test_skip_colour_only_pass_reuses_the_sweeps(self):
        self.index(78); self.index(79)                       # lite-79: colours only, the same boxes
        first = self.ran(self.gate(78), ["sweep", "z_sweep"])
        self.assertEqual(first, {"sweep": "run", "z_sweep": "run"})
        self.assertEqual(self.ran(self.gate(79), ["sweep", "z_sweep"]), {"sweep": "reused", "z_sweep": "reused"})

    def test_skip_moved_part_reruns(self):
        self.index(78); self.index(80, x=3.0)
        self.ran(self.gate(78), ["sweep"])
        self.assertEqual(self.ran(self.gate(80), ["sweep"]), {"sweep": "run"})

    def test_skip_code_change_reruns(self):
        self.index(78); self.ran(self.gate(78), ["sweep"])
        open(os.path.join(self.root, "cad/studies/sweep_toolhead.py"), "w").write("# v2\n")
        self.assertEqual(self.ran(self.gate(78), ["sweep"]), {"sweep": "run"})

    def test_skip_test_files_and_driver_dont_count(self):
        self.index(78); self.ran(self.gate(78), ["sweep"])
        p = os.path.join(self.root, "cad/scripts"); os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "test_new.py"), "w").write("x"); open(os.path.join(p, "refresh.py"), "w").write("x")
        self.assertEqual(self.ran(self.gate(78), ["sweep"]), {"sweep": "reused"})

    def test_skip_fresh_forces_link_and_downstream(self):
        self.index(78)
        self.ran(self.gate(78), ["sweep", "z_sweep", "print_area", "test_print_area"])
        got = self.ran(self.gate(78, fresh=["z_sweep"]), ["sweep", "z_sweep", "print_area", "test_print_area"])
        self.assertEqual(got, {"sweep": "reused", "z_sweep": "forced", "print_area": "forced", "test_print_area": "forced"})
        got = self.ran(self.gate(78, fresh=[]), ["sweep"])
        self.assertEqual(got, {"sweep": "forced"})

    def test_skip_every_link_declared(self):
        decl = rf.inputs(80, root=self.root, models=self.models)
        self.assertEqual(sorted(decl), sorted(rf.ORDER))
        self.assertEqual(sorted(rf.DEPS), sorted(rf.ORDER))

    def test_skip_failed_link_not_recorded(self):
        self.index(78)
        g = self.gate(78); s = rf.Step("sweep")
        self.assertFalse(g(s))                               # it would run; it fails, so done() is never called
        self.assertEqual(self.ran(self.gate(78), ["sweep"]), {"sweep": "run"})

if __name__ == "__main__":
    unittest.main(verbosity=2)
