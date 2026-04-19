import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import Layout from "../components/Layout.jsx";
import EmailComposer from "../components/EmailComposer.jsx";
import ScheduleReminder from "../components/ScheduleReminder.jsx";
import { api, fetchJson } from "../lib/api.js";

const HS_SYNC_KEY = "ai_crm_hubspot_sync_v1";

function readHsSync() {
  try {
    return JSON.parse(localStorage.getItem(HS_SYNC_KEY) || "{}");
  } catch {
    return {};
  }
}
function writeHsSync(recordId, payload) {
  try {
    const m = readHsSync();
    m[String(recordId)] = { ...payload, t: Date.now() };
    localStorage.setItem(HS_SYNC_KEY, JSON.stringify(m));
  } catch {
    /* ignore */
  }
}

function formatWhen(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return "—";
  }
}

function buildPreviewState(row) {
  const intent = String(row.intent || "").trim().toLowerCase();
  const intentVal = ["low", "medium", "high"].includes(intent) ? intent : "medium";
  return {
    budget: String(row.budget ?? ""),
    intent: intentVal,
    industry: row.industry || "",
    product: row.product || "",
    timeline: row.timeline || "",
    deal_score: row.deal_score ?? 0,
    risk_level: String(row.risk_level || "").toLowerCase().includes("high")
      ? "high"
      : String(row.risk_level || "").toLowerCase().includes("low")
        ? "low"
        : String(row.risk_level || "").toLowerCase().includes("medium")
          ? "medium"
          : "medium",
    summary: row.summary || "",
    next_action: row.next_action || "",
    pain_points: row.pain_points || "",
    mentioned_company: row.mentioned_company || "",
    procurement_stage: row.procurement_stage || "",
    use_case: row.use_case || "",
    decision_criteria: row.decision_criteria || "",
    budget_owner: row.budget_owner || "",
    implementation_scope: row.implementation_scope || "",
    stakeholders: Array.isArray(row.stakeholders) ? row.stakeholders.join(", ") : "",
    tags: Array.isArray(row.tags) ? row.tags.join(", ") : "",
    competitors: Array.isArray(row.competitors) ? row.competitors.join(", ") : "",
  };
}

function splitCsv(s) {
  return String(s || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

export default function RecordsPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const focusId = location.state?.focusId;
  const q = searchParams.get("q") ?? "";

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [sourceFilter, setSourceFilter] = useState("all");
  const [expanded, setExpanded] = useState(() => new Set());

  const [emailOpen, setEmailOpen] = useState(false);
  const [meetOpen, setMeetOpen] = useState(false);
  const [activeRow, setActiveRow] = useState(null);
  const [emailDraft, setEmailDraft] = useState({ to: "", subject: "", body: "" });
  const [genLoading, setGenLoading] = useState(false);

  const [hsOpen, setHsOpen] = useState(false);
  const [hsRecordId, setHsRecordId] = useState(null);
  const [hsEdits, setHsEdits] = useState(null);
  const [hsSaving, setHsSaving] = useState(false);
  const [hsSyncing, setHsSyncing] = useState({});
  const [hsNotice, setHsNotice] = useState({});
  const [hubspotMap, setHubspotMap] = useState(() => readHsSync());
  const [deleteAllBusy, setDeleteAllBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await fetchJson(api.crmRecords);
      setRows(Array.isArray(r) ? r : []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load records");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (focusId == null) return;
    setSearchParams({ q: String(focusId) }, { replace: true });
    setExpanded(new Set([Number(focusId)]));
  }, [focusId, setSearchParams]);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    return rows.filter((r) => {
      if (sourceFilter !== "all") {
        const st = String(r.source_type || "").toLowerCase();
        if (st !== sourceFilter.toLowerCase()) return false;
      }
      if (!t) return true;
      const hay = [
        String(r.id),
        r.content,
        r.intent,
        r.summary,
        r.mentioned_company,
        r.product,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(t);
    });
  }, [rows, q, sourceFilter]);

  const toggleExpand = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openHubspotPreview = (row) => {
    setHsRecordId(row.id);
    setHsEdits(buildPreviewState(row));
    setHsOpen(true);
  };

  const applyPatch = async () => {
    if (!hsEdits || hsRecordId == null) return false;
    setHsSaving(true);
    try {
      const body = {
        budget: hsEdits.budget,
        intent: hsEdits.intent,
        industry: hsEdits.industry,
        product: hsEdits.product,
        timeline: hsEdits.timeline,
        deal_score: Number(hsEdits.deal_score) || 0,
        risk_level: hsEdits.risk_level,
        summary: hsEdits.summary,
        next_action: hsEdits.next_action,
        pain_points: hsEdits.pain_points,
        mentioned_company: hsEdits.mentioned_company,
        procurement_stage: hsEdits.procurement_stage,
        use_case: hsEdits.use_case,
        decision_criteria: hsEdits.decision_criteria,
        budget_owner: hsEdits.budget_owner,
        implementation_scope: hsEdits.implementation_scope,
        stakeholders: splitCsv(hsEdits.stakeholders),
        tags: splitCsv(hsEdits.tags),
        competitors: splitCsv(hsEdits.competitors),
      };
      await fetchJson(api.crmRecord(hsRecordId), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await load();
      setHsNotice((n) => ({ ...n, [hsRecordId]: { type: "ok", message: "CRM record updated." } }));
      return true;
    } catch (e) {
      setHsNotice((n) => ({
        ...n,
        [hsRecordId]: { type: "err", message: e instanceof Error ? e.message : "Update failed" },
      }));
      return false;
    } finally {
      setHsSaving(false);
    }
  };

  const syncHubspot = async (recordId) => {
    setHsSyncing((s) => ({ ...s, [recordId]: true }));
    setHsNotice((n) => ({ ...n, [recordId]: null }));
    try {
      const data = await fetchJson(api.hubspotPush(recordId), { method: "POST" });
      writeHsSync(recordId, { dealId: data.hubspot_deal_id });
      setHubspotMap((m) => ({ ...m, [String(recordId)]: { dealId: data.hubspot_deal_id, t: Date.now() } }));
      setHsNotice((n) => ({
        ...n,
        [recordId]: {
          type: "ok",
          message: "Synced to HubSpot",
          linkUrl: data.deal_record_url || null,
        },
      }));
    } catch (e) {
      setHsNotice((n) => ({
        ...n,
        [recordId]: { type: "err", message: e instanceof Error ? e.message : "Sync failed" },
      }));
    } finally {
      setHsSyncing((s) => ({ ...s, [recordId]: false }));
    }
  };

  const deleteAllRecords = async () => {
    const ok = window.confirm(
      "Delete ALL CRM records and linked accounts, contacts, and deals? Database IDs will restart at 1. This cannot be undone.",
    );
    if (!ok) return;
    setDeleteAllBusy(true);
    setErr(null);
    try {
      await fetchJson(api.crmRecords, { method: "DELETE" });
      try {
        localStorage.removeItem(HS_SYNC_KEY);
      } catch {
        /* ignore */
      }
      setHubspotMap({});
      setExpanded(new Set());
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleteAllBusy(false);
    }
  };

  const openEmail = async (row) => {
    setActiveRow(row);
    setGenLoading(true);
    setEmailOpen(true);
    try {
      const data = await fetchJson(api.google.gmailGenerate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          record_id: row.id,
          summary: row.summary || "",
          pain_points: row.pain_points || "",
          next_action: row.next_action || "",
          mentioned_company: row.mentioned_company || "",
          contact_id: row.contact_id ?? null,
          deal_id: row.deal_id ?? null,
        }),
      });
      setEmailDraft({
        to: data?.to || "",
        subject: data?.subject || "",
        body: data?.body || "",
      });
    } catch (e) {
      setEmailDraft({
        to: "",
        subject: "",
        body: `Could not generate draft.\n${e instanceof Error ? e.message : ""}`,
      });
    } finally {
      setGenLoading(false);
    }
  };

  return (
    <Layout>
      <div className="py-6">
        <h2 className="mb-2 font-headline text-4xl font-extrabold tracking-tighter text-primary">CRM Records</h2>
        <p className="mb-6 text-on-surface-variant">
          Expand a row for full detail, HubSpot preview/sync, Gmail, and meetings.
        </p>

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <input
            type="search"
            value={q}
            onChange={(e) => {
              const v = e.target.value;
              if (v.trim()) setSearchParams({ q: v }, { replace: true });
              else setSearchParams({}, { replace: true });
            }}
            placeholder="Filter (synced with top search)…"
            className="max-w-md flex-1 rounded-full border border-outline-variant/30 bg-surface-container-high px-4 py-2 text-sm shadow-none outline-none ring-0 focus:border-outline-variant/30 focus:outline-none focus:ring-0 focus-visible:outline-none [&::-webkit-search-cancel-button]:appearance-none"
            aria-label="Filter records"
          />
          <div className="flex flex-wrap gap-1">
            {[
              ["all", "All"],
              ["call", "Call"],
              ["email", "Email"],
              ["meeting", "Meeting"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setSourceFilter(id)}
                className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase ${
                  sourceFilter === id ? "bg-primary text-on-primary" : "bg-surface-container-high text-on-surface-variant"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={load}
            className="rounded-full border border-outline-variant/30 px-4 py-2 text-xs font-bold uppercase text-primary"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={deleteAllRecords}
            disabled={deleteAllBusy || loading}
            className="rounded-full border border-error/40 bg-error/5 px-4 py-2 text-xs font-bold uppercase text-error disabled:opacity-50"
          >
            {deleteAllBusy ? "Deleting…" : "Delete all records"}
          </button>
        </div>

        {loading && <p className="text-on-surface-variant">Loading…</p>}
        {err && (
          <p className="text-error" role="alert">
            {err}
          </p>
        )}

        {!loading && !err && (
          <div className="overflow-x-auto rounded-xl border border-outline-variant/10 bg-surface-container-lowest shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-container text-[10px] font-black uppercase tracking-widest text-[#424b54]/50">
                <tr>
                  <th className="w-10 px-2 py-3" />
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Company / product</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Intent</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/10">
                {filtered.map((row) => (
                  <React.Fragment key={row.id}>
                    <tr className="hover:bg-surface-container-low/80">
                      <td className="px-2 py-3">
                        <button
                          type="button"
                          onClick={() => toggleExpand(row.id)}
                          className="rounded-lg p-1 text-primary hover:bg-surface-container-high"
                          aria-expanded={expanded.has(row.id)}
                          aria-label={expanded.has(row.id) ? "Collapse" : "Expand"}
                        >
                          <span className="material-symbols-outlined text-lg">
                            {expanded.has(row.id) ? "expand_less" : "expand_more"}
                          </span>
                        </button>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">#{row.id}</td>
                      <td className="max-w-[200px] truncate px-4 py-3 font-semibold text-primary">
                        {(row.mentioned_company || "").trim() || row.product || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs uppercase text-on-surface-variant">{row.source_type || "—"}</td>
                      <td className="px-4 py-3">{row.intent || "—"}</td>
                      <td className="px-4 py-3">{row.risk_level || "—"}</td>
                      <td className="px-4 py-3">{row.deal_score ?? "—"}</td>
                    </tr>
                    {expanded.has(row.id) && (
                      <tr className="bg-surface-container-low/50">
                        <td colSpan={7} className="px-4 py-6">
                          <div className="grid gap-6 md:grid-cols-2">
                            <div>
                              <p className="text-[10px] font-bold uppercase text-on-surface-variant">When</p>
                              <p className="text-sm">{formatWhen(row.created_at)}</p>
                              {row.summary?.trim() ? (
                                <>
                                  <p className="mt-4 text-[10px] font-bold uppercase text-on-surface-variant">Summary</p>
                                  <p className="mt-1 text-sm leading-relaxed text-on-surface">{row.summary}</p>
                                </>
                              ) : null}
                              <p className="mt-4 text-[10px] font-bold uppercase text-on-surface-variant">Next action</p>
                              <p className="mt-1 text-sm">{row.next_action?.trim() || "—"}</p>
                              <p className="mt-4 text-[10px] font-bold uppercase text-on-surface-variant">Pain points</p>
                              <p className="mt-1 text-sm">{row.pain_points?.trim() || "—"}</p>
                              <p className="mt-4 text-[10px] font-bold uppercase text-on-surface-variant">Mapping</p>
                              <p className="text-xs text-on-surface-variant">
                                Account {row.account_id ?? "—"} · Contact {row.contact_id ?? "—"} · Deal {row.deal_id ?? "—"}
                              </p>
                            </div>
                            <div>
                              <p className="text-[10px] font-bold uppercase text-on-surface-variant">Transcript excerpt</p>
                              <p className="mt-1 max-h-40 overflow-y-auto rounded-lg bg-surface-container-high p-3 text-xs leading-relaxed text-on-surface">
                                {(row.content || "").slice(0, 1200)}
                                {(row.content || "").length > 1200 ? "…" : ""}
                              </p>
                            </div>
                          </div>

                          <div className="mt-6 flex flex-wrap gap-2 border-t border-outline-variant/20 pt-4">
                            <button
                              type="button"
                              onClick={() => openHubspotPreview(row)}
                              className="rounded-full border border-secondary/40 bg-secondary/10 px-4 py-2 text-[10px] font-bold uppercase text-secondary"
                            >
                              Preview &amp; edit (HubSpot)
                            </button>
                            <button
                              type="button"
                              disabled={hsSyncing[row.id]}
                              onClick={() => syncHubspot(row.id)}
                              className="rounded-full bg-primary px-4 py-2 text-[10px] font-bold uppercase text-on-primary disabled:opacity-50"
                            >
                              {hsSyncing[row.id] ? "Syncing…" : hubspotMap[String(row.id)] ? "Re-sync HubSpot" : "Sync to HubSpot"}
                            </button>
                            <button
                              type="button"
                              onClick={() => openEmail(row)}
                              className="rounded-full bg-primary/10 px-4 py-2 text-[10px] font-bold uppercase text-primary"
                            >
                              AI Gmail draft
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setActiveRow(row);
                                setMeetOpen(true);
                              }}
                              className="rounded-full bg-secondary/15 px-4 py-2 text-[10px] font-bold uppercase text-secondary"
                            >
                              Schedule meeting
                            </button>
                          </div>

                          {hsNotice[row.id]?.message ? (
                            <p
                              className={`mt-3 text-xs ${hsNotice[row.id].type === "err" ? "text-error" : "text-emerald-800"}`}
                            >
                              {hsNotice[row.id].message}
                              {hsNotice[row.id].linkUrl ? (
                                <>
                                  {" "}
                                  <a
                                    href={hsNotice[row.id].linkUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="font-bold underline"
                                  >
                                    Open in HubSpot
                                  </a>
                                </>
                              ) : null}
                            </p>
                          ) : null}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <p className="p-8 text-center text-on-surface-variant">No records match.</p>
            )}
          </div>
        )}

        {genLoading && emailOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-primary/10 backdrop-blur-sm">
            <p className="rounded-lg bg-background px-4 py-2 text-sm font-medium">Generating draft…</p>
          </div>
        )}

        {emailOpen && activeRow && !genLoading && (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-primary/20 p-4 backdrop-blur-sm"
            role="presentation"
            onClick={() => setEmailOpen(false)}
          >
            <div onClick={(e) => e.stopPropagation()}>
              <EmailComposer
                contactId={activeRow.contact_id}
                dealId={activeRow.deal_id}
                defaultEmail={emailDraft.to}
                defaultSubject={emailDraft.subject}
                defaultBody={emailDraft.body}
                onClose={() => setEmailOpen(false)}
              />
            </div>
          </div>
        )}

        {meetOpen && activeRow && (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-primary/20 p-4 backdrop-blur-sm"
            role="presentation"
            onClick={() => setMeetOpen(false)}
          >
            <div onClick={(e) => e.stopPropagation()}>
              <ScheduleReminder
                contactId={activeRow.contact_id}
                dealId={activeRow.deal_id}
                defaultEmail=""
                onClose={() => setMeetOpen(false)}
              />
            </div>
          </div>
        )}

        {hsOpen && hsEdits && (
          <div
            className="fixed inset-0 z-[110] flex items-center justify-center bg-primary/30 p-4 backdrop-blur-sm"
            role="presentation"
            onClick={() => setHsOpen(false)}
          >
            <div
              className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-outline-variant/20 bg-surface-container-lowest p-6 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-headline text-lg font-bold text-primary">HubSpot preview · record #{hsRecordId}</h3>
                <button
                  type="button"
                  onClick={() => setHsOpen(false)}
                  className="rounded-full p-2 hover:bg-surface-container-high"
                  aria-label="Close"
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              <p className="mb-4 text-xs text-on-surface-variant">
                Edit fields, apply to CRM, then sync to HubSpot. Sync uses the saved CRM record on the server.
              </p>
              <div className="grid max-h-[55vh] grid-cols-1 gap-3 overflow-y-auto pr-1 md:grid-cols-2">
                {[
                  ["budget", "Budget", "text"],
                  ["industry", "Industry", "text"],
                  ["product", "Product", "text"],
                  ["timeline", "Timeline", "text"],
                  ["mentioned_company", "Company", "text"],
                  ["procurement_stage", "Stage", "text"],
                ].map(([k, label, type]) => (
                  <label key={k} className="text-xs font-bold uppercase text-on-surface-variant">
                    {label}
                    <input
                      type={type}
                      value={hsEdits[k] ?? ""}
                      onChange={(e) => setHsEdits((ed) => ({ ...ed, [k]: e.target.value }))}
                      className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm text-primary"
                    />
                  </label>
                ))}
                <label className="text-xs font-bold uppercase text-on-surface-variant">
                  Intent
                  <select
                    value={hsEdits.intent}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, intent: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </label>
                <label className="text-xs font-bold uppercase text-on-surface-variant">
                  Risk
                  <select
                    value={hsEdits.risk_level}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, risk_level: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </label>
                <label className="text-xs font-bold uppercase text-on-surface-variant">
                  Deal score
                  <input
                    type="number"
                    value={hsEdits.deal_score}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, deal_score: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="col-span-full text-xs font-bold uppercase text-on-surface-variant">
                  Summary
                  <textarea
                    rows={2}
                    value={hsEdits.summary}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, summary: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="col-span-full text-xs font-bold uppercase text-on-surface-variant">
                  Next action
                  <textarea
                    rows={2}
                    value={hsEdits.next_action}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, next_action: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="col-span-full text-xs font-bold uppercase text-on-surface-variant">
                  Pain points
                  <textarea
                    rows={2}
                    value={hsEdits.pain_points}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, pain_points: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="col-span-full text-xs font-bold uppercase text-on-surface-variant">
                  Stakeholders (comma-separated)
                  <input
                    value={hsEdits.stakeholders}
                    onChange={(e) => setHsEdits((ed) => ({ ...ed, stakeholders: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-outline-variant/30 bg-background px-2 py-1.5 text-sm"
                  />
                </label>
              </div>
              <div className="mt-6 flex flex-wrap gap-2 border-t border-outline-variant/20 pt-4">
                <button
                  type="button"
                  disabled={hsSaving}
                  onClick={() => applyPatch()}
                  className="rounded-full bg-surface-container-high px-4 py-2 text-xs font-bold uppercase text-primary"
                >
                  {hsSaving ? "Saving…" : "Apply to CRM"}
                </button>
                <button
                  type="button"
                  disabled={hsSaving || hsSyncing[hsRecordId]}
                  onClick={async () => {
                    const ok = await applyPatch();
                    if (!ok) return;
                    setHsOpen(false);
                    await syncHubspot(hsRecordId);
                  }}
                  className="rounded-full bg-primary px-4 py-2 text-xs font-bold uppercase text-on-primary disabled:opacity-50"
                >
                  Apply &amp; sync HubSpot
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
