import pytest
from pydantic import ValidationError

from app.models import CategorizationResult, Transaction


def test_description_whitespace_is_cleaned():
    t = Transaction(posted_date="2026-08-01", description="  SQ *TIM   HORTONS ", amount="-4.25")
    assert t.description == "SQ *TIM HORTONS"


def test_amount_rejects_fractions_of_a_cent():
    with pytest.raises(ValidationError):
        Transaction(posted_date="2026-08-01", description="X", amount="4.255")


def test_ai_output_must_use_a_known_category():
    with pytest.raises(ValidationError):
        CategorizationResult(merchant="Tim Hortons", category="Coffee", confidence=0.9)


def test_ai_confidence_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        CategorizationResult(merchant="Tim Hortons", category="Dining", confidence=1.5)