#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep offline copies of the web sites a build depends on (vendor docs, wikis), and their text for reading.

Each site in a sites file is crawled with browsertrix-crawler (a real headless Chrome in docker, pinned by digest),
which gets through sites that refuse plain HTTP clients and builds pages that need JavaScript. A crawl leaves:

    <out>/collections/<name>/<name>.wacz     the archive: open it offline in https://replayweb.page (or its app)
    <out>/collections/<name>/text/*.md       one Markdown file per page: title, URL, crawl time, then the page text
    <out>/collections/<name>/text/INDEX.md   every page, with its file
    <out>/collections/<name>/text/images/    each page's images (taken from the WARC); each page's .md lists its own
    <out>/<name>.log                         the crawler's log

Re-running a site replaces its collection, so a re-crawl picks up changed docs. The copies are other people's
copyright and never go in git: --out inside a git checkout is refused. Note facts in your own words, with a link.

    python3 platform/webarchive/crawl.py SITES.json --out DIR [--only NAME ...] [--text-only]

SITES.json: {"sites": [{"name": "...", "url": "https://...", "scope": "prefix", "page_limit": 200,
             "exclude": ["regex", ...], "note": "..."}]}
  "urls": [...] in place of "url" crawls several start pages into one collection (e.g. scope "page": just those).
  scope: browsertrix --scopeType (page, page-spa, prefix, host, domain); default "prefix".
  extra_hops: also save pages this many links beyond the scope (browsertrix --extraHops); default 0.
  --text-only rewrites text/ from an existing crawl without crawling again.

Prints "webarchive: OK" when every site crawled and gave at least one page of text; exit 1 otherwise.
"""
import argparse
import gzip
import hashlib
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
MIN_IMAGE_BYTES = 2048  # smaller ones are icons, spacers and tracking pixels
IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
             "image/svg+xml": ".svg", "image/avif": ".avif"}


def load_sites(path):
    sites = json.loads(Path(path).read_text())["sites"]
    names = set()
    for s in sites:
        if not NAME_RE.match(s.get("name", "")):
            raise ValueError(f"site name {s.get('name')!r}: use lower-case letters, digits and '-'")
        if s["name"] in names:
            raise ValueError(f"site name {s['name']!r} appears twice")
        names.add(s["name"])
        urls = s.get("urls") or [s.get("url", "")]
        if ("url" in s) == ("urls" in s):
            raise ValueError(f"site {s['name']}: give either url or urls")
        if not all(u.startswith(("http://", "https://")) for u in urls):
            raise ValueError(f"site {s['name']}: every url must start with http(s)://")
        s["urls"] = urls
        if s.get("scope", "prefix") not in SCOPES:
            raise ValueError(f"site {s['name']}: scope must be one of {sorted(SCOPES)}")
    return sites


def crawl_args(site):
    """The browsertrix `crawl` arguments for one site."""
    args = ["crawl"]
    for u in site.get("urls") or [site["url"]]:
        args += ["--url", u]
    args += ["--collection", site["name"], "--scopeType", site.get("scope", "prefix"),
             "--text", "to-pages", "--generateWACZ", "--overwrite", "--workers", "2", "--delay", "1",
             "--timeout", "60", "--pageLimit", str(site.get("page_limit", 500))]
    if site.get("extra_hops"):
        args += ["--extraHops", str(site["extra_hops"])]
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


def warc_records(path):
    """(WARC headers, HTTP headers, body) for each response record in a .warc.gz; browsertrix stores bodies decoded."""
    with gzip.open(path, "rb") as f:
        data = f.read()
    i = 0
    while True:
        i = data.find(b"WARC/1.", i)
        if i < 0:
            return
        end = data.find(b"\r\n\r\n", i)
        head = dict(_header_lines(data[i:end]))
        n = int(head.get("content-length", 0))
        block = data[end + 4:end + 4 + n]
        i = end + 4 + n
        if head.get("warc-type") != "response" or not block.startswith(b"HTTP/"):
            continue
        hend = block.find(b"\r\n\r\n")
        http = dict(_header_lines(block[:hend]))
        body = block[hend + 4:]
        if "chunked" in http.get("transfer-encoding", ""):
            body = _dechunk(body)
        yield head, http, body


def _header_lines(raw):
    for line in raw.decode("latin1").split("\r\n")[1:]:
        k, sep, v = line.partition(":")
        if sep:
            yield k.strip().lower(), v.strip()


def _dechunk(body):
    out, i = bytearray(), 0
    while True:
        j = body.find(b"\r\n", i)
        size = int(body[i:j].split(b";")[0] or b"0", 16) if j >= 0 else 0
        if size == 0:
            return bytes(out)
        out += body[j + 2:j + 2 + size]
        i = j + 2 + size + 2


def read_images(archive_dir):
    """{page id: [(url, content type, bytes)]}: the images each page loaded, from the crawl's WARC files."""
    by_page, seen = {}, set()
    for f in sorted(Path(archive_dir).glob("*.warc.gz")):
        for head, http, body in warc_records(f):
            ctype = http.get("content-type", "").split(";")[0].strip().lower()
            page = head.get("warc-page-id")
            if ctype not in IMAGE_EXT or not page or len(body) < MIN_IMAGE_BYTES:
                continue
            url = head.get("warc-target-uri", "")
            if (page, url) in seen:
                continue
            seen.add((page, url))
            by_page.setdefault(page, []).append((url, ctype, body))
    return by_page


def read_pages(pages_dir):
    """The crawled pages with text, one per page: `/x` and `/x/` are one page, and the longer text wins.
    Each page keeps `ids`, every crawl id its spellings had, so images loaded by either spelling stay with it."""
    best, ids = {}, {}
    for f in sorted(Path(pages_dir).glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if "url" not in d or not d.get("text"):
                continue  # the header line, or a page that gave no text (a PDF, a redirect)
            k = norm_url(d["url"])
            ids.setdefault(k, []).append(d.get("id"))
            if k not in best or len(d["text"]) > len(best[k]["text"]):
                best[k] = d
    return [dict(best[k], ids=ids[k]) for k in sorted(best)]


def write_text(pages, text_dir, images=None):
    """One Markdown file per page plus INDEX.md; returns the number of pages written. `images` (from read_images)
    are saved under images/<page>/ and listed at the end of their page's file, largest first."""
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
        md = f"# {title}\n\nSource: {p['url']}\nCrawled: {p.get('ts', '')}\n\n---\n\n{p['text'].strip()}\n"
        imgs = {}
        for pid in p.get("ids") or [p.get("id")]:
            for url, ctype, body in (images or {}).get(pid, []):
                imgs.setdefault(url, (ctype, body))
        if imgs:
            d = text_dir / "images" / name
            d.mkdir(parents=True)
            lines = []
            for url, (ctype, body) in sorted(imgs.items(), key=lambda kv: -len(kv[1][1])):
                stem = re.sub(r"[^A-Za-z0-9._-]+", "-", url.split("?")[0].rstrip("/").rsplit("/", 1)[-1])[:60]
                stem = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", stem) or "image"
                fn = f"{stem}-{hashlib.sha256(body).hexdigest()[:8]}{IMAGE_EXT[ctype]}"
                (d / fn).write_bytes(body)
                lines.append(f"- [images/{name}/{fn}](images/{name}/{fn}) ({len(body) // 1024} KB) <- {url}")
            md += f"\n## Images ({len(lines)})\n\n" + "\n".join(lines) + "\n"
        (text_dir / f"{name}.md").write_text(md)
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
        n = (write_text(read_pages(coll / "pages"), coll / "text", read_images(coll / "archive"))
             if (coll / "pages").is_dir() else 0)
        if n == 0:
            print(f"FAIL   {site['name']}: no page text in {coll}")
            ok = False
            continue
        print(f"ok     {site['name']}: {n} pages -> {coll / 'text'}  (archive: {coll / (site['name'] + '.wacz')})")
    print("webarchive: OK" if ok else "webarchive: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
