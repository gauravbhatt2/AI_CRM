# CRM UI (Vite + React)

SPA for the AI CRM system: upload, records, analytics, chat.

**Setup:** from this directory run `npm install` then `npm run dev`.

**API:** `src/lib/api.js` uses `VITE_API_URL` when set, else `http://127.0.0.1:8000`. See parent **`../README.md`** for backend env and pipeline.

**Production build:** `npm run build` writes to `dist/` (gitignored).
