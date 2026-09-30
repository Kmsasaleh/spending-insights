"use client";

import { useMemo, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StoredTransaction } from "@/lib/api";
import { spendingByCategory, spendingByMonth } from "@/lib/insights";

const PINE = "#1b4d3e";
const MUTED = "#cbd5e1";
const AXIS = "#64748b";

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
const dollars = (cents: number) => money.format(cents / 100);

export default function Dashboard({ transactions }: { transactions: StoredTransaction[] }) {
  const months = useMemo(() => spendingByMonth(transactions), [transactions]);
  const [picked, setPicked] = useState<string | null>(null);

  // Default to the most recent month; fall back if the picked month disappears.
  const current = months.find((m) => m.month === picked) ?? months.at(-1);
  const categories = useMemo(
    () => (current ? spendingByCategory(transactions, current.month) : []),
    [transactions, current]
  );

  if (!current) return null;

  const index = months.indexOf(current);
  const previous = index > 0 ? months[index - 1] : undefined;
  const change =
    previous && previous.cents > 0
      ? Math.round(((current.cents - previous.cents) / previous.cents) * 100)
      : null;
  const top = categories[0];

  const monthData = months.map((m) => ({ ...m, value: m.cents / 100 }));
  const categoryData = categories.map((c) => ({ ...c, value: c.cents / 100 }));

  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold text-ink">Spending</h2>
        <label className="text-sm text-slate-600">
          Month
          <select
            value={current.month}
            onChange={(e) => setPicked(e.target.value)}
            className="ml-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-ink focus-visible:outline-2 focus-visible:outline-pine"
          >
            {months.map((m) => (
              <option key={m.month} value={m.month}>
                {m.long}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="mt-3 max-w-prose text-slate-700">
        In {current.long} you spent{" "}
        <strong className="font-semibold tabular-nums text-ink">{dollars(current.cents)}</strong>
        {change !== null && previous && (
          <>
            , {Math.abs(change)}% {change >= 0 ? "more" : "less"} than {previous.long}
          </>
        )}
        .
        {top && (
          <>
            {" "}
            {top.category} was your biggest category at{" "}
            <span className="tabular-nums">{dollars(top.cents)}</span>.
          </>
        )}
      </p>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <figure className="rounded-lg border border-slate-200 bg-white p-4">
          <figcaption className="text-sm font-medium text-slate-600">By month</figcaption>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthData}>
                <XAxis dataKey="short" tick={{ fill: AXIS, fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis
                  tickFormatter={(v) => `$${v}`}
                  tick={{ fill: AXIS, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip formatter={(v) => money.format(Number(v))} cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="value" name="Spent" radius={[4, 4, 0, 0]}>
                  {monthData.map((m) => (
                    <Cell
                      key={m.month}
                      fill={m.month === current.month ? PINE : MUTED}
                      cursor="pointer"
                      onClick={() => setPicked(m.month)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">Click a bar to see that month.</p>
        </figure>

        <figure className="rounded-lg border border-slate-200 bg-white p-4">
          <figcaption className="text-sm font-medium text-slate-600">
            By category, {current.long}
          </figcaption>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData} layout="vertical" margin={{ left: 8 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="category"
                  width={120}
                  tick={{ fill: AXIS, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip formatter={(v) => money.format(Number(v))} cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="value" name="Spent" fill={PINE} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </figure>
      </div>
    </section>
  );
}