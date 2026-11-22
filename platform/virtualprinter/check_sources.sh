#!/usr/bin/env bash
# Check that a pinned commit can still be fetched from each of its sources, with the pinned tree (vt350#224): the
# virtual printer's simulavr from its default mirror and from the fallback fork.
#
#   check_sources.sh <commit> <tree sha256> <git URL> [<git URL> ...]
#
# For each URL: a shallow fetch of exactly that commit, then the sha256 of `git archive --format=tar` of it (as the
# Dockerfile checks). Prints "ok"/"FAIL" per URL and a last line "check-sources: OK" or "check-sources: FAILED (<n>)",
# exit 1. Needs git and the network. Generic: the commit, hash and URLs come in as arguments.
set -uo pipefail
(( $# >= 3 )) || { sed -n '2,10p' "$0"; exit 2; }
sha=$1; want=$2; shift 2
fail=0
for url in "$@"; do
    d=$(mktemp -d)
    if git init -q "$d" && git -C "$d" fetch -q --depth 1 "$url" "$sha" 2>/dev/null; then
        got=$(git -C "$d" archive --format=tar FETCH_HEAD | sha256sum | cut -d' ' -f1)
        if [[ "$got" == "$want" ]]; then echo "ok   $url: ${sha:0:12}, tree ${want:0:12}"
        else echo "FAIL $url: ${sha:0:12} has tree $got, expected $want"; fail=$((fail + 1)); fi
    else
        echo "FAIL $url: can't fetch ${sha:0:12}"; fail=$((fail + 1))
    fi
    rm -rf "$d"
done
if (( fail )); then echo "check-sources: FAILED ($fail)"; exit 1; fi
echo "check-sources: OK"
