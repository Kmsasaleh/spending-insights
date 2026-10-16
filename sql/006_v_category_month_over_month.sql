-- 006: Month-over-month change for each category
--
-- LAG looks one row back within the same user and category, ordered by
-- month. Because 004 already filled empty months with 0, "one row back"
-- is always the previous calendar month. Without the spine, LAG would
-- jump over a missing month and compare against an older one.

create or replace view public.v_category_month_over_month
with (security_invoker = true)
as
with with_previous as (
  select
    user_id,
    month,
    category,
    spent,
    lag(spent) over (partition by user_id, category order by month) as previous_spent
  from public.v_spending_by_category_month
)
select
  user_id,
  month,
  category,
  spent,
  previous_spent,
  spent - previous_spent as change,
  -- Only when last month had real spending. If it was 0 (division by zero)
  -- or negative (refunds outweighed purchases), a percentage is meaningless.
  case
    when previous_spent > 0
      then round(100 * (spent - previous_spent) / previous_spent, 1)
  end as pct_change
from with_previous;

revoke all on public.v_category_month_over_month from anon;
grant select on public.v_category_month_over_month to authenticated;
