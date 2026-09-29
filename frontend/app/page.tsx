"use client";

import { useEffect, useState } from "react";
import {
  CATEGORIES,
  getTransactions,
  updateCategory,
  uploadStatement,
  type Category,
  type CategorizeResponse,
  type StoredTransaction,
} from "@/lib/api";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

function describeError(e: unknown): string {
  return e instanceof TypeError
    ? "Couldn't reach the server. Check that the backend is running."
    : (e as Error).message;
}

function needsReview(t: StoredTransaction): boolean {
  if (t.source === "user") return false;
  return t.category === null || (t.confidence ?? 0) < 0.7;
}

export default function Home() {
  const [transactions, setTransactions] = useState<StoredTransaction[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [inputKey, setInputKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState<CategorizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load saved history once, when the page first opens.
  useEffect(() => {
    getTransactions()
      .then(setTransactions)
      .catch((e) => setError(describeError(e)))
      .finally(() => setLoadingHistory(false));
  }, []);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      setSummary(await uploadStatement(file));
      setTransactions(await getTransactions());
      setFile(null);
      setInputKey((k) => k + 1); // clears the file picker so the same file isn't uploaded twice
    } catch (e) {
      setError(describeError(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleCategoryChange(id: number, category: Category) {
    const previous = transactions;
    // Show the change immediately, then confirm with the server.
    setTransactions((ts) =>
      ts.map((t) => (t.id === id ? { ...t, category, source: "user", confidence: 1 } : t))
    );
    try {
      const saved = await updateCategory(id, category);
      setTransactions((ts) => ts.map((t) => (t.id === id ? saved : t)));
    } catch (e) {
      setTransactions(previous); // undo the change if saving failed
      setError(`That change wasn't saved. ${describeError(e)}`);
    }
  }

  const reviewCount = transactions.filter(needsReview).length;

  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Spending Insights</h1>
      <p className="mt-2 max-w-prose text-slate-600">
        Upload an Amex CSV export. Every transaction is categorized and saved to your history.
        Change any category below and future statements will follow your choice.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <input
          key={inputKey}
          type="file"
          accept=".csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setError(null);
          }}
          className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-200 file:px-3 file:py-2 file:text-sm hover:file:bg-slate-300"
        />
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="rounded-md bg-pine px-4 py-2 text-sm font-medium text-white disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine"
        >
          {uploading ? "Categorizing…" : "Categorize statement"}
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {summary && (
        <p className="mt-4 text-sm text-slate-600">
          Saved {summary.transactions.length} transactions. {summary.from_memory}{" "}
          {summary.from_memory === 1 ? "was" : "were"} recognized from memory and{" "}
          {summary.sent_to_claude} {summary.sent_to_claude === 1 ? "was" : "were"} sent to Claude.
        </p>
      )}

      <section className="mt-10">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-semibold text-ink">History</h2>
          {transactions.length > 0 && (
            <p className="text-sm text-slate-600">
              {transactions.length} transactions
              {reviewCount > 0 && `, ${reviewCount} to review`}
            </p>
          )}
        </div>

        {loadingHistory ? (
          <p className="mt-4 text-sm text-slate-600">Loading your history…</p>
        ) : transactions.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">
            No transactions yet. Upload your first Amex statement above to get started.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Merchant</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {transactions.map((t) => (
                  <tr key={t.id}>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">{t.posted_date}</td>
                    <td className="px-4 py-3">
                      <div className="text-ink">{t.merchant ?? "Unknown merchant"}</div>
                      <div className="text-xs text-slate-500">{t.description}</div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <select
                        aria-label={`Category for ${t.merchant ?? t.description}`}
                        value={t.category ?? ""}
                        onChange={(e) => handleCategoryChange(t.id, e.target.value as Category)}
                        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-sm text-ink focus-visible:outline-2 focus-visible:outline-pine"
                      >
                        {t.category === null && (
                          <option value="" disabled>
                            Choose a category
                          </option>
                        )}
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                      {needsReview(t) && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                          Check
                        </span>
                      )}
                      {t.source === "user" && (
                        <span className="ml-2 text-xs text-slate-500">Edited</span>
                      )}
                    </td>
                    <td
                      className={`whitespace-nowrap px-4 py-3 text-right tabular-nums ${
                        Number(t.amount) > 0 ? "text-pine" : "text-ink"
                      }`}
                    >
                      {money.format(Number(t.amount))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}