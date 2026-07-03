import duckdb
import os
import logging

logger = logging.getLogger(__name__)

def build_silver_layer(bronze_path: str, output_path: str):
    """
    Transforms Bronze data to Silver:
    1. Deduplicates (latest by caseNumber/hearingDate)
    2. Hashes PII (Defendant Name, Participant Names)
    3. Type casting
    """
    logger.info(f"Starting Silver Layer build from {bronze_path}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    con = duckdb.connect()
    
    try:
        # 1. Define PII Hashing & Type Casting Logic
        # We use SHA256 for simple hashing as requested.
        # Note: We are losing the original names here.
        
        # We handle caseParticipant array using list_transform
        
        query = f"""
        COPY (
            WITH raw_data AS (
                SELECT * FROM read_parquet('{bronze_path}')
            ),
            deduplicated AS (
                -- Deterministic Deduplication:
                -- Keep the latest record for each caseNumber/hearingDate combination by
                -- ordering by source_file DESC (since source_file contains the YYYY/MM/DD path).
                SELECT DISTINCT ON (caseNumber, hearingDate) *
                FROM raw_data
                ORDER BY caseNumber, hearingDate, source_file DESC
            )
            SELECT 
                qualifiedFips,
                courtLevel,
                divisionType,
                caseNumber,
                formattedCaseNumber,
                
                -- HASH PII: Defendant Name (Cryptographically secure SHA-256)
                sha256(name) as defendant_name_hash,
                
                -- Standardize Dates
                -- TODO (Data Quality): Implement Silver-layer validation rules / assertions.
                -- E.g., assert that offense_date <= hearing_timestamp::DATE and that
                -- financial information amounts are non-negative.
                try_strptime(offenseDate, '%m/%d/%Y')::DATE as offense_date,
                
                chargeAmended,
                codeSection,
                chargeDesc,
                caseType,
                
                -- Standardize Hearing Timestamp
                try_strptime(hearingDate, '%m/%d/%Y, %I:%M %p') as hearing_timestamp,
                
                -- Localities (nested access)
                locality.localityName as locality_name,
                
                -- HASH PII: Participants (Cryptographically secure SHA-256)
                -- We iterate over the list and hash the race/gender? No, keep race/gender, Hash Names.
                -- Participant struct structure varies, assuming standard fields.
                -- CAUTION: Complex nested transformation in DuckDB SQL can be verbose.
                -- For now, we will KEEP demographics but HASH specific PII fields if accessible.
                -- If we can't easily deep-transform the struct, we might drop the PII parts or hash the whole sub-struct.
                -- Let's attempt to reconstruct the struct with hashed names.
                
                list_transform(caseParticipant, x -> struct_pack(
                    participant_hash := sha256(x.contactInformation.personName.fullName), 
                    role := x.participantCode,
                    race := x.personalDetails.race,
                    gender := x.personalDetails.gender
                )) as participants_anonymized,
                
                financialInformation,
                caseHearing,
                disposition,
                
                -- Meta
                'hashed_sha256' as anonymization_method
                
            FROM deduplicated
        ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
        """
        
        logger.info(f"Executing DuckDB transformation...")
        con.execute(query)
        logger.info(f"Silver Layer successfully saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to build Silver Layer: {e}")
        # If the complex struct transformation fails, we might need a simpler fallback
        logger.error("Tip: Check if 'caseParticipant' structure matches the assumptions.")
        raise
    finally:
        con.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BRONZE_FILE = "output/bronze/cases.parquet"
    OUTPUT_FILE = "output/silver/cases.parquet"
    
    if os.path.exists(BRONZE_FILE):
        build_silver_layer(BRONZE_FILE, OUTPUT_FILE)
    else:
        logger.warning(f"Bronze file {BRONZE_FILE} not found. Run bronze pipeline first.")
