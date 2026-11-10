#!/usr/bin/env python3
"""Tests for kalisim, the batch-mode runner (vt350#116), against a fake klippy: plain python3, no Kalico.

    python3 cad/klipper/kalisim/test_kalisim.py

The fake (FAKE_KLIPPY below) keeps the contract test_kalico_batch.py checks on the real one: G28 sets the position
to 0, a G1 is refused with "Move out of range: x y z [e]" in the log and exit 255 when a coordinate is past +-1000,
and every accepted move is a "move" line in the timeline file named by [move_timeline] path.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import kalisim  # noqa: E402

FAKE_KLIPPY = r'''
import json, re, sys
args = sys.argv[1:]
cfg, rest = args[0], args[1:]
opt = {}
dicts = []
while rest:
    k, v, rest = rest[0], rest[1], rest[2:]
    if k == "-d":
        dicts.append(v)
    else:
        opt[k] = v
json.dump({"cfg": cfg, "opt": opt, "dicts": dicts, "cfg_text": open(cfg).read()},
          open(opt["-i"] + ".args.json", "w"))
tl = re.search(r"(?m)^path: (.*)$", open(cfg).read()).group(1)
pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
seq = 0
with open(tl, "w") as t, open(opt["-l"], "w") as log:
    log.write("Starting Klippy...\n")
    for line in open(opt["-i"]):
        line = line.strip()
        if line == "G28":
            seq += 1; t.write(json.dumps({"seq": seq, "kind": "set_position", "pos": [0, 0, 0, 0]}) + "\n")
        elif line.startswith("G1"):
            new = dict(pos)
            for a, v in re.findall(r"([XYZ])(-?[0-9.]+)", line):
                new[a] = float(v)
            if any(abs(v) > 5000 for v in new.values()):
                log.write("mcu 'mcu': Unable to connect\n")
                sys.exit(1)
            if any(abs(v) > 1000 for v in new.values()):
                log.write("Move out of range: %.3f %.3f %.3f [0.000]\n" % (new["X"], new["Y"], new["Z"]))
                sys.exit(255)
            if new != pos:
                pos = new; seq += 1
                t.write(json.dumps({"seq": seq, "kind": "move", "pos": [pos["X"], pos["Y"], pos["Z"], 0],
                                    "speed": 100, "tool": "extruder"}) + "\n")
'''

ENVELOPE = """\
; a header comment
; @setup
G28
G90
G1 F6000
; @in-range
; corners
G1 X1 Y2 Z3
G1 X5
; @past x_max
G1 X1000.5
; @past z_min
G1 Z-1000.5
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kalico = os.path.join(self.tmp, "kalico")
        os.makedirs(os.path.join(self.kalico, "klippy"))
        with open(os.path.join(self.kalico, "klippy", "__main__.py"), "w") as f:
            f.write(FAKE_KLIPPY)
        self.cfg = os.path.join(self.tmp, "printer.cfg")
        with open(self.cfg, "w") as f:
            f.write("[printer]\nkinematics: corexy\n")
        self.dicts = [("mcu", "/d/main.dict"), ("o2s_left", "/d/l.dict")]

    def run_lines(self, lines):
        work = os.path.join(self.tmp, "work")
        os.makedirs(work, exist_ok=True)
        return kalisim.run(self.cfg, lines, self.dicts, self.kalico, workdir=work), work


class DictArgs(unittest.TestCase):
    def test_mcu_first_then_named(self):
        self.assertEqual(kalisim.dict_args([("o2s_left", "/l"), ("mcu", "/m"), ("o2s_right", "/r")]),
                         ["-d", "/m", "-d", "o2s_left=/l", "-d", "o2s_right=/r"])

    def test_needs_mcu(self):
        with self.assertRaisesRegex(ValueError, "mcu"):
            kalisim.dict_args([("o2s_left", "/l")])

    def test_names_are_unique(self):
        with self.assertRaisesRegex(ValueError, "o2s_left"):
            kalisim.dict_args([("mcu", "/m"), ("o2s_left", "/l"), ("o2s_left", "/l2")])

    def test_parse_dict_option(self):
        self.assertEqual(kalisim.parse_dict_option("/x/main.dict"), ("mcu", "/x/main.dict"))
        self.assertEqual(kalisim.parse_dict_option("o2s_left=/x/l.dict"), ("o2s_left", "/x/l.dict"))


class Blocks(unittest.TestCase):
    def test_split(self):
        b = kalisim.parse_blocks(ENVELOPE)
        self.assertEqual(list(b), ["setup", "in-range", "past x_max", "past z_min"])
        self.assertEqual(b["setup"], ["G28", "G90", "G1 F6000"])
        self.assertEqual(b["in-range"], ["G1 X1 Y2 Z3", "G1 X5"])
        self.assertEqual(b["past z_min"], ["G1 Z-1000.5"])

    def test_command_before_any_block_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "before"):
            kalisim.parse_blocks("G28\n; @setup\n; @in-range\n")

    def test_setup_and_in_range_are_required(self):
        for text in ("; @setup\nG28\n", "; @in-range\nG1 X1\n"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "setup.*in-range"):
                kalisim.parse_blocks(text)

    def test_duplicate_block_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "past x_max"):
            kalisim.parse_blocks(ENVELOPE + "; @past x_max\nG1 X2000\n")

    def test_move_targets(self):
        self.assertEqual(kalisim.move_targets(["G28", "G90", "G1 F6000", "G1 X1 Y-2.5 Z3 F100", "G0 Z4", "M400",
                                               "G92 X5", "SET_KINEMATIC_POSITION X=1"]),
                         [{"x": 1.0, "y": -2.5, "z": 3.0}, {"z": 4.0}])

    def test_relative_moves_are_refused(self):
        with self.assertRaisesRegex(ValueError, "G91"):
            kalisim.move_targets(["G91", "G1 X1"])


class Run(Base):
    def test_command_line_and_sim_config(self):
        r, work = self.run_lines(["G28", "G1 X1"])
        with open(os.path.join(work, "in.gcode.args.json")) as f:
            a = json.load(f)
        self.assertEqual(a["dicts"], ["/d/main.dict", "o2s_left=/d/l.dict"])
        self.assertEqual(a["opt"]["-o"], os.path.join(work, "out.serial"))
        self.assertEqual(a["opt"]["-l"], os.path.join(work, "klippy.log"))
        self.assertEqual(a["cfg_text"], f"[include {self.cfg}]\n\n[move_timeline]\npath: "
                                        f"{os.path.join(work, 'timeline.jsonl')}\n")
        self.assertEqual(r.returncode, 0)

    def test_result_has_log_and_timeline(self):
        r, _ = self.run_lines(["G28", "G1 X1 Y2", "G1 Z3"])
        self.assertIn("Starting Klippy", r.log)
        self.assertEqual([e["kind"] for e in r.timeline], ["set_position", "move", "move"])
        self.assertEqual(r.moves(), [[1.0, 2.0, 0.0], [1.0, 2.0, 3.0]])

    def test_refused_move(self):
        r, _ = self.run_lines(["G28", "G1 X1", "G1 X2000"])
        self.assertEqual(r.returncode, 255)
        self.assertEqual(r.out_of_range(), [2000.0, 0.0, 0.0])
        self.assertEqual(r.moves(), [[1.0, 0.0, 0.0]])

    def test_no_refusal(self):
        r, _ = self.run_lines(["G28", "G1 X1"])
        self.assertIsNone(r.out_of_range())

    def test_missing_timeline_is_empty(self):
        with open(os.path.join(self.kalico, "klippy", "__main__.py"), "w") as f:
            f.write("import sys\nopen(sys.argv[sys.argv.index('-l') + 1], 'w').write('Config error\\n')\n"
                    "sys.exit(1)\n")
        r, _ = self.run_lines(["G28"])
        self.assertEqual((r.returncode, r.timeline, r.log), (1, [], "Config error\n"))

    def test_temp_workdir_is_removed(self):
        before = set(os.listdir(tempfile.gettempdir()))
        r = kalisim.run(self.cfg, ["G28", "G1 X1"], self.dicts, self.kalico)
        self.assertEqual(r.moves(), [[1.0, 0.0, 0.0]])
        self.assertEqual(set(os.listdir(tempfile.gettempdir())), before)


class Envelope(Base):
    def check(self, text):
        return kalisim.check_envelope(self.cfg, text, self.dicts, self.kalico)

    def test_ok(self):
        ok, lines = self.check(ENVELOPE)
        self.assertTrue(ok, lines)
        self.assertEqual(lines[0], "in-range: 2 moves accepted")
        self.assertRegex(lines[1], r"^past x_max: refused: Move out of range: 1000\.500 0\.000 0\.000")
        self.assertRegex(lines[2], r"^past z_min: refused")
        self.assertEqual(lines[-1], "kalisim-envelope: OK")

    def test_in_range_move_refused(self):
        ok, lines = self.check(ENVELOPE.replace("G1 X5\n", "G1 X5000\n"))
        self.assertFalse(ok)
        self.assertRegex(lines[0], r"^in-range: FAILED: exit 255; refused: Move out of range: 5000")
        self.assertEqual(lines[-1], "kalisim-envelope: FAILED")

    def test_in_range_move_not_where_commanded(self):
        # a no-op move (same as the last) is never planned: the walk didn't reach what it says
        ok, lines = self.check(ENVELOPE.replace("G1 X5\n", "G1 X1\n"))
        self.assertFalse(ok)
        self.assertRegex(lines[0], r"^in-range: FAILED: 1 of 2 moves planned")

    def test_in_range_position_mismatch(self):
        with open(os.path.join(self.kalico, "klippy", "__main__.py")) as f:
            src = f.read()
        with open(os.path.join(self.kalico, "klippy", "__main__.py"), "w") as f:
            f.write(src.replace('pos["X"], pos["Y"]', 'pos["X"] + 0.01, pos["Y"]'))
        ok, lines = self.check(ENVELOPE)
        self.assertFalse(ok)
        self.assertRegex(lines[0], r"^in-range: FAILED: move 1 planned at \[1\.01, 2\.0, 3\.0\], commanded "
                                   r"\{'x': 1\.0, 'y': 2\.0, 'z': 3\.0\}")

    def test_past_move_accepted(self):
        ok, lines = self.check(ENVELOPE.replace("G1 X1000.5", "G1 X999"))
        self.assertFalse(ok)
        self.assertEqual(lines[1], "past x_max: FAILED: accepted (exit 0)")

    def test_past_refused_for_another_move(self):
        # the refusal must name the probe's own target: here Kalico reports a different X than the probe's
        with open(os.path.join(self.kalico, "klippy", "__main__.py")) as f:
            src = f.read()
        with open(os.path.join(self.kalico, "klippy", "__main__.py"), "w") as f:
            f.write(src.replace('% (new["X"], new["Y"]', '% (new["X"] + 1, new["Y"]'))
        ok, lines = self.check(ENVELOPE)
        self.assertEqual(lines[0], "in-range: 2 moves accepted")
        self.assertFalse(ok)
        self.assertRegex(lines[1], r"^past x_max: FAILED: refused at \[1001\.5, 0\.0, 0\.0\], not the probe "
                                   r"\{'x': 1000\.5\}")

    def test_past_failing_for_another_reason(self):
        ok, lines = self.check(ENVELOPE.replace("G1 X1000.5", "G1 X6000"))
        self.assertFalse(ok)
        self.assertEqual(lines[1], "past x_max: FAILED: exit 1 with no \"Move out of range\" (see the klippy log)")

    def test_past_with_a_second_command_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "past x_max: one move"):
            self.check(ENVELOPE.replace("G1 X1000.5\n", "M400\nG1 X1000.5\n"))

    def test_past_with_two_moves_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "past x_max: one move"):
            self.check(ENVELOPE.replace("G1 X1000.5\n", "G1 X1\nG1 X1000.5\n"))

    def test_refusal_rounding(self):
        # the log prints 3 decimals: 346.0125 shows as 346.012 or 346.013
        self.assertTrue(kalisim._matches([346.012, 1.0, 2.0], {"x": 346.0125}, kalisim.LOG_DECIMALS_TOL))
        self.assertTrue(kalisim._matches([346.013, 1.0, 2.0], {"x": 346.0125}, kalisim.LOG_DECIMALS_TOL))
        self.assertFalse(kalisim._matches([346.011, 1.0, 2.0], {"x": 346.0125}, kalisim.LOG_DECIMALS_TOL))
        self.assertFalse(kalisim._matches([346.0125, 1.0, 2.0], {"x": 346.0125, "y": 1.002}, kalisim.LOG_DECIMALS_TOL))


class Cli(Base):
    def test_envelope_command(self):
        gc = os.path.join(self.tmp, "e.gcode")
        with open(gc, "w") as f:
            f.write(ENVELOPE)
        out = kalisim.main(["envelope", "--config", self.cfg, "--gcode", gc, "--kalico", self.kalico,
                            "-d", "/d/main.dict", "-d", "o2s_left=/d/l.dict"])
        self.assertEqual(out[-1], "kalisim-envelope: OK")

    def test_kalico_dir_from_the_environment(self):
        gc = os.path.join(self.tmp, "m.gcode")
        with open(gc, "w") as f:
            f.write("G28\nG1 X1\n")
        old = os.environ.get("KALICO_DIR")
        os.environ["KALICO_DIR"] = self.kalico
        try:
            out = kalisim.main(["run", "--config", self.cfg, "--gcode", gc, "-d", "/d/m.dict"])
        finally:
            if old is None:
                del os.environ["KALICO_DIR"]
            else:
                os.environ["KALICO_DIR"] = old
        self.assertEqual(len(out), 2)

    def test_envelope_failure_exits_nonzero(self):
        gc = os.path.join(self.tmp, "e.gcode")
        with open(gc, "w") as f:
            f.write(ENVELOPE.replace("G1 X1000.5", "G1 X999"))
        with self.assertRaisesRegex(SystemExit, "kalisim-envelope: FAILED"):
            kalisim.main(["envelope", "--config", self.cfg, "--gcode", gc, "--kalico", self.kalico,
                          "-d", "/d/main.dict"])

    def test_run_command_prints_the_timeline(self):
        gc = os.path.join(self.tmp, "m.gcode")
        with open(gc, "w") as f:
            f.write("G28\nG1 X1\n")
        out = kalisim.main(["run", "--config", self.cfg, "--gcode", gc, "--kalico", self.kalico, "-d", "/d/m.dict"])
        self.assertEqual([json.loads(l)["kind"] for l in out], ["set_position", "move"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
