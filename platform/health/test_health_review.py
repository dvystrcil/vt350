#!/usr/bin/env python3
"""Tests for health_review.py (vt350#120): the parsing and the verdicts, without the network. Plain python3, in CI."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health_review as hr  # noqa: E402

DF = """FROM python:3.12-slim-bookworm@sha256:""" + "a" * 64 + """ AS dicts
ARG KALICO_SHA=991e1823e983a31d26b9264d2b6305fd64e3a09a
FROM ghcr.io/kalicocrew/kalico@sha256:""" + "b" * 64 + "\n"


class Pins(unittest.TestCase):
    def test_args_and_digests(self):
        args, froms = hr.dockerfile_pins(DF)
        self.assertEqual(args["KALICO_SHA"], "991e1823e983a31d26b9264d2b6305fd64e3a09a")
        self.assertEqual(froms, [("python:3.12-slim-bookworm", "sha256:" + "a" * 64),
                                 ("ghcr.io/kalicocrew/kalico", "sha256:" + "b" * 64)])

    def test_ls_remote(self):
        out = "abc123\trefs/heads/main\ndef456\trefs/heads/mainline\n"
        self.assertEqual(hr.parse_ls_remote(out, "main"), "abc123")
        self.assertIsNone(hr.parse_ls_remote(out, "dev"))


class Verdicts(unittest.TestCase):
    def test_drift_is_amber_not_red(self):
        self.assertEqual(hr.pin_check("K", "aaa", "aaa", "u")[1], "ok")
        self.assertEqual(hr.pin_check("K", "aaa", "bbb", "u")[1], "amber")
        self.assertEqual(hr.pin_check("K", "aaa", None, "u")[1], "amber")

    def test_ci(self):
        self.assertEqual(hr.ci_check([("a", "success"), ("b", "skipped")])[1], "ok")
        self.assertEqual(hr.ci_check([("a", "success"), ("b", "failure")])[1], "red")
        self.assertEqual(hr.ci_check(None)[1], "amber")

    def test_manual_run(self):
        self.assertEqual(hr.run_check("echo fine")[1], "ok")
        r = hr.run_check("echo broke; exit 3")
        self.assertEqual(r[1], "red")
        self.assertIn("exit 3", r[2])
        self.assertIn("`broke`", r[2])

    def test_report_marks_red_and_lists_the_manual_boxes(self):
        md = hr.report([("CI", "ok", "x"), ("Manual run", "red", "y")], "2026-11-17")
        self.assertIn("RED (Manual run)", md)
        self.assertEqual(md.count("- [ ] "), len(hr.MANUAL))
        md = hr.report([("CI", "ok", "x"), ("Version drift: K", "amber", "y")], "2026-11-17")
        self.assertIn("no red checks", md)


if __name__ == "__main__":
    unittest.main()
