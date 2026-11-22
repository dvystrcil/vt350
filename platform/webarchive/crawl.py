#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep offline copies of the web sites a build depends on (vendor docs, wikis), and their text for reading.

Each site in a sites file is crawled with browsertrix-crawler (a real headless Chrome in docker, pinned by digest),
which gets through sites that refuse plain HTTP clients and builds pages that need JavaScript. A crawl leaves:

    <out>/collections/<name>/<name>.wacz     the archive: open it offline in https://replayweb.page (or its app)
    <out>/collections/<name>/text/*.md       one Markdown file per page: title, URL, crawl time, then the page text
    <out>/collections/<name>/text/INDEX.md   every page, with its file
    <out>/<name>.log                         the crawler's log

Re-running a site replaces its collection, so a re-crawl picks up changed docs. The copies are other people's
copyright and never go in git: --out inside a git checkout is refused. Note facts in your own words, with a link.

    python3 platform/webarchive/crawl.py SITES.json --out DIR [--only NAME ...] [--text-only]

SITES.json: {"sites": [{"name": "...", "url": "https://...", "scope": "prefix", "page_limit": 200,
             "exclude": ["regex", ...], "note": "..."}]}
  scope: browsertrix --scopeType (page, page-spa, prefix, host, domain); default "prefix".
  --text-only rewrites text/ from an existing crawl without crawling again.

Prints "webarchive: OK" when every site crawled and gave at least one page of text; exit 1 otherwise.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# browsertrix-crawler 1.15.4 (2026-11-11). Bump by pulling a newer tag and copying its RepoDigest here.
IMAGE = "webrecorder/browsertrix-crawler@sha256:261da066ea1a581558ca99b77e7a70a7183e73865f77b832c1823d816a6c75f0"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SCOPES = {"page", "page-spa", "prefix", "host", "domain"}


def load_sites(path):
    sites = json.loads(Path(path).read_text())["sites"]
    names = set()
    for s in sites:
        if not NAME_RE.match(s.get("name", "")):
            raise ValueError(f"site name {s.get('name')!r}: use lower-case letters, digits and '-'")
        if s["name"] in names:
            raise ValueError(f"site name {s['name']!r} appears twice")
        names.add(s["name"])
        if not s.get("url", "").startswith(("http://", "https://")):
            raise ValueError(f"site {s['name']}: url must start with http(s)://")
        if s.get("scope", "prefix") not in SCOPES:
            raise ValueError(f"site {s['name']}: scope must be one of {sorted(SCOPES)}")
    return sites


def crawl_args(site):
    """The browsertrix `crawl` arguments for one site."""
    args = ["crawl", "--url", site["url"], "--collection", site["name"], "--scopeType", site.get("scope", "prefix"),
            "--text", "to-pages", "--generateWACZ", "--overwrite", "--workers", "2", "--delay", "1",
            "--timeout", "60", "--pageLimit", str(site.get("page_limit", 500))]
    for rx in site.get("exclude", []):
        args += ["--exclude", rx]
    return args


def norm_url(url):
    """The key two spellings of one page share: no fragment, no trailing slash."""
    return url.split("#", 1)[0].rstrip("/")


def slug(url):
    path = re.sub(r"^https?://", "", norm_url(url))
    s = re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-").lower()
    return (s or "index")[:120]


def read_pages(pages_dir):
    """The crawled pages with text, one per page: `/x` and `/x/` are one page, and the longer text wins."""
    best = {}
    for f in sorted(Path(pages_dir).glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if "url" not in d or not d.get("text"):
                continue  # the header line, or a page that gave no text (a PDF, a redirect)
            k = norm_url(d["url"])
            if k not in best or len(d["text"]) > len(best[k]["text"]):
                best[k] = d
    return [best[k] for k in sorted(best)]


def write_text(pages, text_dir):
    """One Markdown file per page plus INDEX.md; returns the number of pages written."""
    text_dir = Path(text_dir)
    if text_dir.exists():
        shutil.rmtree(text_dir)
    text_dir.mkdir(parents=True)
    rows, used = [], set()
    for p in pages:
        name = slug(p["url"])
        while name in used:
            name += "-x"
        used.add(name)
        title = (p.get("title") or p["url"]).strip()
        (text_dir / f"{name}.md").write_text(
            f"# {title}\n\nSource: {p['url']}\nCrawled: {p.get('ts', '')}\n\n---\n\n{p['text'].strip()}\n")
        rows.append(f"| [{title}]({name}.md) | {p['url']} |")
    (text_dir / "INDEX.md").write_text("# Pages\n\n| Page | URL |\n|---|---|\n" + "\n".join(rows) + "\n")
    return len(pages)


def git_root(path):
    """The git work tree that holds `path` (or would, once made), or None."""
    p = Path(path)
    while not p.exists():
        p = p.parent
    r = subprocess.run(["git", "-C", str(p), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def run_crawl(site, out):
    log = out / f"{site['name']}.log"
    cmd = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "-v", f"{out}:/crawls",
           IMAGE] + crawl_args(site)
    with open(log, "w") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
    return rc, log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sites")
    ap.add_argument("--out", required=True, help="where the collections go (kept out of git: they are big)")
    ap.add_argument("--only", action="append", default=[], help="crawl just this site (repeatable)")
    ap.add_argument("--text-only", action="store_true", help="rewrite text/ from the last crawl; no crawling")
    a = ap.parse_args(argv)
    sites = load_sites(a.sites)
    unknown = set(a.only) - {s["name"] for s in sites}
    if unknown:
        sys.exit(f"webarchive: no such site: {', '.join(sorted(unknown))}")
    out = Path(a.out).expanduser().resolve()
    repo = git_root(out)
    if repo:
        sys.exit(f"webarchive: --out {out} is inside the git checkout {repo}; crawled sites are other people's "
                 "copyright (Beacon's docs are CC BY-NC-ND), so keep them outside git")
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for site in sites:
        if a.only and site["name"] not in a.only:
            continue
        coll = out / "collections" / site["name"]
        if not a.text_only:
            rc, log = run_crawl(site, out)
            if rc != 0:
                print(f"FAIL   {site['name']}: crawler exit {rc}; see {log}")
                ok = False
                continue
        n = write_text(read_pages(coll / "pages"), coll / "text") if (coll / "pages").is_dir() else 0
        if n == 0:
            print(f"FAIL   {site['name']}: no page text in {coll}")
            ok = False
            continue
        print(f"ok     {site['name']}: {n} pages -> {coll / 'text'}  (archive: {coll / (site['name'] + '.wacz')})")
    print("webarchive: OK" if ok else "webarchive: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
