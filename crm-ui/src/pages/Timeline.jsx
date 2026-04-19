import React, { useEffect, useState } from "react";
import { motion as Motion } from "framer-motion";
import { api, fetchJson } from "../lib/api.js";

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

const Timeline = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const data = await fetchJson(api.timeline);
        const list = Array.isArray(data?.items) ? data.items : [];
        if (!c) setItems(list);
      } catch (e) {
        if (!c) setErr(e instanceof Error ? e.message : "Failed to load timeline");
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl py-10">
      <div className="mb-12 flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h2 className="mb-2 font-headline text-4xl font-extrabold tracking-tighter text-primary">Interaction timeline</h2>
          <p className="max-w-lg font-body text-sm leading-relaxed text-on-surface-variant">
            Chronological view from the CRM interactions API.
          </p>
        </div>
      </div>

      {loading && <p className="text-on-surface-variant">Loading…</p>}
      {err && (
        <p className="text-error" role="alert">
          {err}
        </p>
      )}

      {!loading && !err && (
        <div className="relative space-y-6">
          <div className="absolute bottom-0 left-[31px] top-0 w-[2px] bg-gradient-to-b from-secondary/30 via-outline-variant/20 to-transparent" />
          {items.length === 0 ? (
            <p className="text-on-surface-variant">No timeline entries yet.</p>
          ) : (
            items.map((ev, idx) => (
              <Motion.div
                key={ev.id ?? idx}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className="relative pl-16"
              >
                <div className="absolute left-0 top-2 flex h-16 w-16 items-center justify-center">
                  <div className="z-10 h-4 w-4 rounded-full bg-secondary ring-4 ring-secondary/20" />
                </div>
                <div className="rounded-xl border-l-4 border-secondary bg-surface-container-low p-6 shadow-md">
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-on-surface-variant">
                    <span className="rounded bg-surface-container-highest px-2 py-0.5 font-bold uppercase text-primary">
                      {ev.source_type || "interaction"}
                    </span>
                    <span>{formatWhen(ev.created_at)}</span>
                    {ev.intent ? (
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                        intent {ev.intent}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="font-headline text-lg font-bold text-primary">Record #{ev.id}</h3>
                  {ev.content_excerpt ? (
                    <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">{ev.content_excerpt}</p>
                  ) : null}
                </div>
              </Motion.div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default Timeline;
