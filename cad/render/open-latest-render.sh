#!/usr/bin/env bash
# Open the newest finished render's out/ folder (the Desktop launcher "VT350 Renders" runs this).
# Newest = the most recently modified <job>-render/out/ that holds at least one image.
# Falls back to the top-level batch folder if none is found or the share isn't mounted.
# Usage: open-latest-render.sh [root]    --print: show the folder instead of opening it
set -euo pipefail
print=0; [ "${1:-}" = "--print" ] && { print=1; shift; }
root="${1:-/mnt/nfs/media/gpu-batch}"
dir=$(ls -1td "$root"/*-render/out 2>/dev/null | while read -r d; do
        compgen -G "$d/*.jpg" >/dev/null || compgen -G "$d/*.png" >/dev/null && { echo "$d"; break; }
      done || true)
[ -n "$dir" ] || dir="$root"
if [ "$print" = 1 ]; then echo "$dir"; else exec xdg-open "$dir"; fi
