#!/usr/bin/env python3
"""Tests for where cad/scripts/derive_stls.py reads its models from (homelab#1961).

derive_stls.py needs FreeCAD, so these run the REAL script under stub FreeCAD/Part/Mesh/MeshPart/numpy/reglib
modules. The stub openDocument raises with the path it was asked for, and the script logs that traceback.

Run: python3 cad/scripts/test_derive_stls.py
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "derive_stls.py")

STUBS = {
    "FreeCAD.py": """
        Vector = object
        def openDocument(path):
            raise RuntimeError("OPENED " + path)
    """,
    "Part.py": "",
    "Mesh.py": "",
    "MeshPart.py": "",
    "numpy.py": "",
    "reglib.py": "mesh_inertia = shape_inertia = mat = moved = dists = register = None\n",
}


class ModelsDir(unittest.TestCase):
    def run_script(self, env_extra):
        with tempfile.TemporaryDirectory() as tmp:
            stubs = os.path.join(tmp, "stubs")
            os.makedirs(stubs)
            for name, body in STUBS.items():
                with open(os.path.join(stubs, name), "w") as f:
                    f.write(textwrap.dedent(body))
            repo = os.path.join(tmp, "repo")
            os.makedirs(os.path.join(repo, "cad", "data", "logs"))
            env = dict(os.environ, PYTHONPATH=stubs, VT350_REPO=repo, **env_extra)
            env.pop("VT350_MODELS", None) if "VT350_MODELS" not in env_extra else None
            env.pop("VT350_ONLY", None)
            subprocess.run([sys.executable, SCRIPT], env=env, check=False, timeout=60)
            with open(os.path.join(repo, "cad", "data", "logs", "derive_stls.log")) as f:
                return f.read()

    def test_models_dir_from_env(self):
        log = self.run_script({"VT350_MODELS": "/work/job-x/in/models"})
        self.assertIn("OPENED /work/job-x/in/models/vt350-lite-22.FCStd", log)

    def test_default_is_the_laptop_models_dir(self):
        log = self.run_script({})
        self.assertIn("OPENED /home/dan/Documents/VT350/vt350-lite-22.FCStd", log)


if __name__ == "__main__":
    unittest.main()
