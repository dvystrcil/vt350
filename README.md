# vt350

Build repository for a [Voron Trident 350](https://vorondesign.com/voron_trident) 3D printer — CAD files, research notes, and machine configurations.

Created 2026-05-17 to centralize the build before construction begins.

## Layout

**Picking this back up? Start with [`notes/status.md`](notes/status.md).**

| Path | Purpose |
|---|---|
| `notes/status.md` | Where the build stands: decisions, open questions, where every file lives |
| `notes/scripts.md` | **Scripts at your command:** what to run, when, and how (refresh chain, backups, checks, renders, handoff lanes) |
| `notes/cut-list.md` | Extrusion cut list measured from the model (draft) |
| `notes/reference/` | Styled HTML reference pages (comparisons, part explainers), published at https://dvystrcil.github.io/vt350/ |
| `cad/README.md` | The FreeCAD model files (kept outside git), how each was made, and FreeCAD performance setup |
| `platform/` | The generic tools: FreeCAD clash and pass library, renders, Kalico simulation, parts and pages checks. They take a printer's data and work unchanged for another printer ([#122](https://github.com/dvystrcil/vt350/issues/122)); see [`platform/README.md`](platform/README.md) |
| `cad/passes/` | The VT350's model-writing passes (lite-N): how each working copy was made, with its checks |
| `cad/studies/` | The VT350's studies: toolhead and Z sweeps, print area, frame map, one-off investigations |
| `cad/scripts/` | The VT350's refresh chain (`refresh.py`) and STL derivation (`derive_stls.py`) |
| `cad/data/` | Script inputs/outputs: fastener records, frame map, kept fastener solids, run logs |
| `config/` | Klipper / Mainsail / Moonraker configuration (from build stage #15) |

## License

Our own work is **GPL-3.0-or-later** ([`LICENSE`](LICENSE)). That covers the code, configs, notes, CAD data and our own designs. Third-party parts keep their own licences, and so do our remixes of them; the exceptions are listed below.

Every file's licence is machine-readable: [`REUSE.toml`](REUSE.toml) labels each file, the licence texts are in [`LICENSES/`](LICENSES/), and CI runs `reuse lint` ([REUSE 3.3](https://reuse.software/spec-3.3/)), so an unlabelled file fails the build ([#122](https://github.com/dvystrcil/vt350/issues/122)).

The exception is `cad/derived/`: modified third-party parts, each under its original licence. `cad/derived/madmax-andrewmcgr-dock-arm/` and `cad/derived/madmax-andrewmcgr-carriage-beacon/` are **GPL-3.0** and `cad/derived/a4tv2-duct-4010-madmax-dock/` is **CC BY-NC-SA 4.0** (non-commercial); see the README in each folder.

`parts/printed/` is the other exception: third-party printed parts copied unchanged, each folder with its upstream `LICENSE` (GPL-3.0 or CC BY-NC-SA 4.0), plus copies of the `cad/derived/` remixes. The licence of each source is in [`parts/printed/README.md`](parts/printed/README.md).
