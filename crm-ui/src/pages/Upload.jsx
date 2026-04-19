import React, { useState } from "react";
import { motion as Motion } from "framer-motion";
import UploadReviewPanel from "../components/UploadReviewPanel.jsx";
import { api, fetchJson } from "../lib/api.js";

const TEXT_MAX = 50000;

const SOURCE_OPTIONS = [
  ["call", "Call"],
  ["email", "Email"],
  ["meeting", "Meeting"],
  ["sms", "SMS"],
  ["crm_update", "CRM update"],
];

const Upload = () => {
  const [mode, setMode] = useState("transcript");
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [sourceType, setSourceType] = useState("call");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  /** Full JSON from POST /ingest/audio — drives review + speaker edit UI. */
  const [audioIngestResult, setAudioIngestResult] = useState(null);

  const submitAudio = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Choose an audio or video file.");
      return;
    }
    setLoading(true);
    setError(null);
    setMessage(null);
    setAudioIngestResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(api.ingestAudio, { method: "POST", body: fd, mode: "cors" });
      const t = await res.text();
      let data = {};
      try {
        data = t ? JSON.parse(t) : {};
      } catch {
        data = {};
      }
      if (!res.ok) throw new Error(data?.detail || `Upload failed (${res.status})`);
      setAudioIngestResult(data);
      setMessage(`Ingested successfully. CRM record #${data.record_id ?? "—"} — review extraction and transcript below.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const submitTranscript = async (e) => {
    e.preventDefault();
    if (!text.trim()) {
      setError("Paste transcript text to continue.");
      return;
    }
    if (text.length > TEXT_MAX) {
      setError(`Transcript exceeds ${TEXT_MAX.toLocaleString()} characters.`);
      return;
    }
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const data = await fetchJson(api.ingestTranscript, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text.trim(),
          source_type: sourceType,
        }),
      });
      setMessage(`Saved to CRM. Record id: ${data.record_id ?? "—"}. You can review it under CRM Records.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const textLen = text.length;

  return (
    <div className="flex min-h-[calc(100vh-6rem)] flex-col">
      <div className="mb-8 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Ingestion</span>
        <h1 className="font-headline text-4xl font-extrabold tracking-tighter text-primary md:text-5xl">Upload</h1>
        <p className="mt-3 max-w-xl text-sm font-medium leading-relaxed text-on-surface-variant">
          Ingest transcripts or media (audio/video). The pipeline runs extraction and creates CRM records (Groq + DB required).
        </p>
      </div>

      <div className="grid flex-1 gap-6 lg:grid-cols-12 lg:gap-8">
        <section className="flex flex-col rounded-2xl border border-outline-variant/15 bg-surface-container-low/80 p-6 shadow-sm lg:col-span-4">
          <h2 className="font-headline text-xs font-bold uppercase tracking-widest text-primary">1 · Interaction type</h2>
          <p className="mt-2 text-xs leading-relaxed text-on-surface-variant">
            Used for both transcript and media so downstream analytics stay consistent.
          </p>
          <div className="mt-4 flex flex-col gap-2">
            {SOURCE_OPTIONS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setSourceType(id)}
                className={`rounded-xl border px-4 py-3 text-left text-sm font-semibold transition-colors ${
                  sourceType === id
                    ? "border-secondary bg-secondary/10 text-primary ring-1 ring-secondary/30"
                    : "border-outline-variant/25 bg-background text-on-surface-variant hover:border-outline-variant/50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-outline-variant/15 bg-surface-container-lowest p-6 shadow-sm lg:col-span-8">
          <div className="mb-6 flex flex-col gap-4 border-b border-outline-variant/15 pb-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-headline text-xs font-bold uppercase tracking-widest text-primary">2 · Content source</h2>
              <p className="mt-1 text-xs text-on-surface-variant">Paste text or upload a media file for transcription.</p>
            </div>
            <div className="inline-flex rounded-full bg-surface-container-high p-1">
              {[
                ["transcript", "Transcript", "article"],
                ["media", "Media", "perm_media"],
              ].map(([id, label, icon]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setMode(id)}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors ${
                    mode === id ? "bg-primary text-on-primary shadow-sm" : "text-on-surface-variant hover:text-primary"
                  }`}
                >
                  <span className="material-symbols-outlined text-base">{icon}</span>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-xl border border-error/30 bg-error-container/30 px-4 py-3 text-sm text-error" role="alert">
              {error}
            </div>
          )}
          {message && (
            <div className="mb-4 rounded-xl border border-secondary/30 bg-secondary/10 px-4 py-3 text-sm text-primary">{message}</div>
          )}

          {mode === "media" ? (
            <form onSubmit={submitAudio} className="flex flex-1 flex-col">
              <Motion.div whileHover={{ scale: 1.002 }} className="flex flex-1 flex-col">
                <div className="flex flex-1 flex-col rounded-xl border-2 border-dashed border-outline-variant/35 bg-surface-container-low/50 p-8">
                  <div className="mb-4 flex items-center gap-2 text-secondary">
                    <span className="material-symbols-outlined">graphic_eq</span>
                    <span className="font-headline text-sm font-bold">Audio or video file</span>
                  </div>
                  <p className="mb-4 text-xs text-on-surface-variant">
                    Accepts common audio and video formats. The server transcribes with Whisper; FFmpeg may be required on the host.
                  </p>
                  <input
                    type="file"
                    accept="audio/*,video/*"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-primary/10 file:px-4 file:py-2 file:font-headline file:text-xs file:font-bold file:uppercase file:text-primary"
                  />
                  {file && (
                    <p className="mt-3 text-xs font-medium text-primary">
                      Selected: <span className="font-mono">{file.name}</span> ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </p>
                  )}
                </div>
              </Motion.div>
              <div className="mt-6 border-t border-outline-variant/15 pt-6">
                <p className="mb-3 text-xs text-on-surface-variant">
                  Runs the same ingestion pipeline as transcripts; a CRM record is created from the generated text and extraction.
                </p>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-full bg-primary px-8 py-3 font-headline text-xs font-bold uppercase tracking-widest text-on-primary shadow-lg shadow-primary/15 disabled:opacity-50"
                >
                  {loading ? "Uploading…" : "Upload & ingest media"}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={submitTranscript} className="flex flex-1 flex-col">
              <div className="flex flex-1 flex-col">
                <label className="mb-2 flex items-center justify-between text-xs font-bold uppercase text-on-surface-variant">
                  <span>Transcript</span>
                  <span className={textLen > TEXT_MAX ? "font-mono text-error" : "font-mono text-on-surface-variant/80"}>
                    {textLen.toLocaleString()} / {TEXT_MAX.toLocaleString()}
                  </span>
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value.slice(0, TEXT_MAX))}
                  rows={16}
                  placeholder="Paste the full conversation or meeting notes. Include speakers if available for better extraction."
                  className="min-h-[280px] w-full flex-1 rounded-xl border border-outline-variant/30 bg-background p-4 text-sm leading-relaxed text-primary placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-secondary/25"
                />
                <p className="mt-2 text-xs text-on-surface-variant">
                  Tip: richer transcripts improve budget, intent, and risk scoring. Avoid secrets or PII you do not want stored.
                </p>
              </div>
              <div className="mt-6 border-t border-outline-variant/15 pt-6">
                <p className="mb-3 text-xs text-on-surface-variant">
                  Submits to <code className="rounded bg-surface-container-high px-1.5 py-0.5 font-mono text-[11px]">POST /ingest/transcript</code>{" "}
                  with the interaction type above.
                </p>
                <button
                  type="submit"
                  disabled={loading || !text.trim()}
                  className="rounded-full bg-primary px-8 py-3 font-headline text-xs font-bold uppercase tracking-widest text-on-primary shadow-lg shadow-primary/15 disabled:opacity-50"
                >
                  {loading ? "Processing…" : "Ingest transcript"}
                </button>
              </div>
            </form>
          )}
        </section>
      </div>

      {audioIngestResult && (
        <UploadReviewPanel
          key={`${audioIngestResult.record_id}-${audioIngestResult.job_id ?? ""}`}
          ingestResponse={audioIngestResult}
          onDismiss={() => setAudioIngestResult(null)}
        />
      )}
    </div>
  );
};

export default Upload;
