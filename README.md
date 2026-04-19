# CRM_AI — AI-assisted CRM ingestion

Monorepo: **FastAPI** backend (PostgreSQL, Groq LLM, optional pyannote + OpenRouter + Google OAuth) and **Vite + React** dashboard.

| Path | Role |
|------|------|
| `ai-crm-system/` | Python API: ingestion, two-phase extraction (single-pass facts → evaluation), CRM mapping, HubSpot sync, agents, optional Google Workspace |
| `crm-ui/` | React SPA (React Router): upload, records, analytics, chat, settings |
| `ai-crm-system/docs/` | **BRD_AI_CRM.md** (business), **PRD_AI_CRM.md** (product / API / data model) |

## Prerequisites

- **Python 3.11+** (venv recommended)
- **Node.js 20+** and npm
- **PostgreSQL** (`DATABASE_URL`)
- **FFmpeg** on `PATH` (recommended for Whisper decoding many formats)
- **Groq API key** — extraction & evaluation (required for ingest)
- **Optional:** Hugging Face token — pyannote speaker diarization (accept model license on HF)
- **Optional:** OpenRouter API key — deal chat (Gemma); falls back to Groq if unset/failing
- **Optional:** Google OAuth client id/secret + redirect — Gmail/Calendar features under `/api/v1/google/` when configured

## Backend (`ai-crm-system`)

```bash
cd ai-crm-system
python -m venv myvenv
myvenv\Scripts\activate   # Windows
# source myvenv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create **`ai-crm-system/.env`** (never commit secrets):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL URL |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) |
| `GROQ_MODEL` | e.g. `llama-3.3-70b-versatile` |
| `WHISPER_MODEL` | Default **`turbo`** (large-v3-turbo; faster than `large` / `large-v3` for English). Alternatives: `tiny`, `base`, `small`, `medium`, `large`, `large-v3` |
| `WHISPER_LANGUAGE` | Default `en` — skips Whisper auto language detection (English-only) |
| `HUGGINGFACE_TOKEN` | Optional; enables **pyannote** diarization (`PYANNOTE_ENABLED=true`) |
| `OPENROUTER_API_KEY` | Optional; **deal chat** via OpenRouter |
| `OPENROUTER_MODEL` | e.g. `google/gemma-3-12b-it:free` |
| `GROQ_LABEL_SPEAKERS` | Extra Groq call for labels if pyannote did not run (default `true`) |
| `HUBSPOT_API_KEY` | Optional; HubSpot deal/contact/company sync |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Optional; Google OAuth for Gmail + Calendar routes |

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- OpenAPI: `http://127.0.0.1:8000/docs`

### Pipeline (conceptual)

1. **Audio:** Whisper transcription → optional **pyannote** diarization (Speaker A/B) merged to segments → optional Groq/heuristic speaker labels if pyannote off.
2. **Text/audio:** Transcript → **factual extraction** (Groq, single call; very long text is truncated with middle omitted) → **merge with heuristic hints** → **evaluation** (Groq, from merged facts JSON) → refiners → AI intelligence → CRM mapping → persist → audit.
3. **Agents:** `POST /api/v1/agents/chat` — OpenRouter when configured (structured CRM fields only, no raw transcript); Groq fallback. Also **next-action** and **follow-up** endpoints.
4. **Google (optional):** OAuth + on-demand Gmail/Calendar actions — not automatic full inbox sync.

## Frontend (`crm-ui`)

```bash
cd crm-ui
npm install
npm run dev
```

Default: `http://127.0.0.1:5173`. Set **`VITE_API_URL`** (e.g. in `.env`) to point at the backend if it is not `http://127.0.0.1:8000`. See `src/lib/api.js` and `app/core/config.py` for CORS.

```bash
npm run build    # output in dist/ (listed in .gitignore — do not commit)
```

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `503` on ingest | `GROQ_API_KEY`, `GROQ_MODEL`, DB |
| `Failed to fetch` in UI | API running, port, CORS, `VITE_API_URL` |
| Whisper / FFmpeg | Install FFmpeg; restart shell |
| pyannote errors | `pip install` includes torch/pyannote; HF token; model license; or set `PYANNOTE_ENABLED=false` |
| Chat always “Not available” | Set `OPENROUTER_API_KEY` or rely on Groq fallback |
| Google features disabled | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` in backend `.env` |

## Repo hygiene

- **`crm-ui/dist/`** — build artifact; gitignored. Regenerate with `npm run build`.
- **`node_modules/`**, **`.env`** — not committed.
- Requirements and behavior are defined in **`ai-crm-system/docs/BRD_AI_CRM.md`** and **`ai-crm-system/docs/PRD_AI_CRM.md`** only.

## License

Add your license if you distribute this repository.
