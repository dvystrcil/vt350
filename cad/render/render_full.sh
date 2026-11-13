#!/usr/bin/env bash
# Full renders of the printer in its chosen colours (#38), on this laptop: FreeCAD export -> Blender Cycles (OPTIX).
#
#   cad/render/render_full.sh [N | model.FCStd] [samples]      # default: lite-26 + vt350-ebox.FCStd, 128 samples
#
# 1. FreeCAD GUI (needed: hidden parts and the model's own colours only exist in GUI mode) runs export_meshes.py on
#    the model plus the ebox file (VT350_EXTRA). Parts are coloured by cad/render/colours.json: frame RAL 6011 green powder
#    coat, printed PET-GF white, [a]_ accents PET-GF orange. Anything else keeps the model's colour. A FreeCAD
#    window opens and closes by itself; if GNOME says "Not Responding", click Wait.
# 2. Blender (snap, headless) renders the "obico" (chamber camera) and "outside" (3/4 front) views on the RTX 2070.
# Output: ~/Documents/VT350/renders/<model>-<UTC>/{export,out}. Never saves a model, writes nothing to git.
# Colours: edit colours.json and re-run. Changed only a role's hex/finish? VT350_REUSE_EXPORT=<run>/export skips the
# slow export. Changed or added a RULE? Run a full export: roles are assigned when parts are exported.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# the generic export + render scripts (vt350#122); this printer's colour map is colours.json beside this script
PLATFORM="$(cd "$HERE/../../platform/render" && pwd)"
export VT350_COLOURS="${VT350_COLOURS:-$HERE/colours.json}"
APP="${VT350_APP:-/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage}"
DOCS="${VT350_DOCS:-/home/dan/Documents/VT350}"
arg="${1:-26}"; SAMPLES="${2:-128}"
if [[ "$arg" =~ ^[0-9]+$ ]]; then MODEL="$DOCS/vt350-lite-$arg.FCStd"; else MODEL="$arg"; fi
EXTRA="${VT350_EXTRA-$DOCS/vt350-ebox.FCStd}"
[[ -f "$MODEL" ]] || { echo "render_full: no model $MODEL" >&2; exit 1; }
for x in ${EXTRA//:/ }; do [[ -f "$x" ]] || { echo "render_full: no extra model $x" >&2; exit 1; }; done
command -v blender >/dev/null || { echo "render_full: blender not on PATH (snap install blender --classic)" >&2; exit 1; }

RUN="$DOCS/renders/$(basename "$MODEL" .FCStd)-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN"
if [[ -n "${VT350_REUSE_EXPORT:-}" ]]; then
    EXP="$VT350_REUSE_EXPORT"; echo "reusing export $EXP"
else
    EXP="$RUN/export"; mkdir -p "$EXP"
    echo "[$(date +%T)] FreeCAD export: $(basename "$MODEL") ${EXTRA:++ $(basename "${EXTRA//:/ + }")} -> $EXP"
    env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
        VT350_MODEL="$MODEL" VT350_EXTRA="$EXTRA" VT350_RENDER_OUT="$EXP" \
        "$APP" "$PLATFORM/export_meshes.py" >"$RUN/freecad.out" 2>&1 || true   # FreeCAD's exit code is meaningless (os._exit)
    # "index: FAILED ..." is the part-index hook's, non-fatal by design (#90): only other FAILED lines fail the export
    if grep -v "] index: " "$EXP/export.log" 2>/dev/null | grep -q "FAILED" || ! grep -q "] done: " "$EXP/export.log" 2>/dev/null; then
        echo "render_full: export FAILED; see $EXP/export.log and $RUN/freecad.out" >&2; exit 1
    fi
    grep -E "colour map:|done: " "$EXP/export.log" | sed 's/^\[ *[0-9.]*s\] /  /'
fi
echo "[$(date +%T)] Blender: $SAMPLES samples -> $RUN/out"
blender -b -P "$PLATFORM/render.py" -- "$EXP" "$RUN/out" "$SAMPLES" >"$RUN/blender.out" 2>&1 \
    || { echo "render_full: blender FAILED; see $RUN/blender.out" >&2; exit 1; }
grep -m1 "^GPU:" "$RUN/blender.out" || echo "  (no GPU line: rendered on CPU)"
shopt -s nullglob; imgs=("$RUN"/out/*.png "$RUN"/out/*.jpg)
(( ${#imgs[@]} )) || { echo "render_full: blender wrote no images; see $RUN/blender.out" >&2; exit 1; }
printf '  %s\n' "${imgs[@]}"
echo "render_full: OK"
