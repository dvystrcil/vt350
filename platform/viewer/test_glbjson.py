"""Tests for glbjson.py (vt350#220): a GLB's buffer comes out embedded, byte for byte. Stdlib only (CI: viewer.yml).

    python3 platform/viewer/test_glbjson.py
"""
import base64, json, os, struct, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glbjson


def make_glb(doc, binary):
    j = json.dumps(doc).encode(); j += b" " * (-len(j) % 4)
    b = binary + b"\0" * (-len(binary) % 4)
    body = struct.pack("<II", len(j), glbjson.JSON_CHUNK) + j + struct.pack("<II", len(b), glbjson.BIN_CHUNK) + b
    return struct.pack("<III", glbjson.MAGIC, 2, 12 + len(body)) + body


class GlbJson(unittest.TestCase):
    def test_buffer_embedded_exactly(self):
        data = bytes(range(7))                                   # 7 bytes: the chunk pads to 8, byteLength stays 7
        doc = glbjson.convert(make_glb({"asset": {"version": "2.0"}, "buffers": [{"byteLength": 7}]}, data))
        uri = doc["buffers"][0]["uri"]
        self.assertTrue(uri.startswith("data:application/octet-stream;base64,"))
        self.assertEqual(base64.b64decode(uri.split(",", 1)[1]), data)
        self.assertEqual(doc["asset"]["version"], "2.0")

    def test_not_a_glb(self):
        with self.assertRaises(ValueError):
            glbjson.convert(b"\0" * 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
