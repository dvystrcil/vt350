# The pages workflow's large files: renders and models too big to commit live as GitHub release assets, and this
# script puts them in place before the site is uploaded. A manifest (JSON) lists each one with its sha256, so a
# changed or truncated asset fails the build instead of reaching the site.
#   python3 platform/pages/fetch_assets.py <manifest.json> [--repo owner/name] [--from-dir DIR]
#     manifest: {"assets": [{"release": tag, "asset": file name, "sha256": hex, "into": dir (relative to the
#                manifest's folder)}]}; a .zip is unpacked into "into", anything else is copied there.
#     --from-dir: take the files from DIR instead of downloading them (tests; a run by hand with the files at hand).
#     Downloads use `gh release download` (GH_TOKEN in CI). Last line "fetch-assets: OK".
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def place(src, into):
    """Unpack a zip into `into` (refusing any member that would land outside it), or copy the file there."""
    os.makedirs(into, exist_ok=True)
    if not src.endswith(".zip"):
        shutil.copy2(src, os.path.join(into, os.path.basename(src))); return 1
    root = os.path.realpath(into)
    with zipfile.ZipFile(src) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        for n in names:
            dest = os.path.realpath(os.path.join(root, n))
            if not dest.startswith(root + os.sep): raise ValueError(f"{os.path.basename(src)}: {n} unpacks outside {into}")
        z.extractall(root)
    return len(names)


def run(manifest, repo=None, from_dir=None):
    base = os.path.dirname(os.path.abspath(manifest))
    entries = json.load(open(manifest))["assets"]
    problems, ready = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for e in entries:
            if from_dir:
                src = os.path.join(from_dir, e["asset"])
            else:
                cmd = ["gh", "release", "download", e["release"], "--pattern", e["asset"], "--dir", tmp, "--clobber"]
                if repo: cmd += ["--repo", repo]
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode: problems.append(f"{e['asset']}: download failed: {r.stderr.strip()[:200]}"); continue
                src = os.path.join(tmp, e["asset"])
            if not os.path.isfile(src): problems.append(f"{e['asset']}: missing"); continue
            got = sha256(src)
            if got != e["sha256"]: problems.append(f"{e['asset']}: sha256 {got}, manifest says {e['sha256']}"); continue
            ready.append((e, src))
        if problems: return problems          # all or nothing: place files only when every asset checked out
        for e, src in ready:
            n = place(src, os.path.join(base, e["into"]))
            print(f"{e['asset']}: {n} file(s) into {e['into']}")
    return problems


def main(argv):
    if not argv or argv[0].startswith("-"):
        print("usage: fetch_assets.py <manifest.json> [--repo owner/name] [--from-dir DIR]"); return 2
    opts = dict(zip(argv[1::2], argv[2::2]))
    problems = run(argv[0], opts.get("--repo") or os.environ.get("GITHUB_REPOSITORY"), opts.get("--from-dir"))
    for p in problems: print(p)
    if problems: return 1
    print("fetch-assets: OK"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
