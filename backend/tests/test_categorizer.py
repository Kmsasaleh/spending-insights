from types import SimpleNamespace

import app.categorizer as categorizer


def fake_claude(monkeypatch, replies):
    """Replace the real Anthropic client. Each API call returns the next reply in `replies`."""
    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            results = replies[len(calls) - 1]
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input={"results": results})])

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(categorizer, "Anthropic", lambda: FakeClient())
    return calls


def answer(tid, echo, category, merchant="Merchant", confidence=0.9):
    return {"id": tid, "echo": echo, "merchant": merchant, "category": category, "confidence": confidence}


def test_answers_are_matched_by_id_not_by_order(monkeypatch, make_txns):
    txns = make_txns("TIM HORTONS #1", "SHELL C11318")
    fake_claude(monkeypatch, [[
        answer("T2", "SHELL C11318", "Transport"),   # answers arrive in a different order
        answer("T1", "TIM HORTONS #1", "Dining"),
    ]])
    results = categorizer.categorize_batch(txns)
    assert [r.category.value for r in results] == ["Dining", "Transport"]


def test_a_misaligned_answer_is_rejected_and_retried(monkeypatch, make_txns):
    txns = make_txns("TIM HORTONS #1", "SHELL C11318")
    calls = fake_claude(monkeypatch, [
        # First reply is shifted: T1 carries Shell's answer, so its echo doesn't match.
        [answer("T1", "SHELL C11318", "Transport"), answer("T2", "SHELL C11318", "Transport")],
        # The retry contains only the failed row, and answers it correctly.
        [answer("T1", "TIM HORTONS #1", "Dining")],
    ])
    results = categorizer.categorize_batch(txns)
    assert [r.category.value for r in results] == ["Dining", "Transport"]
    assert len(calls) == 2


def test_invalid_output_becomes_needs_review(monkeypatch, make_txns):
    txns = make_txns("TIM HORTONS #1")
    bad = [
        answer("T1", "TIM HORTONS #1", "Coffee"),   # not a real category
        answer("T9", "SOMETHING ELSE", "Dining"),   # id that wasn't sent
    ]
    fake_claude(monkeypatch, [bad, bad])
    assert categorizer.categorize_batch(txns) == [None]


def test_dates_are_never_sent_to_claude(monkeypatch, make_txns):
    txns = make_txns("TIM HORTONS #1")
    calls = fake_claude(monkeypatch, [[answer("T1", "TIM HORTONS #1", "Dining")]])
    categorizer.categorize_batch(txns)
    assert "2026-08-01" not in calls[0]["messages"][0]["content"]