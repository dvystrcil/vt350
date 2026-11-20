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


class TheSync(unittest.TestCase):
    """cad/sync-tools-page.py carries a changed pin onto the page (vt350#224: Renovate and the monthly repin)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("sync_tools_page", os.path.join(HERE, "sync-tools-page.py"))
        cls.sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.sync)

    def test_changed_pins_replace_their_old_values_only(self):
        page = ("| a | `git=1:2.39.5-0+deb12u3`, `make=4.3-4.1` | `actions/checkout@v7` |\n"
                "| b | `git=1:2.39.5-0+deb12u3` `git=1:2.39.5-0+deb12u30` | `20261120T000000Z` |\n")
        before = {("apt", "git"): {"git=1:2.39.5-0+deb12u3", "git=1:2.47.3-0+deb13u1"},
                  ("action", "actions/checkout"): {"actions/checkout@v7"},
                  ("DEBIAN_SNAPSHOT", ""): {"20261120T000000Z"}}
        after = {("apt", "git"): {"git=1:2.39.5-0+deb12u4", "git=1:2.47.3-0+deb13u1"},
                 ("action", "actions/checkout"): {"actions/checkout@" + "a" * 40},
                 ("DEBIAN_SNAPSHOT", ""): {"20261201T000000Z"}}
        new, notes = self.sync.sync(page, before, after)
        self.assertEqual(new, page.replace("deb12u3`", "deb12u4`").replace("@v7", "@" + "a" * 40)
                         .replace("20261120T000000Z", "20261201T000000Z"))
        self.assertIn("deb12u30", new)
        self.assertEqual(len(notes), 3, notes)

    def test_a_new_pin_is_reported_for_a_hand_edit(self):
        new, notes = self.sync.sync("page", {}, {("apt", "swig"): {"swig=4.3.0-1"}})
        self.assertEqual(new, "page")
        self.assertIn("add it to cad/tools.md by hand", notes[0])

    def test_names(self):
        self.assertEqual(self.sync.name("python:3.12-slim@sha256:ab"), "python")
        self.assertEqual(self.sync.name("tornado==6.5.8"), "tornado")
        self.assertEqual(self.sync.name("g++=4:14.2.0-1"), "g++")
        self.assertEqual(self.sync.name("20261120T000000Z"), "")


if __name__ == "__main__":
    unittest.main()
