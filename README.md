# vt350

Build repository for a [Voron Trident 350](https://vorondesign.com/voron_trident) 3D printer — CAD files, research notes, and machine configurations.

Created 2026-05-17 to centralize the build before construction begins.

## Layout

**Picking this back up? Start with [`notes/status.md`](notes/status.md).**

| Path | Purpose |
|---|---|
| `notes/status.md` | Where the build stands: decisions, open questions, where every file lives |
| `notes/cut-list.md` | Extrusion cut list measured from the model (draft) |
| `cad/README.md` | The FreeCAD model files (kept outside git), how each was made, and FreeCAD performance setup |
| `cad/scripts/` | FreeCAD scripts that produced each model working copy, with their checks |
| `cad/data/` | Script inputs/outputs: fastener records, frame map, kept fastener solids, run logs |
| `config/` | Klipper / Mainsail / Moonraker configuration (from build stage #15) |

If the prose under `notes/` grows substantial, this repo will move to a
dual-license setup (MIT for code/configs + CC-BY-4.0 for prose) per the
[repo-protections convention](https://github.com/dvystrcil/skills/tree/main/repo-protections).

## License

[MIT](LICENSE).

The exception is `cad/derived/`: modified third-party parts, each under its original licence. `cad/derived/madmax-andrewmcgr-dock-arm/` is **GPL-3.0** and `cad/derived/a4tv2-duct-4010-madmax-dock/` is **CC BY-NC-SA 4.0** (non-commercial); see the README in each folder.
