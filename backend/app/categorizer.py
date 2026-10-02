import re

from anthropic import Anthropic
from pydantic import ValidationError

from app.models import Category, CategorizationResult, Transaction

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 25

SYSTEM_PROMPT = f"""You categorize personal credit card and bank transactions.
For each transaction, return:
- id: the id shown in [brackets], copied exactly
- echo: the first 15 characters of that transaction's description, copied exactly
- merchant: a clean, readable merchant name (e.g. "SQ *TIM HORTONS #4521" -> "Tim Hortons")
- category: exactly one of: {", ".join(c.value for c in Category)}
- confidence: 0.0 to 1.0, how sure you are about the category

Category definitions:
- Groceries: supermarkets, grocery delivery, convenience and campus food stores.
- Dining: restaurants, cafés, coffee shops, bakeries, juice and smoothie bars, bars, food delivery apps.
- Transport: transit fares and fare-card top-ups, fuel, parking (including parking apps), rideshare rides, car costs.
- Shopping: retail and online stores, including drugstore chains and gift cards bought at a store.
- Health: prescriptions, medical and dental care, gyms, barbers, hair salons and personal care services.
- Subscriptions: recurring digital services and memberships (streaming, software, apps, shopping memberships).
- Bills & Utilities: phone, internet, electricity, insurance, bank and card fees.
- Entertainment: movies, events and event tickets, games, outings.
- Travel: flights, hotels, travel documents, rental cars.
- Income: pay and money received as income.
- Transfers: payments made to the credit card itself and moves between your own accounts.
- Other: only when none of the categories above fits.

Rules:
- Return exactly one result per transaction. Never skip, merge or renumber transactions.
- Amounts are negative for purchases and positive for payments or refunds.
- Payments to the card (e.g. "PAYMENT RECEIVED") are always Transfers, never a bill.
- A refund gets the category the original purchase would have had.
- Food delivery is Dining; rideshare rides are Transport, even when travelling.
- A name containing "wellness" or "health" can still be a café: judge by what is sold.
- If you genuinely cannot tell, use Other with low confidence."""

# A "tool" forces Claude to reply in this exact JSON shape instead of free text.
TOOL = {
    "name": "record_categorizations",
    "description": "Record the categorization for every transaction.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "echo": {"type": "string"},
                        "merchant": {"type": "string"},
                        "category": {"type": "string", "enum": [c.value for c in Category]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["id", "echo", "merchant", "category", "confidence"],
                },
            }
        },
        "required": ["results"],
    },
}


def _signature(text: str) -> str:
    """First 6 letters/digits, ignoring case, spaces and symbols: used to match an answer to its row."""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())[:6]


def _ask_claude(transactions: list[Transaction]) -> dict[int, CategorizationResult]:
    """One API call. Returns {row index: result} for answers that pass every check."""
    ids = [f"T{i + 1}" for i in range(len(transactions))]
    # Only the description and amount are sent: no dates, names, or account info.
    lines = [f'[{tid}] "{t.description}" | {t.amount}' for tid, t in zip(ids, transactions)]

    response = Anthropic().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_categorizations"},
        messages=[{"role": "user", "content": "Categorize these transactions:\n" + "\n".join(lines)}],
    )
    tool_input = next(block.input for block in response.content if block.type == "tool_use")

    found: dict[int, CategorizationResult] = {}
    for item in tool_input.get("results", []):
        try:
            i = ids.index(item["id"])
        except (KeyError, ValueError, TypeError):
            continue
        if i in found:
            continue
        # Guard against answers shifted onto the wrong row: the echo must match this row.
        if _signature(item.get("echo", "")) != _signature(transactions[i].description):
            continue
        try:
            found[i] = CategorizationResult(
                merchant=item["merchant"],
                category=item["category"],
                confidence=item["confidence"],
            )
        except (KeyError, TypeError, ValidationError):
            continue  # never trust unvalidated output
    return found


def categorize_batch(transactions: list[Transaction]) -> list[CategorizationResult | None]:
    """Categorize up to BATCH_SIZE transactions, retrying once for any rows that failed checks.

    Returns one result per transaction, in the same order. None means "needs review".
    """
    results: list[CategorizationResult | None] = [None] * len(transactions)
    for i, result in _ask_claude(transactions).items():
        results[i] = result

    missing = [i for i, r in enumerate(results) if r is None]
    if missing:
        retry = _ask_claude([transactions[i] for i in missing])
        for j, result in retry.items():
            results[missing[j]] = result
    return results


def categorize(transactions: list[Transaction]) -> list[CategorizationResult | None]:
    """Categorize any number of transactions, BATCH_SIZE at a time."""
    results: list[CategorizationResult | None] = []
    for start in range(0, len(transactions), BATCH_SIZE):
        results.extend(categorize_batch(transactions[start:start + BATCH_SIZE]))
    return results