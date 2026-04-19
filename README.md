# AI CRM — AI-assisted CRM ingestion

Monorepo: **FastAPI** backend (PostgreSQL, Groq LLM, OpenRouter, Google OAuth) and **Vite + React** dashboard. Optimised for low-latency ingestion — no torch, no pyannote, no 1.5 GB model downloads on first run.

| Path | Role |
|------|------|
| `ai-crm-system/` | Python API: ingestion, two-phase extraction (facts → evaluation), CRM mapping, HubSpot sync, agents, Google Workspace |
| `crm-ui/` | React SPA (React Router): upload, records, analytics, chat, settings |
| `ai-crm-system/docs/` | **BRD_AI_CRM.md** (business), **PRD_AI_CRM.md** (product / API / data model) |

## Prerequisites

- **Python 3.11+** (venv recommended)
- **Node.js 20+** and npm
- **PostgreSQL** (`DATABASE_URL`)
- **FFmpeg** on `PATH` (required by faster-whisper to decode non-WAV audio)
- **Groq API key** — required for ingestion (extraction + evaluation)
- **Optional:** OpenRouter API key — deal chat; falls back to Groq if unset
- **Optional:** Google OAuth client id/secret/redirect — Gmail/Calendar under `/api/v1/google/`

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
| `GROQ_LABEL_SPEAKERS` | Default **`false`** (heuristic labeler is instant; enable only when LLM speaker labels matter) |
| `WHISPER_MODEL` | Default **`base`**. Options: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `WHISPER_LANGUAGE` | Default `en` — skips language auto-detection |
| `WHISPER_FAST_DECODE` | Default `true` (beam_size=1, much faster) |
| `WHISPER_BEAM_SIZE` | Only read when `WHISPER_FAST_DECODE=false` |
| `WHISPER_VAD` | Default `true` — Voice Activity Detection prunes silence |
| `WHISPER_DEVICE` | `auto` (default), `cpu`, or `cuda` |
| `WHISPER_COMPUTE_TYPE` | Empty = auto (`int8` on CPU, `float16` on CUDA). Can override with `int8_float16`, `float32`, etc. |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | Optional; deal chat |
| `HUBSPOT_API_KEY` | Optional; HubSpot deal/contact/company sync |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Optional; Google OAuth |

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- OpenAPI: `http://127.0.0.1:8000/docs`

### Pipeline

1. **Audio:** `faster-whisper` transcribes the file (CTranslate2 backend, INT8 on CPU by default) and emits timestamped segments. Speaker labels are applied by a fast rule-based labeler; set `GROQ_LABEL_SPEAKERS=true` to use Groq for higher-quality labels at the cost of one extra roundtrip.
2. **Text/audio:** transcript → **factual extraction** (single Groq JSON call, long inputs truncated with middle omitted) → **merge with heuristic hints** → **evaluation** (Groq JSON from merged facts) → deterministic refiners → AI intelligence → CRM mapping → persist → audit.
3. **Agents:** `POST /api/v1/agents/chat` (OpenRouter preferred, Groq fallback), `POST /api/v1/agents/next-action/{id}`, `POST /api/v1/agents/followup/{id}`.
4. **Google (optional):** OAuth + on-demand Gmail/Calendar actions — no automatic inbox sync.

### Performance notes

- Responses are **gzip-compressed** (1 KB threshold) by the FastAPI middleware.
- `/api/v1/google/status/` is **cached for ~20 s** in-process (and in the browser) so the TopBar pill cannot hammer Google on every remount / focus event.
- Default Whisper stack (`base` model + `int8` + `beam=1` + VAD) typically transcribes 1 minute of audio in **~3–6 seconds on CPU**; large-v3 needs 5–10× more time.
- No torch / no pyannote / no CUDA runtime required for CPU deployment.

### Speed vs accuracy — what to tune

The system ships with `WHISPER_PROFILE=balanced` by default. Flip the single env
variable to `fast` or `quality` and every related flag is set for you; any explicit
`WHISPER_MODEL`/`WHISPER_BEAM_SIZE`/`WHISPER_FAST_DECODE`/`GROQ_LABEL_SPEAKERS`
env var overrides the profile preset.

| Profile | Whisper model | Beam | Speaker labels (Groq) | Two-pass extraction | Approx. WER | Relative ingest speed |
|---------|---------------|------|-----------------------|---------------------|-------------|-----------------------|
| `fast` | `base` | 1 | off | off | ~6% | 1× (baseline) |
| `balanced` **(default)** | `small` | 5 | on | on | ~4% | 0.5× |
| `quality` | `large-v3` | 5 | on | on | ~3% | 0.1–0.15× |

Accuracy knobs beyond the profile:

| Knob | Default | What it does |
|------|---------|--------------|
| `EXTRACTION_REQUIRE_EVIDENCE` | `true` | Blank any LLM-extracted field whose value is not a literal substring of the transcript. Kills hallucinations. |
| `EXTRACTION_SELF_CONSISTENCY` | `true` (balanced/quality) | Run Groq facts extraction twice (`t=0.0` and `t=0.2`) and blank fields where the two passes disagree. |
| `EXTRACTION_USE_SPEAKER_LABELS` | `true` | Feed the speaker-labeled transcript (`[00:12] Customer: …`) into Groq so Sales vs Customer attribution is unambiguous. Audio path only. |
| `ACCOUNT_FUZZY_MATCH_THRESHOLD` | `88` | Token-set ratio (0–100) below which a new company name is treated as a new Account. Prevents "Acme Corp" / "Acme Inc." duplicates. |
| `EXTRACTION_CACHE_SIZE` | `64` | In-process SHA256 cache of identical transcripts — re-ingests return the cached extraction with zero Groq/Whisper cost. |
| `WHISPER_VAD_MIN_SILENCE_MS` | `500` | Tighter VAD threshold — drops more silent noise before decoding. |
| `WHISPER_LOG_PROB_THRESHOLD` | `-1.0` | Reject Whisper segments with avg log-probability below this. Set to `-0.5` for stricter filtering on noisy audio. |

Three common `.env` profiles:

```bash
# FAST - dashboards, internal demos, low-latency ingestion
WHISPER_PROFILE=fast

# BALANCED (default) - production CRM, speaker-aware extraction, evidence grounding
WHISPER_PROFILE=balanced

# QUALITY - noisy audio, multi-speaker calls, legal/compliance
WHISPER_PROFILE=quality
```

Non-audio extraction accuracy (budget normalization, Indian units like `lakh`/`crore`,
CRM dedup, evidence grounding, speaker-aware prompts) applies to **every** profile
and every ingest channel (audio, transcript, email, meeting, SMS, CRM update).

## Frontend (`crm-ui`)

```bash
cd crm-ui
npm install
npm run dev
```

Default: `http://127.0.0.1:5173`. Set **`VITE_API_URL`** (e.g. in `.env`) to point at the backend if it is not `http://127.0.0.1:8000`.

```bash
npm run build    # output in dist/ (listed in .gitignore)
```

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `503` on ingest | `GROQ_API_KEY`, `GROQ_MODEL`, DB reachable |
| `Failed to fetch` in UI | Backend running, port, CORS, `VITE_API_URL` |
| Whisper / FFmpeg | Install FFmpeg and restart shell — `ffmpeg -version` |
| Slow first audio upload | The `base` model downloads once (~140 MB). Subsequent calls are cached in the process. |
| Chat always "Not available" | Set `OPENROUTER_API_KEY` or rely on Groq fallback |
| Google features disabled | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` in backend `.env` |

## Repo hygiene

- **`crm-ui/dist/`** — build artifact; gitignored.
- **`node_modules/`**, **`.env`** — not committed.
- Business / product requirements live in **`ai-crm-system/docs/BRD_AI_CRM.md`** and **`ai-crm-system/docs/PRD_AI_CRM.md`**.

## License

Add your license if you distribute this repository.
