#!/usr/bin/env bash
# Every test file must remove the temp dirs it makes. Each one runs with its own empty TMPDIR, and anything left in
# it afterwards fails the check. Leaked test dirs once filled the laptop's /tmp (a tmpfs, 1M inodes) and broke every
# tool on it.
#
#   platform/testing/check_test_tmp.sh [test_file.py ...]     # default: every test_*.py that runs under plain python3
#
# Prints "check-test-tmp: OK" on success, exit 0; otherwise 1. Files that need FreeCAD or Blender are skipped with a
# line saying so; run those by hand under freecadcmd with TMPDIR set. "Needs Kalico" files run in the kalisim
# container: cad/klipper/test_in_container.sh checks their TMPDIR the same way.
set -uo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
if (( $# )); then files=("$@"); else mapfile -t files < <(git ls-files '*test_*.py'); fi
base=$(mktemp -d); trap 'rm -rf "$base"' EXIT
fail=0; ran=0
for f in "${files[@]}"; do
    if grep -qE '^(import|from) (FreeCAD|bpy)\b' "$f" || head -15 "$f" | grep -qE 'Needs (Blender|Kalico)'; then
        echo "skip   $f (needs FreeCAD, Blender or Kalico)"; continue
    fi
    t="$base/$(echo "$f" | tr / _)"; mkdir -p "$t"
    out=$(cd "$(dirname "$f")" && TMPDIR="$t" python3 "$(basename "$f")" 2>&1)
    if ! grep -qE '^Ran [1-9][0-9]* tests?' <<<"$out" || ! grep -qx 'OK' <<<"$out"; then
        echo "FAILED $f: tests did not pass"; echo "$out" | tail -5 | sed 's/^/       /'; fail=1; continue
    fi
    left=$(ls -A "$t")
    if [[ -n "$left" ]]; then
        echo "FAILED $f left $(wc -l <<<"$left") entries in TMPDIR:"; head -5 <<<"$left" | sed 's/^/       /'; fail=1
    else
        echo "clean  $f"; ran=$((ran + 1))
    fi
done
(( ran > 0 )) || { echo "check-test-tmp: no test file ran"; exit 1; }
(( fail )) && { echo "check-test-tmp: FAILED"; exit 1; }
echo "check-test-tmp: OK"
