# A drag-to-turn page from turntable renders (vt350#220): frame_view.py --turntable names the views, render.py renders
# them, this makes the page. Two ways out:
#
#   python3 turntable_page.py stage <frames dir> <page.json> <out dir>
#       a self-contained preview folder: index.html + turntable.json + frames/. Open it with any web server
#       (python3 -m http.server -d <out dir>) or publish the folder as a private artifact.
#   python3 turntable_page.py publish <frames dir> <page.json> <pages dir> <name> --release TAG [--repo R] [--upload 0|1]
#       a page on a static site that keeps big files as GitHub release assets (platform/pages/fetch_assets.py):
#       writes <pages>/<name>.html and <pages>/<name>/turntable.json, zips the frames, uploads the zip to the release
#       (--upload 1; creates it as a pre-release if missing; --upload 0 leaves the zip beside the frames dir), and
#       records the zip's sha256 in <pages>/assets.json.
#       With an index.html holding <ul class="pages">, adds an entry for the page if it has none.
#
# page.json: {"title", "title_accent", "model", "prefix", "elevations": [..], "azimuths": N, "start_elevation"?,
#   "foot"?, "credits"?, "links"?: [{"href", "text"}], "page_title"?, "blurb"?, "issue"?}.
# Every frame <prefix>-tt-e<EE>-a<AAA>.jpg must be in the frames dir, or nothing is written.
# Last line "turntable-page: OK".
import html, json, os, shutil, sys, tempfile, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pages"))
import sitepub

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "turntable.html")
PAGE_KEYS = ("title", "title_accent", "model", "prefix", "elevations", "azimuths", "start_elevation", "foot",
             "credits", "links")


def frame_names(cfg):
    n = cfg["azimuths"]
    return [f"{cfg['prefix']}-tt-e{e:02d}-a{i * 360 // n:03d}.jpg" for e in cfg["elevations"] for i in range(n)]


def missing_frames(frames, cfg):
    return [f for f in frame_names(cfg) if not os.path.isfile(os.path.join(frames, f))]


def render_page(cfg, base, standalone):
    s = open(TEMPLATE, encoding="utf-8").read()
    s = s[s.index("\n") + 1:]                       # drop the template's own comment line
    title = cfg.get("page_title") or f"{cfg['title']} {cfg.get('title_accent', '')}".replace("·", "").strip()
    s = s.replace("__TITLE__", html.escape(title)).replace("__BASE__", base)
    if not standalone:                              # an artifact wraps the page in its own document
        s = s[s.index("<title>"):]
    return s


def page_json(cfg):
    return {k: cfg[k] for k in PAGE_KEYS if k in cfg}


def stage(frames, cfg, out):
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    for f in frame_names(cfg): shutil.copy2(os.path.join(frames, f), os.path.join(out, "frames", f))
    json.dump(page_json(cfg), open(os.path.join(out, "turntable.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(out, "index.html"), "w").write(render_page(cfg, "", standalone=False))
    print(f"staged {len(frame_names(cfg))} frames + index.html + turntable.json in {out}")


def zip_frames(frames, cfg, path):
    """Stored (JPEGs don't shrink), sorted, fixed timestamps: the same frames give the same zip (and asset name)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(frame_names(cfg)):
            info = zipfile.ZipInfo("frames/" + f, date_time=(2020, 1, 1, 0, 0, 0))
            z.writestr(info, open(os.path.join(frames, f), "rb").read())


def publish(frames, cfg, pages, name, tag, repo=None, do_upload=True):
    folder = os.path.join(pages, name); os.makedirs(folder, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        z = os.path.join(tmp, "frames.zip"); zip_frames(frames, cfg, z)
        asset = sitepub.put_asset(z, f"{cfg['prefix']}-{name}-frames", ".zip", tag, name, pages, repo, do_upload,
                                  keep_dir=os.path.dirname(os.path.abspath(frames)))     # --upload 0: beside frames/
    json.dump(page_json(cfg), open(os.path.join(folder, "turntable.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(pages, name + ".html"), "w").write(render_page(cfg, name + "/", standalone=True))
    print(f"{name}.html, {name}/turntable.json; {asset} ({'uploaded to ' + tag if do_upload else 'not uploaded'})")
    idx = os.path.join(pages, "index.html")
    if os.path.exists(idx):
        print(sitepub.index_message(sitepub.add_index_entry(idx, name, cfg.get("page_title") or name,
                                                            cfg.get("blurb", ""), cfg.get("issue", ""))))


def main(argv):
    if len(argv) < 4 or argv[0] not in ("stage", "publish"):
        print("usage: turntable_page.py stage <frames> <page.json> <out> | "
              "publish <frames> <page.json> <pages> <name> --release TAG [--repo R] [--upload 0|1]"); return 2
    frames, cfg = argv[1], json.load(open(argv[2]))
    gone = missing_frames(frames, cfg)
    if gone:
        print(f"{len(gone)} of {len(frame_names(cfg))} frames missing from {frames}, e.g. {gone[0]}"); return 1
    if argv[0] == "stage":
        stage(frames, cfg, argv[3])
    else:
        opts = dict(zip(argv[5::2], argv[6::2]))
        if "--release" not in opts: print("publish needs --release TAG"); return 2
        publish(frames, cfg, argv[3], argv[4], opts["--release"], opts.get("--repo"), opts.get("--upload", "1") == "1")
    print("turntable-page: OK"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
