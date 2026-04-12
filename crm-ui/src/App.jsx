import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./crm-app.css";

const API_URL = "http://127.0.0.1:8000/ingest/audio";
const TRANSCRIPT_API_URL = "http://127.0.0.1:8000/ingest/transcript";
const REVENUE_API_URL = "http://127.0.0.1:8000/api/v1/analytics/revenue";
const CRM_RECORDS_API_URL = "http://127.0.0.1:8000/api/v1/crm/records";

const NAV_ITEMS = [
  ["dashboard", "Dashboard", "Overview"],
  ["upload", "Capture", "Ingest"],
  ["analytics", "Analytics", "Signals"],
  ["records", "Records", "Review"],
];

const PAGE_META = {
  dashboard: {
    eyebrow: "Revenue workspace",
    title: "Sales ops command center",
    desc: "A cleaner, HubSpot-inspired layout for monitoring ingestion, budget signals, and record quality.",
  },
  upload: {
    eyebrow: "Capture pipeline data",
    title: "Turn conversations into CRM records",
    desc: "Upload recordings or paste raw notes, then let transcription, extraction, and mapping run end to end.",
  },
  analytics: {
    eyebrow: "Performance signals",
    title: "Revenue analytics",
    desc: "Filter parsed opportunities by budget and intent so follow-up stays focused on the best-fit deals.",
  },
  records: {
    eyebrow: "Source of truth",
    title: "Mapped CRM records",
    desc: "Review each ingested row with its source, commercial signals, and linked account, contact, and deal IDs.",
  },
};

const TEXT_PLACEHOLDERS = {
  call: "Paste a sales call transcript...",
  email: "Paste an email thread or message body...",
  meeting: "Paste discovery or meeting notes...",
  sms: "Paste an SMS or chat thread...",
  crm_update: "Paste a CRM activity note or field update...",
};

const showField = (value) =>
  value != null && String(value).trim() !== "" ? String(value).trim() : "--";

function formatTimestamp(sec) {
  if (sec == null || Number.isNaN(Number(sec))) return "--";
  const s = Math.floor(Number(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

function formatCompact(value) {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value) || 0);
}

function intentMatchesFilter(intentRaw, filter) {
  if (filter === "all") return true;
  return (intentRaw || "").toLowerCase().includes(filter);
}

function friendlyFetchError(message) {
  if (message === "Failed to fetch" || message === "Load failed") {
    return "Cannot reach the API. Start the FastAPI server on port 8000 and try again.";
  }
  return message;
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
  const [activeSection, setActiveSection] = useState("dashboard");

  const filteredRevenueRecords = useMemo(() => {
    const min = analyticsBudgetMin.trim() ? Number(analyticsBudgetMin) : null;
    const max = analyticsBudgetMax.trim() ? Number(analyticsBudgetMax) : null;
    return (revenueData?.records ?? []).filter((record) => {
      const budget = Number(record.budget) || 0;
      if (min !== null && !Number.isNaN(min) && budget < min) return false;
      if (max !== null && !Number.isNaN(max) && budget > max) return false;
      return intentMatchesFilter(record.intent, analyticsIntent);
    });
  }, [analyticsBudgetMax, analyticsBudgetMin, analyticsIntent, revenueData]);

  const filteredRevenueTotalBudget = useMemo(
    () => filteredRevenueRecords.reduce((sum, row) => sum + (Number(row.budget) || 0), 0),
    [filteredRevenueRecords],
  );

  const customEntries =
    result?.extracted?.custom_fields && typeof result.extracted.custom_fields === "object"
      ? Object.entries(result.extracted.custom_fields).filter(
          ([, value]) => value != null && String(value).trim() !== "",
        )
      : [];

  const totalRecords = revenueData?.total_records ?? 0;
  const totalBudget = Number(revenueData?.total_budget ?? 0);
  const crmCount = crmRecords?.length ?? 0;
  const highIntentCount = (revenueData?.records ?? []).filter((row) =>
    intentMatchesFilter(row.intent, "high"),
  ).length;
  const averageBudget = totalRecords ? totalBudget / totalRecords : 0;
  const latestRecord = crmRecords?.[crmCount - 1] ?? null;

  async function fetchJson(url, fallback, setData, setErr, fallbackMessage) {
    const res = await fetch(url, { mode: "cors", cache: "no-store" });
    const text = await res.text();
    let data = fallback;
    try {
      data = text ? JSON.parse(text) : fallback;
    } catch {
      throw new Error(text || fallbackMessage || `Request failed (${res.status})`);
    }
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
    }
    setData(data);
    setErr(null);
  }

  const refreshDashboard = async () => {
    try {
      await Promise.all([
        fetchJson(
          REVENUE_API_URL,
          {},
          (data) =>
            setRevenueData({
              total_records: data.total_records ?? 0,
              total_budget: data.total_budget ?? 0,
              records: Array.isArray(data.records) ? data.records : [],
            }),
          setRevenueError,
        ),
        fetchJson(
          CRM_RECORDS_API_URL,
          [],
          (data) => setCrmRecords(Array.isArray(data) ? data : []),
          setCrmRecordsError,
        ),
      ]);
    } catch {
      /* non-fatal */
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setRevenueLoading(true);
      try {
        await fetchJson(
          REVENUE_API_URL,
          {},
          (data) =>
            !cancelled &&
            setRevenueData({
              total_records: data.total_records ?? 0,
              total_budget: data.total_budget ?? 0,
              records: Array.isArray(data.records) ? data.records : [],
            }),
          (message) => !cancelled && setRevenueError(message),
          "Failed to load revenue data.",
        );
      } catch (err) {
        if (!cancelled) {
          setRevenueError(
            friendlyFetchError(
              err instanceof Error ? err.message : "Failed to load revenue data.",
            ),
          );
        }
      } finally {
        if (!cancelled) setRevenueLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setCrmRecordsLoading(true);
      try {
        await fetchJson(
          CRM_RECORDS_API_URL,
          [],
          (data) => !cancelled && setCrmRecords(Array.isArray(data) ? data : []),
          (message) => !cancelled && setCrmRecordsError(message),
          "Failed to load CRM records.",
        );
      } catch (err) {
        if (!cancelled) {
          setCrmRecordsError(
            friendlyFetchError(
              err instanceof Error ? err.message : "Failed to load CRM records.",
            ),
          );
        }
      } finally {
        if (!cancelled) setCrmRecordsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleProcess = async () => {
    if (inputMode === "audio" && !file) return setError("Please choose an audio file first.");
    if (inputMode === "text" && !transcriptText.trim()) {
      return setError("Please enter transcript text.");
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let res;
      if (inputMode === "audio") {
        const formData = new FormData();
        formData.append("file", file);
        res = await fetch(API_URL, {
          method: "POST",
          body: formData,
          mode: "cors",
          cache: "no-store",
        });
      } else {
        res = await fetch(TRANSCRIPT_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: transcriptText.trim(),
            metadata: { ui_text_source: textSource },
            external_id: "ui_input",
            source_type: textSource,
          }),
          mode: "cors",
          cache: "no-store",
        });
      }

      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((item) => item.msg || item).join(" ")
              : `Request failed (${res.status})`,
        );
      }

      setResult(inputMode === "text" ? { ...data, transcript: transcriptText.trim() } : data);
      await refreshDashboard();
    } catch (err) {
      setError(friendlyFetchError(err instanceof Error ? err.message : "Something went wrong."));
    } finally {
      setLoading(false);
    }
  };

  const metrics = [
    ["Total records", revenueLoading ? "..." : totalRecords.toLocaleString(), "teal"],
    ["Parsed budget", revenueLoading ? "..." : formatCurrency(totalBudget), "orange"],
    ["High intent", revenueLoading ? "..." : highIntentCount.toLocaleString(), "blue"],
    ["Avg. opportunity", revenueLoading ? "..." : formatCurrency(averageBudget), "green"],
  ];

  const renderUploadResults = () =>
    !result || loading ? null : (
      <div className="crm-stack">
        <div className="crm-card crm-card--elevated">
          <div className="crm-result-hero">
            <div>
              <p className="crm-result-hero-title">Record created</p>
              <p className="crm-result-hero-sub">
                Extraction and entity mapping completed. Review the normalized fields below.
              </p>
            </div>
            <div className="crm-result-hero-ids">
              <span className="crm-id-chip"><span className="crm-id-chip-lbl">Job</span>{result.job_id || "--"}</span>
              <span className="crm-id-chip"><span className="crm-id-chip-lbl">Record</span>#{result.record_id ?? "--"}</span>
            </div>
          </div>
          <div className="crm-result-strip">
            {[
              ["Budget", showField(result.extracted?.budget)],
              ["Intent", showField(result.extracted?.intent)],
              ["Timeline", showField(result.extracted?.timeline)],
            ].map(([label, value]) => (
              <div className="crm-strip-item" key={label}>
                <div className="crm-strip-label">{label}</div>
                <div className="crm-strip-value">{value}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="crm-card">
          <div className="crm-section-title-row">
            <p className="crm-section-title">Entity mapping</p>
            <span className="crm-meta-pill">{result.mapping_method || "--"} / {result.source_type || "--"}</span>
          </div>
          <div className="crm-mapping">
            {[
              ["Account", result.account_id],
              ["Contact", result.contact_id],
              ["Deal", result.deal_id],
            ].map(([label, value]) => (
              <div className="crm-map-item" key={label}>
                <div className="crm-map-label">{label}</div>
                <div className="crm-map-id">{value ?? "--"}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="crm-card">
          <p className="crm-section-title">Structured extraction</p>
          <div className="crm-grid">
            <div className="crm-field"><div className="crm-field-label">Industry</div><div className="crm-field-value">{showField(result.extracted?.industry)}</div></div>
            <div className="crm-field"><div className="crm-field-label">Product</div><div className="crm-field-value">{showField(result.extracted?.product)}</div></div>
            <div className="crm-field crm-field--full">
              <div className="crm-field-label">Competitors</div>
              <div className="crm-field-value">
                {Array.isArray(result.extracted?.competitors) && result.extracted.competitors.length ? (
                  <ul className="crm-list">{result.extracted.competitors.map((item, index) => <li key={index}>{item}</li>)}</ul>
                ) : "--"}
              </div>
            </div>
          </div>
          {customEntries.length ? (
            <>
              <p className="crm-section-title crm-section-title--spaced">Custom fields ({customEntries.length})</p>
              <div className="crm-kv-grid">
                {customEntries.map(([key, value]) => (
                  <div className="crm-kv" key={key}>
                    <div className="crm-kv-k">{key}</div>
                    <div className="crm-kv-v">{String(value)}</div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
        <div className="crm-card">
          <div className="crm-section-title-row">
            <p className="crm-section-title">Transcript</p>
            {result.structured_transcript?.segments?.length ? (
              <span className="crm-meta-pill">{result.structured_transcript.segments.length} segments</span>
            ) : null}
          </div>
          {result.structured_transcript?.segments?.length ? (
            <div className="crm-seg-list">
              {result.structured_transcript.segments.map((seg, index) => (
                <div className="crm-seg" key={index}>
                  <div className="crm-seg-head">
                    <span className="crm-seg-time">{formatTimestamp(seg.start)} - {formatTimestamp(seg.end)}</span>
                    {seg.speaker ? <span className="crm-seg-sp">{seg.speaker}</span> : null}
                  </div>
                  <p className="crm-seg-body">{seg.text}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="crm-transcript">{result.transcript || "--"}</div>
          )}
        </div>
      </div>
    );

  return (
    <div className="crm">
      <div className="crm-bg" aria-hidden="true" />
      <div className="crm-layout">
        <aside className="crm-sidebar">
          <div className="crm-sidebar-brand">
            <div className="crm-sidebar-brand-mark">R</div>
            <div>
              <span className="crm-sidebar-brand-text">Relanto CRM AI</span>
              <span className="crm-sidebar-tagline">Pipeline intelligence workspace</span>
            </div>
          </div>
          <nav className="crm-nav">
            {NAV_ITEMS.map(([id, label, short]) => (
              <button key={id} type="button" className={`crm-nav-item${activeSection === id ? " crm-nav-item--active" : ""}`} onClick={() => setActiveSection(id)}>
                <span className="crm-nav-item-kicker">{short}</span>
                <span className="crm-nav-item-label">{label}</span>
              </button>
            ))}
          </nav>
          <div className="crm-sidebar-footer">
            <div className="crm-sidebar-footer-label">Workspace health</div>
            <div className="crm-sidebar-footer-value">{revenueError || crmRecordsError ? "Needs attention" : "Live"}</div>
          </div>
        </aside>
        <main className="crm-main">
          <div className="crm-topbar">
            <div>
              <p className="crm-topbar-eyebrow">{PAGE_META[activeSection].eyebrow}</p>
              <h1 className="crm-topbar-title">{PAGE_META[activeSection].title}</h1>
            </div>
            <div className="crm-topbar-pills">
              <span className="crm-topbar-pill">{revenueLoading ? "Syncing..." : `${totalRecords} records`}</span>
              <span className="crm-topbar-pill crm-topbar-pill--accent">{loading ? "Processing live" : "Workspace ready"}</span>
            </div>
          </div>
          <div className="crm-inner">
            <p className="crm-page-desc">{PAGE_META[activeSection].desc}</p>
            {activeSection === "dashboard" && (
              <div className="crm-stack">
                <section className="crm-hero-panel">
                  <div className="crm-hero-copy">
                    <span className="crm-hero-badge">Hub-style pipeline view</span>
                    <h2 className="crm-hero-title">A cleaner front door for sales operations</h2>
                    <p className="crm-hero-text">Capture signals, review opportunity quality, and audit mapped CRM records in one calmer workspace.</p>
                    <div className="crm-hero-actions">
                      <button type="button" className="crm-btn" onClick={() => setActiveSection("upload")}>Capture interaction</button>
                      <button type="button" className="crm-btn crm-btn--ghost" onClick={() => setActiveSection("records")}>Review records</button>
                    </div>
                  </div>
                  <div className="crm-hero-aside">
                    <div className="crm-mini-card"><span className="crm-mini-label">Latest mapped row</span><strong className="crm-mini-value">{latestRecord ? `#${latestRecord.id}` : "--"}</strong><p className="crm-mini-copy">{latestRecord ? `${latestRecord.source_type || "unknown source"} / ${latestRecord.intent || "intent pending"}` : "Run an upload to populate recent activity."}</p></div>
                    <div className="crm-mini-card"><span className="crm-mini-label">Budget in view</span><strong className="crm-mini-value">{formatCompact(totalBudget)}</strong><p className="crm-mini-copy">Commercial signals available for analytics and record review.</p></div>
                  </div>
                </section>
                <section className="crm-overview-grid">
                  {metrics.map(([label, value, tone]) => (
                    <article className={`crm-overview-card crm-overview-card--${tone}`} key={label}>
                      <div className="crm-overview-label">{label}</div>
                      <div className="crm-overview-value">{value}</div>
                    </article>
                  ))}
                </section>
                <section className="crm-two-col">
                  <div className="crm-card">
                    <div className="crm-section-title-row"><p className="crm-section-title">Operating rhythm</p><span className="crm-meta-pill">Suggested next steps</span></div>
                    <div className="crm-playbook">
                      {[
                        ["1", "Ingest new interactions", "Upload audio or paste notes so Whisper and Gemini can normalize the record."],
                        ["2", "Review intent and budget", "Use analytics to isolate stronger opportunities and focus follow-up."],
                        ["3", "Audit mapped records", "Check account, contact, and deal links before downstream updates."],
                      ].map(([step, title, body]) => (
                        <div className="crm-playbook-item" key={step}>
                          <div className="crm-playbook-step">{step}</div>
                          <div><div className="crm-playbook-title">{title}</div><p className="crm-playbook-copy">{body}</p></div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="crm-card">
                    <div className="crm-section-title-row"><p className="crm-section-title">Snapshot</p><span className="crm-meta-pill">Live counters</span></div>
                    <div className="crm-snapshot-grid">
                      {[
                        ["Filtered records", filteredRevenueRecords.length],
                        ["Intent filter", analyticsIntent],
                        ["CRM rows", crmRecordsLoading ? "..." : crmCount.toLocaleString()],
                        ["API status", revenueError || crmRecordsError ? "Check API" : "Healthy"],
                      ].map(([label, value]) => (
                        <div className="crm-snapshot-item" key={label}><span className="crm-snapshot-label">{label}</span><strong>{value}</strong></div>
                      ))}
                    </div>
                  </div>
                </section>
              </div>
            )}

            {activeSection === "upload" && (
              <div className="crm-stack">
                <section className="crm-two-col crm-two-col--wide">
                  <div className="crm-card">
                    <div className="crm-section-title-row"><p className="crm-section-title">Capture workflow</p><span className="crm-meta-pill">Audio or text</span></div>
                    <div className="crm-mode-tabs" role="tablist">
                      <button type="button" className={`crm-mode-tab${inputMode === "audio" ? " crm-mode-tab--active" : ""}`} onClick={() => setInputMode("audio")} disabled={loading}>Audio upload</button>
                      <button type="button" className={`crm-mode-tab${inputMode === "text" ? " crm-mode-tab--active" : ""}`} onClick={() => setInputMode("text")} disabled={loading}>Text capture</button>
                    </div>
                    {inputMode === "audio" ? (
                      <div className="crm-mode-panel">
                        <div className="crm-upload-row">
                          <div className="crm-file-wrap">
                            <input id="audio-file" className="crm-file-input" type="file" accept="audio/*,video/*" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setError(null); setResult(null); }} disabled={loading} />
                            <label htmlFor="audio-file" className="crm-file-label">Drop a recording or choose a file</label>
                          </div>
                          <button type="button" className="crm-btn" onClick={handleProcess} disabled={loading || !file}>{loading ? "Processing..." : "Process audio"}</button>
                        </div>
                        {file ? <p className="crm-file-name">Selected file: {file.name}</p> : null}
                      </div>
                    ) : (
                      <div className="crm-mode-panel">
                        <p className="crm-section-title">Source type</p>
                        <div className="crm-source-chips">
                          {Object.keys(TEXT_PLACEHOLDERS).map((key) => (
                            <button key={key} type="button" className={`crm-chip${textSource === key ? " crm-chip--on" : ""}`} onClick={() => setTextSource(key)} disabled={loading}>{key === "crm_update" ? "CRM" : key}</button>
                          ))}
                        </div>
                        <textarea className="crm-textarea" value={transcriptText} placeholder={TEXT_PLACEHOLDERS[textSource]} onChange={(e) => { setTranscriptText(e.target.value); setError(null); }} disabled={loading} />
                        <div className="crm-text-actions"><button type="button" className="crm-btn" onClick={handleProcess} disabled={loading || !transcriptText.trim()}>{loading ? "Processing..." : "Process text"}</button></div>
                      </div>
                    )}
                  </div>
                  <div className="crm-card">
                    <div className="crm-section-title-row"><p className="crm-section-title">What happens next</p><span className="crm-meta-pill">Pipeline automation</span></div>
                    <div className="crm-side-notes">
                      {[
                        ["Transcription", "Audio is transcribed first so the rest of the stack can work from clean text."],
                        ["Extraction", "Gemini parses budget, intent, timeline, product, and competitor details."],
                        ["Mapping", "The app links the interaction to account, contact, and deal IDs for CRM analysis."],
                      ].map(([title, body]) => (
                        <div className="crm-side-note" key={title}><strong>{title}</strong><p>{body}</p></div>
                      ))}
                    </div>
                  </div>
                </section>
                {error ? <div className="crm-error"><strong>Processing issue</strong>{error}</div> : null}
                {renderUploadResults()}
              </div>
            )}
            {activeSection === "analytics" && (
              <div className="crm-stack">
                <section className="crm-overview-grid crm-overview-grid--compact">
                  {[
                    ["Filtered records", filteredRevenueRecords.length, "teal"],
                    ["Filtered budget", formatCurrency(filteredRevenueTotalBudget), "orange"],
                    ["Intent mode", analyticsIntent, "blue"],
                  ].map(([label, value, tone]) => (
                    <article className={`crm-overview-card crm-overview-card--${tone}`} key={label}>
                      <div className="crm-overview-label">{label}</div>
                      <div className="crm-overview-value">{value}</div>
                    </article>
                  ))}
                </section>
                <div className="crm-card">
                  <div className="crm-section-title-row"><p className="crm-section-title">Revenue analytics</p><span className="crm-meta-pill">Budget by record</span></div>
                  {revenueLoading ? <p className="crm-revenue-loading">Loading analytics...</p> : null}
                  {!revenueLoading && revenueError ? <p className="crm-revenue-err">{revenueError}</p> : null}
                  {!revenueLoading && !revenueError && revenueData ? (
                    revenueData.total_records === 0 || !revenueData.records?.length ? (
                      <p className="crm-revenue-empty">No CRM records yet. Use Capture to populate the analytics view.</p>
                    ) : (
                      <>
                        <div className="crm-analytics-filters">
                          <div className="crm-filter-group"><span className="crm-filter-label">Budget range</span><div className="crm-filter-inputs"><input type="number" className="crm-filter-input" placeholder="Min" value={analyticsBudgetMin} onChange={(e) => setAnalyticsBudgetMin(e.target.value)} /><span className="crm-filter-sep">to</span><input type="number" className="crm-filter-input" placeholder="Max" value={analyticsBudgetMax} onChange={(e) => setAnalyticsBudgetMax(e.target.value)} /></div></div>
                          <div className="crm-filter-group"><label className="crm-filter-label" htmlFor="analytics-intent">Intent</label><select id="analytics-intent" className="crm-filter-select" value={analyticsIntent} onChange={(e) => setAnalyticsIntent(e.target.value)}><option value="all">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>
                          <button type="button" className="crm-filter-reset" onClick={() => { setAnalyticsBudgetMin(""); setAnalyticsBudgetMax(""); setAnalyticsIntent("all"); }}>Reset filters</button>
                        </div>
                        {filteredRevenueRecords.length ? (
                          <div className="crm-chart-wrap">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={filteredRevenueRecords} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                                <defs><linearGradient id="revenueBarFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ff7a59" /><stop offset="100%" stopColor="#ffb36b" /></linearGradient></defs>
                                <CartesianGrid stroke="rgba(102, 116, 139, 0.14)" vertical={false} />
                                <XAxis dataKey="id" stroke="#94a3b8" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} />
                                <YAxis stroke="#94a3b8" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} tickFormatter={(value) => (value >= 1000 ? `${value / 1000}k` : String(value))} />
                                <Tooltip cursor={{ fill: "rgba(255, 122, 89, 0.08)" }} contentStyle={{ background: "#fff", border: "1px solid rgba(148, 163, 184, 0.2)", borderRadius: "14px", color: "#0f172a" }} formatter={(value) => [typeof value === "number" ? value.toLocaleString() : value, "Budget"]} labelFormatter={(label) => `Record #${label}`} />
                                <Bar dataKey="budget" fill="url(#revenueBarFill)" radius={[10, 10, 0, 0]} maxBarSize={42} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        ) : <p className="crm-revenue-no-data">No records match the current filters.</p>}
                      </>
                    )
                  ) : null}
                </div>
              </div>
            )}
            {activeSection === "records" && (
              <div className="crm-stack">
                <section className="crm-overview-grid crm-overview-grid--compact">
                  {[
                    ["Rows available", crmRecordsLoading ? "..." : crmCount.toLocaleString(), "green"],
                    ["Latest record", latestRecord ? `#${latestRecord.id}` : "--", "orange"],
                  ].map(([label, value, tone]) => (
                    <article className={`crm-overview-card crm-overview-card--${tone}`} key={label}>
                      <div className="crm-overview-label">{label}</div>
                      <div className="crm-overview-value">{value}</div>
                    </article>
                  ))}
                </section>
                <div className="crm-card">
                  {crmRecordsLoading ? <p className="crm-records-loading">Loading records...</p> : null}
                  {!crmRecordsLoading && crmRecordsError ? <p className="crm-records-err">{crmRecordsError}</p> : null}
                  {!crmRecordsLoading && !crmRecordsError && crmRecords?.length === 0 ? <p className="crm-records-empty">No CRM records yet. Capture an interaction to populate this workspace.</p> : null}
                  {!crmRecordsLoading && !crmRecordsError && crmRecords?.length ? (
                    <div className="crm-table-wrap">
                      <table className="crm-table">
                        <thead><tr><th>ID</th><th>Source</th><th>Budget</th><th>Intent</th><th>Industry</th><th>Timeline</th><th>Acct</th><th>Contact</th><th>Deal</th></tr></thead>
                        <tbody>
                          {crmRecords.map((row) => (
                            <tr key={row.id}>
                              <td className="crm-td-mono">{row.id}</td>
                              <td className="crm-td-muted">{row.source_type || "--"}</td>
                              <td className="crm-td-mono">{typeof row.budget === "number" ? row.budget.toLocaleString() : "--"}</td>
                              <td>{row.intent || "--"}</td>
                              <td>{row.industry || "--"}</td>
                              <td>{row.timeline || "--"}</td>
                              <td className="crm-td-mono crm-td-muted">{row.account_id ?? "--"}</td>
                              <td className="crm-td-mono crm-td-muted">{row.contact_id ?? "--"}</td>
                              <td className="crm-td-mono crm-td-muted">{row.deal_id ?? "--"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
