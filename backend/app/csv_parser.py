import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.models import Transaction

# Header names banks commonly use, in priority order (best match first).
DATE_NAMES = ["date", "transaction date", "trans date", "trans. date",
              "posted date", "posting date", "date posted"]
DESCRIPTION_NAMES = ["description", "description 1", "merchant", "payee", "details",
                     "transaction details", "transaction description", "memo", "name"]
AMOUNT_NAMES = ["amount", "transaction amount", "amount (cad)", "cad$", "cad"]
DEBIT_NAMES = ["debit", "debits", "withdrawal", "withdrawals", "money out",
               "debit amount", "paid out"]
CREDIT_NAMES = ["credit", "credits", "deposit", "deposits", "money in",
                "credit amount", "paid in"]

# Month/day comes before day/month: when a date like 08/03 could be either,
# we assume the North American order.
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y",
                "%d %b %Y", "%d-%b-%Y", "%b %d, %Y", "%b %d %Y", "%Y%m%d"]


def _clean(cell: str | None) -> str:
    return (cell or "").strip().strip('"').strip()


def _normalize_date_text(text: str) -> str:
    # "03 Sept. 2026" -> "03 Sep 2026"
    return text.strip().replace(".", "").replace("Sept", "Sep")


def _is_date(text: str, fmt: str) -> bool:
    try:
        datetime.strptime(_normalize_date_text(text), fmt)
        return True
    except ValueError:
        return False


def _parse_amount(text: str) -> Decimal | None:
    """'$1,234.56' -> 1234.56, '(12.00)' -> -12.00, '12.00-' -> -12.00, '' -> None."""
    t = text.upper().replace("CAD", "").replace("$", "").replace(",", "").replace(" ", "")
    if not t:
        return None
    negative = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if t.endswith("-"):
        negative, t = True, t[:-1]
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return -value if negative else value


def _pick_date_format(values: list[str]) -> str | None:
    """Return the format that parses the most values (at least 80% of them)."""
    samples = [v for v in values if v]
    if not samples:
        return None
    best, best_hits = None, 0
    for fmt in DATE_FORMATS:
        hits = sum(_is_date(s, fmt) for s in samples)
        if hits > best_hits:
            best, best_hits = fmt, hits
    return best if best_hits >= 0.8 * len(samples) else None


def _mostly_amounts(values: list[str]) -> bool:
    filled = [v for v in values if v]
    return bool(filled) and sum(_parse_amount(v) is not None for v in filled) >= 0.8 * len(filled)


def _looks_like_header(row: list[str]) -> bool:
    """A header row contains no dates and no amounts, just labels."""
    for raw in row:
        cell = _clean(raw)
        if cell and (_parse_amount(cell) is not None
                     or any(_is_date(cell, f) for f in DATE_FORMATS)):
            return False
    return True


def _find(headers: list[str], names: list[str]) -> int | None:
    for name in names:
        if name in headers:
            return headers.index(name)
    return None


def parse_statement_csv(content: str) -> tuple[list[Transaction], list[str]]:
    """Parse a CSV export from any bank or card into Transactions.

    Money out is always negative and money in positive, whatever the bank's own convention.
    Returns (transactions, errors). Bad rows are skipped and reported.
    """
    content = content.lstrip("\ufeff")  # remove invisible marker some exports add

    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel  # plain commas
    rows = [r for r in csv.reader(io.StringIO(content), dialect) if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("The file is empty")

    has_header = _looks_like_header(rows[0])
    data = rows[1:] if has_header else rows
    if not data:
        raise ValueError("No transaction rows found")

    width = max(len(r) for r in data)
    columns = [[_clean(r[i]) if i < len(r) else "" for r in data] for i in range(width)]

    # 1. Use the header names when there are any.
    headers = [_clean(h).lower() for h in rows[0]] if has_header else []
    date_col = _find(headers, DATE_NAMES)
    desc_col = _find(headers, DESCRIPTION_NAMES)
    amount_col = _find(headers, AMOUNT_NAMES)
    debit_col = _find(headers, DEBIT_NAMES)
    credit_col = _find(headers, CREDIT_NAMES)

    # 2. Fill in anything still unknown by looking at the data itself.
    if date_col is None:
        date_col = next((i for i, col in enumerate(columns) if _pick_date_format(col)), None)
    numeric = [i for i, col in enumerate(columns) if i != date_col and _mostly_amounts(col)]
    if amount_col is None and debit_col is None and credit_col is None:
        if len(numeric) == 1:
            amount_col = numeric[0]
        elif len(numeric) >= 2:
            # No header: assume debit, credit (any later number column is usually the balance).
            debit_col, credit_col = numeric[0], numeric[1]
    if desc_col is None:
        used = {date_col, amount_col, debit_col, credit_col, *numeric}
        text_cols = [i for i in range(width) if i not in used]
        desc_col = max(text_cols, key=lambda i: sum(len(v) for v in columns[i]), default=None)

    if date_col is None or desc_col is None or (
        amount_col is None and debit_col is None and credit_col is None
    ):
        found = ", ".join(h for h in headers if h) or "no header row"
        raise ValueError(
            f"Couldn't find the date, description and amount columns (columns found: {found})"
        )

    date_fmt = _pick_date_format(columns[date_col])
    if date_fmt is None:
        raise ValueError("Couldn't recognize the date format in this file")

    # 3. Sign convention for a single Amount column: if most amounts are positive,
    #    purchases are shown as positive (typical of credit cards), so flip them.
    flip = False
    if amount_col is not None:
        amounts = [a for a in (_parse_amount(v) for v in columns[amount_col]) if a is not None]
        flip = sum(a > 0 for a in amounts) > sum(a < 0 for a in amounts)

    transactions: list[Transaction] = []
    errors: list[str] = []
    for n, row in enumerate(data, start=1):

        def cell(i: int | None) -> str:
            return _clean(row[i]) if i is not None and i < len(row) else ""

        try:
            posted = datetime.strptime(_normalize_date_text(cell(date_col)), date_fmt).date()
            if amount_col is not None:
                amount = _parse_amount(cell(amount_col))
                if amount is None:
                    raise ValueError("missing amount")
                if flip:
                    amount = -amount
            else:
                debit = _parse_amount(cell(debit_col)) or Decimal("0")
                credit = _parse_amount(cell(credit_col)) or Decimal("0")
                amount = abs(credit) - abs(debit)
            transactions.append(
                Transaction(posted_date=posted, description=cell(desc_col), amount=amount)
            )
        except (ValueError, ValidationError) as e:
            errors.append(f"Row {n}: {e}")

    return transactions, errors