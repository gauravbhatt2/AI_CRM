import { useCallback, useEffect, useRef, useState } from "react";
import { api, fetchJson } from "../lib/api.js";

// Module-level cache shared across every GoogleConnect mount in this tab.
// Avoids the "status called every second" storm caused by React StrictMode
// double-mount + route remounts + focus refetches.
const STATUS_CACHE_TTL_MS = 20_000;
let _statusCache = null; // { at: number, data: { connected: boolean, ... } }
let _inflight = null;

async function fetchGoogleStatus(force = false) {
  const now = Date.now();
  if (!force && _statusCache && now - _statusCache.at < STATUS_CACHE_TTL_MS) {
    return _statusCache.data;
  }
  if (_inflight) return _inflight;
  _inflight = (async () => {
    try {
      const data = await fetchJson(api.google.status);
      _statusCache = { at: Date.now(), data };
      return data;
    } catch (e) {
      const data = { connected: false };
      _statusCache = { at: Date.now(), data };
      throw e;
    } finally {
      _inflight = null;
    }
  })();
  return _inflight;
}

/** Top-bar pill: red = disconnected, green = connected. */
export default function GoogleConnect() {
  const [isConnected, setIsConnected] = useState(
    Boolean(_statusCache?.data?.connected),
  );
  const [isLoading, setIsLoading] = useState(!_statusCache);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const checkStatus = useCallback(async (force = false) => {
    try {
      const data = await fetchGoogleStatus(force);
      setIsConnected(Boolean(data?.connected));
    } catch {
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchGoogleStatus(false)
      .then((data) => {
        if (cancelled) return;
        setIsConnected(Boolean(data?.connected));
      })
      .catch(() => {
        if (!cancelled) setIsConnected(false);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onFocus = () => {
      void checkStatus(false);
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [checkStatus]);

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const connect = async () => {
    try {
      const data = await fetchJson(api.google.auth);
      if (data?.url) window.location.href = data.url;
      else alert("Could not start Google sign-in.");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Google sign-in failed.");
    }
  };

  const signOut = async () => {
    setOpen(false);
    try {
      await fetch(api.google.signout, { method: "POST", mode: "cors" });
      _statusCache = null;
      setIsConnected(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Sign out failed.");
    } finally {
      await checkStatus(true);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => {
          if (isLoading) return;
          if (!isConnected) connect();
          else setOpen((v) => !v);
        }}
        className={
          "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-headline font-bold uppercase tracking-wider transition-all " +
          (isLoading
            ? "border-outline-variant/50 bg-surface-container-high text-on-surface-variant"
            : isConnected
              ? "border-emerald-300/80 bg-emerald-50 text-emerald-900 shadow-sm hover:bg-emerald-100"
              : "border-red-300/80 bg-red-50 text-red-900 shadow-sm hover:bg-red-100")
        }
        aria-expanded={isConnected ? open : undefined}
      >
        <span
          className={
            "h-2 w-2 shrink-0 rounded-full " +
            (isLoading ? "animate-pulse bg-slate-400" : isConnected ? "bg-emerald-500" : "bg-red-500")
          }
          aria-hidden
        />
        {isLoading ? "Google…" : isConnected ? "Google" : "Connect Google"}
        {isConnected && !isLoading ? (
          <span className="text-[10px] opacity-70" aria-hidden>
            ▾
          </span>
        ) : null}
      </button>

      {isConnected && open && !isLoading && (
        <div
          className="absolute right-0 top-[calc(100%+8px)] z-[80] min-w-[200px] rounded-xl border border-outline-variant/20 bg-surface-container-lowest py-1 shadow-xl"
          role="menu"
        >
          <button
            type="button"
            role="menuitem"
            className="block w-full px-4 py-2.5 text-left text-xs font-semibold text-primary hover:bg-surface-container-high"
            onClick={() => {
              setOpen(false);
              checkStatus(true);
            }}
          >
            Refresh status
          </button>
          <button
            type="button"
            role="menuitem"
            className="block w-full px-4 py-2.5 text-left text-xs font-semibold text-primary hover:bg-surface-container-high"
            onClick={() => {
              setOpen(false);
              connect();
            }}
          >
            Re-authorize
          </button>
          <button
            type="button"
            role="menuitem"
            className="mt-1 block w-full border-t border-outline-variant/20 px-4 py-2.5 text-left text-xs font-bold text-error hover:bg-error-container/30"
            onClick={signOut}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
