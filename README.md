# AI Data Factory

Production-grade data pipeline that transforms web content into high-quality LLM training data. Scrape URLs, clean and chunk content, generate training examples via LLM, run quality control, and export in standard formats.

```
Spider → Refiner → Factory → Inspector → Shipper
(scrape)  (clean)   (generate)  (QC)       (export)
```

## Architecture

```
Docker Compose (4 containers)

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
```

- **Frontend → API:** REST (CRUD, job management, downloads)
- **API → Worker:** Redis Queue (job dispatch)
- **Worker → API:** Redis Pub/Sub (progress updates)
- **API → Frontend:** SSE (real-time progress streaming)
- **Storage:** SQLite (WAL-mode) + filesystem

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key (for training data generation)

### 1. Clone and configure

```bash
git clone <repo-url> && cd AIDataFactory
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

### 3. Open the dashboard

- **Dashboard:** http://localhost:3000
- **API docs:** http://localhost:8000/docs (Swagger UI)
- **Health check:** http://localhost:8000/api/health

### Local Development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,pipeline]"
playwright install chromium

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start API server
cd src && uvicorn main:app --reload --port 8000

# Start worker (separate terminal)
cd src && python -m worker
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Pipeline Stages

| Stage | Module | Description |
|-------|--------|-------------|
| Spider | `ingestion.py` | Scrapes URLs via httpx + Playwright fallback, respects robots.txt |
| Refiner | `processing.py` | Extracts content (trafilatura), chunks (tiktoken), deduplicates (MinHash LSH) |
| Factory | `generation.py` | Generates training examples via LLM with Jinja2 prompt templates |
| Inspector | `quality.py` | Quality checks: toxicity (detoxify), readability (textstat), format, duplicates |
| Shipper | `export.py` | Exports to JSON/JSONL/CSV with dataset cards |

## Prompt Templates

Built-in templates for training data generation:

| Template | Output Format |
|----------|---------------|
| `qa_generation` | Question-answer pairs |
| `summarization` | Summary pairs |
| `classification` | Label-text pairs |
| `instruction_following` | Instruction-response pairs |

Custom templates can be added — see [CONTRIBUTING.md](CONTRIBUTING.md).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET/POST | `/api/projects` | List / create projects |
| GET/DELETE | `/api/projects/{id}` | Get / delete project |
| POST | `/api/projects/{id}/jobs` | Create pipeline job |
| GET | `/api/jobs/{id}` | Get job status |
| POST | `/api/jobs/{id}/cancel` | Cancel running job |
| GET | `/api/jobs/{id}/stream` | SSE progress stream |
| GET | `/api/jobs/{id}/exports` | List job exports |
| GET | `/api/exports/{id}/download` | Download export file |
| GET | `/api/exports/{id}/card` | Dataset card (markdown) |
| GET | `/api/stats/overview` | Aggregate statistics |
| GET | `/api/stats/costs` | Cost tracking |
| GET | `/api/templates` | List prompt templates |
| GET | `/api/templates/{type}` | Template details |

Full interactive docs at `/docs` (Swagger UI).

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///db/factory.db` | Database connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OPENAI_API_KEY` | — | Required for LLM generation |
| `GENERATION_MODEL` | `gpt-4o-mini` | LLM model (via litellm) |
| `GENERATION_MAX_CONCURRENT` | `5` | Concurrent LLM calls |
| `GENERATION_EXAMPLES_PER_CHUNK` | `3` | Examples per text chunk |
| `QUALITY_MIN_SCORE` | `0.7` | Minimum QC score (0-1) |
| `SCRAPING_MAX_CONCURRENT` | `3` | Concurrent scrape requests |
| `SCRAPING_RATE_LIMIT` | `2.0` | Seconds between requests |

## Project Structure

```
AIDataFactory/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py                 # FastAPI app
│       ├── worker.py               # Redis queue consumer
│       ├── config.py               # Pydantic settings
│       ├── api/routes/             # REST endpoints
│       ├── db/                     # SQLAlchemy models + database
│       ├── schemas/                # Pydantic request/response schemas
│       ├── clients/                # Redis + LLM client wrappers
│       ├── pipeline/
│       │   ├── orchestrator.py     # Stage coordinator
│       │   ├── stages/             # 5 pipeline stages
│       │   └── quality_checks/     # QC checker plugins
│       └── templates/              # Jinja2 prompt templates
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── app/                    # Next.js pages
        ├── components/             # Dashboard + UI components
        ├── hooks/                  # SSE + data fetching hooks
        └── lib/                    # API client + types
```

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Redis, Playwright, trafilatura, tiktoken, litellm, detoxify, textstat

**Frontend:** Next.js 15, Tailwind v4, ShadCN UI, Recharts

**Infrastructure:** Docker Compose, Redis 7, SQLite (WAL-mode)

## License

MIT
