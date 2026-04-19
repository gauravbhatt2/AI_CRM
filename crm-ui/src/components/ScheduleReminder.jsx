import { useState } from "react";
import { api, fetchJson } from "../lib/api.js";

export default function ScheduleReminder({ contactId, dealId, defaultEmail = "", onClose }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [attendees, setAttendees] = useState(defaultEmail);
  const [status, setStatus] = useState(null);

  const handleSchedule = async (e) => {
    e.preventDefault();
    setStatus("scheduling");
    try {
      const list = attendees
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean);
      await fetchJson(api.google.calendar, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          start_time: new Date(startTime).toISOString(),
          end_time: new Date(endTime).toISOString(),
          attendees: list,
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
        <h3 className="font-headline text-lg font-bold text-primary">Schedule meeting</h3>
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
          Event created and logged to CRM.
        </p>
      )}
      {status === "error" && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-900">
          Failed. Connect Google first.
        </p>
      )}
      <form onSubmit={handleSchedule} className="flex flex-col gap-3">
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          Title
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
            Start
            <input
              type="datetime-local"
              required
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
            />
          </label>
          <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
            End
            <input
              type="datetime-local"
              required
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
            />
          </label>
        </div>
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          Attendees (comma-separated)
          <input
            type="text"
            value={attendees}
            onChange={(e) => setAttendees(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <label className="text-xs font-bold uppercase tracking-wide text-on-surface-variant">
          Description
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-1 w-full rounded-xl border border-outline-variant/30 bg-background px-3 py-2 text-sm text-primary"
          />
        </label>
        <button
          type="submit"
          disabled={status === "scheduling"}
          className="mt-2 rounded-full bg-secondary px-4 py-2.5 text-xs font-headline font-bold uppercase tracking-widest text-on-secondary disabled:opacity-60"
        >
          {status === "scheduling" ? "Scheduling…" : "Schedule"}
        </button>
      </form>
    </div>
  );
}
