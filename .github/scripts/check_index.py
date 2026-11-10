# The pages workflow's guard: notes/reference/ must have an index.html that links every page and links nothing that
# isn't there, and every page must stand alone (doctype, utf-8 charset, title), so it renders the same opened from a
# clone as on GitHub Pages.
#   python3 .github/scripts/check_index.py [dir]      # default notes/reference; last line "check-index: OK"
import os, re, sys

_HREF = re.compile(r"""href\s*=\s*["']([^"'#?]+)["']""", re.I)
_RULES = (("<!doctype html>", re.compile(r"<!doctype\s+html\s*>", re.I)),
          ('<meta charset="utf-8">', re.compile(r"""<meta\s+charset\s*=\s*["']?utf-8["']?\s*/?>""", re.I)),
          ("<title>", re.compile(r"<title>[^<]*\S[^<]*</title>", re.I)))


def problems(d):
    pages = sorted(f for f in os.listdir(d) if f.endswith(".html") and os.path.isfile(os.path.join(d, f)))
    if "index.html" not in pages: return ["no index.html"]
    out = []
    for name in ["index.html"] + [p for p in pages if p != "index.html"]:
        text = open(os.path.join(d, name), encoding="utf-8").read()
        out += [f"{name} has no {what}" for what, rx in _RULES if not rx.search(text)]
    index = open(os.path.join(d, "index.html"), encoding="utf-8").read()
    links = {h for h in _HREF.findall(index) if h.endswith(".html") and "://" not in h}
    out += [f"index.html does not link {p}" for p in pages if p != "index.html" and p not in links]
    out += [f"index.html links {h}, which does not exist" for h in sorted(links) if h not in pages]
    return out


def main(argv):
    d = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "notes", "reference")
    found = problems(d)
    for p in found: print(p)
    if found: return 1
    print("check-index: OK"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
