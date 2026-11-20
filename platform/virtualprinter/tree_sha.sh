#!/usr/bin/env bash
# Print the sha256 of one commit's tree, as the virtual printer's Dockerfile checks it (vt350#224): `git archive
# --format=tar` of the commit (every file's path, mode and content), piped through sha256sum.
#
#   tree_sha.sh <git URL> <commit>
#
# For SIMULAVR_TREE_SHA256 when SIMULAVR_SHA moves (cad/klipper/repin.sh simulavr-tree). A shallow fetch of exactly
# that commit, in a temp dir that's removed. Needs git and the network. Generic: the URL and commit are arguments.
set -euo pipefail
(( $# == 2 )) || { sed -n '2,9p' "$0"; exit 2; }
url=$1; sha=$2
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
git init -q "$d"
git -C "$d" fetch -q --depth 1 "$url" "$sha"
test "$(git -C "$d" rev-parse FETCH_HEAD)" = "$sha" || { echo "tree_sha: $url gave another commit" >&2; exit 1; }
git -C "$d" archive --format=tar FETCH_HEAD | sha256sum | cut -d' ' -f1
