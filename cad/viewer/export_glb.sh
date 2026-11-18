#!/usr/bin/env bash
# A GLB of part of the printer for the 3D viewer (vt350#220): FreeCAD export -> licence check -> Blender GLB.
#
#   cad/viewer/export_glb.sh [N | model.FCStd] [selection.json] [-- glb.py options, e.g. --decimate 0.5]
#       default: lite-62, cad/viewer/toolhead.json (the Left head on the gantry carriage)
#
# 1. FreeCAD GUI under xvfb-run (no window; the GUI is needed for the model's own colours of parts the colour map
#    gives no role) runs platform/render/export_meshes.py with RENDER_SELECT = the selection: only those parts,
#    coloured by cad/render/colours.json as in the renders. Never saves the model.
# 2. platform/viewer/licence_check.py: every exported part against cad/viewer/licences.json; an unknown or
#    non-shareable licence stops here, before any GLB exists.
# 3. Blender (headless) runs platform/viewer/glb.py: one GLB with the renders' materials.
# Output: ~/Documents/VT350/renders/<model>-viewer-<UTC>/{export/, licences.log, <model>-<selection>.glb}; ends with
# "glb-export: OK". Writes nothing to git.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
APP="${VT350_APP:-/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage}"
DOCS="${VT350_DOCS:-/home/dan/Documents/VT350}"
export VT350_COLOURS="${VT350_COLOURS:-$ROOT/cad/render/colours.json}"
arg="${1:-62}"; SELECT="${2:-$HERE/toolhead.json}"
shift $(( $# < 2 ? $# : 2 )); [[ "${1:-}" == "--" ]] && shift
if [[ "$arg" =~ ^[0-9]+$ ]]; then MODEL="$DOCS/vt350-lite-$arg.FCStd"; else MODEL="$arg"; fi
[[ -f "$MODEL" ]] || { echo "export_glb: no model $MODEL" >&2; exit 1; }
[[ -f "$SELECT" ]] || { echo "export_glb: no selection $SELECT" >&2; exit 1; }
command -v blender >/dev/null || { echo "export_glb: blender not on PATH" >&2; exit 1; }
command -v xvfb-run >/dev/null || { echo "export_glb: xvfb-run not found (apt install xvfb)" >&2; exit 1; }

NAME="$(basename "$MODEL" .FCStd)"
RUN="$DOCS/renders/$NAME-viewer-$(date -u +%Y%m%dT%H%M%SZ)"; EXP="$RUN/export"; mkdir -p "$EXP"
echo "[$(date +%T)] FreeCAD export: $NAME, $(basename "$SELECT") -> $EXP"
RENDER_SELECT="$SELECT" VT350_MODEL="$MODEL" VT350_EXTRA="" VT350_RENDER_OUT="$EXP" \
    xvfb-run -a -s "-screen 0 1280x1024x24" "$APP" "$ROOT/platform/render/export_meshes.py" >"$RUN/freecad.out" 2>&1 || true
if grep -v "] index: " "$EXP/export.log" 2>/dev/null | grep -q "FAILED" || ! grep -q "] done: " "$EXP/export.log" 2>/dev/null; then
    echo "export_glb: export FAILED; see $EXP/export.log and $RUN/freecad.out" >&2; exit 1
fi
grep -E "move |colour map:|done: " "$EXP/export.log" | sed 's/^\[ *[0-9.]*s\] /  /'
python3 "$ROOT/platform/viewer/licence_check.py" "$EXP/scene.json" "$HERE/licences.json" "$RUN/licences.log" \
    || { echo "export_glb: see $RUN/licences.log" >&2; exit 1; }
GLB="$RUN/$NAME-$(basename "$SELECT" .json).glb"
echo "[$(date +%T)] Blender: GLB -> $GLB"
blender -b -P "$ROOT/platform/viewer/glb.py" -- "$EXP" "$GLB" "$@" >"$RUN/blender.out" 2>&1 \
    || { echo "export_glb: blender FAILED; see $RUN/blender.out" >&2; exit 1; }
grep -E "^glb: " "$RUN/blender.out"
grep -qx "glb-export: OK" "$RUN/blender.out" || { echo "export_glb: no GLB; see $RUN/blender.out" >&2; exit 1; }
echo "glb-export: OK"
