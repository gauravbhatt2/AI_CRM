import { useEffect, useState } from "react";
import { api, fetchJson } from "../lib/api.js";

export default function EmailComposer({
  contactId,
  dealId,
  defaultEmail = "",
  defaultSubject = "",
  defaultBody = "",
  onClose,
}) {
  const [to, setTo] = useState(defaultEmail);
  const [subject, setSubject] = useState(defaultSubject);
  const [body, setBody] = useState(defaultBody);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (defaultEmail) setTo(defaultEmail);
    if (defaultSubject) setSubject(defaultSubject);
    if (defaultBody) setBody(defaultBody);
  }, [defaultEmail, defaultSubject, defaultBody]);

  const handleSend = async (e) => {
    e.preventDefault();
    setStatus("sending");
    try {
      await fetchJson(api.google.gmailSend, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to,
          subject,
          body,
          contact_id: contactId ?? null,
          deal_id: dealId ?? null,
        }),
      });
      setStatus("success");
    } catch (err) {
      console.error(err);
      setStatus("error");
    }
  };

  return (
    <div className="w-full max-w-lg rounded-2xl border border-outline-variant/20 bg-surface-container-lowest p-6 shadow-xl">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-headline text-lg font-bold text-primary">Send via Gmail</h3>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-on-surface-variant hover:bg-surface-container-high"
            aria-label="Close"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        ) : null}
      </div>
      {status === "success" && (
        <p className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-900">
          Sent and logged to CRM.
        </p>
      )}
      {status === "error" && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-900">
          Send failed. Connect Google first.
        </p>
      )}
      <form onSubmit={handleSend} className="flex flex-col gap-3">
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          To
          <input
            type="email"
            required
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          Subject
          <input
            type="text"
            required
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          Body
          <textarea
            required
            rows={5}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <button
          type="submit"
          disabled={status === "sending"}
          className="mt-2 rounded-full bg-primary px-4 py-2.5 text-xs font-headline font-bold uppercase tracking-widest text-on-primary disabled:opacity-60"
        >
          {status === "sending" ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
}
