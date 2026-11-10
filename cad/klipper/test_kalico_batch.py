#!/usr/bin/env python3
"""Needs Kalico: runs printer.cfg through real Kalico batch mode in the kalisim container (vt350#116 AC1, AC3, AC4).

    bash cad/klipper/test_in_container.sh      # builds the image, runs this file in it, prints "kalico-batch: OK"

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
ROOT = os.path.dirname(os.path.dirname(HERE))
KALISIM = os.path.join(ROOT, "platform", "kalisim")     # the generic runner (vt350#122); this file is the VT350's
sys.path[:0] = [HERE, os.path.join(ROOT, "platform")]
import dock_params  # noqa: E402
import kalisim  # noqa: E402
import limits  # noqa: E402

KALICO = os.environ.get("KALICO_DIR")
DICTS = os.environ.get("KALISIM_DICTS")
CFG = os.path.join(HERE, "printer.cfg")
# printer.cfg's MCU name -> the kconfig fragment (cad/klipper/kconfig/<name>.config) its dictionary is built from
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
                               "(cad/klipper/test_in_container.sh)")


class PinnedKalico(Base):
    """AC1: a pinned Kalico, one dictionary per MCU in the real wiring."""

    def test_runtime_and_dictionaries_are_the_pinned_commit(self):
        sha = re.search(r"(?m)^ARG KALICO_SHA=([0-9a-f]{40})$", read(KALISIM, "Dockerfile")).group(1)
        self.assertEqual(read(DICTS, "KALICO_SHA").strip(), sha)
        self.assertIn(f"-g{sha[:8]}", read(KALICO, "klippy", ".version"))

    def test_plugin_in_the_image_is_this_repo_s(self):
        self.assertEqual(read(KALICO, "klippy", "plugins", "move_timeline.py"),
                         read(KALISIM, "plugins", "move_timeline.py"))

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
            want = [l for l in read(HERE, "kconfig", f"{frag}.config").splitlines()
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


TOOLCHANGER = os.environ.get("KALISIM_TOOLCHANGER", "/opt/toolchanger")
TC_MODULES = ("toolchanger.py", "tool.py", "tool_probe.py", "tool_probe_endstop.py")


def dock_path(p, tool, kind):
    """The XY waypoints MadMax's pickup_gcode / dropoff_gcode (madmax/toolchanger.cfg) pass through, in order."""
    t, tc = p["tools"][tool], p["toolchanger"]
    park, detach = t["params_park_x"], t["params_detach_x"]
    if kind == "pickup":
        return [(park, tc["params_safe_shuttle_y"]), (park, tc["params_close_y"]), (park, tc["params_attach_y"]),
                (detach, tc["params_attach_y"]), (detach, tc["params_safe_toolhead_y"])]
    return [(detach, tc["params_safe_toolhead_y"]), (detach, tc["params_attach_y"]), (park, tc["params_attach_y"]),
            (park, tc["params_close_y"]), (park, tc["params_safe_shuttle_y"])]


class Toolchange(Base):
    """AC4: MadMax's tool-change macros, on klipper-toolchanger, through a pickup and a dock for each head."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.p = dock_params.derive_committed()
        cls.r = kalisim.run(CFG, read(HERE, "toolchange.gcode").splitlines(), dicts(), KALICO)

    def test_module_is_the_pinned_klipper_toolchanger(self):
        sha = re.search(r"(?m)^ARG TOOLCHANGER_SHA=([0-9a-f]{40})$", read(KALISIM, "Dockerfile")).group(1)
        self.assertEqual(read(TOOLCHANGER, "SHA").strip(), sha)
        for m in TC_MODULES:
            with self.subTest(m=m):
                self.assertEqual(read(KALICO, "klippy", "extras", m), read(TOOLCHANGER, "klipper", "extras", m))

    def test_kalico_s_own_tools_calibrate_is_kept(self):
        # klipper-toolchanger's install.sh would replace it; Kalico ships its own (vt350#116, option A)
        self.assertNotEqual(read(KALICO, "klippy", "extras", "tools_calibrate.py"),
                            read(TOOLCHANGER, "klipper", "extras", "tools_calibrate.py"))

    def test_runs_to_the_end(self):
        self.assertEqual(self.r.returncode, 0, self.r.log[-3000:])
        done = re.findall(r"(?m)^(toolchanger initialized, active None|Selected tool \d \(tool T\d\)|Tool unselected)$",
                          self.r.log)
        self.assertEqual(done, ["toolchanger initialized, active None", "Selected tool 0 (tool T0)",
                                "Selected tool 1 (tool T1)", "Tool unselected"])

    def test_only_the_known_unknown_commands(self):
        # Kalico answers an unknown command with a message and carries on, so these don't stop a tool change. Both come
        # from MadMax's macros: after_change_gcode calls SET_INPUT_SHAPER (needs an [input_shaper], not configured
        # yet), and dropoff_gcode calls STOP_TOOL_PROBE_CRASH_DETECTION, which only [tool_probe_endstop] registers
        # (MadMax's own Beacon config leaves it out too: tool_detection.cfg "tool_probes cause errors when using
        # Beacon"). A new one fails here.
        unknown = re.findall(r'(?m)^Unknown command:"(\w+)"$', self.r.log)
        self.assertEqual(sorted(set(unknown)), ["SET_INPUT_SHAPER", "STOP_TOOL_PROBE_CRASH_DETECTION"])

    def test_each_head_passes_its_dock_waypoints_in_order(self):
        xy = [tuple(m[:2]) for m in self.r.moves()]
        i = 0
        for tool, kind in (("T0", "pickup"), ("T0", "dropoff"), ("T1", "pickup"), ("T1", "dropoff")):
            for w in dock_path(self.p, tool, kind):
                with self.subTest(tool=tool, kind=kind, waypoint=w):
                    hits = [j for j in range(i, len(xy)) if abs(xy[j][0] - w[0]) < 1e-6 and abs(xy[j][1] - w[1]) < 1e-6]
                    self.assertTrue(hits, f"{tool} {kind}: no move to {w} after move {i}: {xy[i:i + 8]}")
                    i = hits[0] + 1

    def test_dock_zone_only_at_the_dock_xs_or_the_shuttle_line(self):
        # printer.cfg lets Y below 0 anywhere along X (the box limit). The macros go there only at a dock's park or
        # detach X, or on the empty carriage's travel line, Y = params_safe_shuttle_y (-26.96 on the VT350: MadMax's
        # distance from the parked heads, which AC5 clash-checks)
        docks = {v for t in self.p["tools"].values() for v in (t["params_park_x"], t["params_detach_x"])}
        shuttle = self.p["toolchanger"]["params_safe_shuttle_y"]
        zone = [(x, y) for x, y, _ in self.r.moves() if y < 0]
        self.assertTrue(zone, "no move below Y 0: the run didn't reach a dock")
        for x, y in zone:
            self.assertTrue(any(abs(x - d) < 1e-6 for d in docks) or abs(y - shuttle) < 1e-6, (x, y))

    def test_committed_timeline_is_current(self):
        want = [json.loads(l) for l in read(HERE, "toolchange_timeline.jsonl").splitlines() if l.strip()]
        self.assertEqual(self.r.timeline, want, "regenerate: see cad/klipper/README.md, 'The tool changes'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
