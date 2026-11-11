"""render.py --frames (vt350#135 AC4): one PNG per motion frame, each moving group's objects moved by the frame's
translation, from an export made ONCE (nothing re-exported per frame).

Needs Blender, so not in CI (test_motion.py, stdlib-only, is):

    python3 platform/render/test_render_frames.py                # `blender` on PATH
    VT350_BLENDER="docker run ... --entrypoint blender gpu-batch-blender:local" python3 platform/render/test_render_frames.py

A two-box fixture at 64x36, 1 sample: "frame" stays, "bed__box" (group bed) moves. ~1 min.
"""
import json, os, shlex, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import motion  # noqa: E402

BLENDER = shlex.split(os.environ.get("VT350_BLENDER", "blender"))


def box_stl(path, x0, y0, z0, s):
    v = [(x0 + dx * s, y0 + dy * s, z0 + dz * s) for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    with open(path, "w") as f:
        f.write("solid b\n")
        for a, b, c in faces:
            f.write("facet normal 0 0 0\nouter loop\n" + "".join("vertex %f %f %f\n" % v[k] for k in (a, b, c))
                    + "endloop\nendfacet\n")
        f.write("endsolid b\n")


def write_fixture(src):
    box_stl(os.path.join(src, "frame.stl"), -300, 0, 0, 100)
    box_stl(os.path.join(src, "bed__box.stl"), 0, 0, 0, 100)
    scene = {"model": "fixture.FCStd", "lights": [], "camera": None,
             "buckets": {"frame": {"material": "", "labels": ["frame"], "color": [0.6, 0.6, 0.6]},
                         "bed__box": {"material": "", "labels": ["bed"], "color": [0.9, 0.3, 0.1], "group": "bed"}},
             "views": [{"name": "front", "pos": [-100, -1500, 50], "look": [-100, 0, 50], "lens_mm": 35}]}
    with open(os.path.join(src, "scene.json"), "w") as f:
        json.dump(scene, f)


def frames(n, step):
    return motion.frames_file([{"t": i, "seq": 1, "pos": [0, 0, 0], "carried": None, "groups": {"bed": [0, 0, -step * i]}}
                               for i in range(n)], fps=10)


class RenderFrames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vt350-frames-test-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.src, cls.out = os.path.join(cls.tmp, "export"), os.path.join(cls.tmp, "out")
        os.makedirs(cls.src)
        write_fixture(cls.src)
        cls.ff = os.path.join(cls.tmp, "frames.json")
        with open(cls.ff, "w") as f:
            json.dump(frames(3, 150), f)                   # 150 mm a frame: the box leaves its place each time
        cls.first = cls.run_blender(cls.ff)
        cls.ff2 = os.path.join(cls.tmp, "frames4.json")
        with open(cls.ff2, "w") as f:
            json.dump(frames(4, 150), f)                   # the same 3 + one more
        cls.resumed = cls.run_blender(cls.ff2)

    @classmethod
    def run_blender(cls, ff, *extra):
        return subprocess.run(BLENDER + ["-b", "--python-exit-code", "1", "-P", os.path.join(HERE, "render.py"), "--",
                                         cls.src, cls.out, "1", "--frames", ff, "--size", "64x36", *extra],
                              capture_output=True, text=True)

    def log(self, r):
        return r.stdout[-3000:] + r.stderr[-3000:]

    def test_blender_ran(self):
        self.assertEqual(self.first.returncode, 0, self.log(self.first))
        self.assertIn("frames: done", self.first.stdout, self.log(self.first))

    def test_one_png_per_frame_and_no_still_views(self):
        self.assertEqual(sorted(os.listdir(self.out)), [motion.frame_name(i) for i in range(4)])

    def test_the_moving_group_moves_between_frames(self):
        b = []
        for i in range(3):
            with open(os.path.join(self.out, motion.frame_name(i)), "rb") as f:
                b.append(f.read())
        self.assertNotEqual(b[0], b[1])
        self.assertNotEqual(b[1], b[2])

    def test_a_png_is_the_size_asked(self):
        with open(os.path.join(self.out, motion.frame_name(0)), "rb") as f:
            head = f.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual((int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")), (64, 36))

    def test_a_second_run_renders_only_the_missing_frames(self):
        self.assertEqual(self.resumed.returncode, 0, self.log(self.resumed))
        self.assertIn("3 already rendered, 1 to render", self.resumed.stdout)

    def test_a_group_the_export_lacks_fails_the_run(self):
        ff = os.path.join(self.tmp, "gantry.json")
        with open(ff, "w") as f:
            json.dump({"fps": 10, "frames": [{"i": 0, "groups": {"bed": [0, 0, 0], "gantry": [0, 1, 0]}}]}, f)
        r = self.run_blender(ff)
        self.assertNotEqual(r.returncode, 0, self.log(r))
        self.assertIn("gantry", self.log(r))

    def test_an_unknown_view_fails_the_run(self):
        r = self.run_blender(self.ff, "--view", "nope")
        self.assertNotEqual(r.returncode, 0, self.log(r))
        self.assertIn("no view 'nope'", self.log(r))


if __name__ == "__main__":
    unittest.main(verbosity=1)
