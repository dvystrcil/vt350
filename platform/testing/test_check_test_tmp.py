#!/usr/bin/env python3
"""Tests for platform/testing/check_test_tmp.sh: a failing test file's report names the failing test and its message.

The CI log of vt350 run 43665070452 showed only "FAILED (failures=1)" for cad/render/test_render_full.py, so
finding which assertion failed meant re-running the file by hand. Each case writes a small test file to a temp
dir and runs the check on it.

Run: python3 platform/testing/test_check_test_tmp.py
"""
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_test_tmp.sh")

# Passing tests print verbose lines and ResourceWarnings before the FAIL block, which a short `tail` never reached.
NOISY_PASSES = "".join(
    f"    def test_pass_{i}(self):\n        import warnings; warnings.warn('noise {i}', ResourceWarning)\n"
    for i in range(30))


class CheckTestTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="check-test-tmp-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def check(self, name, body):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as f:
            f.write(textwrap.dedent(body))
        return subprocess.run(["bash", SCRIPT, path], capture_output=True, text=True)

    def test_a_failure_shows_the_test_name_and_its_assertion(self):
        r = self.check("test_fails.py", textwrap.dedent("""\
            import unittest
            class T(unittest.TestCase):
                def test_orphan_renders(self):
                    self.assertEqual({'renders/x.jpg'}, set(), "renders/ JPEGs the README doesn't show")
            """) + NOISY_PASSES + "unittest.main(verbosity=2)\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("FAIL: test_orphan_renders", r.stdout)
        self.assertIn("renders/ JPEGs the README doesn't show", r.stdout)
        self.assertIn("'renders/x.jpg'", r.stdout)
        self.assertNotIn("noise 0", r.stdout)
        self.assertIn("check-test-tmp: FAILED", r.stdout)

    def test_an_error_shows_the_test_name_and_the_exception(self):
        r = self.check("test_errors.py", """\
            import unittest
            class T(unittest.TestCase):
                def test_blows_up(self):
                    raise KeyError("VT350_DOCS")
            unittest.main()
            """)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ERROR: test_blows_up", r.stdout)
        self.assertIn("KeyError: 'VT350_DOCS'", r.stdout)

    def test_a_crash_before_unittest_shows_the_traceback_end(self):
        r = self.check("test_crash.py", """\
            import no_such_module_vt350
            """)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ModuleNotFoundError: No module named 'no_such_module_vt350'", r.stdout)

    def test_a_passing_file_is_clean(self):
        r = self.check("test_ok.py", """\
            import unittest
            class T(unittest.TestCase):
                def test_ok(self):
                    pass
            unittest.main()
            """)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("check-test-tmp: OK", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
