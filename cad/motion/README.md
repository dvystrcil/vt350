# cad/motion: playing the firmware's moves on the model

Kalico batch mode (`cad/klipper/`) gives a **timeline**: every move the firmware planned, in printer coordinates. The files here say how the VT350 model moves for a given printer position, so a player can animate it ([#135](https://github.com/dvystrcil/vt350/issues/135)).

| File | What it is |
|---|---|
| `rig.json` | Generated. The VT350's rig for `platform/freecad/timeline.py`: the XY mapping, the bed's Z, and each head's docked nozzle, pickup offset and dock |
| `rig.py` | VT350-specific. Derives `rig.json` from `cad/data/logs/sweep_toolhead.log`, `cad/klipper/xy_mapping.json` and `cad/klipper/toolchanger.cfg`; `--check` fails if it differs |
| `test_rig.py` | The derivation, and the committed tool-change timeline played through the rig. Plain python3 |

```sh
python3 cad/motion/rig.py --check              # "rig: OK"
python3 cad/motion/rig.py --write              # after a CAD log or toolchanger.cfg changes
python3 platform/freecad/timeline.py --timeline cad/klipper/toolchange_timeline.jsonl --rig cad/motion/rig.json --fps 30
```

## How the model moves

Every group moves by translation from the saved model pose. The groups are the ones `cad/studies/sweep_toolhead.py` finds:

- **bed:** Z. Its dZ is `top_dz − Z` (93.32 at Z 0 puts the magnet sheet at the nozzle tip).
- **gantry and belt:** Y, with the carriage.
- **carriage:** X and Y. It's placed so the carried head's nozzle is at the printer position. With no head on it, the left head's offsets place it.
- **heads:** a docked head doesn't move. The carried head moves with the carriage.

**The handover comes from the dock geometry, not the timeline's `tool` field.** Kalico switches extruders before the pickup moves, so `tool` already names the next head while the carriage is still empty. Instead, a head couples when the carriage passes its docked nozzle point moving into the dock (−Y, toward `params_attach_y`), and uncouples when it passes that point moving out. The 6 mm push to the keyslots' large opening therefore moves the head with the carriage, and on dropoff the head stays where the carriage leaves it.

**Limits:**
- Timing uses each move's commanded speed, with no acceleration, so it is approximate. The path is exact, since every planned move is a straight line.
- The XY mapping is still PROPOSED (#116).
- The model's dock expects the carriage 0.315 mm higher than the gantry carriage (`sweep_toolhead.log`), so a carried head sits 0.315 mm low.
