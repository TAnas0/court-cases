import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import task

# Setup logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG tasks
default_args = {
    "owner": "anas",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

@task
def validate_raw():
    """
    Step 0: Validate Raw JSON data against the JSON Schema before pipeline execution.
    """
    logger.info("--- Step 0: Schema Validation ---")
    from src.pipeline.validate import validate_data
    validate_data("output/*/*/*.json", "src/pipeline/schema.json", sample_size=5)

@task
def bronze_layer():
    """
    Step 1: Ingest raw JSONL files and save them to the Bronze Parquet layer.
    """
    logger.info("--- Step 1: Bronze Layer ---")
    from src.pipeline.bronze import build_bronze_layer
    build_bronze_layer("output/*/*/*.json", "output/bronze/cases.parquet")

@task
def silver_layer():
    """
    Step 2: Clean, deduplicate, and anonymize Bronze Parquet data to the Silver layer.
    """
    logger.info("--- Step 2: Silver Layer ---")
    from src.pipeline.silver import build_silver_layer
    build_silver_layer("output/bronze/cases.parquet", "output/silver/cases.parquet")

@task
def gold_layer():
    """
    Step 3: Aggregate Silver data into structured, analytical Gold tables.
    """
    logger.info("--- Step 3: Gold Layer ---")
    from src.pipeline.gold import build_gold_layer
    build_gold_layer("output/silver/cases.parquet", "output/gold/court_analytics.duckdb")

# Define the DAG
with DAG(
    "medallion_pipeline",
    default_args=default_args,
    description="Standardized Medallion Architecture (Bronze -> Silver -> Gold) Pipeline using DuckDB",
    schedule=None,  # Manual execution or triggered after scraper
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    
    # Define execution order
    validate_raw() >> bronze_layer() >> silver_layer() >> gold_layer()
