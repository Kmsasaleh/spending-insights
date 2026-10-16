# SQL: dashboard analytics in PostgreSQL

The dashboard's numbers are calculated in the database by these views, and the browser reads them directly through Supabase. Row Level Security limits every query to the signed-in user.

| File | What it does | Techniques |
|---|---|---|
| `001_rls_read_own_rows.sql` | Lets signed-in users read only their own rows; all writes stay blocked from the browser | Row Level Security policies |
| `002_description_key_and_index.sql` | SQL copy of the backend's merchant normalization, plus an index on `(user_id, posted_date)` | `regexp_replace`, immutable SQL function, composite index |
| `003_v_month_spine.sql` | One row per user per month, first to last, with no gaps | `generate_series`, `CROSS JOIN LATERAL`, `date_trunc` |
| `004_v_spending_by_category_month.sql` | Spending per category per month, 0 for empty months | CTEs, `GROUP BY`, `LEFT JOIN` onto the spine, `COALESCE` |
| `005_v_monthly_spending.sql` | Monthly total and change from the previous month | CTEs, `GROUP BY`, `LAG() OVER (PARTITION BY … ORDER BY …)` |
| `006_v_category_month_over_month.sql` | Month-over-month change for each category | CTE, `LAG() OVER (PARTITION BY user, category …)` |
| `007_v_daily_running_total.sql` | Cumulative spending through each month, day by day | Daily `generate_series`, `SUM() OVER (… ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` |
| `008_v_top_merchants.sql` | Top 3 merchants per category per month, named from `merchant_memory` | `LEFT JOIN` to `merchant_memory`, `ROW_NUMBER() OVER (PARTITION BY …)` |

Every view is created `with (security_invoker = true)`, so it runs with the signed-in user's permissions and the table policies apply. Without it, a view runs as its owner and would show every user's data. The tests check for this.

## Applying to Supabase

Open the Supabase SQL editor and run the files in number order (001 to 008). Every file can be safely run again.

## Tests

`tests/run.sh` builds a throwaway database with a small imitation of Supabase's roles and `auth.uid()`, applies every file twice, and runs `tests/20_assertions.sql`. Those assertions check totals, gap months, refunds, month-over-month change, running totals, merchant ranking, that no other user's rows are visible, that the browser can't write, and that signed-out users can't read. CI runs this on every push.

```bash
PGHOST=localhost PGUSER=postgres PGPASSWORD=postgres sql/tests/run.sh
```
