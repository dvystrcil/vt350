#!/usr/bin/env python3
"""kalisim's Debian pins (vt350#224): apt_snapshot.sh against a fake /etc/apt, and every apt package in the
Dockerfile at an exact version from the snapshot. Plain python3, no Docker, no network:

    python3 platform/kalisim/test_apt_snapshot.py
"""
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "apt_snapshot.sh")
# the virtual printer's image (platform/virtualprinter) carries the same script for its own build context
TWIN = os.path.join(HERE, "..", "virtualprinter", "apt_snapshot.sh")
TS = "20261120T000000Z"
SOURCES = """\
Types: deb
URIs: http://deb.debian.org/debian
Suites: bookworm bookworm-updates
Components: main

Types: deb
URIs: http://deb.debian.org/debian-security
Suites: bookworm-security
Components: main
"""


class AptSnapshot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.src = os.path.join(self.root, "etc", "apt", "sources.list.d", "debian.sources")
        os.makedirs(os.path.dirname(self.src))
        os.makedirs(os.path.join(self.root, "etc", "apt", "apt.conf.d"))
        with open(self.src, "w") as f:
            f.write(SOURCES)

    def _run(self, ts=TS):
        return subprocess.run(["sh", SCRIPT, ts], capture_output=True, text=True,
                              env=dict(os.environ, APT_ROOT=self.root))

    def test_points_both_archives_at_the_snapshot(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(self.src) as f:
            text = f.read()
        self.assertIn(f"URIs: http://snapshot.debian.org/archive/debian/{TS}\n", text)
        self.assertIn(f"URIs: http://snapshot.debian.org/archive/debian-security/{TS}\n", text)
        self.assertNotIn("deb.debian.org", text)

    def test_a_leftover_deb_debian_org_source_or_bad_timestamp_fails(self):
        with open(os.path.join(self.root, "etc", "apt", "sources.list"), "w") as f:
            f.write("deb http://deb.debian.org/debian bookworm main\n")
        self.assertEqual(self._run().returncode, 1)
        self.assertEqual(self._run("latest").returncode, 1)

    def test_same_script_as_the_virtual_printers(self):
        if os.path.exists(TWIN):
            with open(SCRIPT) as a, open(TWIN) as b:
                self.assertEqual(a.read(), b.read(), "keep the two apt_snapshot.sh copies identical")


class TheDockerfile(unittest.TestCase):
    def test_every_apt_package_has_an_exact_version_from_the_snapshot(self):
        with open(os.path.join(HERE, "Dockerfile")) as f:
            text = f.read()
        self.assertRegex(text, r"(?m)^ARG DEBIAN_SNAPSHOT=\d{8}T\d{6}Z$")
        joined = text.replace("\\\n", " ")
        installs = [c for c in re.split(r"&&|\n", joined) if "apt-get install" in c]
        self.assertEqual(len(installs), text.count("apt-get update"))
        self.assertEqual(len(installs), text.count('apt_snapshot.sh "$DEBIAN_SNAPSHOT"'))
        for c in installs:
            pkgs = [w for w in c.split() if not w.startswith("-") and w not in ("apt-get", "install")]
            self.assertTrue(pkgs)
            for p in pkgs:
                self.assertRegex(p, r"^[a-z0-9.+-]+=[0-9][^\s=]*$", f"apt package without an exact version: {p}")


if __name__ == "__main__":
    unittest.main()
