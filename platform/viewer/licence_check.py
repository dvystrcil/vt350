#!/usr/bin/env python3
"""The licence check of a viewer export (vt350#220 AC3): every part in the export against a licence file (rules.py).
Plain python, no FreeCAD.

    python3 platform/viewer/licence_check.py <parts>[:<parts>...] <licences.json> [log file]

<parts> is either
  - an export's scene.json with "parts" (export_meshes.py with RENDER_SELECT: exactly the exported parts), or
  - a part index, <model>.parts.json (platform/freecad/part_index.py, format "vt350-part-index/1"): every leaf solid of
    that model that no other leaf consumes, the set export_meshes.py exports from a whole model. It also lists the
    hidden parts and stand-ins the export leaves out, so it is a superset: a whole-model export passes only if every
    part of every model in it is cleared. For a whole printer pass the model's index and each VT350_EXTRA file's,
    ':'-separated.

Logs one line per part (its licence and where that was read), then "licence-check: OK", or the failures and
"licence-check: FAILED" (exit 1): a part no rule matches or whose rule says "unknown" (an open question), a part
whose licence isn't shareable, or a scene.json with no part list (a whole export: pass its part indexes instead).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules

INDEX_FORMAT = "vt350-part-index/1"


def parts_of(fn):
    """-> the parts [{"label", "path"}] one file lists, or None for a scene.json without "parts"."""
    d = json.load(open(fn, encoding="utf-8"))
    if d.get("format") == INDEX_FORMAT:
        return [{"label": p["label"], "path": p["path"]} for p in d["parts"] if not p.get("consumed")]
    return d.get("parts") or None


def main(parts_fns, lic_fn, log_fn=None):
    lic = json.load(open(lic_fn, encoding="utf-8"))
    parts, problems = [], []
    for fn in [f for f in parts_fns.split(":") if f]:
        got = parts_of(fn)
        if got is None:
            problems.append(f"no 'parts' in {os.path.basename(fn)}: export with RENDER_SELECT, or pass the part "
                            f"indexes (<model>.parts.json) of a whole-model export")
        else:
            parts += got
    lines = []
    if not problems:
        lines, problems = rules.check(lic, parts)
    out = lines + [f"{len(parts)} parts, {len(problems)} problems"] + problems
    out.append("licence-check: " + ("FAILED" if problems else "OK"))
    text = "\n".join(out) + "\n"
    if log_fn:
        open(log_fn, "w", encoding="utf-8").write(text)
    sys.stdout.write("\n".join(out[-(len(problems) + 2):]) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:4]))
