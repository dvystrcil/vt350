# Tests for check_tool_tmp.py: the PR check that every temp dir/file a tool makes is cleaned up (or marked kept).
#   python3 cad/scripts/test_check_tool_tmp.py      # "Ran N tests" + "OK"
import os, shutil, subprocess, sys, tempfile, textwrap, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_tool_tmp as c


def py(src):
    return c.check_python("t.py", textwrap.dedent(src))


class Python(unittest.TestCase):
    def test_a_mkdtemp_nobody_removes_is_a_leak(self):
        self.assertEqual([f.line for f in py("""\
            import tempfile
            def f():
                d = tempfile.mkdtemp()
                return d
            """)], [3])

    def test_rmtree_in_the_same_function_is_cleanup(self):
        self.assertEqual(py("""\
            import shutil, tempfile
            def f():
                d = tempfile.mkdtemp()
                try: pass
                finally: shutil.rmtree(d)
            """), [])

    def test_rmtree_in_another_function_does_not_count(self):
        self.assertEqual(len(py("""\
            import shutil, tempfile
            def f():
                return tempfile.mkdtemp()
            def g(d):
                shutil.rmtree(d)
            """)), 1)

    def test_a_weakref_finalize_is_cleanup(self):
        self.assertEqual(py("""\
            import tempfile, weakref
            class P:
                def __init__(self):
                    self.dir = tempfile.mkdtemp()
                    self._f = weakref.finalize(self, print, self.dir)
            """), [])

    def test_mkstemp_needs_a_remove(self):
        self.assertEqual(len(py("import tempfile\nfd, p = tempfile.mkstemp()\n")), 1)
        self.assertEqual(py("import os, tempfile\ndef f():\n    fd, p = tempfile.mkstemp()\n    os.remove(p)\n"), [])

    def test_named_temporary_file_only_leaks_with_delete_false(self):
        self.assertEqual(py("import tempfile\nwith tempfile.NamedTemporaryFile() as f: pass\n"), [])
        self.assertEqual(len(py("import tempfile\nf = tempfile.NamedTemporaryFile(delete=False)\n")), 1)
        self.assertEqual(py("import tempfile\nf = tempfile.NamedTemporaryFile(delete=True)\n"), [])

    def test_temporary_directory_is_always_fine(self):
        self.assertEqual(py("import tempfile\nwith tempfile.TemporaryDirectory() as d: pass\n"), [])

    def test_a_tmp_kept_marker_on_the_line_or_the_line_above_allows_it(self):
        self.assertEqual(py("import tempfile\nd = tempfile.mkdtemp()   # tmp-kept: the output, printed\n"), [])
        self.assertEqual(py("import tempfile\n# tmp-kept: the output, printed\nd = tempfile.mkdtemp()\n"), [])

    def test_a_marker_needs_a_reason(self):
        self.assertEqual(len(py("import tempfile\nd = tempfile.mkdtemp()   # tmp-kept:\n")), 1)

    def test_a_bare_name_import_is_caught_too(self):
        self.assertEqual(len(py("from tempfile import mkdtemp\ndef f():\n    return mkdtemp()\n")), 1)


class Shell(unittest.TestCase):
    def sh(self, src):
        return c.check_shell("t.sh", textwrap.dedent(src))

    def test_mktemp_without_a_trap_is_a_leak(self):
        self.assertEqual([f.line for f in self.sh('#!/bin/bash\nT=$(mktemp -d)\necho hi\n')], [2])

    def test_an_exit_trap_that_removes_is_cleanup(self):
        self.assertEqual(self.sh('#!/bin/bash\nT=$(mktemp -d); trap \'rm -rf "$T"\' EXIT\n'), [])

    def test_a_trap_that_removes_nothing_is_not_cleanup(self):
        self.assertEqual(len(self.sh('#!/bin/bash\nT=$(mktemp)\ntrap \'echo bye\' EXIT\n')), 1)

    def test_a_commented_out_trap_is_not_cleanup(self):
        self.assertEqual(len(self.sh('#!/bin/bash\nT=$(mktemp)\n# trap \'rm -f "$T"\' EXIT\n')), 1)

    def test_a_comment_mentioning_mktemp_is_not_a_call(self):
        self.assertEqual(self.sh('#!/bin/bash\n# we used to mktemp here\n'), [])

    def test_a_marker_allows_it(self):
        self.assertEqual(self.sh('#!/bin/bash\nT=$(mktemp)   # tmp-kept: handed to the caller\n'), [])


class Repo(unittest.TestCase):
    def test_the_cli_fails_on_a_leak_and_passes_when_clean(self):
        d = tempfile.mkdtemp(prefix="check-tool-tmp-test-")
        self.addCleanup(shutil.rmtree, d, True)
        git = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, check=True)
        git("init", "-q")
        open(os.path.join(d, "tool.py"), "w").write("import tempfile\ndef f():\n    return tempfile.mkdtemp()\n")
        open(os.path.join(d, "test_tool.py"), "w").write("import tempfile\nx = tempfile.mkdtemp()\n")   # tests: not this check's job
        git("add", ".")
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_tool_tmp.py")], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LEAK   tool.py:3", r.stdout)
        self.assertNotIn("test_tool.py", r.stdout)
        open(os.path.join(d, "tool.py"), "w").write("import tempfile\nwith tempfile.TemporaryDirectory() as t: pass\n")
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_tool_tmp.py")], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "check-tool-tmp: OK (1 files)")

    def test_this_repo_is_clean(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_tool_tmp.py")], cwd=HERE, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
