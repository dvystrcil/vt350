# Tools we use

Every program the VT350's CAD, checks, renders and simulation run on, with the exact version and where that version
is pinned (#124). Two kinds:

- **Pinned in this repo:** the version is written in a file here. `cad/check-tools-page.sh` reads each pin and fails
  if this page disagrees, and CI runs it (`cad/test_tools_page.py`).
- **Installed on the laptop:** nothing here pins it; the version is what was installed on 2026-11-17.
  `cad/check-tools-page.sh --local` compares these against what's installed now (each one it can't find is skipped).

Not a parts list: physical parts are the BOM (#22).

## Pinned in this repo

| Tool | Version | Pinned in | Licence | Link |
|---|---|---|---|---|
| Kalico (klippy source, MCU dictionaries) | `991e1823e983a31d26b9264d2b6305fd64e3a09a` | `platform/kalisim/Dockerfile` (`KALICO_SHA`) | GPL-3.0 | https://github.com/KalicoCrew/kalico |
| Kalico runtime image | `ghcr.io/kalicocrew/kalico@sha256:90a873fe66bfcac6dea7e435becde140292022021da24a20dca023f9fbdc5ea0` | `platform/kalisim/Dockerfile` (second `FROM`) | GPL-3.0 | https://docs.kalico.gg/Installation.html#running-in-docker |
| Builder image (Python, Debian bookworm) | `python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df` | `platform/kalisim/Dockerfile` (first `FROM`) | PSF-2.0 (Python), Debian packages their own | https://hub.docker.com/_/python |
| gcc-arm-none-eabi, binutils, newlib | Debian bookworm's packages, from the builder image's apt (not pinned further) | `platform/kalisim/Dockerfile` | GPL-3.0 (gcc, binutils), BSD-style (newlib) | https://packages.debian.org/bookworm/gcc-arm-none-eabi |
| klipper-toolchanger | `94756dfde9b729fd69f9b8780067821c5c99a528` | `platform/kalisim/Dockerfile` (`TOOLCHANGER_SHA`) | GPL-3.0 | https://github.com/viesturz/klipper-toolchanger |
| FreeCAD | `FreeCAD_26.3rc2-Linux-x86_64.AppImage` (26.3 RC2) | `platform/README.md` (`FREECAD_APPIMAGE`) | LGPL-2.0-or-later | https://www.freecad.org |
| GitHub Actions: checkout | `actions/checkout@v7` | `.github/workflows/*.yml` | MIT | https://github.com/actions/checkout |
| GitHub Actions: cache | `actions/cache@v4` | `.github/workflows/test-tmp.yml` (the static ffmpeg) | MIT | https://github.com/actions/cache |
| GitHub Actions: Pages | `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5` | `.github/workflows/*.yml` | MIT | https://github.com/actions/deploy-pages |
| Secret scan | `dvystrcil/secret-scan-action@v1` | `.github/workflows/*.yml` | the action's own | https://github.com/dvystrcil/secret-scan-action |
| Temp-dir cleanup check | `dvystrcil/tmp-cleanup-action@v1` | `.github/workflows/*.yml` | the action's own | https://github.com/dvystrcil/tmp-cleanup-action |

## Installed on the laptop (2026-11-17)

| Tool | Version | Used for | Licence | Link |
|---|---|---|---|---|
| FreeCAD Fasteners workbench | 0.5.64 | the model's screws, nuts and washers (`Part::FeaturePython` fasteners; `cad/data/fasteners/`) | GPL-2.0-or-later | https://github.com/shaise/FreeCAD_FastenersWB |
| Blender | 5.3.0 | renders (`cad/render/render_full.sh`, `platform/render/render.py`) | GPL-2.0-or-later | https://www.blender.org |
| Docker | 29.10.0 | the Kalico simulation image (`platform/kalisim/`), `act` | Apache-2.0 | https://www.docker.com |
| act | 0.2.98 | running the GitHub workflows locally | MIT | https://github.com/nektos/act |
| ffmpeg | 9.0.2 | motion videos (`platform/render/motion.py`), `test_motion.py` | LGPL-2.1-or-later (GPL build) | https://ffmpeg.org |
| ffmpeg, CI static build | 6.0.1 (John Van Sickle, `old-releases/ffmpeg-6.0.1-amd64-static.tar.xz`, sha256 `28268bf4…07a5`) | `test_motion.py` in `.github/workflows/test-tmp.yml`, from the Actions cache | GPL-3.0 (static build with libx264) | https://johnvansickle.com/ffmpeg/ |
| restic | 0.19.1 | model backups (`cad/backup-models.sh`) | BSD-2-Clause | https://restic.net |
| Python | 3.15.2 (CI: ubuntu-latest's python3) | every script and test | PSF-2.0 | https://www.python.org |
| PrusaSlicer (flatpak `com.prusa3d.PrusaSlicer`) | 2.9.7 | the printed-parts slice check (`platform/parts/slice-check.py`) | AGPL-3.0 | https://github.com/prusa3d/PrusaSlicer |
| OrcaSlicer (flatpak `com.orcaslicer.OrcaSlicer`) | 2.5.1 | the printed-parts slice check (`ORCA_SLICER`) | AGPL-3.0 | https://github.com/SoftFever/OrcaSlicer |
| xvfb-run (Xvfb) | the distribution's | FreeCAD GUI exports without a display (`cad/motion/render_frames.py`) | MIT/X11 | https://www.x.org |

## The batch lane

The cluster batch lane (`homelab/bin/gpu-batch-submit.py`) runs FreeCAD and Blender in images built by
[dvystrcil/gpu-batch-docker](https://github.com/dvystrcil/gpu-batch-docker) (MIT; latest release v0.0.22 on
2026-11-16). Which image tag a chain uses is set in the homelab repo, not here, so this page doesn't pin it.

## Not part of the platform

- freecad-mcp: the repo is archived and nothing deploys it (checked 2026-11-10).
