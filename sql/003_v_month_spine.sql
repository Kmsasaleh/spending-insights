-- 003: Month spine
--
-- One row per user per calendar month, from their first transaction's month
-- to their last, with no gaps. Other views LEFT JOIN onto this so a month
-- with no spending appears as 0 instead of disappearing.
--
-- It ends at the last month with data, not today, so a statement uploaded
-- in August doesn't show September and October as $0.

create or replace view public.v_month_spine
with (security_invoker = true)
as
select
  r.user_id,
  m::date as month
from (
  select
    user_id,
    date_trunc('month', min(posted_date)::timestamp) as first_month,
    date_trunc('month', max(posted_date)::timestamp) as last_month
  from public.transactions
  group by user_id
) as r
cross join lateral generate_series(r.first_month, r.last_month, interval '1 month') as m;

revoke all on public.v_month_spine from anon;
grant select on public.v_month_spine to authenticated;
