#!/usr/bin/env python3
"""PR check: every temp dir or file a tool makes must be cleaned up, or marked as kept on purpose.

Real runs of clashlib, litepool, sweep_toolhead and export_pose left their work dirs in /tmp on every run, and with
the tests' leaks they filled the laptop's /tmp (a tmpfs, 1M inodes). check_test_tmp.sh runs the tests with an empty
TMPDIR; this checks the tools, most of which need FreeCAD and can't run in CI, by reading their code.

  python3 cad/scripts/check_tool_tmp.py      # every tracked .py/.sh except test_*.py; "check-tool-tmp: OK (N files)"

Python: each tempfile.mkdtemp(), mkstemp() or NamedTemporaryFile(delete=False) call needs, in the same function (or
the module, at top level), a cleanup: shutil.rmtree, weakref.finalize, os.remove, os.unlink or .unlink(). Shell: each
mktemp needs a trap in the same file that runs rm. TemporaryDirectory() and a deleting NamedTemporaryFile clean up by
themselves. Either way, a `tmp-kept: <reason>` comment on the call's line or the line above allows it: use that for an
output dir whose path is handed to the user.
"""
import ast, re, subprocess, sys
from typing import NamedTuple

LEAKY = {"mkdtemp", "mkstemp"}
CLEANUP = {"rmtree", "finalize", "remove", "unlink"}
MARKER = re.compile(r"#\s*tmp-kept:\s*\S")


class Finding(NamedTuple):
    path: str
    line: int
    code: str


def _marked(lines, n):
    """A tmp-kept marker (with a reason) on line n (1-based) or the line above."""
    return any(MARKER.search(lines[i - 1]) for i in (n, n - 1) if 1 <= i <= len(lines))


def _name(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _leaky(call):
    n = _name(call)
    if n in LEAKY: return True
    if n == "NamedTemporaryFile":
        return any(k.arg == "delete" and isinstance(k.value, ast.Constant) and k.value.value is False for k in call.keywords)
    return False


def _scopes(tree):
    """[(scope, [calls directly in it])]: each function's own calls (not its nested functions'), and the module's."""
    out = []
    def collect(node, calls):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                out.append((ch, collect(ch, [])))
            else:
                if isinstance(ch, ast.Call): calls.append(ch)
                collect(ch, calls)
        return calls
    out.append((tree, collect(tree, [])))
    return out


def check_python(path, src):
    lines = src.splitlines()
    tree = ast.parse(src, path)
    found = []
    for scope, calls in _scopes(tree):
        cleans = any(_name(c) in CLEANUP for c in calls)
        for c in calls:
            if _leaky(c) and not cleans and not _marked(lines, c.lineno):
                found.append(Finding(path, c.lineno, lines[c.lineno - 1].strip()))
    return sorted(found, key=lambda f: f.line)


def check_shell(path, src):
    lines = src.splitlines()
    trapped = any(re.search(r"^\s*[^#]*\btrap\b.*\brm\b", l) for l in lines)
    found = []
    for n, l in enumerate(lines, 1):
        code = l.split("#", 1)[0] if not l.lstrip().startswith("#") else ""
        if re.search(r"\bmktemp\b", code) and not trapped and not _marked(lines, n):
            found.append(Finding(path, n, l.strip()))
    return found


def main():
    files = subprocess.run(["git", "ls-files", "*.py", "*.sh"], capture_output=True, text=True, check=True).stdout.split()
    files = [f for f in files if not f.rsplit("/", 1)[-1].startswith("test_")]
    found = []
    for f in files:
        src = open(f, encoding="utf-8", errors="replace").read()
        try:
            found += check_python(f, src) if f.endswith(".py") else check_shell(f, src)
        except SyntaxError as e:
            print(f"SKIP   {f}: not parseable as Python 3 ({e.msg}, line {e.lineno})")
    for x in found:
        print(f"LEAK   {x.path}:{x.line}  {x.code}")
    if found:
        print(f"check-tool-tmp: FAILED ({len(found)} temp dir/file(s) never removed; clean up, or mark `# tmp-kept: <reason>`)")
        return 1
    print(f"check-tool-tmp: OK ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
