# Virginia Court Case Analytics Pipeline

> An end-to-end data engineering project that scrapes, processes, and analyses millions of criminal court records from Virginia's Online Case Information System (OCIS 2.0).

---

## Architecture

```mermaid
flowchart LR
    A[OCIS API\nVA Courts] -->|Airflow DAG\nscrape_data| B[Bronze Layer\nRaw JSONL\noutput/bronze/]
    B -->|silver.py\nDedupe · PII-hash · Type-cast| C[Silver Layer\nParquet\noutput/silver/]
    C -->|gold.py\nAggregations| D[Gold Layer\nDuckDB\noutput/gold/]
    D -->|Streamlit| E[Analytics\nDashboard]
    D -->|Duck-UI| F[SQL Explorer]
```

The pipeline follows the **Medallion Architecture** (Bronze → Silver → Gold):

| Layer | Format | Purpose |
|-------|--------|---------|
| **Bronze** | Parquet | Raw data ingested 1-to-1 from JSONL — full fidelity, no mutations |
| **Silver** | Parquet | Deduplicated, cleaned, PII-hashed with SHA-256 |
| **Gold** | DuckDB | Pre-aggregated analytics tables, served to dashboards |

---

## Design Decisions

**Why Airflow?** Airflow provides robust scheduling, retry semantics, and a UI for monitoring long scrape runs that can span days. The DAG's `start_date` / `end_date` params make backfilling trivial.

**Why DuckDB?** DuckDB is an embedded OLAP engine — no server to manage, reads Parquet natively, and can run sub-second analytical queries over millions of rows on a laptop. It is the ideal "Gold layer" for a portfolio-scale project.

**Why the Medallion pattern?** Each layer is independently replayable. If the Silver transformation logic changes, Bronze is untouched and Silver can be recomputed without re-scraping. This mirrors production data-lake patterns (Databricks / Delta Lake) at zero cost.

**Rate limiting + retry** All HTTP requests go through a `RateLimitedCachedSession` (≤ 2 req/s, hard cap 60/min) backed by `requests-ratelimiter`. Transient failures automatically retry up to 3× with exponential backoff via `tenacity`.

---

## Quick Start

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- Python 3.11+ (for local runs / tests)

### 1 — Clone and configure

```bash
git clone https://github.com/tanas0/court-cases.git
cd court-cases
cp .env.example .env          # edit DATABASE_URL at minimum
```

### 2 — Start the stack

```bash
# First-time only: creates required directories and sets AIRFLOW_UID
bash setup_airflow.sh

docker compose build
docker compose up -d
```

Airflow UI → http://localhost:8080 (credentials: `airflow / airflow`)  
Jupyter Lab → http://localhost:8888 *(dev override only)*  
DuckDB UI → http://localhost:5522 *(dev override only)*

> **Production** — exclude dev services by running:
> ```bash
> docker compose -f docker-compose.yaml up -d
> ```

### 3 — Trigger a scrape

In the Airflow UI, unpause the `court_case_scraper_workflow` DAG and trigger it with your desired date range:

```json
{ "start_date": "2024-05-01", "end_date": "2024-05-31" }
```

### 4 — Run the Medallion pipeline

```bash
# Inside the Airflow worker, or locally with the venv active:
python -m src.pipeline.orchestrator
```

This runs Validation → Bronze → Silver → Gold and produces `output/gold/court_analytics.duckdb`.

### 5 — Launch the dashboard

```bash
streamlit run src/analysis/app.py
# Or set DUCKDB_PATH to point at the generated file:
DUCKDB_PATH=output/gold/court_analytics.duckdb streamlit run src/analysis/app.py
```

---

## Pipeline Overview

```
Raw JSONL (output/YYYY/MM/DD/*.json)
    │
    ▼  validate.py   — schema validation against schema.json
    │
    ▼  bronze.py     — ingest raw JSONL → Parquet (no mutations)
    │
    ▼  silver.py     — deduplicate · hash PII · enforce dtypes · clean
    │
    ▼  gold.py       — aggregate into DuckDB analytical tables
```

### Silver transformations

- Deduplicates on composite key `(case_number, code_section, is_appeal, commenced_by)`.
- Hashes defendant and participant names with SHA-256 before storage.
- Casts all date columns to `date` / `datetime` types.
- Maps boolean flags (`Y`/`N` → `True`/`False`).

### Gold tables

| Table | Description |
|-------|-------------|
| `case_summary` | One row per case with disposition, financial totals, sentence days |
| `court_efficiency` | Per-court case volume, avg time-to-disposition |
| `charge_stats` | Dismissal rates and conviction rates per charge code |

---

## Running Tests

```bash
# With the virtualenv active and DATABASE_URL set:
DATABASE_URL=postgresql://user:pass@localhost:5432/virginia_court_cases \
  python -m pytest -v
```

The test suite covers DAG import validation and model relationship correctness.

---

## Project Structure

```
court-cases/
├── dags/
│   └── court_case_scraper.py   # Airflow DAG: scrape → ingest
├── src/
│   ├── main.py                 # Core scraper entry point
│   ├── search.py               # Search API client (with retry)
│   ├── details.py              # Case detail API client (with retry)
│   ├── utils.py                # Rate-limited session, helpers
│   ├── analysis/
│   │   ├── app.py              # Streamlit dashboard
│   │   └── main.py             # Statistical analysis CLI
│   ├── database/
│   │   └── main.py             # SQLAlchemy engine + session
│   ├── models/                 # SQLAlchemy ORM models
│   ├── pipeline/
│   │   ├── bronze.py           # Raw → Parquet ingestion
│   │   ├── silver.py           # Cleaning & deduplication
│   │   ├── gold.py             # Aggregation → DuckDB
│   │   ├── validate.py         # Schema validation
│   │   └── orchestrator.py     # Runs the full pipeline
│   └── services/
│       └── case.py             # DataFrame normalisation + DB upsert
├── output/
│   ├── bronze/                 # Raw Parquet files
│   ├── silver/                 # Cleaned Parquet files
│   └── gold/
│       └── court_analytics.duckdb
├── docker-compose.yaml         # Production Airflow stack
├── docker-compose.override.yml # Dev extras (Jupyter, DuckDB UI)
├── pyproject.toml              # Single source of truth for deps
└── .env.example                # All required environment variables
```

---

## Future Work

- [ ] **1.7** Clean up `.gitignore` and remove committed artefacts (`app.log`, `demo_cache1.sqlite`)
- [ ] **1.8** Fix SSL verification (currently `verify=False`)
- [ ] **1.9** Disable `echo=True` on SQLAlchemy engine in production
- [ ] **2.2** Add pipeline tests (Bronze/Silver/Gold unit tests)
- [ ] **2.3** Fix existing test suite (currently requires `DATABASE_URL` at collection time)
- [ ] **2.4** Add dedicated Medallion Pipeline DAG to Airflow
- [ ] **2.5** Add Great Expectations or Pandera schema validation
- [ ] **2.8** Upgrade SQLAlchemy to 2.x (`mapped_column`, `DeclarativeBase`)
- [ ] **3.x** Publish dashboard to Streamlit Community Cloud
