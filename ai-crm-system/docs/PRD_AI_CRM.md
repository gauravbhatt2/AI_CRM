# Product Requirements Document (PRD)

## AI-Assisted CRM Ingestion, Intelligence & HubSpot Sync

**Version:** 2.0
**Last Updated:** April 15, 2026
**Companion BRD:** `BRD_AI_CRM.md`
**Product:** AI CRM System (FastAPI + React + PostgreSQL + Groq LLM)

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Personas & User Roles](#2-personas--user-roles)
3. [User Journeys](#3-user-journeys)
4. [System Architecture](#4-system-architecture)
5. [Functional Requirements — Ingestion](#5-functional-requirements--ingestion)
6. [Functional Requirements — Extraction](#6-functional-requirements--extraction)
7. [Functional Requirements — AI Intelligence Layer](#7-functional-requirements--ai-intelligence-layer)
8. [Functional Requirements — CRM Mapping](#8-functional-requirements--crm-mapping)
9. [Functional Requirements — HubSpot Sync](#9-functional-requirements--hubspot-sync)
10. [Functional Requirements — Analytics & Dashboard](#10-functional-requirements--analytics--dashboard)
11. [Functional Requirements — UI/UX](#11-functional-requirements--uiux)
12. [API Reference](#12-api-reference)
13. [Data Model](#13-data-model)
14. [Non-Functional Requirements](#14-non-functional-requirements)
15. [Configuration & Environment](#15-configuration--environment)
16. [Acceptance Criteria](#16-acceptance-criteria)
17. [Known Limitations & Backlog](#17-known-limitations--backlog)
18. [Out of Scope](#18-out-of-scope)
19. [File Structure Reference](#19-file-structure-reference)
20. [Document History](#20-document-history)

---

## 1. Product Overview

The AI CRM System is a full-stack application that automates the conversion of unstructured conversations into structured, AI-enriched CRM records. Built with **FastAPI** (backend), **React + Vite** (frontend), **PostgreSQL** (persistence), **Groq LLM** (AI extraction and intelligence), and **local Whisper** (audio transcription), it delivers:

- **Multi-channel ingestion** — audio files, transcripts, emails, meeting notes, SMS
- **17-field structured extraction** — budget, intent, timeline, product, competitors, stakeholders, and 11 more CRM-ready fields
- **AI Intelligence Layer** — automatic classification, deal scoring, risk detection, summarization, next action suggestions, and tagging for every record
- **HubSpot synchronization** — one-click push of deals, contacts, companies, and notes with proper field mapping and entity associations
- **Modern analytics dashboard** — intent distribution, risk analysis, deal scoring, revenue metrics, and interaction timeline

---

## 2. Personas & User Roles

| Persona | Goals | Primary Actions |
|---------|-------|----------------|
| **Sales Rep / Account Executive** | Get deals and notes populated from calls without manual typing; review AI suggestions | Upload audio/text → review extracted data → sync to HubSpot |
| **Sales Manager** | Monitor pipeline quality; identify at-risk deals; coach reps | Review AI intelligence dashboard; filter by risk/intent; track deal scores |
| **RevOps User** | Push clean, consistent fields to HubSpot; verify sync state; maintain CRM hygiene | Configure HubSpot mapping; verify field quality; re-sync after corrections |
| **Customer Success Manager** | Understand customer context; track interaction history across channels | Browse CRM records timeline; review pain points and stakeholder mapping |
| **Developer / IT Admin** | Configure environment; manage integrations; extend the system | Set up `.env` variables; manage API keys; deploy backend and frontend |

---

## 3. User Journeys

### 3.1 Audio Ingestion Journey

```
User uploads audio file (.mp3, .wav, .m4a, etc.)
    │
    ▼
System transcribes via local Whisper (with optional speaker diarization)
    │
    ▼
LLM extracts 17 structured CRM fields from transcript
    │
    ▼
AI Intelligence Layer enriches: classification, score, risk, summary, next action, tags
    │
    ▼
CRM mapping resolves to existing Account/Contact/Deal (or creates new)
    │
    ▼
Record persisted to PostgreSQL with all fields + audit log entry
    │
    ▼
UI displays: extracted fields, AI insights, transcript segments with timestamps
    │
    ▼
User reviews and clicks "Push to HubSpot" → deal created with all mapped properties
```

### 3.2 Text Ingestion Journey

```
User pastes transcript or sends POST request (with source_type: call/email/meeting/sms)
    │
    ▼
Extraction → AI Intelligence → CRM Mapping → Persist → Display
    │
    ▼
Same enrichment and sync flow as audio (minus transcription step)
```

### 3.3 Interaction Webhook Journey

```
External system sends POST /ingest/interaction (email, meeting notes, SMS, CRM update)
    │
    ▼
Same pipeline with source_type and metadata preserved
    │
    ▼
Record appears in timeline with channel badge
```

### 3.4 HubSpot Sync Journey

```
User clicks "Push to HubSpot" on a CRM record
    │
    ▼
System resolves HubSpot pipeline and stage (API lookup or env override)
    │
    ▼
Creates deal with 17+ mapped properties (budget as amount, intent, timeline, product, etc.)
    │
    ▼
Searches for existing contact (by email/phone) → creates if not found
    │
    ▼
Searches for existing company (by mentioned_company) → creates if not found
    │
    ▼
Creates associations: Deal ↔ Contact, Deal ↔ Company
    │
    ▼
Creates engagement note with full transcript content
    │
    ▼
Returns HubSpot IDs and portal URLs → stored in localStorage for deep links
```

### 3.5 Analytics & Intelligence Journey

```
User navigates to AI Intelligence dashboard
    │
    ▼
System aggregates: total records, avg deal score, high-risk count, sales interaction count
    │
    ▼
Displays: Interaction type pie chart, Risk distribution pie chart
    │
    ▼
Shows intelligence table: ID, Intent (badge), Deal Score (progress bar), Risk (indicator), Next Action, Tags
    │
    ▼
User clicks through to individual records for detailed view
```

---

## 4. System Architecture

### 4.1 Backend Architecture

```
app/
├── main.py                      # FastAPI app factory, CORS, router registration, lifespan
├── core/
│   └── config.py                # Settings class — all env variables and defaults
├── api/
│   ├── deps.py                  # get_db() dependency injection
│   └── routes/
│       ├── health.py            # GET /health — liveness check
│       ├── ingestion.py         # POST /ingest/transcript, /ingest/audio, /ingest/interaction
│       ├── extraction.py        # GET /api/v1/extraction/preview
│       ├── crm.py               # GET/DELETE /api/v1/crm/records, POST /api/v1/crm/map
│       ├── analytics.py         # GET /api/v1/analytics/revenue, /insights, /ai-intelligence
│       ├── interactions.py      # GET /api/v1/interactions/timeline
│       └── hubspot.py           # POST /api/v1/hubspot/push/{record_id}
├── db/
│   ├── database.py              # Engine init, table creation, idempotent schema migrations
│   ├── models.py                # SQLAlchemy ORM: Account, Contact, Deal, CrmRecord, AuditLog
│   ├── crm_record_repository.py # CRUD for CrmRecord
│   └── audit_repository.py      # Append-only audit logging
├── models/
│   ├── ingestion.py             # Pydantic: request/response models, ExtractedEntities
│   ├── crm.py                   # Pydantic: CRMMapRequest/Response
│   ├── extraction.py            # Pydantic: extraction preview models
│   └── health.py                # Pydantic: health response
├── services/
│   ├── extraction_service.py    # Extraction prompt template (17-field), prompt builder
│   ├── groq_extraction.py       # Groq LLM execution, JSON parsing, normalization, heuristic merge
│   ├── groq_llm.py              # OpenAI-compatible Groq client
│   ├── groq_mapping.py          # LLM-assisted CRM entity resolution
│   ├── groq_speakers.py         # Speaker diarization for Whisper segments
│   ├── ai_intelligence.py       # AI Intelligence Layer — 9 functions + batch runner
│   ├── ingestion_pipeline.py    # Orchestrator: extract → AI intel → map → persist → audit
│   ├── mapping_service.py       # CRM entity resolution (LLM + rules)
│   ├── transcription_service.py # Local Whisper transcription
│   ├── hubspot_client.py        # Low-level HubSpot REST operations
│   └── hubspot_service.py       # High-level HubSpot sync orchestration
├── utils/
│   ├── budget.py                # parse_budget_to_int — consistent budget parsing
│   ├── groq_retry.py            # groq_chat_with_retry — rate limit retry with backoff
│   ├── heuristic_extraction.py  # Rule-based extraction fallback + merge logic
│   ├── extraction_refine.py     # Post-LLM refinement: timeline hints, product cleanup
│   └── hubspot_product.py       # Product string cleaning for HubSpot
└── ingestion/
    └── receiver.py              # Transcript acceptance, job ID generation
```

### 4.2 Frontend Architecture

```
crm-ui/src/
├── main.jsx          # React root mount
├── App.jsx           # Single-file app (~2000 lines):
│                     #   - Helper components (IntentBadge, RiskIndicator, DealScoreBar, Spinner, EmptyState)
│                     #   - Section navigation (sidebar)
│                     #   - Audio/text ingestion with loading states
│                     #   - CRM record list with search, filter, expand
│                     #   - AI Intelligence dashboard (KPIs, pie charts, table)
│                     #   - Revenue analytics (bar charts)
│                     #   - Interaction timeline
│                     #   - HubSpot sync per record
├── crm-app.css       # Full design system: CSS variables, components, animations, responsive
├── index.css         # Base styles
└── App.css           # Legacy styles
```

### 4.3 Pipeline Flow (Internal)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    run_transcript_pipeline()                          │
│                                                                      │
│  1. receiver.accept_transcript()         → job_id, context           │
│  2. extract_entities(transcript)         → 17 structured fields      │
│     └─ build_extraction_prompt()         → strict JSON prompt        │
│     └─ execute_groq_json_extraction()    → LLM call + parse          │
│        └─ _run_groq_extraction_attempt() → JSON mode, then fallback  │
│        └─ heuristic_extract_entities()   → rule-based backup         │
│        └─ merge_extraction_prefer_llm()  → LLM wins, heuristic fills │
│        └─ refine_product_core_field()    → product cleanup           │
│        └─ refine_timeline_core_field()   → timeline cleanup          │
│  3. map_entities_to_crm()                → account/contact/deal IDs  │
│  4. run_ai_intelligence()                → classification, score,    │
│     │                                      risk, summary, next       │
│     │                                      action, tags              │
│     ├─ normalize_data()                                              │
│     ├─ classify_interaction()                                        │
│     ├─ score_deal()                                                  │
│     ├─ detect_risk()                                                 │
│     ├─ generate_summary()                                            │
│     ├─ auto_tag()                                                    │
│     └─ generate_next_action()                                        │
│  5. create_crm_record()                  → PostgreSQL insert         │
│  6. log_audit_event()                    → append-only audit         │
│  7. Return TranscriptIngestResponse                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Functional Requirements — Ingestion

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| ING-1 | Accept audio uploads (multipart) and produce text transcript via local Whisper | Must | Done |
| ING-2 | Accept plain text / transcript payloads via POST body | Must | Done |
| ING-3 | Accept interaction webhooks with source_type (`call`, `email`, `meeting`, `sms`, `crm_update`) | Must | Done |
| ING-4 | Persist `source_type`, `external_interaction_id`, and timestamps on every record | Must | Done |
| ING-5 | Store participant metadata (from explicit list and metadata.participants) | Should | Done |
| ING-6 | Support idempotency via `external_id` field (deduplication tracking) | Should | Done |
| ING-7 | Structured transcript with timed segments and optional speaker labels | Should | Done |
| ING-8 | Fail gracefully with clear errors if DB URL missing or FFmpeg unavailable | Must | Done |
| ING-9 | Return `job_id`, `record_id`, extracted entities, mapping method, and CRM links in response | Must | Done |

---

## 6. Functional Requirements — Extraction

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| EXT-1 | Extract 17 core fields via strict JSON prompt to Groq LLM | Must | Done |
| EXT-2 | Budget normalization: strip currency symbols, convert to integer (`$75k` → `75000`) | Must | Done |
| EXT-3 | Intent standardization: output exactly `"high"`, `"medium"`, or `"low"` | Must | Done |
| EXT-4 | Timeline filtering: extract only decision/implementation timelines; ignore logistics | Must | Done |
| EXT-5 | Product/version separation: clean product name + separate version field | Must | Done |
| EXT-6 | Competitor normalization: official names, deduplicated array | Must | Done |
| EXT-7 | Advanced CRM fields: `mentioned_company`, `procurement_stage`, `use_case`, `decision_criteria`, `budget_owner`, `implementation_scope` | Must | Done |
| EXT-8 | Support `custom_fields` (up to 20 key-value pairs) for domain-specific data | Must | Done |
| EXT-9 | Heuristic extraction fallback when LLM is unavailable or rate-limited | Should | Done |
| EXT-10 | Merge heuristic results with LLM output (LLM non-empty values win) | Should | Done |
| EXT-11 | Post-LLM refinement passes for product and timeline fields | Should | Done |
| EXT-12 | Enrich `map_version` in custom_fields from transcript patterns for automotive contexts | Should | Done |
| EXT-13 | Prompt truncation for very long transcripts (120K char limit with middle omission) | Should | Done |
| EXT-14 | No hallucination: null for any field not evidenced in the text | Must | Done |

### 6.1 Extraction Prompt Design

The extraction prompt uses a strict structure with clearly delineated rule sections:

```
═══ HARD RULES ═══
  - Strict JSON only, no markdown, no commentary
  - No hallucination; null for missing
  - All 17 keys must appear

═══ BUDGET RULES ═══
  - Integer output (no currency symbols)
  - Conversion examples provided
  - null if not mentioned

═══ INTENT RULES ═══
  - Exactly "high" | "medium" | "low"
  - Definitions for each level
  - Default to "medium" if uncertain

═══ TIMELINE RULES ═══
  - Decision/implementation only
  - Explicit ignore list (ship, send, deliver, mail)
  - Valid/invalid examples

═══ PRODUCT + VERSION ═══
  - Separation rules with examples

═══ COMPETITOR RULES ═══
  - Normalize names
  - Deduplicate

═══ OUTPUT FORMAT ═══
  - Exact 17-key JSON template
  - Field definitions
```

### 6.2 Normalization Pipeline

The extraction output goes through multiple normalization layers:

1. **`_coerce_budget()`** — Strips symbols, handles `k`/`m` suffixes, converts to integer string
2. **`_coerce_intent()`** — Maps freeform LLM output to exactly `high`/`medium`/`low`
3. **`_coerce_competitors()`** — Normalizes array from string or list input
4. **`_coerce_string_list()`** — Handles stakeholders and similar list fields
5. **`_coerce_custom_fields()`** — Limits to 20 entries, trims key/value lengths
6. **`_unwrap_extraction_payload()`** — Handles LLM wrapping (e.g. `{extraction: {...}}`)

### 6.3 Fallback Strategy

```
1. Primary attempt: Groq JSON mode (json_mode=True)
   ├── Success + non-empty → use result
   └── Empty or failure → continue

2. Retry attempt: Groq without JSON mode (json_mode=False)
   ├── Success + non-empty → use result
   └── Failure → continue

3. Heuristic fallback: Rule-based regex extraction
   ├── Budget patterns, intent keywords, competitor mentions
   └── Timeline inference, company name detection

4. Merge: LLM result + heuristic (LLM values win when non-empty)

5. Refinement: Product cleanup, timeline cleanup, map version enrichment
```

---

## 7. Functional Requirements — AI Intelligence Layer

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| AI-1 | `classify_interaction(text)` → returns `"sales"` / `"support"` / `"inquiry"` / `"complaint"` | Must | Done |
| AI-2 | `score_deal(record)` → returns integer 0-100 with defined scoring logic | Must | Done |
| AI-3 | `generate_next_action(text)` → returns actionable step, max 12 words, starts with verb | Must | Done |
| AI-4 | `detect_risk(text)` → returns `{risk_level: "low"/"medium"/"high", reason: "..."}` | Must | Done |
| AI-5 | `generate_summary(text)` → returns exactly 2 concise sentences | Must | Done |
| AI-6 | `auto_tag(text)` → returns up to 8 relevant CRM tags | Should | Done |
| AI-7 | `normalize_data(record)` → budget/timeline normalization | Should | Done |
| AI-8 | `detect_duplicates(record, db)` → check for existing accounts/contacts | Should | Done |
| AI-9 | `generate_email_draft(record)` → professional follow-up email (3-5 sentences) | Should | Done |
| AI-10 | `run_ai_intelligence(text, extracted)` → batch orchestrator for pipeline integration | Must | Done |
| AI-11 | Heuristic fallbacks for all LLM-dependent functions (keyword matching) | Must | Done |
| AI-12 | All LLM calls go through `groq_chat_with_retry` for rate limit resilience | Must | Done |

### 7.1 Deal Scoring Logic (Detailed)

The deal score starts at **0** and accumulates points based on extracted data:

| Condition | Points | Rationale |
|-----------|--------|-----------|
| Budget is present and non-zero | +20 | Budget visibility indicates real opportunity |
| Intent = `"high"` | +30 | Strong buying signals = high-quality deal |
| Intent = `"medium"` | +15 | Active evaluation is promising but uncertain |
| Timeline is present | +20 | Clear timeline indicates active buying process |
| Competitors present (array non-empty) | +10 | Active comparison means engaged buyer |
| Each missing core field (budget, intent, product, timeline) | -5 | Missing data reduces confidence |

**Score range:** 0-100 (clamped). **Maximum possible:** 80 (all positive conditions met, no missing fields).

### 7.2 Classification Rules

| Category | LLM Signal Keywords | Heuristic Fallback Keywords |
|----------|--------------------|-----------------------------|
| `sales` | Purchasing, pricing, proposals, deals, budget | price, buy, deal, budget, proposal, quote, purchase, cost |
| `support` | Bugs, issues, broken features, how-to help | broken, issue, not working, bug, fix, error, crash |
| `inquiry` | General questions, info gathering, demos, evaluations | (default if nothing else matches) |
| `complaint` | Frustration, escalation, dissatisfaction, threats | angry, frustrated, terrible, worst, unacceptable, cancel, lawsuit |

### 7.3 Risk Detection Factors

| Risk Level | Signal |
|-----------|--------|
| **High** | Cancel threats, legal mentions, extreme dissatisfaction, competitor switching |
| **Medium** | Competitor evaluation, budget objections, delays, churn signals |
| **Low** | Normal conversation, no negative signals detected |

---

## 8. Functional Requirements — CRM Mapping

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| MAP-1 | Map transcript to existing Account / Contact / Deal where match found | Must | Done |
| MAP-2 | Support both LLM-assisted and rule-based mapping strategies | Should | Done |
| MAP-3 | Store mapping method metadata (`llm`, `rules`, `llm+rules`) on record | Should | Done |
| MAP-4 | Create new Account/Contact/Deal when no match and sufficient data exists | Should | Done |

---

## 9. Functional Requirements — HubSpot Sync

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| HS-1 | Create a **deal** with all mapped properties (not a single blob field) | Must | Done |
| HS-2 | Map deal properties: `dealname`, `amount`, `pipeline`, `dealstage`, `intent`, `timeline`, `product`, `product_version`, `competitors`, `pain_points`, `next_step`, `procurement_stage`, `mentioned_company`, `use_case`, `decision_criteria`, `budget_owner`, `implementation_scope` | Must | Done |
| HS-3 | Resolve or create **contact** when hints exist (email, phone from metadata/transcript) | Should | Done |
| HS-4 | Resolve or create **company** when `mentioned_company` is available | Should | Done |
| HS-5 | Associate deal ↔ contact and deal ↔ company via HubSpot Associations API v4 | Should | Done |
| HS-6 | Create a **note** engagement with transcript content | Must | Done |
| HS-7 | Resolve pipeline and stage via HubSpot Pipelines API or env overrides | Must | Done |
| HS-8 | Return HubSpot IDs (deal, contact, company, note) and portal URLs in response | Should | Done |
| HS-9 | Product string cleaning for HubSpot (remove version numbers, normalize format) | Should | Done |
| HS-10 | Extract `product_version` from transcript via regex when not in structured extraction | Should | Done |
| HS-11 | Support re-sync for the same record after corrections | Should | Done |

---

## 10. Functional Requirements — Analytics & Dashboard

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| DASH-1 | Revenue analytics: total records, total budget, per-record budget/intent/timeline | Must | Done |
| DASH-2 | AI Intelligence dashboard: intent distribution (pie chart), risk distribution (pie chart), avg deal score, KPI cards | Must | Done |
| DASH-3 | Intelligence table: ID, Intent (colored badge), Deal Score (progress bar), Risk (icon + color), Next Action, Tags | Must | Done |
| DASH-4 | Insights aggregation: interaction counts, budget sums/averages, source type breakdown, intent keyword buckets | Should | Done |
| DASH-5 | Interaction timeline: chronological view with source type filter and limit | Should | Done |
| DASH-6 | CRM records browser with search by content, filter by record ID | Must | Done |

---

## 11. Functional Requirements — UI/UX

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| UI-1 | Audio upload with drag-and-drop, format support indicator, processing spinner | Must | Done |
| UI-2 | Text ingestion with source type selector (call, email, meeting, sms, crm_update) | Must | Done |
| UI-3 | Display all 17 extracted fields with clear labels and formatting | Must | Done |
| UI-4 | **Intent badges** — colored (green=high, yellow=medium, red=low) | Must | Done |
| UI-5 | **Risk indicators** — icon + color (green=low, orange=medium, red=high) | Must | Done |
| UI-6 | **Deal score progress bar** — 0-100 with color gradient | Must | Done |
| UI-7 | **Tags as chips** — rounded pill style with consistent colors | Should | Done |
| UI-8 | **Summary card** at top of each record (2-line summary + next action highlight) | Must | Done |
| UI-9 | **Advanced CRM fields** grid (mentioned_company, procurement_stage, use_case, decision_criteria, budget_owner, implementation_scope) | Must | Done |
| UI-10 | **HubSpot sync** button per record with success/error feedback and deep link URLs | Must | Done |
| UI-11 | **Loading states** — spinner while processing, disabled buttons during operations | Must | Done |
| UI-12 | **Smooth animations** — fade-in for cards, hover effects, staggered list rendering | Should | Done |
| UI-13 | **Clean card-based layout** — SaaS style with consistent spacing, shadows, rounded corners | Must | Done |
| UI-14 | **Responsive design** — sidebar collapses on mobile, grids reflow | Should | Done |
| UI-15 | **Empty states** — friendly message when no data is available | Should | Done |
| UI-16 | **Pie charts** using Recharts for intent and risk distribution | Must | Done |
| UI-17 | **Bar charts** for revenue analytics | Should | Done |
| UI-18 | Sidebar navigation with section icons and active state highlighting | Should | Done |
| UI-19 | **Delete all records** functionality for development reset | Should | Done |
| UI-20 | localStorage persistence of HubSpot sync state for deep links | Should | Done |

### 11.1 Design System

The frontend uses a CSS-variable-based design system:

| Token Category | Examples |
|---------------|----------|
| **Colors** | `--bg`, `--surface`, `--ink`, `--brand`, `--green`, `--red`, `--yellow` |
| **Typography** | `--font`, `--ink-soft`, `--ink-muted` |
| **Spacing** | Consistent padding/margin scale |
| **Shadows** | `--shadow-sm`, `--shadow-md` for depth hierarchy |
| **Borders** | `--line`, `--radius-md`, `--radius-xl` for roundness |
| **Animations** | `crm-fade-in`, `crm-pulse`, `crm-spin` with staggered delays |

---

## 12. API Reference

### 12.1 Ingestion Endpoints

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/ingest/transcript` | Ingest text transcript | `TranscriptIngestRequest` (content, metadata, external_id, participants, source_type) | `TranscriptIngestResponse` (job_id, record_id, extracted, CRM links, mapping_method) |
| `POST` | `/ingest/audio` | Ingest audio file | Multipart form (file, optional metadata JSON) | `AudioIngestResponse` (transcript, job_id, record_id, extracted, structured_transcript) |
| `POST` | `/ingest/interaction` | Ingest interaction webhook | `InteractionIngestRequest` (source_type, content, metadata, external_id, participants) | `TranscriptIngestResponse` |

### 12.2 CRM Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/api/v1/crm/records` | List all CRM records with all fields | `list[CrmRecordOut]` — includes all 17 extraction fields, AI intelligence fields, CRM links |
| `DELETE` | `/api/v1/crm/records` | Delete all records (destructive reset) | `DeleteRecordsResponse` (deleted count) |
| `POST` | `/api/v1/crm/map` | Map extracted payload to CRM entities | `CRMMapResponse` |

### 12.3 Analytics Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/api/v1/analytics/revenue` | Budget totals and per-record breakdown | `RevenueResponse` (total_records, total_budget, records[]) |
| `GET` | `/api/v1/analytics/ai-intelligence` | AI intelligence aggregation | `AIIntelligenceResponse` (total_records, intent_distribution, risk_distribution, avg_deal_score, records[]) |
| `GET` | `/api/v1/analytics/insights` | Revenue/interaction intelligence summary | `InsightsResponse` (total_interactions, total_budget_sum, avg_budget, by_source_type, intent_keywords_high/low) |

### 12.4 Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness check — returns `{status: "ok"}` |
| `GET` | `/api/v1/extraction/preview` | Extraction preview (placeholder) |
| `GET` | `/api/v1/interactions/timeline` | Chronological interactions (supports `limit` and `source_type` query params) |
| `POST` | `/api/v1/hubspot/push/{record_id}` | Sync one CRM record to HubSpot |

### 12.5 API Documentation

- **OpenAPI (Swagger UI):** `/docs`
- **ReDoc:** `/redoc`

---

## 13. Data Model

### 13.1 Entity Relationship

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│ Account  │ 1───* │ Contact  │       │  Deal    │
│          │ 1───* │          │       │          │
│  id (PK) │       │  id (PK) │       │  id (PK) │
│  name    │       │  name    │       │  value   │
│          │       │  email   │       │  stage   │
│          │       │  acct_id │       │  acct_id │
└────┬─────┘       └────┬─────┘       └────┬─────┘
     │ 1                │ 1                │ 1
     │                  │                  │
     │ *                │ *                │ *
┌────┴──────────────────┴──────────────────┴─────┐
│                  CrmRecord                      │
│                                                 │
│  IDENTITY         │  EXTRACTION (17 fields)     │
│  ─────────        │  ────────────────────────   │
│  id (PK)          │  budget (str→int)           │
│  content (text)   │  intent (high/med/low)      │
│  source_type      │  timeline                   │
│  created_at       │  product                    │
│  external_id      │  product_version            │
│  participants[]   │  competitors[]              │
│  source_metadata  │  industry                   │
│  mapping_method   │  pain_points (text)         │
│  structured_      │  next_step                  │
│    transcript     │  urgency_reason             │
│  custom_fields{}  │  stakeholders[]             │
│                   │  mentioned_company          │
│  AI INTELLIGENCE  │  procurement_stage          │
│  ───────────────  │  use_case                   │
│  interaction_type │  decision_criteria          │
│  deal_score       │  budget_owner               │
│  risk_level       │  implementation_scope       │
│  risk_reason      │                             │
│  summary          │  CRM LINKS                  │
│  tags[]           │  ──────────                 │
│  next_action      │  account_id (FK)            │
│                   │  contact_id (FK)            │
│                   │  deal_id (FK)               │
└─────────────────────────────────────────────────┘

┌──────────┐
│ AuditLog │  (append-only)
│  id (PK) │
│  event   │
│  entity  │
│  detail  │
│  created │
└──────────┘
```

### 13.2 CrmRecord Column Reference

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | Integer (PK) | Auto | Primary key |
| `content` | Text | — | Full transcript/interaction text |
| `budget` | String(1024) | `""` | Numeric budget as string |
| `intent` | String(1024) | `""` | `"high"`, `"medium"`, or `"low"` |
| `product` | String(1024) | `""` | Clean product/service name |
| `product_version` | String(256) | `""` | Version identifier |
| `timeline` | String(1024) | `""` | Decision/implementation timeline |
| `industry` | String(1024) | `""` | Industry vertical |
| `competitors` | JSONB (array) | `[]` | Normalized competitor names |
| `pain_points` | Text | `""` | Customer problems/frustrations |
| `next_step` | Text | `""` | Agreed-upon next step |
| `urgency_reason` | Text | `""` | Why time-sensitive |
| `stakeholders` | JSONB (array) | `[]` | Decision-makers (names/roles) |
| `mentioned_company` | String(512) | `""` | Customer's company |
| `procurement_stage` | String(128) | `""` | Buying process stage |
| `use_case` | Text | `""` | Intended product usage |
| `decision_criteria` | Text | `""` | What matters to buyer |
| `budget_owner` | String(256) | `""` | Budget authority |
| `implementation_scope` | String(256) | `""` | Rollout scope |
| `custom_fields` | JSONB (object) | `{}` | Up to 20 domain-specific k/v pairs |
| `interaction_type` | String(64) | `""` | AI classification result |
| `deal_score` | Integer | `0` | AI deal score (0-100) |
| `risk_level` | String(32) | `""` | AI risk level |
| `risk_reason` | Text | `""` | AI risk explanation |
| `summary` | Text | `""` | AI 2-line summary |
| `tags` | JSONB (array) | `[]` | AI auto-generated tags |
| `next_action` | Text | `""` | AI suggested next action |
| `source_type` | String(64) | `"call"` | Ingestion channel |
| `external_interaction_id` | String(256) | null | External correlation ID (indexed) |
| `participants` | JSONB (array) | `[]` | Participant names/emails |
| `source_metadata` | JSONB (object) | `{}` | Original ingestion metadata |
| `structured_transcript` | JSONB | null | Timestamped segments with speakers |
| `mapping_method` | String(32) | `"rules"` | How CRM entities were resolved |
| `account_id` | Integer (FK) | null | Linked Account |
| `contact_id` | Integer (FK) | null | Linked Contact |
| `deal_id` | Integer (FK) | null | Linked Deal |
| `created_at` | DateTime (TZ) | `now()` | Record creation timestamp |

### 13.3 Schema Migration Strategy

Schema migrations are handled idempotently in `database.py`:

- `Base.metadata.create_all()` creates tables on first run
- `_ensure_crm_records_columns()` adds columns via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- `_ensure_crm_records_interaction_columns()` adds interaction-specific columns
- `_ensure_crm_records_ai_intelligence_columns()` adds all AI + advanced extraction columns (18 statements)
- All migrations run on application startup via `init_db()`
- Safe for repeated execution — existing columns are not modified

---

## 14. Non-Functional Requirements

| Area | Requirement | Implementation |
|------|-------------|---------------|
| **API Standards** | OpenAPI docs at `/docs`; JSON schemas validated by Pydantic | FastAPI auto-generates OpenAPI spec |
| **Configuration** | All secrets via `.env` file; no hardcoded credentials | Pydantic `Settings` class with env loading |
| **Performance** | Async-friendly endpoints; transcription bounded by hardware/model size | `asyncio.to_thread` for blocking LLM/Whisper calls |
| **Resilience** | LLM rate limit handling with retry and backoff; heuristic fallback | `groq_chat_with_retry` with configurable attempts |
| **Observability** | Structured logging for ingestion, extraction, HubSpot, and AI intelligence | Python `logging` module throughout |
| **Data Integrity** | Append-only audit log; PostgreSQL transactions; idempotent migrations | SQLAlchemy session management; audit_repository |
| **Security** | PII minimized in external API calls; audio processed locally | Whisper runs on-server; only structured data sent to Groq |
| **Maintainability** | Modular service architecture; separated concerns | services/, utils/, models/, db/ layers |
| **Backward Compatibility** | New fields have defaults; existing APIs unchanged | All new DB columns have `NOT NULL DEFAULT` values |

---

## 15. Configuration & Environment

### 15.1 Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/db`) |
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM extraction and intelligence |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model identifier |
| `WHISPER_MODEL` | No | `base` | Local Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |
| `GROQ_LABEL_SPEAKERS` | No | `false` | Enable LLM-based speaker diarization |
| `HUBSPOT_API_KEY` | No | — | HubSpot private app token (enables sync features) |
| `HUBSPOT_PIPELINE_ID` | No | — | Override HubSpot pipeline ID |
| `HUBSPOT_DEAL_STAGE_ID` | No | — | Override HubSpot deal stage ID |
| `CORS_ORIGINS` | No | `["*"]` | Allowed CORS origins |
| `DEBUG` | No | `false` | Enable debug logging |

### 15.2 Backend Dependencies

```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
psycopg2-binary
openai
python-dotenv
openai-whisper
requests
python-multipart
```

### 15.3 Frontend Dependencies

```json
{
  "react": "^19.0.0",
  "react-dom": "^19.0.0",
  "recharts": "^3.0.0"
}
```

### 15.4 Running the Application

**Backend:**
```bash
cd ai-crm-system
pip install -r requirements.txt
# Configure .env with DATABASE_URL, GROQ_API_KEY, etc.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd crm-ui
npm install
npm run dev    # Development server on http://localhost:5173
npm run build  # Production build to dist/
```

---

## 16. Acceptance Criteria

### 16.1 Ingestion

- [ ] Audio upload produces transcript and persisted record with all fields populated
- [ ] Text ingestion extracts 17 fields and stores record with correct source_type
- [ ] Interaction webhook processes email/meeting/SMS content through full pipeline
- [ ] External ID deduplication tracking works across multiple ingestions
- [ ] Participant metadata is preserved from both explicit list and metadata.participants

### 16.2 Extraction

- [ ] Budget is always an integer (or null) — no currency symbols in stored value
- [ ] Intent is always exactly `"high"`, `"medium"`, or `"low"`
- [ ] Timeline contains only decision/implementation phrases — logistics phrases are excluded
- [ ] Product and product_version are correctly separated
- [ ] Competitors are normalized and deduplicated
- [ ] All 6 advanced CRM fields (`mentioned_company`, `procurement_stage`, `use_case`, `decision_criteria`, `budget_owner`, `implementation_scope`) are extracted when present
- [ ] Heuristic fallback produces usable output when LLM is unavailable
- [ ] No hallucinated values — fields are null when information is not in the text

### 16.3 AI Intelligence

- [ ] Every record receives interaction_type, deal_score, risk_level, risk_reason, summary, next_action, and tags
- [ ] Deal score follows defined formula: budget +20, high intent +30, medium +15, timeline +20, competitors +10, missing fields -5
- [ ] Next action is max 12 words and starts with a verb
- [ ] Summary is exactly 2 concise sentences
- [ ] Classification covers all four types: sales, support, inquiry, complaint
- [ ] Risk detection identifies negative sentiment and competitive threats

### 16.4 HubSpot Sync

- [ ] Deal created with all mapped properties (not a single blob field)
- [ ] Contact resolved by email/phone or created when not found
- [ ] Company resolved by name or created from mentioned_company
- [ ] Deal ↔ Contact and Deal ↔ Company associations created
- [ ] Note engagement created with transcript content
- [ ] Pipeline/stage resolved via API or env overrides
- [ ] product_version populated even when only in transcript (regex extraction)

### 16.5 UI/UX

- [ ] Audio and text ingestion flows with loading spinners and error handling
- [ ] All 17 extracted fields displayed in record cards
- [ ] AI Intelligence dashboard shows KPI cards, pie charts, and intelligence table
- [ ] Intent badges are color-coded (green/yellow/red)
- [ ] Risk indicators show icon + color
- [ ] Deal score displayed as progress bar (0-100)
- [ ] Tags shown as rounded chip pills
- [ ] Advanced CRM fields displayed in grid layout
- [ ] HubSpot sync button with success/error feedback
- [ ] Responsive design works on mobile

---

## 17. Known Limitations & Backlog

| Item | Status | Notes |
|------|--------|-------|
| Budget misreads (e.g. $99 vs $99,000) | Mitigated | Normalization pipeline handles most cases; edge cases need human review |
| Accuracy KPIs | Backlog | No built-in batch evaluation against labeled dataset |
| Native connectors (Gmail, Calendar, telephony) | Backlog | Currently API/UI ingestion only |
| Real-time streaming transcription | Backlog | Batch processing only |
| Multi-tenant / RBAC | Backlog | Single-instance deployment |
| Code splitting for frontend bundle | Backlog | Single bundle >500KB; Vite code splitting recommended |
| Frontend API base URL | Hardcoded | Currently `http://127.0.0.1:8000`; should be env-based for deployment |

---

## 18. Out of Scope (Current Release)

- Multi-tenant billing and org management as a SaaS product
- Mobile-native applications (iOS/Android)
- Real-time streaming transcription during live calls
- Enterprise SSO / SAML / RBAC
- Full GDPR tooling (right to erasure, consent management)
- ML-based predictive deal forecasting (beyond rule-based scoring)
- Native email/calendar/telephony integrations (OAuth connectors)

---

## 19. File Structure Reference

### Backend (`ai-crm-system/`)

```
ai-crm-system/
├── .env                              # Environment configuration (not committed)
├── requirements.txt                  # Python dependencies
├── docs/
│   ├── BRD_AI_CRM.md               # Business Requirements Document
│   └── PRD_AI_CRM.md               # Product Requirements Document (this file)
└── app/
    ├── main.py                      # FastAPI application factory
    ├── core/config.py               # Settings and environment loading
    ├── api/
    │   ├── deps.py                  # Database dependency injection
    │   └── routes/
    │       ├── health.py            # Health check endpoint
    │       ├── ingestion.py         # Audio/text/interaction ingestion
    │       ├── extraction.py        # Extraction preview
    │       ├── crm.py               # CRM records CRUD + API models
    │       ├── analytics.py         # Revenue, insights, AI intelligence
    │       ├── interactions.py      # Interaction timeline
    │       └── hubspot.py           # HubSpot sync endpoint
    ├── db/
    │   ├── database.py              # DB engine, init, migrations
    │   ├── models.py                # ORM models (5 tables)
    │   ├── crm_record_repository.py # CRM record persistence
    │   └── audit_repository.py      # Audit log persistence
    ├── models/
    │   ├── ingestion.py             # Request/response + ExtractedEntities
    │   ├── crm.py                   # CRM mapping models
    │   ├── extraction.py            # Extraction preview models
    │   └── health.py                # Health response model
    ├── services/
    │   ├── extraction_service.py    # 17-field extraction prompt + builder
    │   ├── groq_extraction.py       # LLM execution + normalization
    │   ├── groq_llm.py              # Groq client wrapper
    │   ├── groq_mapping.py          # LLM CRM entity resolution
    │   ├── groq_speakers.py         # Speaker diarization
    │   ├── ai_intelligence.py       # 9 AI functions + batch runner
    │   ├── ingestion_pipeline.py    # Full pipeline orchestrator
    │   ├── mapping_service.py       # CRM mapping (LLM + rules)
    │   ├── transcription_service.py # Local Whisper ASR
    │   ├── hubspot_client.py        # HubSpot REST client
    │   └── hubspot_service.py       # HubSpot sync orchestration
    ├── utils/
    │   ├── budget.py                # Budget parsing utility
    │   ├── groq_retry.py            # LLM retry with backoff
    │   ├── heuristic_extraction.py  # Regex fallback extraction
    │   ├── extraction_refine.py     # Post-LLM field refinement
    │   └── hubspot_product.py       # Product string cleaning
    └── ingestion/
        └── receiver.py              # Transcript acceptance + job ID
```

### Frontend (`crm-ui/`)

```
crm-ui/
├── index.html                       # HTML shell with font preloads
├── package.json                     # Dependencies and scripts
├── vite.config.js                   # Vite configuration
├── eslint.config.js                 # ESLint configuration
└── src/
    ├── main.jsx                     # React root mount
    ├── App.jsx                      # Main application (all UI logic)
    ├── crm-app.css                  # Design system + all component styles
    ├── index.css                    # Base styles
    └── App.css                      # Legacy styles
```

---

## 20. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | April 2026 | Engineering | Initial PRD — core ingestion, extraction, HubSpot sync, basic UI |
| 2.0 | April 15, 2026 | Engineering | Major expansion: 17-field extraction schema with strict rules (budget normalization, intent enum, timeline filtering, product/version separation); AI Intelligence Layer (6 core functions: classify, score, risk, summarize, next action, tag); 6 new advanced CRM fields (mentioned_company, procurement_stage, use_case, decision_criteria, budget_owner, implementation_scope); complete API reference with all 13 endpoints; detailed data model with 33 CrmRecord columns; pipeline architecture documentation; deal scoring formula; classification and risk detection rules; extraction fallback strategy; normalization pipeline; HubSpot field mapping for all new fields; modern SaaS-style UI with design system; comprehensive acceptance criteria |
