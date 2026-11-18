#!/usr/bin/env python3
"""The licence check of a viewer export (vt350#220 AC3): every part in scene.json's "parts" (export_meshes.py with
RENDER_SELECT) against a licence file (rules.py). Plain python, no FreeCAD.

    python3 platform/viewer/licence_check.py <export dir>/scene.json <licences.json> [log file]

Logs one line per part (its licence and where that was read), then "licence-check: OK", or the failures and
"licence-check: FAILED" (exit 1): a part no rule matches, a part whose licence isn't shareable, or an export with no
part list (made without RENDER_SELECT).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules


def main(scene_fn, lic_fn, log_fn=None):
    scene = json.load(open(scene_fn, encoding="utf-8"))
    lic = json.load(open(lic_fn, encoding="utf-8"))
    parts = scene.get("parts")
    if not parts:
        lines, problems = [], ["no 'parts' in scene.json: export with RENDER_SELECT"]
    else:
        lines, problems = rules.check(lic, parts)
    out = lines + [f"{len(parts or [])} parts, {len(problems)} problems"] + problems
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
