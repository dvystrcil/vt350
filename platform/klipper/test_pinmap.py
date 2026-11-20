#!/usr/bin/env python3
"""Tests for pinmap.py: a Klipper config's MCU pins mapped onto simulated boards, and the check that the map covers
every pin.

Plain python3, no Kalico:  python3 platform/klipper/test_pinmap.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pinmap  # noqa: E402

MAIN = """\
[mcu]
serial: /dev/null

[mcu tb]
serial: /dev/null

[stepper_x]
step_pin: PF13
dir_pin: !PF12
enable_pin: !PF14
endstop_pin: ^PG6

[extruder]
step_pin: tb:PB3
heater_pin: tb:PB9
sensor_type: Generic 3950
sensor_pin: tb:PA1

[probe]
pin: ^PG11

[stepper_z]
endstop_pin: probe:z_virtual_endstop

[gcode_macro FOO]
variable_some_pin: PZ9
gcode:
  pin: PZ8

[include extra.cfg]
"""

EXTRA = """\
[fan]
pin: tb:PA10   # inline comment
# pin: PZ7
"""


def write_tree(d, files):
    for rel, text in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return os.path.join(d, "printer.cfg")


class Parse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = write_tree(self.tmp.name, {"printer.cfg": MAIN, "extra.cfg": EXTRA})

    def tearDown(self):
        self.tmp.cleanup()

    def uses(self, path=None):
        return {(u.mcu, u.pin): u for u in pinmap.pin_uses(pinmap.load(path or self.cfg))}

    def test_finds_mcu_pins_in_the_config_and_its_includes(self):
        self.assertEqual(set(self.uses()), {("mcu", "PF13"), ("mcu", "PF12"), ("mcu", "PF14"), ("mcu", "PG6"),
                                            ("tb", "PB3"), ("tb", "PB9"), ("tb", "PA1"), ("mcu", "PG11"),
                                            ("tb", "PA10")})

    def test_skips_virtual_pins_macro_variables_macro_bodies_and_comments(self):
        pins = {p for _, p in self.uses()}
        for p in ("z_virtual_endstop", "PZ9", "PZ8", "PZ7"):
            self.assertNotIn(p, pins)

    def test_thermistor_sensor_pin_is_analog(self):
        u = self.uses()
        self.assertEqual(u["tb", "PA1"].kind, "adc")
        self.assertEqual(u["tb", "PB9"].kind, "digital")

    def test_spi_sensor_pin_is_digital(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[temperature_sensor c]\nsensor_type: MAX31865\n"
                                                        "sensor_pin: PA4\n"})
        self.assertEqual(self.uses(cfg)["mcu", "PA4"].kind, "digital")

    def test_hardware_pwm_pin_is_pwm(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[output_pin led]\npin: PA4\nhardware_pwm: True\n"})
        self.assertEqual(self.uses(cfg)["mcu", "PA4"].kind, "pwm")

    def test_a_later_repeat_of_a_section_overrides_the_option(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[probe]\npin: P1.27\n[include over.cfg]\n",
                                         "over.cfg": "[probe]\npin: ^PG11\n"})
        self.assertEqual(set(self.uses(cfg)), {("mcu", "PG11")})

    def test_pin_lists(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[static_digital_output x]\npins: PA1, !PA2\n"})
        self.assertEqual(set(self.uses(cfg)), {("mcu", "PA1"), ("mcu", "PA2")})

    def test_include_glob_and_subfolder(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[include sub/*.cfg]\n",
                                         "sub/a.cfg": "[fan]\npin: PB1\n", "sub/b.cfg": "[include ../c.cfg]\n",
                                         "c.cfg": "[heater_bed]\nheater_pin: PB2\n"})
        self.assertEqual(set(self.uses(cfg)), {("mcu", "PB1"), ("mcu", "PB2")})

    def test_board_pins_aliases_are_refused(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[board_pins x]\naliases: A=PA1\n"})
        with self.assertRaisesRegex(ValueError, "board_pins"):
            pinmap.pin_uses(pinmap.load(cfg))

    def test_pulldown_is_refused(self):
        cfg = write_tree(self.tmp.name, {"printer.cfg": "[mcu]\n[probe]\npin: ~PA1\n"})
        with self.assertRaisesRegex(ValueError, "pull-down"):
            pinmap.pin_uses(pinmap.load(cfg))


class Generate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = write_tree(self.tmp.name, {"printer.cfg": MAIN, "extra.cfg": EXTRA})
        self.uses = pinmap.pin_uses(pinmap.load(self.cfg))

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_simulated_board_per_mcu_every_pin_mapped_once(self):
        m = pinmap.generate(self.uses)
        self.assertEqual(m["target"], pinmap.DEFAULT_TARGET)
        self.assertEqual(set(m["mcus"]), {"mcu", "tb"})
        self.assertEqual(set(m["mcus"]["mcu"]), {"PF13", "PF12", "PF14", "PG6", "PG11"})
        for pins in m["mcus"].values():
            self.assertEqual(len(set(pins.values())), len(pins))

    def test_analog_pins_land_on_adc_pins_and_the_serial_pins_stay_free(self):
        m = pinmap.generate(self.uses)
        t = pinmap.TARGETS[pinmap.DEFAULT_TARGET]
        self.assertIn(m["mcus"]["tb"]["PA1"], t["adc"])
        used = {s for pins in m["mcus"].values() for s in pins.values()}
        self.assertFalse(used & set(t["reserved"]))

    def test_deterministic(self):
        self.assertEqual(pinmap.generate(self.uses), pinmap.generate(list(reversed(self.uses))))

    def test_previous_assignments_are_kept_when_a_pin_is_added(self):
        old = pinmap.generate(self.uses)
        more = self.uses + [pinmap.PinUse("mcu", "PA0", "digital", "[new] pin")]
        new = pinmap.generate(more, previous=old)
        for pin, sim in old["mcus"]["mcu"].items():
            self.assertEqual(new["mcus"]["mcu"][pin], sim)
        self.assertIn("PA0", new["mcus"]["mcu"])

    def test_too_many_pins_for_the_board_is_an_error(self):
        uses = [pinmap.PinUse("mcu", f"P{i}", "digital", "[x] pin") for i in range(40)]
        with self.assertRaisesRegex(ValueError, "mcu needs 40"):
            pinmap.generate(uses)

    def test_one_pin_used_as_analog_and_pwm_is_an_error(self):
        uses = [pinmap.PinUse("mcu", "PA1", "adc", "[a] sensor_pin"), pinmap.PinUse("mcu", "PA1", "pwm", "[b] pin")]
        with self.assertRaisesRegex(ValueError, "PA1"):
            pinmap.generate(uses)


class Check(unittest.TestCase):
    """AC3: the check fails when the config gains a pin the map doesn't cover."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = write_tree(self.tmp.name, {"printer.cfg": MAIN, "extra.cfg": EXTRA})
        self.map = os.path.join(self.tmp.name, "pinmap.json")
        pinmap.main(["generate", "--config", self.cfg, "--map", self.map])

    def tearDown(self):
        self.tmp.cleanup()

    def test_ok_when_generated_from_the_config(self):
        self.assertEqual(pinmap.main(["check", "--config", self.cfg, "--map", self.map]), ["pinmap: OK"])

    def test_fails_when_the_config_gains_a_pin(self):
        write_tree(self.tmp.name, {"extra.cfg": EXTRA + "\n[heater_bed]\nheater_pin: PA3\n"})
        out = pinmap.main(["check", "--config", self.cfg, "--map", self.map])
        self.assertEqual(out[-1], "pinmap: FAILED")
        self.assertTrue(any("mcu:PA3" in l and "not in the map" in l for l in out), out)

    def test_fails_when_the_map_has_a_pin_the_config_dropped(self):
        write_tree(self.tmp.name, {"extra.cfg": "\n"})
        out = pinmap.main(["check", "--config", self.cfg, "--map", self.map])
        self.assertEqual(out[-1], "pinmap: FAILED")
        self.assertTrue(any("tb:PA10" in l for l in out), out)

    def test_fails_when_the_map_was_edited_by_hand(self):
        with open(self.map) as f:
            m = json.load(f)
        m["mcus"]["tb"]["PA1"] = "PC0"   # not an ADC pin
        with open(self.map, "w") as f:
            json.dump(m, f)
        self.assertEqual(pinmap.main(["check", "--config", self.cfg, "--map", self.map])[-1], "pinmap: FAILED")

    def test_regenerate_keeps_the_existing_map(self):
        with open(self.map) as f:
            before = f.read()
        pinmap.main(["generate", "--config", self.cfg, "--map", self.map])
        with open(self.map) as f:
            self.assertEqual(f.read(), before)

    def test_cli_exit_code(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pinmap.cli(["check", "--config", self.cfg, "--map", self.map]), 0)
        write_tree(self.tmp.name, {"extra.cfg": EXTRA + "\n[heater_bed]\nheater_pin: PA3\n"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pinmap.cli(["check", "--config", self.cfg, "--map", self.map]), 1)


class Apply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "src")
        self.cfg = write_tree(self.src, {"printer.cfg": MAIN, "extra.cfg": EXTRA})
        self.map = os.path.join(self.tmp.name, "pinmap.json")
        pinmap.main(["generate", "--config", self.cfg, "--map", self.map])
        with open(self.map) as f:
            self.m = json.load(f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rewrite_value_keeps_modifiers_and_chip(self):
        sim = self.m["mcus"]["mcu"]["PF12"]
        self.assertEqual(pinmap.rewrite_value("!PF12", self.m), f"!{sim}")
        self.assertEqual(pinmap.rewrite_value("tb:PA1", self.m), f"tb:{self.m['mcus']['tb']['PA1']}")
        self.assertEqual(pinmap.rewrite_value("probe:z_virtual_endstop", self.m), "probe:z_virtual_endstop")

    def test_apply_writes_a_tree_that_uses_only_simulated_pins(self):
        out = os.path.join(self.tmp.name, "out")
        top = pinmap.main(["apply", "--config", self.cfg, "--map", self.map, "--out", out])[-1].split()[-1]
        self.assertTrue(top.endswith("printer.cfg") and top.startswith(out))
        sims = {(mcu, s) for mcu, pins in self.m["mcus"].items() for s in pins.values()}
        got = {(u.mcu, u.pin) for u in pinmap.pin_uses(pinmap.load(top))}
        self.assertEqual(len(got), 9)
        self.assertTrue(got <= sims, got - sims)
        with open(os.path.join(out, "extra.cfg")) as f:
            self.assertIn("# inline comment", f.read())
        with open(self.cfg) as f:
            self.assertEqual(f.read(), MAIN)   # the source is untouched


if __name__ == "__main__":
    unittest.main()
