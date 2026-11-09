# Tests for contact.py (#82): the Z sweep's search windows, its scan + bisection, the pruned search over pairs and the
# log's limit lines. Plain python3, no FreeCAD, so they run in CI:
#   python3 cad/scripts/test_contact.py      # "Ran N tests" + "OK"
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contact


def slab(z0, z1, area=100.0):
    """probe for a part that overlaps a fixed part while the travel d is in [z0, z1]: volume grows linearly in."""
    def probe(d):
        return area * (min(d, z1) - z0) if z0 < d else 0.0
    return probe


class Counting:
    """records each probe; a runaway scan or bisection fails the test instead of hanging it"""
    LIMIT = 5000

    def __init__(self, f): self.f, self.calls = f, []

    def __call__(self, d):
        self.calls.append(d)
        if len(self.calls) > self.LIMIT: raise AssertionError(f"probe called over {self.LIMIT} times")
        return self.f(d)


def fc(probe, lo, hi, **kw):
    return contact.first_contact(Counting(probe), lo, hi, **kw)


class FirstContact(unittest.TestCase):
    def test_contact_is_found_to_within_eps(self):
        r = fc(slab(12.34, 20.0), 0.0, 30.0)
        self.assertEqual(r["kind"], "contact")
        self.assertGreaterEqual(r["d"], 12.34)                  # the reported travel overlaps ...
        self.assertLess(r["d"] - 12.34, contact.EPS + 1e-6)     # ... and is no more than eps past the touch

    def test_the_reported_travel_is_one_that_overlaps_and_eps_less_is_clear(self):
        p = slab(7.0, 9.0, area=1.0)
        r = fc(p, 0.0, 30.0)
        self.assertGreater(p(r["d"]), contact.TOL)
        self.assertLessEqual(p(r["d"] - contact.EPS), contact.TOL)

    def test_no_contact_in_the_window_is_clear(self):
        self.assertEqual(fc(slab(50.0, 60.0), 0.0, 30.0), {"kind": "clear", "d": None})

    def test_contact_at_the_window_end_is_found(self):
        r = fc(slab(29.9, 40.0), 0.0, 30.0)
        self.assertEqual(r["kind"], "contact")
        self.assertAlmostEqual(r["d"], 29.9, delta=contact.EPS + 1e-6)

    def test_the_last_partial_step_is_probed_at_hi_exactly(self):
        p = Counting(slab(100.0, 200.0))
        fc(p, 0.0, 1.2, step=0.5)
        self.assertEqual(p.calls, [0.0, 0.5, 1.0, 1.2])

    def test_steps_are_lo_plus_i_step_not_accumulated(self):
        p = Counting(slab(100.0, 200.0))
        fc(p, 0.1, 0.7, step=0.1)
        self.assertEqual(p.calls, [0.1, 0.1 + 0.1, 0.1 + 2 * 0.1, 0.1 + 3 * 0.1, 0.1 + 4 * 0.1, 0.1 + 5 * 0.1, 0.7])

    def test_a_thin_part_thicker_than_a_step_is_not_jumped(self):
        r = fc(slab(3.01, 3.52), 0.0, 10.0, step=0.5)
        self.assertEqual(r["kind"], "contact")
        self.assertAlmostEqual(r["d"], 3.01, delta=contact.EPS + 1e-6)

    def test_overlap_at_the_window_start_is_reported_as_start_with_its_volume(self):
        r = fc(lambda d: 5.0, 0.0, 10.0)
        self.assertEqual(r, {"kind": "start", "d": 0.0, "volume": 5.0})

    def test_volume_at_tol_is_not_an_overlap(self):
        self.assertEqual(fc(lambda d: contact.TOL, 0.0, 1.0)["kind"], "clear")

    def test_tol_and_eps_can_be_given(self):
        r = fc(slab(2.0, 9.0, area=1.0), 0.0, 5.0, eps=0.1, tol=0.5)
        self.assertEqual(r["kind"], "contact")
        self.assertGreater(r["d"] - 2.0, 0.5)                   # volume first passes 0.5 at d = 2.5
        self.assertLess(r["d"] - 2.5, 0.1 + 1e-9)

    def test_bisection_stops_at_eps(self):
        p = Counting(slab(1.0, 9.0))
        fc(p, 0.0, 2.0, step=1.0, eps=0.25)
        # scan 0, 1, 2 then halve [1, 2] down to 0.25: 1.5, 1.25 -> 2 bisection probes
        self.assertEqual(len(p.calls), 5)

    def test_empty_window_is_clear(self):
        self.assertEqual(fc(slab(0.0, 9.0), 4.0, 4.0)["kind"], "start")
        self.assertEqual(fc(slab(5.0, 9.0), 4.0, 4.0)["kind"], "clear")

    def test_a_volume_of_exactly_tol_in_the_bisection_is_clear(self):
        p = lambda d: 0.0 if d < 1 else (contact.TOL if d < 2 else 1.0)
        r = fc(p, 0.0, 3.0, step=1.0)
        self.assertAlmostEqual(r["d"], 2.0, delta=contact.EPS + 1e-9)

    def test_the_bisection_never_leaves_its_bracket(self):
        p = Counting(slab(1.3, 9.0))
        contact.first_contact(p, 0.0, 2.0, step=1.0)
        self.assertTrue(all(1.0 <= d <= 2.0 for d in p.calls[3:]), p.calls)

    def test_bad_arguments_raise(self):
        for kw in (dict(step=0), dict(step=-1), dict(eps=0)):
            with self.assertRaises(ValueError): fc(slab(1, 2), 0.0, 3.0, **kw)
        with self.assertRaises(ValueError): fc(slab(1, 2), 3.0, 1.0)


class Window(unittest.TestCase):
    def test_xy_gap_of_exactly_twice_the_margin_still_overlaps(self):
        for b in ((21, 0, -10, 30, 20, -2), (-10, 0, -10, -1, 20, -2), (0, 21, -10, 20, 30, -2), (0, -10, -10, 20, -1, -2)):
            self.assertIsNotNone(contact.window(self.BED, b, -1, margin=0.5), b)

    def test_hi_of_exactly_zero_never_meets_and_just_above_does(self):
        self.assertIsNone(contact.window(self.BED, (0, 0, 261, 20, 20, 270), -1, margin=0.5))
        self.assertEqual(contact.window(self.BED, (0, 0, 260.5, 20, 20, 270), -1, margin=0.5), (0.0, 0.5))

    def test_lo_exactly_at_cap_never_meets(self):
        self.assertIsNone(contact.window(self.BED, (0, 0, -10, 20, 20, -2), -1, margin=0.5, cap=241.0))

    # boxes (xmin, ymin, zmin, xmax, ymax, zmax)
    BED = (0, 0, 240, 20, 20, 260)

    def test_down_lower_bound_is_the_box_gap_less_the_margin(self):
        lo, hi = contact.window(self.BED, (0, 0, -10, 20, 20, -2), -1, margin=0.5)
        self.assertAlmostEqual(lo, 242 - 1.0)                   # each box grows by the margin: 2 x 0.5
        self.assertAlmostEqual(hi, 270 + 1.0)                   # past this the bed is wholly below the plate

    def test_up_window(self):
        lo, hi = contact.window(self.BED, (0, 0, 300, 20, 20, 310), +1, margin=0.5)
        self.assertAlmostEqual(lo, 40 - 1.0)
        self.assertAlmostEqual(hi, 70 + 1.0)

    def test_overlapping_boxes_start_at_zero(self):
        self.assertEqual(contact.window(self.BED, (0, 0, 250, 20, 20, 300), -1, margin=0.5)[0], 0.0)
        self.assertEqual(contact.window(self.BED, (0, 0, 200, 20, 20, 250), +1, margin=0.5)[0], 0.0)

    def test_a_part_on_the_wrong_side_never_meets(self):
        self.assertIsNone(contact.window(self.BED, (0, 0, 300, 20, 20, 310), -1))
        self.assertIsNone(contact.window(self.BED, (0, 0, -10, 20, 20, -2), +1))

    def test_no_xy_overlap_never_meets(self):
        self.assertIsNone(contact.window(self.BED, (30, 0, -10, 40, 20, -2), -1, margin=0.5))
        self.assertIsNone(contact.window(self.BED, (0, 30, -10, 20, 40, -2), -1, margin=0.5))
        self.assertIsNone(contact.window(self.BED, (-40, 0, -10, -30, 20, -2), -1, margin=0.5))
        self.assertIsNone(contact.window(self.BED, (0, -40, -10, 20, -30, -2), -1, margin=0.5))

    def test_xy_within_the_margin_counts_as_overlap(self):
        self.assertIsNotNone(contact.window(self.BED, (20.8, 0, -10, 30, 20, -2), -1, margin=0.5))
        self.assertIsNotNone(contact.window(self.BED, (0, -10, -10, 20, -0.8, -2), -1, margin=0.5))
        self.assertIsNone(contact.window(self.BED, (21.1, 0, -10, 30, 20, -2), -1, margin=0.5))

    def test_cap_drops_a_window_that_starts_past_it_and_trims_one_that_ends_past_it(self):
        self.assertIsNone(contact.window(self.BED, (0, 0, -10, 20, 20, -2), -1, margin=0.5, cap=200))
        lo, hi = contact.window(self.BED, (0, 0, -10, 20, 20, -2), -1, margin=0.5, cap=250)
        self.assertEqual(hi, 250)

    def test_direction_must_be_plus_or_minus_one(self):
        with self.assertRaises(ValueError): contact.window(self.BED, self.BED, 0)


class Search(unittest.TestCase):
    """pairs [(key, lo, hi)]; run(batch) -> [first_contact result per pair]; contacts by travel d."""

    def fake(self, truth):
        """truth {key: d or None or ('start', v)}: what first_contact would find in [lo, hi]."""
        self.seen = []

        def run(batch):
            self.seen.append([k for k, _, _ in batch])
            out = []
            for k, lo, hi in batch:
                t = truth[k]
                if isinstance(t, tuple): out.append({"kind": "start", "d": lo, "volume": t[1]})
                elif t is not None and lo <= t <= hi: out.append({"kind": "contact", "d": t})
                else: out.append({"kind": "clear", "d": None})
            return out
        return run

    def test_the_first_contact_wins_and_contacts_are_sorted(self):
        pairs = [("a", 0, 100), ("b", 0, 100), ("c", 0, 100)]
        r = contact.search(pairs, self.fake({"a": 30.0, "b": 10.0, "c": None}), cap=400, report=50)
        self.assertEqual(r["best"], (10.0, "b"))
        self.assertEqual(r["contacts"], [(10.0, "b"), (30.0, "a")])

    def test_pairs_whose_window_starts_past_best_plus_report_are_never_run(self):
        pairs = [("near", 0, 100), ("far", 50, 100)]
        r = contact.search(pairs, self.fake({"near": 10.0, "far": 60.0}), cap=400, report=5, batch=1)
        self.assertEqual(self.seen, [["near"]])
        self.assertEqual(r["contacts"], [(10.0, "near")])

    def test_a_pair_inside_the_report_band_is_run_and_listed(self):
        pairs = [("near", 0, 100), ("next", 12, 100)]
        r = contact.search(pairs, self.fake({"near": 10.0, "next": 13.0}), cap=400, report=5, batch=1)
        self.assertEqual(r["contacts"], [(10.0, "near"), (13.0, "next")])

    def test_contacts_past_the_report_band_are_dropped(self):
        pairs = [("near", 0, 100), ("late", 0, 100)]
        r = contact.search(pairs, self.fake({"near": 10.0, "late": 16.0}), cap=400, report=5)
        self.assertEqual(r["contacts"], [(10.0, "near")])

    def test_windows_are_trimmed_to_best_plus_report(self):
        pairs = [("near", 0, 100), ("next", 1, 100)]
        got = []
        def run(batch):
            got.extend(batch)
            return [{"kind": "contact", "d": 10.0} if k == "near" else {"kind": "clear", "d": None} for k, _, _ in batch]
        contact.search(pairs, run, cap=400, report=5, batch=1)
        self.assertEqual(got, [("near", 0, 100), ("next", 1, 15.0)])

    def test_windows_are_trimmed_to_cap_before_any_contact(self):
        got = []
        def run(batch):
            got.extend(batch); return [{"kind": "clear", "d": None} for _ in batch]
        r = contact.search([("a", 0, 500)], run, cap=400, report=5)
        self.assertEqual(got, [("a", 0, 400)])
        self.assertIsNone(r["best"])

    def test_pairs_run_in_window_order_in_batches(self):
        pairs = [("c", 3, 9), ("a", 1, 9), ("b", 2, 9)]
        contact.search(pairs, self.fake({"a": None, "b": None, "c": None}), cap=400, report=5, batch=2)
        self.assertEqual(self.seen, [["a", "b"], ["c"]])

    def test_a_pair_starting_exactly_at_best_plus_report_is_not_run(self):
        pairs = [("near", 0, 100), ("edge", 15.0, 100)]
        contact.search(pairs, self.fake({"near": 10.0, "edge": 15.0}), cap=400, report=5, batch=1)
        self.assertEqual(self.seen, [["near"]])

    def test_a_contact_exactly_at_best_plus_report_is_listed(self):
        pairs = [("near", 0, 100), ("edge", 0, 100)]
        r = contact.search(pairs, self.fake({"near": 10.0, "edge": 15.0}), cap=400, report=5)
        self.assertEqual(r["contacts"], [(10.0, "near"), (15.0, "edge")])

    def test_a_tie_keeps_the_first_pair_in_window_order(self):
        pairs = [("first", 0, 100), ("second", 1, 100)]
        r = contact.search(pairs, self.fake({"first": 10.0, "second": 10.0}), cap=400, report=5)
        self.assertEqual(r["best"], (10.0, "first"))

    def test_a_start_overlap_just_past_zero_is_an_error(self):
        def run(batch): return [{"kind": "start", "d": lo, "volume": 1.0} for _, lo, _ in batch]
        with self.assertRaises(RuntimeError): contact.search([("x", 0.5, 9.0)], run, cap=400)

    def test_start_overlaps_are_fits_not_contacts(self):
        pairs = [("nut", 0, 100), ("t", 0, 100)]
        r = contact.search(pairs, self.fake({"nut": ("start", 42.0), "t": 20.0}), cap=400, report=5)
        self.assertEqual(r["fits"], [("nut", 42.0)])
        self.assertEqual(r["best"], (20.0, "t"))

    def test_a_start_overlap_past_zero_is_an_error(self):
        def run(batch): return [{"kind": "start", "d": lo, "volume": 1.0} for _, lo, _ in batch]
        with self.assertRaisesRegex(RuntimeError, "box prefilter"):
            contact.search([("x", 3.0, 9.0)], run, cap=400)

    def test_run_must_answer_every_pair(self):
        with self.assertRaisesRegex(RuntimeError, "2 pairs"):
            contact.search([("a", 0, 1), ("b", 0, 1)], lambda b: [], cap=400)

    def test_no_pairs(self):
        self.assertEqual(contact.search([], self.fake({}), cap=400),
                         {"best": None, "contacts": [], "fits": [], "runs": 0})

    def test_runs_counts_pairs_run(self):
        pairs = [("a", 0, 100), ("b", 0, 100), ("far", 90, 100)]
        r = contact.search(pairs, self.fake({"a": 5.0, "b": None, "far": None}), cap=400, report=5, batch=1)
        self.assertEqual(r["runs"], 2)


class Lines(unittest.TestCase):
    LOG = ("[   1.0s] model x\n"
           "[  80.2s] z_lower_limit_mm=43.78 (bed dZ -241.98; 2020 (1) lands on backbone-350 v2)\n"
           "[  99.0s] z_upper_limit_mm=380.81 (bed dZ +95.05; Left head carried)\n"
           "[  99.1s] print_height_mm=337.03 (Left head)\n"
           "[  99.2s] z_sweep: done (read-only, nothing saved)\n")

    def test_parse_reads_the_three_numbers(self):
        self.assertEqual(contact.parse(self.LOG), {"z_lower_limit_mm": 43.78, "z_upper_limit_mm": 380.81,
                                                   "print_height_mm": 337.03})

    def test_parse_takes_the_last_line_of_each(self):
        log = self.LOG + "[ 1s] z_lower_limit_mm=1.5 (again)\n"
        self.assertEqual(contact.parse(log)["z_lower_limit_mm"], 1.5)

    def test_parse_reads_negative_numbers(self):
        self.assertEqual(contact.parse(self.LOG.replace("43.78", "-3.25"))["z_lower_limit_mm"], -3.25)

    def test_parse_refuses_an_unfinished_log(self):
        with self.assertRaisesRegex(ValueError, "not finished"):
            contact.parse(self.LOG.replace("z_sweep: done (read-only, nothing saved)", ""))

    def test_parse_refuses_a_missing_number(self):
        with self.assertRaisesRegex(ValueError, "print_height_mm"):
            contact.parse(self.LOG.replace("print_height_mm=337.03", "print height"))

    def test_line_formats_two_decimals(self):
        self.assertEqual(contact.line("z_lower_limit_mm", 43.784, "why"), "z_lower_limit_mm=43.78 (why)")
        self.assertEqual(contact.parse("x z_lower_limit_mm=43.78 (w)\nz_upper_limit_mm=1.00 (w)\n"
                                       "print_height_mm=2.50\nz_sweep: done (read-only, nothing saved)\n"),
                         {"z_lower_limit_mm": 43.78, "z_upper_limit_mm": 1.0, "print_height_mm": 2.5})


if __name__ == "__main__":
    unittest.main(verbosity=2)
