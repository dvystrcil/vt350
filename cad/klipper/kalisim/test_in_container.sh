#!/usr/bin/env bash
# Build the kalisim image and run the Kalico batch-mode tests in it (vt350#116 AC1, AC3).
#
#   bash cad/klipper/kalisim/test_in_container.sh [image tag]
#
# The repo is mounted read-only; the tests run with an empty TMPDIR, and anything left in it fails the run.
# Prints "kalico-batch: OK" on success.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)  # the repo root, without git (a worktree under act has no .git dir)
tag=${1:-vt350-kalisim:local}
docker build -q -t "$tag" "$root/cad/klipper/kalisim" > /dev/null
docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$root:/repo:ro" "$tag" sh -ec '
    t=$(mktemp -d); trap "rm -rf \"\$t\"" EXIT
    export TMPDIR="$t"
    cd /repo/cad/klipper
    $KALISIM_PYTHON test_kalico_batch.py 2>&1 | tee "$HOME/test.log"
    grep -qE "^Ran [1-9][0-9]* tests" "$HOME/test.log" || exit 1; tail -1 "$HOME/test.log" | grep -qx OK || exit 1
    $KALISIM_PYTHON kalisim/test_kalisim.py 2>&1 | tee "$HOME/test2.log"
    grep -qE "^Ran [1-9][0-9]* tests" "$HOME/test2.log" || exit 1; tail -1 "$HOME/test2.log" | grep -qx OK || exit 1
    left=$(ls -A "$t"); [ -z "$left" ] || { echo "kalico-batch: tests left in TMPDIR: $left"; exit 1; }
'
echo "kalico-batch: OK"
