# Our remixes (vt350)

The current printable version of each part this build changes. Each folder keeps the licence of the part it was made
from: **GPL-3.0** for the MadMax / andrewmcgr parts, **CC BY-NC-SA 4.0** for the A4Tv2 ducts, and this repo's GPL-3.0-or-later for
the user's own BTT base.

| Folder | Part | From model | Made by |
|---|---|---|---|
| `madmax-andrewmcgr-carriage-beacon/` | MadMax carriage, Beacon RevH pocket, **9 mm belts** | lite-25 (#58, PR #62) | `cad/passes/lite25_carriage_9mm.py` |
| `madmax-andrewmcgr-dock-arm/` | Dock arm, −9.06 mm (×4) | lite-23 (#53) | `cad/passes/lite23_cowl_docks.py` + `derive_stls.py` |
| `a4tv2-duct-4010-madmax-dock/` | A4Tv2 4010 ducts with dock bosses, left + right | lite-23 (#53) | `cad/passes/lite23_cowl_docks.py` + `derive_stls.py`. **Not yet print-oriented** (#53 AC8) |
| `btt5160-base-4-middle-screws/` | BTT TMC5160T Plus base | none (Fusion 360, 2026-05-16) | the user, by hand |

The first three are **copies of `cad/derived/`**, where the CAD scripts write them. `platform/parts/check-printed.py` fails if a
copy here differs from its source there, so re-copy after re-running a script. Superseded versions are left out: they
stay in `cad/derived/` as the record of older models (the 6 mm-belt carriage from lite-24, `Dock Arm +5mm.stl` from
lite-14…22).

**Not copied from `cad/data/stl/`** (untracked, the scripts' raw exports in the printer model's frame): the ducts and
`dock_arm_v1_bottom_minus9.06mm*` are the same parts as here, before `derive_stls.py` puts them in the upstream print
frame (same volume to 0.1 %; each arm file holds both arms of one dock); `dock_arm_v1_bottom_minus8.76mm*` is an
earlier lite-23 run, superseded by −9.06; `madmax_carriage_beacon_pocket.stl` is the lite-24 6 mm-belt carriage,
superseded by lite-25.
