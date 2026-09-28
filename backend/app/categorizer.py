from anthropic import Anthropic
from pydantic import ValidationError

from app.models import Category, CategorizationResult, Transaction

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 25

SYSTEM_PROMPT = f"""You categorize credit card transactions.
For each transaction, return:
- merchant: a clean, readable merchant name (e.g. "SQ *TIM HORTONS #4521" -> "Tim Hortons")
- category: exactly one of: {", ".join(c.value for c in Category)}
- confidence: 0.0 to 1.0, how sure you are about the category

Rules:
- Amounts are negative for purchases and positive for payments or refunds.
- Payments made to the credit card itself (e.g. "PAYMENT RECEIVED") are Transfers.
- A refund gets the category the original purchase would have had.
- Recurring digital services (streaming, software, memberships) are Subscriptions.
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
                        "id": {"type": "integer"},
                        "merchant": {"type": "string"},
                        "category": {"type": "string", "enum": [c.value for c in Category]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["id", "merchant", "category", "confidence"],
                },
            }
        },
        "required": ["results"],
    },
}


def categorize_batch(transactions: list[Transaction]) -> list[CategorizationResult | None]:
    """Categorize up to BATCH_SIZE transactions in one API call.

    Returns one result per transaction, in the same order.
    None means the model's answer for that row failed validation.
    """
    # Only the description and amount are sent: no dates, names, or account info.
    lines = [f'{i}. "{t.description}" | {t.amount}' for i, t in enumerate(transactions)]

    response = Anthropic().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_categorizations"},
        messages=[{"role": "user", "content": "Categorize these transactions:\n" + "\n".join(lines)}],
    )

    tool_input = next(block.input for block in response.content if block.type == "tool_use")

    results: list[CategorizationResult | None] = [None] * len(transactions)
    for item in tool_input.get("results", []):
        try:
            idx = item["id"]
            if not isinstance(idx, int) or not 0 <= idx < len(transactions):
                continue  # ignore ids that don't match a transaction we sent
            results[idx] = CategorizationResult(
                merchant=item["merchant"],
                category=item["category"],
                confidence=item["confidence"],
            )
        except (KeyError, TypeError, ValidationError):
            continue  # leave this row as None; never trust unvalidated output
    return results


def categorize(transactions: list[Transaction]) -> list[CategorizationResult | None]:
    """Categorize any number of transactions, BATCH_SIZE at a time."""
    results: list[CategorizationResult | None] = []
    for start in range(0, len(transactions), BATCH_SIZE):
        results.extend(categorize_batch(transactions[start:start + BATCH_SIZE]))
    return results