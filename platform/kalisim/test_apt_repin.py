#!/usr/bin/env python3
"""apt_repin.py (vt350#224): sets the snapshot, asks each stage's base image for its candidates, rewrites only the
versions. No docker: the candidates come from a fake. Plain python3, in CI."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apt_repin  # noqa: E402

DOCKERFILE = """\
ARG BASE=kalisim:local
ARG DEBIAN_SNAPSHOT=20261120T000000Z

FROM ${BASE} AS kalisim

FROM python:3.12-slim-bookworm@sha256:abc AS firmware
RUN sh /usr/local/sbin/apt_snapshot.sh "$DEBIAN_SNAPSHOT" \\
 && apt-get update \\
 && apt-get install -y --no-install-recommends \\
        git=1:2.39.5-0+deb12u3 make=4.3-4.1 \\
        gcc-avr=1:5.4.0+Atmel3.6.2-3 \\
 && rm -rf /var/lib/apt/lists/*

FROM kalisim AS build
RUN apt-get install -y --no-install-recommends git=1:2.47.3-0+deb13u1 swig=4.3.0-1 && true

FROM kalisim
RUN apt-get install -y --no-install-recommends \\
        curl=8.14.1-2+deb13u7 \\
 && rm -rf /var/lib/apt/lists/*
"""

POLICY = """\
git:
  Installed: (none)
  Candidate: 1:2.47.3-0+deb13u2
  Version table:
curl:
  Installed: 8.14.1-2+deb13u7
  Candidate: 8.14.1-2+deb13u8
swig:
  Installed: (none)
  Candidate: 4.3.0-1
"""


class Repin(unittest.TestCase):
    def setUp(self):
        self.asked = {}

    def fake(self, image, pkgs):
        self.asked[image] = pkgs
        if image.startswith("python:"):
            return {"git": "1:2.39.5-0+deb12u4", "make": "4.3-4.1", "gcc-avr": "1:5.4.0+Atmel3.6.2-3"}
        return apt_repin.parse_policy(POLICY)

    def test_versions_move_per_stage_and_nothing_else(self):
        new, changes = apt_repin.repin(DOCKERFILE, "20261201T000000Z", {"kalisim:local": "kalico@sha256:def"},
                                       candidates=self.fake)
        self.assertEqual(self.asked, {"python:3.12-slim-bookworm@sha256:abc": ["gcc-avr", "git", "make"],
                                      "kalico@sha256:def": ["curl", "git", "swig"]})
        expected = (DOCKERFILE.replace("20261120T000000Z", "20261201T000000Z")
                    .replace("git=1:2.39.5-0+deb12u3", "git=1:2.39.5-0+deb12u4")
                    .replace("git=1:2.47.3-0+deb13u1", "git=1:2.47.3-0+deb13u2")
                    .replace("curl=8.14.1-2+deb13u7", "curl=8.14.1-2+deb13u8"))
        self.assertEqual(new, expected)
        self.assertEqual(len(changes), 3, changes)

    def test_same_snapshot_same_versions_changes_nothing(self):
        def same(image, pkgs):
            found = dict(apt_repin.PKG.findall(DOCKERFILE))
            found["git"] = "1:2.39.5-0+deb12u3" if image.startswith("python:") else "1:2.47.3-0+deb13u1"
            return found
        new, changes = apt_repin.repin(DOCKERFILE, "20261120T000000Z", candidates=same)
        self.assertEqual(new, DOCKERFILE)
        self.assertEqual(changes, [])

    def test_a_package_the_snapshot_lacks_fails(self):
        with self.assertRaisesRegex(ValueError, "swig: no candidate"):
            apt_repin.repin(DOCKERFILE, "20261201T000000Z",
                            candidates=lambda image, pkgs: {p: "1" for p in pkgs if p != "swig"})

    def test_a_bad_timestamp_fails(self):
        with self.assertRaisesRegex(ValueError, "not a timestamp"):
            apt_repin.repin(DOCKERFILE, "2026-12-01", candidates=self.fake)

    def test_the_real_dockerfiles_parse(self):
        """Both real Dockerfiles: every install block found, each with a base image."""
        root = os.path.dirname(os.path.dirname(HERE))
        for rel, n in (("platform/kalisim/Dockerfile", 1), ("platform/virtualprinter/Dockerfile", 3)):
            with open(os.path.join(root, rel)) as f:
                lines = f.read().split("\n")
            blocks = apt_repin.install_blocks(lines)
            bases = apt_repin.stages(lines)
            self.assertEqual(len(blocks), n, rel)
            for a, b in blocks:
                self.assertTrue(bases[a], rel)
                self.assertTrue(apt_repin.PKG.findall(apt_repin.block_text(lines, a, b)), rel)


if __name__ == "__main__":
    unittest.main()
