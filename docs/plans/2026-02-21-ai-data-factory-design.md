# AI Data Factory — Design Document

**Date:** 2026-02-21
**Status:** Approved
**Author:** Archie (Lead Architect Agent)
**Product Owner:** Kevin

---

## 1. Overview

The AI Data Factory is a production-grade data pipeline that transforms web content into high-quality training data for LLMs. It scrapes URLs, cleans and chunks the content, generates training examples via LLM APIs, runs quality control, and exports the results in standard formats.

**Target User:** Solo developer / small team building LLM training datasets.
**Deployment:** Local Docker Compose (v1), cloud-deployable later.

---

## 2. Discovery Decisions

| Decision | Answer | Rationale |
|---|---|---|
| Primary Use Case | All formats equally | Flexible template system required |
| Hosting | Local Docker Compose | Zero server cost, full control |
| LLM Provider | OpenAI GPT-4o-mini (via litellm) | Best cost/quality ratio for batch generation |
| Scraping Targets | Mixed sources (docs, blogs, news, forums) | Robust fallback chain needed |
| UI Language | English | International-ready, standard for dev tools |
| v1 Scope | Full pipeline + dashboard | End-to-end product |

---

## 3. Architecture

**Pattern:** Worker-Separation (API + Worker via Redis)

```
Docker Compose Network (4 containers)

  frontend (Next.js 15, port 3000)
      │
      ▼ REST
  backend-api (FastAPI, port 8000)
      │                    │
      │ Redis Queue        │ Redis Pub/Sub
      ▼                    ▼
  worker (Pipeline Engine)
      │
      ▼
  redis (port 6379)

  Shared Volumes:
  - ./data/ → /app/data (raw, processed, generated, exports)
  - ./db/   → /app/db   (SQLite WAL-mode)
```

### Communication:
- **Frontend → API:** REST (CRUD, job management, downloads)
- **API → Worker:** Redis Queue (job dispatch)
- **Worker → API:** Redis Pub/Sub (progress updates, results)
- **API → Frontend:** SSE (real-time progress)
- **Shared State:** SQLite (WAL-mode for concurrent reads) + filesystem

### Container Specs:

| Container | Base Image | Role |
|---|---|---|
| `frontend` | `node:22-alpine` | Next.js 15 App Router |
| `backend-api` | `python:3.12-slim` | FastAPI + uvicorn |
| `worker` | `python:3.12-slim` + Playwright | Pipeline engine, same codebase as API |
| `redis` | `redis:7-alpine` | Message broker, vanilla config |

---

## 4. Pipeline Engine

Each stage implements a common interface (`PipelineStage` protocol) with `process()` and `validate_input()` methods.

### Stage 1: Spider (Ingestion)
- **Input:** `List[URL]` + `ScrapeConfig`
- **Output:** `List[RawDocument(url, html, metadata, status)]`
- httpx first (fast, static pages), Playwright fallback (JS-heavy pages)
- Respects `robots.txt` and `Crawl-Delay`
- Rate limiting: configurable per domain (default: 2 req/sec)
- Retry: 3 attempts with exponential backoff
- Metadata extraction: title, language, publication date

### Stage 2: Refiner (Processing)
- **Input:** `List[RawDocument]`
- **Output:** `List[ProcessedDocument(chunks, metadata)]`
- Content extraction via trafilatura
- Recursive chunking (default: 512 tokens)
- Token counting via tiktoken (cl100k_base)
- Language detection per document
- Deduplication at chunk level (MinHash)

### Stage 3: Factory (Generation)
- **Input:** `List[Chunk]` + `GenerationConfig`
- **Output:** `List[TrainingExample(input, output, metadata, token_count, cost)]`
- litellm as LLM abstraction layer
- Jinja2-based prompt templates
- Built-in templates: Q&A, Summarization, Classification, Instruction-Following
- Batch processing: configurable concurrency (default: 5)
- Cost tracking: per-request token counting + model pricing table

### Stage 4: Inspector (Quality Control)
- **Input:** `List[TrainingExample]`
- **Output:** `List[ScoredExample(example, scores, passed)]`
- Toxicity check: detoxify
- Readability: textstat (Flesch-Kincaid)
- Format validation: schema compliance
- Duplicate detection: cosine similarity
- Configurable threshold (default: 0.7)
- Filtered examples stored for analysis, not discarded

### Stage 5: Shipper (Export)
- **Input:** `List[ScoredExample]` + `ExportConfig`
- **Output:** `ExportResult(file_path, stats, dataset_card)`
- Formats: JSON, JSONL, CSV (v1)
- Auto-generated dataset card (Markdown)
- Versioning: timestamp-based per export
- Only QC-passed examples exported

### Orchestrator:
- Sequential stage execution: Spider → Refiner → Factory → Inspector → Shipper
- Partial results: if stage N fails at item 47/100, items 1-46 proceed
- Progress updates per stage and per item via Redis Pub/Sub → SSE
- Job states: `pending → running → stage_N → completed | failed`

---

## 5. Data Model

SQLite with SQLAlchemy (async via aiosqlite). WAL-mode enabled.

### Tables:

**projects**
- id, name, description, config (JSON), created_at, updated_at

**jobs**
- id, project_id (FK), status, stage, config (JSON), progress, error, cost_total, started_at, completed_at

**raw_documents**
- id, job_id (FK), url, html_path (file reference), title, language, scrape_status, created_at

**chunks**
- id, document_id (FK), content, token_count, chunk_index, metadata (JSON), created_at

**training_examples**
- id, chunk_id (FK), job_id (FK), template_type, input_text, output_text, model_used, token_count, cost, quality_score, quality_details (JSON), passed_qc, created_at

**exports**
- id, job_id (FK), format, file_path, record_count, version, dataset_card, created_at

### Design decisions:
- Raw HTML stored as files (can be multi-MB), DB stores path only
- JSON columns for flexible config/metadata
- Cost tracked at both job level (overview) and example level (granular)
- No DB-level FK enforcement (SQLite performance), validated in code

---

## 6. API Design

FastAPI with auto-generated OpenAPI/Swagger docs.

### Endpoints:

```
Health
  GET  /health

Projects
  POST /api/projects
  GET  /api/projects
  GET  /api/projects/{id}
  PUT  /api/projects/{id}
  DEL  /api/projects/{id}

Jobs
  POST /api/projects/{id}/jobs          (start pipeline)
  GET  /api/projects/{id}/jobs
  GET  /api/jobs/{id}
  POST /api/jobs/{id}/cancel
  GET  /api/jobs/{id}/logs

Exports
  GET  /api/jobs/{id}/exports
  GET  /api/exports/{id}/download
  GET  /api/exports/{id}/card

Templates
  GET  /api/templates
  GET  /api/templates/{type}

Real-time
  GET  /api/jobs/{id}/stream            (SSE)

Stats
  GET  /api/stats/overview
  GET  /api/stats/costs
```

### Job Start Payload:
All config values have sensible defaults. Minimal payload: `{"urls": [...]}`

```json
{
  "urls": ["https://example.com/article"],
  "config": {
    "scraping": { "max_concurrent": 3, "use_playwright": "auto", "respect_robots_txt": true },
    "processing": { "chunk_size": 512, "chunk_strategy": "recursive" },
    "generation": { "template": "qa", "model": "gpt-4o-mini", "examples_per_chunk": 3, "max_concurrent_llm": 5 },
    "quality": { "min_score": 0.7, "checks": ["toxicity", "readability", "format"] },
    "export": { "format": "jsonl" }
  }
}
```

---

## 7. Dashboard UI

**Stack:** Next.js 15 (App Router), Tailwind CSS v4, ShadCN UI, Recharts
**Design:** JARVIS HUD-style with Glasmorphism

### Design Language:
- **Glasmorphism:** Semi-transparent panels with `backdrop-blur`, subtle glowing borders
- **Color palette:** Dark background (#0a0a0f), Cyan/Teal (#00d4ff) primary accent, warm Orange for warnings/costs
- **Pipeline visualization:** Animated data flow between 5 stages (particle/dot animation)
- **Typography:** JetBrains Mono for data/numbers, Inter for labels
- **Glow effects:** Subtle neon glows on active elements, pulsing progress bars
- **HUD elements:** Angular brackets around sections, hexagonal status badges, scan-line animations

### Pages:

```
/                       → Dashboard Home (stats overview)
/projects               → Project list
/projects/[id]          → Project detail with job list
/projects/[id]/new-job  → Start new pipeline job (URL input + config)
/jobs/[id]              → Job detail (live progress, stage status)
/jobs/[id]/results      → Results + quality report
/exports                → All exports (download center)
/settings               → API keys, default configuration
```

### Dashboard Home:
- Stats cards: total jobs, active jobs, generated examples, total cost
- Active jobs: live progress bars with stage indicator
- Recent exports: quick-download links
- Cost chart: last 7 days (Recharts bar chart)

### Job Detail:
- Pipeline visualization: 5 stages as horizontal steps, current stage highlighted with glow
- Progress: per-stage progress bar with item counter
- Live log: SSE-fed log stream (filterable by level)
- Quality summary: donut chart (passed vs filtered), score distribution
- Cost breakdown: per-stage costs, token usage

### New Job:
- URL input: textarea (one per line) or bulk upload (txt/csv)
- Config panels: accordion sections per stage
- Presets: "Quick Start" (all defaults) vs "Custom"
- Cost estimation before start

---

## 8. Tech Stack Summary

| Component | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12+) |
| Pipeline Engine | Custom async pipeline + asyncio |
| Database | SQLite (aiosqlite, WAL-mode) |
| Message Broker | Redis 7 |
| Web Scraping | Playwright + httpx |
| Text Processing | trafilatura + BeautifulSoup4 |
| Chunking | tiktoken + langchain text_splitter |
| LLM Integration | litellm (multi-provider) |
| Prompt Templates | Jinja2 |
| Quality Control | detoxify + textstat + custom |
| Frontend | Next.js 15 + Tailwind v4 + ShadCN |
| Charts | Recharts |
| Real-time | SSE (Server-Sent Events) |
| Containerization | Docker Compose |

---

## 9. Build Order

1. **Foundation:** FastAPI + SQLite + Config + Redis connection + Health endpoint + Logging
2. **Spider:** URL scraping with httpx/Playwright fallback, metadata extraction, rate limiting
3. **Refiner:** HTML → clean text (trafilatura), recursive chunking, token counting
4. **Factory:** litellm integration, template system, Q&A + Summarization generation, cost tracking
5. **Inspector:** Toxicity + readability + format validation + duplicate detection, scoring
6. **Shipper:** JSON/JSONL/CSV export, dataset cards, versioning
7. **Orchestrator:** End-to-end pipeline coordination, job management, SSE progress, error recovery
8. **Dashboard:** JARVIS HUD UI with all pages, live progress, quality reports, cost overview
9. **Docker & Polish:** Docker Compose, error handling review, performance, README

---

## 10. v2 Roadmap (Not in Scope for v1)

- HuggingFace Hub integration (direct upload)
- Scheduled/recurring scraping jobs
- External API endpoints for third-party integration
- Multi-user support
- Advanced analytics & insights
- Parquet export format
- Webhook notifications
- Light mode theme option
- Plugin system for new sources/formats/QC checks
