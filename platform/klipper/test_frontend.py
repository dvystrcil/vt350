#!/usr/bin/env python3
"""Tests for frontend.py: the vendored web front-end configs and switching between them.

Plain python3, no Kalico:  python3 platform/klipper/test_frontend.py
"""
import hashlib
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frontend  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
VT350 = os.path.join(ROOT, "cad", "klipper", "frontend.cfg")

CFG = """\
# The web front end
[include ../../platform/klipper/frontends/fluidd/client.cfg]
"""


def blob(path):
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()   # = git hash-object


class Chosen(unittest.TestCase):
    def test_reads_the_include(self):
        self.assertEqual(frontend.chosen(CFG), "fluidd")

    def test_none_or_two_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            frontend.chosen("# nothing\n")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            frontend.chosen(CFG + CFG.replace("fluidd", "mainsail"))

    def test_unknown_front_end_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "octoprint"):
            frontend.chosen(CFG.replace("fluidd", "octoprint"))


class Use(unittest.TestCase):
    def test_switches_only_the_include_line(self):
        out = frontend.use(CFG, "mainsail")
        self.assertEqual(out, CFG.replace("frontends/fluidd/", "frontends/mainsail/"))
        self.assertEqual(frontend.chosen(out), "mainsail")

    def test_unknown_name_is_refused(self):
        with self.assertRaisesRegex(ValueError, "octoprint"):
            frontend.use(CFG, "octoprint")

    def test_cli_needs_a_config(self):
        with self.assertRaises(SystemExit):
            frontend.main(["--use", "mainsail"])

    def test_cli_switches_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "frontend.cfg")
            with open(p, "w") as f:
                f.write(CFG)
            self.assertEqual(frontend.main(["--config", p]), ["front end: fluidd"])
            self.assertEqual(frontend.main(["--config", p, "--use", "mainsail"]),
                             ["front end: fluidd -> mainsail"])
            with open(p) as f:
                self.assertEqual(frontend.chosen(f.read()), "mainsail")


class Vendored(unittest.TestCase):
    def test_each_client_cfg_is_upstream_s_blob(self):
        self.assertEqual(sorted(frontend.FRONTENDS), ["fluidd", "mainsail"])
        for name, meta in frontend.FRONTENDS.items():
            with self.subTest(name=name):
                self.assertEqual(blob(frontend.client_cfg(name)), meta["blob"])
                self.assertRegex(meta["sha"], r"^[0-9a-f]{40}$")
                self.assertTrue(os.path.isfile(os.path.join(HERE, "frontends", name, "LICENSE")))

    def test_vt350_uses_fluidd(self):     # owner, 2026-11-10
        with open(VT350) as f:
            self.assertEqual(frontend.chosen(f.read()), "fluidd")

    def test_vt350_include_resolves(self):
        with open(VT350) as f:
            inc = frontend.include_path(f.read())
        self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(os.path.dirname(VT350), inc))), inc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
