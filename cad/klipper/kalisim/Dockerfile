# Kalico batch mode with no hardware (vt350#116 AC1). Build context: cad/klipper/kalisim
#
#   docker build -t vt350-kalisim cad/klipper/kalisim
#
# Runtime: Kalico's published container (https://docs.kalico.gg/Installation.html#running-in-docker), pinned by
# digest. It only ships klippy, so the MCU data dictionaries are built in a first stage from the Kalico source at the
# same commit. The image holds:
#   /opt/klipper                                 Kalico 991e182 (klippy/.version v2026.11.00-30-g991e1823), GPL-3.0
#   /opt/klipper/klippy/plugins/move_timeline.py  this repo's timeline plugin
#   /opt/dicts/<name>.dict, <name>.config         one dictionary per MCU, built from kconfig/<name>.config
ARG KALICO_SHA=991e1823e983a31d26b9264d2b6305fd64e3a09a

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
COPY kconfig/ /src/kconfig/
COPY build_dicts.sh /src/build_dicts.sh
RUN bash /src/build_dicts.sh /src/kalico /src/kconfig /out/dicts \
 && echo "$KALICO_SHA" > /out/dicts/KALICO_SHA

# --- run klippy in the published image ----------------------------------------------------------------------------
# ghcr.io/kalicocrew/kalico:main as of 2026-11-09; klippy/.version says g991e1823 (test_kalico_batch.py checks it
# against KALICO_SHA, so the two stages can't drift apart)
FROM ghcr.io/kalicocrew/kalico@sha256:90a873fe66bfcac6dea7e435becde140292022021da24a20dca023f9fbdc5ea0
COPY --from=dicts /out/dicts/ /opt/dicts/
COPY plugins/move_timeline.py /opt/klipper/klippy/plugins/move_timeline.py
ENV KALICO_DIR=/opt/klipper KALISIM_DICTS=/opt/dicts KALISIM_PYTHON=/opt/venv/bin/python
ENTRYPOINT []
WORKDIR /opt/klipper
