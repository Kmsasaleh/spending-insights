from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Category(StrEnum):
    """The fixed set of spending categories. The LLM must pick one of these."""
    GROCERIES = "Groceries"
    DINING = "Dining"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    SUBSCRIPTIONS = "Subscriptions"
    BILLS = "Bills & Utilities"
    ENTERTAINMENT = "Entertainment"
    HEALTH = "Health"
    TRAVEL = "Travel"
    INCOME = "Income"
    TRANSFERS = "Transfers"
    OTHER = "Other"


class Transaction(BaseModel):
    """One row from a bank statement, after parsing and cleaning."""
    posted_date: date
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(decimal_places=2)  # negative = money out, positive = money in
    category: Category | None = None           # None until categorized

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str) -> str:
        # Collapse messy whitespace: "  SQ *TIM   HORTONS " -> "SQ *TIM HORTONS"
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("description cannot be blank")
        return cleaned


class CategorizationResult(BaseModel):
    """What we require the LLM to return for each transaction."""
    merchant: str = Field(min_length=1, max_length=100)  # cleaned name, e.g. "Tim Hortons"
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)