-- 002: Helper function and index

-- The same merchant normalization as description_key() in backend/app/db.py:
-- 'SQ *TIM HORTONS #4521' -> 'SQ TIM HORTONS'
-- Uppercase, turn anything that isn't A-Z or a space into a space, then
-- collapse repeated spaces and trim the ends.
-- Checked against the Python version on 825 descriptions: identical except
-- 'ß', which Python uppercases to 'SS' and Postgres leaves alone.
-- Needed because transactions don't store the key, but merchant_memory is
-- keyed by it (used by the top merchants view, file 008).
create or replace function public.description_key(description text)
returns text
language sql
immutable
parallel safe
set search_path = ''
as $$
  select btrim(
    regexp_replace(
      regexp_replace(upper(description), '[^A-Z ]', ' ', 'g'),
      ' +', ' ', 'g'
    )
  )
$$;

-- Every policy and view filters by user and then by date, so one index on
-- both columns serves all of them.
create index if not exists transactions_user_id_posted_date_idx
  on public.transactions (user_id, posted_date);
