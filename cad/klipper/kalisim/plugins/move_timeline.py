# Kalico plugin: write every planned toolhead move to a timeline file, one JSON object per line (vt350#116).
#
# Copyright (C) 2026 dvystrcil
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file runs inside Kalico (GPL-3.0), so it is GPL-3.0-or-later; see cad/klipper/kalisim/README.md.
#
#   [move_timeline]
#   path: /some/dir/timeline.jsonl
#
# Records, in order:
#   {"seq": 1, "kind": "set_position", "pos": [x, y, z, e], "tool": "extruder"}   homing, SET_KINEMATIC_POSITION
#   {"seq": 2, "kind": "move", "pos": [x, y, z, e], "speed": 100.0, "tool": "extruder"}   a move the host accepted
# A move the host refuses ("Move out of range") raises before it is recorded, so it never appears.
# Positions are the toolhead's commanded (gcode-space after transforms) X, Y, Z and E. The file is line-buffered, so
# it is complete up to the last accepted move even when batch mode exits on an error.
import json


class MoveTimeline:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.path = config.get("path")
        self.seq = 0
        self.fh = open(self.path, "w", buffering=1)
        self.printer.register_event_handler("klippy:connect", self._connect)

    def _write(self, rec):
        self.seq += 1
        self.fh.write(json.dumps(dict(seq=self.seq, **rec)) + "\n")

    def _tool(self, toolhead):
        return toolhead.get_extruder().get_name()

    def _connect(self):
        # Wrap the toolhead's methods on the instance: gcode_move binds toolhead.move at klippy:ready, after this.
        toolhead = self.printer.lookup_object("toolhead")
        move, set_position = toolhead.move, toolhead.set_position

        def logged_move(newpos, speed):
            before = toolhead.get_position()
            move(newpos, speed)
            after = toolhead.get_position()
            if after != before:
                self._write({"kind": "move", "pos": [round(v, 6) for v in after[:4]],
                             "speed": round(speed, 6), "tool": self._tool(toolhead)})

        def logged_set_position(newpos, *args, **kwargs):
            set_position(newpos, *args, **kwargs)
            self._write({"kind": "set_position", "pos": [round(v, 6) for v in toolhead.get_position()[:4]],
                         "tool": self._tool(toolhead)})

        toolhead.move, toolhead.set_position = logged_move, logged_set_position


def load_config(config):
    return MoveTimeline(config)
