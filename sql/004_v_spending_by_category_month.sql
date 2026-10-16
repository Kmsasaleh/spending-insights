-- 004: Spending by category and month
--
-- Every month in the spine x every category the user has ever spent in,
-- with 0 where nothing was spent. Money out is negative in transactions,
-- so spending = -sum(amount); refunds (positive) reduce it.
-- Transfers (e.g. card payments) and Income aren't spending, so they're
-- excluded. A transaction with no category counts as 'Uncategorized'.

create or replace view public.v_spending_by_category_month
with (security_invoker = true)
as
with spending as (
  select
    user_id,
    date_trunc('month', posted_date::timestamp)::date as month,
    coalesce(category, 'Uncategorized') as category,
    -sum(amount) as spent
  from public.transactions
  where coalesce(category, 'Uncategorized') not in ('Transfers', 'Income')
  group by
    user_id,
    date_trunc('month', posted_date::timestamp)::date,
    coalesce(category, 'Uncategorized')
),
user_categories as (
  select distinct user_id, category
  from spending
)
select
  s.user_id,
  s.month,
  c.category,
  coalesce(sp.spent, 0) as spent
from public.v_month_spine as s
join user_categories as c
  on c.user_id = s.user_id
left join spending as sp
  on  sp.user_id  = s.user_id
  and sp.month    = s.month
  and sp.category = c.category;

revoke all on public.v_spending_by_category_month from anon;
grant select on public.v_spending_by_category_month to authenticated;
