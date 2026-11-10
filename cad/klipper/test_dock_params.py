#!/usr/bin/env python3
"""Tests for dock_params.py: the tool-change params from the CAD dock poses, and the vendored MadMax macros (vt350#116 AC4).

Plain python3, no FreeCAD, no Kalico:  python3 cad/klipper/test_dock_params.py
"""
import hashlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dock_params  # noqa: E402
import limits  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))


def read(*p):
    with open(os.path.join(*p)) as f:
        return f.read()


SWEEP = """\
[   32.9s] Left: docked nozzle tip (-399.00, -32.46, 380.80)
[   32.9s] Right: docked nozzle tip (-92.00, -32.46, 380.80)
[  117.5s] -- Left / dock pickup at the large opening, top: own dock pickup slid 6.0 mm forward to the keyslots' large opening, bed top; nozzle (-399.0, -38.5, 380.48) bed dZ +93.32: 13 overlaps
"""
MAP = {"origin_model_xy": [-420.0, 30.5], "sign_xy": [1, 1]}
MADMAX = {"params_close_y": 15.0, "params_attach_y": -7.0, "params_safe_shuttle_y": 35.0,
          "params_safe_toolhead_y": 110.0}


class FromLog(unittest.TestCase):
    def test_docked_poses_and_slide(self):
        self.assertEqual(dock_params.docked(SWEEP), {"Left": (-399.0, -32.46), "Right": (-92.0, -32.46)})
        self.assertEqual(dock_params.slide(SWEEP), 6.0)

    def test_missing_lines_fail_loudly(self):
        with self.assertRaisesRegex(ValueError, "docked nozzle tip"):
            dock_params.docked(SWEEP.splitlines()[2])
        with self.assertRaisesRegex(ValueError, "large opening"):
            dock_params.slide(SWEEP.splitlines()[0])

    def test_heads_docked_at_different_y_fail(self):
        # the macros take one close/attach Y for every tool ([toolchanger]), so the docks must share a Y
        with self.assertRaisesRegex(ValueError, "same Y"):
            dock_params.derive(SWEEP.replace("(-92.00, -32.46", "(-92.00, -33.00"), MAP, MADMAX)


class Derive(unittest.TestCase):
    def setUp(self):
        self.p = dock_params.derive(SWEEP, MAP, MADMAX)

    def test_y_params(self):
        # parked = -32.46 - 30.5; attach = parked - slide; the rest keep MadMax's offset from its own parked Y
        # (attach -7 + slide 6 = -1): close +16, safe shuttle +36, safe toolhead +111
        self.assertEqual(self.p["toolchanger"], {"params_attach_y": -68.96, "params_close_y": -46.96,
                                                 "params_safe_shuttle_y": -26.96, "params_safe_toolhead_y": 48.04})

    def test_tools(self):
        # T0 = Left (extruder), T1 = Right (extruder1); detach 5 mm away from the dock's keyslot plate, which is on the
        # head's outer side (lite23_cowl_docks.py: left = -X dock side, right = +X, mirror image)
        self.assertEqual(self.p["tools"], {
            "T0": {"tool_number": 0, "extruder": "extruder", "params_park_x": 21.0, "params_detach_x": 26.0},
            "T1": {"tool_number": 1, "extruder": "extruder1", "params_park_x": 328.0, "params_detach_x": 323.0}})

    def test_mapping_sign_flips_detach(self):
        p = dock_params.derive(SWEEP, {"origin_model_xy": [0.0, 30.5], "sign_xy": [-1, 1]}, MADMAX)
        self.assertEqual(p["tools"]["T0"]["params_park_x"], 399.0)
        self.assertEqual(p["tools"]["T0"]["params_detach_x"], 394.0)    # still away from the plate, in model +X

    def test_rounded_to_the_config_s_two_decimals(self):
        p = dock_params.derive(SWEEP.replace("(-399.00,", "(-399.004,").replace("-32.46,", "-32.461,"), MAP, MADMAX)
        self.assertEqual(p["tools"]["T0"]["params_park_x"], 21.0)
        self.assertEqual(p["toolchanger"]["params_attach_y"], -68.96)

    def test_madmax_offsets_follow_its_values(self):
        p = dock_params.derive(SWEEP, MAP, dict(MADMAX, params_close_y=17.0))
        self.assertEqual(p["toolchanger"]["params_close_y"], -44.96)

    def test_differences(self):
        cfg = {"toolchanger": {"params_attach_y": "-68.96", "params_close_y": "-46.96",
                               "params_safe_shuttle_y": "-26.96", "params_safe_toolhead_y": "48.04"},
               "tool T0": {"tool_number": "0", "extruder": "extruder", "params_park_x": "21.0",
                           "params_detach_x": "26.0"},
               "tool T1": {"tool_number": "1", "extruder": "extruder1", "params_park_x": "328",
                           "params_detach_x": "323"}}
        self.assertEqual(dock_params.differences(cfg, self.p), [])
        cfg["tool T1"]["params_detach_x"] = "333"
        del cfg["toolchanger"]["params_close_y"]
        self.assertEqual(dock_params.differences(cfg, self.p),
                         ["[toolchanger] params_close_y: toolchanger.cfg None, CAD -46.96",
                          "[tool T1] params_detach_x: toolchanger.cfg 333, CAD 323.0"])


class Committed(unittest.TestCase):
    """The committed files: the vendored MadMax macros are upstream's, and toolchanger.cfg matches the CAD."""

    def test_vendored_macros_are_upstream_s_blobs(self):
        for name, blob in dock_params.UPSTREAM_BLOBS.items():
            with self.subTest(name=name):
                with open(os.path.join(HERE, "madmax", name), "rb") as f:
                    data = f.read()
                got = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()     # = git hash-object
                self.assertEqual(got, blob)

    def test_toolchanger_cfg_matches_the_cad(self):
        self.assertEqual(dock_params.main(["--check"])[-1], "dock-params: OK")

    def test_madmax_reference_values_come_from_the_vendored_file(self):
        self.assertEqual(dock_params.madmax_params(), MADMAX)

    def test_printer_cfg_includes_the_toolchanger(self):
        self.assertIn("include toolchanger.cfg", limits.parse_cfg(read(HERE, "printer.cfg")))

    def test_toolchanger_cfg_includes_the_madmax_macros_first(self):
        # the VT350 [toolchanger] repeats the section to override MadMax's params: it must come after the include
        secs = list(limits.parse_cfg(read(HERE, "toolchanger.cfg")))
        self.assertEqual(secs[:3], ["include madmax/toolchanger_macros.cfg", "include madmax/toolchanger.cfg",
                                    "toolchanger"])

    def test_every_derived_param_names_its_source(self):
        text = read(HERE, "toolchanger.cfg")
        for key in list(dock_params.derive_committed()["toolchanger"]) + ["params_park_x", "params_detach_x"]:
            for i, line in enumerate(text.splitlines()):
                if line.startswith(key + ":"):
                    with self.subTest(key=key, line=i + 1):
                        above = "\n".join(text.splitlines()[max(0, i - 4):i])
                        self.assertIn("# source:", above)

    def test_params_are_inside_the_axis_limits(self):
        lim = limits.cfg_limits(limits.parse_cfg(read(HERE, "printer.cfg")))
        p = dock_params.derive_committed()
        for k, v in p["toolchanger"].items():
            with self.subTest(k=k):
                self.assertTrue(lim["y"][0] <= v <= lim["y"][1], (k, v, lim["y"]))
        for t in p["tools"].values():
            for k in ("params_park_x", "params_detach_x"):
                self.assertTrue(lim["x"][0] <= t[k] <= lim["x"][1], (k, t[k], lim["x"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
