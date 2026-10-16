-- 005: Total spending per month, with the change from the previous month
--
-- Built on the category view (004), so "what counts as spending" is
-- defined in one place. Joined back to the spine so a user with no spending
-- at all in a month still gets a 0 row.

create or replace view public.v_monthly_spending
with (security_invoker = true)
as
with monthly as (
  select
    s.user_id,
    s.month,
    coalesce(sum(c.spent), 0) as spent
  from public.v_month_spine as s
  left join public.v_spending_by_category_month as c
    on c.user_id = s.user_id
    and c.month = s.month
  group by s.user_id, s.month
),
with_previous as (
  select
    user_id,
    month,
    spent,
    lag(spent) over (partition by user_id order by month) as previous_spent
  from monthly
)
select
  user_id,
  month,
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

revoke all on public.v_monthly_spending from anon;
grant select on public.v_monthly_spending to authenticated;
