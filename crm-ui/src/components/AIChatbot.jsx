import React, { useCallback, useEffect, useState } from "react";
import { api, fetchJson } from "../lib/api.js";

const SUGGESTIONS = [
  "Summarize this deal in three bullet points.",
  "What are the main risks for this opportunity?",
  "What are the recommended next steps?",
  "What budget or timeline signals appear in the record?",
];

function formatRecordTimestamp(iso) {
  if (!iso) return "No timestamp";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "No timestamp";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getRecordLabel(record) {
  const title = (record.mentioned_company || "").trim() || record.product || "Record";
  return `#${record.id} - ${title} - ${formatRecordTimestamp(record.created_at)}`;
}

function renderMessageText(text) {
  const lines = String(text || "").split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  let list = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push({ type: "paragraph", text: paragraph.join("\n") });
    paragraph = [];
  };

  const flushList = () => {
    if (!list.length) return;
    blocks.push({ type: "list", items: list });
    list = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    const bulletMatch = trimmed.match(/^([-*•]|\d+[.)])\s+(.*)$/);

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    if (bulletMatch) {
      flushParagraph();
      list.push(bulletMatch[2]);
      continue;
    }

    flushList();
    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();

  if (!blocks.length) {
    return <p className="whitespace-pre-wrap">{text}</p>;
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, index) =>
        block.type === "list" ? (
          <ul key={index} className="list-disc space-y-1 pl-5">
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex} className="whitespace-pre-wrap">
                {item}
              </li>
            ))}
          </ul>
        ) : (
          <p key={index} className="whitespace-pre-wrap">
            {block.text}
          </p>
        ),
      )}
    </div>
  );
}

/** Full-page deal assistant rendered inside `/chat` (page title lives in ChatPage). */
export default function AIChatbot() {
  const [records, setRecords] = useState([]);
  const [recordId, setRecordId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);

  const loadRecords = useCallback(async () => {
    try {
      const r = await fetchJson(api.crmRecords);
      setRecords(Array.isArray(r) ? r : []);
    } catch {
      setRecords([]);
    }
  }, []);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  const send = async (overrideText) => {
    const id = Number(recordId);
    const q = (overrideText ?? input).trim();
    if (!id || !q) return;
    setSending(true);
    if (overrideText == null) setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    try {
      const data = await fetchJson(api.agentsChat, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ record_id: id, query: q }),
      });
      const reply = data?.response || "";
      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: e instanceof Error ? e.message : "Request failed" },
      ]);
    } finally {
      setSending(false);
    }
  };

  const selectedLabel = records.find((r) => String(r.id) === String(recordId));
  const empty = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-outline-variant/20 bg-surface-container-lowest shadow-[0_8px_40px_-12px_rgba(32,27,20,0.12)]">
      <div className="shrink-0 border-b border-outline-variant/15 bg-surface-container-low/60 px-5 py-4">
        <label
          htmlFor="chat-record-select"
          className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-on-surface-variant"
        >
          Conversation context
        </label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <select
            id="chat-record-select"
            value={recordId}
            onChange={(e) => {
              setRecordId(e.target.value);
              setMessages([]);
            }}
            className="w-full flex-1 rounded-xl border border-outline-variant/35 bg-background px-4 py-3 text-sm font-medium text-primary shadow-inner sm:max-w-xl"
          >
            <option value="">Select a CRM record to begin...</option>
            {records.map((r) => (
              <option key={r.id} value={r.id}>
                {getRecordLabel(r)}
              </option>
            ))}
          </select>
          {selectedLabel ? (
            <span className="text-xs text-on-surface-variant sm:pl-2">
              Asking about <span className="font-semibold text-primary">{getRecordLabel(selectedLabel)}</span>
            </span>
          ) : null}
        </div>
        <p className="mt-2 text-xs text-on-surface-variant/90">
          The assistant reads the saved CRM record (summary, transcript excerpt, scores). Pick a record before sending a
          message.
        </p>
      </div>

      <div className="relative flex min-h-0 flex-1 flex-col bg-background px-5 py-6 md:px-8 md:py-8">
        {empty ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <span className="material-symbols-outlined text-4xl">chat_bubble</span>
            </div>
            {!recordId ? (
              <div>
                <p className="font-headline text-sm font-bold text-primary">Select a record</p>
                <p className="mt-2 max-w-md text-sm text-on-surface-variant">
                  Use the dropdown above to attach this chat to a specific deal or interaction. Then you can ask about
                  risks, next steps, or summaries.
                </p>
              </div>
            ) : (
              <>
                <p className="max-w-lg text-sm text-on-surface-variant">Try one of these to get started:</p>
                <div className="flex max-w-2xl flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      disabled={sending}
                      onClick={() => {
                        setInput(s);
                        send(s);
                      }}
                      className="rounded-full border border-outline-variant/30 bg-surface-container-low px-4 py-2 text-left text-xs font-medium leading-snug text-primary shadow-sm transition-colors hover:border-secondary/40 hover:bg-secondary/5 disabled:opacity-50"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1">
              <div className="flex flex-col gap-4 pb-2">
                {messages.map((m, i) => (
                  <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                    <div
                      className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm md:max-w-[85%] ${
                        m.role === "user"
                          ? "rounded-tr-md bg-[#C5BAAF] text-primary"
                          : "rounded-tl-md bg-primary-container text-white"
                      }`}
                    >
                      {renderMessageText(m.text)}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex items-center gap-2 pl-1 text-[10px] font-bold uppercase tracking-wider text-secondary/70">
                    <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-secondary" />
                    Thinking...
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-outline-variant/20 bg-surface-container-low p-4">
        <div className="mx-auto max-w-4xl">
          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <div className="flex gap-2 rounded-2xl border border-outline-variant/25 bg-background p-2 shadow-inner focus-within:ring-2 focus-within:ring-secondary/20">
            <input
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={recordId ? "Ask about this deal..." : "Select a record above to enable chat"}
              disabled={!recordId || sending}
              className="min-h-[44px] flex-1 border-none bg-transparent px-3 text-sm text-primary placeholder:text-on-surface-variant/50 focus:ring-0 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => send()}
              disabled={sending || !recordId || !input.trim()}
              className="flex shrink-0 items-center justify-center rounded-xl bg-primary px-4 text-on-primary shadow-md transition-opacity disabled:opacity-40"
              aria-label="Send"
            >
              <span className="material-symbols-outlined text-xl">send</span>
            </button>
          </div>
          <p className="mt-2 text-center text-[10px] text-on-surface-variant/80">
            Powered by the Agents API - messages are not stored after refresh
          </p>
        </div>
      </div>
    </div>
  );
}
