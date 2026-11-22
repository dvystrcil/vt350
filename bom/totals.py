#!/usr/bin/env python3
"""BOM totals and BOM check, from bom/bom.csv (#22 AC3 + AC5).

Prints spent so far, still to spend and the grand total, per currency. Refuses (exit 1) if the CSV fails the check.

How a row counts (cost = units x unit_price; the build's cost, so only qty_needed units ever count):
  - status "owned" or "ordered": every needed unit is paid for, so qty_needed x unit_price is spent.
    (An "owned" row must have qty_owned >= qty_needed; a part still short is "to buy".)
  - status "to buy": the units already in hand, min(qty_owned, qty_needed), are spent;
    the rest, qty_needed - qty_owned (not below 0), is still to spend.
  - status "decide": not decided yet (whether to buy it, or which one). Never counted in spent or still to spend;
    listed apart with their count, like the unpriced rows. Its qty may be words ("as needed") and its price empty.
  - grand total = spent + still to spend.
  - A row with no unit_price is "unpriced": it's listed with its status and qty, never added as 0,
    so the totals are a floor until every row has a price.
Extra units bought (a 150-pack for 6 inserts) aren't counted: unit_price is per unit and the totals cost the build.

Per-head rows (#22, owner 2026-11-19): a row in category "per head" lists the parts for ONE toolhead. --heads N
(default 2, the planned build) multiplies its qty_needed by N everywhere above; qty_owned is the count owned in all,
never multiplied. So an "owned" per-head row must own qty_needed x N, and an "ordered" one counts qty_needed x N as
spent (ordered for every head: if fewer were ordered, make it "to buy" with qty_owned set). Rows in every other
category are shared (the carriage, the Beacon, the dock bar) and never multiplied. The report's first line names N.

The check (also run before totals; --check runs only it) fails when:
  - the header isn't exactly the AC3 columns;
  - category or item is empty;
  - qty_needed or qty_owned isn't a non-negative number (a "decide" row may write words, e.g. "as needed");
  - unit_price is set but isn't a non-negative number (no currency sign; that goes in `currency`);
  - a priced row's currency isn't a 3-letter code like USD;
  - status isn't one of: owned, ordered, to buy, decide;
  - an "owned" row owns fewer than it needs (a per-head row: fewer than qty_needed x --heads);
  - stage isn't a stage issue #7 to #15 (written "#12"); the per-step Buy lists in #40 group by it.

Stdlib only. Usage:
  python3 bom/totals.py [--heads N] [--csv PATH]            # totals for N heads (default 2); last line "bom-totals: OK"
  python3 bom/totals.py --check [--heads N] [--csv PATH]    # check only; last line "bom-check: OK"
"""
import argparse
import csv
import os
import re
import sys
from collections import namedtuple
from decimal import Decimal, InvalidOperation

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "bom.csv")
HEADER = ["category", "item", "qty_needed", "qty_owned", "vendor", "link",
          "unit_price", "currency", "status", "stage", "notes"]
STATUSES = ("owned", "ordered", "to buy", "decide")
STAGES = range(7, 16)  # the stage issues #7-#15
PER_HEAD = "per head"  # category whose qty_needed is for one toolhead
DEFAULT_HEADS = 2      # the planned build

Totals = namedtuple("Totals", "spent to_spend unpriced decide heads")


def number(text):
    """A non-negative Decimal, or None."""
    try:
        n = Decimal(text.strip())
    except InvalidOperation:
        return None
    return n if n.is_finite() and n >= 0 else None


def heads_factor(r, heads):
    """What a row's qty_needed is multiplied by: the head count for a per-head row, else 1."""
    return heads if r["category"].strip() == PER_HEAD else 1


def check_row(r, heads=DEFAULT_HEADS):
    """Error messages for one row (empty when it's fine)."""
    errors = []
    for col in ("category", "item"):
        if not r[col].strip():
            errors.append(f"{col} is empty")
    for col in ("qty_needed", "qty_owned"):
        if r["status"] == "decide":
            continue  # undecided: the qty may be words ("as needed") or empty
        if number(r[col]) is None:
            errors.append(f"{col} {r[col]!r} isn't a non-negative number")
    price = r["unit_price"].strip()
    if price:
        if number(price) is None:
            errors.append(f"unit_price {price!r} isn't a non-negative number (put the currency in `currency`)")
        if not re.fullmatch(r"[A-Z]{3}", r["currency"].strip()):
            errors.append(f"currency {r['currency']!r} isn't a 3-letter code like USD")
    if r["status"] not in STATUSES:
        errors.append(f"status {r['status']!r} isn't one of: {', '.join(STATUSES)}")
    elif r["status"] == "owned":
        needed, owned = number(r["qty_needed"]), number(r["qty_owned"])
        if needed is not None and owned is not None and owned < needed * heads_factor(r, heads):
            need = f"{needed} x {heads} heads" if heads_factor(r, heads) != 1 else f"{needed}"
            errors.append(f"status 'owned' but qty_owned {owned} < qty_needed {need} (use 'to buy' for the rest)")
    m = re.fullmatch(r"#(\d+)", r["stage"].strip())
    if not m or int(m.group(1)) not in STAGES:
        errors.append(f"stage {r['stage']!r} isn't a stage issue #7 to #15 (written like #12)")
    return errors


def load(path, heads=DEFAULT_HEADS):
    """(rows, errors). Each error starts with the file and line number."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        if header != HEADER:
            return [], [f"{path}: line 1: header is {header}, expected {HEADER}"]
        rows, errors = [], []
        for cells in reader:
            line = reader.line_num
            if not any(c.strip() for c in cells):
                continue
            if len(cells) != len(HEADER):
                errors.append(f"{path}: line {line}: {len(cells)} fields, expected {len(HEADER)}")
                continue
            r = dict(zip(HEADER, cells))
            r["line"] = line
            errors += [f"{path}: line {line} ({r['item'][:40]!r}): {e}" for e in check_row(r, heads)]
            rows.append(r)
    return rows, errors


def compute(rows, heads=DEFAULT_HEADS):
    """Totals per currency for `heads` toolheads. Assumes the rows passed the check."""
    spent, to_spend, unpriced, decide = {}, {}, [], []
    for r in rows:
        if r["status"] == "decide":
            decide.append(r)
            continue
        needed, owned = number(r["qty_needed"]) * heads_factor(r, heads), number(r["qty_owned"])
        if r["status"] in ("owned", "ordered"):
            paid, rest = needed, Decimal(0)
        else:  # to buy
            paid = min(owned, needed)
            rest = needed - paid
        if not r["unit_price"].strip():
            unpriced.append(r)
            continue
        price, cur = number(r["unit_price"]), r["currency"].strip()
        spent[cur] = spent.get(cur, Decimal(0)) + paid * price
        to_spend[cur] = to_spend.get(cur, Decimal(0)) + rest * price
    return Totals(spent, to_spend, unpriced, decide, heads)


def per(r):
    return " per head" if r["category"].strip() == PER_HEAD else ""


def money(n):
    return f"{n.quantize(Decimal('0.01')):,}"


def report(t, path):
    lines = [f"BOM totals from {os.path.relpath(path)} for {t.heads} heads (priced rows only; "
             f"'{PER_HEAD}' rows are for one head, x {t.heads})"]
    currencies = sorted(set(t.spent) | set(t.to_spend))
    if not currencies:
        lines.append("  no priced rows yet")
    for cur in currencies:
        s, r = t.spent.get(cur, Decimal(0)), t.to_spend.get(cur, Decimal(0))
        lines.append(f"  {cur}: spent so far {money(s)}, still to spend {money(r)}, grand total {money(s + r)}")
    if t.unpriced:
        lines.append(f"{len(t.unpriced)} unpriced row(s), not in the totals above:")
        for r in t.unpriced:
            lines.append(f"  line {r['line']}: [{r['status']}] {r['item']} (need {r['qty_needed']}{per(r)}, "
                         f"own {r['qty_owned']}, stage {r['stage']})")
    if t.decide:
        lines.append(f"{len(t.decide)} decide row(s), not decided yet and not in the totals above:")
        for r in t.decide:
            price = f", {r['unit_price']} {r['currency']} each" if r["unit_price"].strip() else ""
            lines.append(f"  line {r['line']}: {r['item']} (need {r['qty_needed']}{per(r)}{price}, stage {r['stage']})")
    return "\n".join(lines)


def positive_int(text):
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError(f"{text} isn't a head count of 1 or more")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", default=DEFAULT_CSV, help="the BOM CSV (default: bom/bom.csv)")
    ap.add_argument("--check", action="store_true", help="only check the CSV; print no totals")
    ap.add_argument("--heads", type=positive_int, default=DEFAULT_HEADS,
                    help=f"toolheads to cost: multiplies '{PER_HEAD}' rows' qty_needed (default {DEFAULT_HEADS})")
    args = ap.parse_args(argv)
    rows, errors = load(args.csv, args.heads)
    if errors:
        print("\n".join(errors))
        print(f"bom-check: FAILED ({len(errors)} problem(s))")
        return 1
    if args.check:
        print(f"{len(rows)} rows checked")
        print("bom-check: OK")
        return 0
    print(report(compute(rows, args.heads), args.csv))
    print("bom-totals: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
