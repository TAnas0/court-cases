import logging
import sys
import os
from src.pipeline.bronze import build_bronze_layer
from src.pipeline.silver import build_silver_layer
from src.pipeline.gold import build_gold_layer
from src.pipeline.validate import validate_data

# Configuration
INPUT_GLOB = "output/*/*/*.json"
SCHEMA_PATH = "src/pipeline/schema.json"
BRONZE_PATH = "output/bronze/cases.parquet"
SILVER_PATH = "output/silver/cases.parquet"
GOLD_PATH = "output/gold/court_analytics.duckdb"

def run_pipeline():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("Orchestrator")
    
    logger.info("🚀 Starting Medallion Data Pipeline")
    
    try:
        # Step 0: Validation
        logger.info("--- Step 0: Schema Validation ---")
        validate_data(INPUT_GLOB, SCHEMA_PATH, sample_size=5)

        # Step 1: Bronze
        logger.info("--- Step 1: Bronze Layer ---")
        build_bronze_layer(INPUT_GLOB, BRONZE_PATH)
        
        # Step 2: Silver
        logger.info("--- Step 2: Silver Layer ---")
        if os.path.exists(BRONZE_PATH):
            build_silver_layer(BRONZE_PATH, SILVER_PATH)
        else:
            logger.error("Bronze path missing, skipping Silver.")
            sys.exit(1)
            
        # Step 3: Gold
        logger.info("--- Step 3: Gold Layer ---")
        if os.path.exists(SILVER_PATH):
            build_gold_layer(SILVER_PATH, GOLD_PATH)
        else:
            logger.error("Silver path missing, skipping Gold.")
            sys.exit(1)
            
        logger.info("✅ Pipeline Completed Successfully")
        
    except Exception as e:
        logger.error(f"❌ Pipeline Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
