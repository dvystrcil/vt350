# Tests for batchvalues.py: where a platform script's setting comes from (env var, then the values file named by
# GPU_BATCH_VALUES, then today's built-in value). Plain python3, no FreeCAD, so they run in CI:
#   python3 platform/freecad/test_batchvalues.py      # "Ran N tests" + "OK"
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batchvalues

DEFAULT = "/home/dan/FreeCAD/FreeCAD_26.3rc2-Linux-x86_64.AppImage"


def appimage(environ):
    return batchvalues.setting("freecad_appimage", env="FREECAD_APPIMAGE", default=DEFAULT, environ=environ)


class Setting(unittest.TestCase):
    def test_no_values_file_and_no_env_gives_todays_value(self):
        self.assertEqual(appimage({}), DEFAULT)

    def test_env_var_still_overrides_the_default(self):
        self.assertEqual(appimage({"FREECAD_APPIMAGE": "/opt/freecad/AppRun"}), "/opt/freecad/AppRun")

    def test_values_file_platform_section_replaces_the_default(self):
        path = self.values({"platform": {"freecad_appimage": "/srv/FreeCAD.AppImage"}})
        self.assertEqual(appimage({"GPU_BATCH_VALUES": path}), "/srv/FreeCAD.AppImage")

    def test_env_var_beats_the_values_file(self):
        path = self.values({"platform": {"freecad_appimage": "/srv/FreeCAD.AppImage"}})
        self.assertEqual(appimage({"GPU_BATCH_VALUES": path, "FREECAD_APPIMAGE": "/opt/freecad/AppRun"}),
                         "/opt/freecad/AppRun")

    def test_guard_only_values_file_keeps_todays_value(self):
        # the homelab's own gpu-batch-docker values.json has only the print_guard section
        path = self.values({"print_guard": {"moonraker_url": None, "fallback": "none"}})
        self.assertEqual(appimage({"GPU_BATCH_VALUES": path}), DEFAULT)

    def test_unknown_platform_key_is_refused_naming_the_file(self):
        path = self.values({"platform": {"freecad_appimge": "/srv/FreeCAD.AppImage"}})
        with self.assertRaisesRegex(batchvalues.ValuesError, f"{path}.*freecad_appimge"):
            appimage({"GPU_BATCH_VALUES": path})

    def test_missing_values_file_is_an_error_not_no_file(self):
        path = os.path.join(tempfile.gettempdir(), "batchvalues-test-no-such-file.json")
        with self.assertRaisesRegex(batchvalues.ValuesError, path):
            appimage({"GPU_BATCH_VALUES": path})

    def test_values_file_that_is_not_json_is_an_error(self):
        path = self.values("platform: {freecad_appimage: /srv/x}")
        with self.assertRaisesRegex(batchvalues.ValuesError, path):
            appimage({"GPU_BATCH_VALUES": path})

    def values(self, doc):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(doc, f) if not isinstance(doc, str) else f.write(doc)
        self.addCleanup(os.remove, path)
        return path


if __name__ == "__main__":
    unittest.main(verbosity=2)
