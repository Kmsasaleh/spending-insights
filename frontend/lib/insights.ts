import { supabase } from "./supabase";

// All dashboard numbers are calculated in PostgreSQL (see /sql). These
// functions only read the views. There's no user filter here because Row
// Level Security already limits every view to the signed-in user.

/** Postgres numeric arrives as a JSON number; work in whole cents so totals stay exact. */
const toCents = (amount: number) => Math.round(amount * 100);

function monthLabel(month: string, style: "short" | "long"): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m - 1, 1).toLocaleDateString("en-CA", { month: style, year: "numeric" });
}

/** Supabase returns errors instead of throwing; turn them into exceptions. */
function rows<T>({ data, error }: { data: T[] | null; error: { message: string } | null }): T[] {
  if (error) throw new Error(`Couldn't load the dashboard. ${error.message}`);
  return data ?? [];
}

export type MonthTotal = {
  month: string; // first day of the month, e.g. "2026-09-01"
  short: string;
  long: string;
  cents: number;
  pctChange: number | null; // vs the previous calendar month; null if that month had no spending
};

export type CategoryTotal = { category: string; cents: number; changeCents: number | null };

export type RunningTotalDay = { day: string; dayOfMonth: number; cents: number };

export type TopMerchant = {
  category: string;
  merchant: string;
  cents: number;
  count: number;
  rank: number;
};

/** Spending for the last 6 calendar months, oldest first. Months with no spending are 0. */
export async function getMonthlySpending(): Promise<MonthTotal[]> {
  const result = await supabase
    .from("v_monthly_spending")
    .select("month, spent, pct_change")
    .order("month", { ascending: false })
    .limit(6);
  return rows<{ month: string; spent: number; pct_change: number | null }>(result)
    .reverse()
    .map((r) => ({
      month: r.month,
      short: monthLabel(r.month, "short"),
      long: monthLabel(r.month, "long"),
      cents: toCents(r.spent),
      pctChange: r.pct_change,
    }));
}

/** Spending per category for one month, largest first, with the change from the month before. */
export async function getCategorySpending(month: string): Promise<CategoryTotal[]> {
  const result = await supabase
    .from("v_category_month_over_month")
    .select("category, spent, change")
    .eq("month", month)
    .gt("spent", 0)
    .order("spent", { ascending: false });
  return rows<{ category: string; spent: number; change: number | null }>(result).map((r) => ({
    category: r.category,
    cents: toCents(r.spent),
    changeCents: r.change === null ? null : toCents(r.change),
  }));
}

/** Cumulative spending through the month, one point per day. */
export async function getRunningTotal(month: string): Promise<RunningTotalDay[]> {
  const result = await supabase
    .from("v_daily_running_total")
    .select("day, running_total")
    .eq("month", month)
    .order("day");
  return rows<{ day: string; running_total: number }>(result).map((r) => ({
    day: r.day,
    dayOfMonth: Number(r.day.slice(8, 10)),
    cents: toCents(r.running_total),
  }));
}

/** Up to 3 merchants per category for one month. */
export async function getTopMerchants(month: string): Promise<TopMerchant[]> {
  const result = await supabase
    .from("v_top_merchants")
    .select("category, merchant, spent, transaction_count, merchant_rank")
    .eq("month", month)
    .order("category")
    .order("merchant_rank");
  return rows<{
    category: string;
    merchant: string;
    spent: number;
    transaction_count: number;
    merchant_rank: number;
  }>(result).map((r) => ({
    category: r.category,
    merchant: r.merchant,
    cents: toCents(r.spent),
    count: r.transaction_count,
    rank: r.merchant_rank,
  }));
}
