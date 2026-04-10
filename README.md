# CRM_AI — AI-assisted CRM ingestion

Monorepo with a **FastAPI** backend that ingests transcripts or audio, extracts structured CRM fields with **Groq** (OpenAI-compatible API), maps entities to accounts/contacts/deals, and persists results in **PostgreSQL**. A **Vite + React** dashboard uploads content, shows extraction results, and surfaces analytics.

## Repository layout

| Path | Role |
|------|------|
| `ai-crm-system/` | Python API (`app/`), SQLAlchemy models, ingestion and extraction services |
| `crm-ui/` | React SPA (upload, dashboard, analytics, CRM records table) |

## Prerequisites

- **Python 3.11+** (recommended; use a virtual environment)
- **Node.js 20+** and npm (for the UI)
- **PostgreSQL** (database URL required for ingest + CRM persistence)
- **FFmpeg** on `PATH` (recommended for Whisper with many audio/video formats)
- **Google AI (Gemini) API key** for extraction, speaker labeling, and CRM entity-resolution prompts

## Backend (`ai-crm-system`)

### Setup

```bash
cd ai-crm-system
python -m venv myvenv
# Windows:
myvenv\Scripts\activate
# macOS/Linux:
# source myvenv/bin/activate

pip install -r requirements.txt
```

### Environment

Create `ai-crm-system/.env` (do not commit secrets). Typical variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql://user:pass@localhost:5432/dbname` |
| `GROQ_API_KEY` | API key from [Groq Console](https://console.groq.com/keys) |
| `GROQ_MODEL` | Model id, e.g. `llama-3.3-70b-versatile` (see [Groq models](https://console.groq.com/docs/models)) |
| `WHISPER_MODEL` | Optional; Whisper size: `tiny`, `base`, `small`, etc. (default `base`) |

The app loads `.env` automatically when started from the `ai-crm-system` directory (see `app/core/config.py`).

### Run the API

From `ai-crm-system`:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive docs: `http://127.0.0.1:8000/docs`
- Health: routes under the included `health` router

### Notable API areas

- **Ingestion** — `POST /ingest/transcript`, `POST /ingest/interaction`, `POST /ingest/audio` (Whisper + optional speaker labels + extraction + CRM mapping)
- **CRM / analytics** — under `/api/v1/...` (see `app/main.py` for prefixes)

### Whisper / audio notes

- Transcription uses **local OpenAI Whisper** (`openai-whisper` in `requirements.txt`).
- If Whisper’s top-level `text` is empty but segments exist, the service joins segment text so extraction still receives a transcript string.

## Frontend (`crm-ui`)

### Setup

```bash
cd crm-ui
npm install
```

### Run (development)

```bash
npm run dev
```

Default Vite URL is usually `http://127.0.0.1:5173`. The UI calls the API at `http://127.0.0.1:8000` (see `src/App.jsx`); ensure the backend is running and CORS includes your dev origin (`app/core/config.py` lists common Vite ports).

### Production build

```bash
npm run build
npm run preview   # optional local preview of dist/
```

## End-to-end workflow

1. Start PostgreSQL and set `DATABASE_URL`.
2. Start the FastAPI app with valid `GROQ_*` variables.
3. Start `crm-ui` with `npm run dev`.
4. Use **Upload** to paste text or upload audio; review extracted fields and mapped CRM ids in the UI.

## Troubleshooting

- **`Failed to fetch` in the UI** — API not running, wrong port, or browser blocked; confirm `http://127.0.0.1:8000/docs` loads.
- **503 on ingest** — Missing `GROQ_API_KEY` or `GROQ_MODEL`, or database not configured for routes that require a session.
- **Empty extraction with audio but timestamps present** — Ensure FFmpeg is available; confirm `GROQ_*` works with a short `POST /ingest/transcript` test; check server logs for Groq errors.
- **Whisper slow or low quality** — Try a larger `WHISPER_MODEL` (uses more RAM) or shorter clips.

## License

Add your preferred license here if this repository is public or shared.
