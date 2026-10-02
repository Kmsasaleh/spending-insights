from decimal import Decimal
from pathlib import Path

import pytest

from app.csv_parser import _parse_amount, parse_statement_csv

DEMO_FILE = Path(__file__).resolve().parents[1] / "demo" / "demo-activity.csv"


def test_amex_export_purchases_become_negative():
    txns, errors = parse_statement_csv(DEMO_FILE.read_text())
    assert errors == []
    assert len(txns) == 36
    coffee = next(t for t in txns if "TIM HORTONS" in t.description)
    assert coffee.amount == Decimal("-4.87")
    payment = next(t for t in txns if "PAYMENT RECEIVED" in t.description)
    assert payment.amount > 0


@pytest.mark.parametrize(
    "content",
    [
        # No header; debit, credit and balance columns
        "08/03/2026,TIM HORTONS #1234,4.87,,1203.50\n08/04/2026,PAYROLL DEPOSIT,,1500.00,2703.50\n",
        # Withdrawals / Deposits columns
        "Posted Date,Description,Withdrawals,Deposits\n"
        "2026-08-03,TIM HORTONS #1234,4.87,\n2026-08-04,PAYROLL DEPOSIT,,1500.00\n",
        # Semicolons, one signed Amount column
        "Date;Payee;Amount\n2026-08-03;TIM HORTONS #1234;-4.87\n2026-08-04;PAYROLL DEPOSIT;1500.00\n",
    ],
)
def test_different_bank_formats_give_the_same_result(content):
    txns, errors = parse_statement_csv(content)
    assert errors == []
    assert [t.amount for t in txns] == [Decimal("-4.87"), Decimal("1500.00")]
    assert str(txns[0].posted_date) == "2026-08-03"
    assert txns[0].description == "TIM HORTONS #1234"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("$1,234.56", Decimal("1234.56")),
        ("(12.00)", Decimal("-12.00")),
        ("12.00-", Decimal("-12.00")),
        ("", None),
        ("abc", None),
    ],
)
def test_amount_formats(text, expected):
    assert _parse_amount(text) == expected


def test_a_bad_row_is_reported_without_losing_the_others():
    content = (
        "Date,Description,Amount\n"
        "2026-08-01,A,-1.00\n2026-08-02,B,-2.00\nnot a date,BROKEN,-3.00\n"
        "2026-08-04,C,-4.00\n2026-08-05,D,-5.00\n2026-08-06,E,-6.00\n"
    )
    txns, errors = parse_statement_csv(content)
    assert len(txns) == 5
    assert len(errors) == 1


def test_an_unrecognizable_file_raises_a_clear_error():
    with pytest.raises(ValueError):
        parse_statement_csv("hello,world\nfoo,bar\n")