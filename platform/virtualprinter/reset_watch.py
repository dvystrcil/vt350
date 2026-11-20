#!/usr/bin/env python3
"""Restart a simulated MCU board when klippy resets it (vt350#224).

    reset_watch.py <klippy.log> <supervisord.conf>

A FIRMWARE_RESTART (or klippy's restart after a shutdown) resets each MCU: with restart_method: command, Kalico
sends the firmware's reset command, and the AVR firmware waits for its watchdog to reboot it. simulavr doesn't
simulate the watchdog (its log: "MCU register WDTCSR not simulated"), so the board hangs and klippy then reports "No
communication with MCU". This follows klippy's log and, for each "Attempting MCU '<name>' ..." line, restarts that
board's simulator (supervisorctl restart simulavr-<name>): a fresh simulavr is a freshly booted board, and klippy's
reconnect finds its new pty at the same path.

Generic: no printer knowledge. Plain python3, standard library only.
"""
import os
import re
import subprocess
import sys
import time

RESET = re.compile(r"^Attempting MCU '([^']+)' (?:reset|reset command|config_reset command|Cheetah-style reset)$")


def board_to_restart(line):
    """The MCU name a klippy log line resets, or None."""
    m = RESET.match(line.strip())
    return m.group(1) if m else None


def follow(path, poll=0.25):
    """Yield the lines appended to path from now on; a file that appears later, or replaces it (klippy's log
    rotation), is read from its start. "Now" is the call, not the first next()."""
    try:
        f = open(path)
        f.seek(0, os.SEEK_END)
    except FileNotFoundError:
        f = None
    return _lines(path, f, poll)


def _lines(path, f, poll):
    ino = os.fstat(f.fileno()).st_ino if f else None
    while True:
        if f is None:
            try:
                f = open(path)
            except FileNotFoundError:
                time.sleep(poll)
                continue
            ino = os.fstat(f.fileno()).st_ino
        line = f.readline()
        if line:
            yield line
            continue
        try:
            st = os.stat(path)
            replaced = st.st_ino != ino or st.st_size < f.tell()
        except FileNotFoundError:
            replaced = False
        if replaced:
            f.close()
            f = None
            continue
        time.sleep(poll)


def main(argv):
    log, conf = argv
    for line in follow(log):
        name = board_to_restart(line)
        if name:
            print(f"reset-watch: klippy reset MCU '{name}': restarting simulavr-{name}", flush=True)
            subprocess.run(["supervisorctl", "-c", conf, "restart", f"simulavr-{name}"], check=False)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
