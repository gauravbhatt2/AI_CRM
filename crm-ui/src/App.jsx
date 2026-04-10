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

  const resetAnalyticsFilters = () => {
    setAnalyticsBudgetMin("");
    setAnalyticsBudgetMax("");
    setAnalyticsIntent("all");
  };

  const refreshDashboard = async () => {
    try {
      const [revRes, crmRes] = await Promise.all([
        fetch(REVENUE_API_URL, { mode: "cors", cache: "no-store" }),
        fetch(CRM_RECORDS_API_URL, { mode: "cors", cache: "no-store" }),
      ]);
      const revText = await revRes.text();
      const crmText = await crmRes.text();
      let revData = {};
      let crmData = [];
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
      if (revRes.ok) {
        setRevenueData({
          total_records: revData.total_records ?? 0,
          total_budget: revData.total_budget ?? 0,
          records: Array.isArray(revData.records) ? revData.records : [],
        });
        setRevenueError(null);
      }
      if (crmRes.ok) {
        setCrmRecords(Array.isArray(crmData) ? crmData : []);
        setCrmRecordsError(null);
      }
    } catch {
      /* non-fatal */
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function fetchRevenue() {
      setRevenueLoading(true);
      setRevenueError(null);
      try {
        const res = await fetch(REVENUE_API_URL, {
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
          const detail =
            typeof data.detail === "string"
              ? data.detail
              : `Request failed (${res.status})`;
          throw new Error(detail);
        }
        if (!cancelled) {
          setRevenueData({
            total_records: data.total_records ?? 0,
            total_budget: data.total_budget ?? 0,
            records: Array.isArray(data.records) ? data.records : [],
          });
        }
      } catch (err) {
        const raw =
          err instanceof Error ? err.message : "Failed to load revenue data.";
        if (!cancelled) {
          setRevenueError(friendlyFetchError(raw));
          setRevenueData(null);
        }
      } finally {
        if (!cancelled) setRevenueLoading(false);
      }
    }

    fetchRevenue();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchCrmRecords() {
      setCrmRecordsLoading(true);
      setCrmRecordsError(null);
      try {
        const res = await fetch(CRM_RECORDS_API_URL, {
          mode: "cors",
          cache: "no-store",
        });
        const text = await res.text();
        let data;
        try {
          data = text ? JSON.parse(text) : [];
        } catch {
          throw new Error(text || `Request failed (${res.status})`);
        }
        if (!res.ok) {
          const detail =
            typeof data.detail === "string"
              ? data.detail
              : `Request failed (${res.status})`;
          throw new Error(detail);
        }
        if (!cancelled) {
          setCrmRecords(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        const raw =
          err instanceof Error ? err.message : "Failed to load CRM records.";
        if (!cancelled) {
          setCrmRecordsError(friendlyFetchError(raw));
          setCrmRecords(null);
        }
      } finally {
        if (!cancelled) setCrmRecordsLoading(false);
      }
    }

    fetchCrmRecords();
    return () => {
      cancelled = true;
    };
  }, []);

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
  const customEntries =
    ex?.custom_fields && typeof ex.custom_fields === "object"
      ? Object.entries(ex.custom_fields).filter(
          ([, v]) => v != null && String(v).trim() !== "",
        )
      : [];

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
            <p className="crm-section-title">Transcript</p>
            <span className="crm-meta-pill" style={{ marginBottom: 0 }}>
              {result.structured_transcript.segments.length} segments · speakers
            </span>
          </div>
          <div className="crm-seg-list">
            {result.structured_transcript.segments.map((seg, i) => (
              <div key={i} className="crm-seg">
                <div className="crm-seg-head">
                  <span className="crm-seg-time">
                    {formatTimestamp(seg.start)} – {formatTimestamp(seg.end)}
                  </span>
                  {seg.speaker ? (
                    <span className="crm-seg-sp">{seg.speaker}</span>
                  ) : null}
                </div>
                <p className="crm-seg-body">{seg.text}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="crm-card">
          <p className="crm-section-title">Transcript</p>
          <div className="crm-transcript">{result.transcript || "—"}</div>
        </div>
      );

    return (
      <>
        <div className="crm-card crm-card--elevated">
          <div className="crm-result-hero">
            <div className="crm-result-hero-main">
              <p className="crm-result-hero-title">Ingestion complete</p>
              <p className="crm-result-hero-sub">
                Structured fields and CRM links are saved. Reference this job
                when auditing.
              </p>
            </div>
            <div className="crm-result-hero-ids">
              <span className="crm-id-chip">
                <span className="crm-id-chip-lbl">Job</span>
                {result.job_id || "—"}
              </span>
              <span className="crm-id-chip">
                <span className="crm-id-chip-lbl">Record</span>
                {`#${result.record_id ?? "—"}`}
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

        <div className="crm-card">
          <div className="crm-section-title-row">
            <p className="crm-section-title">Entity mapping</p>
            <span className="crm-meta-pill" style={{ marginBottom: 0 }}>
              {result.mapping_method || "—"} · {result.source_type || "—"}
            </span>
          </div>
          <div className="crm-mapping">
            <div className="crm-map-item">
              <div className="crm-map-label">Account</div>
              <div className="crm-map-id">{result.account_id ?? "—"}</div>
            </div>
            <div className="crm-map-item">
              <div className="crm-map-label">Contact</div>
              <div className="crm-map-id">{result.contact_id ?? "—"}</div>
            </div>
            <div className="crm-map-item">
              <div className="crm-map-label">Deal</div>
              <div className="crm-map-id">{result.deal_id ?? "—"}</div>
            </div>
          </div>
        </div>

        <div className="crm-card">
          <p className="crm-section-title">Full extraction</p>
          <div className="crm-grid">
            <div className="crm-field">
              <div className="crm-field-label">Industry</div>
              <div className="crm-field-value">{showField(ex?.industry)}</div>
            </div>
            <div className="crm-field">
              <div className="crm-field-label">Product</div>
              <div className="crm-field-value">{showField(ex?.product)}</div>
            </div>
            <div className="crm-field" style={{ gridColumn: "1 / -1" }}>
              <div className="crm-field-label">Competitors</div>
              <div className="crm-field-value">
                {Array.isArray(ex?.competitors) && ex.competitors.length > 0 ? (
                  <ul className="crm-list">
                    {ex.competitors.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>
          {customEntries.length > 0 ? (
            <>
              <p className="crm-section-title" style={{ marginTop: "1.25rem" }}>
                Custom fields ({customEntries.length})
              </p>
              <div className="crm-kv-grid">
                {customEntries.map(([k, v]) => (
                  <div key={k} className="crm-kv">
                    <div className="crm-kv-k">{k}</div>
                    <div className="crm-kv-v">{String(v)}</div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
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
            <span className="crm-sidebar-brand-text">AI CRM</span>
            <span className="crm-sidebar-tagline">Revenue intelligence</span>
          </div>
          <nav className="crm-nav">
            {[
              ["dashboard", "Dashboard"],
              ["upload", "Upload"],
              ["analytics", "Analytics"],
              ["records", "CRM Records"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={
                  "crm-nav-item" +
                  (activeSection === id ? " crm-nav-item--active" : "")
                }
                aria-current={activeSection === id ? "page" : undefined}
                onClick={() => setActiveSection(id)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="crm-sidebar-footer">Interaction mining</div>
        </aside>

        <main className="crm-main">
          <div className="crm-inner">
            {activeSection === "dashboard" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Dashboard</h1>
                  <p className="crm-page-desc">
                    Snapshot of ingested interactions and parsed revenue
                    signals.
                  </p>
                </div>
                <div className="crm-card crm-dash-panel">
                  <p className="crm-section-title">At a glance</p>
                  <div className="crm-dash-stats">
                    <div className="crm-dash-stat">
                      <div className="crm-dash-stat-label">Total records</div>
                      <div className="crm-dash-stat-value">
                        {revenueLoading
                          ? "…"
                          : (revenueData?.total_records ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="crm-dash-stat">
                      <div className="crm-dash-stat-label">
                        Combined budget (parsed)
                      </div>
                      <div className="crm-dash-stat-value">
                        {revenueLoading
                          ? "…"
                          : Number(
                              revenueData?.total_budget ?? 0,
                            ).toLocaleString()}
                      </div>
                    </div>
                    <div className="crm-dash-stat">
                      <div className="crm-dash-stat-label">Rows in CRM</div>
                      <div className="crm-dash-stat-value">
                        {crmRecordsLoading
                          ? "…"
                          : (crmRecords?.length ?? 0).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="crm-dash-hint">
                    <strong>Tip:</strong> Use <strong>Upload</strong> to ingest
                    audio or text, <strong>Analytics</strong> for the budget
                    chart, and <strong>CRM Records</strong> for the full table.
                  </div>
                  <div className="crm-dash-actions">
                    <button
                      type="button"
                      className="crm-dash-action"
                      onClick={() => setActiveSection("upload")}
                    >
                      New upload
                    </button>
                    <button
                      type="button"
                      className="crm-dash-action"
                      onClick={() => setActiveSection("analytics")}
                    >
                      View analytics
                    </button>
                    <button
                      type="button"
                      className="crm-dash-action"
                      onClick={() => setActiveSection("records")}
                    >
                      Browse records
                    </button>
                  </div>
                </div>
              </>
            )}

            {activeSection === "upload" && (
              <>
                <div className="crm-page-head">
                  <h1 className="crm-page-title">Upload</h1>
                  <p className="crm-page-desc">
                    Transcribe calls (Whisper), extract CRM fields (Gemini), and
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
                          {loading && (
                            <span
                              className="crm-btn-spinner"
                              aria-hidden="true"
                            />
                          )}
                          {loading ? "Processing..." : "Process Audio"}
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
                          {loading && (
                            <span
                              className="crm-btn-spinner"
                              aria-hidden="true"
                            />
                          )}
                          {loading ? "Processing..." : "Process Text"}
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
                    <p className="crm-revenue-loading" role="status">
                      Loading analytics...
                    </p>
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
                    All ingested rows with mapped account, contact, and deal
                    ids.
                  </p>
                </div>

                <div className="crm-card crm-records-card">
                  {crmRecordsLoading && (
                    <p className="crm-records-loading" role="status">
                      Loading records...
                    </p>
                  )}

                  {!crmRecordsLoading && crmRecordsError && (
                    <p className="crm-records-err" role="alert">
                      {crmRecordsError}
                    </p>
                  )}

                  {!crmRecordsLoading &&
                    !crmRecordsError &&
                    crmRecords &&
                    crmRecords.length === 0 && (
                      <p className="crm-records-empty">
                        No CRM records yet. Ingest a transcript or audio to see
                        rows here.
                      </p>
                    )}

                  {!crmRecordsLoading &&
                    !crmRecordsError &&
                    crmRecords &&
                    crmRecords.length > 0 && (
                      <div className="crm-table-wrap">
                        <table className="crm-table">
                          <thead>
                            <tr>
                              <th>ID</th>
                              <th>Source</th>
                              <th>Budget</th>
                              <th>Intent</th>
                              <th>Industry</th>
                              <th>Timeline</th>
                              <th>Acct</th>
                              <th>Contact</th>
                              <th>Deal</th>
                            </tr>
                          </thead>
                          <tbody>
                            {crmRecords.map((row) => (
                              <tr key={row.id}>
                                <td className="crm-td-mono">{row.id}</td>
                                <td className="crm-td-muted">
                                  {row.source_type || "—"}
                                </td>
                                <td className="crm-td-mono">
                                  {typeof row.budget === "number"
                                    ? row.budget.toLocaleString()
                                    : "—"}
                                </td>
                                <td>{row.intent || "—"}</td>
                                <td>{row.industry || "—"}</td>
                                <td>{row.timeline || "—"}</td>
                                <td className="crm-td-mono crm-td-muted">
                                  {row.account_id ?? "—"}
                                </td>
                                <td className="crm-td-mono crm-td-muted">
                                  {row.contact_id ?? "—"}
                                </td>
                                <td className="crm-td-mono crm-td-muted">
                                  {row.deal_id ?? "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
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
