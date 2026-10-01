"""Create a blank labelling sheet from one or more bank CSV exports.

Usage (from the backend folder):
    python -m eval.make_label_sheet ~/Downloads/activity-6mo.csv [more.csv ...]
"""
import csv
import sys
from pathlib import Path

from app.csv_parser import parse_statement_csv

OUT = Path(__file__).parent / "private" / "to_label.csv"


def main(paths: list[str]) -> None:
    rows, seen = [], set()
    for p in paths:
        content = Path(p).expanduser().read_text(encoding="utf-8-sig")
        txns, errors = parse_statement_csv(content)
        for e in errors:
            print(f"{p}: {e}")
        for t in txns:
            key = (t.posted_date, t.description, t.amount)
            if key in seen:  # same transaction appearing in two overlapping exports
                continue
            seen.add(key)
            rows.append(t)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "posted_date", "description", "amount", "true_category"])
        for i, t in enumerate(sorted(rows, key=lambda t: t.posted_date), start=1):
            writer.writerow([i, t.posted_date, t.description, t.amount, ""])
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])