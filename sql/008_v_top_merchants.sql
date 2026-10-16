-- 008: Top 3 merchants per category per month
--
-- Joins to merchant_memory for the merchant's name. Memory holds one
-- name per normalized description (store numbers removed), so the same
-- shop is counted under one name even if the LLM named it slightly
-- differently on transactions categorized before it was remembered.
-- If there's no memory entry, it falls back to the transaction's own
-- merchant name, then to the raw description.

create or replace view public.v_top_merchants
with (security_invoker = true)
as
with named as (
  select
    t.user_id,
    date_trunc('month', t.posted_date::timestamp)::date as month,
    coalesce(t.category, 'Uncategorized') as category,
    coalesce(m.merchant, t.merchant, t.description) as merchant,
    t.amount
  from public.transactions as t
  left join public.merchant_memory as m
    on  m.user_id = t.user_id
    and m.description_key = public.description_key(t.description)
  where coalesce(t.category, 'Uncategorized') not in ('Transfers', 'Income')
),
per_merchant as (
  select
    user_id,
    month,
    category,
    merchant,
    -sum(amount) as spent,
    count(*) as transaction_count
  from named
  group by user_id, month, category, merchant
),
ranked as (
  select
    *,
    row_number() over (
      partition by user_id, month, category
      order by spent desc, merchant
    ) as merchant_rank
  from per_merchant
)
select
  user_id,
  month,
  category,
  merchant,
  spent,
  transaction_count,
  merchant_rank
from ranked
where merchant_rank <= 3
  and spent > 0;

revoke all on public.v_top_merchants from anon;
grant select on public.v_top_merchants to authenticated;
