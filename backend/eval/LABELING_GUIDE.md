# Labelling guide

Every transaction gets exactly one category. The model's prompt and these rules
must agree, so accuracy measures the model, not a mismatch in definitions.

| Category | Includes |
|---|---|
| Groceries | Supermarkets, grocery delivery (Instacart, Voila), campus food stores |
| Dining | Restaurants, cafés, coffee shops, bakeries, bars, food delivery (Uber Eats, DoorDash, SkipTheDishes) |
| Transport | Transit, fuel, parking, Uber/Lyft rides, car costs |
| Shopping | Retail and online stores (Amazon, Walmart, clothing, electronics), personal-care stores |
| Subscriptions | Recurring digital services and memberships (streaming, software, apps) |
| Bills & Utilities | Phone, internet, electricity, insurance, bank/card fees |
| Entertainment | Movies, events, games, bars/lounges visited as an outing |
| Health | Pharmacy purchases, gym, medical, dental, barber and personal care services |
| Travel | Flights, hotels, travel documents, rental cars |
| Income | Pay, refunds from employers, money received as income |
| Transfers | Credit card payments, moving money between your own accounts |
| Other | Only when none of the above fits |

Rules:
- A refund gets the category of the original purchase.
- Uber Eats is Dining; Uber rides are Transport, even when travelling.
- When a store sells many kinds of things (e.g. a pharmacy), label by what it mostly sells.
- Amazon Prime membership is Subscriptions; the card's annual membership fee is Bills & Utilities.
- Credit card payments ("PAYMENT RECEIVED") are Transfers.
- Parking (including McMaster parking and parking apps like Honk) is Transport.
- Phone and internet providers (e.g. Rogers) are Bills & Utilities.
- Walmart is Shopping.
- Campus food stores (Student Market, Union Market) are Groceries.
- Label without looking at the app's prediction.