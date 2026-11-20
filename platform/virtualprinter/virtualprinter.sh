#!/usr/bin/env bash
# A virtual printer on this machine (vt350#224): live Kalico on simulated MCU boards, Moonraker, and Fluidd at
# http://127.0.0.1:<port>/. Laptop only: Docker, no registry, no Kubernetes.
#
#   virtualprinter.sh start  --kconfig DIR --source DIR --config REL --map REL [--home-file REL=SRC ...] [--port N]
#   virtualprinter.sh status [--port N]      # "virtual-printer: ready" when Moonraker's /printer/info says so
#   virtualprinter.sh stop                   # "virtual-printer: stopped"
#   virtualprinter.sh build  --kconfig DIR   # the images only (start builds them too)
#
# start builds the kalisim image (platform/kalisim, with the printer's MCU Kconfig fragments from --kconfig) and the
# virtual-printer image FROM it, then runs the container with --source mounted read-only; --config, --map and each
# SRC are relative to --source. It waits until klippy is ready (or fails, with the logs' tail).
# Everything the printer writes (configs, logs, Moonraker's database, the save file) is inside the container and goes
# when it stops (docker run --rm): no volume, nothing on the host. Port default 8080, bound to 127.0.0.1 only.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
platform=$(dirname "$here")
name=virtual-printer
kalisim_tag=kalisim:local
tag=virtual-printer:local
port=8080
cmd=${1:-}; shift || true
kconfig=; source=; config=; map=; home_files=()
while (( $# )); do
    case $1 in
        --kconfig) kconfig=$2; shift 2 ;;
        --source) source=$2; shift 2 ;;
        --config) config=$2; shift 2 ;;
        --map) map=$2; shift 2 ;;
        --home-file) home_files+=(--home-file "$2"); shift 2 ;;
        --port) port=$2; shift 2 ;;
        *) echo "virtual-printer: unknown option $1"; exit 2 ;;
    esac
done

build() {
    [ -n "$kconfig" ] || { echo "virtual-printer: build needs --kconfig"; exit 2; }
    docker build -q --build-context kconfig="$kconfig" -t "$kalisim_tag" "$platform/kalisim" > /dev/null
    docker build -q --build-arg KALISIM_IMAGE="$kalisim_tag" --build-context pinmap="$platform/klipper" \
        -t "$tag" "$here" > /dev/null
    echo "virtual-printer: built $tag (FROM $kalisim_tag)"
}

state() {  # klippy's state from Moonraker's /printer/info, or "down"
    curl -fsS --max-time 3 "http://127.0.0.1:$port/printer/info" 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["state"])' 2>/dev/null || echo down
}

case $cmd in
    build) build ;;
    start)
        [ -n "$source" ] && [ -n "$config" ] && [ -n "$map" ] || {
            echo "virtual-printer: start needs --source, --config and --map"; exit 2; }
        source=$(cd "$source" && pwd)
        build
        docker rm -f "$name" > /dev/null 2>&1 || true
        docker run -d --rm --name "$name" -p "127.0.0.1:$port:8080" -v "$source:/src:ro" "$tag" \
            --source /src --config "$config" --map "$map" "${home_files[@]}" > /dev/null
        # On a busy machine a simulated board can answer klippy's connect too slowly; klippy then stops with an error
        # (state shutdown or error) and a host restart (as Fluidd's RESTART) usually connects. Up to 3 tries.
        tries=0
        for _ in $(seq 120); do
            s=$(state)
            [ "$s" = ready ] && { echo "virtual-printer: ready"; echo "virtual-printer: Fluidd at http://127.0.0.1:$port/"; exit 0; }
            docker inspect "$name" > /dev/null 2>&1 || { echo "virtual-printer: the container exited"; exit 1; }
            if [ "$s" = shutdown ] || [ "$s" = error ]; then
                (( tries < 3 )) || break
                tries=$((tries + 1))
                echo "virtual-printer: klippy stopped while connecting ($s); restarting it ($tries of 3)"
                curl -fsS -X POST --max-time 10 "http://127.0.0.1:$port/printer/restart" > /dev/null || true
                sleep 5
            fi
            sleep 2
        done
        echo "virtual-printer: not ready (klippy: $(state)); the end of klippy.log:"
        docker exec "$name" tail -n 30 /opt/printer_data/logs/klippy.log || true
        exit 1 ;;
    status)
        s=$(state)
        echo "virtual-printer: $s"
        [ "$s" = ready ] ;;
    stop)
        docker stop "$name" > /dev/null 2>&1 || true
        docker inspect "$name" > /dev/null 2>&1 && { echo "virtual-printer: still running"; exit 1; }
        echo "virtual-printer: stopped" ;;
    *) sed -n '2,15p' "$0"; exit 2 ;;
esac
