"""Tests for dupes.py's plain-python side (vt350#195): what each object costs in an .FCStd, read from the zip and
Document.xml. Plain python3, no FreeCAD:  python3 platform/freecad/test_dupes.py
The FreeCAD side (grouping, fitting, linking) is test_dupes_fc.py, run under freecadcmd."""
import os, sys, tempfile, unittest, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dupes  # noqa: E402

DOC = """<?xml version='1.0' encoding='utf-8'?>
<Document SchemaVersion="4">
    <Objects Count="3">
        <Object type="Part::Feature" name="Board" id="1"/>
        <Object type="Mesh::Feature" name="MeshStandIn" id="2"/>
        <Object type="App::Part" name="Head" id="3"/>
    </Objects>
    <ObjectData Count="3">
        <Object name="Board">
            <Properties Count="1">
                <Property name="Shape" type="Part::PropertyPartShape">
                    <Part ElementMap="1" file="Board.Shape.brp"/>
                </Property>
            </Properties>
        </Object>
        <Object name="MeshStandIn">
            <Properties Count="1">
                <Property name="Mesh" type="Mesh::PropertyMeshKernel">
                    <Mesh file="MeshKernel3.bms"/>
                </Property>
            </Properties>
        </Object>
        <Object name="Head">
            <Properties Count="0"/>
        </Object>
    </ObjectData>
</Document>
"""


class ObjectBytes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="dupes_test_")
        cls.path = os.path.join(cls.tmp, "m.FCStd")
        with zipfile.ZipFile(cls.path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("Document.xml", DOC)
            z.writestr("Board.Shape.brp", "x" * 50000)           # compresses to almost nothing
            z.writestr("MeshKernel3.bms", os.urandom(20000))     # doesn't compress
            z.writestr("GuiDocument.xml", "<x/>")
        with zipfile.ZipFile(cls.path) as z:
            cls.csize = {i.filename: i.compress_size for i in z.infolist()}

    def test_each_object_costs_its_files_compressed_size(self):
        b = dupes.object_bytes(self.path)
        self.assertEqual(b["Board"], self.csize["Board.Shape.brp"])
        self.assertLess(b["Board"], 50000)                       # compressed, not raw
        self.assertEqual(b["MeshStandIn"], self.csize["MeshKernel3.bms"])   # a mesh file isn't named after its object

    def test_objects_without_files_are_left_out(self):
        self.assertNotIn("Head", dupes.object_bytes(self.path))

    def test_breakdown_by_kind_adds_up(self):
        br = dupes.file_breakdown(self.path)
        self.assertEqual(br["brp"], self.csize["Board.Shape.brp"])
        self.assertEqual(br["bms"], self.csize["MeshKernel3.bms"])
        self.assertEqual(br["total"], sum(self.csize.values()))


class Cluster(unittest.TestCase):
    def test_near_equal_keys_group_across_a_rounding_boundary(self):
        # lite-50: meshes of one board differ by a point; rounding volume to 0.1 put 1234.449 and 1234.451 apart
        m = ("Mesh::Feature",)
        got = dupes.cluster([((m, 1234.449, 500.0), "a"), ((m, 1234.451, 500.01), "b"), ((m, 1234.45, 499.99), "c")])
        self.assertEqual([sorted(g) for g in got], [["a", "b", "c"]])

    def test_kinds_and_distant_volumes_stay_apart(self):
        s, m = ("Part::Feature", 12), ("Mesh::Feature",)
        got = dupes.cluster([((s, 100.0, 50.0), "s1"), ((m, 100.0, 50.0), "m1"), ((s, 100.0, 50.0), "s2"),
                             ((s, 101.0, 50.0), "s3"), ((("Part::Feature", 13), 100.0, 50.0), "t1")])
        self.assertEqual(sorted(sorted(g) for g in got), [["m1"], ["s1", "s2"], ["s3"], ["t1"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
