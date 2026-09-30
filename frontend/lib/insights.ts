import type { Category, StoredTransaction } from "./api";

// Not real spending: card payments just move money between your own accounts
// (the purchases themselves are already counted), and income isn't spending.
const NOT_SPENDING: (Category | null)[] = ["Transfers", "Income"];

/** Work in whole cents so totals stay exact (no floating-point drift). */
function toCents(amount: string): number {
  return Math.round(Number(amount) * 100);
}

function monthLabel(month: string, style: "short" | "long"): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m - 1, 1).toLocaleDateString("en-CA", { month: style, year: "numeric" });
}

export type MonthTotal = { month: string; short: string; long: string; cents: number };
export type CategoryTotal = { category: string; cents: number };

/** Spending per month (money out is positive here), oldest to newest, last 6 months. */
export function spendingByMonth(transactions: StoredTransaction[]): MonthTotal[] {
  const totals = new Map<string, number>();
  for (const t of transactions) {
    if (NOT_SPENDING.includes(t.category)) continue;
    const month = t.posted_date.slice(0, 7); // "2026-09-25" -> "2026-09"
    // Purchases are negative, so subtracting adds them; refunds (positive) reduce the total.
    totals.set(month, (totals.get(month) ?? 0) - toCents(t.amount));
  }
  return [...totals.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-6)
    .map(([month, cents]) => ({
      month,
      short: monthLabel(month, "short"),
      long: monthLabel(month, "long"),
      cents,
    }));
}

/** Spending per category for one month, largest first. */
export function spendingByCategory(transactions: StoredTransaction[], month: string): CategoryTotal[] {
  const totals = new Map<string, number>();
  for (const t of transactions) {
    if (NOT_SPENDING.includes(t.category) || !t.posted_date.startsWith(month)) continue;
    const key = t.category ?? "Uncategorized";
    totals.set(key, (totals.get(key) ?? 0) - toCents(t.amount));
  }
  return [...totals.entries()]
    .map(([category, cents]) => ({ category, cents }))
    .filter((c) => c.cents > 0)
    .sort((a, b) => b.cents - a.cents);
}