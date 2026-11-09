# Tests for clashlib.run's job dir: it is removed when run() returns or raises, unless the caller passed keep_dir.
# Fake workers (plain python3) stand in for freecadcmd, so these run anywhere, in CI too:
#   python3 cad/scripts/test_clashlib.py      # "Ran N tests" + "OK"
import json, os, shutil, subprocess, sys, tempfile, textwrap, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clashlib

# The worker side clashlib starts: argv is [fake, clashlib.py]; FAKE_MODE picks the outcome.
FAKE = textwrap.dedent("""\
    import json, os, sys
    mode = os.environ["FAKE_MODE"]
    out = os.environ["CLASHLIB_OUT"]
    if mode == "none": sys.exit(1)
    if mode == "hang":
        open(os.environ["FAKE_PIDS"] + os.environ["CLASHLIB_K"], "w").write(str(os.getpid()))
        import time; time.sleep(60)
    if mode == "fatal": json.dump(dict(fatal="worker blew up"), open(out, "w")); sys.exit(0)
    stats = dict(leaves=3, pairs_total=2, pair_poses=1, box_hits=0, load_s=0.1, check_s=0.1)
    json.dump(dict(results=[], errors=[], stats=stats), open(out, "w"))
    """)


def alive(pid):
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False


class JobDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="clashlib-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.temp = os.path.join(self.tmp, "temp"); os.makedirs(self.temp)    # what tempfile hands out during run()
        old_tempdir, old_cmd = tempfile.tempdir, clashlib.FREECADCMD
        def restore():
            tempfile.tempdir, clashlib.FREECADCMD = old_tempdir, old_cmd
            os.environ.pop("FAKE_MODE", None)
        self.addCleanup(restore)
        tempfile.tempdir = self.temp
        fake = os.path.join(self.tmp, "fake_worker.py"); open(fake, "w").write(FAKE)
        clashlib.FREECADCMD = [sys.executable, fake]
        self.model = os.path.join(self.tmp, "m.FCStd"); open(self.model, "wb").write(b"m")

    def run_job(self, mode, **kw):
        os.environ["FAKE_MODE"] = mode
        return clashlib.run(self.model, {"a": ["x"], "b": ["y"]}, n=2, log=lambda *a: None, **kw)

    def test_a_finished_run_removes_its_job_dir(self):
        r = self.run_job("ok")
        self.assertEqual(r["stats"]["n"], 2)
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_worker_failure_still_removes_the_job_dir(self):
        with self.assertRaisesRegex(RuntimeError, "worker blew up"):
            self.run_job("fatal")
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_worker_that_wrote_nothing_still_removes_the_job_dir(self):
        with self.assertRaisesRegex(RuntimeError, "wrote no result"):
            self.run_job("none")
        self.assertEqual(os.listdir(self.temp), [])

    def test_a_timeout_kills_the_workers_and_removes_the_job_dir(self):
        os.environ["FAKE_PIDS"] = os.path.join(self.tmp, "pid")
        self.addCleanup(os.environ.pop, "FAKE_PIDS", None)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_job("hang", timeout=2)
        self.assertEqual(os.listdir(self.temp), [])
        for k in range(2):
            pid = int(open(os.path.join(self.tmp, f"pid{k}")).read())
            self.assertFalse(alive(pid), f"worker {k} (pid {pid}) still running")

    def test_keep_dir_is_kept(self):
        keep = os.path.join(self.tmp, "keep")
        self.run_job("ok", keep_dir=keep)
        self.assertTrue(os.path.isfile(os.path.join(keep, "job.json")))
        self.assertEqual(json.load(open(os.path.join(keep, "w0.json")))["stats"]["leaves"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
