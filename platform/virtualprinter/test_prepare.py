#!/usr/bin/env python3
"""prepare.py, without Docker (vt350#224): the config tree it writes, the supervisord and Moonraker configs.

    python3 platform/virtualprinter/test_prepare.py
"""
import configparser
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "klipper"))
import prepare  # noqa: E402

PRINTER = """\
[mcu]
serial: /dev/serial/by-id/usb-Klipper_stm32h723xx_X-if00

[mcu tool]
serial: /dev/serial/by-id/usb-Klipper_stm32f072xb_T-if00
restart_method: command

[stepper_x]
step_pin: PF13
endstop_pin: ^PG6

[extruder]
heater_pin: tool:PB9
sensor_pin: tool:PA1
sensor_type: ATC Semitec 104GT-2
min_temp: 0
max_temp: 300

[include sub/more.cfg]
"""
MORE = "[fan]\npin: !tool:PA10\n"
MAP = ('{"target": "simulavr-atmega644p", "mcus": {"mcu": {"PF13": "PC0", "PG6": "PC1"},'
       ' "tool": {"PA1": "PA0", "PA10": "PC1", "PB9": "PC0"}}}')


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class Prepare(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        t = self._tmp.name
        self.src = os.path.join(t, "src")
        _write(os.path.join(self.src, "printer", "printer.cfg"), PRINTER)
        _write(os.path.join(self.src, "printer", "sub", "more.cfg"), MORE)
        _write(os.path.join(self.src, "printer", "pinmap.json"), MAP)
        _write(os.path.join(self.src, "printer", "save.cfg"), "[gcode_macro x]\ngcode:\n")
        self.data = os.path.join(t, "data")
        self.home = os.path.join(t, "home")
        self.run_dir = os.path.join(t, "run")
        self.before = self._snapshot(self.src)

    def tearDown(self):
        self._tmp.cleanup()

    def _snapshot(self, root):
        out = {}
        for d, _, files in os.walk(root):
            for f in files:
                with open(os.path.join(d, f)) as fh:
                    out[os.path.join(d, f)] = fh.read()
        return out

    def _prepare(self, home_files=None):
        return prepare.prepare(source=self.src, config="printer/printer.cfg", pin_map="printer/pinmap.json",
                               data=self.data, run=self.run_dir, home=self.home, home_files=home_files or {},
                               firmware="/fw/klipper.elf")

    def test_config_tree_pins_rewritten_and_source_untouched(self):
        self._prepare()
        cfg = os.path.join(self.data, "config")
        with open(os.path.join(cfg, "src", "printer.cfg")) as f:
            text = f.read()
        self.assertIn("step_pin: PC0", text)
        self.assertIn("endstop_pin: ^PC1", text)
        self.assertIn("sensor_pin: tool:PA0", text)
        with open(os.path.join(cfg, "src", "sub", "more.cfg")) as f:
            self.assertIn("pin: !tool:PC1", f.read())
        self.assertEqual(self._snapshot(self.src), self.before)

    def test_top_config_includes_the_tree_and_points_each_mcu_at_its_simulator(self):
        self._prepare()
        with open(os.path.join(self.data, "config", "printer.cfg")) as f:
            text = f.read()
        self.assertTrue(text.index("[include src/printer.cfg]") < text.index("[mcu]"))
        cp = configparser.ConfigParser(strict=False)
        cp.read_string(text.replace("[include src/printer.cfg]", ""))
        self.assertEqual(cp["mcu"]["serial"], os.path.join(self.run_dir, "mcu.tty"))
        self.assertEqual(cp["mcu tool"]["serial"], os.path.join(self.run_dir, "tool.tty"))
        self.assertEqual(cp["mcu"]["baud"], "250000")
        # no DTR on a pty: every board is reset by command, and reset_watch.py restarts its simulator
        self.assertEqual(cp["mcu"]["restart_method"], "command")
        self.assertEqual(cp["mcu tool"]["restart_method"], "command")

    def test_homing_on_simulated_endstops_does_not_retract(self):
        # a simulated endstop input reads its pull-up: triggered from the start, so a homing retract never clears it
        self._prepare()
        with open(os.path.join(self.data, "config", "printer.cfg")) as f:
            text = f.read()
        cp = configparser.ConfigParser(strict=False)
        cp.read_string(text.replace("[include src/printer.cfg]", ""))
        self.assertEqual(cp["stepper_x"]["homing_retract_dist"], "0")
        self.assertNotIn("extruder", cp.sections())

    def test_supervisord_runs_one_simulator_per_mcu_then_klippy_moonraker_nginx(self):
        paths = self._prepare()
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(paths["supervisord"])
        progs = sorted(s for s in cp.sections() if s.startswith("program:"))
        self.assertEqual(progs, ["program:klippy", "program:moonraker", "program:nginx", "program:reset-watch",
                                 "program:simulavr-mcu", "program:simulavr-tool"])
        watch = cp["program:reset-watch"]["command"]
        self.assertIn(os.path.join(self.data, "logs", "klippy.log"), watch)
        self.assertIn(paths["supervisord"], watch)
        sim = cp["program:simulavr-tool"]["command"]
        self.assertIn("-p " + os.path.join(self.run_dir, "tool.tty"), sim)
        self.assertIn("-m atmega644p", sim)
        self.assertTrue(sim.endswith("/fw/klipper.elf"))
        klippy = cp["program:klippy"]["command"]
        self.assertIn(os.path.join(self.data, "config", "printer.cfg"), klippy)
        self.assertIn("-a " + os.path.join(self.data, "comms", "klippy.sock"), klippy)
        for s in cp.sections():
            if s.startswith("program:"):
                self.assertEqual(cp[s]["autorestart"], "true", s)
        # nothing outside the data and run folders
        for key in ("logfile", "pidfile"):
            self.assertTrue(cp["supervisord"][key].startswith(("/dev/", self.run_dir)), key)

    def test_moonraker_talks_to_klippys_socket(self):
        self._prepare()
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(os.path.join(self.data, "config", "moonraker.conf"))
        self.assertEqual(cp["server"]["klippy_uds_address"], os.path.join(self.data, "comms", "klippy.sock"))
        self.assertEqual(cp["server"]["host"], "127.0.0.1")
        self.assertIn("172.16.0.0/12", cp["authorization"]["trusted_clients"])

    def test_home_files_are_seeded(self):
        self._prepare({"printer_data/config/offset_save_file.cfg": "printer/save.cfg"})
        with open(os.path.join(self.home, "printer_data", "config", "offset_save_file.cfg")) as f:
            self.assertIn("[gcode_macro x]", f.read())

    def test_home_file_outside_home_is_refused(self):
        with self.assertRaises(ValueError):
            self._prepare({"../escape.cfg": "printer/save.cfg"})
        with self.assertRaises(ValueError):
            self._prepare({"x.cfg": "../../etc/passwd"})

    def test_rerun_replaces_the_previous_tree(self):
        self._prepare()
        stale = os.path.join(self.data, "config", "src", "stale.cfg")
        _write(stale, "x")
        self._prepare()
        self.assertFalse(os.path.exists(stale))


if __name__ == "__main__":
    unittest.main()
