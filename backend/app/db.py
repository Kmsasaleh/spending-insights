import os
import re
from datetime import datetime, timezone
from functools import lru_cache

from supabase import Client, create_client

from app.models import CategorizationResult


@lru_cache
def get_client() -> Client:
    """Create the Supabase client once and reuse it for every request."""
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def description_key(description: str) -> str:
    """Normalize a description so the same merchant always gets the same key.

    'SQ *TIM HORTONS #4521' and 'SQ *TIM HORTONS #1187' -> 'SQ TIM HORTONS'
    """
    letters_only = re.sub(r"[^A-Z ]", " ", description.upper())
    return " ".join(letters_only.split())


# Every function below takes user_id and filters by it.
# The secret key bypasses database security, so this filtering is what keeps
# each user's data private. It must never be skipped.


def lookup_memory(user_id: str, keys: list[str]) -> dict[str, CategorizationResult]:
    """Return this user's remembered categories for any keys seen before."""
    unique = list({k for k in keys if k})
    found: dict[str, CategorizationResult] = {}
    for start in range(0, len(unique), 100):  # chunks keep each request small
        rows = (
            get_client()
            .table("merchant_memory")
            .select("description_key, merchant, category")
            .eq("user_id", user_id)
            .in_("description_key", unique[start:start + 100])
            .execute()
            .data
        )
        for r in rows:
            found[r["description_key"]] = CategorizationResult(
                merchant=r["merchant"], category=r["category"], confidence=1.0
            )
    return found


def save_memory(user_id: str, entries: dict[str, CategorizationResult]) -> None:
    """Remember new merchants. Never overwrites an existing entry,
    so a category the user corrected is never replaced by the AI."""
    rows = [
        {
            "user_id": user_id,
            "description_key": k,
            "merchant": r.merchant,
            "category": r.category.value,
            "source": "llm",
        }
        for k, r in entries.items()
    ]
    if rows:
        get_client().table("merchant_memory").upsert(
            rows, on_conflict="user_id,description_key", ignore_duplicates=True
        ).execute()


def save_user_correction(user_id: str, key: str, merchant: str, category: str) -> None:
    """A human correction always wins: overwrite whatever memory had for this merchant."""
    get_client().table("merchant_memory").upsert(
        {
            "user_id": user_id,
            "description_key": key,
            "merchant": merchant,
            "category": category,
            "source": "user",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id,description_key",
    ).execute()


def save_transactions(user_id: str, rows: list[dict]) -> None:
    if rows:
        get_client().table("transactions").insert(
            [{**row, "user_id": user_id} for row in rows]
        ).execute()


def list_transactions(user_id: str, limit: int = 1000) -> list[dict]:
    return (
        get_client()
        .table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("posted_date", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def get_transaction(user_id: str, transaction_id: int) -> dict | None:
    rows = (
        get_client()
        .table("transactions")
        .select("*")
        .eq("id", transaction_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def update_transaction_category(user_id: str, transaction_id: int, category: str) -> None:
    get_client().table("transactions").update(
        {"category": category, "source": "user", "confidence": 1.0}
    ).eq("id", transaction_id).eq("user_id", user_id).execute()