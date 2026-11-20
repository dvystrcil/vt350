#!/usr/bin/env python3
"""The virtual printer's build pins (vt350#224): apt_snapshot.sh and pip_lock.py, without Docker or the network,
and the Dockerfile's pins in the shape they need.

    python3 platform/virtualprinter/test_pins.py
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pip_lock  # noqa: E402

SOURCES = """\
Types: deb
# http://snapshot.debian.org/archive/debian/20261104T212339Z
URIs: http://deb.debian.org/debian
Suites: trixie trixie-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp

Types: deb
# http://snapshot.debian.org/archive/debian-security/20261104T212339Z
URIs: http://deb.debian.org/debian-security
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp
"""
TS = "20261120T000000Z"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class AptSnapshot(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.src = os.path.join(self.root, "etc", "apt", "sources.list.d", "debian.sources")
        _write(self.src, SOURCES)
        os.makedirs(os.path.join(self.root, "etc", "apt", "apt.conf.d"))

    def _run(self, ts=TS):
        return subprocess.run(["sh", os.path.join(HERE, "apt_snapshot.sh"), ts], capture_output=True, text=True,
                              env=dict(os.environ, APT_ROOT=self.root))

    def test_points_both_archives_at_the_snapshot(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(self.src) as f:
            text = f.read()
        self.assertIn(f"URIs: http://snapshot.debian.org/archive/debian/{TS}\n", text)
        self.assertIn(f"URIs: http://snapshot.debian.org/archive/debian-security/{TS}\n", text)
        self.assertNotIn("deb.debian.org", text)
        with open(os.path.join(self.root, "etc", "apt", "apt.conf.d", "99snapshot")) as f:
            self.assertIn('Acquire::Check-Valid-Until "false";', f.read())

    def test_another_deb_debian_org_source_fails(self):
        _write(os.path.join(self.root, "etc", "apt", "sources.list"), "deb http://deb.debian.org/debian trixie main\n")
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("a deb.debian.org source is left", r.stdout)

    def test_a_bad_timestamp_fails(self):
        r = self._run("2026-11-20")
        self.assertEqual(r.returncode, 1, r.stdout)
        with open(self.src) as f:
            self.assertEqual(f.read(), SOURCES)


def _file(name, sha):
    return {"filename": name, "digests": {"sha256": sha}}


FILES = {
    ("purelib", "1.0"): [_file("purelib-1.0-py3-none-any.whl", "a" * 64), _file("purelib-1.0.tar.gz", "b" * 64)],
    ("native", "2.0"): [
        _file("native-2.0-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", "c" * 64),
        _file("native-2.0-cp313-cp313-musllinux_1_2_aarch64.whl", "d" * 64),
        _file("native-2.0-cp312-cp312-manylinux_2_17_x86_64.whl", "e" * 64),
        _file("native-2.0-cp313-cp313-win_amd64.whl", "f" * 64),
        _file("native-2.0-cp39-abi3-manylinux_2_17_x86_64.whl", "1" * 64)],
    ("sdistonly", "3.0"): [_file("sdistonly-3.0.tar.gz", "2" * 64)],
}


class PipLock(unittest.TestCase):
    def _fetch(self, name, version):
        return FILES[(name, version)]

    def test_wheel_fits_linux_cpython_313(self):
        fits = pip_lock.wheel_fits
        self.assertTrue(fits("x-1-py3-none-any.whl"))
        self.assertTrue(fits("x-1-py2.py3-none-any.whl"))
        self.assertTrue(fits("x-1-cp313-cp313-manylinux_2_28_aarch64.whl"))
        self.assertTrue(fits("x-1-cp38-abi3-manylinux_2_17_x86_64.whl"))
        self.assertFalse(fits("x-1-cp314-abi3-manylinux_2_17_x86_64.whl"))
        self.assertFalse(fits("x-1-cp312-cp312-manylinux_2_17_x86_64.whl"))
        self.assertFalse(fits("x-1-cp313-cp313-macosx_11_0_arm64.whl"))
        self.assertFalse(fits("x-1.tar.gz"))

    def test_lock_keeps_comments_and_replaces_old_hashes(self):
        text = ("# a comment\n\npurelib==1.0 \\\n    --hash=sha256:" + "9" * 64 + "\nnative==2.0\n")
        out = pip_lock.lock(text, fetch=self._fetch)
        self.assertEqual(out, "# a comment\n\n"
                              "purelib==1.0 \\\n    --hash=sha256:" + "a" * 64 + "\n"
                              "native==2.0 \\\n    --hash=sha256:" + "1" * 64 + " \\\n"
                              "    --hash=sha256:" + "c" * 64 + " \\\n    --hash=sha256:" + "d" * 64 + "\n")
        self.assertEqual(pip_lock.lock(out, fetch=self._fetch), out)

    def test_a_pin_with_no_wheel_or_no_version_fails(self):
        with self.assertRaisesRegex(ValueError, "sdistonly==3.0: no wheel"):
            pip_lock.lock("sdistonly==3.0\n", fetch=self._fetch)
        with self.assertRaisesRegex(ValueError, "not a name==version pin"):
            pip_lock.lock("purelib>=1.0\n", fetch=self._fetch)


class TheDockerfile(unittest.TestCase):
    """Every pin the Dockerfile takes from outside is exact: apt versions, the snapshot, hashes on the pip files."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "Dockerfile")) as f:
            cls.text = f.read()

    def test_every_apt_package_has_a_version_and_comes_from_the_snapshot(self):
        installs = re.findall(r"apt-get install -y --no-install-recommends((?:[^\n]*\\\n)*[^\n]*)", self.text)
        self.assertEqual(len(installs), 3)
        for block in installs:
            pkgs = block.split("&&")[0].replace("\\", " ").split()
            self.assertTrue(pkgs)
            for p in pkgs:
                self.assertRegex(p, r"^[a-z0-9.+-]+=[0-9][^\s=]*$", f"apt package without an exact version: {p}")
        self.assertEqual(self.text.count('apt_snapshot.sh "$DEBIAN_SNAPSHOT"'), 3)
        self.assertEqual(self.text.count("apt-get update"), 3)
        self.assertRegex(self.text, r"(?m)^ARG DEBIAN_SNAPSHOT=\d{8}T\d{6}Z$")

    def test_pip_installs_require_hashes(self):
        commands = [c for c in re.split(r"&&|\n", self.text.replace("\\\n", " ")) if "pip install" in c]
        self.assertEqual(len(commands), 3)
        for line in commands:
            if "--no-index" in line:
                continue
            self.assertIn("--require-hashes", line)
        for f in ("moonraker-requirements.txt", "simulavr-build-requirements.txt"):
            with open(os.path.join(HERE, f)) as fh:
                text = fh.read()
            pins = [l for l in text.splitlines() if pip_lock.PIN.match(l)]
            self.assertTrue(pins, f)
            for p in pins:
                self.assertTrue(p.endswith("\\"), f"{f}: {p} has no hash")

    def test_simulavr_pinned_by_commit_and_tree_hash(self):
        self.assertRegex(self.text, r"(?m)^ARG SIMULAVR_SHA=[0-9a-f]{40}$")
        self.assertRegex(self.text, r"(?m)^ARG SIMULAVR_TREE_SHA256=[0-9a-f]{64}$")
        self.assertIn('[ "$tree" = "$SIMULAVR_TREE_SHA256" ]', self.text)

    def test_every_external_from_is_by_digest(self):
        for image in re.findall(r"(?m)^FROM (\S+)", self.text):
            if image.startswith("${") or image == "kalisim":
                continue
            self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
