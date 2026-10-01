"""Measure categorization accuracy on your hand-labelled transactions.

Usage (from the backend folder):
    python -m eval.run_eval            # reuses saved Claude answers if nothing changed
    python -m eval.run_eval --refresh  # always ask Claude again
"""
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from app.categorizer import MODEL, SYSTEM_PROMPT, categorize  # noqa: E402
from app.csv_parser import _pick_date_format  # noqa: E402
from app.db import description_key  # noqa: E402
from app.models import Category, Transaction  # noqa: E402
from app.service import REMEMBER_THRESHOLD  # noqa: E402

EVAL_DIR = Path(__file__).parent
PRIVATE = EVAL_DIR / "private"           # git-ignored: real transactions
LABELS = PRIVATE / "to_label.csv"
CACHE = PRIVATE / "llm_predictions.json"
RESULTS = EVAL_DIR / "RESULTS.md"         # committed: aggregate numbers only
VALID = {c.value for c in Category}
TEST_MONTHS = 3  # the most recent months are held out for the final number
# Baseline: simple keyword rules, checked in order. First match wins.
RULES = [
    ("Transfers", ["PAYMENT RECEIVED", "PAYMENT - THANK"]),
    ("Subscriptions", ["NETFLIX", "SPOTIFY", "APPLE.COM/BILL", "OPENAI", "CHATGPT",
                       "PRIME MEMBER", "LINKEDIN", "DISNEY", "YOUTUBE"]),
    ("Dining", ["TIM HORTONS", "STARBUCKS", "MCDONALD", "UBER EATS", "DOORDASH", "SKIPTHEDISHES",
                "PIZZA", "BURGER", "CAFE", "COFFEE", "SUBWAY", "A&W", "KFC", "CHICK-FIL-A",
                "GRILL", "SUSHI", "RESTAURANT", "TST*", "BAKERY", "CHIPOTLE"]),
    ("Groceries", ["NOFRILLS", "NO FRILLS", "FORTINOS", "LOBLAWS", "SOBEYS", "FRESHCO",
                   "FOOD BASICS", "COSTCO", "INSTACART", "MARKET"]),
    ("Transport", ["PRESTO", "UBERTRIP", "UBER CANADA", "LYFT", "ESSO", "SHELL", "PETRO",
                   "PIONEER", "PARKING", "GO TRANSIT", "NYCT"]),
    ("Bills & Utilities", ["ROGERS", "BELL MOBILITY", "TELUS", "FIDO", "KOODO", "VIRGIN",
                           "HYDRO", "ENBRIDGE", "MEMBERSHIP FEE", "INSURANCE"]),
    ("Health", ["SHOPPERS DRUG", "PHARMA", "REXALL", "GOODLIFE", "FIT", "BARBER", "DENTAL", "CLINIC"]),
    ("Entertainment", ["CINEPLEX", "LOUNGE", "TICKETMASTER", "BILLIARD"]),
    ("Travel", ["AIR CANADA", "WESTJET", "HOTEL", "AIRBNB", "EXPEDIA", "ESTA"]),
    ("Shopping", ["AMZN", "AMAZON", "WAL-MART", "WALMART", "WINNERS", "INDIGO", "BEST BUY",
                  "CANADIAN TIRE", "DOLLARAMA", "IKEA"]),
]


@dataclass
class Row:
    id: str
    posted: date
    description: str
    amount: Decimal
    true: str

    @property
    def month(self) -> str:
        return self.posted.strftime("%Y-%m")


def load_rows() -> list[Row]:
    with LABELS.open(encoding="utf-8-sig", newline="") as f:
        raw = [r for r in csv.DictReader(f) if (r.get("true_category") or "").strip()]
    if not raw:
        sys.exit("No labelled rows found in to_label.csv")
    unknown = sorted({r["true_category"].strip() for r in raw} - VALID)
    if unknown:
        sys.exit(f"Unknown labels, fix their spelling in to_label.csv: {unknown}")
    fmt = _pick_date_format([r["posted_date"].strip() for r in raw])
    if fmt is None:
        sys.exit("Couldn't read the posted_date column")
    rows = [
        Row(
            id=r["id"].strip(),
            posted=datetime.strptime(r["posted_date"].strip(), fmt).date(),
            description=r["description"].strip(),
            amount=Decimal(r["amount"].strip()),
            true=r["true_category"].strip(),
        )
        for r in raw
    ]
    return sorted(rows, key=lambda r: (r.posted, int(r.id)))


def rules_predict(description: str) -> str:
    text = description.upper()
    for category, keywords in RULES:
        if any(k in text for k in keywords):
            return category
    return "Other"


def llm_predictions(rows: list[Row], refresh: bool) -> dict[str, dict | None]:
    """Claude's answer for every row. Saved, so re-running costs nothing unless the prompt changes."""
    prompt_id = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12]
    ids = {r.id for r in rows}
    if CACHE.exists() and not refresh:
        cached = json.loads(CACHE.read_text())
        if (cached.get("model"), cached.get("prompt")) == (MODEL, prompt_id) and set(cached["predictions"]) == ids:
            print("Using saved Claude answers (same model, prompt and labels).\n")
            return cached["predictions"]
    print(f"Asking Claude ({MODEL}) to categorize {len(rows)} transactions...\n")
    txns = [Transaction(posted_date=r.posted, description=r.description, amount=r.amount) for r in rows]
    results = categorize(txns)
    preds = {
        r.id: None if res is None else {"category": res.category.value, "confidence": res.confidence}
        for r, res in zip(rows, results)
    }
    CACHE.write_text(json.dumps({"model": MODEL, "prompt": prompt_id, "predictions": preds}, indent=1))
    return preds


def simulate_memory(rows: list[Row], llm: dict, fixes: bool) -> tuple[dict, int]:
    """Replay the history month by month, as the app would see it: one upload per month.

    fixes=True also assumes you correct every mistake after each upload (the app's
    category dropdown), which teaches memory. That's the best case for memory.
    """
    memory: dict[str, str] = {}
    preds: dict[str, str | None] = {}
    sent = 0
    for month in sorted({r.month for r in rows}):
        batch = [r for r in rows if r.month == month]
        asked: dict[str, tuple[str | None, float]] = {}  # repeats in one upload are sent once
        for r in batch:
            key = description_key(r.description)
            if key in memory:
                preds[r.id] = memory[key]
            elif key and key in asked:
                preds[r.id] = asked[key][0]
            else:
                p = llm[r.id]
                preds[r.id] = p["category"] if p else None
                sent += 1
                if key:
                    asked[key] = (preds[r.id], p["confidence"] if p else 0.0)
        # After the upload: confident answers are remembered automatically...
        for key, (category, confidence) in asked.items():
            if category and confidence >= REMEMBER_THRESHOLD and key not in memory:
                memory[key] = category
        # ...and corrections override them.
        if fixes:
            for r in batch:
                key = description_key(r.description)
                if key and preds[r.id] != r.true:
                    memory[key] = r.true
    return preds, sent


def accuracy(rows: list[Row], preds: dict) -> float:
    return sum(preds[r.id] == r.true for r in rows) / len(rows)


def main() -> None:
    rows = load_rows()
    n = len(rows)
    llm = llm_predictions(rows, refresh="--refresh" in sys.argv)
    claude = {k: (v["category"] if v else None) for k, v in llm.items()}
    rules = {r.id: rules_predict(r.description) for r in rows}
    memory, memory_sent = simulate_memory(rows, llm, fixes=False)
    fixed, fixed_sent = simulate_memory(rows, llm, fixes=True)

    # Hold out the most recent months. Prompt changes are decided by looking at
    # the dev months only; the test months are only used to report the final number.
    months = sorted({r.month for r in rows})
    test_months = set(months[-TEST_MONTHS:])
    dev = [r for r in rows if r.month not in test_months]
    test = [r for r in rows if r.month in test_months]

    out: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        out.append(line)

    say("# Evaluation results")
    say()
    say(f"- **Labelled transactions:** {n} ({rows[0].posted} to {rows[-1].posted}, {len(months)} months)")
    say(f"- **Dev set** (used to improve the prompt): {len(dev)} transactions, "
        f"first {len(months) - TEST_MONTHS} months")
    say(f"- **Test set** (held out, only for reporting): {len(test)} transactions, last {TEST_MONTHS} months")
    say(f"- **Model:** `{MODEL}`")
    say(f"- **Run:** {date.today()}")
    say()
    say("| Method | Dev accuracy | Test accuracy | Sent to Claude (all months) |")
    say("|---|---|---|---|")
    for name, preds, sent in [
        ("Keyword rules (baseline)", rules, 0),
        ("Claude", claude, n),
        ("Claude + merchant memory", memory, memory_sent),
        ("Claude + memory + monthly corrections", fixed, fixed_sent),
    ]:
        say(f"| {name} | {accuracy(dev, preds):.1%} | {accuracy(test, preds):.1%} | {sent} ({sent / n:.0%}) |")

    say()
    say("## Claude accuracy by category (dev set)")
    say()
    say("| Category | Transactions | Accuracy |")
    say("|---|---|---|")
    for category, count in Counter(r.true for r in dev).most_common():
        group = [r for r in dev if r.true == category]
        say(f"| {category} | {count} | {accuracy(group, claude):.0%} |")

    say()
    say("## Most common mistakes on the dev set (true → predicted)")
    say()
    mistakes = Counter((r.true, claude[r.id]) for r in dev if claude[r.id] != r.true)
    for (true, predicted), count in mistakes.most_common(8):
        say(f"- {true} → {predicted}: {count}")

    say()
    say("## Is Claude's confidence meaningful? (dev set)")
    say()
    confident = [r for r in dev if llm[r.id] and llm[r.id]["confidence"] >= REMEMBER_THRESHOLD]
    unsure = [r for r in dev if r not in confident]
    if confident:
        say(f"- Confidence ≥ {REMEMBER_THRESHOLD}: {len(confident)} transactions, {accuracy(confident, claude):.0%} correct")
    if unsure:
        say(f"- Confidence < {REMEMBER_THRESHOLD}: {len(unsure)} transactions, {accuracy(unsure, claude):.0%} correct")

    RESULTS.write_text("\n".join(out) + "\n")
    print(f"\nSaved summary to {RESULTS} (aggregate numbers only, safe to commit).")

    # Only dev-set mistakes are shown, so prompt changes are never based on the test months.
    print("\nClaude's mistakes on the dev set (private, not saved):")
    for r in [r for r in dev if claude[r.id] != r.true]:
        print(f"  {r.description[:45]:<45} true={r.true:<18} claude={claude[r.id]}")


if __name__ == "__main__":
    main()