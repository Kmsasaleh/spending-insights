"use client";

import { useState } from "react";
import { uploadStatement, type CategorizeResponse } from "@/lib/api";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CategorizeResponse | null>(null);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await uploadStatement(file));
    } catch (e) {
      setError(
        e instanceof TypeError
          ? "Couldn't reach the server. Check that the backend is running."
          : (e as Error).message
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Spending Insights</h1>
      <p className="mt-2 max-w-prose text-slate-600">
        Upload an Amex CSV export. Every transaction is categorized and saved to your history.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
            setError(null);
          }}
          className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-200 file:px-3 file:py-2 file:text-sm hover:file:bg-slate-300"
        />
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="rounded-md bg-pine px-4 py-2 text-sm font-medium text-white disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine"
        >
          {loading ? "Categorizing…" : "Categorize statement"}
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-10">
          <p className="text-sm text-slate-600">
            Saved {result.transactions.length} transactions. {result.from_memory}{" "}
            {result.from_memory === 1 ? "was" : "were"} recognized from memory and{" "}
            {result.sent_to_claude} {result.sent_to_claude === 1 ? "was" : "were"} sent to Claude.
          </p>

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
                {result.transactions.map((t, i) => (
                  <tr key={i}>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">{t.posted_date}</td>
                    <td className="px-4 py-3">
                      <div className="text-ink">{t.merchant ?? "Unknown merchant"}</div>
                      <div className="text-xs text-slate-500">{t.description}</div>
                    </td>
                    <td className="px-4 py-3">
                      {t.category ?? "Needs review"}
                      {t.confidence !== null && t.confidence < 0.7 && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                          Check
                        </span>
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
        </section>
      )}
    </main>
  );
}