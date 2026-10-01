# Evaluation results

- **Labelled transactions:** 587 (2025-09-02 to 2026-08-03, 10 months)
- **Dev set** (used to improve the prompt): 495 transactions, first 7 months
- **Test set** (held out, only for reporting): 92 transactions, last 3 months
- **Model:** `claude-haiku-4-5-20251001`
- **Run:** 2026-10-01

| Method | Dev accuracy | Test accuracy | Sent to Claude (all months) |
|---|---|---|---|
| Keyword rules (baseline) | 71.9% | 59.8% | 0 (0%) |
| Claude | 91.1% | 82.6% | 587 (100%) |
| Claude + merchant memory | 91.5% | 84.8% | 239 (41%) |
| Claude + memory + monthly corrections | 93.5% | 88.0% | 236 (40%) |

## Claude accuracy by category (dev set)

| Category | Transactions | Accuracy |
|---|---|---|
| Dining | 154 | 96% |
| Shopping | 91 | 97% |
| Groceries | 70 | 99% |
| Transport | 58 | 97% |
| Subscriptions | 48 | 100% |
| Other | 31 | 13% |
| Transfers | 21 | 100% |
| Entertainment | 10 | 70% |
| Bills & Utilities | 9 | 89% |
| Health | 3 | 67% |

## Most common mistakes on the dev set (true → predicted)

- Other → Shopping: 8
- Other → Dining: 5
- Dining → Health: 4
- Other → Subscriptions: 4
- Other → Health: 4
- Other → Entertainment: 3
- Entertainment → Other: 2
- Shopping → Subscriptions: 2

## Is Claude's confidence meaningful? (dev set)

- Confidence ≥ 0.8: 448 transactions, 93% correct
- Confidence < 0.8: 47 transactions, 70% correct
