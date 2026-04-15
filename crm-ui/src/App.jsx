import { useCallback, useEffect, useMemo, useState } from "react";
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
import "./crm-app.css";

const API_URL = "http://127.0.0.1:8000/ingest/audio";
const TRANSCRIPT_API_URL = "http://127.0.0.1:8000/ingest/transcript";
const REVENUE_API_URL = "http://127.0.0.1:8000/api/v1/analytics/revenue";
const INSIGHTS_API_URL = "http://127.0.0.1:8000/api/v1/analytics/insights";
const TIMELINE_API_URL = "http://127.0.0.1:8000/api/v1/interactions/timeline";
const CRM_RECORDS_API_URL = "http://127.0.0.1:8000/api/v1/crm/records";
const HUBSPOT_PUSH_API_BASE = "http://127.0.0.1:8000/api/v1/hubspot/push";
const AI_INTEL_API_URL = "http://127.0.0.1:8000/api/v1/analytics/ai-intelligence";

const HS_SYNC_STORAGE_KEY = "ai_crm_hubspot_sync_v1";
const CRM_HUBSPOT_FIELD_KEYS = [
  "pain_points",
  "next_step",
  "procurement_stage",
  "mentioned_company",
];
const CRM_HUBSPOT_FIELD_LABELS = {
  pain_points: "Pain points",
  next_step: "Next step",
  procurement_stage: "Procurement stage",
  mentioned_company: "Mentioned company",
};

function readHubspotSyncMap() {
  try {
    return JSON.parse(localStorage.getItem(HS_SYNC_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeHubspotSyncRecord(recordId, payload) {
  try {
    const m = readHubspotSyncMap();
    m[String(recordId)] = { ...payload, t: Date.now() };
    localStorage.setItem(HS_SYNC_STORAGE_KEY, JSON.stringify(m));
  } catch {
    /* ignore */
  }
}

function getCrmHubspotKeyEntries(customFields) {
  if (!customFields || typeof customFields !== "object") return [];
  return CRM_HUBSPOT_FIELD_KEYS.map((k) => [
    k,
    customFields[k],
    CRM_HUBSPOT_FIELD_LABELS[k] || k,
  ]).filter(([, v]) => v != null && String(v).trim() !== "");
}

function getOtherCustomEntries(customFields) {
  if (!customFields || typeof customFields !== "object") return [];
  return Object.entries(customFields).filter(
    ([k, v]) =>
      !CRM_HUBSPOT_FIELD_KEYS.includes(k) &&
      v != null &&
      String(v).trim() !== "",
  );
}

function formatTimestamp(sec) {
  if (sec == null || Number.isNaN(Number(sec))) return "—";
  const s = Math.floor(Number(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function intentMatchesFilter(intentRaw, filter) {
  if (filter === "all") return true;
  const s = (intentRaw || "").toLowerCase();
  if (filter === "high") return s.includes("high");
  if (filter === "medium") return s.includes("medium");
  if (filter === "low") return s.includes("low");
  return false;
}

function friendlyFetchError(message) {
  if (message === "Failed to fetch" || message === "Load failed") {
    return (
      "Cannot reach the API. Start the FastAPI server on port 8000 " +
      "(e.g. uvicorn app.main:app --reload), then try again. " +
      "CORS allows this Vite dev URL."
    );
  }
  return message;
}

function parseApiError(text, status) {
  try {
    const data = text ? JSON.parse(text) : {};
    if (typeof data.detail === "string") return data.detail;
  } catch {
    /* ignore */
  }
  return `Request failed (${status})`;
}

function excerpt(text, max = 220) {
  const s = (text || "").trim();
  if (!s) return "";
  if (s.length <= max) return s;
  return `${s.slice(0, max).trim()}…`;
}

function formatRecordWhen(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return null;
  }
}

/** Tooltip: mapping_method is local Account/Contact/Deal linking — not Groq field extraction. */
const CRM_ENTITY_LINK_HELP =
  "How this row links to Account / Contact / Deal in this app’s database. " +
  "This is not the AI extraction method and does not mean transcript fields used a fallback.";

/**
 * Human label for `mapping_method` (llm | rules | rules_fallback).
 * `rules_fallback` means an AI CRM-link suggestion existed but was not applied; rules were used.
 */
function describeCrmMappingMethod(method) {
  const m = (method || "").trim().toLowerCase();
  if (m === "llm") return "Entity links: AI-assisted";
  if (m === "rules") return "Entity links: rules-based";
  if (m === "rules_fallback") {
    return "Entity links: rules (AI link step not applied)";
  }
  return (method || "").trim() || "—";
}

/* ── Design tokens (mirrored in JS for runtime badge colours) ── */
const INTENT_COLORS = {
  sales:     { bg: "#dbeafe", color: "#1d4ed8", border: "#93c5fd" },
  support:   { bg: "#fef9c3", color: "#854d0e", border: "#fde047" },
  inquiry:   { bg: "#ede9fe", color: "#5b21b6", border: "#c4b5fd" },
  complaint: { bg: "#fee2e2", color: "#991b1b", border: "#fca5a5" },
};

const RISK_CONFIG = {
  high:   { color: "#dc2626", bg: "#fee2e2", icon: "⚠", label: "High"   },
  medium: { color: "#d97706", bg: "#fef3c7", icon: "◉", label: "Medium" },
  low:    { color: "#16a34a", bg: "#f0fdf4", icon: "✓", label: "Low"    },
};

const PIE_COLORS = ["#6366f1", "#f59e0b", "#22c55e", "#ef4444", "#3b82f6", "#ec4899"];

/* ── Shared mini-components ─────────────────────────────────────────── */

function IntentBadge({ type }) {
  const c = INTENT_COLORS[type] || { bg: "#f1f5f9", color: "#475569", border: "#cbd5e1" };
  return (
    <span className="crm-ai-badge" style={{ background: c.bg, color: c.color, borderColor: c.border }}>
      {type || "—"}
    </span>
  );
}

function RiskIndicator({ level }) {
  const c = RISK_CONFIG[level] || { color: "#64748b", bg: "#f1f5f9", icon: "—", label: "—" };
  return (
    <span className="crm-ai-risk" style={{ background: c.bg, color: c.color }}>
      <span className="crm-ai-risk-icon" aria-hidden="true">{c.icon}</span>
      {c.label}
    </span>
  );
}

function DealScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, Number(score) || 0));
  const color = pct >= 70 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="crm-ai-score-wrap">
      <div className="crm-ai-score-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="crm-ai-score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="crm-ai-score-val">{pct}</span>
    </div>
  );
}

function Spinner({ size = 14, color = "rgba(255,255,255,.35)", topColor = "#fff" }) {
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-block",
        width: size, height: size,
        border: `2px solid ${color}`,
        borderTopColor: topColor,
        borderRadius: "50%",
        animation: "crm-spin 0.65s linear infinite",
        flexShrink: 0,
      }}
    />
  );
}

function EmptyState({ text }) {
  return (
    <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--muted)" }}>
      <div style={{ fontSize: "2rem", marginBottom: 10 }}>🗂</div>
      <p style={{ margin: 0, fontSize: "0.9rem", fontWeight: 600 }}>{text}</p>
    </div>
  );
}

function App() {
  const [inputMode, setInputMode] = useState("audio");
  const [textSource, setTextSource] = useState("call");
  const [file, setFile] = useState(null);
  const [transcriptText, setTranscriptText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const [revenueData, setRevenueData] = useState(null);
  const [revenueLoading, setRevenueLoading] = useState(true);
  const [revenueError, setRevenueError] = useState(null);
  const [analyticsBudgetMin, setAnalyticsBudgetMin] = useState("");
  const [analyticsBudgetMax, setAnalyticsBudgetMax] = useState("");
  const [analyticsIntent, setAnalyticsIntent] = useState("all");

  const [crmRecords, setCrmRecords] = useState(null);
  const [crmRecordsLoading, setCrmRecordsLoading] = useState(true);
  const [crmRecordsError, setCrmRecordsError] = useState(null);
  const [recordsQuery, setRecordsQuery] = useState("");
  const [recordsSourceFilter, setRecordsSourceFilter] = useState("all");
  const [recordsDeleting, setRecordsDeleting] = useState(false);
  const [syncingByRecord, setSyncingByRecord] = useState({});
  const [hubspotNoticeByRecord, setHubspotNoticeByRecord] = useState({});
  const [hubspotSyncMap, setHubspotSyncMap] = useState({});

  const [insightsData, setInsightsData] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(true);
  const [insightsError, setInsightsError] = useState(null);

  const [timelineItems, setTimelineItems] = useState(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState(null);

  const [aiIntelData, setAiIntelData] = useState(null);
  const [aiIntelLoading, setAiIntelLoading] = useState(true);
  const [aiIntelError, setAiIntelError] = useState(null);

  const [activeSection, setActiveSection] = useState("dashboard");

  const filteredRevenueRecords = useMemo(() => {
    if (!revenueData?.records?.length) return [];
    const minRaw = analyticsBudgetMin.trim().replace(/,/g, "");
    const maxRaw = analyticsBudgetMax.trim().replace(/,/g, "");
    const minN = minRaw === "" ? null : Number(minRaw);
    const maxN = maxRaw === "" ? null : Number(maxRaw);

    return revenueData.records.filter((r) => {
      const b = typeof r.budget === "number" ? r.budget : 0;
      if (minN !== null && !Number.isNaN(minN) && b < minN) return false;
      if (maxN !== null && !Number.isNaN(maxN) && b > maxN) return false;
      if (!intentMatchesFilter(r.intent, analyticsIntent)) return false;
      return true;
    });
  }, [revenueData, analyticsBudgetMin, analyticsBudgetMax, analyticsIntent]);

  const filteredRevenueTotalBudget = useMemo(
    () =>
      filteredRevenueRecords.reduce(
        (sum, r) => sum + (Number(r.budget) || 0),
        0,
      ),
    [filteredRevenueRecords],
  );

  const filteredCrmRecords = useMemo(() => {
    if (!Array.isArray(crmRecords)) return [];
    const q = recordsQuery.trim().toLowerCase();
    return crmRecords.filter((r) => {
      if (recordsSourceFilter !== "all") {
        const st = (r.source_type || "").toLowerCase();
        if (st !== recordsSourceFilter.toLowerCase()) return false;
      }
      if (!q) return true;
      const hay = [
        String(r.id),
        r.content,
        r.intent,
        r.industry,
        r.product,
        r.timeline,
        ...(Array.isArray(r.competitors) ? r.competitors : []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [crmRecords, recordsQuery, recordsSourceFilter]);

  const resetAnalyticsFilters = () => {
    setAnalyticsBudgetMin("");
    setAnalyticsBudgetMax("");
    setAnalyticsIntent("all");
  };

  const refreshDashboard = useCallback(async () => {
    try {
      const [revRes, crmRes, insRes, aiRes] = await Promise.all([
        fetch(REVENUE_API_URL, { mode: "cors", cache: "no-store" }),
        fetch(CRM_RECORDS_API_URL, { mode: "cors", cache: "no-store" }),
        fetch(INSIGHTS_API_URL, { mode: "cors", cache: "no-store" }),
        fetch(AI_INTEL_API_URL, { mode: "cors", cache: "no-store" }),
      ]);
      const revText = await revRes.text();
      const crmText = await crmRes.text();
      const insText = await insRes.text();
      const aiText = await aiRes.text();
      let revData = {};
      let crmData = [];
      let insData = {};
      let aiData = {};
      try {
        revData = revText ? JSON.parse(revText) : {};
      } catch {
        /* ignore */
      }
      try {
        crmData = crmText ? JSON.parse(crmText) : [];
      } catch {
        /* ignore */
      }
      try {
        insData = insText ? JSON.parse(insText) : {};
      } catch {
        /* ignore */
      }
      try {
        aiData = aiText ? JSON.parse(aiText) : {};
      } catch {
        /* ignore */
      }
      if (revRes.ok) {
        setRevenueData({
          total_records: revData.total_records ?? 0,
          total_budget: revData.total_budget ?? 0,
          records: Array.isArray(revData.records) ? revData.records : [],
        });
        setRevenueError(null);
      } else {
        setRevenueError(
          friendlyFetchError(parseApiError(revText, revRes.status)),
        );
        setRevenueData(null);
      }
      if (crmRes.ok) {
        setCrmRecords(Array.isArray(crmData) ? crmData : []);
        setCrmRecordsError(null);
      } else {
        setCrmRecordsError(
          friendlyFetchError(parseApiError(crmText, crmRes.status)),
        );
        setCrmRecords(null);
      }
      if (insRes.ok) {
        setInsightsData(insData);
        setInsightsError(null);
      } else {
        setInsightsError(
          friendlyFetchError(parseApiError(insText, insRes.status)),
        );
        setInsightsData(null);
      }
      if (aiRes.ok) {
        setAiIntelData(aiData);
        setAiIntelError(null);
      } else {
        setAiIntelError(
          friendlyFetchError(parseApiError(aiText, aiRes.status)),
        );
        setAiIntelData(null);
      }
    } catch (err) {
      const raw =
        err instanceof Error ? err.message : "Failed to refresh dashboard.";
      setRevenueError(friendlyFetchError(raw));
      setCrmRecordsError(friendlyFetchError(raw));
      setInsightsError(friendlyFetchError(raw));
      setAiIntelError(friendlyFetchError(raw));
    }
  }, []);

  const handleDeleteAllRecords = async () => {
    if (
      !window.confirm(
        "Delete every CRM record in the database? This cannot be undone.",
      )
    ) {
      return;
    }
    setRecordsDeleting(true);
    setCrmRecordsError(null);
    try {
      const res = await fetch(CRM_RECORDS_API_URL, {
        method: "DELETE",
        mode: "cors",
        cache: "no-store",
      });
      const text = await res.text();
      if (!res.ok) {
        throw new Error(parseApiError(text, res.status));
      }
      await refreshDashboard();
    } catch (err) {
      const raw =
        err instanceof Error ? err.message : "Failed to delete records.";
      setCrmRecordsError(friendlyFetchError(raw));
    } finally {
      setRecordsDeleting(false);
    }
  };

  const pushToHubspot = async (recordId) => {
    setSyncingByRecord((prev) => ({ ...prev, [recordId]: true }));
    setHubspotNoticeByRecord((prev) => ({ ...prev, [recordId]: null }));
    try {
      const res = await fetch(`${HUBSPOT_PUSH_API_BASE}/${recordId}`, {
        method: "POST",
        mode: "cors",
        cache: "no-store",
      });
      const text = await res.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = {};
      }
      if (!res.ok) {
        throw new Error(parseApiError(text, res.status));
      }
      const dealId = data.hubspot_deal_id || data.hubspot?.id;
      const openUrl = data.deal_record_url;
      const parts = ["Synced to HubSpot ✅"];
      if (dealId) parts.push(`Deal #${dealId}`);
      if (data.hubspot_contact_id) parts.push(`Contact linked`);
      if (data.hubspot_company_id) parts.push(`Company linked`);
      if (data.hubspot_note_id) parts.push(`Transcript note added`);
      const msg = parts.join(" · ");
      writeHubspotSyncRecord(recordId, {
        dealId: dealId || null,
        url: openUrl || null,
      });
      setHubspotSyncMap((prev) => ({
        ...prev,
        [String(recordId)]: {
          dealId: dealId || null,
          url: openUrl || null,
          t: Date.now(),
        },
      }));
      setHubspotNoticeByRecord((prev) => ({
        ...prev,
        [recordId]: {
          type: "success",
          message: msg,
          linkUrl: openUrl || null,
        },
      }));
    } catch (err) {
      const raw = err instanceof Error ? err.message : "HubSpot sync failed.";
      setHubspotNoticeByRecord((prev) => ({
        ...prev,
        [recordId]: { type: "error", message: friendlyFetchError(raw) },
      }));
    } finally {
      setSyncingByRecord((prev) => ({ ...prev, [recordId]: false }));
    }
  };

  useEffect(() => {
    setHubspotSyncMap(readHubspotSyncMap());
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setRevenueLoading(true);
      setCrmRecordsLoading(true);
      setInsightsLoading(true);
      setAiIntelLoading(true);
      setRevenueError(null);
      setCrmRecordsError(null);
      setInsightsError(null);
      setAiIntelError(null);
      try {
        await refreshDashboard();
      } finally {
        if (!cancelled) {
          setRevenueLoading(false);
          setCrmRecordsLoading(false);
          setInsightsLoading(false);
          setAiIntelLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [refreshDashboard]);

  useEffect(() => {
    if (activeSection !== "timeline") return;
    let cancelled = false;

    async function loadTimeline() {
      setTimelineLoading(true);
      setTimelineError(null);
      try {
        const res = await fetch(`${TIMELINE_API_URL}?limit=200`, {
          mode: "cors",
          cache: "no-store",
        });
        const text = await res.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch {
          throw new Error(text || `Request failed (${res.status})`);
        }
        if (!res.ok) {
          throw new Error(parseApiError(text, res.status));
        }
        const items = Array.isArray(data.items) ? data.items : [];
        if (!cancelled) setTimelineItems(items);
      } catch (err) {
        const raw =
          err instanceof Error ? err.message : "Failed to load timeline.";
        if (!cancelled) {
          setTimelineError(friendlyFetchError(raw));
          setTimelineItems(null);
        }
      } finally {
        if (!cancelled) setTimelineLoading(false);
      }
    }

    loadTimeline();
    return () => {
      cancelled = true;
    };
  }, [activeSection]);

  const handleFileChange = (e) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setError(null);
    setResult(null);
  };

  const handleInputModeChange = (mode) => {
    setInputMode(mode);
    setError(null);
  };

  const parseIngestError = (data, status) => {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => d.msg || d).join(" ");
    }
    return `Request failed (${status})`;
  };

  const handleProcess = async () => {
    if (inputMode === "audio") {
      if (!file) {
        setError("Please choose an audio file first.");
        return;
      }
    } else {
      const trimmed = transcriptText.trim();
      if (!trimmed) {
        setError("Please enter transcript text.");
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      if (inputMode === "audio") {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(API_URL, {
          method: "POST",
          body: formData,
          mode: "cors",
          cache: "no-store",
        });

        const text = await res.text();
        let data;
        try {
          data = text ? JSON.parse(text) : {};
        } catch {
          throw new Error(text || `Request failed (${res.status})`);
        }

        if (!res.ok) {
          throw new Error(
            parseIngestError(data, res.status) || `HTTP ${res.status}`,
          );
        }

        setResult(data);
        await refreshDashboard();
      } else {
        const trimmed = transcriptText.trim();

        const res = await fetch(TRANSCRIPT_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: trimmed,
            metadata: { ui_text_source: textSource },
            external_id: "ui_input",
            source_type: textSource,
          }),
          mode: "cors",
          cache: "no-store",
        });

        const text = await res.text();
        let data;
        try {
          data = text ? JSON.parse(text) : {};
        } catch {
          throw new Error(text || `Request failed (${res.status})`);
        }

        if (!res.ok) {
          throw new Error(
            parseIngestError(data, res.status) || `HTTP ${res.status}`,
          );
        }

        setResult({ ...data, transcript: trimmed });
        await refreshDashboard();
      }
    } catch (err) {
      const raw =
        err instanceof Error ? err.message : "Something went wrong. Try again.";
      setError(friendlyFetchError(raw));
    } finally {
      setLoading(false);
    }
  };

  const textPlaceholders = {
    call: "Paste a sales call transcript…",
    email: "Paste email thread or body (signatures are fine)…",
    meeting: "Paste meeting notes or calendar description…",
    sms: "Paste SMS or chat thread…",
    crm_update: "Paste CRM activity note, task outcome, or field change log…",
  };

  const ex = result?.extracted;
  /** Show em dash when field is missing, null, or whitespace-only (empty string is not nullish). */
  const showField = (v) =>
    v != null && String(v).trim() !== "" ? String(v).trim() : "—";
  const hubspotKeyEntries = getCrmHubspotKeyEntries(ex?.custom_fields);
  const customEntriesOther = getOtherCustomEntries(ex?.custom_fields);

  function renderUploadError() {
    if (!error) return null;
    return (
      <div className="crm-error" role="alert">
        <strong>Something went wrong</strong>
        {error}
      </div>
    );
  }

  function renderUploadResults() {
    if (!result || loading) return null;

    const transcriptBlock =
      result.structured_transcript?.segments?.length > 0 ? (
        <div className="crm-card">
          <div className="crm-section-title-row">
            <span className="crm-section-title" style={{ marginBottom: 0 }}>Transcript</span>
            <span className="crm-meta-pill">
              {result.structured_transcript.segments.length} segments · speakers
            </span>
          </div>
          <div className="crm-seg-list">
            {result.structured_transcript.segments.map((seg, i) => (
              <div key={i} className="crm-seg">
                <div className="crm-seg-head">
                  <span className="crm-seg-time">{formatTimestamp(seg.start)} – {formatTimestamp(seg.end)}</span>
                  {seg.speaker && <span className="crm-seg-sp">{seg.speaker}</span>}
                </div>
                <p className="crm-seg-body">{seg.text}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="crm-card">
          <span className="crm-section-title">Transcript</span>
          <div className="crm-transcript">{result.transcript || "—"}</div>
        </div>
      );

    return (
      <>
        {/* ── Hero result card ── */}
        <div className="crm-card crm-card--elevated">
          <div className="crm-result-hero">
            <div className="crm-result-hero-main">
              <p className="crm-result-hero-title">✅ Ingestion complete</p>
              <p className="crm-result-hero-sub">
                AI extraction, deal scoring, and risk analysis saved to CRM.
              </p>
            </div>
            <div className="crm-result-hero-ids">
              <span className="crm-id-chip">
                <span className="crm-id-chip-lbl">Job</span>
                {result.job_id || "—"}
              </span>
              <span className="crm-id-chip">
                <span className="crm-id-chip-lbl">Record</span>
                #{result.record_id ?? "—"}
              </span>
            </div>
          </div>
          <div className="crm-result-strip">
            <div className="crm-strip-item">
              <div className="crm-strip-label">Budget</div>
              <div className="crm-strip-value">{showField(ex?.budget)}</div>
            </div>
            <div className="crm-strip-item">
              <div className="crm-strip-label">Intent</div>
              <div className="crm-strip-value">{showField(ex?.intent)}</div>
            </div>
            <div className="crm-strip-item">
              <div className="crm-strip-label">Timeline</div>
              <div className="crm-strip-value">{showField(ex?.timeline)}</div>
            </div>
          </div>
        </div>

        {/* ── Entity mapping ── */}
        <div className="crm-card">
          <div className="crm-section-title-row">
            <span className="crm-section-title" style={{ marginBottom: 0 }}>Entity mapping</span>
            <span className="crm-meta-pill" title={CRM_ENTITY_LINK_HELP}>
              {describeCrmMappingMethod(result.mapping_method)} · {result.source_type || "—"}
            </span>
          </div>
          <div className="crm-mapping">
            <div className="crm-map-item"><div className="crm-map-label">Account</div><div className="crm-map-id">{result.account_id ?? "—"}</div></div>
            <div className="crm-map-item"><div className="crm-map-label">Contact</div><div className="crm-map-id">{result.contact_id ?? "—"}</div></div>
            <div className="crm-map-item"><div className="crm-map-label">Deal</div><div className="crm-map-id">{result.deal_id ?? "—"}</div></div>
          </div>
        </div>

        {/* ── Extraction fields ── */}
        <div className="crm-card">
          <span className="crm-section-title">Extracted fields</span>
          <div className="crm-grid">
            <div className="crm-field"><div className="crm-field-label">Industry</div><div className="crm-field-value">{showField(ex?.industry)}</div></div>
            <div className="crm-field"><div className="crm-field-label">Product</div><div className="crm-field-value">{showField(ex?.product)}</div></div>
            <div className="crm-field" style={{ gridColumn: "1 / -1" }}>
              <div className="crm-field-label">Competitors</div>
              <div className="crm-field-value">
                {Array.isArray(ex?.competitors) && ex.competitors.length > 0
                  ? <ul className="crm-list">{ex.competitors.map((c, i) => <li key={i}>{c}</li>)}</ul>
                  : "—"}
              </div>
            </div>
          </div>
          {hubspotKeyEntries.length > 0 && (
            <>
              <span className="crm-section-title" style={{ marginTop: "1.25rem", display: "block" }}>CRM highlights</span>
              <div className="crm-kv-grid">
                {hubspotKeyEntries.map(([k, v, label]) => (
                  <div key={k} className="crm-kv crm-kv--highlight">
                    <div className="crm-kv-k">{label}</div>
                    <div className="crm-kv-v">{String(v)}</div>
                  </div>
                ))}
              </div>
            </>
          )}
          {customEntriesOther.length > 0 && (
            <>
              <span className="crm-section-title" style={{ marginTop: "1.25rem", display: "block" }}>Other fields ({customEntriesOther.length})</span>
              <div className="crm-kv-grid">
                {customEntriesOther.map(([k, v]) => (
                  <div key={k} className="crm-kv">
                    <div className="crm-kv-k">{k}</div>
                    <div className="crm-kv-v">{String(v)}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {transcriptBlock}
      </>
    );
  }

  return (
    <div className="crm">
      <div className="crm-bg" aria-hidden="true" />
      <div className="crm-gridlines" aria-hidden="true" />
      <div className="crm-orb crm-orb--1" aria-hidden="true" />
      <div className="crm-orb crm-orb--2" aria-hidden="true" />

      <div className="crm-layout">
        <aside className="crm-sidebar" aria-label="Application navigation">
          <div className="crm-sidebar-brand">
            <span className="crm-sidebar-brand-mark" aria-hidden="true">AI</span>
            <span>
              <span className="crm-sidebar-brand-text">AI CRM</span>
              <span className="crm-sidebar-tagline">Revenue intelligence</span>
            </span>
          </div>
          <nav className="crm-nav">
            {[
              ["dashboard",    "🏠", "Dashboard"],
              ["intelligence", "🧠", "AI Intelligence"],
              ["timeline",     "⏱",  "Timeline"],
              ["upload",       "⬆",  "Upload"],
              ["analytics",    "📊", "Analytics"],
              ["records",      "📋", "CRM Records"],
            ].map(([id, icon, label]) => (
              <button
                key={id}
                type="button"
                className={"crm-nav-item" + (activeSection === id ? " crm-nav-item--active" : "")}
                aria-current={activeSection === id ? "page" : undefined}
                onClick={() => setActiveSection(id)}
              >
                <span className="crm-nav-icon" aria-hidden="true">{icon}</span>
                {label}
              </button>
            ))}
          </nav>
          <div className="crm-sidebar-footer">Interaction mining · v2</div>
        </aside>

        <main className="crm-main">
          <div className="crm-inner">
            {activeSection === "dashboard" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Dashboard</h1>
                  <p className="crm-page-desc">Live snapshot of ingested interactions and AI-parsed revenue signals.</p>
                </div>

                {/* ── Stats row ── */}
                <div className="crm-ai-kpi-row">
                  <div className="crm-ai-kpi crm-ai-kpi--blue">
                    <div className="crm-ai-kpi-label">Total records</div>
                    <div className="crm-ai-kpi-value">
                      {revenueLoading ? <Spinner size={20} color="#bfdbfe" topColor="#3b82f6" /> : (revenueData?.total_records ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="crm-ai-kpi crm-ai-kpi--green">
                    <div className="crm-ai-kpi-label">Combined budget</div>
                    <div className="crm-ai-kpi-value">
                      {revenueLoading ? "…" : Number(revenueData?.total_budget ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="crm-ai-kpi crm-ai-kpi--orange">
                    <div className="crm-ai-kpi-label">Strong intent</div>
                    <div className="crm-ai-kpi-value">
                      {insightsLoading ? "…" : (insightsData?.intent_keywords_high ?? 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="crm-ai-kpi crm-ai-kpi--purple">
                    <div className="crm-ai-kpi-label">Avg deal score</div>
                    <div className="crm-ai-kpi-value">
                      {aiIntelLoading ? "…" : (aiIntelData?.avg_deal_score ?? 0)}
                    </div>
                  </div>
                </div>

                {/* ── Insights card ── */}
                <div className="crm-card">
                  <span className="crm-section-title">Interaction insights</span>
                  {insightsLoading && <p className="crm-revenue-loading" role="status">Loading…</p>}
                  {!insightsLoading && insightsError && <p className="crm-revenue-err" role="alert">{insightsError}</p>}
                  {!insightsLoading && !insightsError && insightsData && (
                    <>
                      <div className="crm-dash-stats">
                        <div className="crm-dash-stat">
                          <div className="crm-dash-stat-label">Avg budget</div>
                          <div className="crm-dash-stat-value">
                            {Number(insightsData.avg_budget ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </div>
                        </div>
                        <div className="crm-dash-stat">
                          <div className="crm-dash-stat-label">Strong signals</div>
                          <div className="crm-dash-stat-value">{(insightsData.intent_keywords_high ?? 0).toLocaleString()}</div>
                        </div>
                        <div className="crm-dash-stat">
                          <div className="crm-dash-stat-label">Exploratory</div>
                          <div className="crm-dash-stat-value">{(insightsData.intent_keywords_low ?? 0).toLocaleString()}</div>
                        </div>
                      </div>
                      {insightsData.by_source_type && Object.keys(insightsData.by_source_type).length > 0 && (
                        <div className="crm-insights-sources">
                          <span className="crm-record-tags-lbl">By channel</span>
                          <div className="crm-record-tag-row" style={{ marginTop: 6 }}>
                            {Object.entries(insightsData.by_source_type).map(([src, n]) => (
                              <span key={src} className="crm-record-tag" title={`${n} record(s)`}>{src}: {n}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                  <div className="crm-dash-actions">
                    {[
                      ["upload",       "⬆ New upload"],
                      ["timeline",     "⏱ Timeline"],
                      ["analytics",    "📊 Analytics"],
                      ["records",      "📋 Records"],
                      ["intelligence", "🧠 AI Intelligence"],
                    ].map(([id, label]) => (
                      <button key={id} type="button"
                        className={"crm-dash-action" + (id === "intelligence" ? " crm-dash-action--ai" : "")}
                        onClick={() => setActiveSection(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeSection === "intelligence" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">🧠 AI Intelligence</h1>
                  <p className="crm-page-desc">Classification, deal scoring, risk detection, and next-action suggestions — automatically derived from every ingested interaction.</p>
                </div>

                {aiIntelLoading && (
                  <div className="crm-card crm-ai-loading-card">
                    <div className="crm-ai-loading">
                      <span className="crm-ai-loading-spinner" />
                      Analyzing interactions with AI…
                    </div>
                  </div>
                )}

                {!aiIntelLoading && aiIntelError && <p className="crm-revenue-err" role="alert">{aiIntelError}</p>}

                {!aiIntelLoading && !aiIntelError && aiIntelData && (
                  <>
                    {/* KPI row */}
                    <div className="crm-ai-kpi-row">
                      <div className="crm-ai-kpi crm-ai-kpi--blue">
                        <div className="crm-ai-kpi-label">Total records</div>
                        <div className="crm-ai-kpi-value">{(aiIntelData.total_records ?? 0).toLocaleString()}</div>
                      </div>
                      <div className="crm-ai-kpi crm-ai-kpi--green">
                        <div className="crm-ai-kpi-label">Avg deal score</div>
                        <div className="crm-ai-kpi-value">{aiIntelData.avg_deal_score ?? 0}</div>
                      </div>
                      <div className="crm-ai-kpi crm-ai-kpi--orange">
                        <div className="crm-ai-kpi-label">High risk</div>
                        <div className="crm-ai-kpi-value">{aiIntelData.risk_distribution?.high ?? 0}</div>
                      </div>
                      <div className="crm-ai-kpi crm-ai-kpi--purple">
                        <div className="crm-ai-kpi-label">Sales interactions</div>
                        <div className="crm-ai-kpi-value">{aiIntelData.intent_distribution?.sales ?? 0}</div>
                      </div>
                    </div>

                    {/* Charts — pie charts side by side */}
                    <div className="crm-ai-charts-row">
                      <div className="crm-card crm-ai-chart-card">
                        <span className="crm-section-title">Interaction type</span>
                        {aiIntelData.intent_distribution && Object.keys(aiIntelData.intent_distribution).length > 0 ? (
                          <div className="crm-ai-pie-wrap">
                            <ResponsiveContainer width="100%" height={260}>
                              <PieChart>
                                <Pie
                                  data={Object.entries(aiIntelData.intent_distribution).map(([name, value]) => ({ name, value }))}
                                  cx="50%" cy="50%"
                                  innerRadius={55} outerRadius={95}
                                  paddingAngle={3} dataKey="value"
                                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                  labelLine={false}
                                >
                                  {Object.keys(aiIntelData.intent_distribution).map((_, i) => (
                                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                  ))}
                                </Pie>
                                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, fontSize: 13 }} />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                        ) : <EmptyState text="No interaction data yet." />}
                      </div>

                      <div className="crm-card crm-ai-chart-card">
                        <span className="crm-section-title">Risk distribution</span>
                        {aiIntelData.risk_distribution && Object.keys(aiIntelData.risk_distribution).length > 0 ? (
                          <div className="crm-ai-pie-wrap">
                            <ResponsiveContainer width="100%" height={260}>
                              <PieChart>
                                <Pie
                                  data={Object.entries(aiIntelData.risk_distribution).map(([name, value]) => ({ name, value }))}
                                  cx="50%" cy="50%"
                                  innerRadius={55} outerRadius={95}
                                  paddingAngle={3} dataKey="value"
                                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                  labelLine={false}
                                >
                                  {Object.entries(aiIntelData.risk_distribution).map(([key], i) => (
                                    <Cell key={i} fill={key === "high" ? "#ef4444" : key === "medium" ? "#f59e0b" : "#22c55e"} />
                                  ))}
                                </Pie>
                                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, fontSize: 13 }} />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                        ) : <EmptyState text="No risk data yet." />}
                      </div>
                    </div>

                    {/* Intelligence table */}
                    {Array.isArray(aiIntelData.records) && aiIntelData.records.length > 0 ? (
                      <div className="crm-card">
                        <span className="crm-section-title">Intelligence overview</span>
                        <div className="crm-table-wrap crm-ai-table-wrap">
                          <table className="crm-table crm-ai-table">
                            <thead>
                              <tr>
                                <th>ID</th>
                                <th>Intent type</th>
                                <th style={{ minWidth: 140 }}>Deal score</th>
                                <th>Risk</th>
                                <th>Next action</th>
                                <th>Tags</th>
                              </tr>
                            </thead>
                            <tbody>
                              {aiIntelData.records.map((rec) => (
                                <tr key={rec.id} className="crm-ai-table-row">
                                  <td className="crm-td-mono">#{rec.id}</td>
                                  <td><IntentBadge type={rec.interaction_type} /></td>
                                  <td><DealScoreBar score={rec.deal_score} /></td>
                                  <td><RiskIndicator level={rec.risk_level} /></td>
                                  <td className="crm-ai-action-cell">{rec.next_action || "—"}</td>
                                  <td>
                                    <div className="crm-ai-tag-row">
                                      {Array.isArray(rec.tags) && rec.tags.length > 0
                                        ? rec.tags.slice(0, 4).map((t, i) => <span key={i} className="crm-ai-tag">{t}</span>)
                                        : <span style={{ color: "var(--muted-2)", fontSize: "0.8rem" }}>—</span>}
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : (
                      <div className="crm-card"><EmptyState text="No records processed yet. Upload a transcript to generate AI intelligence." /></div>
                    )}
                  </>
                )}
              </>
            )}

            {activeSection === "timeline" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Interaction timeline</h1>
                  <p className="crm-page-desc">
                    Unified history of captured interactions (newest first). Matches
                    FRD 2.4 automated capture and DRD interaction metadata.
                  </p>
                </div>

                <div className="crm-card crm-records-card">
                  {timelineLoading && (
                    <div className="crm-ai-loading-card">
                      <div className="crm-ai-loading">
                        <span className="crm-ai-loading-spinner" />
                        Loading timeline…
                      </div>
                    </div>
                  )}
                  {!timelineLoading && timelineError && (
                    <p className="crm-records-err" role="alert">
                      {timelineError}
                    </p>
                  )}
                  {!timelineLoading &&
                    !timelineError &&
                    Array.isArray(timelineItems) &&
                    timelineItems.length === 0 && (
                      <p className="crm-records-empty">
                        No interactions yet. Use <strong>Upload</strong> to ingest
                        a call, email, or other channel.
                      </p>
                    )}
                  {!timelineLoading &&
                    !timelineError &&
                    timelineItems &&
                    timelineItems.length > 0 && (
                      <ul className="crm-record-list">
                        {timelineItems.map((t) => {
                          const when = formatRecordWhen(t.created_at);
                          const plist = Array.isArray(t.participants)
                            ? t.participants.filter(Boolean)
                            : [];
                          return (
                            <li key={t.id}>
                              <div className="crm-record-card crm-timeline-card">
                                <div className="crm-record-summary">
                                  <span className="crm-record-summary-top">
                                    <span className="crm-record-id">#{t.id}</span>
                                    <span className="crm-meta-pill">
                                      {t.source_type || "—"}
                                    </span>
                                    {when ? (
                                      <span className="crm-record-when">
                                        {when}
                                      </span>
                                    ) : null}
                                  </span>
                                  <span className="crm-record-metrics">
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Budget
                                      </span>
                                      <span className="crm-record-metric-val">
                                        {typeof t.budget_parsed === "number"
                                          ? t.budget_parsed.toLocaleString()
                                          : "—"}
                                      </span>
                                    </span>
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Intent
                                      </span>
                                      <span className="crm-record-metric-val crm-record-metric-val--clip">
                                        {t.intent?.trim() ? t.intent : "—"}
                                      </span>
                                    </span>
                                  </span>
                                  <span className="crm-record-excerpt">
                                    {t.content_excerpt || "—"}
                                  </span>
                                </div>
                                <div className="crm-timeline-meta">
                                  {t.external_interaction_id ? (
                                    <span className="crm-meta-pill">
                                      ext: {t.external_interaction_id}
                                    </span>
                                  ) : null}
                                  {plist.length > 0 ? (
                                    <span className="crm-meta-pill">
                                      {plist.slice(0, 4).join(" · ")}
                                      {plist.length > 4
                                        ? ` +${plist.length - 4}`
                                        : ""}
                                    </span>
                                  ) : null}
                                  <span className="crm-meta-pill">
                                    A{t.account_id ?? "—"} · C
                                    {t.contact_id ?? "—"} · D
                                    {t.deal_id ?? "—"}
                                  </span>
                                </div>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                </div>
              </>
            )}

            {activeSection === "upload" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Upload</h1>
                  <p className="crm-page-desc">
                    Transcribe calls (Whisper), extract CRM fields (Groq), and
                    map entities — audio/video or paste text with channel type.
                  </p>
                </div>

                <div className="crm-card">
                  <div
                    className="crm-mode-tabs"
                    role="tablist"
                    aria-label="Ingest input type"
                  >
                    <button
                      type="button"
                      role="tab"
                      id="tab-audio"
                      className={
                        "crm-mode-tab" +
                        (inputMode === "audio" ? " crm-mode-tab--active" : "")
                      }
                      aria-selected={inputMode === "audio"}
                      disabled={loading}
                      onClick={() => handleInputModeChange("audio")}
                    >
                      Audio Input
                    </button>
                    <button
                      type="button"
                      role="tab"
                      id="tab-text"
                      className={
                        "crm-mode-tab" +
                        (inputMode === "text" ? " crm-mode-tab--active" : "")
                      }
                      aria-selected={inputMode === "text"}
                      disabled={loading}
                      onClick={() => handleInputModeChange("text")}
                    >
                      Text Input
                    </button>
                  </div>

                  {inputMode === "audio" && (
                    <div
                      className="crm-mode-panel"
                      role="tabpanel"
                      aria-labelledby="tab-audio"
                    >
                      <div className="crm-upload-row">
                        <div className="crm-file-wrap">
                          <input
                            id="audio-file"
                            className="crm-file-input"
                            type="file"
                            accept="audio/*,video/*"
                            onChange={handleFileChange}
                            disabled={loading}
                          />
                          <label
                            htmlFor="audio-file"
                            className="crm-file-label"
                          >
                            Drop or choose audio / video
                          </label>
                        </div>
                        <button
                          type="button"
                          className="crm-btn"
                          onClick={handleProcess}
                          disabled={loading || !file}
                        >
                          {loading && <Spinner />}
                          {loading ? "Processing…" : "Process Audio"}
                        </button>
                      </div>
                      {file && (
                        <p className="crm-file-name" aria-live="polite">
                          {file.name}
                        </p>
                      )}
                    </div>
                  )}

                  {inputMode === "text" && (
                    <div
                      className="crm-mode-panel"
                      role="tabpanel"
                      aria-labelledby="tab-text"
                    >
                      <p className="crm-section-title" style={{ marginTop: 0 }}>
                        Source type
                      </p>
                      <div
                        className="crm-source-chips"
                        role="group"
                        aria-label="Text source"
                      >
                        {[
                          ["call", "Call"],
                          ["email", "Email"],
                          ["meeting", "Meeting"],
                          ["sms", "SMS"],
                          ["crm_update", "CRM"],
                        ].map(([id, label]) => (
                          <button
                            key={id}
                            type="button"
                            className={
                              "crm-chip" +
                              (textSource === id ? " crm-chip--on" : "")
                            }
                            disabled={loading}
                            onClick={() => {
                              setTextSource(id);
                              setError(null);
                            }}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <textarea
                        id="transcript-input"
                        className="crm-textarea"
                        placeholder={
                          textPlaceholders[textSource] || textPlaceholders.call
                        }
                        value={transcriptText}
                        onChange={(e) => {
                          setTranscriptText(e.target.value);
                          setError(null);
                        }}
                        disabled={loading}
                        aria-label="Transcript or message text"
                      />
                      <div className="crm-text-actions">
                        <button
                          type="button"
                          className="crm-btn"
                          onClick={handleProcess}
                          disabled={loading || !transcriptText.trim()}
                        >
                          {loading && <Spinner />}
                          {loading ? "Processing…" : "Process Text"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {renderUploadError()}
                {renderUploadResults()}
              </>
            )}

            {activeSection === "analytics" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Analytics</h1>
                  <p className="crm-page-desc">
                    Budget and intent signals aggregated from CRM records.
                  </p>
                </div>

                <div className="crm-card crm-analytics-card">
                  <div className="crm-analytics-head">
                    <h2 className="crm-analytics-title">Revenue Analytics</h2>
                  </div>

                  {revenueLoading && (
                    <div className="crm-ai-loading-card">
                      <div className="crm-ai-loading">
                        <span className="crm-ai-loading-spinner" />
                        Loading analytics…
                      </div>
                    </div>
                  )}

                  {!revenueLoading && revenueError && (
                    <p className="crm-revenue-err" role="alert">
                      {revenueError}
                    </p>
                  )}

                  {!revenueLoading && !revenueError && revenueData && (
                    <>
                      {revenueData.total_records === 0 ||
                        !revenueData.records?.length ? (
                        <p className="crm-revenue-empty">
                          No CRM records yet. Open <strong>Upload</strong> to
                          ingest transcripts or audio and populate revenue data.
                        </p>
                      ) : (
                        <>
                          <div className="crm-analytics-filters">
                            <div className="crm-filter-group">
                              <span className="crm-filter-label">
                                Budget range
                              </span>
                              <div className="crm-filter-inputs">
                                <input
                                  type="number"
                                  className="crm-filter-input"
                                  placeholder="Min"
                                  min={0}
                                  value={analyticsBudgetMin}
                                  onChange={(e) =>
                                    setAnalyticsBudgetMin(e.target.value)
                                  }
                                  aria-label="Minimum budget"
                                />
                                <span
                                  className="crm-filter-sep"
                                  aria-hidden="true"
                                >
                                  –
                                </span>
                                <input
                                  type="number"
                                  className="crm-filter-input"
                                  placeholder="Max"
                                  min={0}
                                  value={analyticsBudgetMax}
                                  onChange={(e) =>
                                    setAnalyticsBudgetMax(e.target.value)
                                  }
                                  aria-label="Maximum budget"
                                />
                              </div>
                            </div>
                            <div className="crm-filter-group">
                              <label
                                className="crm-filter-label"
                                htmlFor="analytics-intent"
                              >
                                Intent
                              </label>
                              <select
                                id="analytics-intent"
                                className="crm-filter-select"
                                value={analyticsIntent}
                                onChange={(e) =>
                                  setAnalyticsIntent(e.target.value)
                                }
                              >
                                <option value="all">All</option>
                                <option value="high">High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                              </select>
                            </div>
                            <button
                              type="button"
                              className="crm-filter-reset"
                              onClick={resetAnalyticsFilters}
                            >
                              Reset filters
                            </button>
                          </div>

                          <div className="crm-stat-row">
                            <div className="crm-stat">
                              <div className="crm-stat-label">
                                Records (filtered)
                              </div>
                              <div className="crm-stat-value">
                                {filteredRevenueRecords.length}
                              </div>
                            </div>
                            <div className="crm-stat">
                              <div className="crm-stat-label">
                                Total budget (filtered)
                              </div>
                              <div className="crm-stat-value">
                                {filteredRevenueTotalBudget.toLocaleString()}
                              </div>
                            </div>
                          </div>

                          {filteredRevenueRecords.length === 0 ? (
                            <p className="crm-revenue-no-data" role="status">
                              No data available
                            </p>
                          ) : (
                            <div className="crm-chart-wrap">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                  data={filteredRevenueRecords}
                                  margin={{
                                    top: 12,
                                    right: 12,
                                    left: 4,
                                    bottom: 8,
                                  }}
                                >
                                  <defs>
                                    <linearGradient
                                      id="revenueBarFill"
                                      x1="0"
                                      y1="0"
                                      x2="0"
                                      y2="1"
                                    >
                                      <stop
                                        offset="0%"
                                        stopColor="#22d3ee"
                                        stopOpacity={1}
                                      />
                                      <stop
                                        offset="100%"
                                        stopColor="#6366f1"
                                        stopOpacity={0.95}
                                      />
                                    </linearGradient>
                                  </defs>
                                  <CartesianGrid
                                    stroke="rgba(255,255,255,0.08)"
                                    strokeDasharray="4 4"
                                    vertical={false}
                                  />
                                  <XAxis
                                    dataKey="id"
                                    stroke="#64748b"
                                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                                    tickLine={{
                                      stroke: "rgba(255,255,255,0.15)",
                                    }}
                                    label={{
                                      value: "Record ID",
                                      position: "insideBottom",
                                      offset: -2,
                                      fill: "#94a3b8",
                                      fontSize: 11,
                                    }}
                                  />
                                  <YAxis
                                    stroke="#64748b"
                                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                                    tickLine={{
                                      stroke: "rgba(255,255,255,0.15)",
                                    }}
                                    tickFormatter={(v) =>
                                      v >= 1000 ? `${v / 1000}k` : String(v)
                                    }
                                    label={{
                                      value: "Budget",
                                      angle: -90,
                                      position: "insideLeft",
                                      fill: "#94a3b8",
                                      fontSize: 11,
                                    }}
                                  />
                                  <Tooltip
                                    cursor={{
                                      fill: "rgba(34, 211, 238, 0.1)",
                                    }}
                                    contentStyle={{
                                      background: "rgba(15, 23, 42, 0.97)",
                                      border:
                                        "1px solid rgba(148, 163, 184, 0.2)",
                                      borderRadius: "12px",
                                      color: "#f8fafc",
                                      fontSize: "13px",
                                    }}
                                    labelStyle={{ color: "#94a3b8" }}
                                    formatter={(value) => [
                                      typeof value === "number"
                                        ? value.toLocaleString()
                                        : value,
                                      "Budget",
                                    ]}
                                    labelFormatter={(label) =>
                                      `Record #${label}`
                                    }
                                  />
                                  <Bar
                                    dataKey="budget"
                                    fill="url(#revenueBarFill)"
                                    radius={[8, 8, 0, 0]}
                                    maxBarSize={48}
                                  />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </>
            )}

            {activeSection === "records" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">CRM Records</h1>
                  <p className="crm-page-desc">
                    Interaction mining output: budget, intent, mapping, and
                    transcript excerpts—search and open a card for full detail.
                  </p>
                </div>

                <div className="crm-card crm-records-card">
                  <div className="crm-records-toolbar">
                    <div className="crm-records-toolbar-main">
                      <label className="crm-records-search-wrap">
                        <span className="crm-sr-only">Search records</span>
                        <input
                          type="search"
                          className="crm-records-search"
                          placeholder="Search id, transcript, intent, industry…"
                          value={recordsQuery}
                          onChange={(e) => setRecordsQuery(e.target.value)}
                          aria-label="Filter CRM records"
                        />
                      </label>
                      <div
                        className="crm-source-chips"
                        role="group"
                        aria-label="Filter by source"
                      >
                        {[
                          ["all", "All"],
                          ["call", "Call"],
                          ["email", "Email"],
                          ["meeting", "Meeting"],
                          ["sms", "SMS"],
                          ["crm_update", "CRM"],
                        ].map(([id, label]) => (
                          <button
                            key={id}
                            type="button"
                            className={
                              "crm-chip" +
                              (recordsSourceFilter === id
                                ? " crm-chip--on"
                                : "")
                            }
                            onClick={() => setRecordsSourceFilter(id)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="crm-records-danger"
                      onClick={handleDeleteAllRecords}
                      disabled={
                        recordsDeleting ||
                        crmRecordsLoading ||
                        !crmRecords?.length
                      }
                    >
                      {recordsDeleting ? "Clearing…" : "Delete all records"}
                    </button>
                  </div>

                  {crmRecordsLoading && (
                    <div className="crm-ai-loading-card">
                      <div className="crm-ai-loading">
                        <span className="crm-ai-loading-spinner" />
                        Loading records…
                      </div>
                    </div>
                  )}

                  {!crmRecordsLoading && crmRecordsError && (
                    <p className="crm-records-err" role="alert">{crmRecordsError}</p>
                  )}

                  {!crmRecordsLoading && !crmRecordsError && crmRecords && crmRecords.length === 0 && (
                    <EmptyState text="No CRM records yet. Use Upload to ingest a transcript or audio." />
                  )}

                  {!crmRecordsLoading &&
                    !crmRecordsError &&
                    crmRecords &&
                    crmRecords.length > 0 &&
                    filteredCrmRecords.length === 0 && (
                      <p className="crm-records-empty" role="status">
                        No records match your filters.{" "}
                        <button
                          type="button"
                          className="crm-records-reset-filters"
                          onClick={() => {
                            setRecordsQuery("");
                            setRecordsSourceFilter("all");
                          }}
                        >
                          Reset filters
                        </button>
                      </p>
                    )}

                  {!crmRecordsLoading &&
                    !crmRecordsError &&
                    filteredCrmRecords.length > 0 && (
                      <ul className="crm-record-list">
                        {filteredCrmRecords.map((row) => {
                          const when = formatRecordWhen(row.created_at);
                          const hubspotKeyEntries = getCrmHubspotKeyEntries(
                            row.custom_fields,
                          );
                          const customEntriesOther = getOtherCustomEntries(
                            row.custom_fields,
                          );
                          const hsSynced = Boolean(
                            hubspotSyncMap[String(row.id)],
                          );
                          return (
                            <li key={row.id}>
                              <details className="crm-record-card crm-record-card--enhanced">
                                <summary className="crm-record-summary">
                                  <span className="crm-record-summary-top">
                                    <span className="crm-record-id">
                                      #{row.id}
                                    </span>
                                    <span className="crm-meta-pill">
                                      {row.source_type || "—"}
                                    </span>
                                    {row.interaction_type && (
                                      <IntentBadge type={row.interaction_type} />
                                    )}
                                    {row.risk_level && (
                                      <RiskIndicator level={row.risk_level} />
                                    )}
                                    {when ? (
                                      <span className="crm-record-when">
                                        {when}
                                      </span>
                                    ) : null}
                                  </span>
                                  {/* AI Summary at top */}
                                  {row.summary?.trim() && (
                                    <div className="crm-record-ai-summary">
                                      {row.summary}
                                    </div>
                                  )}
                                  <span className="crm-record-metrics">
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Budget
                                      </span>
                                      <span className="crm-record-metric-val">
                                        {typeof row.budget === "number"
                                          ? row.budget.toLocaleString()
                                          : "—"}
                                      </span>
                                    </span>
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Intent
                                      </span>
                                      <span className="crm-record-metric-val crm-record-metric-val--clip">
                                        {row.intent?.trim()
                                          ? row.intent
                                          : "—"}
                                      </span>
                                    </span>
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Deal Score
                                      </span>
                                      <span className="crm-record-metric-val">
                                        <DealScoreBar score={row.deal_score ?? 0} />
                                      </span>
                                    </span>
                                    <span className="crm-record-metric">
                                      <span className="crm-record-metric-lbl">
                                        Industry
                                      </span>
                                      <span className="crm-record-metric-val crm-record-metric-val--clip">
                                        {row.industry?.trim()
                                          ? row.industry
                                          : "—"}
                                      </span>
                                    </span>
                                  </span>
                                  {/* Tags chips */}
                                  {Array.isArray(row.tags) && row.tags.length > 0 && (
                                    <div className="crm-record-ai-tags">
                                      {row.tags.map((t, i) => (
                                        <span key={i} className="crm-ai-tag">{t}</span>
                                      ))}
                                    </div>
                                  )}
                                  {/* Next Action highlighted box */}
                                  {row.next_action?.trim() && (
                                    <div className="crm-record-next-action">
                                      <span className="crm-record-next-action-label">Next Action</span>
                                      {row.next_action}
                                    </div>
                                  )}
                                </summary>
                                <div className="crm-record-body">
                                  {/* Risk reason */}
                                  {row.risk_reason?.trim() && (
                                    <div className="crm-record-risk-detail">
                                      <span className="crm-record-tags-lbl">Risk Analysis</span>
                                      <p className="crm-record-risk-reason">{row.risk_reason}</p>
                                    </div>
                                  )}
                                  {/* Pain points */}
                                  {row.pain_points && (
                                    <div className="crm-record-tags">
                                      <span className="crm-record-tags-lbl">Pain Points</span>
                                      <p className="crm-record-pain-text">{row.pain_points}</p>
                                    </div>
                                  )}
                                  {/* Stakeholders */}
                                  {Array.isArray(row.stakeholders) && row.stakeholders.length > 0 && (
                                    <div className="crm-record-tags">
                                      <span className="crm-record-tags-lbl">Stakeholders</span>
                                      <div className="crm-record-tag-row">
                                        {row.stakeholders.map((s, i) => (
                                          <span key={i} className="crm-record-tag crm-record-tag--stake">{s}</span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  {/* Advanced CRM fields */}
                                  {(row.mentioned_company || row.procurement_stage || row.use_case || row.decision_criteria || row.budget_owner || row.implementation_scope) && (
                                    <div className="crm-record-advanced-fields">
                                      <span className="crm-record-tags-lbl">Advanced CRM</span>
                                      <div className="crm-advanced-grid">
                                        {row.mentioned_company && <div className="crm-adv-item"><span className="crm-adv-label">Company</span><span className="crm-adv-value">{row.mentioned_company}</span></div>}
                                        {row.procurement_stage && <div className="crm-adv-item"><span className="crm-adv-label">Stage</span><span className="crm-adv-value">{row.procurement_stage}</span></div>}
                                        {row.use_case && <div className="crm-adv-item"><span className="crm-adv-label">Use Case</span><span className="crm-adv-value">{row.use_case}</span></div>}
                                        {row.decision_criteria && <div className="crm-adv-item"><span className="crm-adv-label">Decision Criteria</span><span className="crm-adv-value">{row.decision_criteria}</span></div>}
                                        {row.budget_owner && <div className="crm-adv-item"><span className="crm-adv-label">Budget Owner</span><span className="crm-adv-value">{row.budget_owner}</span></div>}
                                        {row.implementation_scope && <div className="crm-adv-item"><span className="crm-adv-label">Scope</span><span className="crm-adv-value">{row.implementation_scope}</span></div>}
                                      </div>
                                    </div>
                                  )}
                                  {(row.external_interaction_id ||
                                    (Array.isArray(row.participants) &&
                                      row.participants.length > 0)) && (
                                      <p className="crm-record-detail-meta">
                                        {row.external_interaction_id ? (
                                          <span className="crm-meta-pill">
                                            ext: {row.external_interaction_id}
                                          </span>
                                        ) : null}
                                        {Array.isArray(row.participants) &&
                                          row.participants.length > 0 ? (
                                          <span className="crm-meta-pill">
                                            {row.participants
                                              .slice(0, 6)
                                              .filter(Boolean)
                                              .join(" · ")}
                                            {row.participants.length > 6
                                              ? ` +${row.participants.length - 6}`
                                              : ""}
                                          </span>
                                        ) : null}
                                      </p>
                                    )}
                                  <div className="crm-record-links">
                                    <span className="crm-record-links-lbl">
                                      CRM links
                                    </span>
                                    <div className="crm-record-link-chips">
                                      <span className="crm-id-chip">
                                        <span className="crm-id-chip-lbl">
                                          Account
                                        </span>
                                        {row.account_id ?? "—"}
                                      </span>
                                      <span className="crm-id-chip">
                                        <span className="crm-id-chip-lbl">
                                          Contact
                                        </span>
                                        {row.contact_id ?? "—"}
                                      </span>
                                      <span className="crm-id-chip">
                                        <span className="crm-id-chip-lbl">
                                          Deal
                                        </span>
                                        {row.deal_id ?? "—"}
                                      </span>
                                    </div>
                                  </div>
                                  <div className="crm-hubspot-row">
                                    <button
                                      type="button"
                                      className={
                                        "crm-hubspot-btn" +
                                        (hsSynced ? " crm-hubspot-btn--synced" : "")
                                      }
                                      onClick={() => pushToHubspot(row.id)}
                                      disabled={Boolean(syncingByRecord[row.id])}
                                      aria-busy={Boolean(syncingByRecord[row.id])}
                                    >
                                      {syncingByRecord[row.id] ? (
                                        <span className="crm-hubspot-btn-inner">
                                          <Spinner size={12} />
                                          Syncing…
                                        </span>
                                      ) : hsSynced ? "Re-sync to HubSpot" : "Sync to HubSpot"}
                                    </button>
                                    {hubspotNoticeByRecord[row.id]?.message ? (
                                      <span
                                        className={
                                          "crm-hubspot-msg " +
                                          (hubspotNoticeByRecord[row.id]?.type === "success"
                                            ? "crm-hubspot-msg--success"
                                            : "crm-hubspot-msg--error")
                                        }
                                      >
                                        {hubspotNoticeByRecord[row.id].message}
                                        {hubspotNoticeByRecord[row.id]?.linkUrl ? (
                                          <>
                                            {" "}
                                            <a
                                              href={hubspotNoticeByRecord[row.id].linkUrl}
                                              target="_blank"
                                              rel="noopener noreferrer"
                                              className="crm-hubspot-open-link"
                                            >
                                              Open in HubSpot
                                            </a>
                                          </>
                                        ) : null}
                                      </span>
                                    ) : hsSynced ? (
                                      <span className="crm-hubspot-msg crm-hubspot-msg--success">
                                        Synced to HubSpot ✅
                                      </span>
                                    ) : null}
                                  </div>
                                  <p className="crm-record-detail-meta">
                                    <span
                                      className="crm-meta-pill"
                                      title={CRM_ENTITY_LINK_HELP}
                                    >
                                      <span className="crm-meta-pill-part">
                                        {describeCrmMappingMethod(row.mapping_method)}
                                      </span>
                                      <span className="crm-meta-pill-sep"> · </span>
                                      <span className="crm-meta-pill-part">
                                        {row.product?.trim()
                                          ? `Product: ${row.product}`
                                          : "Product: —"}
                                      </span>
                                      <span className="crm-meta-pill-sep"> · </span>
                                      <span className="crm-meta-pill-part">
                                        {row.timeline?.trim()
                                          ? `Timeline: ${row.timeline}`
                                          : "Timeline: —"}
                                      </span>
                                    </span>
                                  </p>
                                  {Array.isArray(row.competitors) &&
                                    row.competitors.length > 0 ? (
                                    <div className="crm-record-tags">
                                      <span className="crm-record-tags-lbl">
                                        Competitors
                                      </span>
                                      <div className="crm-record-tag-row">
                                        {row.competitors.map((c, i) => (
                                          <span
                                            key={i}
                                            className="crm-record-tag"
                                          >
                                            {c}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  ) : null}
                                  {hubspotKeyEntries.length > 0 ? (
                                    <div className="crm-record-custom">
                                      <span className="crm-record-tags-lbl">
                                        CRM highlights
                                      </span>
                                      <div className="crm-kv-grid">
                                        {hubspotKeyEntries.map(([k, v, label]) => (
                                          <div
                                            key={k}
                                            className="crm-kv crm-kv--highlight"
                                          >
                                            <div className="crm-kv-k">{label}</div>
                                            <div className="crm-kv-v">
                                              {String(v)}
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ) : null}
                                  {customEntriesOther.length > 0 ? (
                                    <div className="crm-record-custom">
                                      <span className="crm-record-tags-lbl">
                                        Other custom fields
                                      </span>
                                      <div className="crm-kv-grid">
                                        {customEntriesOther.map(([k, v]) => (
                                          <div key={k} className="crm-kv">
                                            <div className="crm-kv-k">{k}</div>
                                            <div className="crm-kv-v">
                                              {String(v)}
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ) : null}
                                  <div className="crm-record-transcript-block">
                                    <p className="crm-section-title">
                                      Source text
                                    </p>
                                    <div className="crm-transcript crm-transcript--records">
                                      {row.content || "—"}
                                    </div>
                                  </div>
                                </div>
                              </details>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                </div>
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
