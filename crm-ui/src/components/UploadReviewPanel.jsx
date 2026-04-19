import React, { useMemo, useState } from "react";
import { api, fetchJson } from "../lib/api.js";

const SPEAKER_PRESETS = [
  "Speaker A",
  "Speaker B",
  "Sales",
  "Customer",
  "Prospect",
  "Support",
  "Agent",
  "Unknown",
];

function splitCsv(s) {
  return String(s || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function normalizeSegments(structured, fallbackTranscript) {
  const segs = structured?.segments;
  if (Array.isArray(segs) && segs.length > 0) {
    return segs.map((s) => ({
      start: typeof s.start === "number" ? s.start : Number(s.start) || 0,
      end: typeof s.end === "number" ? s.end : Number(s.end) || 0,
      text: String(s.text ?? "").trim(),
      speaker: s.speaker != null && s.speaker !== undefined ? String(s.speaker).trim() : "",
    }));
  }
  const t = String(fallbackTranscript ?? "").trim();
  return t ? [{ start: 0, end: 0, text: t, speaker: "" }] : [];
}

function fmtTs(sec) {
  try {
    const s = Math.max(0, Math.floor(Number(sec) || 0));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  } catch {
    return "00:00";
  }
}

/**
 * After audio ingest: edit Groq-extracted fields and Whisper segments + speaker labels, then PATCH CRM record.
 */
export default function UploadReviewPanel({ ingestResponse, onDismiss }) {
  const recordId = ingestResponse?.record_id;
  const extractedIn = ingestResponse?.extracted ?? {};
  const structuredIn = ingestResponse?.structured_transcript;
  const transcriptIn = ingestResponse?.transcript ?? "";

  const [extracted, setExtracted] = useState(() => ({
    budget: extractedIn.budget ?? "",
    intent: extractedIn.intent ?? "",
    product: extractedIn.product ?? "",
    product_version: extractedIn.product_version ?? "",
    timeline: extractedIn.timeline ?? "",
    industry: extractedIn.industry ?? "",
    pain_points: extractedIn.pain_points ?? "",
    next_step: extractedIn.next_step ?? "",
    urgency_reason: extractedIn.urgency_reason ?? "",
    mentioned_company: extractedIn.mentioned_company ?? "",
    procurement_stage: extractedIn.procurement_stage ?? "",
    use_case: extractedIn.use_case ?? "",
    decision_criteria: extractedIn.decision_criteria ?? "",
    budget_owner: extractedIn.budget_owner ?? "",
    implementation_scope: extractedIn.implementation_scope ?? "",
    competitorsCsv: Array.isArray(extractedIn.competitors) ? extractedIn.competitors.join(", ") : "",
    stakeholdersCsv: Array.isArray(extractedIn.stakeholders) ? extractedIn.stakeholders.join(", ") : "",
  }));

  const [segments, setSegments] = useState(() => normalizeSegments(structuredIn, transcriptIn));

  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState(null);
  const [saveOk, setSaveOk] = useState(false);

  const datalistOptions = useMemo(() => {
    const u = new Set(SPEAKER_PRESETS);
    segments.forEach((s) => {
      if (s.speaker) u.add(s.speaker);
    });
    return [...u].filter(Boolean).sort();
  }, [segments]);

  const updateSegment = (i, patch) => {
    setSegments((prev) => prev.map((row, j) => (j === i ? { ...row, ...patch } : row)));
  };

  const saveToCrm = async () => {
    if (recordId == null) return;
    setSaving(true);
    setSaveErr(null);
    setSaveOk(false);
    try {
      const plain_text = segments
        .map((s) => s.text)
        .filter(Boolean)
        .join(" ")
        .trim();
      const structured_transcript = {
        plain_text,
        segments: segments.map((s) => ({
          start: Number(s.start) || 0,
          end: Number(s.end) || 0,
          text: String(s.text || "").trim(),
          speaker: s.speaker?.trim() || null,
        })),
      };
      await fetchJson(api.crmRecord(recordId), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          budget: extracted.budget,
          intent: extracted.intent,
          product: extracted.product,
          product_version: extracted.product_version,
          timeline: extracted.timeline,
          industry: extracted.industry,
          pain_points: extracted.pain_points,
          next_step: extracted.next_step,
          urgency_reason: extracted.urgency_reason,
          mentioned_company: extracted.mentioned_company,
          procurement_stage: extracted.procurement_stage,
          use_case: extracted.use_case,
          decision_criteria: extracted.decision_criteria,
          budget_owner: extracted.budget_owner,
          implementation_scope: extracted.implementation_scope,
          competitors: splitCsv(extracted.competitorsCsv),
          stakeholders: splitCsv(extracted.stakeholdersCsv),
          structured_transcript,
        }),
      });
      setSaveOk(true);
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (recordId == null) return null;

  return (
    <div className="mt-8 rounded-2xl border border-secondary/25 bg-surface-container-low/90 p-6 shadow-lg">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Review</span>
          <h3 className="font-headline text-xl font-bold text-primary">Extracted data &amp; transcript</h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            CRM record <span className="font-mono font-semibold">#{recordId}</span>. Correct speakers or text, then save to update the
            database.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-full border border-outline-variant/30 px-4 py-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant hover:bg-surface-container-high"
          >
            Hide
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={saveToCrm}
            className="rounded-full bg-primary px-5 py-2 text-xs font-bold uppercase tracking-widest text-on-primary disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save corrections to CRM"}
          </button>
        </div>
      </div>

      {saveErr && (
        <p className="mb-4 rounded-lg border border-error/30 bg-error-container/20 px-3 py-2 text-sm text-error" role="alert">
          {saveErr}
        </p>
      )}
      {saveOk && (
        <p className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900" role="status">
          Saved. You can open this record anytime under CRM Records.
        </p>
      )}

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h4 className="mb-3 font-headline text-xs font-bold uppercase tracking-widest text-primary">Extracted fields (Groq)</h4>
          <div className="grid max-h-[min(60vh,520px)] grid-cols-1 gap-3 overflow-y-auto pr-1">
            {[
              ["mentioned_company", "Company"],
              ["product", "Product"],
              ["product_version", "Product version"],
              ["budget", "Budget"],
              ["intent", "Intent"],
              ["timeline", "Timeline"],
              ["industry", "Industry"],
              ["pain_points", "Pain points"],
              ["next_step", "Next step"],
              ["urgency_reason", "Urgency"],
              ["procurement_stage", "Stage"],
              ["use_case", "Use case"],
              ["decision_criteria", "Decision criteria"],
              ["budget_owner", "Budget owner"],
              ["implementation_scope", "Scope"],
            ].map(([key, label]) => (
              <label key={key} className="block text-[10px] font-bold uppercase text-on-surface-variant">
                {label}
                <input
                  value={extracted[key] ?? ""}
                  onChange={(e) => setExtracted((ex) => ({ ...ex, [key]: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-outline-variant/25 bg-background px-2 py-1.5 text-sm text-primary"
                />
              </label>
            ))}
            <label className="block text-[10px] font-bold uppercase text-on-surface-variant">
              Competitors (comma-separated)
              <input
                value={extracted.competitorsCsv}
                onChange={(e) => setExtracted((ex) => ({ ...ex, competitorsCsv: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-outline-variant/25 bg-background px-2 py-1.5 text-sm text-primary"
              />
            </label>
            <label className="block text-[10px] font-bold uppercase text-on-surface-variant">
              Stakeholders (comma-separated)
              <input
                value={extracted.stakeholdersCsv}
                onChange={(e) => setExtracted((ex) => ({ ...ex, stakeholdersCsv: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-outline-variant/25 bg-background px-2 py-1.5 text-sm text-primary"
              />
            </label>
          </div>
        </div>

        <div>
          <h4 className="mb-3 font-headline text-xs font-bold uppercase tracking-widest text-primary">Transcript segments (Whisper + speaker)</h4>
          <p className="mb-3 text-xs text-on-surface-variant">
            Pick the speaker label that best fits each slice. Add a custom label via the text field if needed.
          </p>
          <datalist id={`upload-speaker-suggestions-${recordId}`}>
            {datalistOptions.map((sp) => (
              <option key={sp} value={sp} />
            ))}
          </datalist>
          <div className="max-h-[min(60vh,520px)] space-y-3 overflow-y-auto pr-1">
            {segments.length === 0 ? (
              <p className="text-sm text-on-surface-variant">No segments returned.</p>
            ) : (
              segments.map((seg, i) => (
                <div key={i} className="rounded-xl border border-outline-variant/15 bg-background p-3">
                  <div className="mb-2 flex flex-wrap items-end gap-3">
                    <span className="font-mono text-[10px] text-on-surface-variant">
                      {fmtTs(seg.start)} → {fmtTs(seg.end)}
                    </span>
                    <label className="flex min-w-[180px] flex-1 flex-col gap-1 text-[10px] font-bold uppercase text-on-surface-variant">
                      Speaker
                      <input
                        type="text"
                        list={recordId != null ? `upload-speaker-suggestions-${recordId}` : undefined}
                        value={seg.speaker}
                        onChange={(e) => updateSegment(i, { speaker: e.target.value })}
                        placeholder="e.g. Sales, Customer"
                        className="rounded-lg border border-outline-variant/30 bg-surface-container-high px-2 py-1.5 text-xs font-semibold normal-case text-primary"
                      />
                    </label>
                  </div>
                  <textarea
                    value={seg.text}
                    onChange={(e) => updateSegment(i, { text: e.target.value })}
                    rows={3}
                    className="w-full rounded-lg border border-outline-variant/20 bg-surface-container-low/50 p-2 text-sm leading-relaxed text-primary"
                  />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
