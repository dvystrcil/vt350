#!/usr/bin/env bash
# Build Kalico's simulavr firmware from a Kconfig fragment (vt350#224).
#
#   build_firmware.sh <kalico checkout> <fragment> <dest dir>
#
# Resolves the full config (make olddefconfig), checks that every setting the fragment asks for survived resolution
# (olddefconfig drops a misspelt symbol or an unmet dependency silently), builds, and copies klipper.elf, klipper.dict
# and the resolved .config to <dest>. Prints "build-firmware: OK" on success.
set -euo pipefail
kalico=$1; frag=$2; dest=$3
out=$(mktemp -d); cfg="$out/.config"
trap 'rm -rf "$out"' EXIT
grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$frag" > "$cfg"
make -C "$kalico" -s OUT="$out/" KCONFIG_CONFIG="$cfg" olddefconfig
while IFS= read -r want; do
    grep -qxF -- "$want" "$cfg" || { echo "build-firmware: Kconfig dropped '$want'"; exit 1; }
done < <(grep -E '^(CONFIG_|# CONFIG_.* is not set)' "$frag")
make -C "$kalico" -s -j"$(nproc)" OUT="$out/" KCONFIG_CONFIG="$cfg"
mkdir -p "$dest"
cp "$out/klipper.elf" "$out/klipper.dict" "$dest/"
cp "$cfg" "$dest/klipper.config"
echo "build-firmware: klipper.elf ($(wc -c < "$dest/klipper.elf") bytes)"
echo "build-firmware: OK"
