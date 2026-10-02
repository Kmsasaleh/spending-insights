from app.categorizer import categorize
from app.db import description_key, lookup_memory, save_memory
from app.models import CategorizationResult, Transaction

REMEMBER_THRESHOLD = 0.8  # only remember answers Claude was confident about


def categorize_with_memory(
    user_id: str,
    transactions: list[Transaction],
) -> tuple[list[CategorizationResult | None], list[str], int]:
    """Categorize using this user's merchant memory first, and Claude only for the rest.

    Returns (results, sources, number_of_transactions_sent_to_claude).
    """
    keys = [description_key(t.description) for t in transactions]
    memory = lookup_memory(user_id, keys)

    # Repeats of the same unknown merchant in one upload are only asked once.
    first_index: dict[str, int] = {}
    to_ask: list[int] = []
    for i, k in enumerate(keys):
        if k in memory:
            continue
        if k and k in first_index:
            continue
        if k:
            first_index[k] = i
        to_ask.append(i)

    answers = dict(zip(to_ask, categorize([transactions[i] for i in to_ask])))

    results: list[CategorizationResult | None] = []
    sources: list[str] = []
    for i, k in enumerate(keys):
        if k in memory:
            results.append(memory[k])
            sources.append("memory")
        elif i in answers:
            results.append(answers[i])
            sources.append("llm")
        else:
            results.append(answers.get(first_index[k]))
            sources.append("llm")

    new_memory = {
        keys[i]: r
        for i, r in answers.items()
        if r is not None and keys[i] and r.confidence >= REMEMBER_THRESHOLD
    }
    save_memory(user_id, new_memory)

    return results, sources, len(to_ask)