# kalisim: run a printer config and G-code through Kalico's batch mode, with no hardware, and read back the moves.
#
# Copyright (C) 2026 dvystrcil
# SPDX-License-Identifier: GPL-3.0-or-later
"""kalisim: Kalico batch mode as a library (vt350#116). No FreeCAD, no printer-specific knowledge.

    python3 -m kalisim run      --config printer.cfg --gcode moves.gcode -d main.dict -d toolboard=tb.dict
    python3 -m kalisim envelope --config printer.cfg --gcode envelope.gcode -d main.dict -d toolboard=tb.dict

`run` prints the timeline: one JSON object per planned move (plugins/move_timeline.py). `envelope` runs a G-code
file split into blocks by marker comments:

    ; @setup            run first, in every run (homing, G90)
    ; @in-range         run once after @setup: every move must be planned where it was commanded
    ; @past <name>      one move each, run alone after @setup: Kalico must refuse it with "Move out of range"

and ends with "kalisim-envelope: OK" or "kalisim-envelope: FAILED". The Kalico checkout is --kalico or $KALICO_DIR;
it needs plugins/move_timeline.py in its klippy/plugins/ (the Dockerfile here puts it there).

Standard library only, so it runs under whatever Python runs Kalico.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

MARKER = re.compile(r";\s*@(setup|in-range|past \S+)\s*$")
OUT_OF_RANGE = re.compile(r"Move out of range: (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)")
LOG_DECIMALS_TOL = 0.0005 + 1e-9  # Kalico prints a refused move at 3 decimals


def parse_dict_option(opt):
    """"name=path" -> (name, path); a bare path is the main MCU's, as with klippy's own -d."""
    name, sep, path = opt.partition("=")
    return (name, path) if sep else ("mcu", opt)


def dict_args(dicts):
    """klippy's -d arguments: the main MCU's dictionary bare and first, then name=path for each other MCU."""
    names = [n for n, _ in dicts]
    for n in names:
        if names.count(n) > 1:
            raise ValueError(f"dictionary for {n} given twice")
    if "mcu" not in names:
        raise ValueError("no dictionary for the main mcu")
    out = ["-d", dict(dicts)["mcu"]]
    for n, p in dicts:
        if n != "mcu":
            out += ["-d", f"{n}={p}"]
    return out


def parse_blocks(text):
    """{"setup": [...], "in-range": [...], "past <name>": [...]}: commands only, comments and blanks dropped."""
    blocks, cur = {}, None
    for raw in text.splitlines():
        m = MARKER.fullmatch(raw.strip())
        if m:
            cur = m.group(1)
            if cur in blocks:
                raise ValueError(f"block '{cur}' given twice")
            blocks[cur] = []
            continue
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if cur is None:
            raise ValueError(f"command before the first block marker: {line!r}")
        blocks[cur].append(line)
    if "setup" not in blocks or "in-range" not in blocks:
        raise ValueError("need both a '; @setup' and a '; @in-range' block")
    return blocks


def move_targets(lines):
    """The axes each G0/G1 with an X, Y or Z commands, in order: [{"x": 1.0, "z": 3.0}, ...]. Absolute only."""
    out = []
    for line in lines:
        words = line.upper().split()
        if words[0] == "G91":
            raise ValueError("G91 (relative moves) is not supported: targets would depend on the start position")
        if words[0] in ("G0", "G1"):
            t = {w[0].lower(): float(w[1:]) for w in words[1:] if w[0] in "XYZ"}
            if t:
                out.append(t)
    return out


class Result:
    def __init__(self, returncode, log, timeline):
        self.returncode, self.log, self.timeline = returncode, log, timeline

    def moves(self):
        """XYZ of every planned move, in order."""
        return [e["pos"][:3] for e in self.timeline if e["kind"] == "move"]

    def out_of_range(self):
        """XYZ of the move Kalico refused, or None."""
        m = OUT_OF_RANGE.search(self.log)
        return [float(v) for v in m.groups()] if m else None


def _read(path, default):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return default


def run(printer_cfg, lines, dicts, kalico_dir, python=None, workdir=None):
    """Run G-code lines through klippy in batch mode with printer_cfg; returns a Result."""
    if workdir is None:
        with tempfile.TemporaryDirectory(prefix="kalisim-") as d:
            return run(printer_cfg, lines, dicts, kalico_dir, python, d)
    p = {k: os.path.join(workdir, f) for k, f in (("cfg", "sim.cfg"), ("gcode", "in.gcode"),
                                                    ("out", "out.serial"), ("log", "klippy.log"),
                                                    ("timeline", "timeline.jsonl"))}
    with open(p["cfg"], "w") as f:
        f.write(f"[include {os.path.abspath(printer_cfg)}]\n\n[move_timeline]\npath: {p['timeline']}\n")
    with open(p["gcode"], "w") as f:
        f.write("\n".join(lines) + "\n")
    cmd = [python or sys.executable, "-m", "klippy", p["cfg"],
           "-i", p["gcode"], "-o", p["out"], "-l", p["log"]] + dict_args(dicts)
    rc = subprocess.run(cmd, cwd=kalico_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    timeline = [json.loads(l) for l in _read(p["timeline"], "").splitlines() if l.strip()]
    return Result(rc, _read(p["log"], ""), timeline)


def _matches(pos, target, tol=1e-6):
    return all(abs(pos["xyz".index(a)] - v) <= tol for a, v in target.items())


def check_envelope(printer_cfg, text, dicts, kalico_dir, python=None):
    """(ok, report lines): @setup + @in-range must plan every move as commanded; each @past move must be refused."""
    blocks = parse_blocks(text)
    report, ok = [], True
    want = move_targets(blocks["in-range"])
    base = run(printer_cfg, blocks["setup"], dicts, kalico_dir, python)  # the moves @setup plans on its own
    r = run(printer_cfg, blocks["setup"] + blocks["in-range"], dicts, kalico_dir, python)
    got = r.moves()[len(base.moves()):]
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if not _matches(g, w)]
    if base.returncode != 0 or r.returncode != 0:
        rr = base if base.returncode != 0 else r
        m = OUT_OF_RANGE.search(rr.log)
        why = f"refused: {m.group(0)}" if m else "see the klippy log"
        report.append(f"in-range: FAILED: exit {rr.returncode}; {why}"); ok = False
    elif len(got) != len(want):
        report.append(f"in-range: FAILED: {len(got)} of {len(want)} moves planned"); ok = False
    elif bad:
        i, g, w = bad[0]
        report.append(f"in-range: FAILED: move {i + 1} planned at {g}, commanded {w}"); ok = False
    else:
        report.append(f"in-range: {len(want)} moves accepted")
    for name in (b for b in blocks if b.startswith("past ")):
        probe = move_targets(blocks[name])
        if len(probe) != 1 or len(blocks[name]) != 1:
            raise ValueError(f"{name}: one move per @past block, got {blocks[name]}")
        r = run(printer_cfg, blocks["setup"] + blocks[name], dicts, kalico_dir, python)
        refused = r.out_of_range()
        if r.returncode == 0:
            report.append(f"{name}: FAILED: accepted (exit 0)"); ok = False
        elif refused is None:
            report.append(f"{name}: FAILED: exit {r.returncode} with no \"Move out of range\" (see the klippy log)")
            ok = False
        elif not _matches(refused, probe[0], LOG_DECIMALS_TOL):
            report.append(f"{name}: FAILED: refused at {refused}, not the probe {probe[0]}"); ok = False
        else:
            report.append(f"{name}: refused: {OUT_OF_RANGE.search(r.log).group(0)}")
    report.append("kalisim-envelope: " + ("OK" if ok else "FAILED"))
    return ok, report


def main(argv):
    ap = argparse.ArgumentParser(prog="kalisim", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=("run", "envelope"))
    ap.add_argument("--config", required=True)
    ap.add_argument("--gcode", required=True)
    ap.add_argument("--kalico", default=None, help="Kalico checkout (default: $KALICO_DIR)")
    ap.add_argument("--python", default=None)
    ap.add_argument("-d", dest="dicts", action="append", required=True, help="[name=]path, one per MCU")
    a = ap.parse_args(argv)
    dicts = [parse_dict_option(d) for d in a.dicts]
    kalico = a.kalico or os.environ["KALICO_DIR"]
    with open(a.gcode) as f:
        text = f.read()
    if a.command == "run":
        r = run(a.config, text.splitlines(), dicts, kalico, a.python)
        return [json.dumps(e) for e in r.timeline]
    ok, report = check_envelope(a.config, text, dicts, kalico, a.python)
    if not ok:
        raise SystemExit("\n".join(report))
    return report
