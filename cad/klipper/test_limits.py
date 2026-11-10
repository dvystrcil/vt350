#!/usr/bin/env python3
"""Tests for limits.py: printer.cfg's limits against the committed CAD logs, and the envelope G-code (vt350#116).

Plain python3, no FreeCAD, no Kalico:  python3 cad/klipper/test_limits.py
"""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import limits  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
LOGS = os.path.join(ROOT, "cad", "data", "logs")


def read(*p):
    with open(os.path.join(*p)) as f:
        return f.read()


SWEEP = """\
[   31.4s] Left carried: nozzle tip Z 380.48; bed top dZ +93.32 (magnet top 287.16 -> 380.48); nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[   31.4s] Right carried: nozzle tip Z 380.49; bed top dZ +93.32 (magnet top 287.16 -> 380.49); nozzle Y reach -51.93 .. 370.69 (print square Y 30.5 .. 380.5)
[  213.4s]    Left head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  213.4s]    Left head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
[  391.5s]    Right head, left side: first nozzle X with no new overlap -416.0 (print square edge -420.0)
[  391.5s]    Right head, right side: first nozzle X with no new overlap -74.0 (print square edge -70.0)
"""
ZLOG = "[  912.4s] klipper_position_max_configured_mm=330.33 (printer.cfg [stepper_z] position_max: ...)\n"
MAP = {"origin_model_xy": [-420.0, 30.5], "sign_xy": [1, 1]}

CFG = """\
# a comment
[printer]
kinematics: corexy
[stepper_x]
rotation_distance: 40   # inline comment
microsteps: 16
position_min: 4.00
position_max: 346.00
[stepper_y]
rotation_distance: 40
microsteps: 16
full_steps_per_rotation: 400
position_min: -82.43
position_max: 340.19
[stepper_z]
rotation_distance: 8
microsteps: 16
position_min: 0
position_max: 330.33
"""


class ParseCfg(unittest.TestCase):
    def test_sections_keys_and_comments(self):
        c = limits.parse_cfg(CFG)
        self.assertEqual(c["printer"]["kinematics"], "corexy")
        self.assertEqual(c["stepper_x"]["rotation_distance"], "40")
        self.assertNotIn("comment", str(c))

    def test_equals_and_semicolon_comments(self):
        c = limits.parse_cfg("[a]\nk = v ; note\n; whole line\nm=  w\n")
        self.assertEqual(c, {"a": {"k": "v", "m": "w"}})

    def test_indented_continuation_lines_are_not_keys(self):
        c = limits.parse_cfg("[gcode_macro X]\ngcode:\n  G28\n  G1 X1: y\n[b]\nk: 1\n")
        self.assertEqual(c["b"], {"k": "1"})
        self.assertNotIn("G1 X1", c["gcode_macro X"])

    def test_option_outside_a_section_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "outside a section"):
            limits.parse_cfg("k: 1\n")

    def test_cfg_limits_and_step(self):
        c = limits.parse_cfg(CFG)
        self.assertEqual(limits.cfg_limits(c), {"x": (4.0, 346.0), "y": (-82.43, 340.19), "z": (0.0, 330.33)})
        self.assertEqual(limits.step_distance(c, "x"), 40 / (200 * 16))
        self.assertEqual(limits.step_distance(c, "y"), 40 / (400 * 16))
        self.assertEqual(limits.step_distance(c, "z"), 8 / (200 * 16))

    def test_position_min_defaults_to_zero(self):
        c = limits.parse_cfg("[stepper_x]\nposition_max: 5\n[stepper_y]\nposition_max: 6\n[stepper_z]\nposition_max: 7\n")
        self.assertEqual(limits.cfg_limits(c), {"x": (0.0, 5.0), "y": (0.0, 6.0), "z": (0.0, 7.0)})


class CadLimits(unittest.TestCase):
    def test_from_logs(self):
        self.assertEqual(limits.cad_limits(SWEEP, ZLOG, MAP), {"x": (4.0, 346.0), "y": (-82.43, 340.19),
                                                               "z": (0.0, 330.33)})

    def test_mapping_sign_flips_and_orders(self):
        m = {"origin_model_xy": [-70.0, 380.5], "sign_xy": [-1, -1]}
        got = limits.cad_limits(SWEEP, ZLOG, m)
        self.assertEqual(got["x"], (4.0, 346.0))
        self.assertEqual(got["y"], (9.81, 432.43))

    def test_heads_disagree_takes_the_tighter(self):
        log = SWEEP.replace("Right head, right side: first nozzle X with no new overlap -74.0",
                            "Right head, right side: first nozzle X with no new overlap -80.0")
        log = log.replace("Right carried: nozzle tip Z 380.49; bed top dZ +93.32 (magnet top 287.16 -> 380.49); "
                          "nozzle Y reach -51.93 .. 370.69", "Right carried: nozzle tip Z 380.49; bed top dZ +93.32 "
                          "(magnet top 287.16 -> 380.49); nozzle Y reach -50.00 .. 360.00")
        log = log.replace("Left head, left side: first nozzle X with no new overlap -416.0",
                          "Left head, left side: first nozzle X with no new overlap -410.0")
        got = limits.cad_limits(log, ZLOG, MAP)
        self.assertEqual(got["x"], (10.0, 340.0))
        self.assertEqual(got["y"], (-80.5, 329.5))

    def test_missing_lines_fail_loudly(self):
        for drop, what in (("left side", "X"), ("right side", "X"), ("nozzle Y reach", "Y")):
            log = "".join(l for l in SWEEP.splitlines(True) if drop not in l)
            with self.subTest(drop=drop), self.assertRaisesRegex(ValueError, what):
                limits.cad_limits(log, ZLOG, MAP)
        with self.assertRaisesRegex(ValueError, "klipper_position_max_configured_mm"):
            limits.cad_limits(SWEEP, "", MAP)

    def test_last_configured_floor_wins(self):
        z = ZLOG + ZLOG.replace("330.33", "331.00")
        self.assertEqual(limits.cad_limits(SWEEP, z, MAP)["z"], (0.0, 331.0))

    def test_check_reports_each_difference(self):
        cad = {"x": (4.0, 346.0), "y": (-82.43, 340.19), "z": (0.0, 330.33)}
        self.assertEqual(limits.differences(cad, cad), [])
        cfg = dict(cad, x=(4.0, 346.01), z=(-1.0, 330.33))
        self.assertEqual(limits.differences(cfg, cad), ["x position_max: printer.cfg 346.01, CAD 346.0",
                                                        "z position_min: printer.cfg -1.0, CAD 0.0"])


class Envelope(unittest.TestCase):
    def setUp(self):
        self.cfg = limits.parse_cfg(CFG)
        self.text = limits.envelope_gcode(self.cfg)

    def blocks(self):
        out, cur = {}, None
        for line in self.text.splitlines():
            m = re.match(r"; @(\S+)(?: (\S+))?$", line)
            if m:
                cur = m.group(1) + (" " + m.group(2) if m.group(2) else ""); out[cur] = []
            elif cur and line and not line.startswith(";"):
                out[cur].append(line)
        return out

    def test_setup_homes_and_sets_absolute(self):
        self.assertEqual(self.blocks()["setup"][:2], ["G28", "G90"])

    def test_in_range_walks_both_z_ends_and_all_corners(self):
        moves = [l for l in self.blocks()["in-range"] if l.startswith("G1 ")]
        pts = {tuple(float(v) for v in re.findall(r"[XYZ](-?[0-9.]+)", l)) for l in moves}
        for z in (0.0, 330.33):
            for x in (4.0, 346.0):
                for y in (-82.43, 340.19):
                    self.assertIn((x, y, z), pts, (x, y, z))

    def test_consecutive_in_range_moves_differ(self):
        moves = [l for l in self.blocks()["in-range"] if l.startswith("G1 ")]
        for a, b in zip(moves, moves[1:]):
            self.assertNotEqual(a.split(" F")[0], b.split(" F")[0])

    def test_one_step_past_each_limit(self):
        b = self.blocks()
        sx, sz = 40 / 3200, 8 / 3200
        want = {"past x_min": f"G1 X{4.0 - sx:.4f}", "past x_max": f"G1 X{346.0 + sx:.4f}",
                "past y_min": f"G1 Y{-82.43 - 40 / 6400:.4f}", "past y_max": f"G1 Y{340.19 + 40 / 6400:.4f}",
                "past z_min": f"G1 Z{0.0 - sz:.4f}", "past z_max": f"G1 Z{330.33 + sz:.4f}"}
        self.assertEqual({k: v for k, v in b.items() if k.startswith("past")}, {k: [v] for k, v in want.items()})

    def test_step_is_not_rounded_back_inside(self):
        # 4 decimals must still be past the limit: a step of 0.00004 would round back onto it
        cfg = limits.parse_cfg(CFG.replace("rotation_distance: 8\n", "rotation_distance: 0.1\n"))
        with self.assertRaisesRegex(ValueError, "z.*step"):
            limits.envelope_gcode(cfg)


class Committed(unittest.TestCase):
    """The committed files agree with each other."""

    def setUp(self):
        self.cfg = limits.parse_cfg(read(HERE, "printer.cfg"))

    def test_printer_cfg_limits_come_from_the_cad_logs(self):
        cad = limits.cad_limits(read(LOGS, "sweep_toolhead.log"), read(LOGS, "z_sweep.log"), limits.load_mapping())
        self.assertEqual(limits.differences(limits.cfg_limits(self.cfg), cad), [])

    def test_position_max_is_the_z_sweep_configured_floor(self):     # #116 AC3
        want = re.findall(r"klipper_position_max_configured_mm=([0-9.]+)", read(LOGS, "z_sweep.log"))
        self.assertTrue(want)
        self.assertEqual(float(self.cfg["stepper_z"]["position_max"]), float(want[-1]))

    def test_every_limit_names_its_log(self):
        text = read(HERE, "printer.cfg")
        for sec in ("stepper_x", "stepper_y", "stepper_z"):
            body = re.search(rf"(?ms)^\[{sec}\]\n(.*?)(?=^\[|\Z)", text).group(1)
            for key in ("position_min", "position_max"):
                before = body[:body.index(f"\n{key}:")]
                self.assertRegex(before.split("\n# source:")[-1] if "# source:" in before else "",
                                 r"cad/data/logs/\w+\.log", f"{sec} {key}")

    def test_committed_envelope_is_current(self):
        self.assertEqual(read(HERE, "envelope.gcode"), limits.envelope_gcode(self.cfg),
                         "regenerate: python3 cad/klipper/limits.py --gcode > cad/klipper/envelope.gcode")

    def test_mcu_names_and_usb_serials_are_distinct(self):
        mcus = {k: v["serial"] for k, v in self.cfg.items() if k == "mcu" or k.startswith("mcu ")}
        self.assertEqual(sorted(mcus), ["mcu", "mcu o2s_left", "mcu o2s_right"])
        self.assertEqual(len(set(mcus.values())), 3)

    def test_o2s_serials_match_their_firmware_configs(self):
        for side in ("left", "right"):
            kc = read(HERE, "kalisim", "kconfig", f"o2s-{side}.config")
            sn = re.search(r'(?m)^CONFIG_USB_SERIAL_NUMBER="([^"]+)"', kc).group(1)
            self.assertIn("# CONFIG_USB_SERIAL_NUMBER_CHIPID is not set", kc)
            self.assertEqual(self.cfg[f"mcu o2s_{side}"]["serial"],
                             f"/dev/serial/by-id/usb-Klipper_stm32f072xb_{sn}-if00")


class Cli(unittest.TestCase):
    def test_check_marker(self):
        out = limits.main(["--check"])
        self.assertEqual(out[-1], "limits: OK")

    def test_check_fails_on_a_difference(self):
        with self.assertRaisesRegex(SystemExit, "x position_max"):
            limits.main(["--check"], cfg_text=read(HERE, "printer.cfg").replace("position_max: 346.00",
                                                                                 "position_max: 347.00"))

    def test_unknown_arguments_print_usage(self):
        with self.assertRaisesRegex(SystemExit, "--check"):
            limits.main(["--frobnicate"])

    def test_as_a_script(self):
        out = subprocess.run([sys.executable, os.path.join(HERE, "limits.py"), "--check"], capture_output=True,
                             text=True, check=True).stdout
        self.assertEqual(out.splitlines()[-1], "limits: OK")
        self.assertIn("z: 0.0 .. 330.33", out)

    def test_gcode(self):
        self.assertEqual(limits.main(["--gcode"]), [read(HERE, "envelope.gcode").rstrip("\n")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
