#!/usr/bin/env python3
"""Tests for the vendored Squiggly Purge and the VT350 settings it needs. Run: python3 cad/klipper/test_purge.py"""
import hashlib, os, re, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MACRO = os.path.join(HERE, "squiggly-purge", "squiggly_purge.cfg")
UPSTREAM_BLOB = "b13ea744d6ffa1c662a44dc4b8bc8f65e0e325de"     # mjonuschat/voron-mods@4ee68e7


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def section(text, name):
    m = re.search(rf"^\[{re.escape(name)}\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


class Purge(unittest.TestCase):
    def test_vendored_macro_is_upstream_s_blob(self):
        with open(MACRO, "rb") as f:
            data = f.read()
        self.assertEqual(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), UPSTREAM_BLOB)

    def test_printer_cfg_includes_it_with_exclude_object(self):
        p = read("printer.cfg")
        self.assertIn("[include squiggly-purge/squiggly_purge.cfg]", p)
        self.assertRegex(p, r"(?m)^\[exclude_object\]$")

    def test_extruders_set_the_cross_section(self):
        for cfg, sec in (("t0.cfg", "extruder"), ("t1.cfg", "extruder1")):
            body = section(read(cfg), sec)
            self.assertIsNotNone(body, f"{cfg} [{sec}]")
            self.assertRegex(body, r"(?m)^max_extrude_cross_section: 5$", f"{cfg} [{sec}]")


if __name__ == "__main__":
    unittest.main()
