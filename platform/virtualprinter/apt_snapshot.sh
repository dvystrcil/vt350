#!/bin/sh
# Point a Debian image's apt at snapshot.debian.org as of one moment (vt350#224), so every build installs the same
# package versions, and a version Debian has since replaced still downloads.
#
#   apt_snapshot.sh <timestamp>        e.g. 20261120T000000Z
#
# Rewrites the deb.debian.org URIs in /etc/apt/sources.list.d/debian.sources (the deb822 file the Debian and python
# images ship) to snapshot.debian.org/archive/<debian|debian-security>/<timestamp>, and turns off the Release files'
# Valid-Until check (a snapshot's Release file expires in days). Fails if any deb.debian.org source is left.
# APT_ROOT (default empty: the real /etc/apt) is a folder standing in for / , for the tests.
set -eu
ts=${1:?usage: apt_snapshot.sh <timestamp, e.g. 20261120T000000Z>}
case $ts in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z) ;;
    *) echo "apt_snapshot: '$ts' is not a timestamp like 20261120T000000Z"; exit 1 ;;
esac
apt=${APT_ROOT:-}/etc/apt
src=$apt/sources.list.d/debian.sources
test -f "$src" || { echo "apt_snapshot: no $src"; exit 1; }
sed -i -e "s|^URIs: http://deb.debian.org/debian-security/*\$|URIs: http://snapshot.debian.org/archive/debian-security/$ts|" \
       -e "s|^URIs: http://deb.debian.org/debian/*\$|URIs: http://snapshot.debian.org/archive/debian/$ts|" "$src"
if grep -rqs 'deb.debian.org' "$apt/sources.list" "$apt/sources.list.d/"; then
    echo "apt_snapshot: a deb.debian.org source is left:"; grep -rs 'deb.debian.org' "$apt/sources.list" "$apt/sources.list.d/"; exit 1
fi
test "$(grep -c "^URIs: http://snapshot.debian.org/archive/debian\(-security\)\?/$ts\$" "$src")" -eq 2 \
    || { echo "apt_snapshot: expected 2 snapshot URIs in $src"; cat "$src"; exit 1; }
# snapshot.debian.org is slow and drops connections under load: retry rather than fail the build
printf 'Acquire::Check-Valid-Until "false";\nAcquire::Retries "5";\nAcquire::http::Timeout "60";\n' \
    > "$apt/apt.conf.d/99snapshot"
echo "apt_snapshot: apt reads snapshot.debian.org as of $ts"
