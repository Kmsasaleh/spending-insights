import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.models import Transaction

REQUIRED_COLUMNS = {"Date", "Description", "Amount"}


def parse_amex_csv(content: str) -> tuple[list[Transaction], list[str]]:
    """Parse an Amex CSV export into Transactions.

    Returns (transactions, errors). Bad rows are skipped and reported,
    so one broken line doesn't block the whole upload.
    """
    content = content.lstrip("\ufeff")  # remove invisible marker some exports add
    reader = csv.DictReader(io.StringIO(content))

    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Not an Amex CSV: missing columns {sorted(missing)}")

    transactions: list[Transaction] = []
    errors: list[str] = []

    for line_num, row in enumerate(reader, start=2):  # line 1 is the header
        try:
            posted = datetime.strptime(row["Date"].strip(), "%d %b %Y").date()
            raw_amount = row["Amount"].strip().replace(",", "").replace("$", "")
            # Amex: purchases are positive. Our convention: money out is negative.
            amount = -Decimal(raw_amount)
            transactions.append(
                Transaction(posted_date=posted, description=row["Description"], amount=amount)
            )
        except (ValueError, InvalidOperation, ValidationError, AttributeError) as e:
            errors.append(f"Line {line_num}: {e}")

    return transactions, errors