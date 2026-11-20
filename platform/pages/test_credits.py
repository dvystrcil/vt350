# Tests for credits.py: CREDITS.md from REUSE.toml, the licence rules and the projects file (vt350#220).
#   python3 platform/pages/test_credits.py      # "Ran N tests" + "OK"
import io, json, os, shutil, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import credits


def projects(*extra):
    return {"title": "Credits", "intro": ["Intro."], "own_holders": ["2026 Me"],
            "licence_urls": {"LicenseRef-x": "https://x.example/terms"},
            "projects": [{"key": "up", "name": "Upstream", "by": "Up Author", "links": [["up", "https://up.example"]],
                          "used": "the frame", "reuse": ["Up Author"]},
                         {"key": "pg", "name": "Page part", "by": "Pg", "links": [["pg", "https://pg.example"]],
                          "used": "a model"}] + list(extra)}


REUSE = {"annotations": [
    {"path": "**", "SPDX-FileCopyrightText": "2026 Me", "SPDX-License-Identifier": "GPL-3.0-or-later"},
    {"path": "parts/up/**", "SPDX-FileCopyrightText": "Up Author", "SPDX-License-Identifier": "GPL-3.0-only"},
    {"path": ["remix-*/**"], "SPDX-FileCopyrightText": ["Up Author", "2026 Me"], "SPDX-License-Identifier": "GPL-3.0-only"}]}
RULES = {"rules": [{"label": "a", "licence": "GPL-3.0-only", "credit": "up", "source": "s"},
                   {"label": "b", "licence": "MIT", "credit": "pg", "source": "s"},
                   {"label": "c", "licence": "GPL-3.0-or-later", "credit": "own", "source": "s"}]}


class Build(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        os.mkdir(os.path.join(self.d, "LICENSES"))
        for lic in ("GPL-3.0-only", "GPL-3.0-or-later"):
            open(os.path.join(self.d, "LICENSES", lic + ".txt"), "w").close()

    def build(self, p=None, reuse=REUSE, rules=RULES):
        return credits.build(p or projects(), reuse, rules, os.path.join(self.d, "LICENSES"), self.d)

    def test_one_row_per_project_with_its_licences_and_where(self):
        text, probs = self.build()
        self.assertEqual(probs, [])
        rows = [l for l in text.splitlines() if l.startswith("| [")]
        self.assertEqual(len(rows), 2)
        self.assertIn("[Upstream](https://up.example)", rows[0])
        self.assertIn("[GPL-3.0-only](LICENSES/GPL-3.0-only.txt)", rows[0])
        self.assertIn("[`parts/up/`](parts/up/)", rows[0])
        self.assertIn("`remix-*/`", rows[0])
        self.assertIn("pages", rows[0])
        self.assertIn("[MIT](https://spdx.org/licenses/MIT.html)", rows[1])     # no text in LICENSES/: spdx.org
        self.assertNotIn("2026 Me", text)                                         # own work isn't a row

    def test_a_rule_without_credit_fails(self):
        rules = {"rules": RULES["rules"] + [{"label": "d", "licence": "MIT", "source": "s"}]}
        self.assertTrue(any("no 'credit'" in p for p in self.build(rules=rules)[1]))

    def test_an_unknown_credit_fails(self):
        rules = {"rules": RULES["rules"] + [{"label": "d", "licence": "MIT", "credit": "nobody", "source": "s"}]}
        self.assertTrue(any("'nobody'" in p for p in self.build(rules=rules)[1]))

    def test_a_reuse_holder_without_project_fails(self):
        reuse = {"annotations": REUSE["annotations"] + [
            {"path": "x/**", "SPDX-FileCopyrightText": "Stranger", "SPDX-License-Identifier": "CC0-1.0"}]}
        self.assertTrue(any("'Stranger'" in p for p in self.build(reuse=reuse)[1]))

    def test_an_unused_project_fails(self):
        p = projects({"key": "gone", "name": "Gone", "by": "G", "links": [["g", "https://g.example"]], "used": "-"})
        self.assertTrue(any("'gone'" in q for q in self.build(p)[1]))

    def test_a_licenceref_needs_a_url(self):
        rules = {"rules": RULES["rules"] + [{"label": "e", "licence": "LicenseRef-y", "credit": "pg", "source": "s"},
                                            {"label": "f", "licence": "LicenseRef-x", "credit": "pg", "source": "s"}]}
        text, probs = self.build(rules=rules)
        self.assertEqual([p for p in probs if "LicenseRef" in p], [p for p in probs if "LicenseRef-y" in p])
        self.assertTrue(probs)
        self.assertIn("(https://x.example/terms)", text)

    def test_check_finds_a_stale_file(self):
        paths = {}
        for n, data in (("p.json", projects()), ("l.json", RULES)):
            paths[n] = os.path.join(self.d, n); json.dump(data, open(paths[n], "w"))
        toml = os.path.join(self.d, "REUSE.toml")
        open(toml, "w").write('version = 1\n[[annotations]]\npath = "parts/up/**"\n'
                              'SPDX-FileCopyrightText = "Up Author"\nSPDX-License-Identifier = "GPL-3.0-only"\n')
        out = os.path.join(self.d, "CREDITS.md")
        args = ["--projects", paths["p.json"], "--reuse", toml, "--licences", paths["l.json"],
                "--licence-dir", os.path.join(self.d, "LICENSES"), "--out", out]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(credits.main(args + ["--check"]), 1)     # missing
            self.assertEqual(credits.main(args), 0)
            self.assertEqual(credits.main(args + ["--check"]), 0)
            open(out, "a").write("hand edit\n")
            self.assertEqual(credits.main(args + ["--check"]), 1)


class Repo(unittest.TestCase):
    def test_the_repos_credits_are_current(self):
        args = ["--projects", f"{ROOT}/cad/credits.json", "--reuse", f"{ROOT}/REUSE.toml",
                "--licences", f"{ROOT}/cad/viewer/licences.json", "--licence-dir", f"{ROOT}/LICENSES",
                "--out", f"{ROOT}/CREDITS.md", "--check"]
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = credits.main(args)
        self.assertEqual(rc, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
