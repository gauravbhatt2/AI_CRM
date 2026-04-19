import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { motion as Motion } from "framer-motion";
import GoogleConnect from "./GoogleConnect.jsx";

const HIDE_SEARCH_PATHS = new Set(["/upload", "/settings", "/support"]);

const TopBar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const hideSearch = HIDE_SEARCH_PATHS.has(location.pathname);
  const isRecords = location.pathname === "/records";
  const qFromUrl = searchParams.get("q") ?? "";
  const [pending, setPending] = useState("");

  useEffect(() => {
    if (isRecords) setPending(qFromUrl);
  }, [isRecords, qFromUrl]);

  const inputValue = isRecords ? qFromUrl : pending;

  return (
    <header className="fixed top-0 right-0 left-64 z-40 flex h-20 items-center justify-between bg-background/80 px-8 backdrop-blur-xl">
      <div className="flex flex-1 items-center">
        {!hideSearch && (
          <div className="relative flex w-full max-w-md items-center rounded-full bg-surface-container-high px-4 py-2 transition-colors focus-within:bg-surface-container-highest md:max-w-lg">
            <span className="material-symbols-outlined mr-2 text-on-surface-variant">search</span>
            <input
              className="w-full border-none bg-transparent text-sm font-medium text-on-surface shadow-none outline-none ring-0 placeholder:text-on-surface-variant/50 focus:border-transparent focus:outline-none focus:ring-0 focus-visible:outline-none [&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-decoration]:appearance-none"
              placeholder="Search CRM records by id, company, summary…"
              type="search"
              value={inputValue}
              onChange={(e) => {
                const v = e.target.value;
                if (isRecords) {
                  if (v.trim()) setSearchParams({ q: v }, { replace: true });
                  else setSearchParams({}, { replace: true });
                } else {
                  setPending(v);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (!isRecords) {
                    const t = pending.trim();
                    navigate(t ? `/records?q=${encodeURIComponent(t)}` : "/records");
                  }
                }
              }}
              aria-label="Search CRM records"
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <GoogleConnect />

        <div className="flex items-center gap-2 border-l border-outline-variant/20 pl-4">
          <Motion.button
            whileHover={{ backgroundColor: "rgba(0,0,0,0.05)" }}
            type="button"
            className="relative rounded-full p-2 transition-colors"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined text-primary">notifications</span>
          </Motion.button>
        </div>

        <div className="flex items-center gap-3 pl-2">
          <div className="text-right">
            <p className="font-headline text-sm font-bold text-primary">AI CRM</p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-on-surface-variant">Operator</p>
          </div>
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-surface-container-highest bg-surface-container-high font-headline text-sm font-bold text-primary shadow-sm"
            aria-hidden
          >
            AI
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
