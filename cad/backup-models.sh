#!/usr/bin/env bash
# Back up the FreeCAD model files (too big for git) with restic.
#
#   cad/backup-models.sh            # back up
#   cad/backup-models.sh --verify   # back up, then restore the newest model
#                                   # file to a temp dir and compare checksums
#
# Where the backup goes is local, per-machine config, deliberately NOT in this
# public repo: ~/.config/vt350/backup.env must set
#   RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE, VT350_MODELS
# Without the restic password the backup cannot be opened, so keep a copy of it
# in a password manager, not only on this machine.
set -euo pipefail

CONF="${VT350_BACKUP_ENV:-$HOME/.config/vt350/backup.env}"
[[ -r "$CONF" ]] || { echo "missing config: $CONF (see the header of this script)" >&2; exit 1; }
set -a; # shellcheck disable=SC1090
source "$CONF"; set +a
: "${RESTIC_REPOSITORY:?set in $CONF}" "${RESTIC_PASSWORD_FILE:?set in $CONF}" "${VT350_MODELS:?set in $CONF}"
[[ -r "$RESTIC_PASSWORD_FILE" ]] || { echo "missing restic password file (see $CONF)" >&2; exit 1; }
[[ -d "$VT350_MODELS" ]] || { echo "missing model dir: $VT350_MODELS" >&2; exit 1; }
command -v restic >/dev/null || PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"

restic backup --tag vt350 "$VT350_MODELS"
restic snapshots --compact --tag vt350

if [[ "${1:-}" == "--verify" ]]; then
    newest=$(ls -t "$VT350_MODELS"/*.FCStd | head -1)
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    restic restore latest --tag vt350 --target "$tmp" --include "$newest"
    a=$(sha256sum "$newest" | cut -d' ' -f1)
    b=$(sha256sum "$tmp$newest" | cut -d' ' -f1)
    if [[ "$a" == "$b" ]]; then
        echo "verify OK: $(basename "$newest") restored byte-identical"
    else
        echo "verify FAILED: $(basename "$newest") checksum differs" >&2; exit 1
    fi
fi
