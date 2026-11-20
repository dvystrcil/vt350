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

    def _copy_with(self, rel, old, new):
        """A copy of what the check reads, with `old` replaced by `new` in the file `rel`; returns its output."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        files = ["cad/check-tools-page.sh", "cad/tools.md", "platform/README.md", "platform/kalisim/Dockerfile",
                 "platform/virtualprinter/Dockerfile"]
        vp = os.path.join(ROOT, "platform", "virtualprinter")
        files += [f"platform/virtualprinter/{f}" for f in os.listdir(vp) if f.endswith("-requirements.txt")]
        files += [f".github/workflows/{f}" for f in os.listdir(os.path.join(ROOT, ".github", "workflows"))]
        for f in files:
            os.makedirs(os.path.dirname(os.path.join(tmp, f)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, f), os.path.join(tmp, f))
        with open(os.path.join(ROOT, rel)) as f:
            text = f.read()
        self.assertIn(old, text)
        with open(os.path.join(tmp, rel), "w") as f:
            f.write(text.replace(old, new))
        r = subprocess.run(["bash", os.path.join(tmp, "cad", "check-tools-page.sh")], capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_a_changed_pin_fails(self):
        rc, out = self._copy_with("platform/kalisim/Dockerfile", "ARG KALICO_SHA=", "ARG KALICO_SHA=0000000")
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL Kalico commit", out)
        self.assertEqual(out.count("\nFAIL ") + out.startswith("FAIL "), 1, out)

    def test_a_changed_virtual_printer_pin_fails(self):
        for rel, old, new, what in [
                ("platform/virtualprinter/Dockerfile", "curl=8.14.1-2+deb13u7", "curl=8.14.1-2+deb13u8",
                 "FAIL virtual printer apt package: curl=8.14.1-2+deb13u8"),
                ("platform/virtualprinter/Dockerfile", "ARG DEBIAN_SNAPSHOT=", "ARG DEBIAN_SNAPSHOT=1",
                 "FAIL virtual printer DEBIAN_SNAPSHOT"),
                ("platform/virtualprinter/moonraker-requirements.txt", "tornado==6.5.8", "tornado==6.5.9",
                 "FAIL virtual printer pip package: tornado==6.5.9")]:
            with self.subTest(what):
                rc, out = self._copy_with(rel, old, new)
                self.assertEqual(rc, 1, out)
                self.assertIn(what, out)
                self.assertEqual(out.count("\nFAIL ") + out.startswith("FAIL "), 1, out)

if __name__ == "__main__":
    unittest.main()
