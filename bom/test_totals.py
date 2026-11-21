#!/usr/bin/env python3
"""Tests for bom/totals.py (#22 AC3 + AC5).

Each test writes a small CSV in a temp dir and runs the real script (imported for the unit cases, and as a
subprocess for the exit codes). The last test runs it on this repository's bom/bom.csv.

Run: python3 bom/test_totals.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "totals.py")

spec = importlib.util.spec_from_file_location("totals", SCRIPT)
totals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(totals)

HEADER = "category,item,qty_needed,qty_owned,vendor,link,unit_price,currency,status,stage,notes\n"


def row(item="part", needed="2", owned="0", price="1.50", cur="USD", status="to buy", stage="#12", cat="cat"):
    return f"{cat},{item},{needed},{owned},Shop,,{price},{cur},{status},{stage},\n"


class TempCSV(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, text):
        path = os.path.join(self.tmp.name, "bom.csv")
        with open(path, "w", newline="") as f:
            f.write(text)
        return path

    def run_script(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class TestTotals(TempCSV):
    def test_status_maps_to_spent_or_to_spend(self):
        rows, errors = totals.load(self.write(
            HEADER
            + row("a", needed="2", owned="2", price="10", status="owned")     # spent 20
            + row("b", needed="3", owned="0", price="1.25", status="ordered")  # spent 3.75
            + row("c", needed="4", owned="1", price="2", status="to buy")    # spent 2, to spend 6
        ))
        self.assertEqual(errors, [])
        t = totals.compute(rows)
        self.assertEqual(t.spent["USD"], Decimal("25.75"))
        self.assertEqual(t.to_spend["USD"], Decimal("6"))
        self.assertEqual(t.unpriced, [])

    def test_owned_more_than_needed_counts_only_what_the_build_needs(self):
        rows, _ = totals.load(self.write(HEADER + row(needed="6", owned="150", price="0.10", status="owned")))
        self.assertEqual(totals.compute(rows).spent["USD"], Decimal("0.60"))

    def test_currencies_are_kept_apart(self):
        rows, _ = totals.load(self.write(HEADER + row("a", price="1", cur="USD") + row("b", price="1", cur="EUR")))
        t = totals.compute(rows)
        self.assertEqual(t.to_spend, {"USD": Decimal("2"), "EUR": Decimal("2")})

    def test_unpriced_rows_are_listed_not_counted_as_zero(self):
        rows, _ = totals.load(self.write(HEADER + row("priced", price="5") + row("mystery", price="")))
        t = totals.compute(rows)
        self.assertEqual(t.to_spend["USD"], Decimal("10"))
        self.assertEqual([r["item"] for r in t.unpriced], ["mystery"])
        out = totals.report(t, "bom.csv")
        self.assertIn("unpriced", out)
        self.assertIn("mystery", out)

    def test_report_prints_the_three_totals(self):
        rows, _ = totals.load(self.write(HEADER + row(price="1", status="ordered") + row(price="2")))
        out = totals.report(totals.compute(rows), "bom.csv")
        self.assertIn("spent so far", out)
        self.assertIn("still to spend", out)
        self.assertIn("grand total", out)
        self.assertIn("6.00", out)  # 2 + 4

    def test_decide_rows_are_not_counted_and_listed_apart(self):
        rows, errors = totals.load(self.write(
            HEADER
            + row("priced", needed="2", owned="0", price="5")                          # to spend 10
            + row("maybe-psu", needed="1", owned="0", price="40", status="decide")    # not counted
            + row("wire", needed="as needed", owned="0", price="", status="decide")    # not counted
        ))
        self.assertEqual(errors, [])
        t = totals.compute(rows)
        self.assertEqual(t.spent.get("USD", Decimal(0)), Decimal("0"))
        self.assertEqual(t.to_spend["USD"], Decimal("10"))
        self.assertEqual([r["item"] for r in t.decide], ["maybe-psu", "wire"])
        self.assertEqual(t.unpriced, [])  # an unpriced decide row is listed once, under decide
        out = totals.report(t, "bom.csv")
        self.assertIn("2 decide row(s)", out)
        self.assertIn("maybe-psu", out)
        self.assertIn("as needed", out)

    def test_cli_prints_totals_and_marker(self):
        p = self.run_script("--csv", self.write(HEADER + row()))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("still to spend", p.stdout)
        self.assertEqual(p.stdout.strip().splitlines()[-1], "bom-totals: OK")


class TestCheck(TempCSV):
    def errors_for(self, text):
        return totals.load(self.write(text))[1]

    def assertError(self, text, fragment):
        errors = self.errors_for(text)
        self.assertTrue(any(fragment in e for e in errors), f"no error containing {fragment!r} in {errors}")

    def test_good_csv_has_no_errors(self):
        self.assertEqual(self.errors_for(HEADER + row() + row(price="", stage="#7") + row(stage="#15")), [])

    def test_wrong_header(self):
        self.assertError(HEADER.replace("unit_price", "price") + row(), "header")

    def test_non_numeric_qty(self):
        self.assertError(HEADER + row(needed="many"), "qty_needed")
        self.assertError(HEADER + row(owned="-1"), "qty_owned")

    def test_non_numeric_price(self):
        self.assertError(HEADER + row(price="$1.50"), "unit_price")

    def test_unknown_status(self):
        self.assertError(HEADER + row(status="bought"), "status")

    def test_decide_row_may_have_a_word_qty_and_no_price(self):
        self.assertEqual(self.errors_for(
            HEADER + row(needed="as needed", owned="", price="", cur="", status="decide")), [])

    def test_decide_row_still_checks_a_price_it_has(self):
        self.assertError(HEADER + row(needed="as needed", price="$3", status="decide"), "unit_price")

    def test_word_qty_only_for_decide(self):
        for status in ("owned", "ordered", "to buy"):
            self.assertError(HEADER + row(needed="as needed", status=status), "qty_needed")

    def test_stage_outside_the_stage_issues(self):
        for bad in ("", "12", "#6", "#16", "#12a"):
            self.assertError(HEADER + row(stage=bad), "stage")

    def test_price_without_currency(self):
        self.assertError(HEADER + row(cur=""), "currency")

    def test_owned_row_short_of_parts(self):
        self.assertError(HEADER + row(needed="3", owned="1", status="owned"), "owned")

    def test_errors_name_the_line(self):
        errors = self.errors_for(HEADER + row() + row(status="bought"))
        self.assertTrue(any("line 3" in e for e in errors), errors)

    def test_check_mode_fails_with_message_and_exit_1(self):
        p = self.run_script("--check", "--csv", self.write(HEADER + row(status="bought")))
        self.assertEqual(p.returncode, 1)
        self.assertIn("status", p.stdout + p.stderr)
        self.assertNotIn("bom-check: OK", p.stdout)

    def test_totals_refuse_a_bad_csv(self):
        p = self.run_script("--csv", self.write(HEADER + row(needed="x")))
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("bom-totals: OK", p.stdout)


class TestHeads(TempCSV):
    """`per head` rows list one head's parts; --heads N (default 2) multiplies their qty_needed."""

    def bom(self):
        return self.write(
            HEADER
            + row("orbiter", needed="2", owned="1", price="10", cat="per head")  # per head: 2 needed, 1 owned
            + row("frame", needed="4", owned="0", price="1")                      # shared: never multiplied
        )

    def test_one_head(self):
        rows, errors = totals.load(self.bom(), heads=1)
        self.assertEqual(errors, [])
        t = totals.compute(rows, heads=1)
        self.assertEqual(t.spent["USD"], Decimal("10"))       # the 1 owned
        self.assertEqual(t.to_spend["USD"], Decimal("14"))    # 1 more orbiter + 4 frame

    def test_three_heads(self):
        rows, _ = totals.load(self.bom(), heads=3)
        t = totals.compute(rows, heads=3)
        self.assertEqual(t.spent["USD"], Decimal("10"))       # still the 1 owned
        self.assertEqual(t.to_spend["USD"], Decimal("54"))    # 6 - 1 = 5 orbiters + 4 frame

    def test_default_is_two_heads(self):
        self.assertEqual(totals.DEFAULT_HEADS, 2)
        rows, _ = totals.load(self.bom())
        self.assertEqual(totals.compute(rows).to_spend["USD"], Decimal("34"))  # 3 orbiters + 4 frame

    def test_ordered_per_head_row_counts_every_head(self):
        rows, _ = totals.load(self.write(HEADER + row(needed="3", price="1", status="ordered", cat="per head")))
        self.assertEqual(totals.compute(rows, heads=2).spent["USD"], Decimal("6"))

    def test_owned_per_head_row_must_cover_every_head(self):
        text = HEADER + row(needed="1", owned="2", price="1", status="owned", cat="per head")
        self.assertEqual(totals.load(self.write(text), heads=2)[1], [])
        errors = totals.load(self.write(text), heads=3)[1]
        self.assertTrue(any("owned" in e for e in errors), errors)

    def test_report_names_the_head_count(self):
        rows, _ = totals.load(self.bom(), heads=3)
        out = totals.report(totals.compute(rows, heads=3), "bom.csv")
        self.assertIn("for 3 heads", out.splitlines()[0])

    def test_cli_heads_flag(self):
        p = self.run_script("--heads", "3", "--csv", self.bom())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("for 3 heads", p.stdout.splitlines()[0])
        self.assertIn("still to spend 54.00", p.stdout)

    def test_cli_rejects_zero_heads(self):
        p = self.run_script("--heads", "0", "--csv", self.bom())
        self.assertNotEqual(p.returncode, 0)


class TestRepo(unittest.TestCase):
    def test_real_bom_passes_the_check(self):
        p = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.strip().splitlines()[-1], "bom-check: OK")

    def test_real_bom_totals_run(self):
        p = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
