"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getCategorySpending,
  getMonthlySpending,
  getRunningTotal,
  getTopMerchants,
  type CategoryTotal,
  type MonthTotal,
  type RunningTotalDay,
  type TopMerchant,
} from "@/lib/insights";

const PINE = "#1b4d3e";
const MUTED = "#cbd5e1";
const AXIS = "#64748b";
const TOP_CATEGORIES_SHOWN = 4;

const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
const dollars = (cents: number) => money.format(cents / 100);

type MonthDetail = {
  month: string;
  categories: CategoryTotal[];
  running: RunningTotalDay[];
  merchants: TopMerchant[];
};

// dataVersion changes whenever transactions change (upload or category edit),
// which tells the dashboard to read the views again.
export default function Dashboard({ dataVersion }: { dataVersion: number }) {
  const [months, setMonths] = useState<MonthTotal[] | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [detail, setDetail] = useState<MonthDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true; // ignore a response that arrives after a newer request
    getMonthlySpending()
      .then((m) => current && setMonths(m))
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [dataVersion]);

  const current = months?.find((m) => m.month === picked) ?? months?.at(-1);
  const currentMonth = current?.month;

  useEffect(() => {
    if (!currentMonth) return;
    let current = true;
    Promise.all([
      getCategorySpending(currentMonth),
      getRunningTotal(currentMonth),
      getTopMerchants(currentMonth),
    ])
      .then(([categories, running, merchants]) => {
        if (current) setDetail({ month: currentMonth, categories, running, merchants });
      })
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [currentMonth, dataVersion]);

  if (error) {
    return (
      <p role="alert" className="mt-10 text-sm text-red-700">
        {error}
      </p>
    );
  }
  if (!months || !current) return null;

  const shown = detail?.month === current.month ? detail : null;
  const index = months.indexOf(current);
  const previous = index > 0 ? months[index - 1] : undefined;
  const change = current.pctChange === null ? null : Math.round(current.pctChange);
  const top = shown?.categories[0];
  const biggestMove = shown?.categories
    .filter((c) => c.changeCents !== null && c.changeCents !== 0)
    .sort((a, b) => Math.abs(b.changeCents!) - Math.abs(a.changeCents!))[0];

  const monthData = months.map((m) => ({ ...m, value: m.cents / 100 }));
  const categoryData = (shown?.categories ?? []).map((c) => ({ ...c, value: c.cents / 100 }));
  const runningData = (shown?.running ?? []).map((d) => ({ ...d, value: d.cents / 100 }));
  const merchantGroups = (shown?.categories ?? []).slice(0, TOP_CATEGORIES_SHOWN).map((c) => ({
    category: c.category,
    merchants: shown!.merchants.filter((m) => m.category === c.category),
  }));

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
        {biggestMove && previous && (
          <>
            {" "}
            The biggest change was {biggestMove.category},{" "}
            {biggestMove.changeCents! > 0 ? "up" : "down"}{" "}
            <span className="tabular-nums">{dollars(Math.abs(biggestMove.changeCents!))}</span> from{" "}
            {previous.long}.
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

        <figure className="rounded-lg border border-slate-200 bg-white p-4">
          <figcaption className="text-sm font-medium text-slate-600">
            Running total, {current.long}
          </figcaption>
          <div className="mt-3 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={runningData}>
                <XAxis
                  dataKey="dayOfMonth"
                  tick={{ fill: AXIS, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `$${v}`}
                  tick={{ fill: AXIS, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip
                  formatter={(v) => money.format(Number(v))}
                  labelFormatter={(_, payload) => payload?.[0]?.payload.day ?? ""}
                />
                <Line
                  type="stepAfter"
                  dataKey="value"
                  name="Spent so far"
                  stroke={PINE}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">Cumulative spending by day of the month.</p>
        </figure>

        <figure className="rounded-lg border border-slate-200 bg-white p-4">
          <figcaption className="text-sm font-medium text-slate-600">
            Top merchants, {current.long}
          </figcaption>
          {merchantGroups.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No spending this month.</p>
          ) : (
            <div className="mt-3 space-y-4">
              {merchantGroups.map((g) => (
                <div key={g.category}>
                  <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {g.category}
                  </h3>
                  <ol className="mt-1 space-y-1 text-sm">
                    {g.merchants.map((m) => (
                      <li key={m.merchant} className="flex justify-between gap-4">
                        <span className="text-ink">
                          {m.merchant}
                          {m.count > 1 && <span className="text-slate-500"> × {m.count}</span>}
                        </span>
                        <span className="tabular-nums text-slate-700">{dollars(m.cents)}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          )}
        </figure>
      </div>
    </section>
  );
}
