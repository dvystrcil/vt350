# SPDX-License-Identifier: GPL-3.0-or-later
"""crawl.py without docker: the sites file checks, the crawler arguments and the text extraction."""
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
