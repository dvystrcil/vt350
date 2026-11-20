#!/usr/bin/env bash
# Check cad/tools.md against the pins it lists (#124). Every in-repo pin (the Kalico and toolchanger commits, both
# image digests, the FreeCAD AppImage, every GitHub action version) must appear on the page exactly as pinned.
#
#   cad/check-tools-page.sh           # the in-repo pins (what CI runs, through cad/test_tools_page.py)
#   cad/check-tools-page.sh --local   # also the laptop's installed versions (each tool not installed is skipped)
#
# Last line: "check-tools-page: OK", or "check-tools-page: FAILED (<n>)" with exit 1.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PAGE="$ROOT/cad/tools.md"
DF="$ROOT/platform/kalisim/Dockerfile"
fail=0
need() {   # need <what> <value>: the value must be on the page
    if [[ -z "$2" ]]; then echo "FAIL $1: no pin found in the repo"; fail=$((fail + 1)); return; fi
    if grep -qF -- "$2" "$PAGE"; then echo "ok   $1: $2"; else echo "FAIL $1: $2 is not on cad/tools.md"; fail=$((fail + 1)); fi
}
# kalisim's Debian snapshot and every name=version word in its apt-get install lines (and their continuations)
need "kalisim DEBIAN_SNAPSHOT" "$(sed -n 's/^ARG DEBIAN_SNAPSHOT=//p' "$DF")"
while read -r pkg; do need "kalisim apt package" "$pkg"; done < <(
    sed -e ':a' -e '/\\$/N; s/\\\n//; ta' "$DF" | grep 'apt-get install' \
        | grep -oE '[a-z0-9][a-z0-9.+-]*=[0-9][^ =\\]*' | sort -u)
need "Kalico commit" "$(sed -n 's/^ARG KALICO_SHA=//p' "$DF")"
need "klipper-toolchanger commit" "$(sed -n 's/^ARG TOOLCHANGER_SHA=//p' "$DF")"
while read -r img; do need "image" "$img"; done < <(sed -n 's/^FROM \([^ ]*\).*/\1/p' "$DF")
need "FreeCAD AppImage" "$(grep -o 'FreeCAD_[^ /`]*\.AppImage' "$ROOT/platform/README.md" | head -1)"
while read -r act; do need "action" "$act"; done < <(grep -ho 'uses: [^ ]*' "$ROOT"/.github/workflows/*.yml | sed 's/uses: //' | sort -u)
if [[ "${1:-}" == "--local" ]]; then
    local_ver() {   # local_ver <what> <command...>: the first version-looking word the command prints
        local what="$1"; shift
        if ! command -v "$1" >/dev/null 2>&1; then echo "skip $what: $1 not installed"; return; fi
        need "$what (installed)" "$("$@" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)"
    }
    local_ver Blender blender --version
    local_ver Docker docker --version
    local_ver act act --version
    local_ver ffmpeg ffmpeg -version
    local_ver restic restic version
    local_ver Python python3 --version
fi
if (( fail )); then echo "check-tools-page: FAILED ($fail)"; exit 1; fi
echo "check-tools-page: OK"
