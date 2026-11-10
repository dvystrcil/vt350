# Tests for check_index.py: the guard the pages workflow runs before publishing notes/reference/.
#   python3 .github/scripts/test_check_index.py      # "Ran N tests" + "OK"
import os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_index

GOOD_HEAD = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>{}</title>\n</head>\n'


def page(title, body=""):
    return GOOD_HEAD.format(title) + "<body>" + body + "</body>\n</html>\n"


class Check(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def write(self, name, text):
        with open(os.path.join(self.d, name), "w", encoding="utf-8") as f: f.write(text)

    def test_an_index_linking_every_page_passes(self):
        self.write("a.html", page("A")); self.write("b.html", page("B"))
        self.write("index.html", page("Index", '<a href="a.html">A</a> <a href="b.html">B</a>'))
        self.assertEqual(check_index.problems(self.d), [])

    def test_a_missing_index_is_a_problem(self):
        self.write("a.html", page("A"))
        self.assertEqual(check_index.problems(self.d), ["no index.html"])

    def test_a_page_the_index_does_not_link_is_a_problem(self):
        self.write("a.html", page("A")); self.write("b.html", page("B"))
        self.write("index.html", page("Index", '<a href="a.html">A</a>'))
        self.assertEqual(check_index.problems(self.d), ["index.html does not link b.html"])

    def test_a_link_to_a_page_that_does_not_exist_is_a_problem(self):
        self.write("index.html", page("Index", '<a href="gone.html">Gone</a>'))
        self.assertEqual(check_index.problems(self.d), ["index.html links gone.html, which does not exist"])

    def test_links_to_other_sites_and_anchors_are_not_pages(self):
        self.write("index.html", page("Index", '<a href="https://example.com/x.html">x</a> <a href="#top">t</a>'))
        self.assertEqual(check_index.problems(self.d), [])

    def test_single_quoted_and_upper_case_hrefs_count_as_links(self):
        self.write("a.html", page("A")); self.write("index.html", page("Index", "<A HREF='a.html'>A</A>"))
        self.assertEqual(check_index.problems(self.d), [])

    def test_a_page_without_a_charset_is_a_problem(self):
        # opened straight from a clone, a page without one can show the degree sign as garbage
        self.write("a.html", "<!doctype html><html><head><title>A</title></head><body></body></html>")
        self.write("index.html", page("Index", '<a href="a.html">A</a>'))
        self.assertEqual(check_index.problems(self.d), ["a.html has no <meta charset=\"utf-8\">"])

    def test_a_page_without_a_title_or_doctype_is_a_problem(self):
        self.write("a.html", '<meta charset="utf-8"><p>hi</p>')
        self.write("index.html", page("Index", '<a href="a.html">A</a>'))
        self.assertEqual(check_index.problems(self.d), ["a.html has no <!doctype html>", "a.html has no <title>"])

    def test_the_index_is_held_to_the_same_rules(self):
        self.write("index.html", "<p>no head</p>")
        self.assertEqual(check_index.problems(self.d),
                         ["index.html has no <!doctype html>", "index.html has no <meta charset=\"utf-8\">",
                          "index.html has no <title>"])

    def test_files_in_subfolders_are_not_pages(self):
        os.mkdir(os.path.join(self.d, "img")); self.write(os.path.join("img", "x.html"), "junk")
        self.write("index.html", page("Index"))
        self.assertEqual(check_index.problems(self.d), [])

    def test_the_command_prints_ok_and_exits_0_when_clean(self):
        self.write("index.html", page("Index"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_index.py"), self.d], capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip().splitlines()[-1]), (0, "check-index: OK"))

    def test_the_command_lists_problems_and_exits_1(self):
        self.write("a.html", page("A")); self.write("index.html", page("Index"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_index.py"), self.d], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("index.html does not link a.html", r.stdout)
        self.assertNotIn("check-index: OK", r.stdout)

    def test_the_real_folder_passes(self):
        real = os.path.join(HERE, "..", "..", "notes", "reference")
        self.assertEqual(check_index.problems(real), [])


if __name__ == "__main__":
    unittest.main()
