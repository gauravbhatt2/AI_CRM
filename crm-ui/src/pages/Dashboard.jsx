import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion as Motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, fetchJson } from "../lib/api.js";

const PIE_COLORS = ["#76555f", "#424b54", "#bec7d2", "#614240", "#ede1d5"];

function parseBudget(v) {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  const n = Number(String(v ?? "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function riskRank(level) {
  const s = String(level || "").toLowerCase();
  if (s.includes("high")) return 1;
  if (s.includes("medium")) return 2;
  if (s.includes("low")) return 3;
  return 99;
}

/** Higher = stronger commercial intent (for sorting high → low). */
function intentStrength(raw) {
  const s = String(raw || "").toLowerCase();
  if (s.includes("high")) return 3;
  if (s.includes("medium")) return 2;
  if (s.includes("low")) return 1;
  return 0;
}

function parseTime(iso) {
  if (!iso) return 0;
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? t : 0;
}

function formatShortDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

const KPICard = ({ title, value, sub, trend, icon, borderClass }) => (
  <Motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`flex flex-col justify-between rounded-xl border-l-4 bg-surface-container-lowest p-8 shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] ${borderClass}`}
  >
    <div className="flex items-start justify-between">
      <span className="material-symbols-outlined text-primary-container">{icon}</span>
      {trend != null && trend !== "" && (
        <span className="rounded px-2 py-0.5 text-[10px] font-black text-primary">{trend}</span>
      )}
    </div>
    <div className="mt-4">
      <p className="font-headline text-xs font-bold uppercase tracking-tighter text-on-surface-variant">{title}</p>
      <h3 className="mt-1 font-headline text-3xl font-black text-primary">
        {value}
        {sub != null && sub !== "" && <span className="text-lg opacity-40">{sub}</span>}
      </h3>
    </div>
  </Motion.div>
);

const SORT_OPTIONS = [
  { id: "criticality", label: "Criticality" },
  { id: "intent", label: "Intent" },
  { id: "time", label: "Recent" },
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [insights, setInsights] = useState(null);
  const [aiIntel, setAiIntel] = useState(null);
  const [crm, setCrm] = useState([]);
  const [sortBy, setSortBy] = useState("criticality");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const [rev, ins, ai, rec] = await Promise.all([
          fetchJson(api.revenue).catch(() => null),
          fetchJson(api.insights).catch(() => null),
          fetchJson(api.aiIntel).catch(() => null),
          fetchJson(api.crmRecords).catch(() => []),
        ]);
        if (cancelled) return;
        setRevenue(rev);
        setInsights(ins);
        setAiIntel(ai);
        setCrm(Array.isArray(rec) ? rec : []);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const totalRecords = revenue?.total_records ?? aiIntel?.total_records ?? crm.length ?? 0;
  const avgDealScore = aiIntel?.avg_deal_score ?? "—";
  const highRisk = aiIntel?.risk_distribution?.high ?? 0;
  const avgBudget = insights?.avg_budget != null ? Number(insights.avg_budget) : null;

  const budgetBars = useMemo(() => {
    const rows = Array.isArray(revenue?.records) ? revenue.records : [];
    const sorted = [...rows]
      .map((r) => ({
        id: r.id,
        label: `#${r.id}`,
        budget: parseBudget(r.budget),
      }))
      .filter((r) => r.budget > 0)
      .sort((a, b) => b.budget - a.budget)
      .slice(0, 12);
    return sorted.length ? sorted : [{ id: 0, label: "—", budget: 0 }];
  }, [revenue]);

  const sortedRecords = useMemo(() => {
    const rows = [...crm];
    if (sortBy === "intent") {
      rows.sort((a, b) => intentStrength(b.intent) - intentStrength(a.intent) || b.id - a.id);
    } else if (sortBy === "time") {
      rows.sort((a, b) => parseTime(b.created_at) - parseTime(a.created_at));
    } else {
      rows.sort((a, b) => {
        const ra = riskRank(a.risk_level);
        const rb = riskRank(b.risk_level);
        if (ra !== rb) return ra - rb;
        const sa = Number(a.deal_score) || 0;
        const sb = Number(b.deal_score) || 0;
        if (sa !== sb) return sb - sa;
        return parseTime(b.created_at) - parseTime(a.created_at);
      });
    }
    return rows;
  }, [crm, sortBy]);

  const urgent = useMemo(() => {
    const rows = [...crm].sort((a, b) => riskRank(a.risk_level) - riskRank(b.risk_level));
    return rows.filter((r) => String(r.risk_level || "").toLowerCase().includes("high")).slice(0, 4);
  }, [crm]);

  const intentPie = useMemo(() => {
    const dist = aiIntel?.intent_distribution;
    if (!dist || typeof dist !== "object") return [];
    return Object.entries(dist).map(([name, value]) => ({ name, value: Number(value) || 0 }));
  }, [aiIntel]);

  const riskPie = useMemo(() => {
    const dist = aiIntel?.risk_distribution;
    if (!dist || typeof dist !== "object") return [];
    return Object.entries(dist).map(([name, value]) => ({ name, value: Number(value) || 0 }));
  }, [aiIntel]);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center font-body text-on-surface-variant">
        Loading dashboard…
      </div>
    );
  }

  if (err) {
    return (
      <div className="rounded-xl border border-error/30 bg-error-container/20 p-6 text-sm text-error" role="alert">
        {err}
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-col items-end justify-between gap-4 md:flex-row md:items-end">
        <div className="max-w-2xl">
          <Motion.h2
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="font-headline text-4xl font-extrabold leading-tight text-on-surface"
          >
            Strategic overview
          </Motion.h2>
          <Motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="mt-2 font-body text-lg text-on-surface-variant"
          >
            Executive snapshot of pipeline health, risk, and engagement across ingested CRM data.
          </Motion.p>
        </div>
        <div className="flex gap-3">
          <Motion.button
            type="button"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => navigate("/upload")}
            className="flex items-center gap-2 rounded-full bg-primary px-6 py-2.5 font-headline text-xs font-bold uppercase tracking-widest text-on-primary shadow-lg shadow-primary/10 transition-all hover:shadow-primary/20"
          >
            <span className="material-symbols-outlined text-sm">add</span>
            New upload
          </Motion.button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total records"
          value={totalRecords.toLocaleString()}
          trend=""
          icon="storage"
          borderClass="border-primary"
        />
        <KPICard
          title="Avg deal score"
          value={typeof avgDealScore === "number" ? avgDealScore : avgDealScore}
          sub={typeof avgDealScore === "number" ? "/100" : ""}
          trend=""
          icon="analytics"
          borderClass="border-secondary"
        />
        <KPICard
          title="High risk"
          value={String(highRisk)}
          trend=""
          icon="warning"
          borderClass="border-tertiary-fixed-dim"
        />
        <KPICard
          title="Avg budget (insights)"
          value={avgBudget != null ? avgBudget.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
          trend=""
          icon="payments"
          borderClass="border-primary-container"
        />
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="relative col-span-12 h-[400px] overflow-hidden rounded-xl bg-surface-container-low p-8 lg:col-span-8">
          <div className="relative z-10 mb-6 flex items-start justify-between">
            <div>
              <h4 className="font-headline text-xl font-bold">Budget by record (top)</h4>
              <p className="text-sm text-on-surface-variant">From analytics revenue feed</p>
            </div>
          </div>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={budgetBars} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ede1d5" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid #ede1d5",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="budget" fill="#76555f" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="relative col-span-12 flex flex-col overflow-hidden rounded-xl bg-[#B38D97]/10 p-8 lg:col-span-4">
          <div className="relative z-10">
            <div className="mb-4 flex items-center gap-2 text-secondary">
              <span className="material-symbols-outlined">auto_awesome</span>
              <p className="font-headline text-xs font-bold uppercase tracking-widest">Priority</p>
            </div>
            <h4 className="mb-4 font-headline text-xl font-bold">High-risk records</h4>
            <div className="space-y-4">
              {urgent.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No high-risk records yet.</p>
              ) : (
                urgent.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    onClick={() => navigate("/records", { state: { focusId: row.id } })}
                    className="group flex w-full cursor-pointer gap-4 text-left"
                  >
                    <div className="w-1 rounded-full bg-error transition-all group-hover:w-2" />
                    <div>
                      <p className="text-sm font-bold text-on-surface">
                        #{row.id} · {(row.mentioned_company || "").trim() || "Record"}
                      </p>
                      <p className="mt-1 line-clamp-2 text-xs text-on-surface-variant">
                        {(row.summary || "").slice(0, 140) || row.content?.slice(0, 140) || "—"}
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {aiIntel && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="rounded-xl bg-surface-container-lowest p-8 shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)]">
            <h4 className="mb-1 font-headline text-lg font-bold text-primary">Interaction mix</h4>
            <p className="mb-4 text-sm text-on-surface-variant">By type across the pipeline (AI intelligence feed).</p>
            <div className="h-64">
              {intentPie.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={intentPie}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={72}
                      paddingAngle={2}
                    >
                      {intentPie.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-on-surface-variant">No distribution yet.</p>
              )}
            </div>
          </div>
          <div className="rounded-xl bg-surface-container-lowest p-8 shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)]">
            <h4 className="mb-1 font-headline text-lg font-bold text-primary">Risk mix</h4>
            <p className="mb-4 text-sm text-on-surface-variant">High / medium / low classification counts.</p>
            <div className="h-64">
              {riskPie.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskPie}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={72}
                      paddingAngle={2}
                    >
                      {riskPie.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-on-surface-variant">No distribution yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-xl bg-surface-container-lowest p-6 shadow-[12px_12px_32px_-4px_rgba(32,27,20,0.04)] md:p-8">
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h4 className="font-headline text-lg font-bold text-primary">All records</h4>
            <p className="mt-1 text-sm text-on-surface-variant">
              Sort by intent strength, recency, or criticality (risk &amp; score). Click a row to open it in CRM Records.
            </p>
          </div>
          <div className="flex flex-wrap gap-1 rounded-full bg-surface-container-high p-1">
            {SORT_OPTIONS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setSortBy(id)}
                className={`rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors ${
                  sortBy === id ? "bg-primary text-on-primary shadow-sm" : "text-on-surface-variant hover:text-primary"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-outline-variant/15">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-outline-variant/15 bg-surface-container-low/80 text-[10px] font-black uppercase tracking-widest text-[#424b54]/60">
              <tr>
                <th className="px-4 py-3">Record</th>
                <th className="px-4 py-3">Company / product</th>
                <th className="px-4 py-3">Intent</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3 text-right">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/10">
              {sortedRecords.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-on-surface-variant">
                    No CRM records yet. Upload content to populate this list.
                  </td>
                </tr>
              ) : (
                sortedRecords.map((row) => (
                  <tr
                    key={row.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate("/records", { state: { focusId: row.id } })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        navigate("/records", { state: { focusId: row.id } });
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-surface-container-low/90"
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs font-semibold text-primary">#{row.id}</td>
                    <td className="max-w-[220px] truncate px-4 py-3 font-medium text-on-surface">
                      {(row.mentioned_company || "").trim() || row.product || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs uppercase text-on-surface-variant">{row.intent || "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-on-surface-variant">{formatShortDate(row.created_at)}</td>
                    <td className="px-4 py-3 text-xs font-medium text-on-surface">{row.risk_level || "—"}</td>
                    <td className="px-4 py-3 text-right font-mono text-xs">{row.deal_score ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
