#!/usr/bin/env python3
"""Build a CREDITS.md from a repo's REUSE.toml, a licence-rules file and a projects file, or check it is current.

    python3 platform/pages/credits.py --projects P --reuse REUSE.toml --licences L --licence-dir LICENSES --out CREDITS.md
    (same) --check      exit 1 if the file differs from what would be written; last line "credits: OK"

Generic (stdlib only): the printer's data is in the files it is given.
- REUSE.toml (https://reuse.software/spec-3.3/): each [[annotations]] entry's SPDX-FileCopyrightText holders and
  SPDX-License-Identifier say who made which repo files.
- The licence-rules file (platform/viewer/rules.py format): every rule needs a "credit", a project key or "own" (or a
  list of keys), saying whose parts it clears for the pages.
- The projects file: {"title", "intro": [markdown paragraphs], "own_holders": [REUSE holders that are this repo],
  "licence_names"?: {id: shown name}, "licence_urls"?: {id: url},
  "projects": [{"key", "name", "by", "links": [[text, url], ...] (the name links to the first), "used", "reuse"?: [holders],
                "licence_urls"?: {id: url}}]}.
One row per project, in the projects file's order. Its licences are those of its REUSE entries and its rules; each
links to <licence-dir>/<id>.txt when that exists, else to licence_urls, else (an SPDX id) to spdx.org. It fails (exit
1, with every problem) on a REUSE holder or rule credit with no project, a project nothing uses, a rule without a
credit, or a LicenseRef with no text and no URL.
"""
import argparse, json, os, sys, tomllib

OWN = "own"


def as_list(v):
    return v if isinstance(v, list) else [v]


def build(projects, reuse, rules, licence_dir, out_dir):
    """-> (markdown text, problems). projects/reuse/rules are the parsed files."""
    probs = []
    known = {p["key"]: p for p in projects["projects"]}
    own = set(projects.get("own_holders", []))
    holder_of = {}
    for p in projects["projects"]:
        for h in p.get("reuse", []):
            holder_of[h] = p["key"]
    files = {k: [] for k in known}            # key -> [paths]
    lics = {k: [] for k in known}             # key -> [SPDX ids], first-seen order
    pages = {k: False for k in known}

    def add_lic(k, lic):
        if lic not in lics[k]: lics[k].append(lic)

    for a in reuse.get("annotations", []):
        lic = a.get("SPDX-License-Identifier", "")
        for h in as_list(a.get("SPDX-FileCopyrightText", [])):
            if h in own: continue
            k = holder_of.get(h)
            if not k:
                probs.append(f"REUSE holder {h!r} has no project in the projects file"); continue
            for path in as_list(a.get("path", [])):
                if path not in files[k]: files[k].append(path)
            add_lic(k, lic)
    for i, r in enumerate(rules.get("rules", [])):
        if "credit" not in r:
            probs.append(f"licence rule {i + 1} ({r.get('source', '')[:60]}...) has no 'credit'"); continue
        for k in as_list(r["credit"]):
            if k == OWN: continue
            if k not in known:
                probs.append(f"licence rule {i + 1}: credit {k!r} is no project in the projects file"); continue
            pages[k] = True
            add_lic(k, r["licence"])
    for k in known:
        if not files[k] and not pages[k]:
            probs.append(f"project {k!r} is used by no REUSE entry and no licence rule")

    names = projects.get("licence_names", {})

    def lic_link(k, lic):
        url = known[k].get("licence_urls", {}).get(lic) or projects.get("licence_urls", {}).get(lic)
        if not url and os.path.isfile(os.path.join(licence_dir, lic + ".txt")):
            url = os.path.relpath(os.path.join(licence_dir, lic + ".txt"), out_dir)
        if not url:
            if lic.startswith("LicenseRef-"):
                probs.append(f"project {k!r}: {lic} has no text in {licence_dir} and no licence_urls entry")
                return lic
            url = f"https://spdx.org/licenses/{lic}.html"
        return f"[{names.get(lic, lic)}]({url})"

    def where(k):
        out = []
        if files[k]:
            shown = []
            dirs = [q[:-2] for q in files[k] if q.endswith("/**") and "*" not in q[:-3]]
            for path in files[k]:
                p = path[:-3] + "/" if path.endswith("/**") else path
                if any(p != d and p.startswith(d) for d in dirs): continue    # inside a folder already listed
                shown.append(f"[`{p}`]({p})" if "*" not in p else f"`{p}`")
            out.append("repo: " + ", ".join(shown))
        if pages[k]: out.append("pages")
        return "; ".join(out)

    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    rows = []
    for p in projects["projects"]:
        k = p["key"]
        if not (files[k] or pages[k]): continue
        (t0, u0), more = p["links"][0], p["links"][1:]
        proj = f"[{cell(p['name'])}]({u0})" + "".join(f", [{cell(t)}]({u})" for t, u in more)
        rows.append(f"| {proj} | {cell(p['by'])} | {cell(p['used'])} | "
                    f"{', '.join(lic_link(k, l) for l in lics[k])} | {cell(where(k))} |")
    text = [f"# {projects['title']}", "",
            "<!-- GENERATED by platform/pages/credits.py from REUSE.toml, cad/viewer/licences.json and "
            "cad/credits.json: do not edit by hand; edit those and rerun it -->", ""]
    for para in projects.get("intro", []):
        text += [para, ""]
    text += ["| Project | By | What we used | Licence | Where |", "|---|---|---|---|---|"] + rows + [""]
    text += ["\"repo\" names the files this repository redistributes; \"pages\" means parts shown on the public "
             "reference pages.", ""]
    return "\n".join(text), probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--projects", required=True)
    ap.add_argument("--reuse", required=True)
    ap.add_argument("--licences", required=True)
    ap.add_argument("--licence-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    with open(a.projects, encoding="utf-8") as f: projects = json.load(f)
    with open(a.reuse, "rb") as f: reuse = tomllib.load(f)
    with open(a.licences, encoding="utf-8") as f: rules = json.load(f)
    text, probs = build(projects, reuse, rules, a.licence_dir, os.path.dirname(os.path.abspath(a.out)))
    for p in probs: print(f"credits: {p}")
    if probs: return 1
    if a.check:
        old = open(a.out, encoding="utf-8").read() if os.path.isfile(a.out) else None
        if old != text:
            print(f"credits: {a.out} is stale: rerun platform/pages/credits.py without --check"); return 1
    else:
        with open(a.out, "w", encoding="utf-8") as f: f.write(text)
    print(f"credits: {text.count(chr(10) + '| ') - 1} rows")
    print("credits: OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
