# Medallion Data Pipeline

This directory contains the ETL pipeline for processing Virginia Court Case data. It follows the **Medallion Architecture**:

## Layers

### 0. Validation (`validate.py`)
- **Input**: Raw JSONL files (`output/YYYY/MM/DD/*.json`).
- **Action**: Validates a sample of input files against `schema.json`.
- **Goal**: Ensure upstream data matches expected structure before ingestion.

### 1. Bronze Layer (`bronze.py`)
- **Input**: Raw JSONL files.
- **Output**: `output/bronze/cases.parquet`.
- **Action**: Ingests raw data 1:1 into Parquet format using DuckDB. Preserves full fidelity.

### 2. Silver Layer (`silver.py`)
- **Input**: Bronze Parquet.
- **Output**: `output/silver/cases.parquet`.
- **Action**:
    - **Deduplication**: Retains unique cases.
    - **PII Hashing**: Hashes Defendant and Participant names (SHA256) for privacy.
    - **Cleaning**: Enforces data types and standardizes fields.

### 3. Gold Layer (`gold.py`)
- **Input**: Silver Parquet.
- **Output**: `output/gold/court_analytics.duckdb`.
- **Action**: Aggregates data for business analytics (Metric summaries, efficiency stats).

## Usage

To run the entire pipeline (Validation -> Bronze -> Silver -> Gold):

```bash
python -m src.pipeline.orchestrator
```

