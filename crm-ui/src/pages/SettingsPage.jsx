import React, { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout.jsx";
import GoogleConnect from "../components/GoogleConnect.jsx";
import { API_BASE_URL, api, fetchJson } from "../lib/api.js";

const HS_SYNC_KEY = "ai_crm_hubspot_sync_v1";

export default function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [healthErr, setHealthErr] = useState(null);
  const [checking, setChecking] = useState(false);
  const [cacheCleared, setCacheCleared] = useState(false);

  const pingBackend = useCallback(async () => {
    setChecking(true);
    setHealthErr(null);
    setHealth(null);
    try {
      const data = await fetchJson(api.health);
      setHealth(data);
    } catch (e) {
      setHealthErr(e instanceof Error ? e.message : "Unreachable");
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    pingBackend();
  }, [pingBackend]);

  const clearHubSpotCache = () => {
    try {
      localStorage.removeItem(HS_SYNC_KEY);
      setCacheCleared(true);
      window.setTimeout(() => setCacheCleared(false), 4000);
    } catch {
      setCacheCleared(false);
    }
  };

  return (
    <Layout>
      <div className="py-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Workspace</span>
        <h1 className="mt-1 font-headline text-4xl font-extrabold tracking-tighter text-primary">Settings</h1>
        <p className="mt-2 max-w-2xl text-on-surface-variant">
          Connection checks, integrations, and browser data for this Aura client. Server secrets stay in the FastAPI{" "}
          <code className="rounded bg-surface-container-high px-1.5 py-0.5 font-mono text-xs">.env</code>, not here.
        </p>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Backend API</h2>
          <div className="mt-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-bold uppercase text-on-surface-variant">Base URL (from Vite)</p>
                <p className="mt-2 break-all font-mono text-sm text-primary">{API_BASE_URL}</p>
                <p className="mt-2 text-xs text-on-surface-variant">
                  Set <code className="font-mono">VITE_API_URL</code> before <code className="font-mono">npm run build</code> for production.
                </p>
              </div>
              <button
                type="button"
                onClick={pingBackend}
                disabled={checking}
                className="shrink-0 rounded-full border border-outline-variant/30 bg-background px-4 py-2 text-xs font-bold uppercase tracking-wider text-primary hover:bg-surface-container-high disabled:opacity-50"
              >
                {checking ? "Checking…" : "Test connection"}
              </button>
            </div>
            <div className="mt-4 border-t border-outline-variant/15 pt-4">
              {health && (
                <p className="text-sm text-primary">
                  <span className="font-bold">Status:</span> {health.status ?? "—"}
                  {health.version != null ? (
                    <>
                      {" "}
                      · <span className="font-bold">API version:</span> {health.version}
                    </>
                  ) : null}
                </p>
              )}
              {healthErr && (
                <p className="text-sm text-error" role="alert">
                  {healthErr}
                </p>
              )}
              {!health && !healthErr && !checking && <p className="text-sm text-on-surface-variant">No response yet.</p>}
            </div>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-secondary underline decoration-secondary/40 underline-offset-2 hover:decoration-secondary"
            >
              Open API docs (Swagger)
              <span className="material-symbols-outlined text-sm">open_in_new</span>
            </a>
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Google Workspace</h2>
          <p className="mt-2 max-w-2xl text-sm text-on-surface-variant">
            Connect once to enable AI Gmail drafts, sending, and calendar scheduling from CRM Records. Tokens are stored on the server;
            this bar reflects whether the backend has a valid session.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-sm">
            <GoogleConnect />
            <p className="text-xs text-on-surface-variant">
              Use the same control in the top bar anytime. Re-authorize after password changes or revoked scopes.
            </p>
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Browser data</h2>
          <div className="mt-4 rounded-2xl border border-outline-variant/15 bg-surface-container-low p-6 shadow-sm">
            <p className="text-sm text-on-surface-variant">
              The app caches HubSpot “last synced” hints in <code className="font-mono text-xs">localStorage</code> so buttons can show
              re-sync state. Clearing does not delete CRM rows on the server.
            </p>
            <button
              type="button"
              onClick={clearHubSpotCache}
              className="mt-4 rounded-full bg-primary/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-primary hover:bg-primary/15"
            >
              Clear HubSpot sync cache
            </button>
            {cacheCleared && (
              <p className="mt-3 text-xs font-medium text-emerald-800 dark:text-emerald-200" role="status">
                Cleared. Re-sync state will repopulate after the next HubSpot push.
              </p>
            )}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-headline text-sm font-bold uppercase tracking-widest text-secondary">Server configuration</h2>
          <ul className="mt-4 list-inside list-disc space-y-2 rounded-2xl border border-dashed border-outline-variant/25 bg-background/50 p-6 text-sm text-on-surface-variant">
            <li>
              <strong className="text-primary">Database:</strong> set <code className="font-mono text-xs">DATABASE_URL</code> for PostgreSQL.
            </li>
            <li>
              <strong className="text-primary">LLM:</strong> <code className="font-mono text-xs">GROQ_API_KEY</code> for extraction and agents.
            </li>
            <li>
              <strong className="text-primary">HubSpot:</strong> portal and private app token as documented in your backend env template.
            </li>
            <li>
              <strong className="text-primary">CORS:</strong> allow your UI origin in FastAPI settings so the browser can call the API.
            </li>
          </ul>
        </section>
      </div>
    </Layout>
  );
}
