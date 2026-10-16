-- 007: Running total of spending through each month
--
-- One row per day (a day spine from generate_series, so days with no
-- spending still appear), with the cumulative spend since the 1st of that
-- month. The running total restarts each month because of PARTITION BY.
-- The latest month stops at the last transaction date instead of running
-- flat to the end of the month.

create or replace view public.v_daily_running_total
with (security_invoker = true)
as
with daily as (
  select
    user_id,
    posted_date as day,
    -sum(amount) as spent
  from public.transactions
  where coalesce(category, 'Uncategorized') not in ('Transfers', 'Income')
  group by user_id, posted_date
),
last_dates as (
  select user_id, max(posted_date) as last_date
  from public.transactions
  group by user_id
),
days as (
  select
    s.user_id,
    s.month,
    d::date as day
  from public.v_month_spine as s
  join last_dates as l
    on l.user_id = s.user_id
  cross join lateral generate_series(
    s.month::timestamp,
    least(s.month + interval '1 month - 1 day', l.last_date::timestamp),
    interval '1 day'
  ) as d
)
select
  d.user_id,
  d.month,
  d.day,
  coalesce(dl.spent, 0) as spent,
  sum(coalesce(dl.spent, 0)) over (
    partition by d.user_id, d.month
    order by d.day
    rows between unbounded preceding and current row
  ) as running_total
from days as d
left join daily as dl
  on  dl.user_id = d.user_id
  and dl.day     = d.day;

revoke all on public.v_daily_running_total from anon;
grant select on public.v_daily_running_total to authenticated;
