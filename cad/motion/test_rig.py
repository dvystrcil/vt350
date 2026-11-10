#!/usr/bin/env python3
"""Tests for rig.py: the VT350 rig from the CAD logs and the tool-change config, and the committed timeline played
through it (vt350#135 AC2).

Plain python3, no FreeCAD, no Kalico:  python3 cad/motion/test_rig.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, "platform", "freecad")]
import rig  # noqa: E402
import timeline  # noqa: E402

SWEEP = """\
[   32.9s] Left: pickup carriage offset (-154.000, -257.725, 0.315) from the gantry carriage; same part: volume diff 0.000 mm3
[   32.9s] Right: pickup carriage offset (153.014, -257.725, 0.315) from the gantry carriage; same part: volume diff 0.000 mm3
[   32.9s] Left: docked nozzle tip (-399.00, -32.46, 380.80)
[   32.9s] Right: docked nozzle tip (-92.00, -32.46, 380.80)
[   32.9s] Left carried: nozzle tip Z 380.48; bed top dZ +93.32 (magnet top 287.16 -> 380.48); nozzle Y reach -51.93 .. 370.69
[   32.9s] Right carried: nozzle tip Z 380.49; bed top dZ +93.32 (magnet top 287.16 -> 380.49); nozzle Y reach -51.93 .. 370.69
"""
MAP = {"origin_model_xy": [-420.0, 30.5], "sign_xy": [1, 1]}
DOCK = {"toolchanger": {"params_attach_y": -68.96},
        "tools": {"T0": {"params_park_x": 21.0}, "T1": {"params_park_x": 328.0}}}


def read(*p):
    with open(os.path.join(*p)) as f:
        return f.read()


class Derive(unittest.TestCase):
    def setUp(self):
        self.r = rig.derive(SWEEP, MAP, DOCK)

    def test_mapping_and_groups(self):
        self.assertEqual(self.r["xy"], MAP)
        self.assertEqual(self.r["bed"], {"group": "bed", "top_dz": 93.32})
        self.assertEqual(self.r["gantry_groups"], ["gantry", "belt"])
        self.assertEqual(self.r["carriage_group"], "carriage")
        self.assertEqual(self.r["reference_head"], "Left")

    def test_heads(self):
        self.assertEqual(self.r["heads"], {
            "Left": {"group": "Left", "tool": "T0", "nozzle": [-399.0, -32.46, 380.8], "pickup": [-154.0, -257.725, 0.315],
                     "dock": [21.0, -62.96], "into": [0, -1]},
            "Right": {"group": "Right", "tool": "T1", "nozzle": [-92.0, -32.46, 380.8],
                      "pickup": [153.014, -257.725, 0.315], "dock": [328.0, -62.96], "into": [0, -1]}})

    def test_dock_into_follows_the_attach_side(self):
        r = rig.derive(SWEEP, MAP, {"toolchanger": {"params_attach_y": -50.0}, "tools": DOCK["tools"]})
        self.assertEqual(r["heads"]["Left"]["into"], [0, 1])

    def test_park_x_must_be_the_docked_nozzle(self):
        bad = {"toolchanger": DOCK["toolchanger"], "tools": {"T0": {"params_park_x": 22.0}, "T1": {"params_park_x": 328.0}}}
        with self.assertRaisesRegex(ValueError, "T0 park_x 22.0.*docked nozzle at printer X 21.0"):
            rig.derive(SWEEP, MAP, bad)

    def test_heads_disagree_on_the_bed_fails(self):
        with self.assertRaisesRegex(ValueError, "bed top dZ"):
            rig.derive(SWEEP.replace("dZ +93.32 (magnet top 287.16 -> 380.49)", "dZ +93.40 (x)"), MAP, DOCK)

    def test_missing_lines_fail_loudly(self):
        for gone in ("pickup carriage offset", "bed top dZ"):
            with self.subTest(gone=gone), self.assertRaisesRegex(ValueError, gone):
                rig.derive("\n".join(l for l in SWEEP.splitlines() if gone not in l), MAP, DOCK)


class Committed(unittest.TestCase):
    """rig.json matches the CAD, and the committed tool-change timeline plays through it with the right handovers."""

    def test_rig_json_is_current(self):
        self.assertEqual(rig.main(["--check"])[-1], "rig: OK")

    def test_toolchange_hands_the_heads_over_in_order(self):
        r = json.loads(read(HERE, "rig.json"))
        records = [json.loads(l) for l in read(ROOT, "cad", "klipper", "toolchange_timeline.jsonl").splitlines() if l]
        held = [s["carried"] for s in timeline.segments(r, records)]
        runs = [h for i, h in enumerate(held) if i == 0 or h != held[i - 1]]
        self.assertEqual(runs, [None, "Left", None, "Right", None])     # T0 pickup, T0 dock, T1 pickup, T1 dock

    def test_t0_pushed_to_the_large_opening_then_docked_where_it_started(self):
        r = json.loads(read(HERE, "rig.json"))
        records = [json.loads(l) for l in read(ROOT, "cad", "klipper", "toolchange_timeline.jsonl").splitlines() if l]
        fr = timeline.frames(r, records, fps=None)
        at = [f for f in fr if f["pos"][:2] == [21.0, -68.96] and f["carried"] == "Left"][0]
        self.assertEqual(at["groups"]["Left"], [0.0, -6.0, -0.315])      # the 6 mm keyslot slide, model -Y
        self.assertEqual(fr[-1]["groups"]["Left"], [0.0, 0.0, 0.0])
        self.assertEqual(fr[-1]["groups"]["Right"], [0.0, 0.0, 0.0])

    def test_bed_reaches_the_configured_floor(self):
        # z_sweep.log's floor is bed dZ -237.00 at printer Z 330.33; the log's 2-decimal top dZ leaves 0.01 mm
        r = json.loads(read(HERE, "rig.json"))
        self.assertAlmostEqual(timeline.groups(r, (175.0, 175.0, 330.33), None)["bed"][2], -237.0, delta=0.011)


if __name__ == "__main__":
    unittest.main(verbosity=2)
