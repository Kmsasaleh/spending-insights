-- 001: Row Level Security policies
--
-- RLS was already enabled on both tables, but with no policies, so the
-- database API returned nothing to signed-in users. The FastAPI backend is
-- unaffected because its secret key bypasses RLS.
--
-- The dashboard now reads the views (files 003-008) straight from the
-- browser with the user's own login token, so signed-in users need to be
-- able to read their own rows, and only their own rows.
--
-- Only SELECT is allowed. All writes still go through the backend, so
-- there are no INSERT, UPDATE or DELETE policies, which means those
-- actions stay blocked for browser requests.

alter table public.transactions enable row level security;
alter table public.merchant_memory enable row level security;

drop policy if exists "Users can read their own transactions" on public.transactions;
create policy "Users can read their own transactions"
  on public.transactions
  for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can read their own merchant memory" on public.merchant_memory;
create policy "Users can read their own merchant memory"
  on public.merchant_memory
  for select
  to authenticated
  using ((select auth.uid()) = user_id);
