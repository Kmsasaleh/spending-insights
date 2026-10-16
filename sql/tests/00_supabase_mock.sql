-- Test only: recreate the parts of Supabase that the SQL files rely on,
-- so they can be tested on a plain Postgres (locally or in CI).

do $$
begin
  if not exists (select from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
end $$;

create schema auth;
grant usage on schema auth to anon, authenticated;

-- Same logic as Supabase's auth.uid(): the "sub" claim of the request's login token.
create function auth.uid() returns uuid language sql stable as $$
  select (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid
$$;

-- Supabase grants table privileges to these roles by default and relies on
-- Row Level Security to filter rows. Copy that, so the tests prove RLS works.
grant usage on schema public to anon, authenticated;
alter default privileges in schema public grant all on tables to anon, authenticated;

-- The two tables, matching the columns used by backend/app/db.py.
create table public.transactions (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  posted_date date not null,
  description text not null,
  amount numeric(12,2) not null,
  merchant text,
  category text,
  confidence real,
  source text not null,
  created_at timestamptz default now()
);

create table public.merchant_memory (
  user_id uuid not null,
  description_key text not null,
  merchant text not null,
  category text not null,
  source text not null,
  updated_at timestamptz default now(),
  unique (user_id, description_key)
);

-- Same starting point as production: RLS on, no policies yet.
alter table public.transactions enable row level security;
alter table public.merchant_memory enable row level security;
