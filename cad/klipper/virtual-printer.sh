#!/usr/bin/env bash
# The VT350 as a virtual printer (vt350#224): its config on simulated boards, with Moonraker and Fluidd.
#
#   bash cad/klipper/virtual-printer.sh start    # builds, starts, waits: "virtual-printer: ready"; Fluidd at http://127.0.0.1:8080/
#   bash cad/klipper/virtual-printer.sh status   # "virtual-printer: ready"
#   bash cad/klipper/virtual-printer.sh stop     # "virtual-printer: stopped"
#
# The VT350's values for the generic platform/virtualprinter/virtualprinter.sh: the MCU Kconfig fragments, printer.cfg
# and its pin map, and MadMax's save file seeded as the batch tests seed it. Extra options (--port N) pass through.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
cmd=${1:-}; shift || true
exec bash "$root/platform/virtualprinter/virtualprinter.sh" "$cmd" \
    --kconfig "$root/cad/klipper/kconfig" --source "$root" \
    --config cad/klipper/printer.cfg --map cad/klipper/pinmap.json \
    --home-file printer_data/config/offset_save_file.cfg=cad/klipper/madmax/offset_save_file.cfg "$@"
