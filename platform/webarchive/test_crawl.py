# SPDX-License-Identifier: GPL-3.0-or-later
"""crawl.py without docker: the sites file checks, the crawler arguments and the text extraction."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

import crawl


class Sites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = Path(self.tmp.name) / "sites.json"

    def load(self, sites):
        self.f.write_text(json.dumps({"sites": sites}))
        return crawl.load_sites(self.f)

    def test_good(self):
        s = self.load([{"name": "docs-1", "url": "https://example.com/", "scope": "host"}])
        self.assertEqual(s[0]["name"], "docs-1")

    def test_rejects(self):
        for bad in ([{"name": "Bad Name", "url": "https://x/"}],
                    [{"name": "a", "url": "ftp://x/"}],
                    [{"name": "a", "url": "https://x/", "scope": "everything"}],
                    [{"name": "a", "url": "https://x/"}, {"name": "a", "url": "https://y/"}]):
            with self.assertRaises(ValueError):
                self.load(bad)

    def test_args(self):
        a = crawl.crawl_args({"name": "d", "url": "https://x/", "page_limit": 7, "exclude": ["\\?p=", "/cart"]})
        self.assertEqual(a[a.index("--scopeType") + 1], "prefix")
        self.assertEqual(a[a.index("--pageLimit") + 1], "7")
        self.assertEqual([a[i + 1] for i, v in enumerate(a) if v == "--exclude"], ["\\?p=", "/cart"])
        self.assertIn("--overwrite", a)
        self.assertNotIn("--extraHops", a)

    def test_urls(self):
        s = self.load([{"name": "m", "urls": ["https://x/a", "https://x/b"], "scope": "page", "extra_hops": 1}])
        a = crawl.crawl_args(s[0])
        self.assertEqual([a[i + 1] for i, v in enumerate(a) if v == "--url"], ["https://x/a", "https://x/b"])
        self.assertEqual(a[a.index("--extraHops") + 1], "1")
        for bad in ([{"name": "m", "url": "https://x/", "urls": ["https://x/"]}],
                    [{"name": "m"}],
                    [{"name": "m", "urls": ["https://x/", "x.com"]}]):
            with self.assertRaises(ValueError):
                self.load(bad)


class Text(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / "pages").mkdir()
        lines = [{"format": "json-pages-1.0", "id": "pages"},
                 {"url": "https://x.com/a", "title": "A", "text": "short"},
                 {"url": "https://x.com/a/", "title": "A", "text": "the longer one"},
                 {"url": "https://x.com/b/#top", "title": "B", "text": "bee"},
                 {"url": "https://x.com/pdf", "title": "no text"}]
        (self.d / "pages" / "pages.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")

    def test_dedupes_and_writes(self):
        pages = crawl.read_pages(self.d / "pages")
        self.assertEqual([p["text"] for p in pages], ["the longer one", "bee"])
        n = crawl.write_text(pages, self.d / "text")
        self.assertEqual(n, 2)
        self.assertEqual(sorted(p.name for p in (self.d / "text").iterdir()), ["INDEX.md", "x-com-a.md", "x-com-b.md"])
        self.assertIn("Source: https://x.com/a/", (self.d / "text" / "x-com-a.md").read_text())

    def test_slug(self):
        self.assertEqual(crawl.slug("https://docs.x.com/"), "docs-x-com")
        self.assertEqual(crawl.slug("https://x.com/A_b/c?d=1"), "x-com-a-b-c-d-1")


def warc_record(page_id, url, ctype, body, chunked=False):
    """One gzipped WARC response record, laid out the way browsertrix writes them."""
    if chunked:
        body = b"%x\r\n" % len(body) + body + b"\r\n0\r\n\r\n"
    http = (b"HTTP/1.1 200 OK\r\ncontent-type: " + ctype.encode() +
            (b"\r\ntransfer-encoding: chunked" if chunked else b"") + b"\r\n\r\n" + body)
    head = (f"WARC/1.1\r\nWARC-Page-ID: {page_id}\r\nWARC-Target-URI: {url}\r\nWARC-Type: response\r\n"
            f"Content-Type: application/http; msgtype=response\r\nContent-Length: {len(http)}\r\n\r\n").encode()
    return gzip.compress(head + http + b"\r\n\r\n")


class Images(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / "archive").mkdir()
        big, png = b"\x89PNG" + b"x" * 5000, b"\x89PNG" + b"y" * 3000
        warcinfo = gzip.compress(b"WARC/1.1\r\nWARC-Type: warcinfo\r\nContent-Length: 4\r\n\r\nabcd\r\n\r\n")
        (self.d / "archive" / "rec-0.warc.gz").write_bytes(
            warcinfo
            + warc_record("p1", "https://x.com/a/", "text/html", b"<html>" + b"h" * 3000)
            + warc_record("p1", "https://x.com/img/mount-2.jpg?v=3", "image/jpeg", big)
            + warc_record("p1", "https://x.com/img/mount-2.jpg?v=3", "image/jpeg", big)  # loaded twice: kept once
            + warc_record("p1", "https://x.com/favicon.png", "image/png", b"\x89PNG tiny")  # under MIN_IMAGE_BYTES
            + warc_record("p2", "https://x.com/img/b.png", "image/png; charset=binary", png, chunked=True))
        self.big, self.png = big, png

    def test_read_images(self):
        imgs = crawl.read_images(self.d / "archive")
        self.assertEqual(sorted(imgs), ["p1", "p2"])
        self.assertEqual([(u, len(b)) for u, _, b in imgs["p1"]], [("https://x.com/img/mount-2.jpg?v=3", 5004)])
        self.assertEqual(imgs["p2"][0][2], self.png)  # chunked body joined back together

    def test_listed_in_page(self):
        pages = [{"url": "https://x.com/a/", "title": "A", "text": "t", "ids": ["p1", "p2"]}]
        crawl.write_text(pages, self.d / "text", crawl.read_images(self.d / "archive"))
        md = (self.d / "text" / "x-com-a.md").read_text()
        self.assertIn("## Images (2)", md)
        saved = sorted((self.d / "text" / "images" / "x-com-a").iterdir())
        self.assertEqual([p.suffix for p in saved], [".png", ".jpg"])
        self.assertTrue(saved[1].name.startswith("mount-2-"))
        self.assertEqual(saved[1].read_bytes(), self.big)
        self.assertLess(md.index("mount-2-"), md.index("/b-"))  # largest first

    def test_no_images_no_section(self):
        crawl.write_text([{"url": "https://x.com/c", "title": "C", "text": "t", "id": "p9"}], self.d / "text", {})
        self.assertNotIn("## Images", (self.d / "text" / "x-com-c.md").read_text())


class OutsideGit(unittest.TestCase):
    def test_refuses_out_in_a_checkout(self):
        here = Path(__file__).resolve().parent
        if not crawl.git_root(here):
            self.skipTest("not in a git checkout")
        with tempfile.TemporaryDirectory() as t:
            sites = Path(t) / "sites.json"
            sites.write_text(json.dumps({"sites": [{"name": "a", "url": "https://x/"}]}))
            with self.assertRaises(SystemExit) as cm:
                crawl.main([str(sites), "--out", str(here / "not-made-yet" / "web")])
            self.assertIn("outside git", str(cm.exception))
            self.assertFalse((here / "not-made-yet").exists())

    def test_allows_out_outside(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(crawl.git_root(Path(t) / "web"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
