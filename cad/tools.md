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
| Debian snapshot (the builder's apt packages) | `20261120T000000Z` (kalisim) | `platform/kalisim/Dockerfile` (`DEBIAN_SNAPSHOT`; `platform/kalisim/apt_snapshot.sh` points apt at snapshot.debian.org) | the packages' own | https://snapshot.debian.org |
| MCU dictionary build, Debian bookworm | kalisim: `git=1:2.39.5-0+deb12u3`, `ca-certificates=20250419~deb12u2`, `make=4.3-4.1`, `gcc=4:12.2.0-3`, `libc6-dev=2.36-9+deb12u14`, `gcc-arm-none-eabi=15:12.2.rel1-1`, `binutils-arm-none-eabi=2.40-2+18+b1`, `libnewlib-arm-none-eabi=3.3.0-1.3+deb12u1` | `platform/kalisim/Dockerfile` (`dicts` stage) | GPL (git, make, gcc, binutils), LGPL-2.1 (glibc), BSD-style (newlib), MPL-2.0 (ca-certificates) | https://packages.debian.org/bookworm/gcc-arm-none-eabi |
| klipper-toolchanger | `94756dfde9b729fd69f9b8780067821c5c99a528` | `platform/kalisim/Dockerfile` (`TOOLCHANGER_SHA`) | GPL-3.0 | https://github.com/viesturz/klipper-toolchanger |
| FreeCAD | `FreeCAD_26.3rc2-Linux-x86_64.AppImage` (26.3 RC2) | `platform/README.md` (`FREECAD_APPIMAGE`) | LGPL-2.0-or-later | https://www.freecad.org |
| GitHub Actions: checkout | `actions/checkout@v7`; `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (v7, by SHA: `repin-virtualprinter.yml`, which can write to the repo) | `.github/workflows/*.yml` | MIT | https://github.com/actions/checkout |
| GitHub Actions: cache | `actions/cache@v4` | `.github/workflows/test-tmp.yml` (the static ffmpeg) | MIT | https://github.com/actions/cache |
| GitHub Actions: Pages | `actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5` | `.github/workflows/*.yml` | MIT | https://github.com/actions/deploy-pages |
| Secret scan | `dvystrcil/secret-scan-action@v1` | `.github/workflows/*.yml` | the action's own | https://github.com/dvystrcil/secret-scan-action |
| Temp-dir cleanup check | `dvystrcil/tmp-cleanup-action@v1` | `.github/workflows/*.yml` | the action's own | https://github.com/dvystrcil/tmp-cleanup-action |

### The virtual printer (#224)

Built FROM the kalisim image above (`platform/virtualprinter/Dockerfile`), so the Kalico pins there apply too. Debian packages come
from **snapshot.debian.org** as of one moment (`DEBIAN_SNAPSHOT`, set by `platform/virtualprinter/apt_snapshot.sh`), each at an exact
version. The snapshot is what keeps a rebuild working: Debian's mirrors drop a package version as soon as a security
or point release replaces it, so exact versions alone stop building within weeks; the snapshot serves every version
forever, and the exact versions make a changed snapshot fail loudly instead of quietly installing something else.
Python packages are pinned by version and sha256 (`pip install --require-hashes`; hashes written by
`platform/virtualprinter/pip_lock.py`).

| Tool | Version | Pinned in | Licence | Link |
|---|---|---|---|---|
| Debian snapshot (every apt package below) | `20261120T000000Z` | `platform/virtualprinter/Dockerfile` (`DEBIAN_SNAPSHOT`) | the packages' own | https://snapshot.debian.org |
| Firmware builder image | `python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df` (as kalisim's) | `platform/virtualprinter/Dockerfile` (first `FROM`) | PSF-2.0 (Python), Debian packages their own | https://hub.docker.com/_/python |
| Firmware build, Debian bookworm | `git=1:2.39.5-0+deb12u3`, `ca-certificates=20250419~deb12u2`, `make=4.3-4.1`, `gcc=4:12.2.0-3`, `libc6-dev=2.36-9+deb12u14`, `gcc-avr=1:5.4.0+Atmel3.6.2-3`, `avr-libc=1:2.0.0+Atmel3.6.2-3`, `binutils-avr=2.26.20160125+Atmel3.6.2-4` | `platform/virtualprinter/Dockerfile` (`firmware` stage) | GPL (git, make, gcc, binutils), LGPL-2.1 (glibc), BSD-style (avr-libc), MPL-2.0 (ca-certificates) | https://packages.debian.org/bookworm/gcc-avr |
| simulavr build, Debian trixie | `git=1:2.47.3-0+deb13u1`, `ca-certificates=20250419+deb13u1`, `make=4.4.1-2`, `cmake=3.31.6-2`, `g++=4:14.2.0-1`, `swig=4.3.0-1`, `gcc-avr=1:14.2.0-2`, `avr-libc=1:2.2.1-1` | `platform/virtualprinter/Dockerfile` (`build` stage) | GPL (git, make, gcc, swig), BSD-3-Clause (cmake), BSD-style (avr-libc), MPL-2.0 (ca-certificates) | https://packages.debian.org/trixie/swig |
| Runtime, Debian trixie | `supervisor=4.2.5-3`, `nginx-light=1.26.3-3+deb13u11`, `libsodium23=1.0.18-1+deb13u1`, `curl=8.14.1-2+deb13u7` | `platform/virtualprinter/Dockerfile` (last stage) | BSD-style (supervisor, nginx), ISC (libsodium), curl licence | https://packages.debian.org/trixie/nginx-light |
| simulavr | `7d6905de000955f4a7f60b7f39c067b86d40817a` (pedrolamas/simulavr mirror; tree sha256 `6d195bbaea9b1c27e508de4f42142cc38ee2a93a06b0841b4146f52b9bb3a03f`; fallback: the fork https://github.com/dvystrcil/simulavr via `SIMULAVR_URL`) | `platform/virtualprinter/Dockerfile` (`SIMULAVR_SHA`, `SIMULAVR_TREE_SHA256`, `SIMULAVR_URL`) | GPL-2.0-or-later | https://github.com/pedrolamas/simulavr |
| simulavr's build python package | `setuptools==80.9.0` (with sha256) | `platform/virtualprinter/simulavr-build-requirements.txt` | MIT | https://pypi.org/project/setuptools/ |
| Moonraker | `985c1d0bbeb90bc057d34a232c9dc3b05e0c6c8d` (v0.11.0) | `platform/virtualprinter/Dockerfile` (`MOONRAKER_SHA`) | GPL-3.0 | https://github.com/Arksine/moonraker |
| Moonraker's Python packages (each with sha256) | `aiofiles==25.1.0`, `apprise==1.13.0`, `certifi==2026.10.23`, `charset-normalizer==3.5.2`, `click==8.5.1`, `dbus-fast==5.0.22`, `distro==1.9.0`, `idna==3.20`, `ifaddr==0.2.0`, `importlib_metadata==9.0.0`, `inotify-simple==2.0.1`, `Jinja2==3.1.6`, `ldap3==2.9.1`, `libnacl==2.1.0`, `Markdown==3.11.3`, `MarkupSafe==3.0.4`, `oauthlib==4.0.1`, `paho-mqtt==2.1.0`, `pillow==12.3.0`, `preprocess_cancellation==0.2.1`, `pyasn1==0.6.5`, `pyserial==3.4`, `python-periphery==2.4.1`, `PyYAML==6.0.3`, `requests==2.34.2`, `requests-oauthlib==2.0.0`, `smart_open==9.0.6`, `streaming-form-data==2.1.0`, `tornado==6.5.8`, `urllib3==2.8.0`, `wrapt==2.5.2`, `zeroconf==0.150.0`, `zipp==4.1.2` | `platform/virtualprinter/moonraker-requirements.txt` | each package's own | https://pypi.org |
| Fluidd | `v1.37.7`, release `fluidd.zip` sha256 `e45889071dae4e79f22e38bfb28cad0ce0c89e134c09d174cd447c4c93bd9556` | `platform/virtualprinter/Dockerfile` (`FLUIDD_VERSION`, `FLUIDD_SHA256`) | GPL-3.0 | https://github.com/fluidd-core/fluidd |

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
