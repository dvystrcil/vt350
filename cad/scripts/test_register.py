# Tests for register.py (#6): matching a STEP assembly's solids to a model's copy of the same part by label, and the
# least-squares rigid fit (rotation + translation, no scale, no mirror) of their centres of mass. Plain python3, no
# FreeCAD, so they run in CI:
#   python3 cad/scripts/test_register.py      # "Ran N tests" + "OK"
import math, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register


def rot(axis, deg):
    """rotation matrix (rows) about a unit axis by deg"""
    x, y, z = axis; n = math.sqrt(x * x + y * y + z * z); x, y, z = x / n, y / n, z / n
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg)); C = 1 - c
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]


def apply(R, t, p):
    return [sum(R[i][j] * p[j] for j in range(3)) + t[i] for i in range(3)]


PTS = [[0, 0, 0], [40, 0, 0], [0, 25, 0], [0, 0, 30], [12, -7, 19], [-21, 4, 9], [3, 33, -12]]
R0, T0 = rot((0.3, -1.0, 0.4), 137.0), [-412.5, 8.25, 471.0]


def solids(pts, labels=None, vols=None):
    labels = labels or [f"part{i}" for i in range(len(pts))]
    vols = vols or [100.0 + 10 * i for i in range(len(pts))]
    return [dict(label=l, vol=v, com=list(p)) for l, v, p in zip(labels, vols, pts)]


class NormLabel(unittest.TestCase):
    def test_copy_suffixes_are_stripped(self):
        self.assertEqual(register.norm_label("HubHousing V5 With Logo (1) (1)"), "HubHousing V5 With Logo")
        self.assertEqual(register.norm_label("Latch (1)"), "Latch")
        self.assertEqual(register.norm_label("Latch"), "Latch")

    def test_freecad_duplicate_counter_is_stripped(self):
        self.assertEqual(register.norm_label("KnurledNut001"), "KnurledNut")
        self.assertEqual(register.norm_label("Spring v1 (1)002"), "Spring v1")

    def test_a_name_that_is_a_version_keeps_it(self):
        # "v1" / "v4" are part of the name, and a 1- or 2-digit number is not FreeCAD's 3-digit counter
        self.assertEqual(register.norm_label("Orbiter Spider Shaft v4 (1)"), "Orbiter Spider Shaft v4")
        self.assertEqual(register.norm_label("Component18"), "Component18")
        self.assertEqual(register.norm_label("Molded Gear Housing (65 teeth) v1"), "Molded Gear Housing (65 teeth) v1")


class Pair(unittest.TestCase):
    def test_only_labels_unique_on_both_sides_pair(self):
        a = solids([[0, 0, 0]] * 4, ["A", "B", "B001", "C"])
        b = solids([[0, 0, 0]] * 4, ["A (1)", "B (1)", "C (1)", "D"])
        self.assertEqual([k for k, _, _ in register.pair(a, b)], ["A", "C"])     # B twice in a; D not in a

    def test_small_solids_are_left_out(self):
        a = solids([[0, 0, 0]] * 2, ["A", "ball"], [500.0, 3.1])
        b = solids([[0, 0, 0]] * 2, ["A", "ball"], [500.0, 3.1])
        self.assertEqual([k for k, _, _ in register.pair(a, b, min_vol=10.0)], ["A"])

    def test_pairs_come_back_sorted_by_label(self):
        a = solids([[0, 0, 0]] * 3, ["z", "a", "m"]); b = solids([[0, 0, 0]] * 3, ["m", "z", "a"])
        self.assertEqual([k for k, _, _ in register.pair(a, b)], ["a", "m", "z"])


class Fit(unittest.TestCase):
    def test_a_known_rotation_and_translation_come_back(self):
        Q = [apply(R0, T0, p) for p in PTS]
        R, t = register.fit(PTS, Q)
        for i in range(3):
            self.assertAlmostEqual(t[i], T0[i], places=6)
            for j in range(3): self.assertAlmostEqual(R[i][j], R0[i][j], places=9)

    def test_identity(self):
        R, t = register.fit(PTS, PTS)
        for i in range(3):
            self.assertAlmostEqual(t[i], 0.0, places=9)
            for j in range(3): self.assertAlmostEqual(R[i][j], 1.0 if i == j else 0.0, places=9)

    def test_half_turns_are_found(self):
        # 180 degrees: the quaternion's scalar part is 0, where a naive solver loses the axis
        for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)):
            R1 = rot(axis, 180.0)
            R, t = register.fit(PTS, [apply(R1, [1, 2, 3], p) for p in PTS])
            for i in range(3):
                for j in range(3): self.assertAlmostEqual(R[i][j], R1[i][j], places=9, msg=f"axis {axis}")

    def test_the_result_is_a_proper_rotation(self):
        Q = [apply(R0, T0, p) for p in PTS]
        R, _ = register.fit(PTS, Q)
        self.assertAlmostEqual(register.det(R), 1.0, places=9)

    def test_a_mirror_image_is_not_fitted_as_a_rotation(self):
        mirrored = [[-x, y, z] for x, y, z in PTS]
        R, t = register.fit(PTS, mirrored)
        self.assertAlmostEqual(register.det(R), 1.0, places=9)           # never a reflection ...
        res = register.residuals(PTS, mirrored, R, t)
        self.assertGreater(max(res), 1.0)                                # ... so a mirrored copy shows up as residual

    def test_fewer_than_three_points_or_collinear_points_refuse(self):
        with self.assertRaises(ValueError): register.fit(PTS[:2], PTS[:2])
        line = [[0, 0, 0], [1, 1, 1], [2, 2, 2], [5, 5, 5]]
        with self.assertRaises(ValueError): register.fit(line, line)

    def test_mismatched_lengths_refuse(self):
        with self.assertRaises(ValueError): register.fit(PTS, PTS[:-1])


class Register(unittest.TestCase):
    def test_exact_copy_has_zero_residuals(self):
        src = solids(PTS); dst = solids([apply(R0, T0, p) for p in PTS], [f"part{i} (1)" for i in range(len(PTS))])
        r = register.register(src, dst)
        self.assertEqual(r["n"], len(PTS))
        self.assertLess(r["com_max"], 1e-6); self.assertLess(r["com_rms"], 1e-6)
        self.assertEqual(r["vol_max"], 0.0)
        self.assertTrue(r["ok"])

    def test_a_moved_solid_is_the_worst_and_fails(self):
        moved = [apply(R0, T0, p) for p in PTS]; moved[4] = [moved[4][0] + 0.3, moved[4][1], moved[4][2]]
        r = register.register(solids(PTS), solids(moved))
        self.assertFalse(r["ok"])
        self.assertEqual(r["com_worst"], "part4")
        self.assertGreater(r["com_max"], 0.1)

    def test_a_volume_difference_fails_and_names_the_solid(self):
        vols = [100.0 + 10 * i for i in range(len(PTS))]; v2 = list(vols); v2[2] += 2.0
        r = register.register(solids(PTS, vols=vols), solids([apply(R0, T0, p) for p in PTS], vols=v2))
        self.assertFalse(r["ok"])
        self.assertEqual(r["vol_worst"], "part2")
        self.assertAlmostEqual(r["vol_max"], 2.0)

    def test_limits_are_inclusive_of_tiny_noise(self):
        noisy = [apply(R0, T0, p) for p in PTS]; noisy[0][2] += 0.004
        vols = [100.0 + 10 * i for i in range(len(PTS))]; v2 = list(vols); v2[1] += 0.2
        r = register.register(solids(PTS, vols=vols), solids(noisy, vols=v2))
        self.assertTrue(r["ok"], r)

    def test_too_few_pairs_refuse(self):
        with self.assertRaises(ValueError):
            register.register(solids(PTS[:2]), solids(PTS[:2]))

    def test_matrix_is_rows_of_the_fitted_rotation_and_translation(self):
        r = register.register(solids(PTS), solids([apply(R0, T0, p) for p in PTS]))
        m = r["matrix"]                                 # 4x4 rows, for FreeCAD.Matrix(*sum(m, []))
        self.assertEqual(len(m), 4); self.assertEqual(m[3], [0.0, 0.0, 0.0, 1.0])
        for i in range(3): self.assertAlmostEqual(m[i][3], T0[i], places=6)


class PlaneOffset(unittest.TestCase):
    """the hub housing: the same part at a different height, read from its horizontal faces"""
    def test_every_face_moved_the_same_gives_that_offset(self):
        self.assertAlmostEqual(register.plane_offset([457.6, 462.1, 486.4, 496.9], [455.6, 460.1, 484.4, 494.9]), -2.0)

    def test_faces_that_do_not_agree_refuse(self):
        with self.assertRaises(ValueError):
            register.plane_offset([457.6, 462.1, 486.4], [455.6, 460.1, 484.9])

    def test_different_face_counts_refuse(self):
        with self.assertRaises(ValueError): register.plane_offset([1.0, 2.0], [1.0])
        with self.assertRaises(ValueError): register.plane_offset([], [])

    def test_order_does_not_matter(self):
        self.assertAlmostEqual(register.plane_offset([3.0, 1.0, 2.0], [1.5, 2.5, 3.5]), 0.5)


class Boundaries(unittest.TestCase):
    """the edges of each limit, exactly"""
    def test_a_solid_of_exactly_min_vol_pairs(self):
        a = solids([[0, 0, 0]] * 2, ["A", "B"], [10.0, 9.99]); b = solids([[0, 0, 0]] * 2, ["A", "B"], [10.0, 9.99])
        self.assertEqual([k for k, _, _ in register.pair(a, b, min_vol=10.0)], ["A"])

    def test_exactly_three_points_fit(self):
        tri = [[0, 0, 0], [10, 0, 0], [0, 7, 0]]
        R, t = register.fit(tri, [apply(R0, T0, p) for p in tri])
        for i in range(3):
            for j in range(3): self.assertAlmostEqual(R[i][j], R0[i][j], places=9)

    def test_exactly_three_pairs_register(self):
        tri = [[0, 0, 0], [10, 0, 0], [0, 7, 3]]
        self.assertEqual(register.register(solids(tri), solids([apply(R0, T0, p) for p in tri]))["n"], 3)

    def test_points_in_each_coordinate_plane_are_not_collinear(self):
        for tri in ([[0, 0, 0], [10, 0, 0], [0, 7, 0]], [[0, 0, 0], [0, 10, 0], [0, 0, 7]],
                    [[0, 0, 0], [10, 0, 0], [0, 0, 7]], [[0, 0, 0], [3, 0, 0], [6, 0, 0], [0, 0, 5]]):
            R, t = register.fit(tri, tri)
            self.assertAlmostEqual(register.det(R), 1.0, places=9, msg=str(tri))

    def test_identical_points_refuse(self):
        with self.assertRaises(ValueError): register.fit([[1, 2, 3]] * 4, [[1, 2, 3]] * 4)

    def test_volume_difference_equal_to_the_limit_passes(self):
        vols = [100.0 + 10 * i for i in range(len(PTS))]; v2 = list(vols); v2[3] += 0.5
        r = register.register(solids(PTS, vols=vols), solids(PTS, vols=v2), vol_tol=0.5)
        self.assertEqual(r["vol_max"], 0.5); self.assertTrue(r["ok"])

    def test_com_residual_equal_to_the_limit_passes(self):
        r = register.register(solids(PTS), solids(PTS))
        self.assertTrue(register.register(solids(PTS), solids(PTS), com_tol=r["com_max"])["ok"])

    def test_matrix_rows_carry_the_rotation(self):
        r = register.register(solids(PTS), solids([apply(R0, T0, p) for p in PTS]))
        for i in range(3): self.assertEqual(r["matrix"][i][:3], r["R"][i])

    def test_faces_that_agree_exactly_pass_a_zero_tolerance(self):
        self.assertEqual(register.plane_offset([1.0, 2.0], [1.5, 2.5], tol=0.0), 0.5)

    def test_collinear_points_on_a_skew_line_refuse(self):
        # a line whose direction has three different components, so a cross product with its indices mixed up is
        # not zero on it
        for d in ((1, 2, 3), (3, -1, 2), (-2, 5, 1)):
            line = [[k * d[0], k * d[1], k * d[2]] for k in (0, 1, 2.5, 4)]
            with self.assertRaises(ValueError, msg=str(d)): register.fit(line, line)


if __name__ == "__main__":
    unittest.main()
