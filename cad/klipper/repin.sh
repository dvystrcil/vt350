#!/usr/bin/env bash
# Keep the virtual printer's and kalisim's build pins current (vt350#224). What the monthly workflow
# (.github/workflows/repin-virtualprinter.yml) runs, and what anyone can run by hand from the repo root:
#
#   cad/klipper/repin.sh monthly            # snapshot + moonraker + pip-lock + tools-page HEAD + build
#   cad/klipper/repin.sh fixup <base>       # on a Renovate branch: what Renovate can't recompute, against <base>
#
# The steps, each runnable on its own:
#   snapshot [TS]      DEBIAN_SNAPSHOT to TS (default: today 00:00 UTC) in both Dockerfiles, every apt package to
#                      that snapshot's version (platform/kalisim/apt_repin.py); builds the kalisim image in between,
#                      because the virtual printer's stages are FROM it
#   moonraker          Moonraker's python packages re-resolved within Moonraker's own ranges (at MOONRAKER_SHA) in
#                      the kalisim image, then hashed (needs the kalisim image: snapshot or build first)
#   pip-lock           every platform/virtualprinter/*-requirements.txt re-hashed (pip_lock.py)
#   simulavr-tree      SIMULAVR_TREE_SHA256 recomputed for SIMULAVR_SHA (platform/virtualprinter/tree_sha.sh)
#   tools-page <base>  cad/tools.md updated for every pin that differs from git ref <base> (cad/sync-tools-page.py)
#   build              both images: kalisim:local, then virtual-printer:local FROM it (the build is the test)
#
# Needs docker, git, python3 and the network. Last line: "repin: <step> OK"; any failure exits non-zero.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
kdf=$root/platform/kalisim/Dockerfile
vp=$root/platform/virtualprinter
kalisim_tag=${KALISIM_TAG:-kalisim:local}   # KALISIM_TAG: another tag for the kalisim image
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
arg() { sed -n "s/^ARG $1=//p" "$2"; }

build_kalisim() {
    docker build -q --build-context kconfig="$root/cad/klipper/kconfig" -t "$kalisim_tag" "$root/platform/kalisim" >/dev/null
    echo "  built $kalisim_tag"
}
build_vp() {
    docker build -q --build-arg KALISIM_IMAGE="$kalisim_tag" --build-context pinmap="$root/platform/klipper" \
        -t virtual-printer:local "$vp" >/dev/null
    echo "  built virtual-printer:local"
}

snapshot() {
    local ts=${1:-$(date -u +%Y%m%dT000000Z)}
    python3 "$root/platform/kalisim/apt_repin.py" "$kdf" "$ts"
    build_kalisim
    python3 "$root/platform/kalisim/apt_repin.py" "$vp/Dockerfile" "$ts" --image "kalisim:local=$kalisim_tag"
}

moonraker() {
    local sha req tmp=$work/moonraker
    mkdir -p "$tmp"
    sha=$(arg MOONRAKER_SHA "$vp/Dockerfile")
    req=$vp/moonraker-requirements.txt
    curl -fsSL --retry 3 -o "$tmp/ranges.txt" \
        "https://raw.githubusercontent.com/Arksine/moonraker/$sha/scripts/moonraker-requirements.txt"
    grep -v '^--find-links' "$tmp/ranges.txt" > "$tmp/req.txt"
    # an empty venv on the image's own python (as the Dockerfile's build stage), wheels only, then pip freeze
    docker run --rm --entrypoint sh -v "$tmp/req.txt:/req.txt:ro" "$kalisim_tag" -ec '
        python3 -m venv /tmp/env
        /tmp/env/bin/pip install -q --disable-pip-version-check --only-binary=:all: -r /req.txt >&2
        /tmp/env/bin/pip freeze --disable-pip-version-check' > "$tmp/freeze.txt"
    grep -qE '^[A-Za-z0-9].*==' "$tmp/freeze.txt" || { echo "repin: pip freeze gave no pins"; exit 1; }
    # the file's comment header (dated today), then the freeze
    { sed -n '/^#/p' "$req" | sed "s/ranges on [0-9-]*,/ranges on $(date -u +%F),/"; cat "$tmp/freeze.txt"; } > "$tmp/new.txt"
    cp "$tmp/new.txt" "$req"
    python3 "$vp/pip_lock.py" "$req"
}

pip_lock() {
    local f
    for f in "$vp"/*-requirements.txt; do python3 "$vp/pip_lock.py" "$f"; done
}

simulavr_tree() {
    local sha url tree
    sha=$(arg SIMULAVR_SHA "$vp/Dockerfile"); url=$(arg SIMULAVR_URL "$vp/Dockerfile")
    tree=$(bash "$vp/tree_sha.sh" "$url" "$sha")
    sed -i "s/^ARG SIMULAVR_TREE_SHA256=.*/ARG SIMULAVR_TREE_SHA256=$tree/" "$vp/Dockerfile"
    echo "  simulavr ${sha:0:12}: tree $tree"
}

tools_page() { python3 "$root/cad/sync-tools-page.py" "${1:?tools-page needs a base git ref}"; }

fixup() {
    local base=${1:?fixup needs a base git ref, e.g. origin/main}
    if [[ "$(git -C "$root" show "$base:platform/virtualprinter/Dockerfile" | arg SIMULAVR_SHA /dev/stdin)" \
          != "$(arg SIMULAVR_SHA "$vp/Dockerfile")" ]]; then
        simulavr_tree
    fi
    if ! git -C "$root" diff --quiet "$base" -- 'platform/virtualprinter/*-requirements.txt'; then pip_lock; fi
    tools_page "$base"
}

step=${1:-}; shift || true
case $step in
    snapshot) snapshot "$@" ;;
    moonraker) moonraker ;;
    pip-lock) pip_lock ;;
    simulavr-tree) simulavr_tree ;;
    tools-page) tools_page "$@" ;;
    build) build_kalisim; build_vp ;;
    fixup) fixup "$@" ;;
    monthly)
        base=$(git -C "$root" rev-parse HEAD)
        snapshot "$@"; moonraker; pip_lock; tools_page "$base"; build_vp ;;
    *) sed -n '2,20p' "$0"; exit 2 ;;
esac
echo "repin: $step OK"
