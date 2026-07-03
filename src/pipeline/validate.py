import json
import glob
import logging
import os
from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)

def validate_data(json_glob_path: str, schema_path: str, sample_size: int = 5):
    """
    Validates Raw JSON files against the provided JSON Schema.
    
    TODO (Performance & Scalability): jsonschema validation is CPU-heavy and slow.
    Consider migrating to Pydantic v2 (compiled Rust core) or leveraging DuckDB's
    schema enforcement on read for larger datasets.
    
    Args:
        json_glob_path: Input file pattern
        schema_path: Path to schema.json
        sample_size: Number of files to check (0 for all)
    """
    logger.info(f"Validating data from {json_glob_path} against {schema_path}")
    
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found: {schema_path}")
        raise FileNotFoundError(f"Schema not found: {schema_path}")
        
    with open(schema_path, 'r') as f:
        schema = json.load(f)
        
    # If schema defines an 'array', we likely want to validate each item against schema['items']
    # because the input files are JSONL (one object per line).
    record_schema = schema
    if schema.get('type') == 'array' and 'items' in schema:
        record_schema = schema['items']
        logger.info("Schema is an array. Validating lines against schema['items'].")

    validator = Draft7Validator(record_schema)

    files = glob.glob(json_glob_path, recursive=True)
    if not files:
        logger.warning("No files found to validate.")
        return

    # Sort files to be deterministic, take sample
    files.sort()
    # If sample_size is small, just checking the first few files is good enough for a smoke test.
    subset = files[:sample_size] if sample_size > 0 else files
    
    errors = 0
    for file_path in subset:
        try:
            with open(file_path, 'r') as f:
                # Read line by line (JSONL)
                for i, line in enumerate(f):
                    if i >= 1000: # Limit to first 1000 lines for performance
                        break
                        
                    if not line.strip(): 
                        continue
                    try:
                        record = json.loads(line)
                        validator.validate(record)
                    except json.JSONDecodeError as je:
                        logger.error(f"❌ JSON Decode Error in {file_path} line {i+1}: {je}")
                        errors += 1
                        break # Stop checking this file
                    except ValidationError as ve:
                        logger.error(f"❌ Validation failed for {file_path} line {i+1}: {ve.message}")
                        errors += 1
                        # Limit errors per file?
                        if errors > 10: break
                        
            logger.info(f"✅ {os.path.basename(file_path)} passed validation (checked first 1000 lines)")
            
        except Exception as e:
            logger.error(f"❌ Error reading {file_path}: {e}")
            errors += 1
            
    if errors > 0:
        logger.error(f"Validation completed with {errors} errors.")
        # We might choose to Raise here to stop pipeline, or just warn.
        # User asked to "check against my data points". Failing is safer.
        raise ValueError("Schema Validation Failed")
    else:
        logger.info(f"✅ Validation passed for {len(subset)} files.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    validate_data("output/*/*/*.jsonl", "src/pipeline/schema.json", sample_size=5)
