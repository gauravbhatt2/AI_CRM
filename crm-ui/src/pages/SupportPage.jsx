import React from "react";
import Layout from "../components/Layout.jsx";
import { API_BASE_URL } from "../lib/api.js";

const FAQ = [
  {
    q: "The UI says the API is unreachable",
    a: "Confirm the FastAPI process is running and that VITE_API_URL (or the default http://127.0.0.1:8000) matches where the API listens. Check firewalls and VPN. Open Settings → Test connection.",
  },
  {
    q: "Google shows disconnected or Gmail fails",
    a: "Complete OAuth from Settings or the top bar. Ensure Google Cloud OAuth client allows your app URL and the backend redirect URI. Server must have valid client id/secret and token storage (see backend .env).",
  },
  {
    q: "Upload or transcript ingestion errors",
    a: "Verify GROQ_API_KEY and DATABASE_URL on the server. For audio, FFmpeg may be required. Read the API error body in the browser network tab or server logs.",
  },
  {
    q: "HubSpot sync fails",
    a: "Check HubSpot credentials and deal pipeline permissions on the backend. CRM rows must exist before push; edit fields in CRM Records preview if needed.",
  },
  {
    q: "CORS errors in the browser console",
    a: "The FastAPI app must list your UI origin in CORS allowed origins. For local dev, http://localhost:5173 (Vite) is commonly added.",
  },
];

export default function SupportPage() {
  const docsUrl = `${API_BASE_URL}/docs`;
  const redocUrl = `${API_BASE_URL}/redoc`;

  return (
    <Layout>
      <div className="py-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Help</span>
        <h1 className="mt-1 font-headline text-4xl font-extrabold tracking-tighter text-primary">Support</h1>
        <p className="mt-2 max-w-2xl text-on-surface-variant">
          Quick fixes for this PoC, links to API documentation, and who to contact for credentials and infrastructure.
        </p>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Resources</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <a
              href={docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low p-5 shadow-sm transition-colors hover:border-secondary/30 hover:bg-surface-container-high/80"
            >
              <div>
                <p className="font-headline text-sm font-bold text-primary">Swagger UI</p>
                <p className="mt-1 text-xs text-on-surface-variant">Try endpoints and inspect request bodies.</p>
              </div>
              <span className="material-symbols-outlined text-secondary">menu_book</span>
            </a>
            <a
              href={redocUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low p-5 shadow-sm transition-colors hover:border-secondary/30 hover:bg-surface-container-high/80"
            >
              <div>
                <p className="font-headline text-sm font-bold text-primary">ReDoc</p>
                <p className="mt-1 text-xs text-on-surface-variant">Readable API reference.</p>
              </div>
              <span className="material-symbols-outlined text-secondary">article</span>
            </a>
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Common issues</h2>
          <div className="mt-4 space-y-3">
            {FAQ.map((item) => (
              <details
                key={item.q}
                className="group rounded-xl border border-outline-variant/15 bg-surface-container-low/60 px-5 py-3 open:bg-surface-container-low open:shadow-sm"
              >
                <summary className="cursor-pointer list-none font-headline text-sm font-bold text-primary marker:content-none [&::-webkit-details-marker]:hidden">
                  <span className="flex items-center justify-between gap-2">
                    {item.q}
                    <span className="material-symbols-outlined text-on-surface-variant transition-transform group-open:rotate-180">
                      expand_more
                    </span>
                  </span>
                </summary>
                <p className="mt-3 border-t border-outline-variant/10 pt-3 text-sm leading-relaxed text-on-surface-variant">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Diagnostics (copy)</h2>
          <div className="mt-4 rounded-2xl border border-outline-variant/15 bg-[#1a1c1e] p-4 font-mono text-xs leading-relaxed text-[#e8eaed]">
            <p>API base: {API_BASE_URL}</p>
            <p className="mt-2 opacity-80">User agent: {typeof navigator !== "undefined" ? navigator.userAgent : "—"}</p>
            <p className="mt-3 text-[10px] uppercase tracking-wider opacity-50">Include this block when reporting UI bugs.</p>
          </div>
        </section>

        <section className="mt-10 rounded-2xl border border-secondary/20 bg-secondary/5 p-6">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Need more help?</h2>
          <p className="mt-2 text-sm text-on-surface-variant">
            For API keys, database accounts, OAuth consent screens, and deployment access, contact your{" "}
            <strong className="text-primary">team administrator</strong> or platform owner. This interface does not store or rotate secrets.
          </p>
        </section>
      </div>
    </Layout>
  );
}
