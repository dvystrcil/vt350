# Shared by the page makers (platform/viewer/turntable_page.py, viewer_page.py): put a big file on a GitHub release
# under a name made from its sha256, record it in the pages' assets.json (read by fetch_assets.py), and list a page in
# the pages' index.html. A new name per content means a re-render never replaces a file the live site still uses.
import datetime, hashlib, html, json, os, shutil, subprocess


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def asset_name(stem, sha, ext):
    return f"{stem}-{sha[:8]}{ext}"


def upload(path, tag, repo=None):
    """Upload path to release tag, creating the release as a pre-release if it doesn't exist."""
    r = ["--repo", repo] if repo else []
    if subprocess.run(["gh", "release", "view", tag] + r, capture_output=True).returncode:
        subprocess.run(["gh", "release", "create", tag, "--prerelease", "--title", f"Page assets: {tag}",
                        "--notes", "Large files for the reference pages, fetched and checked by "
                                   "platform/pages/fetch_assets.py. Not a printer release."] + r, check=True)
    subprocess.run(["gh", "release", "upload", tag, path, "--clobber"] + r, check=True)


def put_asset(src, stem, ext, tag, into, pages, repo=None, do_upload=True, keep_dir=None):
    """The whole step: name src by its sha256, upload it (or copy it to keep_dir), record it in assets.json."""
    sha = sha256(src); name = asset_name(stem, sha, ext)
    if do_upload:
        tmp = os.path.join(os.path.dirname(os.path.abspath(src)), name)
        if os.path.abspath(src) != tmp: shutil.copy2(src, tmp)
        try: upload(tmp, tag, repo)
        finally:
            if os.path.abspath(src) != tmp: os.remove(tmp)
    elif keep_dir:
        shutil.copy2(src, os.path.join(keep_dir, name))
    set_asset(os.path.join(pages, "assets.json"), {"release": tag, "asset": name, "into": into, "sha256": sha})
    return name


def set_asset(manifest, entry):
    """One entry per (into, file type): a new frames zip or GLB replaces the old one for that page folder."""
    m = json.load(open(manifest)) if os.path.exists(manifest) else {"assets": []}
    ext = os.path.splitext(entry["asset"])[1]
    m["assets"] = [a for a in m["assets"]
                   if not (a["into"] == entry["into"] and os.path.splitext(a["asset"])[1] == ext)] + [entry]
    with open(manifest, "w") as f: json.dump(m, f, indent=1); f.write("\n")


def add_index_entry(index, name, title, blurb, issue):
    """Add <li> for name.html after <ul class="pages">. True: added; False: already there; None: no such list."""
    s = open(index, encoding="utf-8").read()
    if f'href="{name}.html"' in s: return False
    anchor = '  <ul class="pages">\n'
    if anchor not in s: return None
    li = (f'    <li>\n      <a href="{name}.html">{html.escape(title)}</a>\n'
          f'      <p>{html.escape(blurb)}</p>\n'
          f'      <span class="meta">{datetime.date.today().isoformat()} · {html.escape(issue)}</span>\n'
          '    </li>\n')
    open(index, "w", encoding="utf-8").write(s.replace(anchor, anchor + li, 1)); return True


def index_message(added):
    return {True: "index.html: entry added", False: "index.html: already lists it",
            None: 'index.html: no <ul class="pages">; add the link by hand'}[added]
