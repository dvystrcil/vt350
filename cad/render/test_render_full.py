# Tests for render_full.sh's judgement of the FreeCAD export (#90): stub FreeCAD ($VT350_APP) and a stub blender on
# PATH, so it runs anywhere, in CI too:   python3 cad/render/test_render_full.py      # "Ran N tests" + "OK"
# The export is judged by export.log, not FreeCAD's exit code. The part-index hook's "index: FAILED ..." line is
# non-fatal by design (export_meshes.py), so it must not fail the render; a real "FAILED" must.
import os, subprocess, tempfile, textwrap, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "render_full.sh")

FAKE_FREECAD = textwrap.dedent("""\
    #!/usr/bin/env python3
    import os, sys
    out = os.environ["VT350_RENDER_OUT"]
    open(os.path.join(out, "export.log"), "w").write(open(os.environ["FAKE_EXPORT_LOG"]).read())
    """)
FAKE_BLENDER = textwrap.dedent("""\
    #!/usr/bin/env python3
    import os, sys
    rest = sys.argv[sys.argv.index("--") + 1:]
    os.makedirs(rest[1], exist_ok=True)
    open(os.path.join(rest[1], "m-obico.png"), "wb").write(b"png")
    print("GPU: fake")
    """)

DONE = "[   80.0s] done: 12 buckets, 0 hidden solids skipped\n"


class RenderFull(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="render-full-test-")
        self.docs = os.path.join(self.tmp, "docs"); os.makedirs(self.docs)
        self.model = os.path.join(self.docs, "vt350-lite-99.FCStd"); open(self.model, "wb").write(b"model")
        bin_ = os.path.join(self.tmp, "bin"); os.makedirs(bin_)
        for name, text in (("freecad", FAKE_FREECAD), ("blender", FAKE_BLENDER)):
            p = os.path.join(bin_, name); open(p, "w").write(text); os.chmod(p, 0o755)
        self.log = os.path.join(self.tmp, "export.log")
        self.env = dict(os.environ, VT350_APP=os.path.join(bin_, "freecad"), VT350_DOCS=self.docs, VT350_EXTRA="",
                        PATH=bin_ + os.pathsep + os.environ["PATH"], FAKE_EXPORT_LOG=self.log)

    def render(self, log):
        open(self.log, "w").write(log)
        return subprocess.run(["bash", SCRIPT, self.model, "1"], env=self.env, capture_output=True, text=True)

    def test_a_done_log_renders(self):
        r = self.render("[    0.4s] opened m\n" + DONE)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("render_full: OK", r.stdout)

    def test_runs_go_under_the_docs_folder(self):
        self.render("[    0.4s] opened m\n" + DONE)
        self.assertEqual([d.startswith("vt350-lite-99-") for d in os.listdir(os.path.join(self.docs, "renders"))], [True])

    def test_an_index_hook_failure_does_not_fail_the_render(self):
        r = self.render("[    0.4s] opened m\n[   79.0s] index: FAILED for /x/m.FCStd: PermissionError: [Errno 13]\n" + DONE)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("render_full: OK", r.stdout)

    def test_a_real_failure_still_fails_even_with_an_index_line(self):
        r = self.render("[    0.4s] opened m\n[   79.0s] index: written /x/m.parts.json\n[   79.5s] FAILED\n"
                        "Traceback (most recent call last):\n" + DONE)
        self.assertEqual(r.returncode, 1); self.assertIn("export FAILED", r.stderr)

    def test_no_done_line_fails(self):
        r = self.render("[    0.4s] opened m\n[   79.0s] index: fresh /x/m.parts.json\n")
        self.assertEqual(r.returncode, 1); self.assertIn("export FAILED", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
