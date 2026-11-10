"""Tests for check_reuse_labels.py: every folder that ships its own LICENSE must be labelled by its own REUSE.toml
annotation with a matching licence, not fall through to the repo default (vt350#122). Plain python3 + git;
Main builds tiny git repos in temp dirs and removes them."""
import importlib.util, io, os, shutil, subprocess, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("crl", os.path.join(HERE, "check_reuse_labels.py"))
crl = importlib.util.module_from_spec(spec); spec.loader.exec_module(crl)

GPL = "                    GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n"
CC = "Attribution-NonCommercial-ShareAlike 4.0 International\n"
TOML = '''version = 1
[[annotations]]
path = "**"
SPDX-FileCopyrightText = "me"
SPDX-License-Identifier = "GPL-3.0-or-later"
[[annotations]]
path = "parts/a/**"
precedence = "override"
SPDX-FileCopyrightText = "them"
SPDX-License-Identifier = "GPL-3.0-only"
[[annotations]]
path = ["parts/b/**", "cad/b/**"]
precedence = "override"
SPDX-FileCopyrightText = "them"
SPDX-License-Identifier = "CC-BY-NC-SA-4.0"
'''


class Check(unittest.TestCase):
    def run_check(self, files, toml=TOML):
        return crl.check(crl.parse(toml), files)

    def test_labelled_folders_pass(self):
        files = {"parts/a/LICENSE": GPL, "parts/a/x.stl": None, "parts/b/LICENSE": CC, "cad/b/LICENSE": CC,
                 "LICENSE": GPL, "README.md": None}
        self.assertEqual(self.run_check(files), [])

    def test_folder_falling_through_to_the_default_fails(self):
        self.assertEqual(self.run_check({"parts/c/LICENSE": GPL, "parts/c/y.stl": None}),
                         ["parts/c/: has its own GPL-3.0 licence but falls through to the repo default "
                          "GPL-3.0-or-later in REUSE.toml; add an annotation for it"])

    def test_licence_family_mismatch_fails(self):
        self.assertEqual(self.run_check({"parts/a/LICENSE": CC}),
                         ["parts/a/: REUSE.toml labels it GPL-3.0-only, but its LICENSE is CC BY-NC-SA 4.0"])

    def test_unknown_licence_text_fails(self):
        self.assertEqual(self.run_check({"parts/a/LICENSE": "Some other licence\n"}),
                         ["parts/a/LICENSE: can't tell which licence this text is"])

    def test_gpl_v2_is_not_gpl_v3(self):
        v2 = "GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n"
        self.assertEqual(self.run_check({"parts/a/LICENSE": v2}), ["parts/a/LICENSE: can't tell which licence this text is"])
        self.assertEqual(self.run_check({"parts/a/LICENSE": "Version 3\n"}),
                         ["parts/a/LICENSE: can't tell which licence this text is"])

    def test_only_licence_files_are_read(self):
        self.assertEqual(self.run_check({"parts/c/README.md": CC, "parts/c/NOTICE": GPL}), [])

    def test_no_matching_annotation_fails(self):
        toml = 'version = 1\n[[annotations]]\npath = "parts/a/**"\nSPDX-FileCopyrightText = "t"\n' \
               'SPDX-License-Identifier = "GPL-3.0-only"\n'
        self.assertEqual(self.run_check({"parts/z/LICENSE": GPL}, toml), ["parts/z/LICENSE: no REUSE.toml annotation matches"])

    def test_header_exemption_is_a_folder_not_a_prefix(self):
        self.assertEqual(crl.check(crl.parse(TOML), {"tools/kk/COPYING": GPL}, header_labelled=("tools/k",)),
                         ["tools/kk/: has its own GPL-3.0 licence but falls through to the repo default "
                          "GPL-3.0-or-later in REUSE.toml; add an annotation for it"])
        self.assertEqual(crl.check(crl.parse(TOML), {"tools/k/sub/COPYING": GPL}, header_labelled=("tools/k",)), [])

    def test_root_licence_is_the_default_and_needs_no_override(self):
        self.assertEqual(self.run_check({"LICENSE": GPL}), [])

    def test_root_licence_must_match_the_default(self):
        self.assertEqual(self.run_check({"LICENSE": CC}),
                         ["./: REUSE.toml labels it GPL-3.0-or-later, but its LICENSE is CC BY-NC-SA 4.0"])

    def test_copying_counts_like_license(self):
        self.assertIn("parts/c", self.run_check({"parts/c/COPYING": GPL})[0])

    def test_header_labelled_folder_is_exempt_when_listed(self):
        # kalisim carries SPDX headers in its files instead of an annotation
        self.assertEqual(crl.check(crl.parse(TOML), {"tools/k/COPYING": GPL}, header_labelled=("tools/k",)), [])

    def test_last_matching_annotation_wins(self):
        toml = TOML + '[[annotations]]\npath = "parts/a/sub/**"\nprecedence = "override"\n' \
                      'SPDX-FileCopyrightText = "x"\nSPDX-License-Identifier = "CC-BY-NC-SA-4.0"\n'
        self.assertEqual(self.run_check({"parts/a/sub/LICENSE": CC}, toml), [])
        self.assertEqual(len(self.run_check({"parts/a/sub/LICENSE": GPL}, toml)), 1)

    def test_single_star_does_not_cross_folders(self):
        toml = TOML + '[[annotations]]\npath = "cad/*-x/**"\nprecedence = "override"\n' \
                      'SPDX-FileCopyrightText = "x"\nSPDX-License-Identifier = "GPL-3.0-only"\n'
        self.assertEqual(self.run_check({"cad/a-x/LICENSE": GPL}, toml), [])
        self.assertIn("repo default", self.run_check({"cad/a/b-x/LICENSE": GPL}, toml)[0])


class Main(unittest.TestCase):
    """main() on a tiny git repo: only tracked LICENSE/COPYING files count; the default exempts kalisim's headers."""

    def repo(self, files, git=True):
        d = tempfile.mkdtemp(prefix="reuse-labels-")
        self.addCleanup(shutil.rmtree, d, True)
        for rel, text in files.items():
            os.makedirs(os.path.join(d, os.path.dirname(rel)), exist_ok=True)
            with open(os.path.join(d, rel), "w", encoding="utf-8") as f:
                f.write(text)
        if git:
            subprocess.run(["git", "init", "-q", d], check=True)
            subprocess.run(["git", "-C", d, "add", "--", *[r for r in files if not r.startswith("untracked/")]],
                           check=True)
        return d

    def run_main(self, d):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = crl.main([d])
        return rc, out.getvalue().splitlines()

    def test_ok(self):
        d = self.repo({"REUSE.toml": TOML, "LICENSE": GPL, "parts/a/LICENSE": GPL,
                       "cad/klipper/kalisim/COPYING": GPL, "untracked/LICENSE": CC})
        self.assertEqual(self.run_main(d), (0, ["check-reuse-labels: OK"]))

    def test_failure_lists_each_error_and_counts_them(self):
        d = self.repo({"REUSE.toml": TOML, "parts/a/LICENSE": CC, "parts/c/COPYING": GPL})
        self.assertEqual(self.run_main(d), (1, [
            "parts/a/: REUSE.toml labels it GPL-3.0-only, but its LICENSE is CC BY-NC-SA 4.0",
            "parts/c/: has its own GPL-3.0 licence but falls through to the repo default GPL-3.0-or-later in "
            "REUSE.toml; add an annotation for it",
            "check-reuse-labels: FAILED (2)"]))


    def test_without_git_every_file_counts(self):
        # act runs the workflow on a copy of the checkout with no .git
        d = self.repo({"REUSE.toml": TOML, "parts/a/LICENSE": GPL, "untracked/LICENSE": CC, ".git/x/LICENSE": CC},
                      git=False)
        self.assertEqual(self.run_main(d), (1, [
            "untracked/: has its own CC BY-NC-SA 4.0 licence but falls through to the repo default GPL-3.0-or-later "
            "in REUSE.toml; add an annotation for it", "check-reuse-labels: FAILED (1)"]))


class Script(Main):
    def test_exit_code_and_output_when_run_as_a_script(self):
        script = os.path.join(HERE, "check_reuse_labels.py")
        for files, rc, last in (({"REUSE.toml": TOML, "parts/a/LICENSE": GPL}, 0, "check-reuse-labels: OK"),
                                ({"REUSE.toml": TOML, "parts/c/LICENSE": GPL}, 1, "check-reuse-labels: FAILED (1)")):
            p = subprocess.run(["python3", script, self.repo(files)], capture_output=True, text=True)
            self.assertEqual((p.returncode, p.stdout.splitlines()[-1]), (rc, last))


class ThisRepo(unittest.TestCase):
    def test_this_repository_passes(self):
        self.assertEqual(crl.main([]), 0)   # the default root: this checkout, as CI runs it


if __name__ == "__main__":
    unittest.main(verbosity=1)
