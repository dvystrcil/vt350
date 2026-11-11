# cad/motion: playing the firmware's moves on the model

Kalico batch mode (`cad/klipper/`) gives a **timeline**: every move the firmware planned, in printer coordinates. The files here say how the VT350 model moves for a given printer position, so a player can animate it ([#135](https://github.com/dvystrcil/vt350/issues/135)).

| File | What it is |
|---|---|
| `rig.json` | Generated. The VT350's rig for `platform/freecad/timeline.py`: the XY mapping, the bed's Z, and each head's docked nozzle, pickup offset and dock |
| `rig.py` | VT350-specific. Derives `rig.json` from `cad/data/logs/sweep_toolhead.log`, `cad/klipper/xy_mapping.json` and `cad/klipper/toolchanger.cfg`; `--check` fails if it differs |
| `test_rig.py` | The derivation, and the committed tool-change timeline played through the rig. Plain python3 |
| `play.py` | VT350-specific. Opens the FreeCAD GUI player (`platform/freecad/player.py`) on the model. It gets the groups from `cad/studies/sweep_toolhead.py`'s plan stage and caches them in `$VT350_WORK/motion/` |
| `test_play.py` | The plan's groups named the way the rig names them, the cache, the default model and the FreeCAD command. Plain python3 |
| `render_frames.py` | VT350-specific. Real-renderer (Blender) frames of the timeline and a video of the dock moves: one grouped mesh export, `frames.json`, the batch-lane job, the MP4. Everything in `$VT350_WORK/motion/` |
| `test_render_frames.py` | The export's cache key and judgement, the docks camera, the frames, the batch-lane command. Plain python3 |

```sh
python3 cad/motion/rig.py --check              # "rig: OK"
python3 cad/motion/rig.py --write              # after a CAD log or toolchanger.cfg changes
python3 platform/freecad/timeline.py --timeline cad/klipper/toolchange_timeline.jsonl --rig cad/motion/rig.json --fps 30
python3 cad/motion/play.py                     # watch it in FreeCAD: play/pause, step, speed, stop
python3 cad/motion/play.py --speed 0.25        # start in slow motion
```

## The FreeCAD player

`play.py` opens FreeCAD with a **Motion player** panel on the right. **Play/Pause** plays the timeline at the speed factor. **|<** and **>|** step one frame (1/30 s of timeline) and pause. The slider scrubs. **Stop** puts every Placement back and returns to the first frame. The panel shows the frame's time, timeline seq, printer X/Y/Z and which head is on the carriage.

The player opens a **private copy** of the model in a temp dir, never the model itself. Even File → Save only writes the copy, and the copy is removed when the panel closes. The first run on a model takes about a minute, for the plan stage. After that, the groups come from the cache.

**The belts are clipped.** Each belt is one loop, and its side runs change length as the gantry moves in Y, so the whole loop can't move rigidly. The player shows only the part in the XY joints' Y band (the X runs and the idler wraps, `sweep_toolhead.BELT_CLIP`), the same part the clash sweep checks, and it moves with the gantry. The side runs are hidden while the player is open. Before this, the whole loop moved with the gantry and shot out the front of the frame.

**The docks' carriage copies are hidden.** Each dock holds a copy of the carriage at its pickup pose (the plan stage gets the pickup offset from it). The moving carriage takes its place, so the player hides both copies (`dock_copies` in the plan: the two carriage compounds and their SpeedClips). Before this, a ghost carriage stayed in the dock once the real one left.

Don't recompute while it plays. Some moved parts feed a boolean or compound, and a recompute would rebuild those from the moved inputs. Press Stop first.

## Real-renderer frames and video

```sh
python3 cad/motion/render_frames.py prepare                  # groups + ONE mesh export (FreeCAD GUI, xvfb) + frames.json
python3 cad/motion/render_frames.py submit                   # Blender frames in the batch lane; result comment on #135
python3 cad/motion/render_frames.py encode <job>/out         # frames -> notes/reference/toolchange-docks.mp4
python3 cad/motion/render_frames.py stills --at 21,-68.96    # full-size stills at the move ends at a printer XY
```

The meshes are exported **once**, at the model pose, with the player's groups (`play.py`'s cached groups file: clipped belts, dock copies left out). Each group's parts go in buckets of their own (`platform/render/export_meshes.py` with `VT350_GROUPS`), so Blender moves each group's objects by the frame's translation (`platform/render/render.py --frames`). Nothing is re-exported per frame. The export is cached in `$VT350_WORK/motion/render-<model>-<key>/export`, keyed by the groups file, the exporter and the colour map. That directory is also the batch-lane input: `prepare` copies `colours.py`, `colours.json` and `motion.py` into it, since the lane stages only the script. The camera, `docks`, is computed from the rig: aimed at the middle of the docked nozzles.

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
