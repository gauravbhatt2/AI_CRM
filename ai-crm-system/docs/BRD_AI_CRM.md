# Business Requirements Document (BRD)

## AI-Assisted CRM Ingestion, Intelligence & HubSpot Sync

**Version:** 2.3
**Last Updated:** April 19, 2026
**Product:** AI CRM System (FastAPI + React + PostgreSQL + Groq LLM)
**Companion Document:** `PRD_AI_CRM.md`

---

## 1. Executive Summary

Sales and support teams generate rich conversational data — calls, meetings, emails, SMS — that rarely lands in the CRM in a structured, timely way. Reps spend hours manually updating deal records, and critical context (budget signals, competitor mentions, next steps, stakeholder names) is lost between handoffs.

This product solves that by turning **raw audio or text conversations** into **structured, AI-enriched CRM records** in seconds. It:

1. **Transcribes** audio locally via `faster-whisper` (CTranslate2 backend — no torch, no large model downloads by default). No audio leaves the server. Rule-based speaker labeling tags each segment as "Sales" / "Customer" / named participants; a Groq-powered refinement pass is available behind an opt-in flag.
2. **Extracts** structured CRM fields via a **two-phase** Groq pipeline — **factual extraction** (statements, entities, participants, timestamps) then **evaluation** (intent, pain points, scoring, next actions) from merged facts — with heuristic fallback where needed.
3. **Classifies, scores, and analyzes** every interaction through an AI Intelligence Layer — producing deal scores, risk assessments, summaries, next actions, and tags automatically.
4. **Persists** everything to a local PostgreSQL datastore with full audit trail.
5. **Syncs** deals, contacts, companies, and notes to **HubSpot** with proper field mapping, associations, and pipeline resolution.
6. **Visualizes** all data through a modern SaaS-style React dashboard with analytics, charts, and actionable intelligence.

The result: revenue teams get a single source of truth without manual data entry, leadership gets real-time pipeline visibility, and operations gets clean, consistent CRM data.

---

## 2. Business Problem

### 2.1 Current Pain Points

| Problem | Business Impact | Affected Stakeholders |
|---------|----------------|----------------------|
| Manual CRM updates lag behind conversations | Pipeline visibility is stale; forecasting is unreliable | Sales leadership, RevOps |
| Important facts (product interest, timeline, next steps, stakeholders) stay in notes or nowhere | Coaching, handoffs, and follow-ups miss context; deals slip | Account executives, CS managers |
| Disconnected tools (ASR services, spreadsheets, CRM) | Duplicate effort, inconsistent records, low CRM adoption | All revenue team members |
| No structured analysis of conversation quality | Managers cannot identify at-risk deals or coaching opportunities proactively | Sales managers, VP Sales |
| Budget and intent signals are subjective and inconsistent | Deal scoring varies by rep; pipeline accuracy degrades | RevOps, Finance |
| No unified view across interaction channels | Email, call, meeting, and SMS data live in separate silos | Operations, Customer Success |

### 2.2 Root Cause

The fundamental issue is that **structured CRM data requires human translation** from unstructured conversations. This translation is:
- **Time-consuming** — reps spend 20-30% of their time on data entry
- **Inconsistent** — different reps capture different fields to different standards
- **Lossy** — nuance (competitor mentions, stakeholder dynamics, urgency signals) is routinely dropped
- **Delayed** — data enters the CRM hours or days after the conversation

---

## 3. Business Objectives

| # | Objective | Measurable Outcome |
|---|-----------|-------------------|
| 1 | **Eliminate manual conversation-to-CRM data entry** | Structured record created within seconds of ingestion |
| 2 | **Maximize data completeness** on every interaction | 17+ fields extracted per record (budget, intent, product, timeline, competitors, stakeholders, pain points, use case, decision criteria, procurement stage, etc.) |
| 3 | **Provide AI-driven deal intelligence** | Every record gets: classification, deal score (0-100), risk assessment, 2-line summary, actionable next step, and auto-tags |
| 4 | **Enable seamless HubSpot synchronization** | One-click sync of deals, contacts, companies, and notes with proper associations and field mapping |
| 5 | **Support multi-channel ingestion** | Process calls (audio), emails, meetings, SMS, and CRM updates through a single pipeline |
| 6 | **Deliver actionable analytics** | Dashboard with intent distribution, risk analysis, deal scoring, revenue metrics, and interaction timeline |
| 7 | **Maintain full auditability** | Append-only audit log of every ingestion event with metadata |

---

## 4. Stakeholders

| Role | Interest | How They Use the System |
|------|----------|------------------------|
| **Sales / Account Executives** | Accurate deals, next steps, contact context without manual entry | Ingest calls/emails; review extracted data; sync to HubSpot |
| **Sales Managers** | Pipeline quality, coaching opportunities, risk visibility | Review AI intelligence dashboard; monitor deal scores and risk levels |
| **Sales Operations / RevOps** | Consistent fields, HubSpot hygiene, reporting accuracy | Configure HubSpot mapping; verify sync quality; use analytics |
| **Customer Success** | Interaction history, pain points, stakeholder mapping | Review records timeline; understand customer context across channels |
| **Engineering / IT** | Secure APIs, environment configuration, integration scopes | Deploy and configure the system; manage API keys and database |
| **Leadership / VP Sales** | Pipeline visibility, reduced overhead, revenue intelligence | Consume analytics dashboards and aggregated insights |

---

## 5. Scope

### 5.1 In Scope (Delivered)

| Area | Capabilities |
|------|-------------|
| **Audio Ingestion** | Upload audio/video files; local `faster-whisper` transcription (INT8 on CPU, float16 on CUDA); heuristic speaker labels by default with opt-in Groq refinement (`GROQ_LABEL_SPEAKERS=true`); supported formats via FFmpeg |
| **Text Ingestion** | Direct transcript paste/POST; email, meeting notes, SMS content |
| **Multi-channel Support** | Source types: `call`, `email`, `meeting`, `sms`, `crm_update` with metadata tracking |
| **AI Extraction (17 fields)** | `budget` (integer), `intent` (high/medium/low), `timeline` (decision-only), `product`, `product_version`, `competitors`, `industry`, `pain_points`, `next_step`, `urgency_reason`, `stakeholders`, `mentioned_company`, `procurement_stage`, `use_case`, `decision_criteria`, `budget_owner`, `implementation_scope` |
| **Custom Fields** | Up to 20 additional key-value pairs per record for domain-specific data |
| **AI Intelligence Layer** | Interaction classification (sales/support/inquiry/complaint), deal scoring (0-100), risk detection (low/medium/high with reason), 2-line summary generation, next action suggestion (max 12 words), auto-tagging (max 8 tags), data normalization, duplicate detection, email draft generation |
| **Local CRM Datastore** | PostgreSQL with full relational model: Accounts, Contacts, Deals, CRM Records, Audit Logs |
| **HubSpot Integration** | Create/update deals with mapped properties; resolve/create contacts and companies; create engagement notes; associate entities; pipeline/stage resolution |
| **Analytics Dashboard** | Revenue analytics, AI intelligence metrics (intent/risk distribution pie charts, deal score averages), interaction timeline, record browser with search/filter |
| **Modern UI** | SaaS-style React dashboard (React Router pages) with intent badges, risk indicators, deal score bars, tag chips, loading states, animations, responsive design |
| **Audit Trail** | Append-only audit log for every ingestion event |
| **Agents API** | Deal chat, next-action suggestion, follow-up email/WhatsApp drafts grounded in CRM fields |
| **Google Workspace (optional)** | OAuth flow; Gmail generate/send and Calendar scheduling when credentials are configured (on-demand; not automatic mailbox ingestion) |

### 5.2 Out of Scope (Current Release)

| Item | Notes |
|------|-------|
| Automatic ingestion from full Gmail inbox or Calendar history | Optional OAuth supports compose/send and scheduling; bulk sync from providers is not implemented |
| Native telephony / CTI connectors | Interactions submitted via API/UI |
| Real-time streaming transcription during live calls | Batch processing only |
| Enterprise SSO / RBAC | Single-user deployment; authentication layer can be added |
| Full GDPR tooling | Deployment-dependent; PII handling via access control |
| Mobile-native apps | Responsive web UI only |
| Multi-tenant billing / SaaS org management | Single-instance deployment |
| ML-based deal forecasting beyond rule-based scoring | Current scoring uses structured heuristics + LLM |

---

## 6. Solution Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                        REACT DASHBOARD                          │
│  Upload │ Records │ Analytics │ AI Intelligence │ HubSpot Sync  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                                                                 │
│  ┌──────────┐  ┌────────────────┐  ┌───────────┐  ┌──────────────┐ │
│  │ Ingestion│→ │ Facts extract  │→ │ Evaluation│→ │ CRM Mapping  │ │
│  │ (Audio/  │  │ (Groq, single  │  │ (Groq,    │  │ (Account/    │ │
│  │  Text)   │  │  pass + merge) │  │ from facts│  │  Contact/    │ │
│  │          │  │                │  │ JSON)     │  │  Deal)       │ │
│  └──────────┘  └────────────────┘  └───────────┘  └──────┬───────┘ │
│       │                                                   │         │
│  ┌────┴──────────────┐  ┌───────────────┐         ┌─────┴──────┐  │
│  │ faster-whisper     │  │ Heuristic      │         │ PostgreSQL │  │
│  │ (CTranslate2,      │  │ speaker labels │         │ (persist)  │  │
│  │  INT8 CPU / FP16)  │  │ (+ opt. Groq)  │         └─────┬──────┘  │
│  └───────────────────┘  └───────────────┘               │         │
│                                                      │         │
│  ┌───────────────────────────────────────────────────┴──────┐  │
│  │                   HubSpot Sync Service                    │  │
│  │  Deals │ Contacts │ Companies │ Notes │ Associations      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingest** — Audio files are transcribed locally via `faster-whisper` (INT8 CPU default). Rule-based speaker labeling tags segments; Groq-based label refinement is an opt-in flag. Text/email payloads pass through directly.
2. **Extract** — Groq extracts **facts** in one pass (very long transcripts are truncated with middle omitted for the facts call), merges with heuristic hints, then **evaluates** intelligence (intent, pain, score, etc.) from merged facts; heuristic fallback fills gaps if LLM is unavailable or rate-limited
3. **Enrich** — AI Intelligence Layer merges LLM evaluation with heuristics: classify, score, detect risk, summarize, suggest next action, auto-tag
4. **Map** — Extracted entities are resolved to existing Accounts, Contacts, and Deals (LLM + rule-based)
5. **Persist** — Full record with all fields stored in PostgreSQL; audit event logged
6. **Sync** — On-demand push to HubSpot with proper field mapping and entity associations

---

## 7. Success Metrics (KPIs)

| KPI | Target | How to Measure |
|-----|--------|----------------|
| **Time to structured record** | < 30 seconds from ingestion to persisted record | Timestamp delta: API request → DB commit |
| **Field completeness** | ≥ 80% of records have budget, intent, product, and timeline populated (where mentioned in conversation) | Query `crm_records` for non-empty core fields |
| **Extraction accuracy** | Fields match human judgment in ≥ 85% of cases on the **Balanced** profile; regression guard at ≥ 75% enforced by `python -m app.evaluation.evaluator` in CI | Built-in evaluator harness (15 gold cases covering USD/EUR/INR budgets, lakh/crore, multi-speaker attribution, procurement stages) + spot-check sampling against human labels |
| **Hallucination rate (extracted fields)** | ≤ 5% of extracted scalar fields are unsupported by the transcript, measured on the Balanced profile with `EXTRACTION_REQUIRE_EVIDENCE=true` | `extraction_grounding.ground_extracted_entities` rejection log per ingest |
| **Transcription accuracy (English, clean audio)** | ≥ 96% word accuracy on the **Balanced** (default) profile; ≥ 97% on **Quality**; ≥ 93% on **Fast** (see PRD §14.1) | Sample-diffed transcripts against reference text |
| **AI Intelligence coverage** | 100% of records receive classification, score, risk, summary, next action, and tags | Query for non-empty AI fields |
| **HubSpot sync success rate** | ≥ 95% of sync attempts complete without API errors | API response logs / UI feedback |
| **Deal score reliability** | Scored deals correlate with actual outcomes (directional) | Retrospective analysis |
| **User adoption** | Users trust and act on synced data | Qualitative feedback; support tickets |
| **Dashboard engagement** | Active daily use of analytics and intelligence views | Usage tracking |

---

## 8. Extraction Schema — 17 Structured Fields

The system extracts exactly these fields from every conversation:

| # | Field | Type | Description | Rules |
|---|-------|------|-------------|-------|
| 1 | `budget` | integer / null | Numeric budget value | Strip currency symbols; `$75,000` → `75000`; `50k` → `50000`; null if not mentioned |
| 2 | `intent` | enum | Buyer intent level | Exactly `"high"`, `"medium"`, or `"low"` — no other values |
| 3 | `timeline` | string / null | Decision/implementation timeline | **Only** decision timelines; ignore logistics ("ship today", "send tomorrow") |
| 4 | `product` | string / null | Clean product/service name | Human-readable; no version numbers in this field |
| 5 | `product_version` | string / null | Version identifier | e.g. `"7.7"`, `"2024.1"` — separate from product name |
| 6 | `competitors` | string[] | Named competitors | Normalized to official names; deduplicated |
| 7 | `industry` | string / null | Industry vertical | e.g. `"retail"`, `"healthcare"` |
| 8 | `pain_points` | string / null | Customer problems/frustrations | Single descriptive string |
| 9 | `next_step` | string / null | Agreed-upon next step | From the conversation context |
| 10 | `urgency_reason` | string / null | Why time-sensitive | Only if urgency is expressed |
| 11 | `stakeholders` | string[] | People involved in decision | Names and/or roles |
| 12 | `mentioned_company` | string / null | Customer's company | Company the customer represents |
| 13 | `procurement_stage` | string / null | Where in buying process | e.g. `"evaluation"`, `"negotiation"`, `"budget approved"` |
| 14 | `use_case` | string / null | Intended product usage | What the customer plans to do with it |
| 15 | `decision_criteria` | string / null | What matters most to buyer | e.g. `"price"`, `"features"`, `"support quality"` |
| 16 | `budget_owner` | string / null | Person controlling budget | Name or role of budget authority |
| 17 | `implementation_scope` | string / null | Rollout scope | e.g. `"company-wide"`, `"regional"`, `"pilot"` |

### Extraction Hard Rules

1. **No hallucination** — if information is not in the text, return null
2. **Budget normalization** — always integer, no currency symbols or commas
3. **Intent standardization** — only `high`, `medium`, `low` (inferred from buying signals)
4. **Timeline filtering** — ignore shipping/logistics; only decision/implementation timelines
5. **Product/version separation** — `"map update version 7.7"` → product: `"map update"`, product_version: `"7.7"`
6. **Competitor normalization** — official names, no duplicates

---

## 9. AI Intelligence Layer — 6 Core Functions

Every ingested record is automatically enriched with AI intelligence:

| Function | Output | Purpose |
|----------|--------|---------|
| **classify_interaction** | `"sales"` / `"support"` / `"inquiry"` / `"complaint"` | Categorize the nature of the interaction |
| **score_deal** | Integer 0-100 | Quantify deal quality based on budget (+20), intent (+30/+15), timeline (+20), competitors (+10), minus missing fields (-5 each) |
| **detect_risk** | `{risk_level, reason}` | Identify churn signals, competitor threats, budget objections, negative sentiment |
| **generate_summary** | 2 concise sentences | Capture the key outcome and customer need |
| **generate_next_action** | Max 12 words, starts with a verb | Actionable step for the team |
| **auto_tag** | Up to 8 tags | e.g. `urgent`, `enterprise`, `demo-request`, `pricing`, `competitor-mentioned` |

### Additional AI Capabilities (Available via API)

| Function | Purpose |
|----------|---------|
| **normalize_data** | Budget and timeline normalization (currency, abbreviations) |
| **detect_duplicates** | Check for existing accounts/contacts by name similarity |
| **generate_email_draft** | Professional 3-5 sentence follow-up email based on record context |

---

## 10. HubSpot Integration

### 10.1 Sync Capabilities

| Entity | Operation | Field Mapping |
|--------|-----------|--------------|
| **Deal** | Create with mapped properties | `dealname`, `amount` (budget), `pipeline`, `dealstage`, `intent`, `timeline`, `product`, `product_version`, `competitors`, `pain_points`, `next_step`, `procurement_stage`, `mentioned_company`, `use_case`, `decision_criteria`, `budget_owner`, `implementation_scope` |
| **Contact** | Search by email/phone → create if not found | `firstname`, `lastname`, `email`, `phone` (from metadata and transcript) |
| **Company** | Search by name → create if not found | `name` (from `mentioned_company` field) |
| **Note** | Create engagement with transcript content | Full transcript text as note body |
| **Associations** | Link entities | Deal ↔ Contact, Deal ↔ Company via HubSpot Associations API v4 |

### 10.2 Pipeline Resolution

- Resolves pipeline ID and stage ID via HubSpot Pipelines API
- Falls back to environment variable overrides (`HUBSPOT_PIPELINE_ID`, `HUBSPOT_DEAL_STAGE_ID`)
- Validates stage belongs to pipeline before creating deal

---

## 11. Constraints & Assumptions

| Category | Constraint |
|----------|-----------|
| **LLM Dependency** | Groq API rate limits and pricing apply; heuristic fallback ensures pipeline never blocks |
| **HubSpot** | Custom properties (`product_version`, `pain_points`, etc.) must exist in the portal; OAuth token must have CRM read/write and engagement scopes |
| **Audio Processing** | FFmpeg must be installed on the server for non-WAV audio formats; Whisper model size affects transcription speed and accuracy |
| **Database** | PostgreSQL required; `DATABASE_URL` must be configured; schema migrations are idempotent |
| **Data Quality** | ASR and LLM outputs can misinterpret numbers or context; critical amounts should be treated as review items |
| **Network** | Backend must reach Groq API and HubSpot API; frontend connects to backend at configured URL |

---

## 12. Compliance & Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| PII in transcripts | High | Access control at deployment; minimize fields sent to external APIs; audio processed locally via Whisper |
| Incorrect extraction | Medium | Human review in UI before HubSpot sync; re-sync capability after corrections; heuristic validation |
| HubSpot API changes | Medium | Versioned client usage; monitoring of 4xx/5xx responses; graceful error handling |
| LLM hallucination in extraction | Medium | Strict prompt engineering with explicit "no hallucination" rules; null-by-default for missing data; intent locked to enum values |
| Groq rate limiting | Low | Built-in retry with exponential backoff; heuristic fallback pipeline; rate limit detection |
| Data loss | Low | PostgreSQL with standard backup practices; append-only audit log |

---

## 13. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Backend Framework** | FastAPI | Latest | Async REST API with OpenAPI docs |
| **Language** | Python | 3.11+ | Backend logic |
| **Database** | PostgreSQL | 14+ | Relational CRM data persistence |
| **ORM** | SQLAlchemy | 2.x | Database access and models |
| **Validation** | Pydantic | 2.x | Request/response schema validation |
| **LLM** | Groq API | Latest | AI extraction and intelligence (via OpenAI-compatible client) |
| **ASR** | OpenAI Whisper | Local | Audio-to-text transcription |
| **Frontend** | React | 19 | Dashboard UI |
| **Build Tool** | Vite | 8 | Frontend build and dev server |
| **Charts** | Recharts | 3 | Data visualization (pie charts, bar charts) |
| **CRM Sync** | HubSpot API | v3 | Deal, contact, company, note sync |
| **HTTP** | Requests | Latest | HubSpot API calls |

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **BRD** | Business Requirements Document (this document) |
| **PRD** | Product Requirements Document (companion: functional and technical detail) |
| **ASR** | Automatic Speech Recognition (e.g. Whisper) |
| **CRM Record** | A row in the local system representing one interaction with all extracted and AI-enriched fields |
| **AI Intelligence Layer** | The set of 6 classification/scoring/analysis functions that run on every record after extraction |
| **Deal Score** | A 0-100 integer indicating deal quality based on budget, intent, timeline, competitors, and field completeness |
| **Extraction** | The process of converting unstructured conversation text into 17 structured CRM fields via LLM |
| **Heuristic Fallback** | Rule-based extraction that activates when the LLM is unavailable or rate-limited |
| **Ingestion** | The full pipeline: receive input → transcribe (if audio) → extract → enrich → map → persist |
| **RevOps** | Revenue Operations — teams responsible for CRM data quality and sales process efficiency |
| **DRD** | Data Requirements Document (referenced in legacy spec labels) |
| **FRD** | Functional Requirements Document (referenced in legacy spec labels) |

---

## 15. Related Documents

| Document | Description |
|----------|------------|
| `PRD_AI_CRM.md` | Product requirements: functional specs, API reference, data model, acceptance criteria, known limitations |

Legacy “Interaction Mining” BRD/FRD/DRD themes (transcription, extraction, unified history, analytics) are covered by the in-scope capabilities above; items not delivered as product features (e.g. automated accuracy KPI jobs, enterprise RBAC) are listed under **Out of Scope** and **PRD — Known Limitations**.

---

## 16. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | April 2026 | Engineering | Initial BRD — core ingestion, extraction, HubSpot sync |
| 2.0 | April 15, 2026 | Engineering | Expanded to cover AI Intelligence Layer (6 functions), 17-field extraction schema, advanced CRM fields, deal scoring logic, modern SaaS UI, comprehensive analytics, multi-channel ingestion, full architecture documentation |
| 2.1 | April 18, 2026 | Engineering | Two-phase extraction, pyannote/OpenRouter, PRD alignment |
| 2.2 | April 19, 2026 | Engineering | Removed pyannote/torch stack; ASR migrated to faster-whisper (CTranslate2); gzip responses; cached Google status endpoint; added transcription-accuracy KPI tied to Fast / Balanced / Quality profiles (PRD §14.1) so the speed-first default is still measurable against a recoverable quality ceiling |
| 2.2 | April 19, 2026 | Engineering | Agents API and optional Google Workspace OAuth reflected in scope; removed duplicate status doc; UI described as multi-page React app |
| 2.3 | April 19, 2026 | Engineering | Facts extraction simplified to a single Groq pass (no sentence chunking); removed separate ASR cleanup / post-extraction validation modules; architecture diagram updated |
| 2.4 | April 19, 2026 | Engineering | **Accuracy-first defaults.** Shipped `WHISPER_PROFILE=balanced` (small + beam=5 + Groq speakers + two-pass self-consistency) as the new default. Introduced three new KPIs: raised extraction-accuracy target to 85% on Balanced with a 75% CI regression gate, added a hallucination-rate KPI (≤ 5% unsupported fields via evidence grounding), and lifted transcription-accuracy expectations (≥ 96% Balanced, ≥ 97% Quality). Added fuzzy account dedup (`ACCOUNT_FUZZY_MATCH_THRESHOLD=88`) so inbound calls cannot create "Acme Corp" / "Acme Inc." duplicates. Added idempotent transcript cache (`EXTRACTION_CACHE_SIZE=64`) for replay-safe re-ingests. Money parser now supports Indian units (lakh/crore) and fractional spelled-out amounts for accurate APAC deal sizing. |
