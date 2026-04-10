# AI Interaction Mining — BRD / FRD / DRD vs implementation

This document maps the requirements in `AI_Interaction_Mining_BRD_FRD_DRD.docx` (and the Interaction Mining capability table) to the current codebase. It also lists **extras** beyond the written spec.

## BRD (business)

| Requirement | Status | Notes |
|-------------|--------|--------|
| Capture & analyze interactions across calls, emails, SMS, meetings | **Partial** | Ingestion supports `source_type` (`call`, `email`, `meeting`, `sms`, `crm_update`) and stores a unified `crm_records` row per interaction. True zero-touch capture from live email/calendar/SMS providers is **not** integrated (no OAuth connectors); content is submitted via API or UI. |
| Transcribe conversations | **Yes** | `/ingest/audio` uses Whisper; optional speaker labeling (Groq) on segments. |
| NLP extraction of sales entities | **Yes** | Groq JSON extraction: budget, intent, product, competitors, industry, timeline, up to 20 `custom_fields`. |
| Map to CRM & unified history | **Yes** | `map_entities_to_crm` resolves account/contact/deal; `GET /api/v1/interactions/timeline` and CRM records list provide history. |
| Revenue / decision insights | **Partial** | `/api/v1/analytics/revenue`, `/api/v1/analytics/insights`, and dashboard UI. Not full forecasting or “deal progress” scoring as in a mature RevOps product. |

**KPIs** (e.g. ≥90% accuracy) are **not** automatically measured; DRD quality hooks are partial (validation on ingest; no batch evaluation job).

## FRD (functional)

| Module | Status | Implementation |
|--------|--------|------------------|
| **2.1 Call transcription** | **Yes** | Whisper → `StructuredTranscript` (segments, timestamps); optional speaker labels. |
| **2.2 AI data extraction** | **Yes** | `app/services/extraction_service.py` + Groq; `ExtractedEntities` schema. |
| **2.3 Contextual mapping** | **Yes** | `mapping_service.py` (LLM + rules); deal stage / intent snapshot / contact email from metadata where applicable. |
| **2.4 Automated data capture** | **Partial** | `/ingest/interaction` for webhook-style pushes; no native Salesforce/Gmail/etc. sync. |
| **2.5 Revenue insights** | **Partial** | Aggregates + keyword buckets on intent; UI dashboard + analytics views. |
| **2.6 Flow** | **Yes** | Capture → (transcribe if audio) → extract → map → persist → expose via API/UI. |

## DRD (data)

| Area | Status | Implementation |
|------|--------|------------------|
| **3.1 Interaction data** | **Yes** | `CrmRecord`: id, `source_type`, timestamps, `participants` (JSONB), content/transcript, `external_interaction_id`. |
| **3.2 Extracted entities** | **Yes** | Stored on `crm_records` + `custom_fields` JSONB. |
| **3.3 CRM mapping** | **Partial** | Account / Contact / Deal IDs on records; `Deal.stage`, `Deal.intent_snapshot`, `Contact.email` where populated by mapping. |
| **3.4 Data flow** | **Yes** | Documented in code path `ingestion_pipeline.run_transcript_pipeline`. |
| **3.5 Security** | **Partial** | TLS depends on deployment; **append-only audit log** (`audit_logs`) on successful ingestion. Full encryption-at-rest, RBAC, GDPR tooling **not** implemented as product features. |
| **3.6 Data quality** | **Partial** | Deduplication is **informational** (counts prior rows with same `external_interaction_id`); validation via Pydantic; no automated accuracy scoring. |

## Extras (implemented but not spelled out in the short BRD text)

- **Groq** as the primary LLM for extraction and mapping (spec may have assumed another vendor).
- **Whisper** local/offline transcription path for audio.
- **Heuristic fallback** when the LLM is unavailable (mapping / extraction paths as coded).
- **REST API surface**: OpenAPI at `/docs`; CRM bulk delete for local reset; mapping method stored per record (`llm`, `rules`, etc.).
- **React UI** (`crm-ui`): upload, analytics chart, CRM records browser, **Timeline** page, **Interaction insights** card on the dashboard.

## Document maintenance

- Primary requirements remain in `AI_Interaction_Mining_BRD_FRD_DRD.docx`. This file is the **implementation status** companion; update it when behavior changes.
