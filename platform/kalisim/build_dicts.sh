#!/usr/bin/env bash
# Build one Kalico data dictionary per MCU from the Kconfig fragments in kconfig/ (vt350#116 AC1).
#
#   build_dicts.sh <kalico checkout> <kconfig dir> <dest dir>
#
# For each kconfig/<name>.config it resolves the full config (make olddefconfig), checks that every setting the
# fragment asks for survived resolution, builds the firmware, and copies out/klipper.dict to <dest>/<name>.dict and
# the resolved config to <dest>/<name>.config. A setting Kconfig dropped (a misspelt symbol, an unmet dependency)
# fails the build: olddefconfig drops those silently.
# Prints "build-dicts: OK" on success.
set -euo pipefail
kalico=$1; frags=$2; dest=$3
mkdir -p "$dest"
n=0
for frag in "$frags"/*.config; do
    name=$(basename "$frag" .config)
    out="/tmp/kalico-out-$name"; cfg="$out/.config"
    rm -rf "$out"; mkdir -p "$out"
    grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$frag" > "$cfg"
    make -C "$kalico" -s OUT="$out/" KCONFIG_CONFIG="$cfg" olddefconfig
    while IFS= read -r want; do
        grep -qxF -- "$want" "$cfg" || { echo "build-dicts: $name: Kconfig dropped '$want'"; exit 1; }
    done < <(grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$frag")
    make -C "$kalico" -s -j"$(nproc)" OUT="$out/" KCONFIG_CONFIG="$cfg"
    cp "$out/klipper.dict" "$dest/$name.dict"
    cp "$cfg" "$dest/$name.config"
    rm -rf "$out"
    echo "build-dicts: $name.dict ($(wc -c < "$dest/$name.dict") bytes)"
    n=$((n + 1))
done
(( n > 0 )) || { echo "build-dicts: no fragments in $frags"; exit 1; }
echo "build-dicts: OK"
