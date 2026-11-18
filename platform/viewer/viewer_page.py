# A live 3D viewer page (three.js) for a GLB, beside a Cycles render from a camera the page can match (vt350#220).
# Template: viewer.html. Two ways out, as turntable_page.py:
#
#   python3 viewer_page.py stage <model> <compare.jpg> <page.json> <out dir>
#       a preview folder: index.html (an artifact body) + viewer.json + the model + render-compare.jpg. <model> is a
#       .glb, or a .gltf.json with its buffer embedded (glb.py --json 1) for a host that doesn't serve .glb.
#   python3 viewer_page.py publish <model.glb> <compare.jpg> <page.json> <pages dir> <name> --release TAG
#                                  [--repo R] [--upload 0|1]
#       <pages>/<name>.html + <name>/viewer.json + <name>/render-compare.jpg (committed); the GLB goes to the release
#       under a name made from its sha256 and into <pages>/assets.json (platform/pages/fetch_assets.py fetches it).
#       --upload 0 leaves the named GLB beside <model.glb> instead. Adds an index entry if index.html has none.
#
# page.json: {"title", "title_accent", "model", "cam": {"pos", "look", "lens_mm"}, "prefix", "compare_alt"?,
#   "caption"?, "about"?, "credits"?, "links"?, "page_title"?, "blurb"?, "issue"?}. Last line "viewer-page: OK".
import html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pages"))
import sitepub

TEMPLATE = os.path.join(HERE, "viewer.html")
PAGE_KEYS = ("title", "title_accent", "model", "cam", "compare_alt", "caption", "about", "credits", "links")


def render_page(cfg, base, standalone):
    s = open(TEMPLATE, encoding="utf-8").read()
    s = s[s.index("\n") + 1:]                       # drop the template's own comment line
    title = cfg.get("page_title") or f"{cfg['title']} {cfg.get('title_accent', '')}".replace("·", "").strip()
    s = s.replace("__TITLE__", html.escape(title)).replace("__BASE__", base)
    return s if standalone else s[s.index("<title>"):]


def viewer_json(cfg, glb):
    return dict({k: cfg[k] for k in PAGE_KEYS if k in cfg}, glb=glb)


def stage(model, compare, cfg, out):
    os.makedirs(out, exist_ok=True)
    shutil.copy2(model, os.path.join(out, os.path.basename(model)))
    shutil.copy2(compare, os.path.join(out, "render-compare.jpg"))
    json.dump(viewer_json(cfg, os.path.basename(model)), open(os.path.join(out, "viewer.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(out, "index.html"), "w").write(render_page(cfg, "", standalone=False))
    print(f"staged index.html, viewer.json, {os.path.basename(model)}, render-compare.jpg in {out}")


def publish(model, compare, cfg, pages, name, tag, repo=None, do_upload=True):
    if not model.endswith(".glb"): raise SystemExit("publish takes a .glb (the site serves it as it is)")
    folder = os.path.join(pages, name); os.makedirs(folder, exist_ok=True)
    asset = sitepub.put_asset(model, f"{cfg['prefix']}-{name}", ".glb", tag, name, pages, repo, do_upload,
                              keep_dir=os.path.dirname(os.path.abspath(model)))
    shutil.copy2(compare, os.path.join(folder, "render-compare.jpg"))
    json.dump(viewer_json(cfg, asset), open(os.path.join(folder, "viewer.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(pages, name + ".html"), "w").write(render_page(cfg, name + "/", standalone=True))
    print(f"{name}.html, {name}/viewer.json, {name}/render-compare.jpg; {asset} "
          f"({'uploaded to ' + tag if do_upload else 'not uploaded'})")
    idx = os.path.join(pages, "index.html")
    if os.path.exists(idx):
        print(sitepub.index_message(sitepub.add_index_entry(idx, name, cfg.get("page_title") or name,
                                                            cfg.get("blurb", ""), cfg.get("issue", ""))))


def main(argv):
    if len(argv) < 5 or argv[0] not in ("stage", "publish"):
        print("usage: viewer_page.py stage <model> <compare.jpg> <page.json> <out> | publish <model.glb> <compare.jpg> "
              "<page.json> <pages> <name> --release TAG [--repo R] [--upload 0|1]"); return 2
    model, compare, cfg = argv[1], argv[2], json.load(open(argv[3]))
    for f in (model, compare):
        if not os.path.isfile(f): print(f"no {f}"); return 1
    if argv[0] == "stage":
        stage(model, compare, cfg, argv[4])
    else:
        opts = dict(zip(argv[6::2], argv[7::2]))
        if "--release" not in opts: print("publish needs --release TAG"); return 2
        publish(model, compare, cfg, argv[4], argv[5], opts["--release"], opts.get("--repo"), opts.get("--upload", "1") == "1")
    print("viewer-page: OK"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
