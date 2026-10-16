-- Assertions. Every check raises an error if it fails, so
-- `psql -v ON_ERROR_STOP=1` exits non-zero and CI goes red.
-- Each block signs in as a user the way the browser does: the
-- `authenticated` role plus a login token whose "sub" is the user's id.

------------------------------------------------------------------------------
-- User A
------------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);

do $$
declare
  n int;
  v numeric;
begin
  -- RLS on the raw tables: only A's rows.
  select count(*) into n from public.transactions;
  assert n = 13, format('A should see 13 transactions, saw %s', n);
  select count(*) into n from public.merchant_memory;
  assert n = 1, format('A should see 1 merchant memory row, saw %s', n);

  -- Spine: June to September with no gap, even though July has no rows.
  assert (select array_agg(month order by month) from public.v_month_spine)
       = array['2026-06-01','2026-07-01','2026-08-01','2026-09-01']::date[],
         'spine should be Jun, Jul, Aug, Sep 2026';

  -- July: one zero row per category A has ever spent in (5 categories).
  select count(*), sum(spent) into n, v
  from public.v_spending_by_category_month where month = '2026-07-01';
  assert n = 5 and v = 0, format('July should be 5 zero rows, got %s rows totalling %s', n, v);

  -- Category totals. August groceries: 86.42 spent - 6.42 refunded = 80.00.
  assert (select spent from public.v_spending_by_category_month
          where month = '2026-08-01' and category = 'Groceries') = 80.00, 'Aug groceries should be 80.00';
  assert (select spent from public.v_spending_by_category_month
          where month = '2026-09-01' and category = 'Uncategorized') = 15.00, 'null category should count as Uncategorized';
  assert not exists (select from public.v_spending_by_category_month
                     where category in ('Transfers', 'Income')), 'Transfers and Income are not spending';

  -- Monthly totals and month-over-month change.
  assert (select array_agg(spent order by month) from public.v_monthly_spending)
       = array[54.87, 0, 143.14, 100.86]::numeric[], 'monthly totals';
  assert (select pct_change from public.v_monthly_spending where month = '2026-07-01') = -100.0, 'July vs June';
  assert (select pct_change from public.v_monthly_spending where month = '2026-08-01') is null,
         'no percent change when the previous month was 0';
  assert (select pct_change from public.v_monthly_spending where month = '2026-09-01') = -29.5, 'Sep vs Aug';

  -- Category month-over-month: LAG compares September with August, not with an older month.
  select previous_spent into v
  from public.v_category_month_over_month where category = 'Dining' and month = '2026-09-01';
  assert v = 42.15, format('Dining previous month should be Aug (42.15), got %s', v);
  assert (select pct_change from public.v_category_month_over_month
          where category = 'Dining' and month = '2026-09-01') = -88.4, 'Dining Sep vs Aug';

  -- Running total: the last day of every month equals that month's total.
  assert not exists (
    select from (
      select distinct on (month) month, running_total
      from public.v_daily_running_total order by month, day desc
    ) as last_day
    join public.v_monthly_spending as m using (month)
    where last_day.running_total <> m.spent
  ), 'running total on the last day should equal the monthly total';
  assert (select running_total from public.v_daily_running_total where day = '2026-09-03') = 64.87,
         'running total on Sep 3 (4.87 + 60.00)';
  assert (select count(*) from public.v_daily_running_total where month = '2026-07-01') = 31,
         'empty July still has 31 days';
  assert (select max(day) from public.v_daily_running_total) = '2026-09-18',
         'latest month stops at the last transaction date';

  -- Top merchants: the name comes from merchant_memory, so the "Tim Horton's" variant is merged.
  assert (select array_agg(merchant order by merchant_rank) from public.v_top_merchants
          where month = '2026-08-01' and category = 'Dining') = array['Uber Eats', 'Tim Hortons'],
         'Aug Dining ranking';
  assert (select transaction_count from public.v_top_merchants
          where month = '2026-08-01' and category = 'Groceries' and merchant_rank = 1) = 2,
         'No Frills purchase and refund grouped together';
  assert (select max(merchant_rank) from public.v_top_merchants) <= 3, 'top 3 only';

  -- Nothing from user B, in any view.
  select (select count(*) from public.v_month_spine where user_id <> auth.uid())
       + (select count(*) from public.v_spending_by_category_month where user_id <> auth.uid())
       + (select count(*) from public.v_monthly_spending where user_id <> auth.uid())
       + (select count(*) from public.v_category_month_over_month where user_id <> auth.uid())
       + (select count(*) from public.v_daily_running_total where user_id <> auth.uid())
       + (select count(*) from public.v_top_merchants where user_id <> auth.uid() or merchant like '%LEAK%')
    into n;
  assert n = 0, format('%s rows from another user leaked into the views', n);

  -- The browser can read but not write.
  begin
    insert into public.transactions (user_id, posted_date, description, amount, source)
    values (auth.uid(), '2026-09-30', 'X', -1, 'user');
    raise exception 'insert from the browser role should have been blocked';
  exception when insufficient_privilege then null;  -- blocked by RLS, as expected
  end;
  update public.transactions set amount = 0;
  get diagnostics n = row_count;
  assert n = 0, format('update from the browser role changed %s rows', n);
  delete from public.merchant_memory;
  get diagnostics n = row_count;
  assert n = 0, format('delete from the browser role removed %s rows', n);

  raise notice 'user A: all checks passed';
end $$;
rollback;

------------------------------------------------------------------------------
-- User C: refunds outweighed purchases in January (spent = -30.00)
------------------------------------------------------------------------------
begin;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"cccccccc-0000-0000-0000-000000000003","role":"authenticated"}', true);

do $$
begin
  assert (select spent from public.v_monthly_spending where month = '2026-01-01') = -30.00, 'Jan net refund';
  assert (select pct_change from public.v_monthly_spending where month = '2026-02-01') is null,
         'no percent change when the previous month was negative';
  assert not exists (select from public.v_top_merchants where month = '2026-01-01'),
         'a merchant you were net refunded by is not a top merchant';
  raise notice 'user C: all checks passed';
end $$;
rollback;

------------------------------------------------------------------------------
-- Signed out (anon): no access to the views, no rows from the tables
------------------------------------------------------------------------------
begin;
set local role anon;

do $$
begin
  begin
    perform 1 from public.v_monthly_spending;
    raise exception 'anon should not be able to read the views';
  exception when insufficient_privilege then null;
  end;
  assert (select count(*) from public.transactions) = 0, 'anon should see no transactions';
  raise notice 'anon: all checks passed';
end $$;
rollback;
