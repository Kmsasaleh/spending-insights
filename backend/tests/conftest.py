import pytest

from app.models import Transaction


@pytest.fixture
def make_txns():
    """Build Transaction objects from descriptions, for tests that don't care about dates or amounts."""
    def _make(*descriptions, amount="-5.00"):
        return [Transaction(posted_date="2026-08-01", description=d, amount=amount) for d in descriptions]
    return _make