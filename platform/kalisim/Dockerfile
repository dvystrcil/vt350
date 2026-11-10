# Kalico batch mode with no hardware (vt350#116 AC1). Build context: platform/kalisim. The printer's MCU Kconfig
# fragments (<name>.config, one per MCU) come in as a second, named build context "kconfig" (vt350#122: they are the
# printer's data, not the platform's):
#
#   docker build --build-context kconfig=cad/klipper/kconfig -t vt350-kalisim platform/kalisim
#
# Runtime: Kalico's published container (https://docs.kalico.gg/Installation.html#running-in-docker), pinned by
# digest. It only ships klippy, so the MCU data dictionaries are built in a first stage from the Kalico source at the
# same commit. The image holds:
#   /opt/klipper                                 Kalico 991e182 (klippy/.version v2026.11.00-30-g991e1823), GPL-3.0
#   /opt/klipper/klippy/plugins/move_timeline.py  this repo's timeline plugin
#   /opt/dicts/<name>.dict, <name>.config         one dictionary per MCU, built from the kconfig context's <name>.config
#   /opt/toolchanger                             viesturz/klipper-toolchanger at TOOLCHANGER_SHA (GPL-3.0); its toolchanger,
#                                                tool, tool_probe and tool_probe_endstop modules copied into klippy/extras/
ARG KALICO_SHA=991e1823e983a31d26b9264d2b6305fd64e3a09a
# viesturz/klipper-toolchanger main as of 2026-04-07 (vt350#116 AC4)
ARG TOOLCHANGER_SHA=94756dfde9b729fd69f9b8780067821c5c99a528

# --- build the dictionaries from source -------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS dicts
ARG KALICO_SHA
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates make gcc libc6-dev \
        gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi \
 && rm -rf /var/lib/apt/lists/*
RUN git init -q /src/kalico \
 && git -C /src/kalico fetch -q --depth 1 https://github.com/KalicoCrew/kalico.git "$KALICO_SHA" \
 && git -C /src/kalico checkout -q --detach FETCH_HEAD \
 && test "$(git -C /src/kalico rev-parse HEAD)" = "$KALICO_SHA"
COPY --from=kconfig / /src/kconfig/
COPY build_dicts.sh /src/build_dicts.sh
RUN bash /src/build_dicts.sh /src/kalico /src/kconfig /out/dicts \
 && echo "$KALICO_SHA" > /out/dicts/KALICO_SHA
# klipper-toolchanger (GPL-3.0): [toolchanger] and [tool] for a printer whose config uses them. The whole checkout is
# kept at /opt/toolchanger for reference; only its modules go into klippy (see the runtime stage).
ARG TOOLCHANGER_SHA
RUN git init -q /out/toolchanger \
 && git -C /out/toolchanger fetch -q --depth 1 https://github.com/viesturz/klipper-toolchanger.git "$TOOLCHANGER_SHA" \
 && git -C /out/toolchanger checkout -q --detach FETCH_HEAD \
 && test "$(git -C /out/toolchanger rev-parse HEAD)" = "$TOOLCHANGER_SHA" \
 && rm -rf /out/toolchanger/.git && echo "$TOOLCHANGER_SHA" > /out/toolchanger/SHA

# --- run klippy in the published image ----------------------------------------------------------------------------
# ghcr.io/kalicocrew/kalico:main as of 2026-11-09; klippy/.version says g991e1823 (test_kalico_batch.py checks it
# against KALICO_SHA, so the two stages can't drift apart)
FROM ghcr.io/kalicocrew/kalico@sha256:90a873fe66bfcac6dea7e435becde140292022021da24a20dca023f9fbdc5ea0
COPY --from=dicts /out/dicts/ /opt/dicts/
COPY plugins/move_timeline.py /opt/klipper/klippy/plugins/move_timeline.py
# klipper-toolchanger's modules go into extras/, not plugins/: they import each other and Kalico's probe module
# relatively ("from . import probe"), which only resolves inside klippy.extras. Its install.sh would also link its
# tools_calibrate.py over Kalico's own, so that one is left out.
COPY --from=dicts /out/toolchanger/ /opt/toolchanger/
RUN for m in toolchanger tool tool_probe tool_probe_endstop; do \
        test ! -e "/opt/klipper/klippy/extras/$m.py" || { echo "Kalico already has extras/$m.py"; exit 1; }; \
        cp "/opt/toolchanger/klipper/extras/$m.py" /opt/klipper/klippy/extras/; \
    done
ENV KALICO_DIR=/opt/klipper KALISIM_DICTS=/opt/dicts KALISIM_PYTHON=/opt/venv/bin/python KALISIM_TOOLCHANGER=/opt/toolchanger
ENTRYPOINT []
WORKDIR /opt/klipper
