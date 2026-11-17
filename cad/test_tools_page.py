#!/usr/bin/env python3
"""cad/tools.md lists every in-repo tool pin exactly as pinned (#124): runs cad/check-tools-page.sh, and checks it
fails when a pin changes without the page. Plain python3, in CI."""
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "check-tools-page.sh")


class TheToolsPage(unittest.TestCase):
    def test_every_pin_is_on_the_page(self):
        r = subprocess.run(["bash", SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "check-tools-page: OK")

    def test_a_changed_pin_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            for d in ("cad", "platform/kalisim", ".github/workflows", "platform"):
                os.makedirs(os.path.join(tmp, d), exist_ok=True)
            shutil.copy(SCRIPT, os.path.join(tmp, "cad"))
            shutil.copy(os.path.join(HERE, "tools.md"), os.path.join(tmp, "cad"))
            shutil.copy(os.path.join(ROOT, "platform", "README.md"), os.path.join(tmp, "platform"))
            for f in os.listdir(os.path.join(ROOT, ".github", "workflows")):
                shutil.copy(os.path.join(ROOT, ".github", "workflows", f), os.path.join(tmp, ".github", "workflows"))
            df = open(os.path.join(ROOT, "platform", "kalisim", "Dockerfile")).read()
            open(os.path.join(tmp, "platform", "kalisim", "Dockerfile"), "w").write(
                df.replace("ARG KALICO_SHA=", "ARG KALICO_SHA=0000000"))
            r = subprocess.run(["bash", os.path.join(tmp, "cad", "check-tools-page.sh")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("FAIL Kalico commit", r.stdout)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
