#!/usr/bin/env bash
# The virtual-printer image's entrypoint (vt350#224): write the configs (prepare.py), then run everything under
# supervisord. Arguments go to prepare.py: --source, --config, --map, --home-file (see prepare.py).
set -euo pipefail
mkdir -p "$VP_RUN"
python3 /opt/virtualprinter/prepare.py "$@"
exec supervisord -c "$VP_RUN/supervisord.conf"
