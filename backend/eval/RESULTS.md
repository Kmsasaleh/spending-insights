# Evaluation results

- **Labelled transactions:** 587 (2025-09-02 to 2026-08-03, 10 months)
- **Model:** `claude-haiku-4-5-20251001`
- **Run:** 2026-10-01

| Method | Accuracy | Sent to Claude |
|---|---|---|
| Keyword rules (baseline) | 70.0% | 0 (0%) |
| Claude | 89.4% | 587 (100%) |
| Claude + merchant memory | 90.1% | 239 (41%) |
| Claude + memory + monthly corrections | 92.3% | 236 (40%) |

## Claude accuracy by category

| Category | Transactions | Accuracy |
|---|---|---|
| Dining | 198 | 92% |
| Shopping | 109 | 95% |
| Groceries | 70 | 99% |
| Transport | 66 | 97% |
| Subscriptions | 55 | 100% |
| Other | 37 | 11% |
| Transfers | 25 | 100% |
| Entertainment | 11 | 64% |
| Bills & Utilities | 10 | 90% |
| Health | 5 | 80% |
| Travel | 1 | 100% |

## Most common mistakes (true → predicted)

- Other → Shopping: 8
- Dining → Groceries: 6
- Other → Dining: 5
- Other → Health: 5
- Dining → Health: 4
- Other → Subscriptions: 4
- Other → Transport: 4
- Dining → Shopping: 3

## Is Claude's confidence meaningful?

- Confidence ≥ 0.8: 530 transactions, 92% correct
- Confidence < 0.8: 57 transactions, 67% correct
