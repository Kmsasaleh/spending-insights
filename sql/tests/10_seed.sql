-- Test data, loaded as the database owner (like the backend's secret key).
--
-- User A: spending in June, August and September, nothing in July (tests the spine).
-- User B: another user whose rows and memory must never appear for A.
-- User C: a month where refunds outweigh purchases (tests the percent-change guard).

insert into public.transactions (user_id, posted_date, description, amount, merchant, category, source) values
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-06-03', 'TIM HORTONS #1234 HAMILTON', -4.87, 'Tim Hortons', 'Dining', 'llm'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-06-10', 'NOFRILLS #3321 HAMILTON', -50.00, 'No Frills', 'Groceries', 'llm'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-02', 'TIM HORTONS #9999 HAMILTON', -10.00, 'Tim Horton''s', 'Dining', 'llm'),  -- name variant
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-05', 'UBER EATS TORONTO', -32.15, 'Uber Eats', 'Dining', 'llm'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-05', 'NOFRILLS #3321 HAMILTON', -86.42, 'No Frills', 'Groceries', 'memory'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-20', 'NETFLIX.COM 866-579-7172', -20.99, 'Netflix', 'Subscriptions', 'llm'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-25', 'PAYMENT THANK YOU', 500.00, 'Amex', 'Transfers', 'llm'),        -- not spending
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-08-28', 'NOFRILLS REFUND', 6.42, 'No Frills', 'Groceries', 'llm'),        -- refund
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-09-01', 'TIM HORTONS #1234 HAMILTON', -4.87, 'Tim Hortons', 'Dining', 'memory'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-09-03', 'SHELL C11318', -60.00, 'Shell', 'Transport', 'llm'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-09-12', 'MYSTERY SHOP 42', -15.00, null, null, 'llm'),                    -- uncategorized
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-09-15', 'NETFLIX.COM 866-579-7172', -20.99, 'Netflix', 'Subscriptions', 'memory'),
 ('aaaaaaaa-0000-0000-0000-000000000001', '2026-09-18', 'SALARY DEPOSIT', 2000.00, 'Employer', 'Income', 'llm'),          -- not spending
 ('bbbbbbbb-0000-0000-0000-000000000002', '2026-09-05', 'SECRET STORE', -999.00, 'Secret Store', 'Shopping', 'llm'),
 ('bbbbbbbb-0000-0000-0000-000000000002', '2026-10-05', 'SECRET STORE', -1.00, 'Secret Store', 'Shopping', 'llm'),
 ('cccccccc-0000-0000-0000-000000000003', '2026-01-10', 'BIG RETURN', 40.00, 'Store', 'Shopping', 'llm'),
 ('cccccccc-0000-0000-0000-000000000003', '2026-01-11', 'SMALL BUY', -10.00, 'Store', 'Shopping', 'llm'),
 ('cccccccc-0000-0000-0000-000000000003', '2026-02-11', 'SMALL BUY', -25.00, 'Store', 'Shopping', 'llm');

insert into public.merchant_memory (user_id, description_key, merchant, category, source) values
 ('aaaaaaaa-0000-0000-0000-000000000001', 'TIM HORTONS HAMILTON', 'Tim Hortons', 'Dining', 'llm'),
 ('bbbbbbbb-0000-0000-0000-000000000002', 'TIM HORTONS HAMILTON', 'B NAME LEAK', 'Dining', 'llm');  -- must never join to A's rows
