import os
import json
import pytest
import duckdb
from src.pipeline.bronze import build_bronze_layer
from src.pipeline.silver import build_silver_layer


@pytest.fixture
def sample_bronze_parquet(tmp_path):
    """Create a minimal Bronze Parquet file for testing Silver transformations."""
    data = [
        # First record
        {
            "qualifiedFips": "003G",
            "courtLevel": "G",
            "divisionType": "C",
            "caseNumber": "CR001",
            "formattedCaseNumber": "CR-001",
            "name": "John Doe",
            "offenseDate": "01/10/2024",
            "chargeAmended": "N",
            "codeSection": "18.2-95",
            "chargeDesc": "Grand Larceny",
            "caseType": "F",
            "hearingDate": "01/15/2024, 09:00 AM",
            "locality": {"localityName": "Albemarle"},
            "caseParticipant": [
                {
                    "contactInformation": {
                        "personName": {
                            "fullName": "Jane Smith"
                        }
                    },
                    "participantCode": "WIT",
                    "personalDetails": {
                        "race": "W",
                        "gender": "F"
                    }
                }
            ],
            "financialInformation": None,
            "caseHearing": None,
            "disposition": None
        },
        # Duplicate record (should be deduplicated by distinct caseNumber, hearingDate)
        {
            "qualifiedFips": "003G",
            "courtLevel": "G",
            "divisionType": "C",
            "caseNumber": "CR001",
            "formattedCaseNumber": "CR-001",
            "name": "John Doe Duplicate",
            "offenseDate": "01/10/2024",
            "chargeAmended": "N",
            "codeSection": "18.2-95",
            "chargeDesc": "Grand Larceny",
            "caseType": "F",
            "hearingDate": "01/15/2024, 09:00 AM",
            "locality": {"localityName": "Albemarle"},
            "caseParticipant": [],
            "financialInformation": None,
            "caseHearing": None,
            "disposition": None
        }
    ]
    jsonl_file = tmp_path / "raw.json"
    with open(jsonl_file, "w") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")
    
    bronze_output = str(tmp_path / "bronze" / "cases.parquet")
    build_bronze_layer(str(jsonl_file), bronze_output)
    return bronze_output


def test_silver_creates_parquet(sample_bronze_parquet, tmp_path):
    output = str(tmp_path / "silver" / "cases.parquet")
    build_silver_layer(sample_bronze_parquet, output)
    assert os.path.exists(output)


def test_silver_deduplicates_and_hashes_pii(sample_bronze_parquet, tmp_path):
    output = str(tmp_path / "silver" / "cases.parquet")
    build_silver_layer(sample_bronze_parquet, output)
    
    con = duckdb.connect()
    res = con.execute(f"SELECT * FROM read_parquet('{output}')").fetchall()
    # Should be deduplicated to 1 record
    assert len(res) == 1
    
    # Check that PII hashing works
    # Col 5 is defendant_name_hash in Silver layout
    row = con.execute(f"SELECT defendant_name_hash, offense_date, hearing_timestamp, locality_name FROM read_parquet('{output}')").fetchone()
    defendant_hash, offense_date, hearing_timestamp, locality = row
    
    # Check name is hashed and not "John Doe" or "John Doe Duplicate"
    assert defendant_hash is not None
    assert defendant_hash != "John Doe"
    
    # Check parsed date and timestamp type/value
    import datetime
    assert isinstance(offense_date, datetime.date)
    assert offense_date == datetime.date(2024, 1, 10)
    assert isinstance(hearing_timestamp, datetime.datetime)
    assert hearing_timestamp == datetime.datetime(2024, 1, 15, 9, 0)
    assert locality == "Albemarle"
    con.close()
