#!/usr/bin/env python3
"""Periodic health review (vt350#120): run the checks that can run unattended, write a markdown report for the health
review issue, and exit 1 if any is red. The checks that need a person (CAD accuracy, clashes, renders, batch lane)
are listed as boxes for the owner to tick.

  python3 platform/health/health_review.py --repo OWNER/REPO --out report.md \
      --dockerfile platform/kalisim/Dockerfile \
      --git-pin KALICO_SHA=https://github.com/KalicoCrew/kalico@main \
      --git-pin TOOLCHANGER_SHA=https://github.com/viesturz/klipper-toolchanger@main \
      --image-pin ghcr.io/kalicocrew/kalico:main \
      --run "bash platform/testing/check_test_tmp.sh" --doc notes/status.md --scripts cad/scripts

Status per check: ok, amber (worth a look, doesn't fail the run: a pin behind upstream, an old doc), red (fails the
run: a workflow red on the default branch, the manual run failing), info (a number to watch). A check that can't reach
its source (no network, no token) is amber and says why. Generic: every printer-specific value comes in as an argument.
Stdlib only (plus `git` and, for CI status, `gh`).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

MANUAL = ["CAD accuracy: the newest lite-N's checks and renders match the build plan",
          "Clash checks: the last sweep and refresh are clean, or each clash has an issue",
          "Renders: the newest renders show the current model",
          "Kalico simulation: printer.cfg limits still match the CAD (kalico-batch)",
          "Batch lane: the last few jobs finished and posted their comment"]
STALE_DAYS = 45


def dockerfile_pins(text):
    """{ARG name: value} for ARG X=value lines, and [(image, digest)] for FROM image@sha256:digest lines."""
    args = dict(re.findall(r"^ARG (\w+)=(\S+)", text, re.M))
    froms = re.findall(r"^FROM ([^\s@]+)@(sha256:[0-9a-f]{64})", text, re.M)
    return args, froms


def parse_ls_remote(out, ref):
    """`git ls-remote URL REF` output -> the sha for refs/heads/REF (or REF itself), or None."""
    for line in out.splitlines():
        sha, _, name = line.partition("\t")
        if name in (f"refs/heads/{ref}", f"refs/tags/{ref}", ref):
            return sha
    return None


def git_head(url, ref):
    r = subprocess.run(["git", "ls-remote", url, ref], capture_output=True, text=True, timeout=60)
    return parse_ls_remote(r.stdout, ref) if r.returncode == 0 else None


def image_digest(image):
    """The registry's current digest for image (registry/repo:tag), via the anonymous token flow; None if unreachable."""
    reg, _, rest = image.partition("/")
    repo, _, tag = rest.rpartition(":")
    try:
        with urllib.request.urlopen(f"https://{reg}/token?scope=repository:{repo}:pull", timeout=30) as r:
            token = json.load(r)["token"]
        req = urllib.request.Request(f"https://{reg}/v2/{repo}/manifests/{tag}", method="HEAD", headers={
            "Authorization": f"Bearer {token}",
            "Accept": ", ".join(["application/vnd.oci.image.index.v1+json",
                                 "application/vnd.docker.distribution.manifest.list.v2+json",
                                 "application/vnd.oci.image.manifest.v1+json",
                                 "application/vnd.docker.distribution.manifest.v2+json"])})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.headers.get("Docker-Content-Digest")
    except Exception:
        return None


def ci_runs(repo, branch):
    """[(workflow name, conclusion or status)] for each active workflow's newest run on branch; None without gh."""
    try:
        wf = json.loads(subprocess.run(["gh", "api", f"repos/{repo}/actions/workflows", "--paginate"],
                                       capture_output=True, text=True, check=True, timeout=120).stdout)
    except Exception:
        return None
    out = []
    for w in wf.get("workflows", []):
        if w.get("state") != "active":
            continue
        try:
            runs = json.loads(subprocess.run(["gh", "api", f"repos/{repo}/actions/workflows/{w['id']}/runs?branch={branch}&per_page=1"],
                                             capture_output=True, text=True, check=True, timeout=120).stdout)
        except Exception:
            out.append((w["name"], "unreachable")); continue
        r = (runs.get("workflow_runs") or [None])[0]
        out.append((w["name"], "no runs" if r is None else (r.get("conclusion") or r.get("status"))))
    return out


def ci_check(runs):
    if runs is None:
        return ("CI", "amber", "couldn't read the workflow runs (no `gh` or no token)")
    bad = [f"{n}: {c}" for n, c in runs if c in ("failure", "timed_out", "startup_failure", "cancelled")]
    if bad:
        return ("CI", "red", "red on the default branch: " + "; ".join(bad))
    return ("CI", "ok", f"{len(runs)} workflows; newest run on the default branch of each is not red")


def pin_check(name, pinned, upstream, where):
    if upstream is None:
        return (f"Version drift: {name}", "amber", f"couldn't reach {where}; pinned {pinned[:19]}")
    if upstream == pinned:
        return (f"Version drift: {name}", "ok", f"pinned = {where} ({pinned[:19]})")
    return (f"Version drift: {name}", "amber", f"pinned {pinned[:19]}, {where} is now {upstream[:19]}: review and bump on purpose")


def run_check(cmd):
    t = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    st = "ok" if r.returncode == 0 else "red"
    return ("Manual run", st, f"`{cmd}`: exit {r.returncode} in {time.time() - t:.0f} s, last line `{last}`")


def doc_check(path, now=None):
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path], capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        return (f"Docs: {path}", "amber", "no commit found")
    days = ((now or time.time()) - int(r.stdout.strip())) / 86400
    return (f"Docs: {path}", "ok" if days <= STALE_DAYS else "amber", f"last changed {days:.0f} days ago (amber over {STALE_DAYS})")


def scripts_check(d):
    files = sorted(f for f in os.listdir(d) if f.endswith((".py", ".sh"))) if os.path.isdir(d) else []
    oneoff = [f for f in files if re.search(r"(repro|probe|tmp|scratch|oneoff)", f)]
    return ("Script hygiene", "info", f"{len(files)} scripts in {d}" + (f"; one-off looking: {', '.join(oneoff)}" if oneoff else ""))


def report(rows, when):
    icon = {"ok": "✅", "amber": "🟡", "red": "🔴", "info": "ℹ️"}
    lines = [f"Health review, {when} (`platform/health/health_review.py`, vt350#120).", "",
             "## Checked automatically", "", "| | Check | Result |", "|---|---|---|"]
    lines += [f"| {icon[s]} | {a} | {d} |" for a, s, d in rows]
    lines += ["", "## For the owner to tick", ""] + [f"- [ ] {m}" for m in MANUAL]
    red = [a for a, s, _ in rows if s == "red"]
    lines += ["", f"**Overall: {'RED (' + ', '.join(red) + ')' if red else 'no red checks'}.**"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dockerfile")
    ap.add_argument("--git-pin", action="append", default=[], help="ARG_NAME=URL@ref")
    ap.add_argument("--image-pin", action="append", default=[], help="registry/repo:tag pinned by digest in --dockerfile")
    ap.add_argument("--run", action="append", default=[])
    ap.add_argument("--doc", action="append", default=[])
    ap.add_argument("--scripts", action="append", default=[])
    a = ap.parse_args(argv)
    rows = [ci_check(ci_runs(a.repo, a.branch))]
    args, froms = dockerfile_pins(open(a.dockerfile).read()) if a.dockerfile else ({}, [])
    for spec in a.git_pin:
        name, _, src = spec.partition("="); url, _, ref = src.rpartition("@")
        if name not in args:
            rows.append((f"Version drift: {name}", "red", f"no ARG {name} in {a.dockerfile}")); continue
        rows.append(pin_check(name, args[name], git_head(url, ref), f"{url} {ref}"))
    for image in a.image_pin:
        repo = image.rpartition(":")[0]
        pinned = next((d for img, d in froms if img == repo), None)
        if pinned is None:
            rows.append((f"Version drift: {image}", "red", f"no FROM {repo}@sha256:… in {a.dockerfile}")); continue
        rows.append(pin_check(image, pinned, image_digest(image), image))
    rows += [run_check(c) for c in a.run]
    rows += [doc_check(d) for d in a.doc]
    rows += [scripts_check(d) for d in a.scripts]
    with open(a.out, "w") as f:
        f.write(report(rows, time.strftime("%Y-%m-%d")))
    for r in rows:
        print(f"{r[1]:5}  {r[0]}: {r[2]}")
    red = any(s == "red" for _, s, _ in rows)
    print("health-review: " + ("RED" if red else "OK"))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
