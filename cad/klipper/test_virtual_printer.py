#!/usr/bin/env python3
"""The virtual printer follows printer.cfg (vt350#224): when the config gains a pin (a [heater_bed], a fan; #15), CI
fails until pinmap.json covers it, and a new heater must be one the virtual printer simulates.

Runs pinmap.py check and prepare.py --check, as kalico-batch CI does, on a temp copy of this folder with a fake
[heater_bed] added. Plain python3, no Docker, no Kalico (a small thermistor list stands in for Kalico's
temperature_sensors.cfg; CI runs the real one on the real config):  python3 cad/klipper/test_virtual_printer.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PINMAP = os.path.join(ROOT, "platform", "klipper", "pinmap.py")
PREPARE = os.path.join(ROOT, "platform", "virtualprinter", "prepare.py")

# The thermistors printer.cfg and the fake bed name, as in Kalico's klippy/extras/temperature_sensors.cfg
SENSORS = """\
[thermistor ATC Semitec 104GT-2]
temperature1: 20
resistance1: 126800
temperature2: 150
resistance2: 1360
temperature3: 300
resistance3: 80.65

[thermistor Generic 3950]
temperature1: 25
resistance1: 100000
beta: 3950
"""
# An Octopus Pro's bed output and its first thermistor input, neither used by printer.cfg yet
BED = """
[heater_bed]
heater_pin: PA1
sensor_pin: PF3
sensor_type: {sensor}
min_temp: 0
max_temp: 120
control: pid
pid_Kp: 50
pid_Ki: 1
pid_Kd: 500
"""


class Drift(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.klipper = os.path.join(self.root, "cad", "klipper")
        shutil.copytree(HERE, self.klipper, ignore=shutil.ignore_patterns("__pycache__"))
        # frontend.cfg includes the front end's client config from the platform
        frontends = os.path.join("platform", "klipper", "frontends")
        shutil.copytree(os.path.join(ROOT, frontends), os.path.join(self.root, frontends))
        self.sensors = os.path.join(self.root, "temperature_sensors.cfg")
        with open(self.sensors, "w") as f:
            f.write(SENSORS)

    def _run(self, *cmd):
        r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=self.root)
        lines = r.stdout.strip().splitlines()
        return r.returncode, lines

    def pinmap(self, action="check"):
        return self._run(PINMAP, action, "--config", "cad/klipper/printer.cfg", "--map", "cad/klipper/pinmap.json")

    def prepare_check(self):
        return self._run(PREPARE, "--check", "--source", self.root, "--config", "cad/klipper/printer.cfg",
                         "--map", "cad/klipper/pinmap.json", "--sensors", self.sensors)

    def add_bed(self, sensor="Generic 3950"):
        with open(os.path.join(self.klipper, "printer.cfg"), "a") as f:
            f.write(BED.format(sensor=sensor))

    def test_the_config_as_committed_passes(self):
        self.assertEqual(self.pinmap()[0], 0)
        rc, out = self.prepare_check()
        self.assertEqual((rc, out[-1]), (0, "virtual-printer: check OK"), out)
        self.assertIn("virtual-printer: simulated heaters: extruder, extruder1", out)

    def test_a_new_heater_bed_fails_until_the_map_is_regenerated(self):
        self.add_bed()
        rc, out = self.pinmap()
        self.assertEqual((rc, out[-1]), (1, "pinmap: FAILED"), out)
        self.assertIn("pinmap: mcu:PA1 ([heater_bed] heater_pin) is not in the map", out)
        self.assertIn("pinmap: mcu:PF3 ([heater_bed] sensor_pin) is not in the map", out)
        rc, out = self.prepare_check()
        self.assertEqual((rc, out[-1]), (1, "virtual-printer: check FAILED"), out)
        # the fix the failure names: regenerate the map; then the bed is a simulated heater
        self.assertEqual(self.pinmap("generate")[0], 0)
        self.assertEqual(self.pinmap()[0], 0)
        rc, out = self.prepare_check()
        self.assertEqual((rc, out[-1]), (0, "virtual-printer: check OK"), out)
        self.assertIn("virtual-printer: simulated heaters: extruder, extruder1, heater_bed", out)

    def test_a_heater_the_virtual_printer_cant_simulate_fails(self):
        self.add_bed(sensor="PT1000")
        self.assertEqual(self.pinmap("generate")[0], 0)
        rc, out = self.prepare_check()
        self.assertEqual((rc, out[-1]), (1, "virtual-printer: check FAILED"), out)
        self.assertIn("virtual-printer: heater not simulated: [heater_bed]: sensor_type 'PT1000' is not a thermistor",
                      out)


if __name__ == "__main__":
    unittest.main()
