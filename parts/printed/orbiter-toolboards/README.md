# Orbiter-Toolboards: the Orbitool O2S wire restraint

Copied **unchanged** from [LorinczElectronics/Orbiter-Toolboards](https://github.com/LorinczElectronics/Orbiter-Toolboards) at commit [`52a5a33`](https://github.com/LorinczElectronics/Orbiter-Toolboards/tree/52a5a330e1c57ea71ecdc2192382872b0b254452). By Lorincz Electronics (Orbiter, Orbitool).

**Licence:** **CC0-1.0** (the upstream repository's `LICENSE`, copied here unchanged): public domain dedication, no conditions. Credited anyway.

The strain relief for the cable that plugs into the Orbitool O2S toolboard (vt350#19). It clamps the cable to the board so the plug doesn't take the pull from the cable chain or the toolchanger's moves. The model has one on each head since lite-35, placed where the upstream O2S assembly puts it. Print one body and one lock per tool.

| File here | Upstream path at the pinned commit | Qty | Our changes |
|---|---|---|---|
| `O2S-WirerestrainBody.stl` | [`Orbiter O2S Toolboard/3D CAD/O2S WirerestrainBody.stl`](https://github.com/LorinczElectronics/Orbiter-Toolboards/blob/52a5a330e1c57ea71ecdc2192382872b0b254452/Orbiter%20O2S%20Toolboard/3D%20CAD/O2S%20WirerestrainBody.stl) | 2 | none (renamed: no space) |
| `O2S-Wirestrain_Lock.stl` | [`Orbiter O2S Toolboard/3D CAD/O2S Wirestrain_Lock.stl`](https://github.com/LorinczElectronics/Orbiter-Toolboards/blob/52a5a330e1c57ea71ecdc2192382872b0b254452/Orbiter%20O2S%20Toolboard/3D%20CAD/O2S%20Wirestrain_Lock.stl) | 2 | none (renamed: no space) |

Upstream updated the body on 2025-11-03 (after the assembly STEP the model's O2S came from) and added an alternative, `Orbitool O2S Wire restrain Straight.stl` (a straight cable exit), which isn't copied here. The model uses the current body from `Orbitool O2S Wire restrain.step` at the same commit (lite-35).

Each file's sha256 is in `../manifest.csv`; `platform/parts/check-printed.py --upstream` re-downloads every file at its commit and compares.
