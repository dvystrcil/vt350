# MadMax tool-change macros (vendored, unchanged)

Copied **unchanged** from [zruncho3d/madmax](https://github.com/zruncho3d/madmax) at commit [`277a63c`](https://github.com/zruncho3d/madmax/tree/277a63cbb696f937fbf9d883a8d8c46a658cd6d9/Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger), the config the owner chose for [vt350#116](https://github.com/dvystrcil/vt350/issues/116) AC4 (option A, 2026-11-10). By zruncho3d and the MadMax contributors (config by r2pdx).

**Licence:** **GPL-3.0** (the upstream repository's `LICENSE`, copied here unchanged).

| File here | Upstream path at the pinned commit | git blob |
|---|---|---|
| `toolchanger.cfg` | [`Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger/toolchanger.cfg`](https://github.com/zruncho3d/madmax/blob/277a63cbb696f937fbf9d883a8d8c46a658cd6d9/Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger/toolchanger.cfg) | `06e94bda` |
| `toolchanger_macros.cfg` | [`Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger/toolchanger_macros.cfg`](https://github.com/zruncho3d/madmax/blob/277a63cbb696f937fbf9d883a8d8c46a658cd6d9/Configs/r2pdx_config-v2-Kalico-Beacon-2025-07-05/klipper-toolchanger/toolchanger_macros.cfg) | `3f4c8abc` |

`../test_dock_params.py` checks each file's git blob id (the full ids are in `../dock_params.py`). Don't edit these files. The VT350's values go in `../toolchanger.cfg`, which includes both files and then repeats `[toolchanger]` to override MadMax's dock positions.

The macros run on [viesturz/klipper-toolchanger](https://github.com/viesturz/klipper-toolchanger) at `94756df` (GPL-3.0). The kalisim image installs it (`platform/kalisim/Dockerfile`).
