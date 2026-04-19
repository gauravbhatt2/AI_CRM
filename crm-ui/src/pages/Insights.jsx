import React, { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout.jsx";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, fetchJson } from "../lib/api.js";

function parseBudget(v) {
  if (typeof v === "number") return v;
  const n = Number(String(v ?? "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function intentOk(raw, filter) {
  if (filter === "all") return true;
  const s = String(raw || "").toLowerCase();
  if (filter === "high") return s.includes("high");
  if (filter === "medium") return s.includes("medium");
  if (filter === "low") return s.includes("low");
  return true;
}

/**
 * AI Insights — keyword mention signals + interactive revenue/budget analysis only.
 * Executive KPIs and pipeline distributions live on Dashboard.
 */
export default function Insights() {
  const [insights, setInsights] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const [rangeLo, setRangeLo] = useState(0);
  const [rangeHi, setRangeHi] = useState(1_000_000);
  const [intent, setIntent] = useState("all");

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const [ins, rev] = await Promise.all([
          fetchJson(api.insights).catch(() => null),
          fetchJson(api.revenue).catch(() => null),
        ]);
        if (!c) {
          setInsights(ins);
          setRevenue(rev);
        }
      } catch (e) {
        if (!c) setErr(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, []);

  const budgetDomain = useMemo(() => {
    const rows = Array.isArray(revenue?.records) ? revenue.records : [];
    const maxVal = rows.reduce((m, r) => Math.max(m, parseBudget(r.budget)), 0);
    const cap =
      maxVal <= 0 ? 1_000_000 : Math.max(10_000, Math.ceil((maxVal * 1.05) / 10_000) * 10_000);
    const step = Math.max(1, Math.round(cap / 200));
    return { min: 0, max: cap, step };
  }, [revenue]);

  useEffect(() => {
    if (!revenue?.records) return;
    setRangeLo(0);
    setRangeHi(budgetDomain.max);
  }, [revenue, budgetDomain.max]);

  const filtered = useMemo(() => {
    const rows = Array.isArray(revenue?.records) ? revenue.records : [];
    return rows.filter((r) => {
      const b = parseBudget(r.budget);
      if (b < rangeLo || b > rangeHi) return false;
      return intentOk(r.intent, intent);
    });
  }, [revenue, rangeLo, rangeHi, intent]);

  const chartData = useMemo(
    () =>
      filtered.slice(0, 24).map((r) => ({
        label: `#${r.id}`,
        budget: parseBudget(r.budget),
      })),
    [filtered],
  );

  const totalBudget = useMemo(() => filtered.reduce((s, r) => s + parseBudget(r.budget), 0), [filtered]);

  return (
    <Layout>
      <div className="py-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Analytics</span>
        <h2 className="mt-1 font-headline text-4xl font-extrabold tracking-tighter text-primary">AI Insights</h2>
        <p className="mt-2 max-w-2xl font-body text-lg leading-relaxed text-on-surface-variant">
          Keyword mention signals from ingested text, plus a filterable revenue view. For KPIs and pipeline distributions, use{" "}
          <strong className="font-semibold text-primary/90">Dashboard</strong>.
        </p>

        {loading && <p className="mt-8 text-on-surface-variant">Loading…</p>}
        {err && (
          <p className="mt-8 text-error" role="alert">
            {err}
          </p>
        )}

        {!loading && insights && (
          <section className="mt-10">
            <h3 className="mb-2 font-headline text-sm font-bold uppercase tracking-widest text-secondary">Keyword signals</h3>
            <p className="mb-4 max-w-2xl text-sm text-on-surface-variant">
              Counts of strong vs exploratory intent phrasing detected across records (analytics pipeline).
            </p>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="rounded-xl border-l-4 border-primary bg-surface-container-low p-6 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">Strong intent mentions</p>
                <p className="mt-2 font-headline text-3xl font-black text-primary">{insights.intent_keywords_high ?? 0}</p>
              </div>
              <div className="rounded-xl border-l-4 border-primary-container bg-surface-container-low p-6 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">Exploratory mentions</p>
                <p className="mt-2 font-headline text-3xl font-black text-primary">{insights.intent_keywords_low ?? 0}</p>
              </div>
            </div>
          </section>
        )}

        {!loading && revenue && (
          <section className="mt-14">
            <h3 className="mb-2 font-headline text-sm font-bold uppercase tracking-widest text-secondary">Revenue &amp; budget explorer</h3>
            <p className="mb-4 max-w-2xl text-sm text-on-surface-variant">
              Adjust filters like a storefront — budget min/max and intent, then review the chart below.
            </p>

            {/* Compact filter strip (e-commerce style: single bar, no heavy card) */}
            <div className="border-y border-outline-variant/20 bg-background/80 py-3">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6 lg:px-1">
                <div className="flex flex-wrap items-center gap-3 lg:min-w-0 lg:flex-1">
                  <span className="w-14 shrink-0 text-[11px] font-bold uppercase tracking-wide text-on-surface-variant">Budget</span>
                  <div className="grid min-w-0 flex-1 grid-cols-1 gap-2 sm:max-w-xl">
                    <div className="flex items-center gap-2">
                      <span className="w-7 shrink-0 text-[10px] font-semibold text-on-surface-variant/80">Min</span>
                      <input
                        type="range"
                        min={budgetDomain.min}
                        max={budgetDomain.max}
                        step={budgetDomain.step}
                        value={rangeLo}
                        disabled={!revenue?.records?.length}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setRangeLo(Math.min(v, rangeHi));
                        }}
                        className="h-1 min-w-0 flex-1 cursor-pointer accent-primary disabled:opacity-40"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-7 shrink-0 text-[10px] font-semibold text-on-surface-variant/80">Max</span>
                      <input
                        type="range"
                        min={budgetDomain.min}
                        max={budgetDomain.max}
                        step={budgetDomain.step}
                        value={rangeHi}
                        disabled={!revenue?.records?.length}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setRangeHi(Math.max(v, rangeLo));
                        }}
                        className="h-1 min-w-0 flex-1 cursor-pointer accent-secondary disabled:opacity-40"
                      />
                    </div>
                  </div>
                  <div className="flex shrink-0 items-baseline gap-1.5 font-mono text-xs tabular-nums text-primary lg:border-l lg:border-outline-variant/25 lg:pl-4">
                    <span>{rangeLo.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                    <span className="text-on-surface-variant/60">—</span>
                    <span>{rangeHi.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                  <button
                    type="button"
                    disabled={!revenue?.records?.length}
                    onClick={() => {
                      setRangeLo(0);
                      setRangeHi(budgetDomain.max);
                    }}
                    className="shrink-0 text-[11px] font-bold uppercase tracking-wide text-secondary hover:underline disabled:opacity-40"
                  >
                    Clear
                  </button>
                </div>

                <div className="flex h-8 w-px shrink-0 bg-outline-variant/25 max-lg:hidden" aria-hidden />

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant">Intent</span>
                  <select
                    value={intent}
                    onChange={(e) => setIntent(e.target.value)}
                    className="rounded-md border-0 bg-surface-container-high py-1.5 pl-2 pr-8 text-xs font-semibold text-primary shadow-sm ring-1 ring-outline-variant/20 focus:outline-none focus:ring-2 focus:ring-secondary/25"
                  >
                    <option value="all">All</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm text-on-surface-variant">
              Filtered total budget:{" "}
              <span className="font-bold text-primary">{totalBudget.toLocaleString()}</span> · {filtered.length} record(s)
            </p>
            <div className="mt-8 h-96 rounded-xl bg-surface-container-low p-4">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ede1d5" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="budget" fill="#424b54" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="p-8 text-on-surface-variant">No rows match filters.</p>
              )}
            </div>
          </section>
        )}
      </div>
    </Layout>
  );
}
