import duckdb
import os
import sys


def convert_json_to_parquet(input_glob, output_path):
    """
    Converts raw nested JSONL files to a flattened Parquet file using DuckDB.
    """
    # Connect to DuckDB (in-memory)
    con = duckdb.connect()

    # Intricacy: We use JSON dot notation to flatten structs during the load.
    # We also use strptime to convert the custom hearing date format to a native TIMESTAMP.
    query = f"""
    COPY (
        SELECT 
            qualifiedFips,
            courtLevel,
            divisionType,
            caseNumber,
            formattedCaseNumber,
            name as defendant_name,
            -- Convert dates to standard format
            strptime(offenseDate, '%m/%d/%Y')::DATE as offense_date,
            chargeAmended,
            codeSection,
            chargeDesc,
            caseType,
            strptime(hearingDate, '%m/%d/%Y, %I:%M %p') as hearing_timestamp,
            locality.localityName as locality_name,
            locality.localityCode as locality_code,
            caseCategory.caseCategoryCode as category_code,
            caseCategory.criminalCaseIndicator = 'Y' as is_criminal,
            caseActiveIndicator.value = 'Y' as is_active,
            disposition.dispositionInfo.dispositionText as disposition_text,
            disposition.dispositionInfo.dispositionDate as disposition_date,
            -- Extract primary defendant demographics (first participant where participantCode='DEF')
            -- We use a list filter + [1] approach or just unnesting. 
            -- For the silver layer, we'll flatten the first primary defendant for convenience.
            list_filter(caseParticipant, x -> x.participantCode = 'DEF')[1].personalDetails.race as race,
            list_filter(caseParticipant, x -> x.participantCode = 'DEF')[1].personalDetails.gender as gender,
            list_filter(caseParticipant, x -> x.participantCode = 'DEF')[1].attorneyDetails[1].judicialOfficialCategoryText as attorney_type,
            financialInformation.fines.amount.decimal as fine_amount,
            financialInformation.costs.amount.decimal as cost_amount,
            -- Keep nested structures for full fidelity
            caseParticipant as participants,
            caseHearing as hearings
        FROM read_json_auto('{input_glob}')
    ) TO '{output_path}' (FORMAT PARQUET);
    """

    try:
        print(f"Processing: {input_glob}")
        con.execute(query)
        print(f"Success: Saved to {output_path}")
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure Silver layer directory exists
    os.makedirs("output/silver/2024/05", exist_ok=True)

    input_path = "output/2024/05/*.json"
    output_path = "output/silver/2024/05/cases.parquet"

    convert_json_to_parquet(input_path, output_path)
