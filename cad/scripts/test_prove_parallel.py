# Tests for prove_parallel.py (#45), with a fake freecadcmd (plain python3) so they run in CI:
#   python3 cad/scripts/test_prove_parallel.py
import json, os, subprocess, sys, tempfile, textwrap, unittest
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prove_parallel as pp

# a fake "freecadcmd <pass.py>": writes <name>.log/.json in $VT350_WORK/logs; the timestamps differ per run, the text
# depends only on FAKE_TEXT (default: the same for every worker count)
FAKE = textwrap.dedent('''
    import os, sys, time, json
    work = os.environ["VT350_WORK"]; name = os.path.basename(sys.argv[-1])[:-3]
    os.makedirs(work + "/logs", exist_ok=True)
    w = os.environ.get("VT350_WORKERS", "?")
    text = os.environ.get("FAKE_TEXT_" + w, "ok   all fine")
    t = float(w) if w.isdigit() else 0
    with open(f"{work}/logs/{name}.log", "w") as f:
        f.write(f"[{t + 1:7.1f}s] opened x\\n[{t + 2:7.1f}s] {text}\\n")
        if not os.environ.get("FAKE_UNFINISHED"): f.write(f"[{t + 3:7.1f}s] DRY RUN (headless): all checks passed, not saved\\n")
    json.dump({"w": 1}, open(f"{work}/logs/{name}.json", "w"))
    if os.environ.get("FAKE_NO_LOG_" + w): os.remove(f"{work}/logs/{name}.log")
''')


class Prove(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="prove-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = os.path.join(self.tmp, "fake.py"); open(fake, "w").write(FAKE)
        self.cmd = [sys.executable, fake]
        self.scripts = os.path.join(self.tmp, "scripts"); os.makedirs(self.scripts)
        for n in ("lite28_a", "lite29_b"): open(os.path.join(self.scripts, n + ".py"), "w").write("")

    def run_pp(self, env=None, workers=3):
        old = dict(os.environ); os.environ.update(env or {})
        try: return pp.prove(["lite28_a", "lite29_b"], workers, os.path.join(self.tmp, "out"), cmd=self.cmd,
                             scripts=self.scripts, log=lambda *a: None)
        finally: os.environ.clear(); os.environ.update(old)

    def test_strip_removes_only_the_timestamp(self):
        self.assertEqual(pp.strip("[   12.3s] ok   x [1.0s]\n[ 1234.5s] FAIL y\n"), ["ok   x [1.0s]", "FAIL y"])

    def test_identical_runs_pass_and_report_both_wall_times(self):
        r = self.run_pp()
        self.assertTrue(r["ok"])
        self.assertEqual([p["name"] for p in r["passes"]], ["lite28_a", "lite29_b"])
        for p in r["passes"]:
            self.assertTrue(p["log_identical"] and p["json_identical"]); self.assertEqual(p["lines"], 3)
            self.assertGreater(p["serial_s"], 0); self.assertGreater(p["parallel_s"], 0)

    def test_serial_is_one_worker_and_parallel_is_pinned(self):
        r = self.run_pp(env={"FAKE_TEXT_1": "ok   serial", "FAKE_TEXT_3": "ok   serial"}, workers=3)
        self.assertTrue(r["ok"])
        r = self.run_pp(env={"FAKE_TEXT_1": "ok   serial", "FAKE_TEXT_3": "ok   parallel"}, workers=3)
        self.assertFalse(r["ok"]); self.assertFalse(r["passes"][0]["log_identical"])
        self.assertIn("ok   parallel", "\n".join(r["passes"][0]["diff"]))

    def test_a_run_that_wrote_no_log_fails_closed(self):
        r = self.run_pp(env={"FAKE_NO_LOG_3": "1"})
        self.assertFalse(r["ok"]); self.assertIn("no log", r["passes"][0]["error"])

    def test_identical_logs_without_the_dry_run_marker_still_fail(self):   # both crashed the same way
        r = self.run_pp(env={"FAKE_UNFINISHED": "1"})
        self.assertTrue(all(p["log_identical"] for p in r["passes"]))
        self.assertFalse(r["ok"]); self.assertIn("not finished", r["passes"][0]["error"])
        self.assertTrue(pp.finished(["opened x", "DRY RUN (headless): all checks passed, not saved"]))
        self.assertFalse(pp.finished(["opened x", "verify: 1 problems", "NOT SAVED"]))
        self.assertFalse(pp.finished(["opened x"]))

    def test_cli_exit_code(self):
        env = dict(os.environ, FREECADCMD=" ".join(self.cmd))
        out = os.path.join(self.tmp, "cli")
        a = subprocess.run([sys.executable, os.path.join(HERE, "prove_parallel.py"), "--workers", "2", "--out", out,
                            "--scripts", self.scripts, "lite28_a"], env=env, capture_output=True, text=True)
        self.assertEqual(a.returncode, 0, a.stderr); self.assertIn("IDENTICAL", a.stdout)
        self.assertTrue(os.path.exists(os.path.join(out, "summary.json")))
        env["FAKE_TEXT_2"] = "ok   other"
        b = subprocess.run([sys.executable, os.path.join(HERE, "prove_parallel.py"), "--workers", "2", "--out", out + "2",
                            "--scripts", self.scripts, "lite28_a"], env=env, capture_output=True, text=True)
        self.assertEqual(b.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
