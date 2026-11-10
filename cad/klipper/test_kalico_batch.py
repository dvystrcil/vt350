#!/usr/bin/env python3
"""Needs Kalico: runs printer.cfg through real Kalico batch mode in the kalisim container (vt350#116 AC1, AC3).

    bash cad/klipper/kalisim/test_in_container.sh      # builds the image, runs this file in it, prints "kalico-batch: OK"

Inside the image: $KALICO_DIR is Kalico, $KALISIM_DICTS holds one dictionary per MCU. Without them this file fails
instead of skipping: a skipped run would look green. check_test_tmp.sh skips it ("Needs Kalico" above).
"""
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kalisim  # noqa: E402
import limits  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
KALICO = os.environ.get("KALICO_DIR")
DICTS = os.environ.get("KALISIM_DICTS")
CFG = os.path.join(HERE, "printer.cfg")
# printer.cfg's MCU name -> the kconfig fragment (kalisim/kconfig/<name>.config) its dictionary is built from
MCUS = {"mcu": "octopus-pro-h723", "o2s_left": "o2s-left", "o2s_right": "o2s-right"}
CHIPS = {"octopus-pro-h723": "stm32h723xx", "o2s-left": "stm32f072xb", "o2s-right": "stm32f072xb"}


def read(*p):
    with open(os.path.join(*p)) as f:
        return f.read()


def dicts(names=MCUS):
    return [(m, os.path.join(DICTS, f"{MCUS[m]}.dict")) for m in names]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (KALICO and DICTS):
            raise RuntimeError("KALICO_DIR and KALISIM_DICTS are unset: run in the kalisim image "
                               "(cad/klipper/kalisim/test_in_container.sh)")


class PinnedKalico(Base):
    """AC1: a pinned Kalico, one dictionary per MCU in the real wiring."""

    def test_runtime_and_dictionaries_are_the_pinned_commit(self):
        sha = re.search(r"(?m)^ARG KALICO_SHA=([0-9a-f]{40})$", read(HERE, "kalisim", "Dockerfile")).group(1)
        self.assertEqual(read(DICTS, "KALICO_SHA").strip(), sha)
        self.assertIn(f"-g{sha[:8]}", read(KALICO, "klippy", ".version"))

    def test_plugin_in_the_image_is_this_repo_s(self):
        self.assertEqual(read(KALICO, "klippy", "plugins", "move_timeline.py"),
                         read(HERE, "kalisim", "plugins", "move_timeline.py"))

    def test_one_dictionary_per_mcu_for_its_chip(self):
        cfg = limits.parse_cfg(read(CFG))
        self.assertEqual(sorted(k for k in cfg if k == "mcu" or k.startswith("mcu ")),
                         sorted("mcu" if m == "mcu" else f"mcu {m}" for m in MCUS))
        for frag, chip in CHIPS.items():
            with self.subTest(frag=frag):
                d = json.loads(read(DICTS, f"{frag}.dict"))
                self.assertEqual(d["config"]["MCU"], chip)

    def test_each_dictionary_was_built_with_its_fragment(self):
        for frag in CHIPS:
            want = [l for l in read(HERE, "kalisim", "kconfig", f"{frag}.config").splitlines()
                    if l.startswith("CONFIG_") or re.match(r"# CONFIG_\w+ is not set", l)]
            got = read(DICTS, f"{frag}.config").splitlines()
            with self.subTest(frag=frag):
                self.assertTrue(want)
                for w in want:
                    self.assertIn(w, got)

    def test_toolboards_have_distinct_usb_serials(self):
        sn = [re.search(r'(?m)^CONFIG_USB_SERIAL_NUMBER="(.*)"$', read(DICTS, f"o2s-{s}.config")).group(1)
              for s in ("left", "right")]
        self.assertEqual(sn, ["Orbitool_O2S_L", "Orbitool_O2S_R"])

    def test_batch_run_uses_every_mcu(self):
        with tempfile.TemporaryDirectory() as d:
            r = kalisim.run(CFG, ["G28", "G90", "G1 X100 Y100 Z10 F6000"], dicts(), KALICO, workdir=d)
            outputs = sorted(f for f in os.listdir(d) if f.startswith("out.serial"))
        self.assertEqual(r.returncode, 0, r.log[-2000:])
        self.assertEqual(r.moves()[-1], [100.0, 100.0, 10.0])
        self.assertEqual(outputs, ["out.serial", "out.serial-o2s_left", "out.serial-o2s_right"])

    def test_timeline_records(self):
        # the plugin's contract (plugins/move_timeline.py): numbered records, homing as set_position, one move per
        # planned move (a no-op isn't planned), each with its speed and the active tool
        r = kalisim.run(CFG, ["G28", "G90", "G1 X100 Y100 Z10 F6000", "G1 X100 Y100 Z10",
                              "ACTIVATE_EXTRUDER EXTRUDER=extruder1", "G1 X110 F3000"], dicts(), KALICO)
        self.assertEqual(r.returncode, 0, r.log[-2000:])
        self.assertEqual([e["seq"] for e in r.timeline], list(range(1, len(r.timeline) + 1)))
        homing = r.timeline[:-2]
        self.assertEqual(homing[0]["kind"], "set_position", homing)
        self.assertEqual(sorted(homing[-1]), ["kind", "pos", "seq", "tool"])
        self.assertEqual(r.timeline[-2:], [
            {"seq": len(r.timeline) - 1, "kind": "move", "pos": [100.0, 100.0, 10.0, 0.0], "speed": 100.0,
             "tool": "extruder"},
            {"seq": len(r.timeline), "kind": "move", "pos": [110.0, 100.0, 10.0, 0.0], "speed": 50.0,
             "tool": "extruder1"}])
        self.assertEqual([e for e in homing if e["kind"] == "set_position"][-1]["pos"][:3], [346.0, 340.19, 0.0])

    def test_a_missing_toolboard_dictionary_fails(self):
        # the dictionaries are really read: without o2s_right's, the config can't load
        r = kalisim.run(CFG, ["G28"], dicts(["mcu", "o2s_left"]), KALICO)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.moves(), [])


class Envelope(Base):
    """AC3: the envelope walk."""

    def test_envelope(self):
        ok, report = kalisim.check_envelope(CFG, read(HERE, "envelope.gcode"), dicts(), KALICO)
        print("\n".join(report), file=sys.stderr)
        self.assertTrue(ok, report)
        self.assertEqual(report[0], "in-range: 9 moves accepted")   # 8 corners + Z position_min (-15)
        refused = [l.split(":")[0] for l in report if ": refused: Move out of range" in l]
        self.assertEqual(refused, [f"past {a}_{e}" for a in "xyz" for e in ("min", "max")])

    def test_walk_visits_the_negative_z_position_min(self):     # vt350#116: accepted by real Kalico in test_envelope
        zmin = float(re.search(r"(?ms)^\[stepper_z\].*?^position_min: *(-?[0-9.]+)", read(HERE, "printer.cfg")).group(1))
        self.assertLess(zmin, 0)
        zs = [t["z"] for t in kalisim.move_targets(kalisim.parse_blocks(read(HERE, "envelope.gcode"))["in-range"])]
        self.assertIn(zmin, zs)

    def test_walk_reaches_the_z_sweep_floor(self):
        want = re.findall(r"klipper_position_max_configured_mm=([0-9.]+)", read(ROOT, "cad/data/logs/z_sweep.log"))
        zs = [t["z"] for t in kalisim.move_targets(kalisim.parse_blocks(read(HERE, "envelope.gcode"))["in-range"])]
        self.assertEqual(max(zs), float(want[-1]))
        self.assertEqual(float(limits.parse_cfg(read(CFG))["stepper_z"]["position_max"]), float(want[-1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
