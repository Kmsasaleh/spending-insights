import app.service as service
from app.db import description_key
from app.models import CategorizationResult


def result(category, confidence=0.9):
    return CategorizationResult(merchant="Merchant", category=category, confidence=confidence)


def test_store_numbers_dont_split_a_merchant():
    assert description_key("SQ *TIM HORTONS #4521") == description_key("SQ *TIM HORTONS #1187")
    assert description_key("SQ *TIM HORTONS #4521") == "SQ TIM HORTONS"


def fake_storage(monkeypatch, remembered, answer_category, confidence=0.9):
    """Replace the database and Claude with in-memory fakes. Returns what was sent and saved."""
    sent, saved = [], {}
    monkeypatch.setattr(service, "lookup_memory",
                        lambda user_id, keys: {k: v for k, v in remembered.items() if k in keys})
    monkeypatch.setattr(service, "save_memory", lambda user_id, entries: saved.update(entries))

    def fake_categorize(txns):
        sent.extend(t.description for t in txns)
        return [result(answer_category, confidence) for _ in txns]

    monkeypatch.setattr(service, "categorize", fake_categorize)
    return sent, saved


def test_known_merchants_skip_claude_and_repeats_are_asked_once(monkeypatch, make_txns):
    sent, saved = fake_storage(monkeypatch, {"TIM HORTONS": result("Dining", 1.0)}, "Transport")
    txns = make_txns("TIM HORTONS #4521", "SHELL C11318", "SHELL C21831")

    results, sources, asked = service.categorize_with_memory("user-1", txns)

    assert sources == ["memory", "llm", "llm"]
    assert asked == 1
    assert sent == ["SHELL C11318"]
    assert [r.category.value for r in results] == ["Dining", "Transport", "Transport"]
    assert list(saved) == ["SHELL C"]


def test_unsure_answers_are_not_remembered(monkeypatch, make_txns):
    _, saved = fake_storage(monkeypatch, {}, "Other", confidence=0.5)
    service.categorize_with_memory("user-1", make_txns("MYSTERY SHOP"))
    assert saved == {}