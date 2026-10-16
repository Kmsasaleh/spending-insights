#!/usr/bin/env bash
# Builds a throwaway database, applies every SQL file in order, and runs the
# assertions. Uses the standard PG* environment variables to connect.
#   PGHOST=localhost PGUSER=postgres PGPASSWORD=postgres sql/tests/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

db=spending_insights_sql_test
psql -X -q -v ON_ERROR_STOP=1 -d postgres -c "drop database if exists $db" -c "create database $db"

run() { psql -X -q -v ON_ERROR_STOP=1 -d "$db" -f "$1"; }

run tests/00_supabase_mock.sql
for f in 0*.sql; do run "$f"; done
run tests/10_seed.sql
# Applying the files a second time must also work (safe to re-run in Supabase).
for f in 0*.sql; do run "$f"; done
run tests/20_assertions.sql

echo "SQL tests passed"
