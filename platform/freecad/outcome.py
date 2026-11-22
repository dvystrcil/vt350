# The outcome of a model pass, as text (vt350#280): the log lines litelib.Pass.finish() has always written, plus a
# title and a short message for the GUI, which shows it in a message box and the Report view. A GUI run can take
# 20 minutes, and its outcome was only in the log, so a NOT SAVED run looked just like a saved one.
#
# Plain python3, no FreeCAD (test_outcome.py runs in CI). Generic: no printer knowledge.
#
# PASS_GUI_NOTICE (GUI runs only): "box" (default) = a message box + the Report view; "report" = the Report view
# only (for unattended GUI runs: a modal box would wait for a click); "none" = the log only.
from collections import namedtuple

Outcome = namedtuple("Outcome", "kind title text log_lines")
MAX_ERRS = 5          # failed checks listed in the message (the log has all of them)
MAX_LINE = 200        # characters of one failed check in the message
MODES = ("box", "report", "none")


def size(b):
    """Bytes for a person: MB from 1 MB, else kB."""
    return f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{b / 1e3:.1f} kB"


def _short(s):
    return s if len(s) <= MAX_LINE else s[:MAX_LINE - 1] + "…"


def outcome(name, errs, dry, log_path, checks, saved):
    """name: the pass; errs: failed checks; dry: a headless run; checks: how many checks ran; saved: [(path, bytes)]
    written. A failure wins over dry (nothing is saved either way)."""
    if errs:
        shown = [f"  - {_short(e)}" for e in errs[:MAX_ERRS]]
        more = [f"  (and {len(errs) - MAX_ERRS} more)"] if len(errs) > MAX_ERRS else []
        text = "\n".join([f"{len(errs)} of {checks} checks failed, so the model was NOT saved.", "", "Failed checks:"]
                         + shown + more + ["", f"Log: {log_path}"])
        return Outcome("not_saved", f"{name}: NOT SAVED", text, ["NOT SAVED"])
    if dry:
        return Outcome("dry", f"{name}: dry run", f"All {checks} checks passed; a headless run is a dry run, so the model "
                       f"was not saved.\n\nLog: {log_path}", ["DRY RUN (headless): all checks passed, not saved"])
    files = [f"  {p} ({size(b)})" for p, b in saved]
    text = "\n".join([f"All {checks} checks passed. Saved:"] + files + ["", f"Log: {log_path}"])
    return Outcome("saved", f"{name}: SAVED", text, [f"SAVED {p} {b}" for p, b in saved])


def notice_mode(env):
    """How a GUI run shows its outcome, from PASS_GUI_NOTICE (see the header); an unknown value keeps the box."""
    m = (env.get("PASS_GUI_NOTICE") or "box").strip().lower()
    return m if m in MODES else "box"
