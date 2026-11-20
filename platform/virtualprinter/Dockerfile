# A virtual printer (vt350#224): live Kalico on simulated MCU boards, with Moonraker and Fluidd. Built FROM the
# kalisim image (platform/kalisim, unchanged), so the two share Kalico's layers and Moonraker runs on Kalico's Python.
# Build context: platform/virtualprinter. Two named contexts: "kalisim" isn't one (it's an image, KALISIM_IMAGE),
# "pinmap" is platform/klipper (the pin mapper the container runs at start):
#
#   docker build --build-arg KALISIM_IMAGE=kalisim:local --build-context pinmap=platform/klipper \
#       -t virtual-printer:local platform/virtualprinter
#
# virtualprinter.sh does this (and builds the kalisim image first). Pinned here, on top of what kalisim pins (each pin
# is listed in cad/tools.md, and cad/check-tools-page.sh fails when one isn't):
#   Debian        every apt package at an exact version, from snapshot.debian.org as of DEBIAN_SNAPSHOT
#                 (apt_snapshot.sh), so a rebuild gets the same packages and a version Debian has since replaced
#                 still downloads; the builder image by digest (the other stages are FROM the kalisim image)
#   simulavr      pedrolamas/simulavr 7d6905d (GPL-2.0-or-later): savannah's simulavr master plus CMake fixes for
#                 current Debian; the mirror docker-klipper-simulavr builds from. Savannah's git was down (502) on
#                 2026-11-19 when this was written. Checked by commit and by the sha256 of its tree (git archive), so
#                 SIMULAVR_URL can point at any other copy (a fork, a local mirror) and still build the same source.
#   firmware      Kalico at the kalisim image's own commit (/opt/dicts/KALICO_SHA), built for a simulavr atmega644p
#                 from simulavr.config
#   Moonraker     Arksine/moonraker v0.11.0 = 985c1d0 (GPL-3.0); its Python packages at the versions in
#                 moonraker-requirements.txt (with sha256 hashes), in their own venv on the image's python
#   Fluidd        fluidd-core/fluidd v1.37.7 release fluidd.zip (GPL-3.0), checked by sha256
#   nginx, supervisor: Debian trixie packages (the Kalico image's Debian), from the same snapshot
ARG KALISIM_IMAGE=kalisim:local
ARG DEBIAN_SNAPSHOT=20261120T000000Z
ARG SIMULAVR_URL=https://github.com/pedrolamas/simulavr.git
ARG SIMULAVR_SHA=7d6905de000955f4a7f60b7f39c067b86d40817a
ARG SIMULAVR_TREE_SHA256=6d195bbaea9b1c27e508de4f42142cc38ee2a93a06b0841b4146f52b9bb3a03f
ARG MOONRAKER_SHA=985c1d0bbeb90bc057d34a232c9dc3b05e0c6c8d
ARG FLUIDD_VERSION=v1.37.7
ARG FLUIDD_SHA256=e45889071dae4e79f22e38bfb28cad0ce0c89e134c09d174cd447c4c93bd9556

FROM ${KALISIM_IMAGE} AS kalisim

# --- the simulated boards' firmware: Kalico for a simulavr atmega644p, at the kalisim image's commit -------------
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS firmware
ARG DEBIAN_SNAPSHOT
COPY apt_snapshot.sh /usr/local/sbin/
RUN sh /usr/local/sbin/apt_snapshot.sh "$DEBIAN_SNAPSHOT" \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        git=1:2.39.5-0+deb12u3 ca-certificates=20250419~deb12u2 make=4.3-4.1 gcc=4:12.2.0-3 \
        libc6-dev=2.36-9+deb12u14 gcc-avr=1:5.4.0+Atmel3.6.2-3 avr-libc=1:2.0.0+Atmel3.6.2-3 \
        binutils-avr=2.26.20160125+Atmel3.6.2-4 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=kalisim /opt/dicts/KALICO_SHA /src/KALICO_SHA
RUN sha=$(cat /src/KALICO_SHA) \
 && git init -q /src/kalico \
 && git -C /src/kalico fetch -q --depth 1 https://github.com/KalicoCrew/kalico.git "$sha" \
 && git -C /src/kalico checkout -q --detach FETCH_HEAD \
 && test "$(git -C /src/kalico rev-parse HEAD)" = "$sha"
COPY simulavr.config build_firmware.sh /src/
RUN bash /src/build_firmware.sh /src/kalico /src/simulavr.config /out/firmware \
 && cp /src/KALICO_SHA /out/firmware/KALICO_SHA \
 && cp -r /src/kalico/docs /out/docs
# Fluidd's static files, from the release zip
ARG FLUIDD_VERSION
ARG FLUIDD_SHA256
ADD --checksum=sha256:${FLUIDD_SHA256} \
    https://github.com/fluidd-core/fluidd/releases/download/${FLUIDD_VERSION}/fluidd.zip /src/fluidd.zip
RUN python3 -m zipfile -e /src/fluidd.zip /out/fluidd && echo "$FLUIDD_VERSION" > /out/fluidd/FLUIDD_VERSION

# --- simulavr's python module and Moonraker's venv, built on the image's own python ------------------------------
FROM kalisim AS build
USER root
ARG DEBIAN_SNAPSHOT
COPY apt_snapshot.sh /usr/local/sbin/
RUN sh /usr/local/sbin/apt_snapshot.sh "$DEBIAN_SNAPSHOT" \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        git=1:2.47.3-0+deb13u1 ca-certificates=20250419+deb13u1 make=4.4.1-2 cmake=3.31.6-2 g++=4:14.2.0-1 \
        swig=4.3.0-1 gcc-avr=1:14.2.0-2 avr-libc=1:2.2.1-1 \
 && rm -rf /var/lib/apt/lists/*
ARG SIMULAVR_URL
ARG SIMULAVR_SHA
ARG SIMULAVR_TREE_SHA256
# simulavr builds its python module with setuptools, which python 3.12+ no longer bundles (build stage only)
COPY simulavr-build-requirements.txt /src/
RUN python3 -m pip install -q --no-cache-dir --root-user-action=ignore --require-hashes --no-deps --only-binary=:all: \
        -r /src/simulavr-build-requirements.txt
# a full clone: simulavr's CMake takes its version from the newest tag (git describe); its CMake also wants avr-gcc,
# for the regression tests it declares (not run). The commit, then the sha256 of its tree (git archive's tar, which
# holds every file's path, mode and content), so a copy from anywhere must be the same source.
RUN git clone -q "$SIMULAVR_URL" /src/simulavr \
 && git -C /src/simulavr checkout -q --detach "$SIMULAVR_SHA" \
 && test "$(git -C /src/simulavr rev-parse HEAD)" = "$SIMULAVR_SHA" \
 && tree=$(git -C /src/simulavr archive --format=tar HEAD | sha256sum | cut -d' ' -f1) \
 && { [ "$tree" = "$SIMULAVR_TREE_SHA256" ] \
      || { echo "simulavr: tree sha256 $tree, expected $SIMULAVR_TREE_SHA256"; exit 1; }; } \
 && cd /src/simulavr \
 && CXXFLAGS="-Wno-overloaded-virtual" make cfgclean python build \
 && mkdir -p /out/pysimulavr \
 && strip build/pysimulavr/_pysimulavr*.so -o /out/pysimulavr/_pysimulavr.so \
 && cp build/pysimulavr/pysimulavr.py /out/pysimulavr/ \
 && echo "$SIMULAVR_SHA" > /out/pysimulavr/SIMULAVR_SHA
ARG MOONRAKER_SHA
COPY moonraker-requirements.txt /src/
RUN git init -q /opt/moonraker \
 && git -C /opt/moonraker fetch -q --depth 1 https://github.com/Arksine/moonraker.git "$MOONRAKER_SHA" \
 && git -C /opt/moonraker checkout -q --detach FETCH_HEAD \
 && test "$(git -C /opt/moonraker rev-parse HEAD)" = "$MOONRAKER_SHA" \
 && python3 -m venv /opt/moonraker-env \
 && grep -v '^--find-links' /opt/moonraker/scripts/moonraker-requirements.txt > /src/moonraker-req.txt \
 && /opt/moonraker-env/bin/pip install -q --no-cache-dir --only-binary=:all: \
        --require-hashes --no-deps -r /src/moonraker-requirements.txt \
 && /opt/moonraker-env/bin/pip install -q --no-index -r /src/moonraker-req.txt \
 && /opt/moonraker-env/bin/pip check

# --- the virtual printer -----------------------------------------------------------------------------------------
FROM kalisim
USER root
ARG DEBIAN_SNAPSHOT
COPY apt_snapshot.sh /usr/local/sbin/
RUN sh /usr/local/sbin/apt_snapshot.sh "$DEBIAN_SNAPSHOT" \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        supervisor=4.2.5-3 nginx-light=1.26.3-3+deb13u11 libsodium23=1.0.18-1+deb13u1 curl=8.14.1-2+deb13u7 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=firmware /out/firmware/ /opt/virtualprinter/firmware/
COPY --from=firmware /out/fluidd/ /opt/fluidd/
# Kalico's docs at the same commit: Moonraker serves <klipper_path>/docs as its "docs" root and warns ("Supplied path
# (/opt/klipper/docs) for (docs) is invalid") when it's missing, and the published Kalico image ships without them
COPY --from=firmware /out/docs/ /opt/klipper/docs/
COPY --from=build /out/pysimulavr/ /opt/virtualprinter/pysimulavr/
COPY --from=build /opt/moonraker/ /opt/moonraker/
COPY --from=build /opt/moonraker-env/ /opt/moonraker-env/
COPY --from=pinmap pinmap.py /opt/virtualprinter/pinmap.py
COPY prepare.py reset_watch.py heatsim.py entrypoint.sh nginx.conf /opt/virtualprinter/
# klippy, Moonraker and the configs a viewer edits all live in /opt/printer_data (the Kalico image's data folder);
# ~/printer_data points there, for configs that name a file in it (a save file, [save_variables]).
RUN mkdir -p /opt/printer_data/comms /opt/printer_data/database \
 && chown -R kalico:kalico /opt/printer_data \
 && ln -s /opt/printer_data /home/kalico/printer_data \
 && test "$(cat /opt/virtualprinter/firmware/KALICO_SHA)" = "$(cat /opt/dicts/KALICO_SHA)"
USER kalico
ENV VP_DATA=/opt/printer_data VP_RUN=/tmp/virtualprinter
EXPOSE 8080
ENTRYPOINT ["/opt/virtualprinter/entrypoint.sh"]
