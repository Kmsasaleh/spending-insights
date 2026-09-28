import os
import re
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


def lookup_memory(keys: list[str]) -> dict[str, CategorizationResult]:
    """Return remembered categories for any keys we've seen before."""
    unique = list({k for k in keys if k})
    found: dict[str, CategorizationResult] = {}
    for start in range(0, len(unique), 100):  # chunks keep each request small
        rows = (
            get_client()
            .table("merchant_memory")
            .select("description_key, merchant, category")
            .in_("description_key", unique[start:start + 100])
            .execute()
            .data
        )
        for r in rows:
            found[r["description_key"]] = CategorizationResult(
                merchant=r["merchant"], category=r["category"], confidence=1.0
            )
    return found


def save_memory(entries: dict[str, CategorizationResult]) -> None:
    """Remember new merchants. Never overwrites an existing entry,
    so a category you corrected by hand is never replaced by the AI."""
    rows = [
        {"description_key": k, "merchant": r.merchant, "category": r.category.value, "source": "llm"}
        for k, r in entries.items()
    ]
    if rows:
        get_client().table("merchant_memory").upsert(
            rows, on_conflict="description_key", ignore_duplicates=True
        ).execute()


def save_transactions(rows: list[dict]) -> None:
    if rows:
        get_client().table("transactions").insert(rows).execute()


def list_transactions(limit: int = 1000) -> list[dict]:
    return (
        get_client()
        .table("transactions")
        .select("*")
        .order("posted_date", desc=True)
        .limit(limit)
        .execute()
        .data
    )