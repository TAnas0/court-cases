import duckdb
import os
import glob
import logging

logger = logging.getLogger(__name__)

def build_bronze_layer(json_glob_path: str, output_path: str):
    """
    Ingests raw JSONL files and converts them 1:1 to a Bronze Parquet file.
    
    TODO (Scalability): This performs a full reload from scratch every execution.
    For production-grade workloads, partition the Parquet files (e.g., PARTITION_BY)
    and implement incremental loading based on file modification times or run manifests.
    
    Args:
        json_glob_path: Glob pattern for matching input JSON files (e.g., 'output/*/*/*.json')
        output_path: Path to write the output Parquet file
    """
    logger.info(f"Starting Bronze Layer ingestion from {json_glob_path}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Check if we have source files
    files = glob.glob(json_glob_path, recursive=True)
    if not files:
        logger.warning(f"No JSON files found matching {json_glob_path}. Skipping Bronze build.")
        return

    con = duckdb.connect()
    try:
        # Schema-on-read using DuckDB's powerful JSON auto-detection
        # We preserve the structure exactly as is.
        query = f"""
        COPY (
            SELECT * FROM read_json_auto('{json_glob_path}', union_by_name=true)
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
        """
        
        logger.info(f"Executing DuckDB COPY to {output_path}...")
        con.execute(query)
        logger.info(f"Bronze Layer successfully saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to build Bronze Layer: {e}")
        raise
    finally:
        con.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Default paths for testing/running directly
    # Assuming code run from project root
    INPUT_GLOB = "output/*/*/*.json" 
    OUTPUT_FILE = "output/bronze/cases.parquet"
    
    build_bronze_layer(INPUT_GLOB, OUTPUT_FILE)
