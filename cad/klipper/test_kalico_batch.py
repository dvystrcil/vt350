#!/usr/bin/env python3
"""Needs Kalico: runs printer.cfg through real Kalico batch mode in the kalisim container (vt350#116 AC1, AC3, AC4).

    bash cad/klipper/test_in_container.sh      # builds the image, runs this file in it, prints "kalico-batch: OK"

Inside the image: $KALICO_DIR is Kalico, $KALISIM_DICTS holds one dictionary per MCU. Without them this file fails
instead of skipping: a skipped run would look green. check_test_tmp.sh skips it ("Needs Kalico" above).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KALISIM = os.path.join(ROOT, "platform", "kalisim")     # the generic runner (vt350#122); this file is the VT350's
sys.path[:0] = [HERE, os.path.join(ROOT, "platform"), os.path.join(ROOT, "platform", "klipper")]
import dock_params  # noqa: E402
import frontend  # noqa: E402
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


# A real install starts its offset save file as a copy of MadMax's (cad/klipper/README.md, "Nozzle offsets"): the
# T<n> macros read every tool's offsets from it (tc_offsets.cfg)
SAVE_SEED = {"printer_data/config/offset_save_file.cfg": os.path.join(HERE, "madmax", "offset_save_file.cfg")}


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
        cfg = limits.load_cfg(CFG)                       # printer.cfg + includes (vt350#294)
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
        zmin = float(limits.load_cfg(CFG)["stepper_z"]["position_min"])      # printer.cfg + includes (vt350#294)
        self.assertLess(zmin, 0)
        zs = [t["z"] for t in kalisim.move_targets(kalisim.parse_blocks(read(HERE, "envelope.gcode"))["in-range"])]
        self.assertIn(zmin, zs)

    def test_walk_reaches_the_z_sweep_floor(self):
        want = re.findall(r"klipper_position_max_configured_mm=([0-9.]+)", read(ROOT, "cad/data/logs/z_sweep.log"))
        zs = [t["z"] for t in kalisim.move_targets(kalisim.parse_blocks(read(HERE, "envelope.gcode"))["in-range"])]
        self.assertEqual(max(zs), float(want[-1]))
        self.assertEqual(float(limits.load_cfg(CFG)["stepper_z"]["position_max"]), float(want[-1]))


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
        cls.r = kalisim.run(CFG, read(HERE, "toolchange.gcode").splitlines(), dicts(), KALICO, home_files=SAVE_SEED)

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


class Frontends(Base):
    """Fluidd is the VT350's front end (owner, 2026-11-10); switching to Mainsail must still load and run the same."""

    def test_each_front_end_runs_the_tool_changes(self):
        want = [json.loads(l) for l in read(HERE, "toolchange_timeline.jsonl").splitlines() if l.strip()]
        # client.cfg-only commands: they exist only if the front end's macros loaded
        extra = ["SET_PAUSE_NEXT_LAYER ENABLE=0", "SET_PAUSE_AT_LAYER ENABLE=0"]
        for name in sorted(frontend.FRONTENDS):
            with self.subTest(front_end=name), tempfile.TemporaryDirectory() as d:
                # a copy of the repo layout, so frontend.cfg's relative include still resolves
                shutil.copytree(HERE, os.path.join(d, "cad", "klipper"))
                os.symlink(os.path.join(ROOT, "platform"), os.path.join(d, "platform"))
                cfg = os.path.join(d, "cad", "klipper", "frontend.cfg")
                frontend.main(["--config", cfg, "--use", name])
                r = kalisim.run(os.path.join(d, "cad", "klipper", "printer.cfg"),
                                read(HERE, "toolchange.gcode").splitlines() + extra, dicts(), KALICO,
                                home_files=SAVE_SEED)
                self.assertEqual(r.returncode, 0, r.log[-2000:])
                # the logged config shows which client.cfg loaded: the two differ only in spacing, e.g. CANCEL_PRINT's
                # "client.park_at_cancel | default(false)" (Fluidd) vs "client.park_at_cancel|default(false)" (Mainsail)
                marker = {"fluidd": "park_at_cancel | default(false)", "mainsail": "park_at_cancel|default(false)"}
                self.assertIn(marker[name], read(frontend.client_cfg(name)))
                self.assertIn(marker[name], r.log)
                self.assertNotIn("SET_PAUSE", " ".join(re.findall(r'(?m)^Unknown command:"(\w+)"$', r.log)))
                self.assertEqual(r.timeline, want)


# The Mellow MultiHead Zero's ball, printer coordinates: cad/data/logs/lite61_offset_probe.log "nozzle reaches all 4
# sides: X -255..-235 ... Y 8..28" -> centre model (-245, 18) -> printer (175, -12.5); its top is about Z 10.
ZERO_XY = (175.0, -12.5)


class TcOffsets(Base):
    """vt350#186 AC2: MadMax's offset macros save what Kalico's tools_calibrate measured, not 0 and not an error.

    Batch mode has no probe to touch: every probing move simply runs its full 100 mm (Kalico's run_probe max_distance)
    or to the axis limit. So the run starts 100 mm above the ball's top, and the wrapper below lowers Z position_min
    and loosens samples_tolerance so the synthetic sequence can finish. The numbers it measures mean nothing; the test
    only checks that the macros carry them into the save file unchanged.
    """

    SEQ = ["G28", "G90", "G1 X175 Y175 Z10 F6000", "INITIALIZE_TOOLCHANGER",
           "T0", f"G0 X{ZERO_XY[0]} Y{ZERO_XY[1]} Z110 F6000", "TC_GET_PROBE_POSITION",
           "T1", "_NUDGE_MOVE_OVER_PROBE", "TOOL_CALIBRATE_TOOL_OFFSET", "_TC_UPDATE_OFFSETS TOOL=1"]

    # _SHOW N=<n> records the G-code offset and both part fans' speeds as show<n> in the save file. (Not a RESPOND:
    # batch mode discards klippy's replies, and only some reach the log.)
    SHOW = ("[gcode_macro _SHOW]\ngcode:\n  {% set o = printer.gcode_move.homing_origin %}\n"
            "  {% set v = \"'%.3f %.3f %.3f %.2f %.2f'\" % (o.x, o.y, o.z, printer['fan_generic part_fan_t0'].speed, "
            "printer['fan_generic part_fan_t1'].speed) %}\n"
            "  SAVE_VARIABLE VARIABLE=show{params.N} VALUE=\"{v}\"\n")

    def run_macros(self, lines, extra="", seed=None):
        """(Result, saved variables) for lines, with the save file in a temporary copy of MadMax's (or seed's text)."""
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(HERE, "madmax", "offset_save_file.cfg"), os.path.join(d, "offsets.cfg"))
            if seed is not None:
                with open(os.path.join(d, "offsets.cfg"), "w") as f:
                    f.write(seed)
            cfg = os.path.join(d, "wrap.cfg")
            with open(cfg, "w") as f:
                f.write(f"[include {CFG}]\n{self.SHOW}{extra}"
                        "[stepper_z]\nposition_min: -1000\nhoming_positive_dir: false\n"
                        "[tools_calibrate]\nsamples_tolerance: 1000\n"
                        f"[save_variables]\nfilename: {d}/offsets.cfg\n")
            r = kalisim.run(cfg, lines, dicts(), KALICO, workdir=d)
            saved = dict(re.findall(r"(?m)^(\w+) = (.*)$", read(d, "offsets.cfg")))
        return r, saved

    @staticmethod
    def logged(r, what):
        """The last x, y, z Kalico logged as "Sensor location at x,y,z" or "Tool offset is x,y,z", to 3 places."""
        m = re.findall(rf"(?m)^{what} (?:at|is) ([-0-9.]+),([-0-9.]+),([-0-9.]+)$", r.log)
        return [round(float(v), 3) for v in m[-1]]

    def test_saves_what_kalico_measured(self):
        r, saved = self.run_macros(self.SEQ)
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        loc, off = self.logged(r, "Sensor location"), self.logged(r, "Tool offset")
        self.assertEqual([float(saved[f"nudge_position_{a}"]) for a in "xyz"], [loc[0], loc[1], round(loc[2] + 3, 3)])
        self.assertEqual([float(saved[f"t1_offset_{a}"]) for a in "xyz"], off)
        self.assertNotEqual(off, [0.0, 0.0, 0.0])     # batch mode's synthetic contacts give T1 a non-zero Z offset
        self.assertEqual(round(loc[0], 3), ZERO_XY[0])

    # MELLOW_CALIBRATE_START / _RUN (tc_offsets.cfg, vt350#291): the Mellow goes on the plate by hand between them
    POS = ("[gcode_macro _POS]\ngcode:\n  SAVE_VARIABLE VARIABLE=pos_y VALUE={printer.toolhead.position.y}\n"
           "  SAVE_VARIABLE VARIABLE=pos_z VALUE={printer.toolhead.position.z}\n")

    def test_mellow_start_homes_and_drops_the_bed(self):
        r, saved = self.run_macros(["MELLOW_CALIBRATE_START", "_POS"], self.POS)
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        y, z = float(saved["pos_y"]), float(saved["pos_z"])
        self.assertEqual(z, 60.0)                        # bed_z: the nozzles ~10 mm above the Mellow's pin
        self.assertGreater(y, 300.0)                     # the toolhead at the back, out of the hands' way

    def test_mellow_run_stops_without_a_probe_position(self):
        r, saved = self.run_macros(["MELLOW_CALIBRATE_START", "MELLOW_CALIBRATE_RUN TOOL=1"])
        self.assertIn("the Mellow's position isn't saved", r.log)
        self.assertEqual(saved["t1_offset_z"], "0.0")

    def test_mellow_run_stops_unhomed(self):
        r, saved = self.run_macros(["MELLOW_CALIBRATE_RUN TOOL=1"])
        self.assertIn("not homed: run MELLOW_CALIBRATE_START first", r.log)

    def test_mellow_two_steps_save_the_offsets(self):
        r, saved = self.run_macros(["MELLOW_CALIBRATE_START", "INITIALIZE_TOOLCHANGER", "T0",
                                    f"G0 X{ZERO_XY[0]} Y{ZERO_XY[1]} Z110 F6000", "TC_GET_PROBE_POSITION",
                                    "MELLOW_CALIBRATE_RUN TOOL=1", "_POS"], self.POS)
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        # T0's baseline and T1 both start at the saved position, so the simulator's contacts give 0: what matters is
        # that the offset run happened and its result was saved
        self.assertEqual([float(saved[f"t1_offset_{a}"]) for a in "xyz"], self.logged(r, "Tool offset"))
        # then the bed back down and the toolhead at the back, for the hands to take the Mellow off
        self.assertEqual(float(saved["pos_z"]), 60.0)
        self.assertGreater(float(saved["pos_y"]), 300.0)

    def test_madmax_s_own_macros_fail_on_kalico(self):
        # the reason tc_offsets.cfg replaces them: Kalico reports last_result, not last_x/y/z_result
        r, saved = self.run_macros(self.SEQ, f"[include {os.path.join(HERE, 'madmax', 'tc_offset_calibration_macros.cfg')}]\n"
                                             "[tools_calibrate]\npin: ^PG11\n")
        self.assertIn("UndefinedError: 'dict object' has no attribute 'last_x_result'", r.log)
        self.assertEqual(saved["nudge_position_x"], "-1000")
        self.assertEqual(saved["t1_offset_z"], "0.0")

    def test_no_offset_run_saves_nothing(self):
        # straight after TOOL_LOCATE_SENSOR, last_result is the sensor's position, not an offset
        r, saved = self.run_macros(self.SEQ[:7] + ["_TC_UPDATE_OFFSETS TOOL=1"])
        self.assertIn("last_result is the sensor position, not an offset", r.log)
        self.assertEqual([saved[f"t1_offset_{a}"] for a in "xyz"], ["0.0", "0.0", "0.0"])

    @staticmethod
    def shows(lines):
        """lines with each "_SHOW" numbered: _SHOW N=1, N=2, ..."""
        n, out = 0, []
        for l in lines:
            if l == "_SHOW":
                n += 1
                l = f"_SHOW N={n}"
            out.append(l)
        return out

    @staticmethod
    def states(saved):
        """[(origin x, y, z, part fan t0, t1)] from each _SHOW, in order."""
        n = sorted(int(k[4:]) for k in saved if re.fullmatch(r"show\d+", k))
        return [tuple(float(v) for v in saved[f"show{i}"].strip("'").split()) for i in n]

    START = ["G28", "G90", "G1 X175 Y175 Z10 F6000", "INITIALIZE_TOOLCHANGER"]

    def test_measured_offset_is_applied_on_the_tool_change(self):
        r, saved = self.run_macros(self.shows(self.SEQ + ["T0", "_SHOW", "T1", "_SHOW"]))
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        off = self.logged(r, "Tool offset")
        self.assertEqual([s[:3] for s in self.states(saved)], [(0.0, 0.0, 0.0), tuple(off)])

    def test_each_tool_gets_its_own_saved_offset(self):
        seed = read(HERE, "madmax", "offset_save_file.cfg").replace("t1_offset_x = 0.0", "t1_offset_x = 0.123") \
            .replace("t1_offset_y = 0.0", "t1_offset_y = -0.456").replace("t1_offset_z = 0.0", "t1_offset_z = 0.789")
        r, saved = self.run_macros(self.shows(self.START + [
            "T0", "_SHOW", "T1", "_SHOW", "T0", "_SHOW",
            # a Z tweak made while printing carries over to the next tool (MadMax's modified_z)
            "T1", "SET_GCODE_OFFSET Z_ADJUST=0.05", "T0", "_SHOW"]), seed=seed)
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        self.assertEqual([s[:3] for s in self.states(saved)],
                         [(0.0, 0.0, 0.0), (0.123, -0.456, 0.789), (0.0, 0.0, 0.0), (0.0, 0.0, 0.05)])

    def test_part_fan_follows_the_tool(self):
        # Batch mode applies a fan change only once motion follows it (Kalico's fan request queue is flushed by the
        # move queue; a dwell isn't enough), so each change is followed by a move before it's read
        mv = lambda x: [f"G1 X{x} Y175 F6000", "M400", "_SHOW"]
        r, saved = self.run_macros(self.shows(self.START + ["T0", "M106 S255"] + mv(170) + ["T1"] + mv(180)
                                              + ["M107"] + mv(170)))
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        self.assertEqual([s[3:] for s in self.states(saved)], [(1.0, 0.0), (0.0, 1.0), (0.0, 0.0)])

    def test_fan_set_just_before_a_change_reaches_the_new_tool(self):
        # A slicer may set the fan, make a move, then change tools. _CHANGE_TOOL reads the fan speed when it starts,
        # and Kalico reports a fan's speed only once its request is applied (when the queued moves flush): without a
        # flush first, it reads the old speed and the new tool's fan starts off
        r, saved = self.run_macros(self.shows(self.START + ["T0", "M106 S127.5", "G1 X170 Y175 F6000", "T1",
                                                            "G1 X180 Y175 F6000", "M400", "_SHOW"]))
        self.assertEqual(r.returncode, 0, r.log[-3000:])
        self.assertEqual([s[3:] for s in self.states(saved)], [(0.0, 0.5)])

    def test_missing_offsets_stop_the_tool_change_with_a_fix(self):
        r, _ = self.run_macros(self.START + ["T1"], seed="[Variables]\nt0_offset_x = 0.0\n")
        self.assertIn("the offset save file has no t0_offset_y, t0_offset_z, t1_offset_x, t1_offset_y, t1_offset_z: "
                      "copy madmax/offset_save_file.cfg", r.log)
        self.assertNotIn("Selected tool 1", r.log)

    def test_no_result_yet_is_an_error(self):
        r, saved = self.run_macros(["G28", "_TC_SAVE_PROBE_POSITION"])
        self.assertIn("tools_calibrate has no result yet", r.log)
        self.assertEqual(saved["nudge_position_x"], "-1000")


if __name__ == "__main__":
    unittest.main(verbosity=2)
