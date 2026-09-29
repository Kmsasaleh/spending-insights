import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from postgrest.exceptions import APIError as DatabaseError
from pydantic import BaseModel

from app.amex_parser import parse_amex_csv
from app.auth import current_user_id
from app.db import (
    description_key,
    get_transaction,
    list_transactions,
    save_transactions,
    save_user_correction,
    update_transaction_category,
)
from app.models import Category
from app.service import categorize_with_memory

# Load .env from the project root when running locally.
# On Render there's no .env file; keys come from the dashboard instead.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MAX_UPLOAD_BYTES = 1_000_000  # 1 MB is far more than a year of statements
MAX_TRANSACTIONS = 500        # caps API cost per upload

app = FastAPI(title="Spending Insights API")

# Only these websites may call the API from a browser.
# Locally that's the Next.js dev server; on deploy we add the Vercel URL.
ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


class CategorizedTransaction(BaseModel):
    posted_date: date
    description: str
    amount: Decimal
    merchant: str | None
    category: Category | None
    confidence: float | None
    source: str  # "memory", "llm", or "user"


class CategorizeResponse(BaseModel):
    transactions: list[CategorizedTransaction]
    parse_errors: list[str]
    uncategorized: int
    sent_to_claude: int
    from_memory: int


class StoredTransaction(BaseModel):
    id: int
    posted_date: date
    description: str
    amount: Decimal
    merchant: str | None
    category: Category | None
    confidence: float | None
    source: str


class CategoryUpdate(BaseModel):
    category: Category


@app.get("/health")
def health():
    """Simple check that the server is running. Render will use this. No login needed."""
    return {"status": "ok"}


@app.post("/categorize", response_model=CategorizeResponse)
def categorize_statement(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
):
    """Upload an Amex CSV: categorize every transaction and save it for this user."""
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
        results, sources, sent_to_claude = categorize_with_memory(user_id, transactions)
    except anthropic.APIError:
        raise HTTPException(502, "Categorization service unavailable, please try again") from None
    except DatabaseError:
        raise HTTPException(502, "Database unavailable, please try again") from None

    rows = [
        CategorizedTransaction(
            posted_date=t.posted_date,
            description=t.description,
            amount=t.amount,
            merchant=r.merchant if r else None,
            category=r.category if r else None,
            confidence=r.confidence if r else None,
            source=s,
        )
        for t, r, s in zip(transactions, results, sources)
    ]

    try:
        save_transactions(user_id, [row.model_dump(mode="json") for row in rows])
    except DatabaseError:
        raise HTTPException(502, "Could not save transactions, please try again") from None

    return CategorizeResponse(
        transactions=rows,
        parse_errors=parse_errors,
        uncategorized=sum(r is None for r in results),
        sent_to_claude=sent_to_claude,
        from_memory=sources.count("memory"),
    )


@app.get("/transactions", response_model=list[StoredTransaction])
def get_transactions(user_id: str = Depends(current_user_id)):
    """Return this user's saved transactions, newest first."""
    try:
        return list_transactions(user_id)
    except DatabaseError:
        raise HTTPException(502, "Database unavailable, please try again") from None


@app.patch("/transactions/{transaction_id}", response_model=StoredTransaction)
def change_category(
    transaction_id: int,
    update: CategoryUpdate,
    user_id: str = Depends(current_user_id),
):
    """Correct one of this user's transactions and teach their merchant memory."""
    try:
        txn = get_transaction(user_id, transaction_id)
        if txn is None:
            raise HTTPException(404, "Transaction not found")

        update_transaction_category(user_id, transaction_id, update.category.value)

        key = description_key(txn["description"])
        if key:
            save_user_correction(
                user_id, key, txn["merchant"] or txn["description"], update.category.value
            )

        return get_transaction(user_id, transaction_id)
    except DatabaseError:
        raise HTTPException(502, "Database unavailable, please try again") from None