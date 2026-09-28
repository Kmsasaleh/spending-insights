from datetime import date
from decimal import Decimal
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.amex_parser import parse_amex_csv
from app.categorizer import categorize
from app.models import Category

# Load .env from the project root (spending-insights/.env) when running locally.
# On Render there's no .env file; keys come from the dashboard instead, and this does nothing.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MAX_UPLOAD_BYTES = 1_000_000  # 1 MB is far more than a year of statements
MAX_TRANSACTIONS = 500        # caps API cost per upload

app = FastAPI(title="Spending Insights API")


class CategorizedTransaction(BaseModel):
    posted_date: date
    description: str
    amount: Decimal
    merchant: str | None
    category: Category | None
    confidence: float | None


class CategorizeResponse(BaseModel):
    transactions: list[CategorizedTransaction]
    parse_errors: list[str]
    uncategorized: int


@app.get("/health")
def health():
    """Simple check that the server is running. Render will use this."""
    return {"status": "ok"}


@app.post("/categorize", response_model=CategorizeResponse)
def categorize_statement(file: UploadFile = File(...)):
    """Upload an Amex CSV and get back every transaction with its category."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")

    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 1 MB)")

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File is not valid text") from None

    try:
        transactions, parse_errors = parse_amex_csv(content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None

    if not transactions:
        raise HTTPException(400, "No valid transactions found in file")
    if len(transactions) > MAX_TRANSACTIONS:
        raise HTTPException(400, f"Too many transactions (max {MAX_TRANSACTIONS} per upload)")

    try:
        results = categorize(transactions)
    except anthropic.APIError:
        raise HTTPException(502, "Categorization service unavailable, please try again") from None

    rows = [
        CategorizedTransaction(
            posted_date=t.posted_date,
            description=t.description,
            amount=t.amount,
            merchant=r.merchant if r else None,
            category=r.category if r else None,
            confidence=r.confidence if r else None,
        )
        for t, r in zip(transactions, results)
    ]
    return CategorizeResponse(
        transactions=rows,
        parse_errors=parse_errors,
        uncategorized=sum(r is None for r in results),
    )